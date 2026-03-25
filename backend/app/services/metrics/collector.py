import asyncio
import time

from app.core.broadcast import connection_manager
from app.schemas.metrics import MetricsSnapshot
from app.services.metrics import cpu, disk, gpu, memory, network, processes, system


class MetricsCollector:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._sort_by: str = "cpu"
        self._limit: int = 25
        self._interval: float = 2.0

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

        snapshot = MetricsSnapshot(
            ts=time.time(),
            cpu=cpu_data,
            memory=mem_data,
            gpu=gpu_data,
            disks=disk_data,
            network=net_data,
            processes=proc_data,
            system=sys_data,
        )

        await connection_manager.broadcast(snapshot.model_dump_json())


metrics_collector = MetricsCollector()
