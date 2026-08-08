import asyncio
import os
import subprocess
import time

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.update_runtime import (
    CHECK_SERVICE,
    UPDATE_SERVICE,
    get_system_version_status,
    trigger_update_check,
    is_update_in_progress,
    trigger_update_install,
)

router = APIRouter(prefix="/api/v1/system", tags=["system"])

_VERSION_TIMEOUT = 7.0  # seconds — covers DNS + connect + read
# Guards only the window between triggering systemd and it reporting the unit
# active. Overlap beyond that is prevented by is_update_in_progress().
_TRIGGER_DEBOUNCE = 10  # seconds
_last_install_ts: float = 0.0


@router.get("/version")
async def get_version_status(_: User = Depends(get_current_user)):
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, get_system_version_status),
            timeout=_VERSION_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return {
            "configured": True,
            "update_available": False,
            "update_in_progress": False,
            "error": "GitHub API timed out — check network connectivity",
            "current_version": None,
            "latest_version": None,
            "checked_at": None,
        }


@router.post("/check-updates", status_code=status.HTTP_202_ACCEPTED)
async def check_updates(_: User = Depends(get_current_user)):
    loop = asyncio.get_event_loop()
    note: str | None = None
    try:
        await loop.run_in_executor(None, trigger_update_check)
    except RuntimeError as exc:
        note = str(exc)

    if note:
        return {
            "success": True,
            "message": f"Update check could not start the update daemon — {note}. "
                       "Version status is still available via the live GitHub check below.",
        }
    return {"success": True, "message": "Update check started."}


@router.post("/install-update", status_code=status.HTTP_202_ACCEPTED)
async def install_update(_: User = Depends(get_current_user)):
    """Start an update install.

    Gated on whether an install is *actually running*, not on how long ago one
    was last triggered. Each install advances the panel one release, so a host
    several versions behind is upgraded by installing repeatedly — and a fixed
    five-minute lockout made that take five minutes per version even though
    each install had long since finished. The old window was also only ever a
    guess at install duration: too short to prevent overlap on a slow host,
    too long on a fast one.
    """
    global _last_install_ts
    loop = asyncio.get_event_loop()

    if await loop.run_in_executor(None, is_update_in_progress):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An update is already installing. Wait for it to finish.",
        )

    # systemd needs a moment to report the unit as active, so a short debounce
    # covers the gap between triggering and is-active becoming true. This is a
    # race guard, not a rate limit — it only has to outlast that window.
    now = time.monotonic()
    elapsed = now - _last_install_ts
    if elapsed < _TRIGGER_DEBOUNCE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An update was just triggered. Give it a moment to start.",
        )
    _last_install_ts = now

    try:
        await loop.run_in_executor(None, trigger_update_install)
    except RuntimeError as exc:
        _last_install_ts = 0.0  # reset on failure so it can be retried at once
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {"success": True, "message": "Update installation started."}


@router.get("/service-logs")
async def get_service_logs(_: User = Depends(get_current_user)):
    def _fetch() -> list[str]:
        cmd = [
            "journalctl",
            "-u", CHECK_SERVICE,
            "-u", UPDATE_SERVICE,
            "--no-pager",
            "-n", "150",
            "--output=short-iso",
        ]
        if os.geteuid() != 0:
            cmd = ["/usr/bin/sudo", "-n"] + cmd
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
            output = result.stdout or result.stderr or ""
            return [line for line in output.splitlines() if line.strip()]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

    loop = asyncio.get_event_loop()
    lines = await loop.run_in_executor(None, _fetch)
    return {"lines": lines}
