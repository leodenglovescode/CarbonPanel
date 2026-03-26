from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    SuccessResponse,
    TokenResponse,
    TOTPLoginRequest,
    TOTPRequiredResponse,
    UserInfo,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse | TOTPRequiredResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await auth_service.login(request, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


@router.post("/login/totp", response_model=TokenResponse)
async def login_totp(request: TOTPLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await auth_service.login_totp(
            request.session_token,
            request.totp_code,
            db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


@router.get("/me", response_model=UserInfo)
async def me(current_user: User = Depends(get_current_user)):
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        totp_enabled=current_user.totp_enabled,
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout(_: User = Depends(get_current_user)):
    # Stateless JWT — client discards the token
    return SuccessResponse()
