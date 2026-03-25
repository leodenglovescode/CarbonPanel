import asyncio

import psutil

from app.schemas.metrics import MemoryMetrics

_MB = 1024 * 1024


async def collect() -> MemoryMetrics:
    loop = asyncio.get_event_loop()

    vm, swap = await asyncio.gather(
        loop.run_in_executor(None, psutil.virtual_memory),
        loop.run_in_executor(None, psutil.swap_memory),
    )

    return MemoryMetrics(
        total_mb=vm.total / _MB,
        used_mb=vm.used / _MB,
        free_mb=vm.available / _MB,
        percent=vm.percent,
        swap_total_mb=swap.total / _MB,
        swap_used_mb=swap.used / _MB,
    )
