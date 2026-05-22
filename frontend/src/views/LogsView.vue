<template>
  <div class="logs-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('logs.title') }}</h1>
        <p class="page-subtitle">
          <span :class="['ws-dot', wsState === 'connected' ? 'dot-on' : wsState === 'connecting' ? 'dot-warn' : 'dot-off']" />
          {{ wsState === 'connected' ? t('logs.connected') : wsState === 'connecting' ? t('logs.connecting') : t('logs.disconnected') }}
          · {{ lines.length }} {{ t('logs.lines') }}
        </p>
      </div>
      <div class="header-actions">
        <select v-model="selectedSource" class="source-select" @change="reconnect">
          <option v-for="(label, key) in sourcesMap" :key="key" :value="key">{{ label }}</option>
          <option value="__custom">{{ t('logs.sources.custom') }}</option>
        </select>
        <input
          v-if="selectedSource === '__custom'"
          v-model="customPath"
          class="custom-input"
          placeholder="/var/log/..."
          @keydown.enter="reconnect"
        />
        <button class="hdr-btn" @click="paused = !paused">{{ paused ? t('logs.resume') : t('logs.pause') }}</button>
        <button class="hdr-btn" @click="lines = []">{{ t('logs.clear') }}</button>
      </div>
    </div>

    <div ref="termEl" class="terminal">
      <div v-for="(line, i) in lines" :key="i" class="log-line" :class="lineClass(line)">{{ line }}</div>
      <div v-if="!lines.length" class="empty-hint">{{ t('common.loading') }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useLocaleStore } from '@/stores/locale'

const { t } = useLocaleStore()
const auth = useAuthStore()

const sourcesMap: Record<string, string> = {
  journalctl: t('logs.sources.journalctl'),
  syslog:     t('logs.sources.syslog'),
  auth:       t('logs.sources.auth'),
  kern:       t('logs.sources.kern'),
}

const selectedSource = ref('journalctl')
const customPath = ref('')
const lines = ref<string[]>([])
const paused = ref(false)
const wsState = ref<'connecting' | 'connected' | 'disconnected'>('connecting')
const termEl = ref<HTMLElement | null>(null)

let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

const activeSource = computed(() =>
  selectedSource.value === '__custom' ? customPath.value : selectedSource.value,
)

function buildUrl(): string {
  const base = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/^http/, 'ws').replace('/api/v1', '')
  return `${base}/ws/logs?token=${auth.token}&source=${encodeURIComponent(activeSource.value)}`
}

function connect() {
  if (ws) { ws.onclose = null; ws.close() }
  wsState.value = 'connecting'
  ws = new WebSocket(buildUrl())

  ws.onopen = () => { wsState.value = 'connected' }
  ws.onclose = () => {
    wsState.value = 'disconnected'
    reconnectTimer = setTimeout(connect, 3000)
  }
  ws.onerror = () => { wsState.value = 'disconnected' }
  ws.onmessage = (ev) => {
    if (paused.value) return
    try {
      const msg = JSON.parse(ev.data as string)
      if (msg.type === 'line') {
        lines.value.push(msg.text)
        if (lines.value.length > 2000) lines.value.splice(0, 500)
        nextTick(() => {
          if (termEl.value) termEl.value.scrollTop = termEl.value.scrollHeight
        })
      }
    } catch { /* ignore */ }
  }
}

function reconnect() {
  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
  lines.value = []
  connect()
}

function lineClass(line: string) {
  const l = line.toLowerCase()
  if (l.includes('error') || l.includes('fatal') || l.includes('crit')) return 'line-error'
  if (l.includes('warn')) return 'line-warn'
  return ''
}

onMounted(connect)
onUnmounted(() => {
  if (reconnectTimer) clearTimeout(reconnectTimer)
  if (ws) { ws.onclose = null; ws.close() }
})
</script>

<style scoped>
.logs-page { padding: 20px; display: flex; flex-direction: column; gap: 14px; height: 100%; overflow: hidden; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; flex-wrap: wrap; flex-shrink: 0; }
.page-title { font-size: 16px; font-weight: 700; }
.page-subtitle { font-size: 11px; color: var(--fg-muted); margin-top: 4px; display: flex; align-items: center; gap: 6px; }

.ws-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.dot-on   { background: var(--accent); box-shadow: 0 0 5px var(--accent); }
.dot-warn { background: var(--warning); }
.dot-off  { background: var(--fg-dim); animation: blink 1.2s ease infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.2} }

.header-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.source-select {
  background: var(--bg-input); border: 1px solid var(--border); color: var(--fg);
  font-family: var(--font); font-size: 11px; padding: 6px 10px; border-radius: var(--radius-sm);
  outline: none; cursor: pointer;
}
.source-select:focus { border-color: var(--accent-border); }
.custom-input {
  background: var(--bg-input); border: 1px solid var(--border); color: var(--fg);
  font-family: var(--font); font-size: 11px; padding: 6px 10px; border-radius: var(--radius-sm);
  outline: none; width: 200px;
}
.custom-input:focus { border-color: var(--accent-border); }
.hdr-btn {
  background: none; border: 1px solid var(--border); color: var(--fg-muted);
  font-family: var(--font); font-size: 11px; padding: 5px 12px;
  border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition);
}
.hdr-btn:hover { border-color: var(--accent-border); color: var(--accent); }

.terminal {
  flex: 1; overflow-y: auto; background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 10px 14px; font-family: var(--font); font-size: 11px;
  line-height: 1.6; color: var(--fg-muted); white-space: pre-wrap; word-break: break-all;
}
.log-line { padding: 1px 0; }
.line-error { color: var(--danger); }
.line-warn  { color: var(--warning); }
.empty-hint { color: var(--fg-dim); font-style: italic; }
</style>
