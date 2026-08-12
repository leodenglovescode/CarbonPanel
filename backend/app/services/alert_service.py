import json
import time
from dataclasses import dataclass, field

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user_preferences import UserPreferences
from app.schemas.metrics import DiskMetrics, MetricsSnapshot
from app.services import webhook_service

_RETRY_COOLDOWN_SECONDS = 30.0
_CONFIG_REFRESH_SECONDS = 5.0
_VIRTUAL_MOUNT_PREFIXES = ("/snap", "/proc", "/sys", "/run", "/dev")
_RULE_KEYS = ("cpu", "ram", "disk", "gpuUsage", "gpuTemp", "networkRx", "networkTx")
_DEFAULT_SEVERITIES = {
    "cpu": "warning",
    "ram": "warning",
    "disk": "warning",
    "gpuUsage": "warning",
    "gpuTemp": "critical",
    "networkRx": "warning",
    "networkTx": "warning",
}
_SEVERITY_RANK = {"info": 0, "warning": 1, "critical": 2}


@dataclass(frozen=True)
class AlertConfig:
    cpu: float = 0
    ram: float = 0
    disk: float = 0
    gpu_usage: float = 0
    gpu_temp: float = 0
    network_rx: float = 0
    network_tx: float = 0
    disk_scope: str = "physical"
    severities: dict[str, str] = field(
        default_factory=lambda: dict(_DEFAULT_SEVERITIES)
    )

    def severity(self, key: str) -> str:
        return self.severities.get(key, _DEFAULT_SEVERITIES.get(key, "warning"))


def _is_physical_disk(disk: DiskMetrics) -> bool:
    if not disk.device.startswith("/dev/"):
        return False
    base_device = disk.device.removeprefix("/dev/")
    if base_device.startswith(("loop", "ram", "zram", "fd")):
        return False
    if disk.mountpoint in ("/boot", "/boot/efi"):
        return True
    return not any(
        disk.mountpoint == prefix or disk.mountpoint.startswith(f"{prefix}/")
        for prefix in _VIRTUAL_MOUNT_PREFIXES
    )


def _config_from_preferences(rows: list[UserPreferences]) -> AlertConfig:
    alert_sets: list[dict] = []
    for row in rows:
        try:
            alerts = json.loads(row.prefs_json).get("alerts")
        except (TypeError, ValueError):
            continue
        if isinstance(alerts, dict):
            alert_sets.append(alerts)

    def lowest_enabled(key: str) -> float:
        values: list[float] = []
        for alerts in alert_sets:
            try:
                value = float(alerts.get(key, 0))
            except (TypeError, ValueError):
                continue
            if value > 0:
                values.append(value)
        return min(values, default=0)

    severities = dict(_DEFAULT_SEVERITIES)
    for key in _RULE_KEYS:
        configured = [
            str(alerts.get("severities", {}).get(key, "")).lower()
            for alerts in alert_sets
            if isinstance(alerts.get("severities"), dict)
        ]
        valid = [value for value in configured if value in _SEVERITY_RANK]
        if valid:
            severities[key] = max(valid, key=_SEVERITY_RANK.__getitem__)

    return AlertConfig(
        cpu=lowest_enabled("cpu"),
        ram=lowest_enabled("ram"),
        disk=lowest_enabled("disk"),
        gpu_usage=lowest_enabled("gpuUsage"),
        gpu_temp=lowest_enabled("gpuTemp"),
        network_rx=lowest_enabled("networkRx"),
        network_tx=lowest_enabled("networkTx"),
        disk_scope=(
            "all"
            if any(alerts.get("diskScope") == "all" for alerts in alert_sets)
            else "physical"
        ),
        severities=severities,
    )


