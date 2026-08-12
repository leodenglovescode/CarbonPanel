import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MetricsSnapshot } from '@/types/metrics'

export type AlertSeverity = 'info' | 'warning' | 'critical'

export interface Toast {
  id: number
  message: string
  level: 'info' | 'warning' | 'danger'
}

export interface AlertThresholds {
  cpu: number
  ram: number
  disk: number
  gpuUsage: number
  gpuTemp: number
  networkRx: number
  networkTx: number
}

export type AlertRuleKey = keyof AlertThresholds
export type DiskAlertScope = 'physical' | 'all'

const DISK_ALERT_SCOPE_STORAGE_KEY = 'cp_alert_disk_scope'
const VIRTUAL_MOUNT_PREFIXES = ['/snap', '/proc', '/sys', '/run', '/dev']
const RULE_KEYS: AlertRuleKey[] = [
  'cpu',
  'ram',
  'disk',
  'gpuUsage',
  'gpuTemp',
  'networkRx',
  'networkTx',
]
const DEFAULT_SEVERITIES: Record<AlertRuleKey, AlertSeverity> = {
  cpu: 'warning',
  ram: 'warning',
  disk: 'warning',
  gpuUsage: 'warning',
  gpuTemp: 'critical',
  networkRx: 'warning',
  networkTx: 'warning',
}

function storedNumber(key: AlertRuleKey) {
  const value = Number.parseFloat(localStorage.getItem(`cp_alert_${key}`) ?? '0')
  return Number.isFinite(value) && value >= 0 ? value : 0
}

function storedSeverity(key: AlertRuleKey): AlertSeverity {
  const value = localStorage.getItem(`cp_alert_severity_${key}`)
  return value === 'info' || value === 'warning' || value === 'critical'
    ? value
    : DEFAULT_SEVERITIES[key]
}

function isPhysicalDiskMetric(device: string, mountpoint: string) {
  if (!device.startsWith('/dev/')) return false
  const baseDevice = device.replace('/dev/', '')
  if (
    baseDevice.startsWith('loop') ||
    baseDevice.startsWith('ram') ||
    baseDevice.startsWith('zram') ||
    baseDevice.startsWith('fd')
  ) {
    return false
  }
  if (mountpoint === '/boot' || mountpoint === '/boot/efi') return true
  return !VIRTUAL_MOUNT_PREFIXES.some(
    (prefix) => mountpoint === prefix || mountpoint.startsWith(`${prefix}/`),
  )
}

function toastLevel(severity: AlertSeverity): Toast['level'] {
  if (severity === 'critical') return 'danger'
  return severity
}

let nextId = 1
const COOLDOWN_MS = 30_000

