<template>
  <div class="log-viewer">
    <div class="log-toolbar">
      <span class="log-status">
        <span :class="['ws-dot', wsConnected ? 'dot-green' : 'dot-gray']" />
        {{ wsConnected ? 'live' : 'disconnected' }}
      </span>
      <span class="log-path">{{ logPath ?? 'no log path' }}</span>
      <div class="toolbar-actions">
        <button :class="['follow-btn', { active: follow }]" @click="follow = !follow">
          {{ follow ? '⬇ follow' : '⬇ follow' }}
        </button>
        <button class="clear-btn" @click="lines = []">clear</button>
      </div>
    </div>

    <div ref="containerEl" class="log-container" @scroll="onScroll">
      <pre class="log-pre"><span
        v-for="(line, i) in lines"
        :key="i"
        class="log-line"
      >{{ line }}
</span><span v-if="lines.length === 0" class="log-empty">{{ logPath ? 'waiting for output…' : 'no log paths configured for this site' }}</span></pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ siteId: string; logPath: string | null }>()

const auth = useAuthStore()
const lines = ref<string[]>([])
const follow = ref(true)
const wsConnected = ref(false)
const containerEl = ref<HTMLDivElement | null>(null)

let ws: WebSocket | null = null

function connect() {
  if (!props.logPath) return
  if (ws) ws.close()

  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${proto}//${location.host}/api/v1/sites/${props.siteId}/logs?token=${auth.token}`
  ws = new WebSocket(url)

  ws.onopen = () => { wsConnected.value = true }
  ws.onclose = () => { wsConnected.value = false }
  ws.onerror = () => { wsConnected.value = false }

  ws.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data)
      if (data.line !== undefined) {
        lines.value.push(data.line)
        if (lines.value.length > 500) {
          lines.value.splice(0, lines.value.length - 500)
        }
        if (follow.value) {
          nextTick(() => scrollToBottom())
        }
      }
    } catch { /* ignore */ }
  }
}

function scrollToBottom() {
  const el = containerEl.value
  if (el) el.scrollTop = el.scrollHeight
}

function onScroll() {
  const el = containerEl.value
  if (!el) return
  const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 20
  if (!atBottom) follow.value = false
}

onMounted(() => connect())
onUnmounted(() => ws?.close())

watch(() => props.siteId, () => {
  lines.value = []
  connect()
})
</script>

<style scoped>
.log-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 300px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.log-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card);
  flex-shrink: 0;
}

.ws-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.dot-green { background: var(--accent); box-shadow: 0 0 4px var(--accent); }
.dot-gray  { background: var(--fg-dim); }

.log-status { display: flex; align-items: center; gap: 5px; font-size: 10px; color: var(--fg-muted); flex-shrink: 0; }
.log-path { font-size: 10px; color: var(--fg-dim); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.toolbar-actions { display: flex; gap: 6px; flex-shrink: 0; }

.follow-btn, .clear-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-dim);
  font-family: var(--font);
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 3px;
  cursor: pointer;
  transition: all var(--transition);
}
.follow-btn:hover, .clear-btn:hover { color: var(--fg); border-color: var(--fg-dim); }
.follow-btn.active { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }

.log-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
  padding: 8px 10px;
}

.log-pre {
  margin: 0;
  font-family: var(--font);
  font-size: 11px;
  color: var(--accent);
  line-height: 1.6;
  white-space: pre;
}

.log-line { display: block; }
.log-empty { color: var(--fg-dim); font-style: italic; }
</style>
