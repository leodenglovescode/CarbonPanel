import asyncio

import psutil

from app.schemas.metrics import CpuMetrics


async def collect() -> CpuMetrics:
    loop = asyncio.get_event_loop()

    per_core, aggregate, freq, load = await asyncio.gather(
        loop.run_in_executor(None, lambda: psutil.cpu_percent(percpu=True)),
        loop.run_in_executor(None, lambda: psutil.cpu_percent(percpu=False)),
        loop.run_in_executor(None, psutil.cpu_freq),
        loop.run_in_executor(None, psutil.getloadavg),
    )

    return CpuMetrics(
        aggregate=aggregate,
        per_core=per_core,
        load_avg=list(load),
        frequency_mhz=freq.current if freq else 0.0,
    )
