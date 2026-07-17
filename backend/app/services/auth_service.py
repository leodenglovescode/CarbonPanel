import base64
import io
import uuid
from datetime import datetime

import pyotp
import qrcode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.device import Device
from app.models.user import User
from app.schemas.auth import (
    ChangeProfileRequest,
    LoginRequest,
    TOTPRequiredResponse,
    TOTPSetupResponse,
)


def _device_name(user_agent: str | None) -> str:
    if not user_agent:
        return "Unknown device"
    ua = user_agent.lower()
    if "iphone" in ua:
        os_name = "iPhone"
    elif "ipad" in ua:
        os_name = "iPad"
    elif "android" in ua:
        os_name = "Android"
    elif "windows" in ua:
        os_name = "Windows"
    elif "mac os" in ua or "macintosh" in ua:
        os_name = "macOS"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Unknown"
    if "edg/" in ua or "edghtml" in ua:
        browser = "Edge"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "chrome" in ua:
        browser = "Chrome"
    elif "safari" in ua:
        browser = "Safari"
    else:
        browser = "Browser"
    return f"{browser} on {os_name}"


async def _record_device(
    user_id: str,
    jti: str,
    ip_address: str | None,
    user_agent: str | None,
    db: AsyncSession,
    name_prefix: str = "",
    device_id: str | None = None,
) -> None:
    name = ((name_prefix + " " if name_prefix else "") + _device_name(user_agent)).strip()

    # Same browser fingerprint re-authenticating (session expired, logged out and
    # back in, etc.) — update its existing row instead of piling up duplicates.
    if device_id:
        result = await db.execute(
            select(Device).where(
                Device.user_id == user_id,
                Device.device_id == device_id,
                Device.revoked == False,  # noqa: E712
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.jti = jti
            existing.name = name
            existing.ip_address = ip_address
            existing.user_agent = user_agent
            existing.last_seen = datetime.utcnow()
            db.add(existing)
            return

    device = Device(
        user_id=user_id,
        jti=jti,
        name=name,
        ip_address=ip_address,
        user_agent=user_agent,
        device_id=device_id,
    )
    db.add(device)


async def login(
    request: LoginRequest,
    db: AsyncSession,
    ip_address: str | None = None,
    user_agent: str | None = None,
    device_id: str | None = None,
) -> str | TOTPRequiredResponse:
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise ValueError("Invalid username or password")

    if user.totp_enabled:
        session_token = create_access_token(
            user_id=user.id,
            username=user.username,
            scope="totp_only",
            expires_minutes=settings.totp_session_expire_minutes,
        )
        return TOTPRequiredResponse(session_token=session_token)

    jti = str(uuid.uuid4())
    token = create_access_token(user_id=user.id, username=user.username, jti=jti)
    await _record_device(user.id, jti, ip_address, user_agent, db, device_id=device_id)
    await db.commit()
    return token


async def login_totp(
    session_token: str,
    totp_code: str,
    db: AsyncSession,
    ip_address: str | None = None,
    user_agent: str | None = None,
    device_id: str | None = None,
) -> str:
    try:
        payload = decode_token(session_token)
    except ValueError:
        raise ValueError("Invalid or expired session token")

    if payload.get("scope") != "totp_only":
        raise ValueError("Invalid session token scope")

    user_id: str = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.totp_secret:
        raise ValueError("User not found or TOTP not configured")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(totp_code, valid_window=1):
        raise ValueError("Invalid TOTP code")

    jti = str(uuid.uuid4())
    token = create_access_token(user_id=user.id, username=user.username, jti=jti)
    await _record_device(user.id, jti, ip_address, user_agent, db, device_id=device_id)
    await db.commit()
    return token


async def setup_2fa(user: User, db: AsyncSession) -> TOTPSetupResponse:
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.username, issuer_name="CarbonPanel")

    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    user.pending_totp_secret = secret
    db.add(user)
    await db.commit()

    return TOTPSetupResponse(secret=secret, otpauth_uri=uri, qr_png_b64=qr_b64)


async def enable_2fa(user: User, totp_code: str, db: AsyncSession) -> None:
    if not user.pending_totp_secret:
        raise ValueError("No pending TOTP setup. Call setup first.")

    totp = pyotp.TOTP(user.pending_totp_secret)
    if not totp.verify(totp_code, valid_window=1):
        raise ValueError("Invalid TOTP code")

    user.totp_secret = user.pending_totp_secret
    user.pending_totp_secret = None
    user.totp_enabled = True
    db.add(user)
    await db.commit()


async def change_profile(user: User, request: ChangeProfileRequest, db: AsyncSession) -> None:
    if not verify_password(request.current_password, user.password_hash):
        raise ValueError("Current password is incorrect")

    if request.new_username:
        result = await db.execute(select(User).where(User.username == request.new_username))
        if result.scalar_one_or_none():
            raise ValueError("Username already taken")
        user.username = request.new_username

    if request.new_password:
        if len(request.new_password) < 8:
            raise ValueError("New password must be at least 8 characters")
        user.password_hash = hash_password(request.new_password)

    db.add(user)
    await db.commit()


async def disable_2fa(user: User, totp_code: str, db: AsyncSession) -> None:
    if not user.totp_enabled or not user.totp_secret:
        raise ValueError("2FA is not enabled")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(totp_code, valid_window=1):
        raise ValueError("Invalid TOTP code")

    user.totp_enabled = False
    user.totp_secret = None
    user.pending_totp_secret = None
    db.add(user)
    await db.commit()
