export interface CpuMetrics {
  aggregate: number
  per_core: number[]
  load_avg: number[]
  frequency_mhz: number
}

export interface MemoryMetrics {
  total_mb: number
  used_mb: number
  free_mb: number
  percent: number
  swap_total_mb: number
  swap_used_mb: number
}

export interface GpuDevice {
  index: number
  name: string
  utilization_percent: number
  memory_used_mb: number
  memory_total_mb: number
  temperature_c: number
  power_draw_w: number
}

export interface GpuMetrics {
  available: boolean
  devices: GpuDevice[]
}

export interface DiskMetrics {
  device: string
  mountpoint: string
  usage_percent: number
  used_gb: number
  total_gb: number
  read_mb_s: number
  write_mb_s: number
}

export interface NetworkMetrics {
  interface: string
  rx_mb_s: number
  tx_mb_s: number
  rx_total_mb: number
  tx_total_mb: number
}

export interface ProcessMetrics {
  pid: number
  name: string
  cpu_percent: number
  memory_mb: number
  status: string
  user: string
}

export interface SystemMetrics {
  hostname: string
  uptime_seconds: number
  boot_time_ts: number
}

export interface MetricsSnapshot {
  type: 'metrics'
  ts: number
  cpu: CpuMetrics
  memory: MemoryMetrics
  gpu: GpuMetrics
  disks: DiskMetrics[]
  network: NetworkMetrics[]
  processes: ProcessMetrics[]
  system: SystemMetrics
}
