import asyncio
import time

import psutil

from app.schemas.metrics import NetworkMetrics

_MB = 1024 * 1024

_prev_counters: dict = {}
_prev_time: float = 0.0


async def collect() -> list[NetworkMetrics]:
    global _prev_counters, _prev_time

    loop = asyncio.get_event_loop()
    counters = await loop.run_in_executor(None, lambda: psutil.net_io_counters(pernic=True))

    now = time.monotonic()
    dt = now - _prev_time if _prev_time else 1.0

    results: list[NetworkMetrics] = []
    for iface, stats in counters.items():
        if iface == "lo":
            continue
        # Skip interfaces with no traffic at all
        if stats.bytes_recv == 0 and stats.bytes_sent == 0:
            continue

        rx_rate = 0.0
        tx_rate = 0.0
        if iface in _prev_counters:
            prev = _prev_counters[iface]
            rx_rate = max(0.0, (stats.bytes_recv - prev.bytes_recv) / dt / _MB)
            tx_rate = max(0.0, (stats.bytes_sent - prev.bytes_sent) / dt / _MB)

        _prev_counters[iface] = stats

        results.append(NetworkMetrics(
            interface=iface,
            rx_mb_s=rx_rate,
            tx_mb_s=tx_rate,
            rx_total_mb=stats.bytes_recv / _MB,
            tx_total_mb=stats.bytes_sent / _MB,
        ))

    _prev_time = now
    return results
