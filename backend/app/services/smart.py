"""Background SMART scanner.

Runs a read-only smartctl health/attribute scan at startup and every 24 h.
Results are cached in memory; the disks API reads from the cache.
"""

import asyncio
import json
import logging
import math
import re
import shutil
from dataclasses import dataclass

log = logging.getLogger(__name__)

_SCAN_INTERVAL = 86_400  # 24 hours

# NVMe does not expose the manufacturer's rated TBW through SMART. Keep this
# catalogue explicit and model-specific so a value is never guessed from
# capacity. Add entries only from a manufacturer's published endurance rating.
_RATED_ENDURANCE_TBW: dict[str, float] = {
    "KINGSTON SNV2S4000G": 1280.0,
}


@dataclass
class SmartResult:
    device: str
    model: str = "Unknown"
    serial: str = ""
    firmware: str = ""
    drive_type: str = "unknown"       # hdd | ssd | nvme | unknown
    capacity_bytes: int | None = None
    health: str = "UNKNOWN"          # PASSED | FAILED | UNKNOWN
    health_percentage: float | None = None
    health_assessment: str = "Unknown"
    health_basis: str = ""
    health_notes: list[str] | None = None
    temperature_c: int | None = None
    temperature_sensors_c: list[int | None] | None = None
    highest_temperature_c: int | None = None
    power_on_hours: int | None = None
    power_cycle_count: int | None = None
    start_stop_count: int | None = None
    load_cycle_count: int | None = None
    reallocated_sectors: int | None = None
    pending_sectors: int | None = None
    uncorrectable_errors: int | None = None
    reported_uncorrectable_errors: int | None = None
    command_timeouts: int | None = None
    crc_errors: int | None = None
    wear_percentage_used: int | None = None
    rated_endurance_tbw: float | None = None
    lifetime_written_tb: float | None = None
    tbw_used_percent: float | None = None
    effective_wear_percent: float | None = None
    critical_warning: int | None = None
    available_spare_percent: int | None = None
    available_spare_threshold: int | None = None
    unsafe_shutdowns: int | None = None
    media_errors: int | None = None
    error_log_entries: int | None = None
    error_log_context: str | None = None
    data_read_bytes: int | None = None
    data_written_bytes: int | None = None
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
    # eMMC/SD: mmcblk0p1 → mmcblk0
    m = re.match(r"^(mmcblk\d+)p\d+$", dev)
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


