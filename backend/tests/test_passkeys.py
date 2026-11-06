import hashlib
import json
from contextlib import asynccontextmanager

import cbor2
import httpx
import pyotp
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from webauthn.helpers import bytes_to_base64url

from app.api import auth, passkeys
from app.core import brute_force
from app.core.security import hash_password
from app.database import get_db
from app.models.device import Device


from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.requests import Request

from app.models.user import User
from app.models.webauthn import WebAuthnChallenge, WebAuthnCredential
from app.services.passkey_service import (
    WebAuthnContext,
    _consume_challenge,
    _store_challenge,
    authentication_options,
    registration_options,
    webauthn_context,
)


def _request(origin: str, host: str, scheme: str = "https") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": scheme,
            "path": "/api/v1/auth/passkey/login/begin",
            "headers": [
                (b"host", host.encode()),
                (b"origin", origin.encode()),
            ],
            "server": (host.partition(":")[0], 443 if scheme == "https" else 80),
            "client": ("127.0.0.1", 1234),
        }
    )


def test_passkeys_require_https_domain_or_localhost() -> None:
    context = webauthn_context(_request("https://panel.example:8443", "panel.example:8443"))
    assert context == WebAuthnContext(
        rp_id="panel.example",
        origin="https://panel.example:8443",
    )

    localhost = webauthn_context(_request("http://localhost:5174", "localhost:5174", scheme="http"))
    assert localhost.rp_id == "localhost"

    with pytest.raises(ValueError, match="IP addresses"):
        webauthn_context(_request("https://192.168.1.2", "192.168.1.2"))
    with pytest.raises(ValueError, match="trusted HTTPS"):
        webauthn_context(_request("http://panel.example", "panel.example", scheme="http"))
    with pytest.raises(ValueError, match="same-origin"):
        webauthn_context(_request("https://evil.example", "panel.example"))


