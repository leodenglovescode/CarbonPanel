from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from fastapi import Header, HTTPException, status

from app.core.security import decode_token

INSTALL_ROOT = Path(os.getenv("CARBONPANEL_INSTALL_ROOT", "/opt/carbonpanel"))
SHARED_DIR = INSTALL_ROOT / "shared"
CURRENT_METADATA_PATH = INSTALL_ROOT / "current" / ".carbonpanel-release.json"
UPDATE_STATUS_PATH = SHARED_DIR / "update-status.json"

DEFAULT_REPO_URL = "https://github.com/leodenglovescode/CarbonPanel"

CHECK_SERVICE = "carbonpanel-update-check.service"
UPDATE_SERVICE = "carbonpanel-update.service"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def _service_is_active(service_name: str) -> bool:
    try:
        result = subprocess.run(
            ["/usr/bin/systemctl", "is-active", "--quiet", service_name],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False

    return result.returncode == 0


def _run_systemctl_start(service_name: str) -> None:
    command = ["/usr/bin/systemctl", "start", service_name]
    if os.geteuid() != 0:
        command = ["/usr/bin/sudo", "-n", *command]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("Required system command is missing on this host.") from exc
    except subprocess.CalledProcessError as exc:
        output = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(output or f"Unable to start {service_name}.") from exc


def get_system_version_status() -> dict[str, Any]:
    current = _read_json(CURRENT_METADATA_PATH)
    update = _read_json(UPDATE_STATUS_PATH)

    update_in_progress = _service_is_active(UPDATE_SERVICE)
    configured = bool(current) or bool(update) or INSTALL_ROOT.exists()
    status_value = str(update.get("status") or ("installing" if update_in_progress else "unknown"))

    return {
        "configured": configured,
        "repo_url": str(update.get("repo_url") or current.get("repo_url") or DEFAULT_REPO_URL),
        "current_version": current.get("version"),
        "current_commit": current.get("commit"),
        "current_source_type": current.get("source_type"),
        "installed_at": current.get("installed_at"),
        "latest_version": update.get("latest_version"),
        "latest_commit": update.get("latest_commit"),
        "latest_source_type": update.get("latest_source_type"),
        "checked_at": update.get("checked_at"),
        "update_available": bool(update.get("update_available")),
        "update_in_progress": update_in_progress,
        "status": "installing" if update_in_progress else status_value,
        "error": update.get("error"),
        "release_url": update.get("release_url"),
        "notes_url": update.get("notes_url"),
    }


def require_authenticated_token(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    try:
        payload = decode_token(token)
    except Exception as exc:  # pragma: no cover - delegated to existing token logic
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
        ) from exc

    scope = payload.get("scope")
    if scope not in (None, "", "full"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient token scope.",
        )

    return payload


def trigger_update_check() -> None:
    _run_systemctl_start(CHECK_SERVICE)


def trigger_update_install() -> None:
    _run_systemctl_start(UPDATE_SERVICE)
