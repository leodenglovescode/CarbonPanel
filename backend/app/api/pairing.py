"""
QR pairing for native clients.

Flow: a signed-in browser calls /pairing/start and renders the returned QR.
The phone scans it, POSTs the embedded code to /pairing/claim, and gets a
long-lived bearer token back. The browser polls /pairing/status to confirm.

The QR deliberately carries a short-lived single-use *code* rather than a
token: a token baked into a QR is valid the moment it's generated and stays
valid for anyone who photographs the screen, whereas a code is worthless once
claimed or after a few minutes, and the claim exchange is what lets the server
record which device actually paired.
"""

import base64
import io
import json
import uuid
from datetime import datetime, timedelta, timezone

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import brute_force, pairing
from app.core.dependencies import get_current_user
from app.core.security import create_access_token
from app.database import get_db
from app.models.device import Device
from app.models.user import User
from app.services import network_endpoints

router = APIRouter(prefix="/pairing", tags=["pairing"])

_QR_PAYLOAD_VERSION = 1


class EndpointOut(BaseModel):
    url: str
    kind: str
    label: str


class StartRequest(BaseModel):
    # Which endpoints to embed. Omitted means "everything discovered" — the UI
    # sends an explicit subset once the user has ticked boxes.
    endpoints: list[str] | None = None


class StartResponse(BaseModel):
    code: str
    expires_in: int
    endpoints: list[EndpointOut]
    selected: list[str]
    qr_png_b64: str


class StatusResponse(BaseModel):
    status: str               # "pending" | "claimed" | "expired"
    device_name: str | None = None


class ClaimRequest(BaseModel):
    code: str = Field(min_length=4, max_length=32)
    device_name: str | None = Field(default=None, max_length=60)


class ClaimResponse(BaseModel):
    token: str
    username: str
    expires_at: datetime
    server_name: str


def _request_scheme(request: Request) -> str:
    # Behind nginx the socket is plain HTTP; the client-facing scheme only
    # survives in X-Forwarded-Proto. Getting this wrong bakes http:// URLs
    # into the QR for a TLS deployment, which then fails to connect.
    forwarded = request.headers.get("x-forwarded-proto")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.url.scheme


def _request_host(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-host")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.headers.get("host")


def _discover(request: Request) -> list[dict]:
    scheme = _request_scheme(request)
    host = _request_host(request)
    # The port is already part of the Host header when it's non-default, so
    # only fall back to the socket port for the interface-derived URLs.
    port = request.url.port
    if port in (80, 443):
        port = None
    return network_endpoints.discover(scheme, port, host)


def _make_qr_png_b64(payload: str) -> str:
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@router.post("/start", response_model=StartResponse)
async def start_pairing(
    body: StartRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    discovered = _discover(request)
    known = [e["url"] for e in discovered]

    if body.endpoints:
        # Allow operator-configured URLs that aren't in the discovered set,
        # but drop anything empty so a stray blank doesn't end up in the QR.
        selected = [u.strip().rstrip("/") for u in body.endpoints if u and u.strip()]
    else:
        selected = known

    if not selected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No reachable addresses found to put in the pairing code. "
                   "Add one manually under Paired Devices.",
        )

    code, expires_in = pairing.generate(user.id, user.username)

    payload = json.dumps(
        {
            "v": _QR_PAYLOAD_VERSION,
            "c": code,
            "e": selected,
            "n": network_endpoints.server_name(),
        },
        separators=(",", ":"),
    )

    return StartResponse(
        code=code,
        expires_in=expires_in,
        endpoints=[EndpointOut(**e) for e in discovered],
        selected=selected,
        qr_png_b64=_make_qr_png_b64(payload),
    )


class EndpointsResponse(BaseModel):
    discovered: list[EndpointOut]
    extra: list[str]


class EndpointsUpdate(BaseModel):
    extra: list[str]


@router.get("/endpoints", response_model=EndpointsResponse)
async def list_endpoints(request: Request, _: User = Depends(get_current_user)):
    """Addresses this panel believes it is reachable at.

    Autodiscovery only sees addresses bound to a local interface, so anything
    reached by name or through a forwarded port lives in `extra`.
    """
    return EndpointsResponse(
        discovered=[EndpointOut(**e) for e in _discover(request)],
        extra=network_endpoints.get_extra_endpoints(),
    )


@router.put("/endpoints", response_model=EndpointsResponse)
async def update_endpoints(
    body: EndpointsUpdate,
    request: Request,
    _: User = Depends(get_current_user),
):
    for url in body.extra:
        cleaned = url.strip()
        if cleaned and not cleaned.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Endpoint must start with http:// or https:// — got {cleaned!r}",
            )
    network_endpoints.set_extra_endpoints(body.extra)
    return EndpointsResponse(
        discovered=[EndpointOut(**e) for e in _discover(request)],
        extra=network_endpoints.get_extra_endpoints(),
    )


@router.get("/status/{code}", response_model=StatusResponse)
async def pairing_status(code: str, user: User = Depends(get_current_user)):
    state, device_name = pairing.peek(code, user.id)
    return StatusResponse(status=state, device_name=device_name)


@router.post("/claim", response_model=ClaimResponse)
async def claim_pairing(
    body: ClaimRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a pairing code for a long-lived device token.

    Unauthenticated by necessity — the phone has no credentials yet. Guarded
    by the same per-IP brute-force limiter as login, plus single-use codes
    with a few minutes' lifetime.
    """
    ip = request.client.host if request.client else None
    if brute_force.is_banned(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed pairing attempts.",
            headers={"Retry-After": str(brute_force.retry_after(ip))},
        )

    pending = pairing.claim(body.code.strip().upper())
    if pending is None:
        brute_force.record_failure(ip)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired pairing code",
        )
    brute_force.record_success(ip)

    result = await db.execute(select(User).where(User.id == pending.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired pairing code",
        )

    device_name = (body.device_name or "").strip() or "Android device"
    expires_minutes = settings.device_token_expire_days * 24 * 60
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)

    jti = str(uuid.uuid4())
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        jti=jti,
        expires_minutes=expires_minutes,
    )

    db.add(Device(
        user_id=user.id,
        jti=jti,
        name=device_name,
        kind="android",
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
        expires_at=expires_at.replace(tzinfo=None),
    ))
    await db.commit()

    pairing.mark_claimed(body.code.strip().upper(), device_name)

    return ClaimResponse(
        token=token,
        username=user.username,
        expires_at=expires_at,
        server_name=network_endpoints.server_name(),
    )
