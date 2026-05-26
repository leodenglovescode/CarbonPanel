import asyncio

import psutil

from app.schemas.metrics import CpuMetrics, CpuTemp

_cpu_name_cache: str = ""


def _get_cpu_name() -> str:
    global _cpu_name_cache
    if _cpu_name_cache:
        return _cpu_name_cache
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    _cpu_name_cache = line.split(":", 1)[1].strip()
                    return _cpu_name_cache
    except Exception:
        pass
    _cpu_name_cache = "Unknown CPU"
    return _cpu_name_cache


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

    per_core, aggregate, freq, load, temps, cpu_name = await asyncio.gather(
        loop.run_in_executor(None, lambda: psutil.cpu_percent(percpu=True)),
        loop.run_in_executor(None, lambda: psutil.cpu_percent(percpu=False)),
        loop.run_in_executor(None, psutil.cpu_freq),
        loop.run_in_executor(None, psutil.getloadavg),
        loop.run_in_executor(None, _collect_temps),
        loop.run_in_executor(None, _get_cpu_name),
    )

    return CpuMetrics(
        aggregate=aggregate,
        per_core=per_core,
        load_avg=list(load),
        frequency_mhz=freq.current if freq else 0.0,
        temps=temps,
        cpu_name=cpu_name,
    )
