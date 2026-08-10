from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.router import api_router, ws_logs_router, ws_router
from app.api.system import router as system_router
from app.config import settings
from app.core.dependencies import COOKIE_NAME, is_allowed_http_origin
from app.services.metrics.collector import metrics_collector
from app.services.smart import smart_scanner

# Defense-in-depth cap on request bodies. The real limit for internet-facing
# deployments is nginx's client_max_body_size (see install script); this
# covers the case where the backend is hit directly (e.g. local dev).
_MAX_BODY_BYTES = 22 * 1024 * 1024


class _RequestTooLarge(Exception):
    pass


class RequestBodyLimitMiddleware:
    """Enforce the body cap while streaming, including chunked requests."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                declared = int(content_length)
            except ValueError:
                await JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})(
                    scope, receive, send
                )
                return
            if declared < 0 or declared > self.max_bytes:
                await JSONResponse(status_code=413, content={"detail": "Request body too large"})(
                    scope, receive, send
                )
                return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _RequestTooLarge
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _RequestTooLarge:
            if response_started:
                raise
            await JSONResponse(status_code=413, content={"detail": "Request body too large"})(
                scope, receive, send
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.secret_key == "dev-secret-change-in-production":
        # This value is public (it's in the repo), so leaving it in place
        # lets anyone forge a valid session/JWT for any account. `make setup`
        # already generates a random one — refuse to serve traffic rather
        # than silently run with a known-forgeable signing key.
        raise RuntimeError(
            "SECRET_KEY is unset (using the well-known dev default). Refusing to "
            "start: this default lets anyone forge auth tokens. Set SECRET_KEY in "
            "backend/.env (run `make setup` or `openssl rand -hex 32`)."
        )
    if settings.admin_password == "changeme":
        print(
            "*** WARNING: ADMIN_PASSWORD is unset (using the well-known default "
            "'changeme'). Set ADMIN_PASSWORD in backend/.env before exposing this "
            "instance to the internet. ***\n"
        )
    metrics_collector.start()
    smart_scanner.start()
    yield
    metrics_collector.stop()
    smart_scanner.stop()


app = FastAPI(
    title="CarbonPanel",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestBodyLimitMiddleware, max_bytes=_MAX_BODY_BYTES)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def csrf_origin_guard(request: Request, call_next):
    if (
        request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and request.cookies.get(COOKIE_NAME)
        and not is_allowed_http_origin(request)
    ):
        return JSONResponse(
            status_code=403,
            content={"detail": "Cross-origin cookie-authenticated request rejected"},
        )
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    # The full CSP/frame-ancestors/HSTS set lives in the nginx config (install
    # script) since nginx serves index.html, not FastAPI. This just covers
    # direct API access with the headers that are meaningful on JSON responses.
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


app.include_router(api_router)
app.include_router(system_router)
app.include_router(ws_router)
app.include_router(ws_logs_router)
