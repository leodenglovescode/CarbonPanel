from pydantic import BaseModel


class CpuMetrics(BaseModel):
    aggregate: float
    per_core: list[float]
    load_avg: list[float]
    frequency_mhz: float


class MemoryMetrics(BaseModel):
    total_mb: float
    used_mb: float
    free_mb: float
    percent: float
    swap_total_mb: float
    swap_used_mb: float


class GpuDevice(BaseModel):
    index: int
    name: str
    utilization_percent: float
    memory_used_mb: float
    memory_total_mb: float
    temperature_c: float
    power_draw_w: float


class GpuMetrics(BaseModel):
    available: bool
    devices: list[GpuDevice] = []


class DiskMetrics(BaseModel):
    device: str
    mountpoint: str
    usage_percent: float
    used_gb: float
    total_gb: float
    read_mb_s: float
    write_mb_s: float


class NetworkMetrics(BaseModel):
    interface: str
    rx_mb_s: float
    tx_mb_s: float
    rx_total_mb: float
    tx_total_mb: float


class ProcessMetrics(BaseModel):
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    status: str
    user: str


class SystemMetrics(BaseModel):
    hostname: str
    uptime_seconds: float
    boot_time_ts: float


class MetricsSnapshot(BaseModel):
    type: str = "metrics"
    ts: float
    cpu: CpuMetrics
    memory: MemoryMetrics
    gpu: GpuMetrics
    disks: list[DiskMetrics]
    network: list[NetworkMetrics]
    processes: list[ProcessMetrics]
    system: SystemMetrics
