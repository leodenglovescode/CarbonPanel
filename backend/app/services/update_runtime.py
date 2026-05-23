from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import Header, HTTPException, status

from app.core.security import decode_token

INSTALL_ROOT = Path(os.getenv("CARBONPANEL_INSTALL_ROOT", "/opt/carbonpanel"))
SHARED_DIR = INSTALL_ROOT / "shared"
CURRENT_METADATA_PATH = INSTALL_ROOT / "current" / ".carbonpanel-release.json"
UPDATE_STATUS_PATH = SHARED_DIR / "update-status.json"

DEFAULT_REPO_URL = "https://github.com/leodenglovescode/CarbonPanel"
GITHUB_API_LATEST = (
    "https://api.github.com/repos/leodenglovescode/CarbonPanel/releases/latest"
)

CHECK_SERVICE = "carbonpanel-update-check.service"
UPDATE_SERVICE = "carbonpanel-update.service"


# ── Helpers ────────────────────────────────────────────────────────────────────

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


def _is_docker_mode() -> bool:
    """True when no self-hosted install files are present (running in Docker)."""
    return not INSTALL_ROOT.exists()


def _fetch_github_release() -> dict[str, Any]:
    """Fetch latest release from GitHub API. Returns {} on any error."""
    from app.services.proxy_service import build_opener

    req = urllib.request.Request(
        GITHUB_API_LATEST,
        headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "CarbonPanel"},
    )
    try:
        opener = build_opener()
        if opener:
            with opener.open(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return {}


# ── Docker-mode version status (GitHub API) ────────────────────────────────────

def _docker_version_status() -> dict[str, Any]:
    current_version = os.getenv("CARBONPANEL_VERSION") or None
    release = _fetch_github_release()
    latest_tag: str | None = release.get("tag_name") or None

    update_available = bool(
        current_version
        and latest_tag
        and current_version.lstrip("v") != latest_tag.lstrip("v")
    )

    docker_image = "ghcr.io/leodenglovescode/carbonpanel:latest"

    return {
        "configured": True,
        "repo_url": DEFAULT_REPO_URL,
        "current_version": current_version,
        "current_commit": None,
        "current_source_type": "docker",
        "installed_at": None,
        "latest_version": latest_tag,
        "latest_commit": None,
        "latest_source_type": "docker",
        "checked_at": release.get("published_at"),
        "update_available": update_available,
        "update_in_progress": False,
        "status": "update-available" if update_available else "up-to-date",
        "error": None if release else "Could not reach GitHub API",
        "release_url": release.get("html_url"),
        "notes_url": release.get("html_url"),
        "deployment_type": "docker",
        "docker_pull_cmd": f"docker pull {docker_image}" if update_available else None,
    }


# ── Self-hosted-mode version status (file-based) ──────────────────────────────

def _selfhosted_version_status() -> dict[str, Any]:
    current = _read_json(CURRENT_METADATA_PATH)
    update = _read_json(UPDATE_STATUS_PATH)

    update_in_progress = _service_is_active(UPDATE_SERVICE)
    configured = bool(current) or bool(update) or INSTALL_ROOT.exists()
    status_value = str(
        update.get("status") or ("installing" if update_in_progress else "unknown")
    )

    return {
        "configured": configured,
        "repo_url": str(
            update.get("repo_url") or current.get("repo_url") or DEFAULT_REPO_URL
        ),
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
        "deployment_type": "self-hosted",
        "docker_pull_cmd": None,
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def get_system_version_status() -> dict[str, Any]:
    if _is_docker_mode():
        return _docker_version_status()
    return _selfhosted_version_status()


def require_authenticated_token(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
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
    except Exception as exc:  # pragma: no cover
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
    if _is_docker_mode():
        # Docker mode: /system/version always fetches live from GitHub API — no daemon needed.
        return
    _run_systemctl_start(CHECK_SERVICE)


def trigger_update_install() -> None:
    if _is_docker_mode():
        raise RuntimeError(
            "Auto-update is not available in Docker deployments. "
            "Pull the latest image: docker pull ghcr.io/leodenglovescode/carbonpanel:latest"
        )
    _run_systemctl_start(UPDATE_SERVICE)
