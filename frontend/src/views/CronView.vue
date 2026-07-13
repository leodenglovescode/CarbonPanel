<template>
  <div class="cron-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('cron.title') }}</h1>
        <p class="page-subtitle">{{ entries.length }} job{{ entries.length !== 1 ? 's' : '' }}</p>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="load">
        {{ loading ? t('common.refreshing') : t('common.refresh') }}
      </button>
    </div>

    <div v-if="loading" class="state-msg">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="state-msg error">{{ error }}</div>
    <div v-else-if="!entries.length" class="state-msg muted">{{ t('cron.noJobs') }}</div>

    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{{ t('cron.source') }}</th>
            <th>{{ t('cron.user') }}</th>
            <th>{{ t('cron.schedule') }}</th>
            <th>{{ t('cron.command') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(e, i) in entries" :key="i">
            <td class="source-cell">{{ shortSource(e.source) }}</td>
            <td class="user-cell">{{ e.user }}</td>
            <td class="schedule-cell"><code>{{ e.schedule }}</code></td>
            <td class="cmd-cell"><code>{{ e.command }}</code></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '@/api/index'
import { useLocaleStore } from '@/stores/locale'

const { t } = useLocaleStore()

interface CronEntry { source: string; user: string; schedule: string; command: string }
const entries = ref<CronEntry[]>([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get<CronEntry[]>('/cron')
    entries.value = data
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to load cron jobs'
  } finally {
    loading.value = false
  }
}

function shortSource(s: string) {
  const parts = s.split('/')
  return parts[parts.length - 1] || s
}

onMounted(load)
</script>

<style scoped>
.cron-page { padding: 20px; display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.page-title { font-size: 16px; font-weight: 700; }
.page-subtitle { font-size: 11px; color: var(--fg-muted); margin-top: 2px; }
.refresh-btn { background: none; border: 1px solid var(--border); color: var(--fg-muted); font-family: var(--font); font-size: 11px; padding: 5px 12px; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); }
.refresh-btn:hover:not(:disabled) { border-color: var(--accent-border); color: var(--accent); }
.refresh-btn:disabled { opacity: 0.5; cursor: default; }
.state-msg { font-size: 12px; color: var(--fg-muted); padding: 20px 0; text-align: center; }
.state-msg.error { color: var(--danger); }
.state-msg.muted { color: var(--fg-dim); }

.table-wrap { overflow-x: auto; background: color-mix(in srgb, var(--bg-card) 72%, transparent); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); border: 1px solid var(--border); border-radius: var(--radius); }
table { width: 100%; border-collapse: collapse; }
thead th { font-size: 9px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--fg-dim); padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border-subtle); }
tbody tr:nth-child(even) { background: var(--bg-stripe); }
tbody tr:hover { background: var(--bg-hover); }
tbody td { font-size: 11px; padding: 8px 14px; color: var(--fg); border-bottom: 1px solid var(--border-row); }
tbody tr:last-child td { border-bottom: none; }

.source-cell { color: var(--fg-muted); max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-cell { color: var(--fg-muted); white-space: nowrap; }
.schedule-cell code { font-size: 11px; color: var(--accent); background: var(--accent-dim); padding: 2px 6px; border-radius: 3px; white-space: nowrap; }
.cmd-cell { max-width: 380px; }
.cmd-cell code { font-size: 11px; color: var(--fg); word-break: break-all; }

@media (max-width: 640px) {
  .cron-page { padding: 12px; gap: 10px; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 8px; }
  .table-wrap { font-size: 10px; }
  thead th { padding: 8px 10px; }
  tbody td { padding: 7px 10px; }
  .cmd-cell { max-width: 200px; }
}
</style>
