from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
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
    """Return true while a unit is active *or activating*.

    The updater units are Type=oneshot. systemd leaves those in ``activating``
    for the entire command, so checking only for ``active`` reports false for
    exactly the period the Web UI needs to follow.
    """
    try:
        result = subprocess.run(
            ["/usr/bin/systemctl", "is-active", service_name],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return (result.stdout or "").strip() in {"active", "activating", "reloading"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Atomically replace a status document without exposing partial JSON."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.chmod(tmp, 0o644)
        tmp.replace(path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _begin_operation(kind: str) -> str:
    operation_id = uuid.uuid4().hex
    now = _utc_now()
    data = _read_json(UPDATE_STATUS_PATH)
    if kind == "check":
        data.update(
            {
                "check_id": operation_id,
                "check_state": "queued",
                "check_started_at": now,
                "check_finished_at": None,
                "status": "checking",
                "error": None,
            }
        )
    else:
        data.update(
            {
                "operation_id": operation_id,
                "operation_kind": "update",
                "operation_state": "queued",
                "operation_started_at": now,
                "operation_updated_at": now,
                "operation_finished_at": None,
                "progress_phase": "queued",
                "progress_label": "Waiting for updater service",
                "progress_percent": 1,
                "restart_pending": False,
                "restart_performed": False,
                "status": "installing",
                "error": None,
            }
        )
    _write_json(UPDATE_STATUS_PATH, data)
    return operation_id


def _fail_operation(kind: str, operation_id: str, message: str) -> None:
    data = _read_json(UPDATE_STATUS_PATH)
    id_field = "check_id" if kind == "check" else "operation_id"
    if data.get(id_field) != operation_id:
        return
    now = _utc_now()
    if kind == "check":
        data.update(
            {
                "check_state": "failed",
                "check_finished_at": now,
                "status": "check_failed",
                "error": message,
            }
        )
    else:
        data.update(
            {
                "operation_state": "failed",
                "operation_updated_at": now,
                "operation_finished_at": now,
                "progress_label": "Update failed to start",
                "restart_pending": False,
                "status": "update_failed",
                "error": message,
            }
        )
    _write_json(UPDATE_STATUS_PATH, data)


def _queued_operation_is_recent(state_field: str, started_field: str) -> bool:
    status = _read_json(UPDATE_STATUS_PATH)
    if status.get(state_field) != "queued":
        return False
    try:
        started = datetime.fromisoformat(str(status[started_field]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return False
    return (datetime.now(timezone.utc) - started).total_seconds() < 30


def is_check_in_progress() -> bool:
    return _service_is_active(CHECK_SERVICE) or _queued_operation_is_recent(
        "check_state", "check_started_at"
    )


def is_update_in_progress() -> bool:
    """True while the update unit is actually running.

    The authoritative answer to "can another install start", replacing a
    fixed time window that could only ever be a guess at how long an install
    takes.
    """
    return _service_is_active(UPDATE_SERVICE) or _queued_operation_is_recent(
        "operation_state", "operation_started_at"
    )


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

    check_in_progress = is_check_in_progress()
    update_in_progress = is_update_in_progress()
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
        "check_id": update.get("check_id"),
        "check_state": update.get("check_state"),
        "check_started_at": update.get("check_started_at"),
        "check_finished_at": update.get("check_finished_at"),
        "operation_id": update.get("operation_id"),
        "operation_kind": update.get("operation_kind"),
        "operation_state": update.get("operation_state"),
        "operation_started_at": update.get("operation_started_at"),
        "operation_updated_at": update.get("operation_updated_at"),
        "operation_finished_at": update.get("operation_finished_at"),
        "progress_phase": update.get("progress_phase"),
        "progress_label": update.get("progress_label"),
        "progress_percent": update.get("progress_percent"),
        "restart_pending": bool(update.get("restart_pending")),
        "restart_performed": bool(update.get("restart_performed")),
    }


def trigger_update_check() -> str:
    if not _service_unit_exists(CHECK_SERVICE):
        raise RuntimeError("Update-check service is not installed on this host.")
    try:
        operation_id = _begin_operation("check")
    except OSError as exc:
        raise RuntimeError("Unable to initialize update-check status.") from exc
    try:
        _run_systemctl_start(CHECK_SERVICE)
    except RuntimeError as exc:
        _fail_operation("check", operation_id, str(exc))
        raise
    return operation_id


def trigger_update_install() -> str:
    if not _service_unit_exists(UPDATE_SERVICE):
        raise RuntimeError("Update service is not installed on this host.")
    try:
        operation_id = _begin_operation("update")
    except OSError as exc:
        raise RuntimeError("Unable to initialize update status.") from exc
    try:
        _run_systemctl_start(UPDATE_SERVICE)
    except RuntimeError as exc:
        _fail_operation("update", operation_id, str(exc))
        raise
    return operation_id