export const useAlertsStore = defineStore('alerts', () => {
  const thresholds = ref<AlertThresholds>({
    cpu: storedNumber('cpu'),
    ram: storedNumber('ram'),
    disk: storedNumber('disk'),
    gpuUsage: storedNumber('gpuUsage'),
    gpuTemp: storedNumber('gpuTemp'),
    networkRx: storedNumber('networkRx'),
    networkTx: storedNumber('networkTx'),
  })
  const severities = ref<Record<AlertRuleKey, AlertSeverity>>(
    Object.fromEntries(
      RULE_KEYS.map((key) => [key, storedSeverity(key)]),
    ) as Record<AlertRuleKey, AlertSeverity>,
  )
  const diskScope = ref<DiskAlertScope>(
    localStorage.getItem(DISK_ALERT_SCOPE_STORAGE_KEY) === 'all' ? 'all' : 'physical',
  )

  const toasts = ref<Toast[]>([])
  const lastFired = ref<Record<string, number>>({})

  function setThreshold(key: AlertRuleKey, value: number) {
    const normalized = Number.isFinite(value) ? Math.max(0, value) : 0
    thresholds.value[key] = normalized
    localStorage.setItem(`cp_alert_${key}`, String(normalized))
  }

  function setSeverity(key: AlertRuleKey, value: AlertSeverity) {
    severities.value[key] = value
    localStorage.setItem(`cp_alert_severity_${key}`, value)
  }

  function setDiskScope(value: DiskAlertScope) {
    diskScope.value = value
    localStorage.setItem(DISK_ALERT_SCOPE_STORAGE_KEY, value)
  }

  function fire(key: string, message: string, severity: AlertSeverity) {
    const now = Date.now()
    if (lastFired.value[key] && now - lastFired.value[key] < COOLDOWN_MS) return
    lastFired.value[key] = now
    const id = nextId++
    toasts.value.push({ id, message, level: toastLevel(severity) })
    setTimeout(() => dismiss(id), 5000)
  }

  function dismiss(id: number) {
    const idx = toasts.value.findIndex((toast) => toast.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  function check(snap: MetricsSnapshot) {
    const values = thresholds.value

    if (values.cpu > 0 && snap.cpu.aggregate >= values.cpu) {
      fire(
        'cpu',
        `CPU usage ${snap.cpu.aggregate.toFixed(0)}% ≥ ${values.cpu}%`,
        severities.value.cpu,
      )
    }
    if (values.ram > 0 && snap.memory.percent >= values.ram) {
      fire(
        'ram',
        `RAM usage ${snap.memory.percent.toFixed(0)}% ≥ ${values.ram}%`,
        severities.value.ram,
      )
    }
    if (values.disk > 0) {
      const disks =
        diskScope.value === 'all'
          ? snap.disks
          : snap.disks.filter((disk) =>
              isPhysicalDiskMetric(disk.device, disk.mountpoint),
            )
      for (const disk of disks) {
        if (disk.usage_percent >= values.disk) {
          fire(
            `disk_${disk.mountpoint}`,
            `Disk ${disk.mountpoint} at ${disk.usage_percent.toFixed(0)}% ≥ ${values.disk}%`,
            severities.value.disk,
          )
        }
      }
    }

    if (snap.gpu.available) {
      for (const gpu of snap.gpu.devices) {
        if (values.gpuUsage > 0 && gpu.utilization_percent >= values.gpuUsage) {
          fire(
            `gpu_usage_${gpu.index}`,
            `GPU ${gpu.index} utilization ${gpu.utilization_percent.toFixed(0)}% ≥ ${values.gpuUsage}%`,
            severities.value.gpuUsage,
          )
        }
        if (values.gpuTemp > 0 && gpu.temperature_c >= values.gpuTemp) {
          fire(
            `gpu_temp_${gpu.index}`,
            `GPU ${gpu.index} temperature ${gpu.temperature_c.toFixed(0)}°C ≥ ${values.gpuTemp}°C`,
            severities.value.gpuTemp,
          )
        }
      }
    }

    for (const network of snap.network) {
      if (values.networkRx > 0 && network.rx_mb_s >= values.networkRx) {
        fire(
          `network_rx_${network.interface}`,
          `${network.interface} receive ${network.rx_mb_s.toFixed(2)} MB/s ≥ ${values.networkRx} MB/s`,
          severities.value.networkRx,
        )
      }
      if (values.networkTx > 0 && network.tx_mb_s >= values.networkTx) {
        fire(
          `network_tx_${network.interface}`,
          `${network.interface} transmit ${network.tx_mb_s.toFixed(2)} MB/s ≥ ${values.networkTx} MB/s`,
          severities.value.networkTx,
        )
      }
    }
  }

  function loadFromDb(data: {
    cpu?: number
    ram?: number
    disk?: number
    gpuUsage?: number
    gpuTemp?: number
    networkRx?: number
    networkTx?: number
    diskScope?: string
    severities?: Partial<Record<AlertRuleKey, AlertSeverity>>
  }) {
    for (const key of RULE_KEYS) {
      const value = data[key]
      if (typeof value === 'number') setThreshold(key, value)
      const severity = data.severities?.[key]
      if (severity === 'info' || severity === 'warning' || severity === 'critical') {
        setSeverity(key, severity)
      }
    }
    if (data.diskScope === 'physical' || data.diskScope === 'all') {
      setDiskScope(data.diskScope)
    }
  }

  return {
    thresholds,
    severities,
    diskScope,
    toasts,
    setThreshold,
    setSeverity,
    setDiskScope,
    dismiss,
    check,
    loadFromDb,
  }
})