@pytest.mark.asyncio
async def test_challenges_are_single_use() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(User.__table__.create)
        await connection.run_sync(WebAuthnChallenge.__table__.create)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        challenge_id = await _store_challenge(
            db,
            ceremony="authentication",
            challenge=b"test-challenge",
            context=WebAuthnContext("panel.example", "https://panel.example"),
            user_id=None,
        )
        consumed = await _consume_challenge(
            db,
            challenge_id=challenge_id,
            ceremony="authentication",
        )
        assert consumed.challenge == b"test-challenge"
        with pytest.raises(ValueError, match="already used"):
            await _consume_challenge(
                db,
                challenge_id=challenge_id,
                ceremony="authentication",
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_expired_challenge_is_rejected_and_consumed() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(User.__table__.create)
        await connection.run_sync(WebAuthnChallenge.__table__.create)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        challenge = WebAuthnChallenge(
            ceremony="authentication",
            challenge=b"expired",
            rp_id="panel.example",
            origin="https://panel.example",
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1),
        )
        db.add(challenge)
        await db.commit()
        with pytest.raises(ValueError, match="expired"):
            await _consume_challenge(
                db,
                challenge_id=challenge.id,
                ceremony="authentication",
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_options_require_discoverable_user_verified_credentials() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(User.__table__.create)
        await connection.run_sync(WebAuthnCredential.__table__.create)
        await connection.run_sync(WebAuthnChallenge.__table__.create)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        user = User(id="user-id", username="admin", password_hash="unused")
        db.add(user)
        await db.commit()
        request = _request("https://panel.example", "panel.example")

        registration = await registration_options(request, user, db)
        selection = registration["public_key"]["authenticatorSelection"]
        assert selection["residentKey"] == "required"
        assert selection["requireResidentKey"] is True
        assert selection["userVerification"] == "required"

        authentication = await authentication_options(request, db)
        assert authentication["public_key"]["userVerification"] == "required"
        assert not authentication["public_key"].get("allowCredentials")

    await engine.dispose()


# Exercise the real WebAuthn verifier with an ephemeral software authenticator.
# No cryptographic verification is mocked in these HTTP-level tests.


class SoftwareAuthenticator:
    def __init__(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = b"ephemeral-test-credential"

    def response(
        self,
        options,
        *,
        registration=False,
        origin="https://panel.example",
        user_handle=b"user-id",
        verified=True,
        tamper=False,
    ):
        client_data = json.dumps(
            {
                "type": "webauthn.create" if registration else "webauthn.get",
                "challenge": options["public_key"]["challenge"],
                "origin": origin,
                "crossOrigin": False,
            }
        ).encode()
        flags = 1 | (4 if verified else 0) | (64 if registration else 0)
        authenticator_data = hashlib.sha256(b"panel.example").digest()
        authenticator_data += bytes([flags]) + (0 if registration else 1).to_bytes(4, "big")
        if registration:
            numbers = self.key.public_key().public_numbers()
            cose = cbor2.dumps(
                {
                    1: 2,
                    3: -7,
                    -1: 1,
                    -2: numbers.x.to_bytes(32, "big"),
                    -3: numbers.y.to_bytes(32, "big"),
                }
            )
            authenticator_data += bytes(16) + len(self.credential_id).to_bytes(2, "big")
            authenticator_data += self.credential_id + cose
            response = {
                "attestationObject": bytes_to_base64url(
                    cbor2.dumps(
                        {
                            "fmt": "none",
                            "attStmt": {},
                            "authData": authenticator_data,
                        }
                    )
                )
            }
        else:
            signature = self.key.sign(
                authenticator_data + hashlib.sha256(client_data).digest(),
                ec.ECDSA(hashes.SHA256()),
            )
            if tamper:
                signature = bytes([signature[0] ^ 1]) + signature[1:]
            response = {
                "authenticatorData": bytes_to_base64url(authenticator_data),
                "signature": bytes_to_base64url(signature),
                "userHandle": bytes_to_base64url(user_handle),
            }
        response["clientDataJSON"] = bytes_to_base64url(client_data)
        encoded_id = bytes_to_base64url(self.credential_id)
        return {"id": encoded_id, "rawId": encoded_id, "type": "public-key", "response": response}


@asynccontextmanager
async def passkey_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        for model in (User, Device, WebAuthnCredential, WebAuthnChallenge):
            await connection.run_sync(model.__table__.create)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    secret = pyotp.random_base32()
    async with factory() as db:
        db.add(
            User(
                id="user-id",
                username="passkey-test",
                password_hash=hash_password("test-password"),
                totp_enabled=True,
                totp_secret=secret,
            )
        )
        await db.commit()

    async def database():
        async with factory() as session:
            yield session

    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(passkeys.router)
    app.dependency_overrides[get_db] = database
    brute_force.record_success("127.0.0.1", "passkey-manage:passkey-test")
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://panel.example",
            headers={"Origin": "https://panel.example"},
        ) as client:
            yield client, secret
    finally:
        brute_force.record_success("127.0.0.1", "passkey-manage:passkey-test")
        await engine.dispose()


async def enroll(client, secret):
    result = await client.post(
        "/auth/login",
        json={
            "username": "passkey-test",
            "password": "test-password",
        },
    )
    result = await client.post(
        "/auth/login/totp",
        json={
            "session_token": result.json()["session_token"],
            "totp_code": pyotp.TOTP(secret).now(),
        },
    )
    assert result.status_code == 200, result.text
    denied = await client.post(
        "/auth/passkey/register/begin",
        json={
            "current_password": "test-password",
            "device_name": "Test authenticator",
        },
    )
    assert denied.status_code == 403  # Enrollment cannot bypass existing TOTP.
    result = await client.post(
        "/auth/passkey/register/begin",
        json={
            "current_password": "test-password",
            "current_totp_code": pyotp.TOTP(secret).now(),
            "device_name": "Test authenticator",
        },
    )
    assert result.status_code == 200, result.text
    options = result.json()
    authenticator = SoftwareAuthenticator()
    payload = {
        "challenge_id": options["challenge_id"],
        "device_name": "Test authenticator",
        "credential": authenticator.response(options, registration=True),
    }
    result = await client.post("/auth/passkey/register/complete", json=payload)
    assert result.status_code == 200, result.text
    replay = await client.post("/auth/passkey/register/complete", json=payload)
    assert replay.status_code == 400
    return authenticator, result.json()["id"]


@pytest.mark.asyncio
async def test_passkey_enrollment_login_replay_and_removal():
    async with passkey_client() as (client, secret):
        denied = await client.post(
            "/auth/passkey/register/begin",
            json={
                "current_password": "test-password",
            },
        )
        assert denied.status_code == 401
        authenticator, credential_id = await enroll(client, secret)
        listed = await client.get("/auth/passkey/credentials")
        assert listed.json()[0]["device_name"] == "Test authenticator"
        client.cookies.clear()
        options = (await client.post("/auth/passkey/login/begin")).json()
        payload = {
            "challenge_id": options["challenge_id"],
            "credential": authenticator.response(options),
        }
        result = await client.post("/auth/passkey/login/complete", json=payload)
        assert result.status_code == 200, result.text
        assert "httponly" in result.headers["set-cookie"].lower()
        assert (await client.get("/auth/me")).json()["id"] == "user-id"
        assert (await client.post("/auth/passkey/login/complete", json=payload)).status_code == 401
        denied = await client.request(
            "DELETE",
            f"/auth/passkey/credentials/{credential_id}",
            json={"current_password": "wrong"},
        )
        assert denied.status_code == 403
        removed = await client.request(
            "DELETE",
            f"/auth/passkey/credentials/{credential_id}",
            json={
                "current_password": "test-password",
                "current_totp_code": pyotp.TOTP(secret).now(),
            },
        )
        assert removed.status_code == 200
        client.cookies.clear()
        options = (await client.post("/auth/passkey/login/begin")).json()
        result = await client.post(
            "/auth/passkey/login/complete",
            json={
                "challenge_id": options["challenge_id"],
                "credential": authenticator.response(options),
            },
        )
        assert result.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "alteration",
    [
        {"verified": False},
        {"tamper": True},
        {"origin": "https://evil.example"},
        {"user_handle": b"another-user"},
    ],
)
async def test_passkey_rejects_invalid_signed_responses(alteration):
    async with passkey_client() as (client, secret):
        authenticator, _ = await enroll(client, secret)
        client.cookies.clear()
        options = (await client.post("/auth/passkey/login/begin")).json()
        result = await client.post(
            "/auth/passkey/login/complete",
            json={
                "challenge_id": options["challenge_id"],
                "credential": authenticator.response(options, **alteration),
            },
        )
        assert result.status_code == 401
        assert "set-cookie" not in result.headers
        assert (await client.get("/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_failed_logins_do_not_ban_every_passkey_user(monkeypatch):
    from unittest.mock import AsyncMock
    from fastapi import HTTPException, Response
    from app.services import passkey_service

    monkeypatch.setattr(
        passkey_service,
        "complete_authentication",
        AsyncMock(side_effect=ValueError("Invalid passkey")),
    )
    attacker_ip = "198.51.100.12"
    request = _request("https://panel.example", "panel.example")
    request.scope["client"] = (attacker_ip, 1234)
    body = passkeys.PasskeyLoginCompleteRequest(challenge_id="missing", credential={})
    try:
        for _ in range(brute_force.MAX_ATTEMPTS):
            with pytest.raises(HTTPException) as error:
                await passkeys.login_complete(body, request, Response(), None)
            assert error.value.status_code == 401
        with pytest.raises(HTTPException) as error:
            passkeys._check_banned(request)
        assert error.value.status_code == 429
        request.scope["client"] = ("198.51.100.13", 1234)
        passkeys._check_banned(request)
    finally:
        brute_force.record_success(attacker_ip)
