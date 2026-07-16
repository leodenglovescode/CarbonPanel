from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.api.router import api_router, ws_logs_router, ws_router
from app.api.system import router as system_router
from app.config import settings
from app.services.metrics.collector import metrics_collector
from app.services.smart import smart_scanner

# Defense-in-depth cap on request bodies. The real limit for internet-facing
# deployments is nginx's client_max_body_size (see install script); this
# covers the case where the backend is hit directly (e.g. local dev).
_MAX_BODY_BYTES = 10 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.secret_key == "dev-secret-change-in-production":
        print(
            "\n*** WARNING: SECRET_KEY is unset (using the well-known dev default). "
            "Any deployment reachable from the internet with this default lets "
            "anyone forge admin tokens. Set SECRET_KEY in backend/.env. ***\n"
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            too_large = int(content_length) > _MAX_BODY_BYTES
        except ValueError:
            too_large = False
        if too_large:
            return JSONResponse(status_code=413, content={"detail": "Request body too large"})
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    # The full CSP/frame-ancestors/HSTS set lives in the nginx config (install
    # script) since nginx serves index.html, not FastAPI. This just covers
    # direct API access with the headers that are meaningful on JSON responses.
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


app.include_router(api_router)
app.include_router(system_router)
app.include_router(ws_router)
app.include_router(ws_logs_router)
