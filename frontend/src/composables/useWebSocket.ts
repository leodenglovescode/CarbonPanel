import { useAuthStore } from '@/stores/auth'
import { useMetricsStore } from '@/stores/metrics'
import { useAlertsStore } from '@/stores/alerts'
import type { MetricsSnapshot } from '@/types/metrics'
import router from '@/router'

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || ''

let ws: WebSocket | null = null
let retryDelay = 1000
let retryTimer: ReturnType<typeof setTimeout> | null = null
let stopped = true

function connect() {
  const auth = useAuthStore()
  const metrics = useMetricsStore()
  const alertsStore = useAlertsStore()

  if (!auth.isAuthenticated) return
  if (ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) return

  stopped = false
  if (retryTimer) {
    clearTimeout(retryTimer)
    retryTimer = null
  }

  const wsBase = WS_BASE || (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host
  // No token in the URL — the browser attaches the httpOnly session cookie
  // to the WS handshake automatically.
  const socket = new WebSocket(wsBase + '/ws')
  ws = socket

  socket.onopen = () => {
    if (ws !== socket) return
    metrics.setConnected(true)
    retryDelay = 1000
    sendInterval(metrics.updateInterval)
  }

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'metrics') {
        const snap = data as MetricsSnapshot
        metrics.handleSnapshot(snap)
        alertsStore.check(snap)
      } else if (data.type === 'error' && data.code === 'auth_failed') {
        auth.logout()
        router.push('/login')
      }
    } catch {
      // ignore parse errors
    }
  }

  socket.onclose = (event) => {
    if (ws !== socket) return
    ws = null
    metrics.setConnected(false)
    if (stopped) return
    if (event.code === 4001) {
      auth.logout()
      router.push('/login')
      return
    }
    retryTimer = setTimeout(() => {
      retryTimer = null
      retryDelay = Math.min(retryDelay * 2, 30000)
      connect()
    }, retryDelay)
  }

  socket.onerror = () => {
    socket.close()
  }
}

function disconnect() {
  const metrics = useMetricsStore()
  stopped = true
  if (retryTimer) {
    clearTimeout(retryTimer)
    retryTimer = null
  }
  const socket = ws
  ws = null
  socket?.close()
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

export function useWebSocket() {
  return { connect, disconnect, sendPrefs, sendInterval }
}
