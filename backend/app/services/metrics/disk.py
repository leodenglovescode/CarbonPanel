import asyncio
import os
import time
from pathlib import Path

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
        except OSError:
            continue

        # Resolve /dev/mapper aliases to dm-N. Match exactly so md1/dm-1
        # cannot accidentally pick md10/dm-10 (or a physical member disk).
        dev = os.path.basename(os.path.realpath(p.device))
        io_key = dev
        if dev not in (io_counters or {}):
            block = Path('/sys/class/block') / dev
            if (block / 'partition').exists():
                io_key = block.resolve().parent.name
        io = (io_counters or {}).get(io_key)

        read_rate = 0.0
        write_rate = 0.0
        if io and io_key in _prev_counters:
            prev = _prev_counters[io_key]
            read_rate = max(0.0, (io.read_bytes - prev.read_bytes) / dt / _MB)
            write_rate = max(0.0, (io.write_bytes - prev.write_bytes) / dt / _MB)

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

    _prev_counters = io_counters or {}
    _prev_time = now
    return results
