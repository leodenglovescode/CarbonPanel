import asyncio
import os
import subprocess
import time

from fastapi import APIRouter, Depends, HTTPException, status

from app.services.update_runtime import (
    CHECK_SERVICE,
    UPDATE_SERVICE,
    get_system_version_status,
    require_authenticated_token,
    trigger_update_check,
    trigger_update_install,
)

router = APIRouter(prefix="/api/v1/system", tags=["system"])

_VERSION_TIMEOUT = 7.0  # seconds — covers DNS + connect + read
_INSTALL_COOLDOWN = 5 * 60  # seconds between install-update triggers
_last_install_ts: float = 0.0


@router.get("/version")
async def get_version_status(_: dict = Depends(require_authenticated_token)):
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
            "deployment_type": None,
            "current_version": None,
            "latest_version": None,
            "checked_at": None,
            "docker_pull_cmd": None,
        }


@router.post("/check-updates", status_code=status.HTTP_202_ACCEPTED)
async def check_updates(_: dict = Depends(require_authenticated_token)):
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
async def install_update(_: dict = Depends(require_authenticated_token)):
    global _last_install_ts
    now = time.monotonic()
    elapsed = now - _last_install_ts
    if elapsed < _INSTALL_COOLDOWN:
        retry_after = int(_INSTALL_COOLDOWN - elapsed)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Update already triggered recently. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
    _last_install_ts = now

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, trigger_update_install)
    except RuntimeError as exc:
        _last_install_ts = 0.0  # reset on failure so it can be retried
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {"success": True, "message": "Update installation started."}


@router.get("/service-logs")
async def get_service_logs(_: dict = Depends(require_authenticated_token)):
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
