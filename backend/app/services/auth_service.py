import base64
import io

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
from app.models.user import User
from app.schemas.auth import (
    ChangeProfileRequest,
    LoginRequest,
    TOTPSetupResponse,
    TokenResponse,
    TOTPRequiredResponse,
)


async def login(request: LoginRequest, db: AsyncSession) -> TokenResponse | TOTPRequiredResponse:
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

    token = create_access_token(user_id=user.id, username=user.username)
    return TokenResponse(access_token=token)


async def login_totp(session_token: str, totp_code: str, db: AsyncSession) -> TokenResponse:
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

    token = create_access_token(user_id=user.id, username=user.username)
    return TokenResponse(access_token=token)


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
