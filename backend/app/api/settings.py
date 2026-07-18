import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import brute_force
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
from app.services.proxy_service import build_opener, get_proxy, set_proxy

router = APIRouter(prefix="/settings", tags=["settings"])


# ── Proxy ──────────────────────────────────────────────────────────────────────

class ProxyConfig(BaseModel):
    enabled: bool = False
    type: str = "http"   # "http" | "socks5"
    host: str = "127.0.0.1"
    port: int = 7890


@router.get("/proxy", response_model=ProxyConfig)
async def get_proxy_settings(_: User = Depends(get_current_user)):
    return get_proxy()


@router.put("/proxy", response_model=ProxyConfig)
async def update_proxy_settings(config: ProxyConfig, _: User = Depends(get_current_user)):
    set_proxy(config.model_dump())
    return config


_PROXY_TEST_URL = "https://api.github.com"


def _test_proxy_sync() -> dict:
    import urllib.request

    req = urllib.request.Request(
        _PROXY_TEST_URL,
        headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "CarbonPanel"},
    )
    try:
        opener = build_opener()
        if opener:
            with opener.open(req, timeout=10) as resp:
                resp.read()
        else:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        return {"success": True, "message": "Connected to GitHub API successfully"}
    except RuntimeError as exc:
        return {"success": False, "message": str(exc)}
    except Exception as exc:
        return {"success": False, "message": f"Connection failed: {exc}"}


@router.post("/proxy/test")
async def test_proxy_settings(_: User = Depends(get_current_user)):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _test_proxy_sync)


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


# TOTP codes are 6 digits (1-in-1M per guess) — without a lockout here, a
# stolen session cookie (XSS, unlocked device, leaked via a misconfigured
# proxy) would let an attacker grind these endpoints to strip/re-arm 2FA
# without ever knowing the actual second factor. Keyed separately from the
# login brute-force counter so the two don't interfere with each other.
def _2fa_brute_force_key(http_request: Request, current_user: User) -> tuple[str | None, str]:
    ip = http_request.client.host if http_request.client else None
    return ip, f"2fa:{current_user.username}"


def _check_2fa_banned(ip: str | None, key: str) -> None:
    if brute_force.is_banned(ip, key):
        secs = brute_force.retry_after(ip, key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Try again in {secs} seconds.",
            headers={"Retry-After": str(secs)},
        )


@router.post("/2fa/enable", response_model=SuccessResponse)
async def enable_2fa(
    request: TOTPConfirmRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ip, key = _2fa_brute_force_key(http_request, current_user)
    _check_2fa_banned(ip, key)
    try:
        await auth_service.enable_2fa(current_user, request.totp_code, db)
        brute_force.record_success(ip, key)
    except ValueError as exc:
        brute_force.record_failure(ip, key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return SuccessResponse()


@router.post("/2fa/disable", response_model=SuccessResponse)
async def disable_2fa(
    request: TOTPConfirmRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ip, key = _2fa_brute_force_key(http_request, current_user)
    _check_2fa_banned(ip, key)
    try:
        await auth_service.disable_2fa(current_user, request.totp_code, db)
        brute_force.record_success(ip, key)
    except ValueError as exc:
        brute_force.record_failure(ip, key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return SuccessResponse()
