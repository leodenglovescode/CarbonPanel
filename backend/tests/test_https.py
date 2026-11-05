import asyncio

import httpx
from fastapi import FastAPI
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.https import RequireHTTPSMiddleware


def build():
    app = FastAPI()

    @app.get("/private")
    async def private():
        return {"ok": True}

    return ProxyHeadersMiddleware(
        RequireHTTPSMiddleware(app, enabled=True), trusted_hosts="127.0.0.1"
    )


def get(url, client=("127.0.0.1", 1234), headers=None):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=build(), client=client)
        ) as http:
            return await http.get(url, headers=headers)

    return asyncio.run(run())


def test_tls_required_and_trusted_proxy():
    assert get("https://panel.test/private").status_code == 200
    assert get("http://panel.test/private").status_code == 400
    assert (
        get("http://panel.test/private", headers={"X-Forwarded-Proto": "https"}).status_code == 200
    )
    assert (
        get(
            "http://panel.test/private",
            client=("198.51.100.5", 1234),
            headers={"X-Forwarded-Proto": "https"},
        ).status_code
        == 400
    )


def test_only_loopback_readiness_probe_can_use_http():
    assert get("http://panel.test/docs").status_code == 200
    assert get("http://panel.test/docs", client=("198.51.100.5", 1234)).status_code == 400


def test_insecure_websocket_is_rejected_before_authentication():
    async def run():
        sent = []

        async def application(*args):
            raise AssertionError("Insecure socket must not reach the app")

        async def receive():
            return {"type": "websocket.connect"}

        async def send(message):
            sent.append(message)

        await RequireHTTPSMiddleware(application, enabled=True)(
            {"type": "websocket", "scheme": "ws", "client": ("127.0.0.1", 1234)},
            receive,
            send,
        )
        assert sent == [{"type": "websocket.close", "code": 1008, "reason": "HTTPS is required"}]

    asyncio.run(run())
