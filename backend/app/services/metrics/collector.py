import asyncio
import time
from collections import deque

from app.core.broadcast import connection_manager
from app.schemas.metrics import HistoryPoint, MetricsSnapshot
from app.services.metrics import cpu, disk, gpu, memory, network, processes, system

_HISTORY_MAX = 300  # keep up to 5 minutes at 1s interval


class MetricsCollector:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._sort_by: str = "cpu"
        self._limit: int = 25
        self._interval: float = 2.0
        self.history: deque[HistoryPoint] = deque(maxlen=_HISTORY_MAX)

    def set_prefs(self, sort_by: str, limit: int) -> None:
        self._sort_by = sort_by
        self._limit = limit

    def set_interval(self, seconds: float) -> None:
        self._interval = max(0.4, min(30.0, seconds))

    def start(self) -> None:
        from app.config import settings
        self._interval = settings.metrics_interval_seconds
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while True:
            try:
                await self._collect_and_broadcast()
            except Exception:
                pass
            await asyncio.sleep(self._interval)

    async def _collect_and_broadcast(self) -> None:
        (
            cpu_data,
            mem_data,
            gpu_data,
            disk_data,
            net_data,
            proc_data,
            sys_data,
        ) = await asyncio.gather(
            cpu.collect(),
            memory.collect(),
            gpu.collect(),
            disk.collect(),
            network.collect(),
            processes.collect(sort_by=self._sort_by, limit=self._limit),
            system.collect(),
        )

        now = time.time()
        snapshot = MetricsSnapshot(
            ts=now,
            cpu=cpu_data,
            memory=mem_data,
            gpu=gpu_data,
            disks=disk_data,
            network=net_data,
            processes=proc_data,
            system=sys_data,
        )

        gpu_util = gpu_data.devices[0].utilization_percent if gpu_data.available and gpu_data.devices else None
        self.history.append(HistoryPoint(
            ts=now,
            cpu=cpu_data.aggregate,
            mem=mem_data.percent,
            gpu=gpu_util,
        ))

        await connection_manager.broadcast(snapshot.model_dump_json())


metrics_collector = MetricsCollector()
