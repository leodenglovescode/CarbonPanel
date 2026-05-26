from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import brute_force
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


def _get_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _check_banned(ip: str | None) -> None:
    if brute_force.is_banned(ip):
        secs = brute_force.retry_after(ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Try again in {secs} seconds.",
            headers={"Retry-After": str(secs)},
        )


@router.post("/login", response_model=TokenResponse | TOTPRequiredResponse)
async def login(
    request_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = _get_ip(request)
    _check_banned(ip)
    ua = request.headers.get("user-agent")
    try:
        result = await auth_service.login(request_data, db, ip_address=ip, user_agent=ua)
        brute_force.record_success(ip)
        return result
    except ValueError as exc:
        brute_force.record_failure(ip)
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
    ip = _get_ip(request)
    _check_banned(ip)
    ua = request.headers.get("user-agent")
    try:
        result = await auth_service.login_totp(
            request_data.session_token,
            request_data.totp_code,
            db,
            ip_address=ip,
            user_agent=ua,
        )
        brute_force.record_success(ip)
        return result
    except ValueError as exc:
        brute_force.record_failure(ip)
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
