from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import decode_token
from app.database import get_db
from app.models.device import Device
from app.models.user import User

COOKIE_NAME = "cp_session"


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise credentials_error
    try:
        payload = decode_token(token)
    except ValueError:
        raise credentials_error

    if payload.get("scope") != "full":
        raise credentials_error

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise credentials_error

    # JTI revocation check — only enforced when jti is present in the token
    jti: str | None = payload.get("jti")
    if jti:
        result = await db.execute(select(Device).where(Device.jti == jti))
        device = result.scalar_one_or_none()
        if device is None or device.revoked:
            raise credentials_error

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise credentials_error
    return user
