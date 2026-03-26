import asyncio
import time

import psutil

from app.schemas.metrics import DiskMetrics

_MB = 1024 * 1024
_GB = 1024 * 1024 * 1024

_prev_counters: dict = {}
_prev_time: float = 0.0


async def collect() -> list[DiskMetrics]:
    global _prev_counters, _prev_time

    loop = asyncio.get_event_loop()

    partitions, io_counters = await asyncio.gather(
        loop.run_in_executor(None, lambda: psutil.disk_partitions(all=False)),
        loop.run_in_executor(None, lambda: psutil.disk_io_counters(perdisk=True)),
    )

    now = time.monotonic()
    dt = now - _prev_time if _prev_time else 1.0

    results: list[DiskMetrics] = []
    for p in partitions:
        try:
            usage = await loop.run_in_executor(None, lambda mp=p.mountpoint: psutil.disk_usage(mp))
        except PermissionError:
            continue

        # Derive the base device name for matching io_counters keys
        dev = p.device.replace("/dev/", "")
        # Strip partition number to get disk name (e.g. sda1 -> sda)
        io_key = next(
            (k for k in (io_counters or {}) if dev.startswith(k) or k.startswith(dev)),
            dev,
        )
        io = (io_counters or {}).get(io_key)

        read_rate = 0.0
        write_rate = 0.0
        if io and io_key in _prev_counters:
            prev = _prev_counters[io_key]
            read_rate = max(0.0, (io.read_bytes - prev.read_bytes) / dt / _MB)
            write_rate = max(0.0, (io.write_bytes - prev.write_bytes) / dt / _MB)

        if io:
            _prev_counters[io_key] = io

        results.append(
            DiskMetrics(
                device=p.device,
                mountpoint=p.mountpoint,
                usage_percent=usage.percent,
                used_gb=usage.used / _GB,
                total_gb=usage.total / _GB,
                read_mb_s=read_rate,
                write_mb_s=write_rate,
            )
        )

    _prev_time = now
    return results
