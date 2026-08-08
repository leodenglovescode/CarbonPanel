import asyncio
import time
from collections import deque
from dataclasses import dataclass
from threading import Lock

from app.core.broadcast import connection_manager
from app.core.dependencies import is_jti_revoked
from app.schemas.metrics import (
    CpuMetrics,
    DiskMetrics,
    GpuMetrics,
    HistoryPoint,
    MemoryMetrics,
    MetricsSnapshot,
    NetworkMetrics,
    ProcessMetrics,
    SystemMetrics,
)
from app.services.metrics import cpu, disk, gpu, memory, network, processes, system

_HISTORY_MAX = 300  # keep up to 5 minutes at 1s interval

# Bounds on what any client may ask for.
_MIN_INTERVAL = 0.4
_MAX_INTERVAL = 30.0

# Floor for the expensive collectors. gpu.collect() forks an nvidia-smi
# subprocess and processes.collect_all() walks every PID; running either at a
# 0.4s cadence would make the panel a meaningful share of the load it exists to
# report. Phones want a live CPU/RAM trace, not a 400ms-fresh process table, so
# the two tiers are decoupled.
_SLOW_TIER_INTERVAL = 2.0

# An HTTP polling client has no connection to hang prefs off, so it re-asserts
# its desired interval on each request and we forget it once it stops asking.
_HTTP_CLIENT_TTL = 15.0


@dataclass
class ClientPrefs:
    interval: float = 2.0
    sort_by: str = "cpu"
    limit: int = 25
    # Token id behind this connection, so a revoked session can be dropped
    # mid-stream rather than streaming on until its token expires.
    jti: str = ""


