import asyncio

from app.schemas.metrics import GpuDevice, GpuMetrics


async def collect() -> GpuMetrics:
    try:
        proc = await asyncio.create_subprocess_exec(
            "nvidia-smi",
            "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
    except (FileNotFoundError, asyncio.TimeoutError, OSError):
        return GpuMetrics(available=False)

    devices: list[GpuDevice] = []
    for line in stdout.decode().strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 7:
            continue
        try:
            devices.append(GpuDevice(
                index=int(parts[0]),
                name=parts[1],
                utilization_percent=float(parts[2]),
                memory_used_mb=float(parts[3]),
                memory_total_mb=float(parts[4]),
                temperature_c=float(parts[5]),
                power_draw_w=float(parts[6]) if parts[6] not in ("N/A", "[N/A]") else 0.0,
            ))
        except (ValueError, IndexError):
            continue

    return GpuMetrics(available=bool(devices), devices=devices)
