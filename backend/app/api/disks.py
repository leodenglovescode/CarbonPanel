import asyncio
import shutil

import psutil
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/disks", tags=["disks"])

_GB = 1024 ** 3
_MB = 1024 ** 2

_VIRTUAL_FSTYPES = {
    "squashfs", "tmpfs", "devtmpfs", "sysfs", "proc", "procfs",
    "cgroup", "cgroup2", "pstore", "bpf", "tracefs", "debugfs",
    "securityfs", "fusectl", "hugetlbfs", "mqueue", "devpts",
    "overlay", "aufs", "ramfs", "efivarfs", "binfmt_misc", "nsfs",
    "configfs", "selinuxfs", "autofs", "sockfs", "pipefs",
    "anon_inodefs", "rpc_pipefs", "nfsd", "fuse",
}


class DiskInfo(BaseModel):
    device: str
    mountpoint: str
    fstype: str
    opts: str
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float
    read_mb_s: float
    write_mb_s: float
    is_removable: bool
    is_virtual: bool


class UnmountRequest(BaseModel):
    mountpoint: str


class ActionResponse(BaseModel):
    success: bool
    output: str


def _is_virtual(device: str, fstype: str) -> bool:
    if fstype.lower() in _VIRTUAL_FSTYPES:
        return True
    dev = device.replace("/dev/", "")
    return dev.startswith("loop")


def _is_removable(device: str, mountpoint: str) -> bool:
    removable_prefixes = ("/media/", "/mnt/", "/run/media/")
    if any(mountpoint.startswith(p) for p in removable_prefixes):
        return True
    removable_devices = ("sd", "hd", "nvme", "mmcblk")
    dev = device.replace("/dev/", "")
    return not any(dev.startswith(p) for p in removable_devices) and mountpoint not in ("/", "/boot", "/home")


@router.get("", response_model=list[DiskInfo])
async def list_disks(_: User = Depends(get_current_user)):
    loop = asyncio.get_event_loop()

    partitions, io_counters = await asyncio.gather(
        loop.run_in_executor(None, lambda: psutil.disk_partitions(all=False)),
        loop.run_in_executor(None, lambda: psutil.disk_io_counters(perdisk=True)),
    )

    results: list[DiskInfo] = []
    for p in partitions:
        try:
            usage = await loop.run_in_executor(None, lambda mp=p.mountpoint: psutil.disk_usage(mp))
        except PermissionError:
            continue

        dev = p.device.replace("/dev/", "")
        io_key = next(
            (k for k in (io_counters or {}) if dev.startswith(k) or k.startswith(dev)),
            dev,
        )
        io = (io_counters or {}).get(io_key)

        fstype = p.fstype or "unknown"
        results.append(DiskInfo(
            device=p.device,
            mountpoint=p.mountpoint,
            fstype=fstype,
            opts=p.opts or "",
            total_gb=usage.total / _GB,
            used_gb=usage.used / _GB,
            free_gb=usage.free / _GB,
            usage_percent=usage.percent,
            read_mb_s=0.0,
            write_mb_s=0.0,
            is_removable=_is_removable(p.device, p.mountpoint),
            is_virtual=_is_virtual(p.device, fstype),
        ))

    return results


@router.post("/unmount", response_model=ActionResponse)
async def unmount_disk(body: UnmountRequest, _: User = Depends(get_current_user)):
    if not body.mountpoint or body.mountpoint == "/":
        raise HTTPException(status_code=400, detail="Cannot unmount root filesystem")

    if not shutil.which("umount"):
        raise HTTPException(status_code=503, detail="umount not available on this system")

    proc = await asyncio.create_subprocess_exec(
        "umount", body.mountpoint,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    output = (stdout + stderr).decode(errors="replace").strip()
    success = proc.returncode == 0

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=output or "umount failed",
        )

    return ActionResponse(success=True, output=output or "Unmounted successfully")


@router.post("/check", response_model=ActionResponse)
async def check_disk(body: UnmountRequest, _: User = Depends(get_current_user)):
    """Run a read-only fsck check on the device at the given mountpoint."""
    partitions = await asyncio.get_event_loop().run_in_executor(
        None, lambda: psutil.disk_partitions(all=False)
    )
    part = next((p for p in partitions if p.mountpoint == body.mountpoint), None)
    if not part:
        raise HTTPException(status_code=404, detail="Mountpoint not found")

    if not shutil.which("fsck"):
        raise HTTPException(status_code=503, detail="fsck not available on this system")

    proc = await asyncio.create_subprocess_exec(
        "fsck", "-n", part.device,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    output = (stdout + stderr).decode(errors="replace").strip()

    return ActionResponse(
        success=proc.returncode in (0, 1),
        output=output or "No output from fsck",
    )