def _parse_json(
    data: dict,
    device: str,
    previous: SmartResult | None = None,
) -> SmartResult:
    smart_status = data.get("smart_status", {})
    if "passed" in smart_status:
        health = "PASSED" if smart_status["passed"] else "FAILED"
    else:
        # NVMe drives often omit smart_status.passed — use critical_warning instead.
        nvme_log = data.get("nvme_smart_health_information_log")
        if isinstance(nvme_log, dict):
            health = "PASSED" if nvme_log.get("critical_warning", 0) == 0 else "FAILED"
        else:
            health = "UNKNOWN"

    rotation_rate = data.get("rotation_rate")
    protocol = str(data.get("device", {}).get("protocol", "")).lower()
    if "nvme" in protocol or device.startswith("/dev/nvme"):
        drive_type = "nvme"
    elif rotation_rate == 0:
        drive_type = "ssd"
    elif isinstance(rotation_rate, int) and rotation_rate > 0:
        drive_type = "hdd"
    else:
        drive_type = "unknown"

    result = SmartResult(
        device=device,
        model=data.get("model_name") or data.get("model_family") or "Unknown",
        serial=data.get("serial_number") or "",
        firmware=data.get("firmware_version") or "",
        drive_type=drive_type,
        capacity_bytes=_nested_int(data, "user_capacity", "bytes"),
        health=health,
        last_checked=_iso_now(),
    )
    result.rated_endurance_tbw = _rated_endurance_tbw(result.model)

    temp = data.get("temperature")
    if isinstance(temp, dict):
        result.temperature_c = _int_value(temp.get("current"))

    nvme = data.get("nvme_smart_health_information_log")
    if isinstance(nvme, dict):
        result.critical_warning = _int_value(nvme.get("critical_warning"))
        result.power_on_hours = _int_value(nvme.get("power_on_hours"))
        result.power_cycle_count = _int_value(nvme.get("power_cycles"))
        result.unsafe_shutdowns = _int_value(nvme.get("unsafe_shutdowns"))
        result.media_errors = _int_value(nvme.get("media_errors"))
        result.error_log_entries = _int_value(nvme.get("num_err_log_entries"))
        result.wear_percentage_used = _int_value(nvme.get("percentage_used"))
        result.available_spare_percent = _int_value(nvme.get("available_spare"))
        result.available_spare_threshold = _int_value(nvme.get("available_spare_threshold"))
        result.data_read_bytes = _nvme_data_bytes(nvme.get("data_units_read"))
        result.data_written_bytes = _nvme_data_bytes(nvme.get("data_units_written"))
        result.temperature_sensors_c = _temperature_sensors(
            nvme.get("temperature_sensors")
        )
        nvme_composite = _int_value(nvme.get("temperature"))
        if result.temperature_c is None:
            result.temperature_c = nvme_composite
        reported_sensors = [
            value for value in (result.temperature_sensors_c or []) if value is not None
        ]
        result.highest_temperature_c = (
            max(reported_sensors) if reported_sensors else result.temperature_c
        )
        if result.data_written_bytes is not None:
            result.lifetime_written_tb = result.data_written_bytes / 1_000_000_000_000
        if result.rated_endurance_tbw and result.lifetime_written_tb is not None:
            result.tbw_used_percent = (
                result.lifetime_written_tb / result.rated_endurance_tbw * 100
            )
        wear_sources = [
            value
            for value in [result.tbw_used_percent, result.wear_percentage_used]
            if value is not None
        ]
        result.effective_wear_percent = max(wear_sources) if wear_sources else None

        messages = data.get("smartctl", {}).get("messages", [])
        invalid_field = any(
            "invalid field in command" in str(message.get("string", "")).lower()
            for message in messages
            if isinstance(message, dict)
        )
        if invalid_field:
            result.error_log_context = (
                "An unsupported NVMe command returned Invalid Field in Command. "
                "This is a command/protocol error, not a NAND media failure, and "
                "is not included in estimated health."
            )
        elif result.error_log_entries is not None:
            result.error_log_context = (
                "NVMe error-log entries are command/protocol records, not media-error "
                "counts, and do not reduce estimated health. Media failures are shown "
                "separately."
            )

    attrs_table = data.get("ata_smart_attributes", {}).get("table", [])
    attrs = {
        a.get("id"): a
        for a in attrs_table
        if isinstance(a, dict) and a.get("id") is not None
    }
    if 9 in attrs:
        result.power_on_hours = _raw_int(attrs[9])
    if 12 in attrs:
        result.power_cycle_count = _raw_int(attrs[12])
    if 4 in attrs:
        result.start_stop_count = _raw_int(attrs[4])
    if 193 in attrs:
        result.load_cycle_count = _raw_int(attrs[193])
    if 5 in attrs:
        result.reallocated_sectors = _raw_int(attrs[5])
    if 187 in attrs:
        result.reported_uncorrectable_errors = _raw_int(attrs[187])
    if 188 in attrs:
        result.command_timeouts = _raw_int(attrs[188])
    if 197 in attrs:
        result.pending_sectors = _raw_int(attrs[197])
    if 198 in attrs:
        result.uncorrectable_errors = _raw_int(attrs[198])
    if 199 in attrs:
        result.crc_errors = _raw_int(attrs[199])

    # Vendor ATA SSDs expose remaining life through different attributes. The
    # normalized value is more portable than the vendor-specific raw payload.
    if result.drive_type == "ssd":
        for attr_id in (202, 231, 233, 177):
            if attr_id in attrs:
                remaining = _normalized_int(attrs[attr_id])
                if remaining is not None and 0 <= remaining <= 100:
                    result.wear_percentage_used = 100 - remaining
                    break

    if (
        result.drive_type == "ssd"
        and result.effective_wear_percent is None
        and result.wear_percentage_used is not None
    ):
        result.effective_wear_percent = float(result.wear_percentage_used)

    _calculate_health(result, previous)
    return result


def _raw_int(attr: dict) -> int | None:
    try:
        return _int_value(attr["raw"]["value"])
    except (KeyError, TypeError, ValueError):
        return None


def _normalized_int(attr: dict) -> int | None:
    return _int_value(attr.get("value"))


