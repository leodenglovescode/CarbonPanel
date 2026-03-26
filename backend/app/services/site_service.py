import asyncio
import json
import shutil
from pathlib import Path
from typing import AsyncIterator

from app.models.site import Site
from app.schemas.sites import SiteCreate, SiteStatus, SiteUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ───────────────────────────────────────────────────────────────────


def _encode_log_paths(paths: list[str]) -> str:
    return json.dumps(paths)


def _decode_log_paths(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return []


async def _run(cmd: list[str]) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    return proc.returncode, stdout.decode(errors="replace").strip()


# ── Status ────────────────────────────────────────────────────────────────────


async def get_status(site: Site) -> SiteStatus:
    try:
        if site.service_manager == "systemd":
            return await _systemd_status(site.service_name)
        if site.service_manager == "pm2":
            return await _pm2_status(site.service_name)
    except Exception:
        pass
    return SiteStatus(status="unknown")


async def _systemd_status(unit: str) -> SiteStatus:
    rc, out = await _run(["systemctl", "is-active", unit])
    status = out.strip()
    pid: int | None = None
    uptime: str | None = None

    if status == "active":
        _, show = await _run(
            ["systemctl", "show", unit, "--property=ActiveEnterTimestamp,MainPID"]
        )
        for line in show.splitlines():
            if line.startswith("MainPID="):
                try:
                    pid = int(line.split("=", 1)[1])
                except ValueError:
                    pass
            if line.startswith("ActiveEnterTimestamp=") and "=" in line:
                uptime = line.split("=", 1)[1].strip()

    return SiteStatus(status=status, uptime=uptime, pid=pid)


async def _pm2_status(app_name: str) -> SiteStatus:
    rc, out = await _run(["pm2", "show", app_name])
    if rc != 0:
        return SiteStatus(status="unknown")

    status = "unknown"
    pid: int | None = None
    uptime: str | None = None

    for line in out.splitlines():
        lower = line.lower()
        if "status" in lower:
            if "online" in lower:
                status = "active"
            elif "stopped" in lower or "errored" in lower:
                status = "inactive"
        if "pid" in lower:
            try:
                pid = int(line.split("|")[-1].strip())
            except ValueError:
                pass
        if "uptime" in lower:
            uptime = line.split("|")[-1].strip()

    return SiteStatus(status=status, uptime=uptime, pid=pid)


# ── Actions ───────────────────────────────────────────────────────────────────


async def run_action(site: Site, action: str) -> tuple[bool, str]:
    if action not in ("start", "stop", "restart"):
        raise ValueError(f"Unknown action: {action}")

    if site.service_manager == "systemd":
        cmd = ["systemctl", action, site.service_name]
    elif site.service_manager == "pm2":
        cmd = ["pm2", action, site.service_name]
    else:
        raise ValueError(f"Unknown service_manager: {site.service_manager}")

    rc, out = await _run(cmd)
    return rc == 0, out


# ── Config file ───────────────────────────────────────────────────────────────


def read_config(path: str) -> str:
    return Path(path).read_text(errors="replace")


def write_config(path: str, content: str) -> None:
    p = Path(path)
    if p.exists():
        shutil.copy2(p, p.with_suffix(p.suffix + ".bak"))
    p.write_text(content)


# ── Log tailing ───────────────────────────────────────────────────────────────


async def tail_log(path: str) -> AsyncIterator[str]:
    proc = await asyncio.create_subprocess_exec(
        "tail",
        "-n",
        "100",
        "-f",
        path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            yield line.decode(errors="replace").rstrip("\n")
    finally:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            proc.kill()


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def list_sites(db: AsyncSession) -> list[Site]:
    result = await db.execute(select(Site).order_by(Site.created_at))
    return list(result.scalars().all())


async def get_site(db: AsyncSession, site_id: str) -> Site | None:
    result = await db.execute(select(Site).where(Site.id == site_id))
    return result.scalar_one_or_none()


async def create_site(db: AsyncSession, data: SiteCreate) -> Site:
    site = Site(
        name=data.name,
        type=data.type,
        service_name=data.service_name,
        service_manager=data.service_manager,
        config_file_path=data.config_file_path,
        log_paths=_encode_log_paths(data.log_paths),
        description=data.description,
    )
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


async def update_site(db: AsyncSession, site: Site, data: SiteUpdate) -> Site:
    if data.name is not None:
        site.name = data.name
    if data.type is not None:
        site.type = data.type
    if data.service_name is not None:
        site.service_name = data.service_name
    if data.service_manager is not None:
        site.service_manager = data.service_manager
    if data.config_file_path is not None:
        site.config_file_path = data.config_file_path
    if data.log_paths is not None:
        site.log_paths = _encode_log_paths(data.log_paths)
    if data.description is not None:
        site.description = data.description
    await db.commit()
    await db.refresh(site)
    return site


async def delete_site(db: AsyncSession, site: Site) -> None:
    await db.delete(site)
    await db.commit()


def site_to_response(site: Site, status: SiteStatus | None = None):
    from app.schemas.sites import SiteResponse

    return SiteResponse(
        id=site.id,
        name=site.name,
        type=site.type,
        service_name=site.service_name,
        service_manager=site.service_manager,
        config_file_path=site.config_file_path,
        log_paths=_decode_log_paths(site.log_paths),
        description=site.description,
        created_at=site.created_at,
        updated_at=site.updated_at,
        status=status,
    )
