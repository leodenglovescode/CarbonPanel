import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.config import settings


def hash_password(password: str) -> str:
    encoded = password.encode()
    if len(encoded) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        # bcrypt rejects inputs above 72 bytes; authentication should fail
        # normally rather than turning attacker-controlled input into a 500.
        return False


def create_access_token(
    user_id: str,
    username: str,
    scope: str = "full",
    expires_minutes: int | None = None,
    jti: str | None = None,
) -> str:
    if expires_minutes is None:
        expires_minutes = settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {
        "sub": user_id,
        "username": username,
        "scope": scope,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if scope == "full":
        payload["jti"] = jti or str(uuid.uuid4())
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except InvalidTokenError as exc:
        raise ValueError("Invalid token") from exc
