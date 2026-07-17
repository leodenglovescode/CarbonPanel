import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webauthn import (
    base64url_to_bytes,
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.structs import (
    AuthenticatorAssertionResponse,
    AuthenticatorAttestationResponse,
    AuthenticatorSelectionCriteria,
    AuthenticationCredential,
    PublicKeyCredentialDescriptor,
    RegistrationCredential,
    UserVerificationRequirement,
)

from app.core.dependencies import get_current_user
from app.core.security import create_access_token
from app.database import get_db
from app.models.user import User
from app.models.webauthn_credential import WebAuthnCredential
from app.services.auth_service import _record_device

router = APIRouter(prefix="/auth/passkey", tags=["passkeys"])

# In-memory challenge store: keyed by "reg:<user_id>" or "auth:<session_id>"
_challenges: dict[str, object] = {}


def _rp_id(request: Request) -> str:
    origin = request.headers.get("origin", "")
    if "://" in origin:
        origin = origin.split("://", 1)[1]
    if ":" in origin:
        origin = origin.split(":")[0]
    return origin or "localhost"


def _origin(request: Request) -> str:
    return request.headers.get("origin", "http://localhost:5173")


# ── Registration ──────────────────────────────────────────────────────────────

@router.post("/register/begin")
async def passkey_register_begin(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebAuthnCredential).where(WebAuthnCredential.user_id == user.id)
    )
    existing = result.scalars().all()

    options = generate_registration_options(
        rp_id=_rp_id(request),
        rp_name="CarbonPanel",
        user_id=user.id.encode(),
        user_name=user.username,
        user_display_name=user.username,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        supported_pub_key_algs=[
            COSEAlgorithmIdentifier.ECDSA_SHA_256,
            COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
        ],
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=cred.credential_id) for cred in existing
        ],
    )
    _challenges[f"reg:{user.id}"] = options.challenge
    return json.loads(options_to_json(options))


class PasskeyRegisterCompleteRequest(BaseModel):
    credential: dict
    device_name: str = ""


@router.post("/register/complete")
async def passkey_register_complete(
    body: PasskeyRegisterCompleteRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    challenge = _challenges.pop(f"reg:{user.id}", None)
    if challenge is None:
        raise HTTPException(status_code=400, detail="No pending registration challenge")

    raw = body.credential
    try:
        cred_obj = RegistrationCredential(
            id=raw["id"],
            raw_id=base64url_to_bytes(raw["rawId"]),
            response=AuthenticatorAttestationResponse(
                client_data_json=base64url_to_bytes(raw["response"]["clientDataJSON"]),
                attestation_object=base64url_to_bytes(raw["response"]["attestationObject"]),
            ),
        )
        verified = verify_registration_response(
            credential=cred_obj,
            expected_challenge=challenge,  # type: ignore[arg-type]
            expected_rp_id=_rp_id(request),
            expected_origin=_origin(request),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Registration failed: {exc}")

    cred = WebAuthnCredential(
        user_id=user.id,
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        device_name=body.device_name or "Passkey",
    )
    db.add(cred)
    await db.commit()
    return {"success": True}


# ── Passkey management ────────────────────────────────────────────────────────

class PasskeyOut(BaseModel):
    id: str
    device_name: str

    model_config = {"from_attributes": True}


@router.get("/credentials", response_model=list[PasskeyOut])
async def list_passkeys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebAuthnCredential).where(WebAuthnCredential.user_id == user.id)
    )
    return result.scalars().all()


@router.delete("/credentials/{cred_id}")
async def delete_passkey(
    cred_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.id == cred_id,
            WebAuthnCredential.user_id == user.id,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    await db.delete(cred)
    await db.commit()
    return {"success": True}


# ── Authentication ────────────────────────────────────────────────────────────

class PasskeyLoginBeginRequest(BaseModel):
    username: str


@router.post("/login/begin")
async def passkey_login_begin(
    body: PasskeyLoginBeginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(WebAuthnCredential).where(WebAuthnCredential.user_id == user.id)
    )
    credentials = result.scalars().all()
    if not credentials:
        raise HTTPException(status_code=400, detail="No passkeys registered for this user")

    options = generate_authentication_options(
        rp_id=_rp_id(request),
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=cred.credential_id) for cred in credentials
        ],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    session_id = str(uuid.uuid4())
    _challenges[f"auth:{session_id}"] = {
        "challenge": options.challenge,
        "user_id": user.id,
    }
    return {**json.loads(options_to_json(options)), "session_id": session_id}


class PasskeyLoginCompleteRequest(BaseModel):
    session_id: str
    credential: dict


@router.post("/login/complete")
async def passkey_login_complete(
    body: PasskeyLoginCompleteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    stored = _challenges.pop(f"auth:{body.session_id}", None)
    if not stored:
        raise HTTPException(status_code=400, detail="No pending login challenge")

    challenge = stored["challenge"]  # type: ignore[index]
    user_id: str = stored["user_id"]  # type: ignore[index]

    raw = body.credential
    cred_id_bytes = base64url_to_bytes(raw["id"])

    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.credential_id == cred_id_bytes,
            WebAuthnCredential.user_id == user_id,
        )
    )
    cred_record = result.scalar_one_or_none()
    if not cred_record:
        raise HTTPException(status_code=400, detail="Credential not found")

    uh_raw = raw["response"].get("userHandle")
    user_handle = base64url_to_bytes(uh_raw) if uh_raw else None

    try:
        cred_obj = AuthenticationCredential(
            id=raw["id"],
            raw_id=base64url_to_bytes(raw["rawId"]),
            response=AuthenticatorAssertionResponse(
                client_data_json=base64url_to_bytes(raw["response"]["clientDataJSON"]),
                authenticator_data=base64url_to_bytes(raw["response"]["authenticatorData"]),
                signature=base64url_to_bytes(raw["response"]["signature"]),
                user_handle=user_handle,
            ),
        )
        verified = verify_authentication_response(
            credential=cred_obj,
            expected_challenge=challenge,  # type: ignore[arg-type]
            expected_rp_id=_rp_id(request),
            expected_origin=_origin(request),
            credential_public_key=cred_record.public_key,
            credential_current_sign_count=cred_record.sign_count,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {exc}")

    cred_record.sign_count = verified.new_sign_count
    db.add(cred_record)

    jti = str(uuid.uuid4())
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    device_id = request.headers.get("x-device-id")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await _record_device(
        user_id, jti, ip, ua, db, name_prefix="Passkey –", device_id=device_id
    )
    await db.commit()

    token = create_access_token(user_id=user_id, username=user.username, jti=jti)
    return {"access_token": token, "token_type": "bearer"}
