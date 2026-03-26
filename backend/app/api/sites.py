import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.security import decode_token
from app.database import get_db
from app.models.user import User
from app.schemas.sites import (
    ConfigReadResponse,
    ConfigWriteRequest,
    SiteActionRequest,
    SiteActionResponse,
    SiteCreate,
    SiteResponse,
    SiteUpdate,
    SystemServiceActionRequest,
    SystemServiceAutostartRequest,
    SystemServiceReorderRequest,
    SystemServiceResponse,
    SystemServiceStarRequest,
)
from app.services import site_service

router = APIRouter(prefix="/sites", tags=["sites"])


def _404(site_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Site '{site_id}' not found",
    )


def _system_service_404(service_name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"System service '{service_name}' not found",
    )


@router.get("", response_model=list[SiteResponse])
async def list_sites(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sites = await site_service.list_sites(db)
    statuses = await asyncio.gather(*(site_service.get_status(site) for site in sites))
    return [
        site_service.site_to_response(site, site_status)
        for site, site_status in zip(sites, statuses, strict=False)
    ]


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    data: SiteCreate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await site_service.create_site(db, data)
    return site_service.site_to_response(site)


@router.get("/system-services", response_model=list[SystemServiceResponse])
async def list_system_services(
    include_all: bool = False,
    starred_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await site_service.list_system_services(
        db,
        current_user.id,
        include_all=include_all,
        starred_only=starred_only,
    )


@router.post("/system-services/{service_name}/action", response_model=SiteActionResponse)
async def system_service_action(
    service_name: str,
    body: SystemServiceActionRequest,
    _: User = Depends(get_current_user),
):
    service = await site_service.get_system_service(service_name)
    if not service:
        raise _system_service_404(service_name)
    try:
        success, output = await site_service.run_system_service_action(
            service.service_name,
            body.action,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return SiteActionResponse(success=success, output=output)


@router.post("/system-services/{service_name}/autostart", response_model=SiteActionResponse)
async def set_system_service_autostart(
    service_name: str,
    body: SystemServiceAutostartRequest,
    _: User = Depends(get_current_user),
):
    service = await site_service.get_system_service(service_name)
    if not service:
        raise _system_service_404(service_name)
    try:
        success, output = await site_service.set_system_service_autostart(
            service.service_name,
            body.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return SiteActionResponse(success=success, output=output)


@router.post("/system-services/{service_name}/star", response_model=SiteActionResponse)
async def set_system_service_star(
    service_name: str,
    body: SystemServiceStarRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = await site_service.get_system_service(service_name)
    if not service:
        raise _system_service_404(service_name)

    await site_service.set_system_service_star(
        db,
        current_user.id,
        service.service_name,
        body.starred,
    )
    return SiteActionResponse(
        success=True,
        output="starred" if body.starred else "unstarred",
    )


@router.post("/system-services/starred/reorder", response_model=SiteActionResponse)
async def reorder_starred_system_services(
    body: SystemServiceReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await site_service.reorder_starred_system_services(
        db,
        current_user.id,
        body.service_names,
    )
    return SiteActionResponse(success=True, output="reordered")


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await site_service.get_site(db, site_id)
    if not site:
        raise _404(site_id)
    st = await site_service.get_status(site)
    return site_service.site_to_response(site, st)


@router.put("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: str,
    data: SiteUpdate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await site_service.get_site(db, site_id)
    if not site:
        raise _404(site_id)
    site = await site_service.update_site(db, site, data)
    return site_service.site_to_response(site)


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await site_service.get_site(db, site_id)
    if not site:
        raise _404(site_id)
    await site_service.delete_site(db, site)


@router.post("/{site_id}/action", response_model=SiteActionResponse)
async def site_action(
    site_id: str,
    body: SiteActionRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await site_service.get_site(db, site_id)
    if not site:
        raise _404(site_id)
    try:
        success, output = await site_service.run_action(site, body.action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return SiteActionResponse(success=success, output=output)


@router.get("/{site_id}/config", response_model=ConfigReadResponse)
async def read_config(
    site_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await site_service.get_site(db, site_id)
    if not site:
        raise _404(site_id)
    if not site.config_file_path:
        raise HTTPException(
            status_code=400,
            detail="No config file path set for this site",
        )
    try:
        content = site_service.read_config(site.config_file_path)
    except (FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ConfigReadResponse(content=content, path=site.config_file_path)


@router.put("/{site_id}/config", status_code=status.HTTP_204_NO_CONTENT)
async def write_config(
    site_id: str,
    body: ConfigWriteRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await site_service.get_site(db, site_id)
    if not site:
        raise _404(site_id)
    if not site.config_file_path:
        raise HTTPException(
            status_code=400,
            detail="No config file path set for this site",
        )
    try:
        site_service.write_config(site.config_file_path, body.content)
    except (FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.websocket("/{site_id}/logs")
async def stream_logs(site_id: str, ws: WebSocket, token: str = ""):
    try:
        payload = decode_token(token)
        if payload.get("scope") != "full":
            await ws.close(code=4001)
            return
    except ValueError:
        await ws.close(code=4001)
        return

    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        site = await site_service.get_site(db, site_id)

    if not site:
        await ws.close(code=4004)
        return

    log_paths = json.loads(site.log_paths or "[]")
    if not log_paths:
        await ws.accept()
        await ws.send_text(json.dumps({"line": "[No log paths configured for this site]"}))
        await ws.close()
        return

    await ws.accept()
    try:
        async for line in site_service.tail_log(log_paths[0]):
            try:
                await ws.send_text(json.dumps({"line": line}))
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
