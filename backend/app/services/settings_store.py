"""
Shared on-disk key/value store for operator settings (settings.json).

Extracted from proxy_service so more than one feature can persist into the
same file without each re-deriving the install-aware path. The path logic is
unchanged from the original: explicit override, then the shared install
directory if it exists and is actually writable, then a dev fallback under
~/.config.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _default_settings_path() -> Path:
    # Honour explicit override first.
    if override := os.getenv("CARBONPANEL_SETTINGS_FILE"):
        return Path(override)
    # In a production install, write alongside the other shared state files.
    # os.access(W_OK) matters, not just is_dir(): a dev checkout running as a
    # regular user on the same host as a real install would otherwise pick a
    # shared/ directory it has no permission to actually write into.
    shared = Path(os.getenv("CARBONPANEL_INSTALL_ROOT", "/opt/carbonpanel")) / "shared"
    if shared.is_dir() and os.access(shared, os.W_OK):
        return shared / "settings.json"
    # Dev / non-installed fallback.
    return Path.home() / ".config" / "carbonpanel" / "settings.json"


SETTINGS_FILE = _default_settings_path()


def read_all() -> dict[str, Any]:
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_all(data: dict[str, Any]) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_key(key: str, default: Any = None) -> Any:
    return read_all().get(key, default)


def set_key(key: str, value: Any) -> None:
    data = read_all()
    data[key] = value
    write_all(data)