def _int_value(value: object) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if re.fullmatch(r"0[xX][\da-fA-F]+", cleaned):
            return int(cleaned, 16)
        match = re.search(r"-?\d+", cleaned)
        if match:
            return int(match.group())
    return None


def _nested_int(data: dict, *keys: str) -> int | None:
    value: object = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return _int_value(value)


def _nvme_data_bytes(value: object) -> int | None:
    units = _int_value(value)
    # NVMe SMART data units are defined as thousands of 512-byte units.
    return units * 512_000 if units is not None else None


def _rated_endurance_tbw(model: str) -> float | None:
    normalized = " ".join(model.upper().split())
    return _RATED_ENDURANCE_TBW.get(normalized)


def _temperature_sensors(value: object) -> list[int | None] | None:
    if isinstance(value, list):
        raw_sensors = value
    elif isinstance(value, dict):
        raw_sensors = list(value.values())
    else:
        return None
    sensors = [
        parsed if (parsed := _int_value(item)) is not None and parsed > 0 else None
        for item in raw_sensors
    ]
    return sensors if any(item is not None for item in sensors) else None


def _logarithmic_risk(
    count: int | None,
    *,
    base: float,
    step: float,
    cap: float,
) -> float:
    """Convert a lifetime counter into a bounded reliability-risk score."""
    if not count or count <= 0:
        return 0.0
    return min(cap, base + step * math.log2(1 + count))


def _hdd_sector_counts(result: SmartResult) -> tuple[int, int, int]:
    uncorrectable = max(
        result.uncorrectable_errors or 0,
        result.reported_uncorrectable_errors or 0,
    )
    return (
        result.reallocated_sectors or 0,
        result.pending_sectors or 0,
        uncorrectable,
    )


def _hdd_trend_penalty(
    result: SmartResult,
    previous: SmartResult | None,
) -> tuple[float, str | None]:
    """Score increases observed since the previous in-memory SMART scan.

    A server restart establishes a new baseline. Stable lifetime counters do not
    accumulate additional deductions on every refresh.
    """
    if previous is None or previous.drive_type != "hdd":
        return 0.0, None

    current = _hdd_sector_counts(result)
    prior = _hdd_sector_counts(previous)
    increases = [max(0, now - before) for now, before in zip(current, prior)]
    largest_increase = max(increases)
    if largest_increase == 0:
        return 0.0, None

    previous_peak = max(prior)
    if largest_increase >= max(64, previous_peak * 0.5):
        return 25.0, f"Sector-error counters rose by up to {largest_increase} since the previous scan."
    if largest_increase >= 8:
        return 15.0, f"Sector-error counters rose by up to {largest_increase} since the previous scan."
    return 8.0, f"Sector-error counters increased by {largest_increase} since the previous scan."


def _hdd_temperature_penalty(temperature_c: int | None) -> float:
    if temperature_c is None or temperature_c < 50:
        return 0.0
    if temperature_c < 55:
        return 3.0
    if temperature_c < 60:
        return 6.0
    return 10.0


