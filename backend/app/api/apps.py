import asyncio

import psutil
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.app_label import AppLabel
from app.models.user import User

router = APIRouter(prefix="/apps", tags=["apps"])

WELL_KNOWN: dict[int, str] = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    587: "SMTP/TLS",
    993: "IMAPS",
    995: "POP3S",
    1433: "MSSQL",
    1521: "Oracle DB",
    2375: "Docker",
    2376: "Docker TLS",
    3000: "Node.js / React",
    3306: "MySQL",
    4000: "Dev server",
    5000: "Flask / Dev",
    5173: "Vite",
    5432: "PostgreSQL",
    5601: "Kibana",
    6379: "Redis",
    8000: "Python / Django",
    8080: "HTTP Alt",
    8443: "HTTPS Alt",
    8787: "CarbonPanel",
    9200: "Elasticsearch",
    9300: "Elasticsearch cluster",
    11211: "Memcached",
    15672: "RabbitMQ UI",
    27017: "MongoDB",
    27018: "MongoDB shard",
    28017: "MongoDB HTTP",
}


class AppInfo(BaseModel):
    port: int
    protocol: str
    pid: int | None
    process_name: str
    user: str
    cmdline: str
    auto_label: str
    custom_label: str | None


class LabelRequest(BaseModel):
    label: str


class ActionResponse(BaseModel):
    success: bool
    output: str


def _get_listening_apps(labels: dict[int, str]) -> list[AppInfo]:
    try:
        conns = psutil.net_connections(kind="inet")
    except psutil.AccessDenied:
        conns = []

    seen: set[tuple[int, str]] = set()
    results: list[AppInfo] = []

    for c in conns:
        if c.status != psutil.CONN_LISTEN:
            continue
        port = c.laddr.port
        proto = "tcp" if c.type == 1 else "udp"
        key = (port, proto)
        if key in seen:
            continue
        seen.add(key)

        pid = c.pid
        pname = ""
        user = ""
        cmdline = ""
        if pid:
            try:
                p = psutil.Process(pid)
                pname = p.name()
                user = p.username()
                cmd = p.cmdline()
                cmdline = " ".join(cmd[:6]) if cmd else ""
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        results.append(AppInfo(
            port=port,
            protocol=proto,
            pid=pid,
            process_name=pname,
            user=user,
            cmdline=cmdline,
            auto_label=WELL_KNOWN.get(port, ""),
            custom_label=labels.get(port),
        ))

    results.sort(key=lambda x: x.port)
    return results


@router.get("", response_model=list[AppInfo])
async def list_apps(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(AppLabel))).scalars().all()
    labels = {r.port: r.label for r in rows}

    loop = asyncio.get_event_loop()
    apps = await loop.run_in_executor(None, lambda: _get_listening_apps(labels))
    return apps


@router.put("/{port}/label", response_model=ActionResponse)
async def set_label(
    port: int,
    body: LabelRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not 1 <= port <= 65535:
        raise HTTPException(status_code=400, detail="Port must be 1–65535")

    existing = await db.get(AppLabel, port)
    if existing:
        existing.label = body.label.strip()
    else:
        db.add(AppLabel(port=port, label=body.label.strip()))
    await db.commit()
    return ActionResponse(success=True, output=f"Label set for port {port}")


@router.delete("/{port}/label", response_model=ActionResponse)
async def delete_label(
    port: int,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(AppLabel).where(AppLabel.port == port))
    await db.commit()
    return ActionResponse(success=True, output=f"Label removed for port {port}")


@router.post("/{port}/kill", response_model=ActionResponse)
async def kill_process(
    port: int,
    _: User = Depends(get_current_user),
):
    loop = asyncio.get_event_loop()
    try:
        conns = await loop.run_in_executor(None, lambda: psutil.net_connections(kind="inet"))
    except psutil.AccessDenied:
        raise HTTPException(status_code=403, detail="Insufficient permissions to read connections")

    conn = next(
        (c for c in conns if c.laddr.port == port and c.status == psutil.CONN_LISTEN and c.pid),
        None,
    )
    if not conn:
        raise HTTPException(status_code=404, detail=f"No listening process found on port {port}")

    try:
        proc = psutil.Process(conn.pid)
        pname = proc.name()
        proc.terminate()
        return ActionResponse(success=True, output=f"Sent SIGTERM to {pname} (PID {conn.pid})")
    except psutil.NoSuchProcess:
        raise HTTPException(status_code=404, detail="Process no longer exists")
    except psutil.AccessDenied:
        raise HTTPException(status_code=403, detail="Permission denied — cannot kill this process")
