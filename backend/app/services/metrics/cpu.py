import asyncio

import psutil

from app.schemas.metrics import CpuMetrics, CpuTemp


def _collect_temps() -> list[CpuTemp]:
    try:
        raw = psutil.sensors_temperatures()
    except (AttributeError, OSError):
        return []
    if not raw:
        return []
    result: list[CpuTemp] = []
    for sensor_name, readings in raw.items():
        for r in readings:
            result.append(CpuTemp(
                sensor=sensor_name,
                label=r.label or sensor_name,
                temp_c=r.current,
                high_c=r.high if r.high else None,
                critical_c=r.critical if r.critical else None,
            ))
    return result


async def collect() -> CpuMetrics:
    loop = asyncio.get_event_loop()

    per_core, aggregate, freq, load, temps = await asyncio.gather(
        loop.run_in_executor(None, lambda: psutil.cpu_percent(percpu=True)),
        loop.run_in_executor(None, lambda: psutil.cpu_percent(percpu=False)),
        loop.run_in_executor(None, psutil.cpu_freq),
        loop.run_in_executor(None, psutil.getloadavg),
        loop.run_in_executor(None, _collect_temps),
    )

    return CpuMetrics(
        aggregate=aggregate,
        per_core=per_core,
        load_avg=list(load),
        frequency_mhz=freq.current if freq else 0.0,
        temps=temps,
    )
