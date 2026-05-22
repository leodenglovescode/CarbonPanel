import asyncio
import os
import re
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
    can_unmount: bool
    bus_type: str


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


def _get_bus_type(device: str) -> str:
    """Determine connection bus via sysfs.

    Returns 'usb', 'nvme', 'sata', 'mmc', 'virtual', or 'unknown'.
    """
    dev = device.replace("/dev/", "")
    if dev.startswith("nvme"):
        return "nvme"
    if dev.startswith("mmcblk"):
        return "mmc"
    if dev.startswith("loop"):
        return "virtual"
    # Strip partition suffix: sda1 → sda, sdb2 → sdb
    base = re.sub(r"\d+$", "", dev)
    sys_path = f"/sys/block/{base}"
    if not os.path.exists(sys_path):
        return "unknown"
    try:
        real_path = os.path.realpath(sys_path)
        if "/usb" in real_path:
            return "usb"
    except OSError:
        pass
    return "sata"


def _can_unmount(device: str, mountpoint: str) -> bool:
    if mountpoint == "/":
        return False
    bus = _get_bus_type(device)
    return bus in ("usb", "mmc")


def _is_removable(device: str, mountpoint: str) -> bool:
    removable_prefixes = ("/media/", "/mnt/", "/run/media/")
    if any(mountpoint.startswith(p) for p in removable_prefixes):
        return True
    removable_devices = ("sd", "hd", "nvme", "mmcblk")
    dev = device.replace("/dev/", "")
    not_standard = not any(dev.startswith(p) for p in removable_devices)
    not_system_mount = mountpoint not in ("/", "/boot", "/home")
    return not_standard and not_system_mount


@router.get("", response_model=list[DiskInfo])
async def list_disks(_: User = Depends(get_current_user)):
    loop = asyncio.get_event_loop()

    partitions = await loop.run_in_executor(None, lambda: psutil.disk_partitions(all=False))

    results: list[DiskInfo] = []
    for p in partitions:
        try:
            usage = await loop.run_in_executor(None, lambda mp=p.mountpoint: psutil.disk_usage(mp))
        except PermissionError:
            continue

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
            can_unmount=_can_unmount(p.device, p.mountpoint),
            bus_type=_get_bus_type(p.device),
        ))

    return results


@router.post("/unmount", response_model=ActionResponse)
async def unmount_disk(body: UnmountRequest, _: User = Depends(get_current_user)):
    if not body.mountpoint or body.mountpoint == "/":
        raise HTTPException(status_code=400, detail="Cannot unmount root filesystem")

    partitions = await asyncio.get_event_loop().run_in_executor(
        None, lambda: psutil.disk_partitions(all=False)
    )
    part = next((p for p in partitions if p.mountpoint == body.mountpoint), None)
    if part and not _can_unmount(part.device, part.mountpoint):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot unmount {part.device} — only USB and removable drives may be unmounted",
        )

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
