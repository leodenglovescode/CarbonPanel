import ipaddress
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn import (
    base64url_to_bytes,
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.core.dependencies import is_allowed_http_origin
from app.models.user import User
from app.models.webauthn import WebAuthnChallenge, WebAuthnCredential

CHALLENGE_TTL = timedelta(minutes=5)


def _utcnow() -> datetime:
    # SQLite returns naive datetimes; store an explicitly-derived naive UTC
    # value so comparisons remain portable without datetime.utcnow().
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class WebAuthnContext:
    rp_id: str
    origin: str


@dataclass(frozen=True)
class ConsumedChallenge:
    challenge: bytes
    user_id: str | None
    rp_id: str
    origin: str
    expires_at: datetime


def webauthn_context(request: Request) -> WebAuthnContext:
    """Return a WebAuthn RP context only for a trusted same-site-style origin.

    Browsers decide whether the certificate chain is trusted before exposing
    WebAuthn. The server independently enforces HTTPS, a domain RP ID, and the
    same origin policy; bare IP addresses are not valid WebAuthn RP IDs.
    """
    origin = request.headers.get("origin", "")
    if not origin or not is_allowed_http_origin(request):
        raise ValueError("Passkeys require a trusted same-origin request")

    try:
        parsed = urlsplit(origin)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Passkeys require a valid HTTPS hostname") from exc

    if (
        not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("Passkeys require a valid HTTPS hostname")

    hostname = hostname.rstrip(".").encode("idna").decode("ascii").lower()
    is_localhost = hostname == "localhost" or hostname.endswith(".localhost")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and is_localhost):
        raise ValueError("Passkeys require trusted HTTPS (localhost is allowed for development)")

    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ValueError("Passkeys require a domain hostname; IP addresses are not supported")

    default_port = (parsed.scheme == "https" and port in {None, 443}) or (
        parsed.scheme == "http" and port in {None, 80}
    )
    port_suffix = "" if default_port else f":{port}"
    canonical_origin = f"{parsed.scheme}://{hostname}{port_suffix}"
    if origin.rstrip("/").lower() != canonical_origin:
        raise ValueError("Passkeys require a canonical HTTPS origin")

    return WebAuthnContext(rp_id=hostname, origin=canonical_origin)


async def _store_challenge(
    db: AsyncSession,
    *,
    ceremony: str,
    challenge: bytes,
    context: WebAuthnContext,
    user_id: str | None,
) -> str:
    now = _utcnow()
    await db.execute(delete(WebAuthnChallenge).where(WebAuthnChallenge.expires_at <= now))
    if ceremony == "registration" and user_id:
        # Starting over invalidates an older unfinished enrollment for the
        # same account instead of accumulating parallel step-up ceremonies.
        await db.execute(
            delete(WebAuthnChallenge).where(
                WebAuthnChallenge.ceremony == ceremony,
                WebAuthnChallenge.user_id == user_id,
            )
        )
    elif ceremony == "authentication":
        # The begin endpoint is intentionally unauthenticated. Bound pending
        # state so request floods cannot grow the SQLite database indefinitely.
        older_ids = (
            select(WebAuthnChallenge.id)
            .where(
                WebAuthnChallenge.ceremony == ceremony,
                WebAuthnChallenge.origin == context.origin,
            )
            .order_by(WebAuthnChallenge.created_at.desc())
            .offset(127)
        )
        await db.execute(delete(WebAuthnChallenge).where(WebAuthnChallenge.id.in_(older_ids)))
    record = WebAuthnChallenge(
        user_id=user_id,
        ceremony=ceremony,
        challenge=challenge,
        rp_id=context.rp_id,
        origin=context.origin,
        expires_at=now + CHALLENGE_TTL,
    )
    db.add(record)
    await db.commit()
    return record.id


async def _consume_challenge(
    db: AsyncSession,
    *,
    challenge_id: str,
    ceremony: str,
    user_id: str | None = None,
) -> ConsumedChallenge:
    conditions = [
        WebAuthnChallenge.id == challenge_id,
        WebAuthnChallenge.ceremony == ceremony,
    ]
    if user_id is not None:
        conditions.append(WebAuthnChallenge.user_id == user_id)

    result = await db.execute(
        delete(WebAuthnChallenge)
        .where(*conditions)
        .returning(
            WebAuthnChallenge.challenge,
            WebAuthnChallenge.user_id,
            WebAuthnChallenge.rp_id,
            WebAuthnChallenge.origin,
            WebAuthnChallenge.expires_at,
        )
    )
    row = result.one_or_none()
    # Commit the deletion before verification so a malformed or replayed
    # response cannot resurrect the challenge through a later rollback.
    await db.commit()
    if row is None:
        raise ValueError("Passkey challenge is missing, expired, or already used")

    consumed = ConsumedChallenge(
        challenge=row.challenge,
        user_id=row.user_id,
        rp_id=row.rp_id,
        origin=row.origin,
        expires_at=row.expires_at,
    )
    if consumed.expires_at <= _utcnow():
        raise ValueError("Passkey challenge is missing, expired, or already used")
    return consumed


def _check_context(context: WebAuthnContext, challenge: ConsumedChallenge) -> None:
    if context.rp_id != challenge.rp_id or context.origin != challenge.origin:
        raise ValueError("Passkey ceremony must finish on the origin where it started")


async def registration_options(
    request: Request,
    user: User,
    db: AsyncSession,
) -> dict:
    context = webauthn_context(request)
    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.user_id == user.id,
            WebAuthnCredential.rp_id == context.rp_id,
        )
    )
    existing = result.scalars().all()
    options = generate_registration_options(
        rp_id=context.rp_id,
        rp_name="CarbonPanel",
        user_id=user.id.encode(),
        user_name=user.username,
        user_display_name=user.username,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            require_resident_key=True,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=credential.credential_id)
            for credential in existing
        ],
        timeout=60_000,
    )
    challenge_id = await _store_challenge(
        db,
        ceremony="registration",
        challenge=options.challenge,
        context=context,
        user_id=user.id,
    )
    return {
        "challenge_id": challenge_id,
        "public_key": json.loads(options_to_json(options)),
    }


