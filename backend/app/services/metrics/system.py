import asyncio
import socket
import time

import psutil

from app.schemas.metrics import SystemMetrics


async def collect() -> SystemMetrics:
    loop = asyncio.get_event_loop()
    boot_time = await loop.run_in_executor(None, psutil.boot_time)
    hostname = socket.gethostname()

    return SystemMetrics(
        hostname=hostname,
        uptime_seconds=time.time() - boot_time,
        boot_time_ts=boot_time,
    )
