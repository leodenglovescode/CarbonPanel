import asyncio
import os
import re
import shutil
from itertools import groupby

import psutil
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services import smart as smart_svc

router = APIRouter(prefix="/disks", tags=["disks"])

_GB = 1024 ** 3
_MB = 1024 ** 2

# Real block-storage device names (bare metal + common VPS bus types) whose
# partitions should be grouped under one physical-disk card. Deliberately
# excludes loop/tmpfs/etc. so unrelated virtual mounts never get merged.
_REAL_DISK_RE = re.compile(
    r"^/dev/(sd[a-z]+|hd[a-z]+|vd[a-z]+|xvd[a-z]+|nvme\d+n\d+|mmcblk\d+)(p?\d+)?$"
)

_VIRTUAL_FSTYPES = {
    "squashfs", "tmpfs", "devtmpfs", "sysfs", "proc", "procfs",
    "cgroup", "cgroup2", "pstore", "bpf", "tracefs", "debugfs",
    "securityfs", "fusectl", "hugetlbfs", "mqueue", "devpts",
    "overlay", "aufs", "ramfs", "efivarfs", "binfmt_misc", "nsfs",
    "configfs", "selinuxfs", "autofs", "sockfs", "pipefs",
    "anon_inodefs", "rpc_pipefs", "nfsd", "fuse",
}


class SmartResult(BaseModel):
    model: str
    serial: str
    firmware: str
    health: str
    temperature_c: int | None
    power_on_hours: int | None
    reallocated_sectors: int | None
    pending_sectors: int | None
    uncorrectable_errors: int | None
    last_checked: str
    error: str | None


class DiskInfo(BaseModel):
    device: str
    mountpoint: str
    extra_mounts: list[str]
    physical_device: str
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
    smart: SmartResult | None


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
    dev = device.replace("/dev/", "")
    if dev.startswith("nvme"):
        return "nvme"
    if dev.startswith("mmcblk"):
        return "mmc"
    if dev.startswith("loop"):
        return "virtual"
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


def _is_removable(device: str) -> bool:
    # Ask the kernel rather than guess from the device name or mountpoint —
    # SATA, USB, and virtio-SCSI disks can all show up as /dev/sd*, and /mnt/
    # is a common convention for mounting *permanent* server data disks too.
    # /sys/block/<dev>/removable is the actual hardware flag.
    base = smart_svc.physical_device(device).replace("/dev/", "")
    try:
        with open(f"/sys/block/{base}/removable") as f:
            return f.read().strip() == "1"
    except OSError:
        return False


def _smart_response(phys: str) -> SmartResult | None:
    r = smart_svc.get_cache().get(phys)
    if r is None:
        return None
    return SmartResult(
        model=r.model,
        serial=r.serial,
        firmware=r.firmware,
        health=r.health,
        temperature_c=r.temperature_c,
        power_on_hours=r.power_on_hours,
        reallocated_sectors=r.reallocated_sectors,
        pending_sectors=r.pending_sectors,
        uncorrectable_errors=r.uncorrectable_errors,
        last_checked=r.last_checked,
        error=r.error,
    )


def _primary_mount(mounts: list[str]) -> str:
    if "/" in mounts:
        return "/"
    return min(mounts, key=len)


def _group_key(device: str) -> str:
    # Group sibling partitions (e.g. /boot, /boot/efi) of the same physical
    # disk into one card instead of listing each as its own "disk".
    return smart_svc.physical_device(device) if _REAL_DISK_RE.match(device) else device


@router.get("", response_model=list[DiskInfo])
async def list_disks(_: User = Depends(get_current_user)):
    loop = asyncio.get_event_loop()
    partitions = await loop.run_in_executor(None, lambda: psutil.disk_partitions(all=False))

    raw: list[tuple] = []
    for p in partitions:
        try:
            usage = await loop.run_in_executor(None, lambda mp=p.mountpoint: psutil.disk_usage(mp))
            raw.append((p, usage))
        except PermissionError:
            continue

    # Group by physical disk: same device bind-mounted at multiple paths, and
    # sibling partitions (e.g. /boot, /boot/efi) of the same real disk, both
    # collapse into one card instead of showing as separate disks.
    raw.sort(key=lambda t: _group_key(t[0].device))
    results: list[DiskInfo] = []

    for _key, group in groupby(raw, key=lambda t: _group_key(t[0].device)):
        group_list = list(group)
        mounts = [t[0].mountpoint for t in group_list]
        primary_mp = _primary_mount(mounts)
        extra_mounts = [m for m in mounts if m != primary_mp]

        primary_part, primary_usage = next(t for t in group_list if t[0].mountpoint == primary_mp)
        device = primary_part.device
        fstype = primary_part.fstype or "unknown"
        phys = smart_svc.physical_device(device)

        results.append(DiskInfo(
            device=device,
            mountpoint=primary_mp,
            extra_mounts=extra_mounts,
            physical_device=phys,
            fstype=fstype,
            opts=primary_part.opts or "",
            total_gb=primary_usage.total / _GB,
            used_gb=primary_usage.used / _GB,
            free_gb=primary_usage.free / _GB,
            usage_percent=primary_usage.percent,
            read_mb_s=0.0,
            write_mb_s=0.0,
            is_removable=_is_removable(device),
            is_virtual=_is_virtual(device, fstype),
            can_unmount=_can_unmount(device, primary_mp),
            bus_type=_get_bus_type(device),
            smart=_smart_response(phys),
        ))

    return results


@router.post("/smart/refresh", response_model=list[SmartResult])
async def refresh_smart(_: User = Depends(get_current_user)):
    """Trigger an immediate SMART scan of all physical drives."""
    await smart_svc.scan_all()
    return [
        SmartResult(
            model=r.model, serial=r.serial, firmware=r.firmware,
            health=r.health, temperature_c=r.temperature_c,
            power_on_hours=r.power_on_hours, reallocated_sectors=r.reallocated_sectors,
            pending_sectors=r.pending_sectors, uncorrectable_errors=r.uncorrectable_errors,
            last_checked=r.last_checked, error=r.error,
        )
        for r in smart_svc.get_cache().values()
    ]


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
