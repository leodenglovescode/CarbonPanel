import asyncio
import json
import os
import re
import shutil
import time
from collections import Counter, OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncIterator

from app.models.site import Site
from app.models.starred_system_service import StarredSystemService
from app.schemas.sites import (
    NginxDiscoverResponse,
    NginxImportResponse,
    NginxSiteCandidate,
    SiteCreate,
    SiteStatus,
    SiteUpdate,
    SystemServiceResponse,
)
from sqlalchemy import func, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession

_NGINX_SITES_AVAILABLE = Path("/etc/nginx/sites-available")

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

_SUPPORTED_SYSTEMD_UNIT_SUFFIXES = (
    ".service",
    ".timer",
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
    if "/" in unit or "\x00" in unit or unit.startswith("-"):
        raise ValueError("Invalid service name")
    if unit.endswith(_SUPPORTED_SYSTEMD_UNIT_SUFFIXES):
        return unit
    if "." in unit:
        raise ValueError("Unsupported unit type")
    return f"{unit}.service"


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

        for suffix in _SUPPORTED_SYSTEMD_UNIT_SUFFIXES:
            for unit_file in base_dir.glob(f"*{suffix}"):
                if not unit_file.is_file() or unit_file.stem.endswith("@"):
                    continue
                service_names.add(unit_file.name)

    return sorted(service_names)


async def _list_all_system_service_names() -> list[str]:
    rc, out = await _run(
        [
            "systemctl",
            "list-unit-files",
            "--type=service",
            "--type=timer",
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
        if (
            not service_name.endswith(_SUPPORTED_SYSTEMD_UNIT_SUFFIXES)
            or service_name.rsplit(".", 1)[0].endswith("@")
        ):
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
        raise ValueError(
            f"Autostart is only supported for systemd services, got: {site.service_manager}"
        )
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


# Sites' config_file_path / log_paths are free-form strings set by whoever
# creates the site — with no restriction, the config read/write endpoints
# would let any authenticated user touch any file the backend process can
# reach (/etc/shadow, SSH keys, ...). Config edits are restricted to where
# site configs actually live; log reads get the same set plus /var/log,
# since that's where nginx/apache/syslog-based app logs live by convention
# (and is what the log-viewer UI's own "/var/log/..." custom-path hint implies).
_ALLOWED_CONFIG_DIRS = (
    Path("/etc/nginx"),
    Path("/etc/apache2"),
    Path("/etc/systemd/system"),
    Path("/etc/supervisor"),
    Path("/etc/uwsgi"),
)
_ALLOWED_LOG_DIRS = _ALLOWED_CONFIG_DIRS + (Path("/var/log"),)


def _resolve_allowed(path: str, allowed_dirs: tuple[Path, ...]) -> Path:
    resolved = Path(path).resolve()
    for base in allowed_dirs:
        base_resolved = base.resolve()
        if resolved == base_resolved or base_resolved in resolved.parents:
            return resolved
    raise PermissionError(
        f"'{path}' is outside the allowed directories "
        f"({', '.join(str(d) for d in allowed_dirs)})"
    )


def read_config(path: str) -> str:
    resolved = _resolve_allowed(path, _ALLOWED_CONFIG_DIRS)
    return resolved.read_text(errors="replace")


def write_config(path: str, content: str) -> None:
    resolved = _resolve_allowed(path, _ALLOWED_CONFIG_DIRS)
    if resolved.exists():
        shutil.copy2(resolved, resolved.with_suffix(resolved.suffix + ".bak"))
    resolved.write_text(content)


async def tail_log(path: str) -> AsyncIterator[str]:
    resolved = _resolve_allowed(path, _ALLOWED_LOG_DIRS)
    proc = await asyncio.create_subprocess_exec(
        "tail",
        "-n",
        "100",
        "-f",
        str(resolved),
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


_ACCESS_LOG_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"\S+ (?P<path>\S+) \S+" (?P<status>\d{3}) (?P<bytes>\d+|-)',
)

_TRAFFIC_TOP_N = 5
_TRAFFIC_TOP_CAP = 200  # prune path/ip counters back to this once cardinality grows past it

# ponytail: per-site incremental tail buffer instead of re-parsing the whole
# log every poll. Bucket count is capped so memory stays flat regardless of
# traffic volume; a stale buffer's first catch-up read is capped too, so a
# site nobody's watched for hours can't pull a huge backlog into memory at once.
_TRAFFIC_BUCKET_MAX = 130  # >2h of minute buckets, covers the 120min max window
_TRAFFIC_CATCHUP_CAP = 5 * 1024 * 1024  # 5MB max read per catch-up
_TRAFFIC_IDLE_EVICT_SECONDS = 900  # drop buffers for sites nobody's polled in 15min

_traffic_buffers: dict[str, "_TrafficBuffer"] = {}
_traffic_locks: dict[str, asyncio.Lock] = {}


class _TrafficBuffer:
    __slots__ = (
        "path", "offset", "inode", "minute_buckets", "path_counts", "ip_counts", "last_access",
    )

    def __init__(self, path: str) -> None:
        self.path = path
        self.offset = 0
        self.inode: int | None = None
        self.minute_buckets: OrderedDict[str, dict[str, int]] = OrderedDict()
        self.path_counts: Counter[str] = Counter()
        self.ip_counts: Counter[str] = Counter()
        self.last_access = time.monotonic()


def _evict_idle_traffic_buffers() -> None:
    # ponytail: many-sites-on-one-VPS is the real long-uptime memory risk here,
    # not a single traffic spike (that's bounded by _TRAFFIC_CATCHUP_CAP already)
    cutoff = time.monotonic() - _TRAFFIC_IDLE_EVICT_SECONDS
    for site_id in [sid for sid, b in _traffic_buffers.items() if b.last_access < cutoff]:
        _traffic_buffers.pop(site_id, None)
        _traffic_locks.pop(site_id, None)


def _get_traffic_lock(site_id: str) -> asyncio.Lock:
    lock = _traffic_locks.get(site_id)
    if lock is None:
        lock = asyncio.Lock()
        _traffic_locks[site_id] = lock
    return lock


def _read_new_traffic_bytes(path: str, offset: int, size: int) -> tuple[bytes, int]:
    start = offset if size - offset <= _TRAFFIC_CATCHUP_CAP else size - _TRAFFIC_CATCHUP_CAP
    with open(path, "rb") as f:
        f.seek(start)
        data = f.read()
        return data, f.tell()


async def _update_traffic_buffer(site_id: str, log_path: str) -> _TrafficBuffer:
    buf = _traffic_buffers.get(site_id)
    if buf is None or buf.path != log_path:
        buf = _TrafficBuffer(log_path)
        _traffic_buffers[site_id] = buf

    try:
        stat = await asyncio.to_thread(os.stat, log_path)
    except OSError:
        return buf

    if buf.inode is not None and stat.st_ino != buf.inode:
        buf.offset = 0  # log rotated
    buf.inode = stat.st_ino

    if stat.st_size < buf.offset:
        buf.offset = 0  # log truncated

    if stat.st_size == buf.offset:
        return buf

    data, new_offset = await asyncio.to_thread(
        _read_new_traffic_bytes, log_path, buf.offset, stat.st_size,
    )
    buf.offset = new_offset

    for raw_line in data.split(b"\n"):
        m = _ACCESS_LOG_RE.match(raw_line.decode(errors="replace"))
        if not m:
            continue
        try:
            ts = datetime.strptime(m.group("time"), "%d/%b/%Y:%H:%M:%S %z")
        except ValueError:
            continue

        minute_key = ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
        bucket = buf.minute_buckets.get(minute_key)
        if bucket is None:
            bucket = {"count": 0, "bytes": 0, "2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
            buf.minute_buckets[minute_key] = bucket

        bucket["count"] += 1
        status_bucket = f"{m.group('status')[0]}xx"
        if status_bucket in bucket:
            bucket[status_bucket] += 1
        raw_bytes = m.group("bytes")
        if raw_bytes.isdigit():
            bucket["bytes"] += int(raw_bytes)

        buf.path_counts[m.group("path").split("?", 1)[0]] += 1
        buf.ip_counts[m.group("ip")] += 1

    while len(buf.minute_buckets) > _TRAFFIC_BUCKET_MAX:
        buf.minute_buckets.popitem(last=False)

    # ponytail: cap tracked cardinality so unique-path/IP floods (scans, cache
    # busting query strings) can't grow these unboundedly between evictions
    if len(buf.path_counts) > _TRAFFIC_TOP_CAP:
        buf.path_counts = Counter(dict(buf.path_counts.most_common(_TRAFFIC_TOP_CAP // 2)))
    if len(buf.ip_counts) > _TRAFFIC_TOP_CAP:
        buf.ip_counts = Counter(dict(buf.ip_counts.most_common(_TRAFFIC_TOP_CAP // 2)))

    return buf


async def get_site_traffic(site_id: str, log_path: str, minutes: int = 30) -> dict:
    """Return a traffic summary built from an incrementally-updated per-site buffer."""
    _resolve_allowed(log_path, _ALLOWED_LOG_DIRS)
    _evict_idle_traffic_buffers()
    async with _get_traffic_lock(site_id):
        buf = await _update_traffic_buffer(site_id, log_path)
        buf.last_access = time.monotonic()

    now = datetime.now(timezone.utc)
    total_requests = total_bytes = 0
    status_counts = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
    requests_per_minute = []

    for i in range(minutes - 1, -1, -1):
        minute_dt = now - timedelta(minutes=i)
        bucket = buf.minute_buckets.get(minute_dt.strftime("%Y-%m-%d %H:%M"))
        count = bucket["count"] if bucket else 0
        requests_per_minute.append({"minute": minute_dt.strftime("%H:%M"), "count": count})
        if bucket:
            total_requests += bucket["count"]
            total_bytes += bucket["bytes"]
            for key in status_counts:
                status_counts[key] += bucket[key]

    return {
        "window_minutes": minutes,
        "total_requests": total_requests,
        "total_bytes": total_bytes,
        "status_2xx": status_counts["2xx"],
        "status_3xx": status_counts["3xx"],
        "status_4xx": status_counts["4xx"],
        "status_5xx": status_counts["5xx"],
        "requests_per_minute": requests_per_minute,
        "top_paths": [
            {"value": path, "count": count}
            for path, count in buf.path_counts.most_common(_TRAFFIC_TOP_N)
        ],
        "top_ips": [
            {"value": ip, "count": count}
            for ip, count in buf.ip_counts.most_common(_TRAFFIC_TOP_N)
        ],
    }


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

        is_admin_service = _is_admin_created_system_service(properties)
        if not starred_only and not include_all and not is_admin_service:
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


# ── nginx auto-discovery ────────────────────────────────────────────────────


def _parse_nginx_config(path: Path) -> tuple[list[str], list[str]]:
    """Return (server_names, log_paths) extracted from an nginx config file."""
    try:
        text_content = path.read_text(errors="replace")
    except OSError:
        return [], []

    server_names: list[str] = []
    for m in re.finditer(r"server_name\s+([^;]+);", text_content):
        for tok in m.group(1).split():
            if tok != "_" and tok not in server_names:
                server_names.append(tok)

    log_paths: list[str] = []
    for directive in ("access_log", "error_log"):
        for m in re.finditer(rf"{directive}\s+([^\s;]+)", text_content):
            val = m.group(1)
            if val != "off" and val not in log_paths:
                log_paths.append(val)

    return server_names, log_paths


async def discover_nginx_sites(db: AsyncSession) -> NginxDiscoverResponse:
    if not _NGINX_SITES_AVAILABLE.exists():
        return NginxDiscoverResponse(nginx_available=False, candidates=[])

    result = await db.execute(select(Site.config_file_path))
    existing_paths = {row[0] for row in result.fetchall() if row[0]}

    candidates: list[NginxSiteCandidate] = []
    for cfg in sorted(_NGINX_SITES_AVAILABLE.iterdir()):
        if cfg.name.startswith(".") or not cfg.is_file():
            continue
        server_names, log_paths = _parse_nginx_config(cfg)
        name = next((n for n in server_names if not n.startswith("*")), cfg.name)
        candidates.append(
            NginxSiteCandidate(
                name=name,
                config_file_path=str(cfg),
                server_names=server_names,
                log_paths=log_paths,
                already_exists=str(cfg) in existing_paths,
            )
        )

    return NginxDiscoverResponse(nginx_available=True, candidates=candidates)


async def import_nginx_sites(
    db: AsyncSession, config_file_paths: list[str]
) -> NginxImportResponse:
    result = await db.execute(select(Site.config_file_path))
    existing_paths = {row[0] for row in result.fetchall() if row[0]}

    imported_sites: list[Site] = []
    skipped = 0

    for cfg_str in config_file_paths:
        if cfg_str in existing_paths:
            skipped += 1
            continue
        try:
            cfg = _resolve_allowed(cfg_str, (_NGINX_SITES_AVAILABLE,))
        except PermissionError:
            skipped += 1
            continue
        if not cfg.is_file():
            skipped += 1
            continue
        server_names, log_paths = _parse_nginx_config(cfg)
        name = next((n for n in server_names if not n.startswith("*")), cfg.name)
        site = await create_site(
            db,
            SiteCreate(
                name=name,
                type="nginx",
                service_manager="systemd",
                service_name="nginx.service",
                config_file_path=cfg_str,
                log_paths=log_paths,
            ),
        )
        imported_sites.append(site)
        existing_paths.add(cfg_str)

    return NginxImportResponse(
        imported=len(imported_sites),
        skipped=skipped,
        sites=[site_to_response(s) for s in imported_sites],
    )
