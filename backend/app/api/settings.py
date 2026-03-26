from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangeProfileRequest,
    SuccessResponse,
    TOTPConfirmRequest,
    TOTPSetupResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.put("/profile", response_model=SuccessResponse)
async def change_profile(
    request: ChangeProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await auth_service.change_profile(current_user, request, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return SuccessResponse()


@router.get("/2fa/setup", response_model=TOTPSetupResponse)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.setup_2fa(current_user, db)


@router.post("/2fa/enable", response_model=SuccessResponse)
async def enable_2fa(
    request: TOTPConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await auth_service.enable_2fa(current_user, request.totp_code, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return SuccessResponse()


@router.post("/2fa/disable", response_model=SuccessResponse)
async def disable_2fa(
    request: TOTPConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await auth_service.disable_2fa(current_user, request.totp_code, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return SuccessResponse()
