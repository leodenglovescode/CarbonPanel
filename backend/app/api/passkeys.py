import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import brute_force
from app.core.dependencies import get_current_user, set_auth_cookie
from app.core.security import create_access_token
from app.database import get_db
from app.models.user import User
from app.models.webauthn import WebAuthnCredential
from app.schemas.auth import StepUpRequest, SuccessResponse
from app.services import auth_service, passkey_service

router = APIRouter(prefix="/auth/passkey", tags=["passkeys"])


class PasskeyRegistrationBeginRequest(StepUpRequest):
    device_name: str = Field(default="Passkey", min_length=1, max_length=80)


class CredentialPayload(BaseModel):
    credential: dict

    @field_validator("credential")
    @classmethod
    def credential_has_reasonable_size(cls, value: dict) -> dict:
        if len(json.dumps(value, separators=(",", ":"))) > 64 * 1024:
            raise ValueError("Passkey response is too large")
        return value


class PasskeyCompleteRequest(CredentialPayload):
    challenge_id: str = Field(min_length=1, max_length=128)
    device_name: str = Field(default="Passkey", min_length=1, max_length=80)


class PasskeyLoginCompleteRequest(CredentialPayload):
    challenge_id: str = Field(min_length=1, max_length=128)


class PasskeyDeleteRequest(StepUpRequest):
    pass


class PasskeyOut(BaseModel):
    id: str
    device_name: str
    rp_id: str
    backed_up: bool
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _management_key(user: User) -> str:
    return f"passkey-manage:{user.username}"


def _check_banned(request: Request, key: str | None = None) -> None:
    # Username-less login failures are per IP. A shared pseudo-username would
    # let one client lock every user out of passkey authentication.
    ip = _ip(request)
    if brute_force.is_banned(ip, key):
        seconds = brute_force.retry_after(ip, key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Try again in {seconds} seconds.",
            headers={"Retry-After": str(seconds)},
        )


@router.post("/register/begin")
async def register_begin(
    body: PasskeyRegistrationBeginRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key = _management_key(user)
    _check_banned(request, key)
    try:
        auth_service.verify_step_up(user, body.current_password, body.current_totp_code)
        result = await passkey_service.registration_options(request, user, db)
        brute_force.record_success(_ip(request), key)
        return result
    except ValueError as exc:
        brute_force.record_failure(_ip(request), key)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/register/complete", response_model=PasskeyOut)
async def register_complete(
    body: PasskeyCompleteRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await passkey_service.complete_registration(
            request,
            user,
            body.challenge_id,
            body.credential,
            body.device_name,
            db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/credentials", response_model=list[PasskeyOut])
async def list_credentials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebAuthnCredential)
        .where(WebAuthnCredential.user_id == user.id)
        .order_by(WebAuthnCredential.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/credentials/{credential_id}", response_model=SuccessResponse)
async def delete_credential(
    credential_id: str,
    body: PasskeyDeleteRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key = _management_key(user)
    _check_banned(request, key)
    try:
        auth_service.verify_step_up(user, body.current_password, body.current_totp_code)
    except ValueError as exc:
        brute_force.record_failure(_ip(request), key)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.id == credential_id,
            WebAuthnCredential.user_id == user.id,
        )
    )
    credential = result.scalar_one_or_none()
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passkey not found")
    await db.delete(credential)
    await db.commit()
    brute_force.record_success(_ip(request), key)
    return SuccessResponse()


@router.post("/login/begin")
async def login_begin(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _check_banned(request)
    try:
        return await passkey_service.authentication_options(request, db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/login/complete", response_model=SuccessResponse)
async def login_complete(
    body: PasskeyLoginCompleteRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    _check_banned(request)
    try:
        user, _ = await passkey_service.complete_authentication(
            request,
            body.challenge_id,
            body.credential,
            db,
        )
        jti = str(uuid.uuid4())
        await auth_service._record_device(
            user.id,
            jti,
            _ip(request),
            request.headers.get("user-agent"),
            db,
            name_prefix="Passkey –",
            device_id=request.headers.get("x-device-id"),
        )
        await db.commit()
        token = create_access_token(user_id=user.id, username=user.username, jti=jti)
        set_auth_cookie(response, token)
        brute_force.record_success(_ip(request))
        return SuccessResponse()
    except ValueError as exc:
        brute_force.record_failure(_ip(request))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