class AlertEvaluator:
    def __init__(self) -> None:
        self._active: set[str] = set()
        self._last_attempt: dict[str, float] = {}
        self._config = AlertConfig()
        self._config_loaded_at = 0.0

    async def _load_config(self) -> AlertConfig:
        now = time.monotonic()
        if now - self._config_loaded_at < _CONFIG_REFRESH_SECONDS:
            return self._config
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(UserPreferences))
            self._config = _config_from_preferences(list(result.scalars().all()))
        self._config_loaded_at = now
        return self._config

    async def _evaluate(
        self,
        *,
        key: str,
        breached: bool,
        event: str,
        metric: str,
        label: str,
        value: float,
        threshold: float,
        unit: str,
        severity: str,
        message: str,
    ) -> None:
        if not breached:
            self._active.discard(key)
            return
        if key in self._active:
            return

        now = time.monotonic()
        if now - self._last_attempt.get(key, 0) < _RETRY_COOLDOWN_SECONDS:
            return
        self._last_attempt[key] = now

        async with AsyncSessionLocal() as db:
            results = await webhook_service.fire_event(
                db,
                event,
                {
                    "metric": metric,
                    "label": label,
                    "value": value,
                    "threshold": threshold,
                    "unit": unit,
                    "severity": severity,
                    "message": message,
                },
            )
        if any(result.success for result in results):
            self._active.add(key)

    def _discard_missing(self, prefix: str, present: set[str]) -> None:
        self._active.difference_update(
            key for key in self._active if key.startswith(prefix) and key not in present
        )

    async def check(self, snapshot: MetricsSnapshot | None) -> None:
        if snapshot is None:
            return
        config = await self._load_config()

        await self._evaluate(
            key="cpu",
            breached=config.cpu > 0 and snapshot.cpu.aggregate >= config.cpu,
            event="alert.cpu",
            metric="cpu",
            label="CPU usage",
            value=snapshot.cpu.aggregate,
            threshold=config.cpu,
            unit="%",
            severity=config.severity("cpu"),
            message=(
                f"CPU usage {snapshot.cpu.aggregate:.0f}% is at or above "
                f"{config.cpu:.0f}%."
            ),
        )
        await self._evaluate(
            key="ram",
            breached=config.ram > 0 and snapshot.memory.percent >= config.ram,
            event="alert.ram",
            metric="ram",
            label="RAM usage",
            value=snapshot.memory.percent,
            threshold=config.ram,
            unit="%",
            severity=config.severity("ram"),
            message=(
                f"RAM usage {snapshot.memory.percent:.0f}% is at or above "
                f"{config.ram:.0f}%."
            ),
        )

        disks = (
            snapshot.disks
            if config.disk_scope == "all"
            else [disk for disk in snapshot.disks if _is_physical_disk(disk)]
        )
        disk_keys = {f"disk:{disk.mountpoint}" for disk in disks}
        self._discard_missing("disk:", disk_keys)
        for disk in disks:
            await self._evaluate(
                key=f"disk:{disk.mountpoint}",
                breached=config.disk > 0 and disk.usage_percent >= config.disk,
                event="alert.disk",
                metric=f"disk:{disk.mountpoint}",
                label=f"Disk {disk.mountpoint} usage",
                value=disk.usage_percent,
                threshold=config.disk,
                unit="%",
                severity=config.severity("disk"),
                message=(
                    f"Disk {disk.mountpoint} usage {disk.usage_percent:.0f}% is at or above "
                    f"{config.disk:.0f}%."
                ),
            )

        gpu_devices = snapshot.gpu.devices if snapshot.gpu.available else []
        gpu_usage_keys = {f"gpu-usage:{device.index}" for device in gpu_devices}
        gpu_temp_keys = {f"gpu-temp:{device.index}" for device in gpu_devices}
        self._discard_missing("gpu-usage:", gpu_usage_keys)
        self._discard_missing("gpu-temp:", gpu_temp_keys)
        for device in gpu_devices:
            await self._evaluate(
                key=f"gpu-usage:{device.index}",
                breached=(
                    config.gpu_usage > 0
                    and device.utilization_percent >= config.gpu_usage
                ),
                event="alert.gpu",
                metric=f"gpu:{device.index}",
                label=f"GPU {device.index} utilization",
                value=device.utilization_percent,
                threshold=config.gpu_usage,
                unit="%",
                severity=config.severity("gpuUsage"),
                message=(
                    f"GPU {device.index} ({device.name}) utilization "
                    f"{device.utilization_percent:.0f}% is at or above "
                    f"{config.gpu_usage:.0f}%."
                ),
            )
            await self._evaluate(
                key=f"gpu-temp:{device.index}",
                breached=(
                    config.gpu_temp > 0 and device.temperature_c >= config.gpu_temp
                ),
                event="alert.gpu_temperature",
                metric=f"gpu-temperature:{device.index}",
                label=f"GPU {device.index} temperature",
                value=device.temperature_c,
                threshold=config.gpu_temp,
                unit="°C",
                severity=config.severity("gpuTemp"),
                message=(
                    f"GPU {device.index} ({device.name}) temperature "
                    f"{device.temperature_c:.0f}°C is at or above "
                    f"{config.gpu_temp:.0f}°C."
                ),
            )

        rx_keys = {f"network-rx:{item.interface}" for item in snapshot.network}
        tx_keys = {f"network-tx:{item.interface}" for item in snapshot.network}
        self._discard_missing("network-rx:", rx_keys)
        self._discard_missing("network-tx:", tx_keys)
        for item in snapshot.network:
            await self._evaluate(
                key=f"network-rx:{item.interface}",
                breached=config.network_rx > 0 and item.rx_mb_s >= config.network_rx,
                event="alert.network_rx",
                metric=f"network-rx:{item.interface}",
                label=f"{item.interface} receive throughput",
                value=item.rx_mb_s,
                threshold=config.network_rx,
                unit="MB/s",
                severity=config.severity("networkRx"),
                message=(
                    f"Network {item.interface} receive throughput {item.rx_mb_s:.2f} MB/s "
                    f"is at or above {config.network_rx:.2f} MB/s."
                ),
            )
            await self._evaluate(
                key=f"network-tx:{item.interface}",
                breached=config.network_tx > 0 and item.tx_mb_s >= config.network_tx,
                event="alert.network_tx",
                metric=f"network-tx:{item.interface}",
                label=f"{item.interface} transmit throughput",
                value=item.tx_mb_s,
                threshold=config.network_tx,
                unit="MB/s",
                severity=config.severity("networkTx"),
                message=(
                    f"Network {item.interface} transmit throughput {item.tx_mb_s:.2f} MB/s "
                    f"is at or above {config.network_tx:.2f} MB/s."
                ),
            )


alert_evaluator = AlertEvaluator()