def _calculate_health(
    result: SmartResult,
    previous: SmartResult | None = None,
) -> None:
    """Build a conservative, explainable SMART health estimate.

    For SSD/NVMe devices, the numeric value represents estimated endurance
    remaining. Rated-TBW consumption takes precedence when it is greater than
    the device's coarse reported percentage-used value. Reliability indicators
    affect the wording/assessment, not the endurance calculation.
    """
    notes: list[str] = []
    endurance_based = (
        result.drive_type in ("ssd", "nvme")
        and result.effective_wear_percent is not None
    )

    if endurance_based:
        score = max(0.0, min(100.0, 100.0 - result.effective_wear_percent))
        if result.tbw_used_percent is not None:
            basis = (
                "Estimated endurance remaining from the greater of calculated TBW "
                "consumption and device-reported wear. SMART warnings are assessed "
                "separately and do not fabricate an endurance percentage."
            )
            notes.append(f"Calculated endurance used: {result.tbw_used_percent:.2f}%.")
        else:
            basis = (
                "Estimated endurance remaining from device-reported wear because a "
                "model-specific rated TBW is unavailable."
            )
        if result.wear_percentage_used is not None:
            notes.append(f"Device-reported endurance used: {result.wear_percentage_used}%.")
    elif result.health == "FAILED":
        score = 0.0
        basis = "SMART overall-health assessment reports failure."
        notes.append("SMART reports this drive is failing; back up and replace it.")
    elif result.wear_percentage_used is not None:
        score = max(0.0, min(100.0, 100.0 - result.wear_percentage_used))
        basis = (
            "Estimated endurance remaining from device-reported SSD wear because "
            "a model-specific rated TBW is unavailable."
        )
        notes.append(f"Device-reported endurance used: {result.wear_percentage_used}%.")
    elif result.health == "PASSED":
        score = 100.0
        if result.drive_type == "hdd":
            basis = (
                "Estimated HDD reliability score from the strongest SMART sector "
                "indicator, corroborating counters, recent changes, and temperature. "
                "It is not the percentage of readable sectors."
            )
        else:
            basis = (
                "Heuristic from SMART overall status, available error counters, and "
                "temperature; this drive does not report a portable lifetime percentage."
            )
    else:
        score = 100.0
        if result.drive_type == "hdd":
            basis = (
                "Limited HDD reliability score from available sector indicators, "
                "recent changes, and temperature. It is not the percentage of readable sectors."
            )
        else:
            basis = (
                "Limited heuristic from the available error counters and temperature; "
                "SMART did not provide an overall status or lifetime percentage."
            )
        notes.append("SMART overall-health assessment is unavailable, so confidence is limited.")

    # HDD health is a reliability score, not good sectors divided by total
    # sectors. Use the strongest sector signal so related SMART attributes are
    # not fully counted multiple times, then add only small independent risks.
    hdd_trend_penalty = 0.0
    if result.health != "FAILED" and not endurance_based:
        if result.drive_type == "hdd":
            reallocated, pending, uncorrectable = _hdd_sector_counts(result)
            sector_risks = (
                _logarithmic_risk(reallocated, base=3, step=2, cap=20),
                _logarithmic_risk(pending, base=8, step=3, cap=30),
                _logarithmic_risk(uncorrectable, base=10, step=3, cap=35),
            )
            sector_risk = max(sector_risks)
            active_sector_indicators = sum(
                count > 0 for count in (reallocated, pending, uncorrectable)
            )
            corroboration_penalty = (
                10.0 if active_sector_indicators == 3
                else 5.0 if active_sector_indicators == 2
                else 0.0
            )
            hdd_trend_penalty, trend_note = _hdd_trend_penalty(result, previous)
            temperature_penalty = _hdd_temperature_penalty(result.temperature_c)
            score -= (
                sector_risk
                + corroboration_penalty
                + hdd_trend_penalty
                + temperature_penalty
            )

            if sector_risk:
                notes.append(
                    f"Strongest current sector indicator deducts {sector_risk:.1f} reliability points."
                )
            if corroboration_penalty:
                notes.append(
                    f"Multiple sector indicators deduct {corroboration_penalty:.0f} additional points."
                )
            if trend_note:
                notes.append(
                    f"{trend_note} Trend deduction: {hdd_trend_penalty:.0f} points."
                )
            if temperature_penalty:
                notes.append(
                    f"Current temperature ({result.temperature_c}°C) deducts "
                    f"{temperature_penalty:.0f} reliability points."
                )
        else:
            reallocated = result.reallocated_sectors or 0
            pending = result.pending_sectors or 0
            uncorrectable = max(
                result.uncorrectable_errors or 0,
                result.reported_uncorrectable_errors or 0,
                result.media_errors or 0,
            )
            score -= max(
                _logarithmic_risk(reallocated, base=3, step=2, cap=20),
                _logarithmic_risk(pending, base=8, step=3, cap=30),
                _logarithmic_risk(uncorrectable, base=10, step=3, cap=35),
            )

        if result.reallocated_sectors:
            notes.append(f"{result.reallocated_sectors} sector(s) have been reallocated.")
        if result.pending_sectors:
            notes.append(f"{result.pending_sectors} unstable sector(s) are pending reallocation.")
        if uncorrectable:
            notes.append(f"{uncorrectable} uncorrectable/media error(s) reported.")

        spare = result.available_spare_percent
        threshold = result.available_spare_threshold
        if spare is not None and threshold is not None and spare < threshold:
            score = min(score, 20)
            notes.append(f"Available spare ({spare}%) is below its {threshold}% threshold.")

        if result.drive_type != "hdd":
            temp = result.highest_temperature_c or result.temperature_c
            if temp is not None and temp >= 80:
                score -= 15
                notes.append(f"Current highest temperature ({temp}°C) is high for this drive type.")
            elif temp is not None and temp >= 70:
                score -= 5
                notes.append(
                    f"Current highest temperature ({temp}°C) is warmer than recommended."
                )

    critical_warning = result.critical_warning or 0
    if critical_warning:
        notes.append(f"NVMe critical-warning flags are set (0x{critical_warning:02x}).")

    spare_below_threshold = (
        result.available_spare_percent is not None
        and result.available_spare_threshold is not None
        and result.available_spare_percent < result.available_spare_threshold
    )
    if endurance_based and spare_below_threshold:
        notes.append(
            f"Available spare ({result.available_spare_percent}%) is below its "
            f"{result.available_spare_threshold}% threshold."
        )
    if endurance_based and result.media_errors:
        notes.append(f"{result.media_errors} media/data-integrity error(s) reported.")

    score = max(0.0, min(100.0, score))
    hottest = result.highest_temperature_c or result.temperature_c
    hdd_sector_counts = (
        _hdd_sector_counts(result) if result.drive_type == "hdd" else (0, 0, 0)
    )
    has_hdd_sector_warning = any(count > 0 for count in hdd_sector_counts)

    if result.health == "FAILED" or critical_warning or score < 30:
        assessment = "Critical"
    elif (
        (result.media_errors or 0) > 0
        or spare_below_threshold
        or score < 60
        or (result.drive_type == "hdd" and hdd_trend_penalty >= 15)
        or (result.drive_type == "hdd" and (hottest or 0) >= 60)
        or (result.drive_type != "hdd" and (hottest or 0) >= 80)
    ):
        assessment = "Warning"
    elif (
        score < 80
        or (result.drive_type == "hdd" and has_hdd_sector_warning)
        or (result.drive_type == "hdd" and hdd_trend_penalty > 0)
        or (result.drive_type == "hdd" and (hottest or 0) >= 55)
        or (result.drive_type != "hdd" and (hottest or 0) >= 70)
    ):
        assessment = "Attention"
    elif score < 95:
        assessment = "Good"
    else:
        assessment = "Excellent"

    if result.crc_errors:
        notes.append(
            f"{result.crc_errors} interface CRC error(s) reported; "
            "check the cable/backplane if increasing."
        )
    if result.error_log_entries and result.drive_type == "nvme":
        notes.append(
            "NVMe error-log entries are shown for diagnostics but are not treated "
            "as media failures or deducted from endurance."
        )
    if not notes:
        notes.append("No critical SMART indicators are currently reported.")

    result.health_percentage = round(score, 1)
    result.health_assessment = assessment
    result.health_basis = basis
    result.health_notes = notes


