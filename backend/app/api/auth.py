from fastapi import APIRouter, Depends, HTTPException, Request, status
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
async def login(
    request_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        return await auth_service.login(request_data, db, ip_address=ip, user_agent=ua)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


@router.post("/login/totp", response_model=TokenResponse)
async def login_totp(
    request_data: TOTPLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        return await auth_service.login_totp(
            request_data.session_token,
            request_data.totp_code,
            db,
            ip_address=ip,
            user_agent=ua,
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
