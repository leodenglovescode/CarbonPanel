from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

INSTALL_ROOT = Path(os.getenv("CARBONPANEL_INSTALL_ROOT", "/opt/carbonpanel"))
SHARED_DIR = INSTALL_ROOT / "shared"
CURRENT_METADATA_PATH = INSTALL_ROOT / "current" / ".carbonpanel-release.json"
UPDATE_STATUS_PATH = SHARED_DIR / "update-status.json"

DEFAULT_REPO_URL = "https://github.com/leodenglovescode/CarbonPanel"

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
    # --no-block: these are Type=oneshot units that can run for minutes (a full
    # update rebuilds the venv + frontend). Without it, `systemctl start` blocks
    # until the unit finishes, which blew right through the timeout below.
    command = ["/usr/bin/systemctl", "start", "--no-block", service_name]
    if os.geteuid() != 0:
        command = ["/usr/bin/sudo", "-n", *command]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=20)
    except FileNotFoundError as exc:
        raise RuntimeError("Required system command is missing on this host.") from exc
    except subprocess.TimeoutExpired as exc:
        # --no-block only waits for systemd to acknowledge the job was queued,
        # which is normally near-instant — a timeout here usually means `sudo`
        # /`systemctl` itself was slow to exit (busy host, journald
        # backpressure, etc.), not that the start actually failed. Check
        # ground truth before raising: if the unit is already running, the
        # trigger worked and this was a false alarm.
        if _service_is_active(service_name):
            return
        stderr = (exc.stderr or "").strip() if isinstance(exc.stderr, str) else ""
        detail = f" ({stderr})" if stderr else ""
        raise RuntimeError(
            f"Timed out waiting for systemctl to start {service_name}{detail}."
        ) from exc
    except subprocess.CalledProcessError as exc:
        output = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(output or f"Unable to start {service_name}.") from exc


# ── Public API ─────────────────────────────────────────────────────────────────

def get_system_version_status() -> dict[str, Any]:
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
    }


def trigger_update_check() -> None:
    if not _service_unit_exists(CHECK_SERVICE):
        # Service not installed (e.g. dev environment) — nothing to trigger.
        return
    _run_systemctl_start(CHECK_SERVICE)


def trigger_update_install() -> None:
    _run_systemctl_start(UPDATE_SERVICE)
