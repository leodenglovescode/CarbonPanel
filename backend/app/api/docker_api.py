import asyncio
import json
import os
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/docker", tags=["docker"])

_PERMISSION_HINT = (
    "Permission denied accessing Docker. The carbonpanel service account uses a "
    "scoped sudo rule (not docker-group membership) for container start/stop/"
    "restart. Run: sudo carbonpanel fix"
)

_STATS_CACHE: dict[str, dict] = {}
_STATS_CACHE_TS: float = 0.0
_STATS_REFRESH_INTERVAL = 10.0
_stats_lock = asyncio.Lock()
_stats_task: asyncio.Task | None = None


async def _exec(cmd: list[str]) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    return proc.returncode, stdout.decode(errors="replace").strip()


async def _run(cmd: list[str]) -> tuple[int, str]:
    # The service account is not in the docker group (scoped sudo instead, see
    # install script) — go straight to sudo. Fall back to a bare call for
    # deployments still on the older docker-group model (pre-upgrade, or a
    # manual non-standard setup) so this doesn't regress them.
    if os.geteuid() != 0:
        sudo_cmd = ["/usr/bin/sudo", "-n", *cmd]
        rc, out = await _exec(sudo_cmd)
        if rc == 0:
            return rc, out
        rc2, out2 = await _exec(cmd)
        if rc2 == 0:
            return rc2, out2
        if "permission denied" in (out + out2).lower():
            return rc, _PERMISSION_HINT
        return rc2, out2
    return await _exec(cmd)


def _safe_id(s: str) -> bool:
    if not s or len(s) > 128 or s.startswith("-"):
        return False
    return all(c.isalnum() or c in "-_." for c in s)


def _parse_mem_mb(s: str) -> float:
    s = s.strip().upper()
    try:
        if s.endswith("GIB"):
            return float(s[:-3]) * 1024
        if s.endswith("MIB"):
            return float(s[:-3])
        if s.endswith("KIB"):
            return float(s[:-3]) / 1024
        if s.endswith("GB"):
            return float(s[:-2]) * 1000
        if s.endswith("MB"):
            return float(s[:-2])
        if s.endswith("KB"):
            return float(s[:-2]) / 1000
        if s.endswith("B"):
            return float(s[:-1]) / (1024 * 1024)
    except ValueError:
        pass
    return 0.0


class ContainerInfo(BaseModel):
    id: str
    name: str
    image: str
    status: str
    state: str
    ports: str
    created: str
    cpu_percent: float = 0.0
    mem_usage_mb: float = 0.0
    mem_limit_mb: float = 0.0
    mem_percent: float = 0.0


class ActionResponse(BaseModel):
    success: bool
    output: str = ""


async def _refresh_stats(running_ids: list[str]) -> None:
    global _STATS_CACHE, _STATS_CACHE_TS
    async with _stats_lock:
        if not running_ids:
            return
        src, stats_out = await _run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}", *running_ids]
        )
        if src != 0:
            return
        new_cache: dict[str, dict] = {}
        for line in stats_out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                s = json.loads(line)
                cid = s.get("ID", s.get("Container", ""))
                new_cache[cid] = s
            except Exception:
                pass
        _STATS_CACHE = new_cache
        _STATS_CACHE_TS = time.monotonic()


async def _ensure_stats_fresh(running_ids: list[str]) -> None:
    global _stats_task
    age = time.monotonic() - _STATS_CACHE_TS
    if age > _STATS_REFRESH_INTERVAL:
        if _stats_task is None or _stats_task.done():
            _stats_task = asyncio.create_task(_refresh_stats(running_ids))


@router.get("/containers", response_model=list[ContainerInfo])
async def list_containers(_: User = Depends(get_current_user)):
    rc, out = await _run(["docker", "ps", "-a", "--format", "{{json .}}"])
    if rc != 0:
        raise HTTPException(status_code=503, detail=out or "Docker unavailable")

    containers_raw: list[dict] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            containers_raw.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    running_ids = [d["ID"] for d in containers_raw if d.get("State") == "running"]

    # On first load, block briefly to get initial stats; after that serve from cache.
    if not _STATS_CACHE and running_ids:
        await _refresh_stats(running_ids)
    else:
        asyncio.create_task(_ensure_stats_fresh(running_ids))

    result = []
    for d in containers_raw:
        cid = d.get("ID", "")
        s = _STATS_CACHE.get(cid, {})
        cpu_pct = mem_mb = mem_limit = mem_pct = 0.0
        if s:
            try:
                cpu_pct = float(s.get("CPUPerc", "0%").rstrip("%"))
            except (ValueError, AttributeError):
                pass
            try:
                parts = s.get("MemUsage", "").split(" / ")
                if len(parts) == 2:
                    mem_mb = _parse_mem_mb(parts[0])
                    mem_limit = _parse_mem_mb(parts[1])
                mem_pct = float(s.get("MemPerc", "0%").rstrip("%"))
            except (ValueError, AttributeError):
                pass

        result.append(ContainerInfo(
            id=cid,
            name=d.get("Names", "").lstrip("/"),
            image=d.get("Image", ""),
            status=d.get("Status", ""),
            state=d.get("State", ""),
            ports=d.get("Ports", ""),
            created=d.get("CreatedAt", ""),
            cpu_percent=cpu_pct,
            mem_usage_mb=mem_mb,
            mem_limit_mb=mem_limit,
            mem_percent=mem_pct,
        ))

    return result


@router.post("/containers/{container_id}/start", response_model=ActionResponse)
async def start_container(container_id: str, _: User = Depends(get_current_user)):
    if not _safe_id(container_id):
        raise HTTPException(400, "Invalid container ID")
    rc, out = await _run(["docker", "start", container_id])
    return ActionResponse(success=rc == 0, output=out)


@router.post("/containers/{container_id}/stop", response_model=ActionResponse)
async def stop_container(container_id: str, _: User = Depends(get_current_user)):
    if not _safe_id(container_id):
        raise HTTPException(400, "Invalid container ID")
    rc, out = await _run(["docker", "stop", container_id])
    return ActionResponse(success=rc == 0, output=out)


@router.post("/containers/{container_id}/restart", response_model=ActionResponse)
async def restart_container(container_id: str, _: User = Depends(get_current_user)):
    if not _safe_id(container_id):
        raise HTTPException(400, "Invalid container ID")
    rc, out = await _run(["docker", "restart", container_id])
    return ActionResponse(success=rc == 0, output=out)
