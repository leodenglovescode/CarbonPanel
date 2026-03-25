from fastapi import APIRouter

from app.api import auth, settings, sites, ws

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(settings.router)
api_router.include_router(sites.router)

# WebSocket is at root level (no /api/v1 prefix)
ws_router = ws.router