class MetricsCollector:
    """Collects system metrics on a shared loop and fans them out to clients.

    Interval and process-sort preferences are tracked *per client*. Previously
    both were single fields on this singleton that any WebSocket could
    overwrite, so two browser tabs with different settings silently fought over
    one another — and a phone polling slowly would have dragged the desktop
    dashboard down with it.
    """

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._default_interval: float = 2.0
        self._lock = Lock()

        # key -> prefs. WebSocket clients key on the socket object; HTTP
        # pollers key on a caller-supplied string.
        self._ws_clients: dict[object, ClientPrefs] = {}
        self._http_clients: dict[str, tuple[ClientPrefs, float]] = {}

        self.history: deque[HistoryPoint] = deque(maxlen=_HISTORY_MAX)

        # Latest collected values. Fast tier refreshes every cycle; slow tier
        # is reused between refreshes so a snapshot is always complete.
        self._ts: float = 0.0
        self._cpu: CpuMetrics | None = None
        self._memory: MemoryMetrics | None = None
        self._network: list[NetworkMetrics] = []
        self._disks: list[DiskMetrics] = []
        self._gpu: GpuMetrics | None = None
        self._system: SystemMetrics | None = None
        self._processes: list[ProcessMetrics] = []
        self._slow_ts: float = 0.0

    # ── client registration ────────────────────────────────────────────────

    def register_ws(self, key: object, jti: str = "") -> ClientPrefs:
        prefs = ClientPrefs(interval=self._default_interval, jti=jti)
        with self._lock:
            self._ws_clients[key] = prefs
        return prefs

    def unregister_ws(self, key: object) -> None:
        with self._lock:
            self._ws_clients.pop(key, None)

    def set_prefs(self, key: object, sort_by: str | None = None, limit: int | None = None) -> None:
        with self._lock:
            prefs = self._ws_clients.get(key)
            if prefs is None:
                return
            if sort_by is not None:
                prefs.sort_by = "memory" if sort_by == "memory" else "cpu"
            if limit is not None:
                prefs.limit = max(1, min(500, int(limit)))

    def set_interval(self, key: object, seconds: float) -> None:
        with self._lock:
            prefs = self._ws_clients.get(key)
            if prefs is not None:
                prefs.interval = _clamp_interval(seconds)

    def note_http_client(
        self,
        key: str,
        interval: float | None = None,
        sort_by: str | None = None,
        limit: int | None = None,
    ) -> ClientPrefs:
        """Record an HTTP poller's preferences and keep the loop awake for it.

        Entries lapse after _HTTP_CLIENT_TTL, so a phone that backgrounds (and
        simply stops polling) stops influencing the collection rate on its own
        without needing to announce that it left.
        """
        prefs = ClientPrefs(
            interval=_clamp_interval(interval) if interval else self._default_interval,
            sort_by="memory" if sort_by == "memory" else "cpu",
            limit=max(1, min(500, int(limit))) if limit else 25,
        )
        with self._lock:
            self._http_clients[key] = (prefs, time.monotonic())
        return prefs

    def _live_prefs(self) -> list[ClientPrefs]:
        now = time.monotonic()
        with self._lock:
            for k in [k for k, (_, seen) in self._http_clients.items()
                      if now - seen >= _HTTP_CLIENT_TTL]:
                del self._http_clients[k]
            return (
                list(self._ws_clients.values())
                + [p for p, _ in self._http_clients.values()]
            )

    def effective_interval(self) -> float:
        """Fastest cadence any live client has asked for."""
        intervals = [p.interval for p in self._live_prefs()]
        if not intervals:
            return self._default_interval
        return _clamp_interval(min(intervals))

    # ── snapshot ───────────────────────────────────────────────────────────

    @property
    def ready(self) -> bool:
        return self._cpu is not None and self._memory is not None

    def snapshot(self, sort_by: str = "cpu", limit: int = 25) -> MetricsSnapshot | None:
        """Build a snapshot from the latest collected values.

        Cheap: reads cached data and ranks the process list. Never collects, so
        it is safe to call on a request path at any rate.
        """
        if self._cpu is None or self._memory is None:
            return None
        return MetricsSnapshot(
            ts=self._ts,
            cpu=self._cpu,
            memory=self._memory,
            gpu=self._gpu or GpuMetrics(available=False),
            disks=self._disks,
            network=self._network,
            processes=processes.rank(self._processes, sort_by, limit),
            system=self._system or SystemMetrics(hostname="", uptime_seconds=0.0, boot_time_ts=0.0),
        )

    # ── loop ───────────────────────────────────────────────────────────────

    def start(self) -> None:
        from app.config import settings
        self._default_interval = _clamp_interval(settings.metrics_interval_seconds)
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while True:
            started = time.monotonic()
            try:
                await self._collect()
                await self._broadcast()
            except Exception:
                pass
            # Subtract the time collection took, so the cadence is the
            # requested interval rather than interval-plus-work.
            elapsed = time.monotonic() - started
            await asyncio.sleep(max(0.05, self.effective_interval() - elapsed))

    async def _collect(self) -> None:
        now_m = time.monotonic()
        need_slow = self._slow_ts == 0.0 or (now_m - self._slow_ts) >= _SLOW_TIER_INTERVAL

        fast = asyncio.gather(cpu.collect(), memory.collect(), network.collect())

        if need_slow:
            slow = asyncio.gather(
                disk.collect(), gpu.collect(), processes.collect_all(), system.collect()
            )
            (cpu_d, mem_d, net_d), (disk_d, gpu_d, proc_d, sys_d) = await asyncio.gather(fast, slow)
            self._disks = disk_d
            self._gpu = gpu_d
            self._processes = proc_d
            self._system = sys_d
            self._slow_ts = now_m
        else:
            cpu_d, mem_d, net_d = await fast

        self._cpu = cpu_d
        self._memory = mem_d
        self._network = net_d
        self._ts = time.time()

        gpu_util = (
            self._gpu.devices[0].utilization_percent
            if self._gpu and self._gpu.available and self._gpu.devices
            else None
        )
        self.history.append(HistoryPoint(
            ts=self._ts,
            cpu=cpu_d.aggregate,
            mem=mem_d.percent,
            gpu=gpu_util,
        ))

    async def _broadcast(self) -> None:
        if not connection_manager.active:
            return
        with self._lock:
            targets = [(ws, self._ws_clients.get(ws)) for ws in list(connection_manager.active)]

        # Clients that agree on sort order and limit share one serialisation —
        # model_dump_json over the process list is the expensive part here.
        payloads: dict[tuple[str, int], str] = {}
        for ws, prefs in targets:
            prefs = prefs or ClientPrefs(interval=self._default_interval)
            # The broadcast loop already visits every connection each tick, so
            # it is the cheapest place to enforce revocation on sockets that
            # are already open.
            if prefs.jti and is_jti_revoked(prefs.jti):
                self.unregister_ws(ws)
                await connection_manager.close(ws, code=4001)
                continue
            cache_key = (prefs.sort_by, prefs.limit)
            payload = payloads.get(cache_key)
            if payload is None:
                snap = self.snapshot(prefs.sort_by, prefs.limit)
                if snap is None:
                    return
                payload = snap.model_dump_json()
                payloads[cache_key] = payload
            await connection_manager.send_to(ws, payload)


def _clamp_interval(seconds: float) -> float:
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return 2.0
    return max(_MIN_INTERVAL, min(_MAX_INTERVAL, value))


metrics_collector = MetricsCollector()
