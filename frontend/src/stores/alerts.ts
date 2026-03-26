import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MetricsSnapshot } from '@/types/metrics'

export interface Toast {
  id: number
  message: string
  level: 'warning' | 'danger'
}

export interface AlertThresholds {
  cpu: number
  ram: number
  disk: number
}

let nextId = 1
const COOLDOWN_MS = 30_000

export const useAlertsStore = defineStore('alerts', () => {
  const thresholds = ref<AlertThresholds>({
    cpu: parseInt(localStorage.getItem('cp_alert_cpu') ?? '0'),
    ram: parseInt(localStorage.getItem('cp_alert_ram') ?? '0'),
    disk: parseInt(localStorage.getItem('cp_alert_disk') ?? '0'),
  })

  const toasts = ref<Toast[]>([])
  const lastFired = ref<Record<string, number>>({})

  function setThreshold(key: keyof AlertThresholds, value: number) {
    thresholds.value[key] = value
    localStorage.setItem(`cp_alert_${key}`, String(value))
  }

  function fire(key: string, message: string, level: Toast['level']) {
    const now = Date.now()
    if (lastFired.value[key] && now - lastFired.value[key] < COOLDOWN_MS) return
    lastFired.value[key] = now
    const id = nextId++
    toasts.value.push({ id, message, level })
    setTimeout(() => dismiss(id), 5000)
  }

  function dismiss(id: number) {
    const idx = toasts.value.findIndex((t) => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  function check(snap: MetricsSnapshot) {
    const { cpu, ram, disk } = thresholds.value

    if (cpu > 0 && snap.cpu.aggregate >= cpu) {
      fire('cpu', `CPU usage ${snap.cpu.aggregate.toFixed(0)}% ≥ ${cpu}%`, cpu >= 90 ? 'danger' : 'warning')
    }
    if (ram > 0 && snap.memory.percent >= ram) {
      fire('ram', `RAM usage ${snap.memory.percent.toFixed(0)}% ≥ ${ram}%`, ram >= 90 ? 'danger' : 'warning')
    }
    if (disk > 0) {
      for (const d of snap.disks) {
        if (d.usage_percent >= disk) {
          fire(
            `disk_${d.mountpoint}`,
            `Disk ${d.mountpoint} at ${d.usage_percent.toFixed(0)}% ≥ ${disk}%`,
            disk >= 90 ? 'danger' : 'warning',
          )
        }
      }
    }
  }

  return { thresholds, toasts, setThreshold, dismiss, check }
})
