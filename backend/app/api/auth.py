from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import brute_force
from app.core.dependencies import get_current_user, oauth2_scheme
from app.core.security import decode_token
from app.database import get_db
from app.models.device import Device
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


def _check_banned(ip: str | None, username: str | None = None) -> None:
    if brute_force.is_banned(ip, username):
        secs = brute_force.retry_after(ip, username)
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
    _check_banned(ip, request_data.username)
    ua = request.headers.get("user-agent")
    device_id = request.headers.get("x-device-id")
    try:
        result = await auth_service.login(
            request_data, db, ip_address=ip, user_agent=ua, device_id=device_id
        )
        brute_force.record_success(ip, request_data.username)
        return result
    except ValueError as exc:
        brute_force.record_failure(ip, request_data.username)
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
    device_id = request.headers.get("x-device-id")
    try:
        result = await auth_service.login_totp(
            request_data.session_token,
            request_data.totp_code,
            db,
            ip_address=ip,
            user_agent=ua,
            device_id=device_id,
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
async def logout(
    token: str = Depends(oauth2_scheme),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Revoke this session's device/jti so a stolen token can't be replayed
    # after the legitimate user logs out — not just a client-side discard.
    try:
        jti = decode_token(token).get("jti")
    except ValueError:
        jti = None
    if jti:
        result = await db.execute(select(Device).where(Device.jti == jti))
        device = result.scalar_one_or_none()
        if device:
            device.revoked = True
            await db.commit()
    return SuccessResponse()
