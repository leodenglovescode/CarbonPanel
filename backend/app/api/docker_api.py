import asyncio
import json
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/docker", tags=["docker"])

_PERMISSION_HINT = (
    "Permission denied accessing Docker socket. "
    "Run: sudo usermod -aG docker $USER  then log out and back in."
)


async def _exec(cmd: list[str]) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    return proc.returncode, stdout.decode(errors="replace").strip()


async def _run(cmd: list[str]) -> tuple[int, str]:
    rc, out = await _exec(cmd)
    # Retry with sudo if the socket is inaccessible and we're not already root
    if rc != 0 and "permission denied" in out.lower() and os.geteuid() != 0:
        sudo_cmd = ["/usr/bin/sudo", "-n", *cmd]
        rc2, out2 = await _exec(sudo_cmd)
        if rc2 == 0:
            return rc2, out2
        # Both failed — return a helpful message instead of the raw kernel error
        return rc, _PERMISSION_HINT
    return rc, out


def _safe_id(s: str) -> bool:
    return bool(s) and len(s) <= 128 and all(c.isalnum() or c in "-_." for c in s)


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
    stats_map: dict[str, dict] = {}

    if running_ids:
        src, stats_out = await _run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}", *running_ids]
        )
        if src == 0:
            for line in stats_out.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    s = json.loads(line)
                    cid = s.get("ID", s.get("Container", ""))
                    stats_map[cid] = s
                except Exception:
                    pass

    result = []
    for d in containers_raw:
        s = stats_map.get(d.get("ID", ""), {})
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
            id=d.get("ID", ""),
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
