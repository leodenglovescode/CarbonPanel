"""Background SMART scanner.

Runs smartctl -a -j on all physical drives at startup and every 24 h.
Results are cached in memory; the disks API reads from the cache.
"""

import asyncio
import json
import logging
import re
import shutil
from dataclasses import dataclass

log = logging.getLogger(__name__)

_SCAN_INTERVAL = 86_400  # 24 hours


@dataclass
class SmartResult:
    device: str
    model: str = "Unknown"
    serial: str = ""
    firmware: str = ""
    health: str = "UNKNOWN"          # PASSED | FAILED | UNKNOWN
    temperature_c: int | None = None
    power_on_hours: int | None = None
    reallocated_sectors: int | None = None
    pending_sectors: int | None = None
    uncorrectable_errors: int | None = None
    last_checked: str = ""
    error: str | None = None


# module-level cache: physical_device → SmartResult
_cache: dict[str, SmartResult] = {}
_task: asyncio.Task | None = None


def get_cache() -> dict[str, SmartResult]:
    return _cache


def physical_device(partition_device: str) -> str:
    """Strip partition suffix to get the block device name."""
    dev = partition_device.replace("/dev/", "")
    # NVMe: nvme0n1p2 → nvme0n1
    m = re.match(r"^(nvme\d+n\d+)p\d+$", dev)
    if m:
        return f"/dev/{m.group(1)}"
    # SATA / SCSI: sda1 → sda, hda2 → hda
    m = re.match(r"^([a-z]+[a-z])\d+$", dev)
    if m:
        return f"/dev/{m.group(1)}"
    # Already a base device
    return partition_device


async def _list_physical_devices() -> list[str]:
    """Return base block devices from /sys/block (non-virtual)."""
    devices: list[str] = []
    try:
        import os
        for name in os.listdir("/sys/block"):
            if re.match(r"^(sd[a-z]+|hd[a-z]+|nvme\d+n\d+|mmcblk\d+)$", name):
                devices.append(f"/dev/{name}")
    except Exception:
        pass
    return devices


def _parse_json(data: dict, device: str) -> SmartResult:
    smart_status = data.get("smart_status", {})
    if "passed" in smart_status:
        health = "PASSED" if smart_status["passed"] else "FAILED"
    else:
        # NVMe drives often omit smart_status.passed — use critical_warning instead.
        # critical_warning == 0 means no issues reported.
        nvme_log = data.get("nvme_smart_health_information_log")
        if isinstance(nvme_log, dict):
            health = "PASSED" if nvme_log.get("critical_warning", 0) == 0 else "FAILED"
        else:
            health = "UNKNOWN"

    result = SmartResult(
        device=device,
        model=data.get("model_name") or data.get("model_family") or "Unknown",
        serial=data.get("serial_number") or "",
        firmware=data.get("firmware_version") or "",
        health=health,
        last_checked=_iso_now(),
    )

    # Temperature
    temp = data.get("temperature")
    if isinstance(temp, dict):
        result.temperature_c = temp.get("current")

    # NVMe health log
    nvme = data.get("nvme_smart_health_information_log")
    if nvme:
        result.power_on_hours = nvme.get("power_on_hours")
        result.reallocated_sectors = nvme.get("media_errors", 0)
        result.uncorrectable_errors = nvme.get("media_errors", 0)

    # ATA attributes
    attrs_table = data.get("ata_smart_attributes", {}).get("table", [])
    attrs = {a["id"]: a for a in attrs_table}
    if 9 in attrs:
        result.power_on_hours = _raw_int(attrs[9])
    if 5 in attrs:
        result.reallocated_sectors = _raw_int(attrs[5])
    if 197 in attrs:
        result.pending_sectors = _raw_int(attrs[197])
    if 198 in attrs:
        result.uncorrectable_errors = _raw_int(attrs[198])

    return result


def _raw_int(attr: dict) -> int | None:
    try:
        return int(attr["raw"]["value"])
    except (KeyError, TypeError, ValueError):
        return None


def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _scan_device(device: str) -> SmartResult:
    if not shutil.which("smartctl"):
        return SmartResult(device=device, error="smartctl not installed", last_checked=_iso_now())

    try:
        proc = await asyncio.create_subprocess_exec(
            "smartctl", "-a", "-j", device,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        rc = proc.returncode or 0
        # Exit code bits: bit0=parse error, bit1=device open failed, bit3=disk failing, etc.
        if rc & 3:  # bits 0+1: command line / device-open error
            try:
                err_data = json.loads(stdout.decode(errors="replace"))
                msgs = [
                    m["string"]
                    for m in err_data.get("smartctl", {}).get("messages", [])
                    if m.get("severity") == "error"
                ]
                err_msg = msgs[0] if msgs else f"smartctl error (rc={rc})"
            except Exception:
                err_msg = f"smartctl error (rc={rc})"
            return SmartResult(device=device, error=err_msg, last_checked=_iso_now())

        try:
            data = json.loads(stdout.decode(errors="replace"))
            result = _parse_json(data, device)
            # Mark FAILED if bit 4 set (drive actively failing)
            if rc & 16:
                result.health = "FAILED"
            return result
        except (json.JSONDecodeError, Exception) as e:
            return SmartResult(device=device, error=f"parse error: {e}", last_checked=_iso_now())
    except asyncio.TimeoutError:
        return SmartResult(device=device, error="smartctl timed out", last_checked=_iso_now())
    except Exception as e:
        return SmartResult(device=device, error=str(e), last_checked=_iso_now())


async def scan_all() -> None:
    """Scan all physical drives and update the cache."""
    devices = await _list_physical_devices()
    if not devices:
        return
    results = await asyncio.gather(*[_scan_device(d) for d in devices], return_exceptions=True)
    for r in results:
        if isinstance(r, SmartResult):
            _cache[r.device] = r
        elif isinstance(r, Exception):
            log.warning("SMART scan error: %s", r)
    log.info("SMART scan complete: %d devices", len(_cache))


async def scan_device(device: str) -> SmartResult:
    """Scan a single physical device and update the cache."""
    result = await _scan_device(device)
    _cache[result.device] = result
    return result


class SmartScanner:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        # Initial scan shortly after startup
        await asyncio.sleep(5)
        while True:
            try:
                await scan_all()
            except Exception as e:
                log.warning("SMART background scan failed: %s", e)
            await asyncio.sleep(_SCAN_INTERVAL)


smart_scanner = SmartScanner()
