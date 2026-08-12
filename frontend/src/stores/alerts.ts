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
export type AlertDurations = Record<AlertRuleKey, number>
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
const DEFAULT_DURATION_SECONDS = 10
const MAX_DURATION_SECONDS = 86_400
const RULE_INSTANCE_PREFIXES: Record<AlertRuleKey, string> = {
  cpu: 'cpu',
  ram: 'ram',
  disk: 'disk_',
  gpuUsage: 'gpu_usage_',
  gpuTemp: 'gpu_temp_',
  networkRx: 'network_rx_',
  networkTx: 'network_tx_',
}

function storedNumber(key: AlertRuleKey) {
  const value = Number.parseFloat(localStorage.getItem(`cp_alert_${key}`) ?? '0')
  return Number.isFinite(value) && value >= 0 ? value : 0
}

function storedDuration(key: AlertRuleKey) {
  const value = Number.parseFloat(
    localStorage.getItem(`cp_alert_duration_${key}`) ?? String(DEFAULT_DURATION_SECONDS),
  )
  return Number.isFinite(value)
    ? Math.min(MAX_DURATION_SECONDS, Math.max(0, value))
    : DEFAULT_DURATION_SECONDS
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
  const durations = ref<AlertDurations>(
    Object.fromEntries(
      RULE_KEYS.map((key) => [key, storedDuration(key)]),
    ) as AlertDurations,
  )
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
  const breachedSince = ref<Record<string, number>>({})

  function ruleInstanceMatches(rule: AlertRuleKey, instanceKey: string) {
    const prefix = RULE_INSTANCE_PREFIXES[rule]
    return rule === 'cpu' || rule === 'ram'
      ? instanceKey === prefix
      : instanceKey.startsWith(prefix)
  }

  function resetRuleState(key: AlertRuleKey) {
    for (const instanceKey of Object.keys(breachedSince.value)) {
      if (ruleInstanceMatches(key, instanceKey)) delete breachedSince.value[instanceKey]
    }
    for (const instanceKey of Object.keys(lastFired.value)) {
      if (ruleInstanceMatches(key, instanceKey)) delete lastFired.value[instanceKey]
    }
  }

  function setThreshold(key: AlertRuleKey, value: number) {
    const normalized = Number.isFinite(value) ? Math.max(0, value) : 0
    if (thresholds.value[key] !== normalized) resetRuleState(key)
    thresholds.value[key] = normalized
    localStorage.setItem(`cp_alert_${key}`, String(normalized))
  }

  function setDuration(key: AlertRuleKey, value: number) {
    const normalized = Number.isFinite(value)
      ? Math.min(MAX_DURATION_SECONDS, Math.max(0, value))
      : DEFAULT_DURATION_SECONDS
    if (durations.value[key] !== normalized) resetRuleState(key)
    durations.value[key] = normalized
    localStorage.setItem(`cp_alert_duration_${key}`, String(normalized))
  }

  function setSeverity(key: AlertRuleKey, value: AlertSeverity) {
    severities.value[key] = value
    localStorage.setItem(`cp_alert_severity_${key}`, value)
  }

  function setDiskScope(value: DiskAlertScope) {
    if (diskScope.value !== value) resetRuleState('disk')
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

  function isSustained(key: string, breached: boolean, durationSeconds: number) {
    if (!breached) {
      delete breachedSince.value[key]
      return false
    }
    const now = Date.now()
    const startedAt = breachedSince.value[key] ?? now
    breachedSince.value[key] = startedAt
    return now - startedAt >= durationSeconds * 1000
  }

  function discardMissing(prefix: string, present: Set<string>) {
    for (const key of Object.keys(breachedSince.value)) {
      if (key.startsWith(prefix) && !present.has(key)) delete breachedSince.value[key]
    }
  }

  function durationSuffix(key: AlertRuleKey) {
    const duration = durations.value[key]
    return duration > 0 ? ` for ${duration}s` : ''
  }

  function check(snap: MetricsSnapshot) {
    const values = thresholds.value

    if (isSustained('cpu', values.cpu > 0 && snap.cpu.aggregate >= values.cpu, durations.value.cpu)) {
      fire(
        'cpu',
        `CPU usage ${snap.cpu.aggregate.toFixed(0)}% ≥ ${values.cpu}%${durationSuffix('cpu')}`,
        severities.value.cpu,
      )
    }
    if (isSustained('ram', values.ram > 0 && snap.memory.percent >= values.ram, durations.value.ram)) {
      fire(
        'ram',
        `RAM usage ${snap.memory.percent.toFixed(0)}% ≥ ${values.ram}%${durationSuffix('ram')}`,
        severities.value.ram,
      )
    }
    const disks =
      diskScope.value === 'all'
        ? snap.disks
        : snap.disks.filter((disk) =>
            isPhysicalDiskMetric(disk.device, disk.mountpoint),
          )
    const diskKeys = new Set(disks.map((disk) => `disk_${disk.mountpoint}`))
    discardMissing('disk_', diskKeys)
    for (const disk of disks) {
      const key = `disk_${disk.mountpoint}`
      if (isSustained(
        key,
        values.disk > 0 && disk.usage_percent >= values.disk,
        durations.value.disk,
      )) {
        fire(
          key,
          `Disk ${disk.mountpoint} at ${disk.usage_percent.toFixed(0)}% ≥ ${values.disk}%${durationSuffix('disk')}`,
          severities.value.disk,
        )
      }
    }

    const gpuDevices = snap.gpu.available ? snap.gpu.devices : []
    const gpuUsageKeys = new Set(gpuDevices.map((gpu) => `gpu_usage_${gpu.index}`))
    const gpuTempKeys = new Set(gpuDevices.map((gpu) => `gpu_temp_${gpu.index}`))
    discardMissing('gpu_usage_', gpuUsageKeys)
    discardMissing('gpu_temp_', gpuTempKeys)
    for (const gpu of gpuDevices) {
      const usageKey = `gpu_usage_${gpu.index}`
      if (isSustained(
        usageKey,
        values.gpuUsage > 0 && gpu.utilization_percent >= values.gpuUsage,
        durations.value.gpuUsage,
      )) {
        fire(
          usageKey,
          `GPU ${gpu.index} utilization ${gpu.utilization_percent.toFixed(0)}% ≥ ${values.gpuUsage}%${durationSuffix('gpuUsage')}`,
          severities.value.gpuUsage,
        )
      }
      const tempKey = `gpu_temp_${gpu.index}`
      if (isSustained(
        tempKey,
        values.gpuTemp > 0 && gpu.temperature_c >= values.gpuTemp,
        durations.value.gpuTemp,
      )) {
        fire(
          tempKey,
          `GPU ${gpu.index} temperature ${gpu.temperature_c.toFixed(0)}°C ≥ ${values.gpuTemp}°C${durationSuffix('gpuTemp')}`,
          severities.value.gpuTemp,
        )
      }
    }

    const networkRxKeys = new Set(snap.network.map((item) => `network_rx_${item.interface}`))
    const networkTxKeys = new Set(snap.network.map((item) => `network_tx_${item.interface}`))
    discardMissing('network_rx_', networkRxKeys)
    discardMissing('network_tx_', networkTxKeys)
    for (const network of snap.network) {
      const rxKey = `network_rx_${network.interface}`
      if (isSustained(
        rxKey,
        values.networkRx > 0 && network.rx_mb_s >= values.networkRx,
        durations.value.networkRx,
      )) {
        fire(
          rxKey,
          `${network.interface} receive ${network.rx_mb_s.toFixed(2)} MB/s ≥ ${values.networkRx} MB/s${durationSuffix('networkRx')}`,
          severities.value.networkRx,
        )
      }
      const txKey = `network_tx_${network.interface}`
      if (isSustained(
        txKey,
        values.networkTx > 0 && network.tx_mb_s >= values.networkTx,
        durations.value.networkTx,
      )) {
        fire(
          txKey,
          `${network.interface} transmit ${network.tx_mb_s.toFixed(2)} MB/s ≥ ${values.networkTx} MB/s${durationSuffix('networkTx')}`,
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
    durations?: Partial<AlertDurations>
  }) {
    for (const key of RULE_KEYS) {
      const value = data[key]
      if (typeof value === 'number') setThreshold(key, value)
      const duration = data.durations?.[key]
      if (typeof duration === 'number') setDuration(key, duration)
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
    durations,
    severities,
    diskScope,
    toasts,
    setThreshold,
    setDuration,
    setSeverity,
    setDiskScope,
    dismiss,
    check,
    loadFromDb,
  }
})
