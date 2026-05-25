<template>
  <div class="sessions-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('sessions.title') }}</h1>
        <p class="page-subtitle">{{ sessions.length }} active</p>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="load">
        {{ loading ? t('common.refreshing') : t('common.refresh') }}
      </button>
    </div>

    <div v-if="loading" class="state-msg">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="state-msg error">{{ error }}</div>
    <div v-else-if="!sessions.length" class="state-msg muted">{{ t('sessions.noSessions') }}</div>

    <div v-else class="sessions-list">
      <div v-for="(s, i) in sessions" :key="i" class="session-card">
        <div class="session-top">
          <span class="session-user">{{ s.user }}</span>
          <span class="session-tty">{{ s.tty }}</span>
          <span v-if="s.from_host !== '-' && s.from_host" class="session-from">from {{ s.from_host }}</span>
        </div>
        <div class="session-meta">
          <span class="meta-item"><span class="meta-lbl">{{ t('sessions.loginTime') }}</span> {{ s.login_time }}</span>
          <span class="meta-item"><span class="meta-lbl">{{ t('sessions.idle') }}</span> {{ s.idle }}</span>
          <span class="meta-item cmd"><span class="meta-lbl">{{ t('sessions.command') }}</span> <code>{{ s.command }}</code></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/index'
import { useLocaleStore } from '@/stores/locale'

const { t } = useLocaleStore()

interface SessionInfo { user: string; tty: string; from_host: string; login_time: string; idle: string; cpu_time: string; command: string }
const sessions = ref<SessionInfo[]>([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get<SessionInfo[]>('/sessions')
    sessions.value = data
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to load sessions'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.sessions-page { padding: 20px; display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.page-title { font-size: 16px; font-weight: 700; }
.page-subtitle { font-size: 11px; color: var(--fg-muted); margin-top: 2px; }
.refresh-btn { background: none; border: 1px solid var(--border); color: var(--fg-muted); font-family: var(--font); font-size: 11px; padding: 5px 12px; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); }
.refresh-btn:hover:not(:disabled) { border-color: var(--accent-border); color: var(--accent); }
.refresh-btn:disabled { opacity: 0.5; cursor: default; }
.state-msg { font-size: 12px; color: var(--fg-muted); padding: 20px 0; text-align: center; }
.state-msg.error { color: var(--danger); }
.state-msg.muted { color: var(--fg-dim); }

.sessions-list { display: flex; flex-direction: column; gap: 8px; }
.session-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 16px; display: flex; flex-direction: column; gap: 8px; }
.session-top { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.session-user { font-size: 13px; font-weight: 600; color: var(--accent); }
.session-tty { font-size: 11px; color: var(--fg-muted); font-family: monospace; }
.session-from { font-size: 11px; color: var(--fg-dim); }
.session-meta { display: flex; gap: 16px; flex-wrap: wrap; }
.meta-item { font-size: 11px; color: var(--fg); display: flex; gap: 5px; align-items: baseline; }
.meta-lbl { font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg-dim); }
.meta-item.cmd { flex: 1; min-width: 200px; }
.meta-item code { font-size: 11px; color: var(--fg-muted); word-break: break-all; }

@media (max-width: 640px) {
  .sessions-page { padding: 12px; gap: 10px; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 8px; }
  .session-meta { gap: 10px; }
  .meta-item.cmd { min-width: unset; }
}
</style>
