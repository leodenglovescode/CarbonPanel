from fastapi import APIRouter, Depends, HTTPException, status

from app.services.update_runtime import (
    get_system_version_status,
    require_authenticated_token,
    trigger_update_check,
    trigger_update_install,
)

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/version")
async def get_version_status(_: dict = Depends(require_authenticated_token)):
    return get_system_version_status()


@router.post("/check-updates", status_code=status.HTTP_202_ACCEPTED)
async def check_updates(_: dict = Depends(require_authenticated_token)):
    try:
        trigger_update_check()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {"success": True, "message": "Update check started."}


@router.post("/install-update", status_code=status.HTTP_202_ACCEPTED)
async def install_update(_: dict = Depends(require_authenticated_token)):
    try:
        trigger_update_install()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {"success": True, "message": "Update installation started."}
