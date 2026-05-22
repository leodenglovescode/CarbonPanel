import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from app.services.update_runtime import (
    get_system_version_status,
    require_authenticated_token,
    trigger_update_check,
    trigger_update_install,
)

router = APIRouter(prefix="/api/v1/system", tags=["system"])

_VERSION_TIMEOUT = 7.0  # seconds — covers DNS + connect + read


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
    try:
        await loop.run_in_executor(None, trigger_update_check)
    except RuntimeError:
        # Service not installed or not permitted — version endpoint serves live/cached data
        pass

    return {"success": True, "message": "Update check started."}


@router.post("/install-update", status_code=status.HTTP_202_ACCEPTED)
async def install_update(_: dict = Depends(require_authenticated_token)):
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, trigger_update_install)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {"success": True, "message": "Update installation started."}
