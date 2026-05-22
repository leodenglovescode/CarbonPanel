from fastapi import APIRouter

from app.api import (
    apps, auth, cron, disks, docker_api, metrics_history,
    processes, sessions, settings, sites, webhooks, ws, ws_logs,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(settings.router)
api_router.include_router(sites.router)
api_router.include_router(disks.router)
api_router.include_router(apps.router)
api_router.include_router(docker_api.router)
api_router.include_router(webhooks.router)
api_router.include_router(processes.router)
api_router.include_router(cron.router)
api_router.include_router(sessions.router)
api_router.include_router(metrics_history.router)

# WebSockets are at root level (no /api/v1 prefix)
ws_router = ws.router
ws_logs_router = ws_logs.router
