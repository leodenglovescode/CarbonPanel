import pyotp
import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.api.bookmarks import BookmarkIn
from app.config import Settings
from app.api.pairing import _is_https_endpoint
from app.core.dependencies import is_allowed_http_origin
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.main import RequestBodyLimitMiddleware
from app.models.user import User
from app.services.auth_service import verify_step_up


def _request(origin: str | None, host: str = "panel.example") -> Request:
    headers = [(b"host", host.encode())]
    if origin:
        headers.append((b"origin", origin.encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/api/v1/settings/2fa/setup",
            "headers": headers,
            "server": (host, 443),
            "client": ("127.0.0.1", 1234),
        }
    )


def test_secure_configuration_rejects_weak_signing_secrets() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(cookie_secure=True, secret_key="short")
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            tls_cert_file="/tmp/certificate.pem",
            secret_key="dev-secret-change-in-production",
        )
    Settings(cookie_secure=True, secret_key="x" * 32)


def test_pyjwt_round_trip_and_tamper_rejection() -> None:
    token = create_access_token("user-id", "admin")
    assert decode_token(token)["sub"] == "user-id"
    with pytest.raises(ValueError):
        decode_token(token + "tampered")


def test_step_up_requires_password_and_enabled_totp() -> None:
    secret = pyotp.random_base32()
    user = User(
        id="user-id",
        username="admin",
        password_hash=hash_password("correct horse battery staple"),
        totp_enabled=True,
        totp_secret=secret,
    )

    with pytest.raises(ValueError, match="password"):
        verify_step_up(user, "wrong", pyotp.TOTP(secret).now())
    with pytest.raises(ValueError, match="2FA"):
        verify_step_up(user, "correct horse battery staple")
    verify_step_up(
        user,
        "correct horse battery staple",
        pyotp.TOTP(secret).now(),
    )


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "https://u:p@host/",
        "https://:password@host/",
        "https://example.com/\nmalicious",
    ],
)
def test_bookmarks_reject_dangerous_urls(url: str) -> None:
    with pytest.raises(ValidationError):
        BookmarkIn(title="bad", url=url)


def test_bookmarks_allow_http_and_https() -> None:
    assert BookmarkIn(title="ok", url="https://example.com/path").url.startswith("https://")
    assert BookmarkIn(title="lan", url="http://192.168.1.2").url.startswith("http://")


def test_cookie_origin_guard_requires_same_or_trusted_origin() -> None:
    assert is_allowed_http_origin(_request("https://panel.example"))
    assert not is_allowed_http_origin(_request("https://evil.panel.example"))
    assert not is_allowed_http_origin(_request(None))
    spoofed = _request("https://evil.panel.example")
    spoofed.scope["headers"].append((b"x-forwarded-host", b"evil.panel.example"))
    assert not is_allowed_http_origin(spoofed)


def test_oversized_bcrypt_input_fails_without_raising() -> None:
    password_hash = hash_password("normal password")
    assert not verify_password("x" * 1000, password_hash)
    with pytest.raises(ValueError, match="72"):
        hash_password("é" * 40)


@pytest.mark.parametrize(
    ("url", "allowed"),
    [
        ("https://panel.example", True),
        ("HTTPS://panel.example", True),
        ("http://192.168.1.2", False),
        ("https://user@panel.example", False),
        ("https://:password@panel.example", False),
        ("https://panel.example/\nheader", False),
    ],
)
def test_pairing_accepts_only_clean_https_endpoints(url: str, allowed: bool) -> None:
    assert _is_https_endpoint(url) is allowed


@pytest.mark.asyncio
async def test_streaming_body_limit_rejects_chunked_overflow() -> None:
    messages = iter(
        [
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"456", "more_body": False},
        ]
    )
    sent: list[dict] = []

    async def receive() -> dict:
        return next(messages)

    async def send(message: dict) -> None:
        sent.append(message)

    async def consuming_app(scope: dict, receive, send) -> None:
        while True:
            message = await receive()
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestBodyLimitMiddleware(consuming_app, max_bytes=5)
    await middleware(
        {"type": "http", "method": "POST", "headers": []},
        receive,
        send,
    )

    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413
