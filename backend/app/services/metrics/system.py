import asyncio
import socket
import shutil
import time
from datetime import datetime

import psutil

from app.schemas.metrics import SystemMetrics


def _host_info() -> tuple[float, bool]:
    # Detect installation without contacting the daemon or invoking sudo.
    return psutil.boot_time(), shutil.which("docker") is not None


async def collect() -> SystemMetrics:
    loop = asyncio.get_event_loop()
    boot_time, docker_installed = await loop.run_in_executor(None, _host_info)
    hostname = socket.gethostname()

    # astimezone() on a naive now() resolves the machine's configured zone,
    # which is what a client needs to render the server's wall clock rather
    # than re-rendering the same instant in its own zone.
    local_now = datetime.now().astimezone()
    offset = local_now.utcoffset()

    return SystemMetrics(
        hostname=hostname,
        docker_installed=docker_installed,
        uptime_seconds=time.time() - boot_time,
        boot_time_ts=boot_time,
        timezone=local_now.tzname() or "",
        utc_offset_seconds=int(offset.total_seconds()) if offset else 0,
    )
