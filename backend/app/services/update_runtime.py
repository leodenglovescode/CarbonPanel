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
GITHUB_API_COMMITS = (
    "https://api.github.com/repos/leodenglovescode/CarbonPanel/commits/HEAD"
)

CHECK_SERVICE = "carbonpanel-update-check.service"
UPDATE_SERVICE = "carbonpanel-update.service"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _read_json(path: Path) -> dict[str, Any]:
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, PermissionError, json.JSONDecodeError):
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


def _service_unit_exists(service_name: str) -> bool:
    """Return True only if the systemd unit file is installed on this host."""
    try:
        result = subprocess.run(
            ["/usr/bin/systemctl", "list-unit-files", "--no-pager", service_name],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return service_name in (result.stdout or "")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _run_systemctl_start(service_name: str) -> None:
    command = ["/usr/bin/systemctl", "start", service_name]
    if os.geteuid() != 0:
        command = ["/usr/bin/sudo", "-n", *command]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=20)
    except FileNotFoundError as exc:
        raise RuntimeError("Required system command is missing on this host.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Timed out waiting for systemctl to start {service_name}.") from exc
    except subprocess.CalledProcessError as exc:
        output = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(output or f"Unable to start {service_name}.") from exc


def _is_docker_mode() -> bool:
    """True when no self-hosted install files are present (running in Docker)."""
    return not INSTALL_ROOT.exists()


def _github_get(url: str) -> dict[str, Any]:
    """GET a GitHub API URL. Returns {} on any error (including 404)."""
    from app.services.proxy_service import build_opener

    req = urllib.request.Request(
        url,
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


def _fetch_github_release() -> dict[str, Any]:
    """Fetch latest release. Returns {} if no releases exist."""
    data = _github_get(GITHUB_API_LATEST)
    # GitHub returns {"message": "Not Found"} with 404 for repos with no releases
    if data.get("message") == "Not Found" or not data.get("tag_name"):
        return {}
    return data


def _fetch_latest_commit_sha() -> str | None:
    """Return the SHA of the latest commit on the default branch, or None on error."""
    data = _github_get(GITHUB_API_COMMITS)
    return data.get("sha") or None


# ── Docker-mode version status (GitHub API) ────────────────────────────────────

def _docker_version_status() -> dict[str, Any]:
    current_version = os.getenv("CARBONPANEL_VERSION") or None
    current_commit = os.getenv("CARBONPANEL_COMMIT") or None

    release = _fetch_github_release()
    latest_tag: str | None = release.get("tag_name") or None

    # When no tagged release exists, fall back to comparing raw commits
    latest_commit: str | None = None
    if not latest_tag:
        latest_commit = _fetch_latest_commit_sha()

    if latest_tag and current_version:
        update_available = current_version.lstrip("v") != latest_tag.lstrip("v")
    elif latest_commit and current_commit:
        update_available = current_commit != latest_commit
    else:
        update_available = False

    docker_image = "ghcr.io/leodenglovescode/carbonpanel:latest"
    error: str | None = None
    if not release and not latest_commit:
        error = "Could not reach GitHub API"

    return {
        "configured": True,
        "repo_url": DEFAULT_REPO_URL,
        "current_version": current_version or current_commit,
        "current_commit": current_commit,
        "current_source_type": "docker",
        "installed_at": None,
        "latest_version": latest_tag or latest_commit,
        "latest_commit": latest_commit,
        "latest_source_type": "docker",
        "checked_at": release.get("published_at"),
        "update_available": update_available,
        "update_in_progress": False,
        "check_in_progress": False,
        "status": "update-available" if update_available else "up-to-date",
        "error": error,
        "release_url": release.get("html_url"),
        "notes_url": release.get("html_url"),
        "deployment_type": "docker",
        "docker_pull_cmd": f"docker pull {docker_image}" if update_available else None,
    }


# ── Self-hosted-mode version status (file-based) ──────────────────────────────

def _selfhosted_version_status() -> dict[str, Any]:
    current = _read_json(CURRENT_METADATA_PATH)
    update = _read_json(UPDATE_STATUS_PATH)

    check_in_progress = _service_is_active(CHECK_SERVICE)
    update_in_progress = _service_is_active(UPDATE_SERVICE)
    configured = bool(current) or bool(update) or INSTALL_ROOT.exists()
    status_value = str(
        update.get("status") or ("installing" if update_in_progress else "unknown")
    )

    if update_in_progress:
        display_status = "installing"
    elif check_in_progress:
        display_status = "checking"
    else:
        display_status = status_value

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
        "check_in_progress": check_in_progress,
        "status": display_status,
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
    if not _service_unit_exists(CHECK_SERVICE):
        # Service not installed (e.g. dev environment) — version check still works via GitHub API.
        return
    _run_systemctl_start(CHECK_SERVICE)


def trigger_update_install() -> None:
    if _is_docker_mode():
        raise RuntimeError(
            "Auto-update is not available in Docker deployments. "
            "Pull the latest image: docker pull ghcr.io/leodenglovescode/carbonpanel:latest"
        )
    _run_systemctl_start(UPDATE_SERVICE)
