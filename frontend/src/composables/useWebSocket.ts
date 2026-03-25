import { onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useMetricsStore } from '@/stores/metrics'
import type { MetricsSnapshot } from '@/types/metrics'
import router from '@/router'

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || ''

export function useWebSocket() {
  const auth = useAuthStore()
  const metrics = useMetricsStore()
  let ws: WebSocket | null = null
  let retryDelay = 1000
  let retryTimer: ReturnType<typeof setTimeout> | null = null
  let stopped = false

  function connect() {
    if (!auth.token) return
    const wsBase = WS_BASE || `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`
    ws = new WebSocket(`${wsBase}/ws?token=${auth.token}`)

    ws.onopen = () => {
      metrics.setConnected(true)
      retryDelay = 1000
      // Sync saved interval to backend on (re)connect
      sendInterval(metrics.updateInterval)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'metrics') {
          metrics.handleSnapshot(data as MetricsSnapshot)
        } else if (data.type === 'error' && data.code === 'auth_failed') {
          auth.logout()
          router.push('/login')
        }
      } catch {
        // ignore parse errors
      }
    }

    ws.onclose = (event) => {
      metrics.setConnected(false)
      if (stopped) return
      if (event.code === 4001) {
        auth.logout()
        router.push('/login')
        return
      }
      retryTimer = setTimeout(() => {
        retryDelay = Math.min(retryDelay * 2, 30000)
        connect()
      }, retryDelay)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function disconnect() {
    stopped = true
    if (retryTimer) clearTimeout(retryTimer)
    ws?.close()
    metrics.setConnected(false)
  }

  function sendPrefs(sort: 'cpu' | 'memory', limit: number) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'set_prefs', process_sort: sort, process_limit: limit }))
    }
  }

  function sendInterval(seconds: number) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'set_interval', seconds }))
    }
  }

  onUnmounted(disconnect)

  return { connect, disconnect, sendPrefs, sendInterval, connected: metrics.connected }
}
