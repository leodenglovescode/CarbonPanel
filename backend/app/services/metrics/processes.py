import asyncio

import psutil

from app.schemas.metrics import ProcessMetrics

_MB = 1024 * 1024


def _collect_sync() -> list[ProcessMetrics]:
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
    return procs


def rank(procs: list[ProcessMetrics], sort_by: str, limit: int) -> list[ProcessMetrics]:
    """Sort and truncate an already-collected process list.

    Split out from collection so one process_iter sweep can serve clients that
    disagree about sort order — walking every PID once per connected client
    would be the single most expensive thing the collector does.
    """
    key = "memory_mb" if sort_by == "memory" else "cpu_percent"
    return sorted(procs, key=lambda p: getattr(p, key), reverse=True)[:limit]


async def collect_all() -> list[ProcessMetrics]:
    """Every process, unsorted. Callers rank it themselves via rank()."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _collect_sync)


async def collect(sort_by: str = "cpu", limit: int = 25) -> list[ProcessMetrics]:
    return rank(await collect_all(), sort_by, limit)
