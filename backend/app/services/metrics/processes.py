import asyncio

import psutil

from app.schemas.metrics import ProcessMetrics

_MB = 1024 * 1024


def _collect_sync(sort_by: str, limit: int) -> list[ProcessMetrics]:
    procs: list[ProcessMetrics] = []
    attrs = ["pid", "name", "cpu_percent", "memory_info", "status", "username"]
    for proc in psutil.process_iter(attrs):
        try:
            info = proc.info
            procs.append(ProcessMetrics(
                pid=info["pid"],
                name=info["name"] or "",
                cpu_percent=info["cpu_percent"] or 0.0,
                memory_mb=(info["memory_info"].rss / _MB) if info["memory_info"] else 0.0,
                status=info["status"] or "",
                user=info["username"] or "",
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    key = "memory_mb" if sort_by == "memory" else "cpu_percent"
    procs.sort(key=lambda p: getattr(p, key), reverse=True)
    return procs[:limit]


async def collect(sort_by: str = "cpu", limit: int = 25) -> list[ProcessMetrics]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _collect_sync, sort_by, limit)
