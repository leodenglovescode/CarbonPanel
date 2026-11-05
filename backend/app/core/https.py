"""Require TLS for deployed API and WebSocket connections behind nginx."""

from ipaddress import ip_address

from starlette.responses import JSONResponse


class RequireHTTPSMiddleware:
    def __init__(self, app, enabled: bool):
        self.app = app
        self.enabled = enabled

    async def __call__(self, scope, receive, send):
        kind = scope["type"]
        if not self.enabled or kind not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        # Uvicorn sets the ASGI scheme from Forwarded headers only for the
        # explicitly trusted loopback nginx peer. Never inspect arbitrary
        # X-Forwarded-Proto headers here.
        if scope.get("scheme") in ("https", "wss"):
            return await self.app(scope, receive, send)
        peer = (scope.get("client") or ("", 0))[0]
        try:
            loopback = ip_address(peer).is_loopback
        except ValueError:
            loopback = False
        # The installer's local readiness probe reads documentation, never
        # an authenticated API or a file, before nginx is restarted.
        if (
            kind == "http"
            and loopback
            and scope.get("method") in ("GET", "HEAD")
            and scope.get("path") in ("/docs", "/openapi.json")
        ):
            return await self.app(scope, receive, send)
        if kind == "websocket":
            await send({"type": "websocket.close", "code": 1008, "reason": "HTTPS is required"})
        else:
            await JSONResponse({"detail": "HTTPS is required"}, status_code=400)(
                scope, receive, send
            )
