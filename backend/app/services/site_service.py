import asyncio
import json
import shutil
from pathlib import Path
from typing import AsyncIterator

from app.models.site import Site
from app.models.starred_system_service import StarredSystemService
from app.schemas.sites import SiteCreate, SiteStatus, SiteUpdate, SystemServiceResponse
from sqlalchemy import func, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession

_SYSTEMD_SHOW_PROPERTIES = [
    "Id",
    "Description",
    "LoadState",
    "ActiveState",
    "SubState",
    "MainPID",
    "ActiveEnterTimestamp",
    "UnitFileState",
    "FragmentPath",
]

_AUTOSTART_ENABLED_STATES = {
    "enabled",
    "enabled-runtime",
    "linked",
    "linked-runtime",
}

_ADMIN_CREATED_UNIT_PATH_PREFIXES = (
    "/etc/systemd/system/",
    "/usr/local/lib/systemd/system/",
)

_ADMIN_CREATED_UNIT_DIRS = tuple(
    Path(path.rstrip("/"))
    for path in _ADMIN_CREATED_UNIT_PATH_PREFIXES
)

_STARRED_SYSTEM_SERVICES_TABLE_READY = False


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


def _normalize_service_name(service_name: str) -> str:
    unit = service_name.strip()
    if not unit:
        raise ValueError("Service name is required")
    if "/" in unit or "\x00" in unit:
        raise ValueError("Invalid service name")
    if not unit.endswith(".service"):
        unit = f"{unit}.service"
    return unit


