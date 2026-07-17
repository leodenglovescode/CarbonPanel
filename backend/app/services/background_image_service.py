from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Literal

from PIL import Image, ImageOps

Target = Literal["app", "login"]

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB — validated before decoding
MAX_OUTPUT_BYTES = 2 * 1024 * 1024  # 2 MB — compressed output ceiling
MAX_DIMENSION = 2560  # long-edge cap; plenty for any display background


def _images_dir() -> Path:
    # Mirrors the resolution order used for other shared runtime state
    # (see proxy_service._default_settings_path) so installs keep every
    # piece of mutable config under the same root.
    #
    # os.access(W_OK) matters, not just is_dir(): a dev checkout running as
    # a regular user on the same host as a real install (or any host where
    # /opt/carbonpanel exists but is owned by the carbonpanel service user)
    # would otherwise "successfully" pick a shared/ directory it has no
    # permission to actually write into, and only find out via a 500 on the
    # first upload.
    if override := os.getenv("CARBONPANEL_DATA_DIR"):
        base = Path(override)
    else:
        shared = Path(os.getenv("CARBONPANEL_INSTALL_ROOT", "/opt/carbonpanel")) / "shared"
        writable = shared.is_dir() and os.access(shared, os.W_OK)
        base = shared if writable else Path.home() / ".config" / "carbonpanel"
    directory = base / "background-images"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _image_path(target: Target) -> Path:
    return _images_dir() / f"{target}.jpg"


def compress_to_jpeg(
    raw: bytes,
    max_bytes: int = MAX_OUTPUT_BYTES,
    max_dimension: int = MAX_DIMENSION,
) -> bytes:
    """Decode any supported image and re-encode as a size-capped JPEG.

    Raises on unreadable/corrupt input — callers should turn that into a 400.
    """
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)  # respect camera orientation before it's lost
    img = img.convert("RGB")  # drop alpha/palette so JPEG encoding is always valid

    if max(img.size) > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    data = b""
    for _ in range(6):  # a few shrink rounds, each trying a quality ladder
        for quality in (85, 70, 55, 40):
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            data = buf.getvalue()
            if len(data) <= max_bytes:
                return data
        w, h = img.size
        if min(w, h) < 200:
            break
        img = img.resize((int(w * 0.8), int(h * 0.8)), Image.LANCZOS)
    return data  # best effort — smallest we managed, even if still over


def save_image(target: Target, jpeg_bytes: bytes) -> None:
    _image_path(target).write_bytes(jpeg_bytes)


def load_image(target: Target) -> bytes | None:
    path = _image_path(target)
    if not path.is_file():
        return None
    return path.read_bytes()


def delete_image(target: Target) -> None:
    _image_path(target).unlink(missing_ok=True)
