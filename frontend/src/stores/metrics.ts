import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MetricsSnapshot } from '@/types/metrics'

const HISTORY_LEN = 60

function pushRing(arr: number[], val: number): number[] {
  const next = [...arr, val]
  if (next.length > HISTORY_LEN) next.shift()
  return next
}

export const useMetricsStore = defineStore('metrics', () => {
  const latest = ref<MetricsSnapshot | null>(null)
  const connected = ref(false)

  const cpuHistory = ref<number[]>([])
  const memHistory = ref<number[]>([])
  const gpuHistory = ref<number[]>([])
  const netRxHistory = ref<Record<string, number[]>>({})
  const netTxHistory = ref<Record<string, number[]>>({})

  const processSort = ref<'cpu' | 'memory'>('cpu')
  const processLimit = ref(25)

  const updateInterval = ref<number>(
    parseFloat(localStorage.getItem('cp_interval') ?? '2'),
  )

  function setUpdateInterval(seconds: number) {
    const clamped = Math.max(0.4, Math.min(30, seconds))
    updateInterval.value = clamped
    localStorage.setItem('cp_interval', String(clamped))
  }

  function handleSnapshot(snapshot: MetricsSnapshot) {
    latest.value = snapshot
    cpuHistory.value = pushRing(cpuHistory.value, snapshot.cpu.aggregate)
    memHistory.value = pushRing(memHistory.value, snapshot.memory.percent)

    if (snapshot.gpu.available && snapshot.gpu.devices.length > 0) {
      gpuHistory.value = pushRing(gpuHistory.value, snapshot.gpu.devices[0].utilization_percent)
    }

    for (const iface of snapshot.network) {
      if (!netRxHistory.value[iface.interface]) netRxHistory.value[iface.interface] = []
      if (!netTxHistory.value[iface.interface]) netTxHistory.value[iface.interface] = []
      netRxHistory.value[iface.interface] = pushRing(netRxHistory.value[iface.interface], iface.rx_mb_s)
      netTxHistory.value[iface.interface] = pushRing(netTxHistory.value[iface.interface], iface.tx_mb_s)
    }
  }

  function setConnected(v: boolean) {
    connected.value = v
  }

  return {
    latest,
    connected,
    cpuHistory,
    memHistory,
    gpuHistory,
    netRxHistory,
    netTxHistory,
    processSort,
    processLimit,
    updateInterval,
    setUpdateInterval,
    handleSnapshot,
    setConnected,
  }
})