def _parse_systemctl_show(output: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value
    return data


def _parse_systemctl_show_many(output: str) -> dict[str, dict[str, str]]:
    results: dict[str, dict[str, str]] = {}
    current: dict[str, str] = {}

    for line in output.splitlines():
        if not line.strip():
            service_name = current.get("Id")
            if service_name:
                results[service_name] = current
            current = {}
            continue

        if line.startswith("Id=") and current:
            service_name = current.get("Id")
            if service_name:
                results[service_name] = current
            current = {}

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        current[key] = value

    service_name = current.get("Id")
    if service_name:
        results[service_name] = current

    return results


def _parse_main_pid(raw: str | None) -> int | None:
    if not raw or raw == "0":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _is_autostart_enabled(unit_file_state: str) -> bool:
    return unit_file_state in _AUTOSTART_ENABLED_STATES


def _is_admin_created_system_service(properties: dict[str, str]) -> bool:
    fragment_path = properties.get("FragmentPath", "")
    return any(
        fragment_path.startswith(prefix)
        for prefix in _ADMIN_CREATED_UNIT_PATH_PREFIXES
    )


def _list_admin_created_service_names() -> list[str]:
    service_names: set[str] = set()

    for base_dir in _ADMIN_CREATED_UNIT_DIRS:
        if not base_dir.exists():
            continue

        for unit_file in base_dir.glob("*.service"):
            if not unit_file.is_file() or unit_file.name.endswith("@.service"):
                continue
            service_names.add(unit_file.name)

    return sorted(service_names)


async def _list_all_system_service_names() -> list[str]:
    rc, out = await _run(
        [
            "systemctl",
            "list-unit-files",
            "--type=service",
            "--no-legend",
            "--no-pager",
        ]
    )
    if rc != 0 and not out:
        return []

    service_names: set[str] = set()
    for line in out.splitlines():
        parts = line.split(None, 1)
        if not parts:
            continue
        service_name = parts[0]
        if not service_name.endswith(".service") or service_name.endswith("@.service"):
            continue
        service_names.add(service_name)

    return sorted(service_names)


async def _show_system_services(service_names: list[str]) -> dict[str, dict[str, str]]:
    if not service_names:
        return {}

    _, show = await _run(
        [
            "systemctl",
            "show",
            *service_names,
            f"--property={','.join(_SYSTEMD_SHOW_PROPERTIES)}",
            "--no-pager",
        ]
    )
    return _parse_systemctl_show_many(show)


def _system_service_from_properties(
    properties: dict[str, str],
    fallback_name: str,
    *,
    starred: bool = False,
) -> SystemServiceResponse:
    unit_file_state = properties.get("UnitFileState") or "unknown"
    return SystemServiceResponse(
        service_name=properties.get("Id") or fallback_name,
        description=properties.get("Description") or None,
        load_state=properties.get("LoadState") or "unknown",
        active_state=properties.get("ActiveState") or "unknown",
        sub_state=properties.get("SubState") or "unknown",
        uptime=properties.get("ActiveEnterTimestamp") or None,
        pid=_parse_main_pid(properties.get("MainPID")),
        unit_file_state=unit_file_state,
        autostart_enabled=_is_autostart_enabled(unit_file_state),
        starred=starred,
    )


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
    status = out.strip() if rc == 0 or out.strip() else "unknown"
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


async def get_autostart_enabled(site: Site) -> bool:
    if site.service_manager != "systemd":
        return False
    rc, out = await _run(["systemctl", "is-enabled", site.service_name])
    state = out.strip().lower()
    return rc == 0 and state in {"enabled", "enabled-runtime", "static", "indirect", "generated"}


async def set_autostart(site: Site, enabled: bool) -> tuple[bool, str]:
    if site.service_manager != "systemd":
        raise ValueError(f"Autostart is only supported for systemd services, got: {site.service_manager}")
    cmd = ["systemctl", "enable" if enabled else "disable", site.service_name]
    rc, out = await _run(cmd)
    return rc == 0, out


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


def read_config(path: str) -> str:
    return Path(path).read_text(errors="replace")


def write_config(path: str, content: str) -> None:
    p = Path(path)
    if p.exists():
        shutil.copy2(p, p.with_suffix(p.suffix + ".bak"))
    p.write_text(content)


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


async def _ensure_starred_system_services_table(db: AsyncSession) -> None:
    global _STARRED_SYSTEM_SERVICES_TABLE_READY

    if _STARRED_SYSTEM_SERVICES_TABLE_READY:
        return

    def _ensure(sync_session) -> None:
        connection = sync_session.connection()
        StarredSystemService.__table__.create(
            bind=connection,
            checkfirst=True,
        )

        column_names = {
            column["name"]
            for column in inspect(connection).get_columns("starred_system_services")
        }
        if "position" not in column_names:
            connection.execute(
                text(
                    "ALTER TABLE starred_system_services "
                    "ADD COLUMN position INTEGER NOT NULL DEFAULT 0"
                )
            )

    await db.run_sync(_ensure)
    _STARRED_SYSTEM_SERVICES_TABLE_READY = True


async def list_starred_system_services(
    db: AsyncSession,
    user_id: str,
) -> list[StarredSystemService]:
    await _ensure_starred_system_services_table(db)
    result = await db.execute(
        select(StarredSystemService)
        .where(StarredSystemService.user_id == user_id)
        .order_by(
            StarredSystemService.position,
            StarredSystemService.created_at,
            StarredSystemService.service_name,
        )
    )
    return list(result.scalars().all())


async def list_starred_system_service_names(db: AsyncSession, user_id: str) -> list[str]:
    starred_services = await list_starred_system_services(db, user_id)
    return [service.service_name for service in starred_services]


async def set_system_service_star(
    db: AsyncSession,
    user_id: str,
    service_name: str,
    starred: bool,
) -> None:
    await _ensure_starred_system_services_table(db)
    unit = _normalize_service_name(service_name)
    result = await db.execute(
        select(StarredSystemService).where(
            StarredSystemService.user_id == user_id,
            StarredSystemService.service_name == unit,
        )
    )
    existing = result.scalar_one_or_none()

    if starred and existing is None:
        max_position_result = await db.execute(
            select(func.max(StarredSystemService.position)).where(
                StarredSystemService.user_id == user_id
            )
        )
        next_position = (max_position_result.scalar_one() or -1) + 1
        db.add(
            StarredSystemService(
                user_id=user_id,
                service_name=unit,
                position=next_position,
            )
        )
    elif not starred and existing is not None:
        await db.delete(existing)

    await db.commit()


async def reorder_starred_system_services(
    db: AsyncSession,
    user_id: str,
    service_names: list[str],
) -> None:
    starred_services = await list_starred_system_services(db, user_id)
    starred_by_name = {
        service.service_name: service
        for service in starred_services
    }

    ordered_names: list[str] = []
    seen: set[str] = set()

    for service_name in service_names:
        unit = _normalize_service_name(service_name)
        if unit in starred_by_name and unit not in seen:
            ordered_names.append(unit)
            seen.add(unit)

    for service in starred_services:
        if service.service_name not in seen:
            ordered_names.append(service.service_name)

    for index, service_name in enumerate(ordered_names):
        starred_by_name[service_name].position = index

    await db.commit()


async def list_system_services(
    db: AsyncSession,
    user_id: str,
    include_all: bool = False,
    starred_only: bool = False,
) -> list[SystemServiceResponse]:
    starred_service_names_in_order = await list_starred_system_service_names(db, user_id)
    starred_service_names = set(starred_service_names_in_order)

    if starred_only:
        candidate_service_names = starred_service_names_in_order
    elif include_all:
        candidate_service_names = await _list_all_system_service_names()
    else:
        candidate_service_names = _list_admin_created_service_names()

    if not candidate_service_names:
        return []

    properties_by_service = await _show_system_services(candidate_service_names)

    services: list[SystemServiceResponse] = []
    for service_name in candidate_service_names:
        properties = properties_by_service.get(service_name, {})
        if properties.get("LoadState") == "not-found":
            continue

        is_starred = service_name in starred_service_names

        if not starred_only and not include_all and not _is_admin_created_system_service(properties):
            continue

        services.append(
            _system_service_from_properties(
                properties,
                service_name,
                starred=is_starred,
            )
        )

    return services


async def get_system_service(service_name: str) -> SystemServiceResponse | None:
    unit = _normalize_service_name(service_name)
    rc, out = await _run(
        [
            "systemctl",
            "show",
            unit,
            f"--property={','.join(_SYSTEMD_SHOW_PROPERTIES)}",
            "--no-pager",
        ]
    )
    properties = _parse_systemctl_show(out)
    if (rc != 0 and not properties) or properties.get("LoadState") == "not-found":
        return None
    return _system_service_from_properties(properties, unit)


async def run_system_service_action(service_name: str, action: str) -> tuple[bool, str]:
    if action not in ("start", "stop", "restart"):
        raise ValueError(f"Unknown action: {action}")

    unit = _normalize_service_name(service_name)
    rc, out = await _run(["systemctl", action, unit])
    return rc == 0, out


async def set_system_service_autostart(service_name: str, enabled: bool) -> tuple[bool, str]:
    unit = _normalize_service_name(service_name)
    rc, out = await _run(["systemctl", "enable" if enabled else "disable", unit])
    return rc == 0, out


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
