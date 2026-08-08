import time
from threading import Lock

from fastapi import Depends, HTTPException, Request, Response, WebSocket, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import decode_token
from app.database import get_db
from app.models.device import Device
from app.models.user import User

COOKIE_NAME = settings.cookie_name


def is_allowed_ws_origin(ws: WebSocket) -> bool:
    """Reject cross-site WebSocket handshakes (CSWSH).

    Unlike normal HTTP requests, the browser does not apply CORS to
    WebSocket handshakes and cookie SameSite enforcement on them is
    inconsistent across browsers — so with auth now living in a cookie,
    any other origin's page can do `new WebSocket(".../ws")` and have the
    browser attach it automatically unless the server checks Origin itself.
    """
    origin = ws.headers.get("origin")
    if not origin:
        return False
    if origin in settings.cors_origins:
        return True
    # Same-origin deployment (prod: frontend + backend behind one nginx
    # origin; dev: vite's proxy forwards the original Host untouched) —
    # Origin should match the Host the handshake actually arrived on.
    origin_host = origin.split("://", 1)[-1]
    host_header = ws.headers.get("host", "")
    if origin_host == host_header:
        return True
    # Some reverse proxies forward Host without the port even when the
    # client's Origin includes one (nginx's $host variable strips it, unlike
    # $http_host — an easy config mistake that silently rejected every
    # WebSocket on any deployment using a non-default port). Compare
    # hostnames alone as a fallback rather than failing closed on that; the
    # hostname still has to match exactly, so this doesn't weaken the
    # cross-origin check itself.
    origin_hostname = origin_host.rsplit(":", 1)[0]
    host_hostname = host_header.rsplit(":", 1)[0]
    return bool(origin_hostname) and origin_hostname == host_hostname


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


def _extract_token(request: Request) -> str | None:
    """Session cookie first, then `Authorization: Bearer`.

    Browsers keep using the httpOnly cookie exactly as before — the cookie is
    checked first so nothing about that path changes. The bearer fallback
    exists for paired native clients (Android), which have no cookie jar worth
    the name. Accepting bearer does not reopen CSRF: browsers never attach an
    Authorization header automatically, which is precisely why the cookie is
    the one that needs SameSite and the Origin checks on the WS handshake.
    """
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    scheme, _, param = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and param:
        return param.strip()
    return None


# --- Revocation-check cache -------------------------------------------------
#
# Native clients poll metrics as fast as every 0.4s, and the jti revocation
# lookup would otherwise be a DB round-trip on every one of those requests —
# costing more than collecting the metrics does. Cache the "this jti is not
# revoked" answer briefly; revoking a device invalidates it immediately via
# invalidate_jti(), so the only staleness window is for revocations performed
# out-of-band (direct DB edits), which resolve within the TTL.

_JTI_CACHE_TTL = 30.0  # seconds
_jti_cache: dict[str, float] = {}  # jti -> checked_at (monotonic)
_jti_cache_lock = Lock()


# Revoked jtis, so already-open WebSockets can be dropped mid-stream. A
# connect-time check alone would let an existing stream run until its token
# expired — up to 8 hours of live metrics and /var/log/auth.log for a session
# the operator believed they had just cut off.
_revoked_jtis: set[str] = set()


def invalidate_jti(jti: str | None) -> None:
    """Drop a cached revocation result — call when revoking a device."""
    if not jti:
        return
    with _jti_cache_lock:
        _jti_cache.pop(jti, None)
        _revoked_jtis.add(jti)


def is_jti_revoked(jti: str | None) -> bool:
    """Cheap in-memory check for long-lived streams to poll between frames."""
    if not jti:
        return False
    with _jti_cache_lock:
        return jti in _revoked_jtis


def _jti_recently_verified(jti: str) -> bool:
    now = time.monotonic()
    with _jti_cache_lock:
        checked_at = _jti_cache.get(jti)
        return checked_at is not None and now - checked_at < _JTI_CACHE_TTL


def _remember_jti(jti: str) -> None:
    now = time.monotonic()
    with _jti_cache_lock:
        # Opportunistic sweep — the keyspace is one entry per active session,
        # so this stays small without needing an LRU.
        for k in [k for k, t in _jti_cache.items() if now - t >= _JTI_CACHE_TTL]:
            del _jti_cache[k]
        _jti_cache[jti] = now


CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
)


async def _authenticate(request: Request, db: AsyncSession) -> str:
    """Validate the caller's token and return their user_id.

    Does no User lookup — callers that need the ORM object do that themselves.
    """
    token = _extract_token(request)
    if not token:
        raise CREDENTIALS_ERROR
    try:
        payload = decode_token(token)
    except ValueError:
        raise CREDENTIALS_ERROR

    if payload.get("scope") != "full":
        raise CREDENTIALS_ERROR

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise CREDENTIALS_ERROR

    # JTI revocation check — only enforced when jti is present in the token
    jti: str | None = payload.get("jti")
    if jti and not _jti_recently_verified(jti):
        result = await db.execute(select(Device).where(Device.jti == jti))
        device = result.scalar_one_or_none()
        if device is None or device.revoked:
            raise CREDENTIALS_ERROR
        _remember_jti(jti)

    return user_id


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = await _authenticate(request, db)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise CREDENTIALS_ERROR
    return user


async def authenticate_ws(ws: WebSocket) -> str | None:
    """Validate a WebSocket handshake's session cookie.

    Returns the token's jti (or "" when the token predates jti tracking), or
    None if the connection must be rejected.

    Exists because the three WebSocket endpoints each decoded the cookie by
    hand and checked only the signature and scope — never revocation. Clicking
    "Revoke" in Settings therefore cut off HTTP within the cache TTL while
    leaving live metrics and the system log stream open until the token
    expired. WebSockets need their own entry point because they carry no
    Request, so the HTTP dependency can't be reused directly.
    """
    token = ws.cookies.get(COOKIE_NAME, "")
    if not token:
        return None
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    if payload.get("scope") != "full":
        return None
    if not payload.get("sub"):
        return None

    jti: str | None = payload.get("jti")
    if not jti:
        # Pre-dates jti tracking; signature and scope are all there is to check.
        return ""
    if is_jti_revoked(jti):
        return None
    if not _jti_recently_verified(jti):
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Device).where(Device.jti == jti))
            device = result.scalar_one_or_none()
            if device is None or device.revoked:
                return None
        _remember_jti(jti)
    return jti


async def require_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> str:
    """Auth check for hot polling endpoints, returning only the user_id.

    Skips the User row fetch entirely. On a warm jti cache this costs zero DB
    queries, which is what makes 0.4s metrics polling affordable. Use it only
    where the endpoint genuinely doesn't need the User object — everything
    else should keep using get_current_user.
    """
    return await _authenticate(request, db)