async def complete_registration(
    request: Request,
    user: User,
    challenge_id: str,
    credential: dict,
    device_name: str,
    db: AsyncSession,
) -> WebAuthnCredential:
    context = webauthn_context(request)
    challenge = await _consume_challenge(
        db,
        challenge_id=challenge_id,
        ceremony="registration",
        user_id=user.id,
    )
    _check_context(context, challenge)
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=challenge.challenge,
            expected_rp_id=challenge.rp_id,
            expected_origin=challenge.origin,
            require_user_verification=True,
        )
    except Exception as exc:
        raise ValueError("Passkey registration could not be verified") from exc

    result = await db.execute(
        select(WebAuthnCredential.id).where(
            WebAuthnCredential.credential_id == verified.credential_id
        )
    )
    if result.scalar_one_or_none() is not None:
        raise ValueError("This passkey is already registered")

    record = WebAuthnCredential(
        user_id=user.id,
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        rp_id=challenge.rp_id,
        device_name=device_name.strip() or "Passkey",
        backed_up=verified.credential_backed_up,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def authentication_options(request: Request, db: AsyncSession) -> dict:
    context = webauthn_context(request)
    options = generate_authentication_options(
        rp_id=context.rp_id,
        user_verification=UserVerificationRequirement.REQUIRED,
        timeout=60_000,
    )
    challenge_id = await _store_challenge(
        db,
        ceremony="authentication",
        challenge=options.challenge,
        context=context,
        user_id=None,
    )
    return {
        "challenge_id": challenge_id,
        "public_key": json.loads(options_to_json(options)),
    }


async def complete_authentication(
    request: Request,
    challenge_id: str,
    credential: dict,
    db: AsyncSession,
) -> tuple[User, WebAuthnCredential]:
    context = webauthn_context(request)
    challenge = await _consume_challenge(
        db,
        challenge_id=challenge_id,
        ceremony="authentication",
    )
    _check_context(context, challenge)

    raw_id = credential.get("rawId") or credential.get("id")
    if not isinstance(raw_id, str):
        raise ValueError("Passkey response is malformed")
    try:
        credential_id = base64url_to_bytes(raw_id)
    except Exception as exc:
        raise ValueError("Passkey response is malformed") from exc

    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.credential_id == credential_id,
            WebAuthnCredential.rp_id == challenge.rp_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise ValueError("Passkey authentication failed")

    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=challenge.challenge,
            expected_rp_id=challenge.rp_id,
            expected_origin=challenge.origin,
            credential_public_key=record.public_key,
            credential_current_sign_count=record.sign_count,
            require_user_verification=True,
        )
    except Exception as exc:
        raise ValueError("Passkey authentication failed") from exc

    result = await db.execute(select(User).where(User.id == record.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("Passkey authentication failed")

    user_handle = credential.get("response", {}).get("userHandle")
    if user_handle:
        try:
            if base64url_to_bytes(user_handle) != user.id.encode():
                raise ValueError("Passkey authentication failed")
        except Exception as exc:
            raise ValueError("Passkey authentication failed") from exc

    record.sign_count = verified.new_sign_count
    record.backed_up = verified.credential_backed_up
    record.last_used_at = _utcnow()
    db.add(record)
    return user, record