def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _scan_device(device: str) -> SmartResult:
    if not shutil.which("smartctl"):
        return SmartResult(device=device, error="smartctl not installed", last_checked=_iso_now())

    try:
        proc = await asyncio.create_subprocess_exec(
            *_smartctl_args(device),
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
            # smartctl exit bit 4 means the overall-health status is failing.
            # Feed it into calculation before the score and assessment are built.
            if rc & 16:
                data.setdefault("smart_status", {})["passed"] = False
            return _parse_json(data, device, previous=_cache.get(device))
        except (json.JSONDecodeError, Exception) as e:
            return SmartResult(device=device, error=f"parse error: {e}", last_checked=_iso_now())
    except asyncio.TimeoutError:
        return SmartResult(device=device, error="smartctl timed out", last_checked=_iso_now())
    except Exception as e:
        return SmartResult(device=device, error=str(e), last_checked=_iso_now())



def _smartctl_args(device: str) -> tuple[str, ...]:
    if re.match(r"^/dev/nvme\d+n\d+$", device):
        # "-a" includes the NVMe self-test log. Some controllers do not support
        # that optional command and record every poll as Invalid Field in
        # Command. Identity, overall health and the SMART/health log provide all
        # data CarbonPanel displays without issuing that unsupported request.
        return ("smartctl", "-H", "-A", "-i", "-j", device)
    return ("smartctl", "-a", "-j", device)


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
