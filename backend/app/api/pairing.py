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
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

import qrcode
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import brute_force, pairing
from app.core.dependencies import get_current_user
from app.core.security import create_access_token
from app.services.auth_service import verify_step_up
from app.database import get_db
from app.models.device import Device
from app.models.user import User
from app.services import network_endpoints

router = APIRouter(prefix="/pairing", tags=["pairing"])

_QR_PAYLOAD_VERSION = 2
EndpointUrl = Annotated[str, Field(max_length=2048)]


class EndpointOut(BaseModel):
    url: str
    kind: str
    label: str


class StartRequest(BaseModel):
    # Which endpoints to embed. Omitted means "everything discovered" — the UI
    # sends an explicit subset once the user has ticked boxes.
    endpoints: list[EndpointUrl] | None = Field(default=None, max_length=20)
    current_password: str = Field(min_length=1, max_length=1024)
    current_totp_code: str | None = Field(default=None, pattern=r"^\d{6}$")


class StartResponse(BaseModel):
    code: str
    expires_in: int
    endpoints: list[EndpointOut]
    selected: list[str]
    certificate_fingerprint: str | None
    qr_png_b64: str


class StatusResponse(BaseModel):
    status: str               # "pending" | "claimed" | "expired"
    device_name: str | None = None


class ClaimRequest(BaseModel):
    code: str = Field(pattern=r"^[23456789ABCDEFGHJKMNPQRSTVWXYZ]{12}$")
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


def _is_https_endpoint(url: str) -> bool:
    if any(ord(char) < 33 for char in url):
        return False
    parsed = urlsplit(url)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and "@" not in parsed.netloc
        and not parsed.query
        and not parsed.fragment
    )


def _certificate_binding() -> tuple[str | None, set[str]]:
    if not settings.tls_cert_file:
        return None, set()
    try:
        cert = x509.load_pem_x509_certificate(Path(settings.tls_cert_file).read_bytes())
        digest = cert.fingerprint(hashes.SHA256()).hex().upper()
        fingerprint = ":".join(digest[i:i + 2] for i in range(0, len(digest), 2))
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        names = {name.lower() for name in san.get_values_for_type(x509.DNSName)}
        names.update(str(ip).lower() for ip in san.get_values_for_type(x509.IPAddress))
        return fingerprint, names
    except (OSError, ValueError, x509.ExtensionNotFound):
        return None, set()


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
    ip = request.client.host if request.client else None
    brute_key = f"pairing-step-up:{user.username}"
    if brute_force.is_banned(ip, brute_key):
        secs = brute_force.retry_after(ip, brute_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Try again in {secs} seconds.",
            headers={"Retry-After": str(secs)},
        )
    try:
        verify_step_up(user, body.current_password, body.current_totp_code)
        brute_force.record_success(ip, brute_key)
    except ValueError as exc:
        brute_force.record_failure(ip, brute_key)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    discovered = [e for e in _discover(request) if _is_https_endpoint(e["url"])]
    known = [e["url"] for e in discovered]

    if body.endpoints:
        # Allow operator-configured URLs that aren't in the discovered set,
        # but drop anything empty so a stray blank doesn't end up in the QR.
        selected = [
            u.strip().rstrip("/")
            for u in body.endpoints
            if u and u.strip() and _is_https_endpoint(u.strip())
        ]
    else:
        selected = known

    if not selected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No secure HTTPS addresses found for pairing. "
                   "Configure TLS and add an HTTPS endpoint under Paired Devices.",
        )

    code, expires_in = pairing.generate(user.id, user.username)
    fingerprint, certificate_names = _certificate_binding()
    pinned_hosts = sorted({
        host
        for url in selected
        if (host := urlsplit(url).hostname)
        and host.lower() in certificate_names
    })

    payload = json.dumps(
        {
            "v": _QR_PAYLOAD_VERSION,
            "c": code,
            "e": selected,
            "n": network_endpoints.server_name(),
            "f": fingerprint,
            "p": pinned_hosts,
        },
        separators=(",", ":"),
    )

    return StartResponse(
        code=code,
        expires_in=expires_in,
        endpoints=[EndpointOut(**e) for e in discovered],
        selected=selected,
        certificate_fingerprint=fingerprint,
        qr_png_b64=_make_qr_png_b64(payload),
    )


class EndpointsResponse(BaseModel):
    discovered: list[EndpointOut]
    extra: list[str]


class EndpointsUpdate(BaseModel):
    extra: list[EndpointUrl] = Field(max_length=20)


@router.get("/endpoints", response_model=EndpointsResponse)
async def list_endpoints(request: Request, _: User = Depends(get_current_user)):
    """Addresses this panel believes it is reachable at.

    Autodiscovery only sees addresses bound to a local interface, so anything
    reached by name or through a forwarded port lives in `extra`.
    """
    return EndpointsResponse(
        discovered=[
            EndpointOut(**e) for e in _discover(request) if _is_https_endpoint(e["url"])
        ],
        extra=[u for u in network_endpoints.get_extra_endpoints() if _is_https_endpoint(u)],
    )


@router.put("/endpoints", response_model=EndpointsResponse)
async def update_endpoints(
    body: EndpointsUpdate,
    request: Request,
    _: User = Depends(get_current_user),
):
    for url in body.extra:
        cleaned = url.strip()
        if cleaned and not _is_https_endpoint(cleaned):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Endpoint must be a valid HTTPS URL — got {cleaned!r}",
            )
    network_endpoints.set_extra_endpoints(body.extra)
    return EndpointsResponse(
        discovered=[
            EndpointOut(**e) for e in _discover(request) if _is_https_endpoint(e["url"])
        ],
        extra=[u for u in network_endpoints.get_extra_endpoints() if _is_https_endpoint(u)],
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
