from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.background_image_service import (
    MAX_UPLOAD_BYTES,
    compress_to_jpeg,
    delete_image,
    load_image,
    save_image,
)

router = APIRouter(prefix="/settings/background-image", tags=["background-image"])

Target = Literal["app", "login"]


@router.post("/{target}")
async def upload_background_image(
    target: Target,
    file: UploadFile,
    _: User = Depends(get_current_user),
):
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image too large — max 20 MB")
    try:
        compressed = compress_to_jpeg(raw)
    except Exception:
        raise HTTPException(400, "Invalid or unsupported image file")
    save_image(target, compressed)
    return {"ok": True, "bytes": len(compressed)}


@router.delete("/{target}")
async def remove_background_image(target: Target, _: User = Depends(get_current_user)):
    delete_image(target)
    return {"ok": True}


@router.get("/app")
async def get_app_background_image(_: User = Depends(get_current_user)):
    data = load_image("app")
    if data is None:
        raise HTTPException(404)
    headers = {"Cache-Control": "private, max-age=31536000, immutable"}
    return Response(content=data, media_type="image/jpeg", headers=headers)


# The login screen renders before authentication exists, so its background
# image has to be servable without a session — this is the one endpoint here
# that's intentionally public. It's a single-admin panel with no per-user
# login screens, so there's nothing user-specific being exposed.
@router.get("/login")
async def get_login_background_image():
    data = load_image("login")
    if data is None:
        raise HTTPException(404)
    headers = {"Cache-Control": "public, max-age=31536000, immutable"}
    return Response(content=data, media_type="image/jpeg", headers=headers)
