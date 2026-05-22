<template>
  <div class="docker-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('docker.title') }}</h1>
        <p class="page-subtitle">{{ containers.length }} container{{ containers.length !== 1 ? 's' : '' }}</p>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="load">
        {{ loading ? t('common.refreshing') : t('common.refresh') }}
      </button>
    </div>

    <div v-if="loading && !containers.length" class="state-msg">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="state-msg error">{{ error }}</div>
    <div v-else-if="!containers.length" class="state-msg muted">{{ t('docker.noDocker') }}</div>

    <div v-else class="container-list">
      <div v-for="c in containers" :key="c.id" class="container-card">
        <div class="card-top">
          <div class="card-info">
            <div class="container-name">{{ c.name }}</div>
            <div class="container-image">{{ c.image }}</div>
          </div>
          <div class="card-badges">
            <span :class="['state-badge', stateBadge(c.state)]">{{ c.state }}</span>
            <span class="id-badge">{{ c.id.slice(0, 12) }}</span>
          </div>
        </div>

        <div v-if="c.state === 'running'" class="stats-row">
          <div class="stat-item">
            <span class="stat-lbl">{{ t('docker.cpu') }}</span>
            <span class="stat-val">{{ c.cpu_percent.toFixed(1) }}%</span>
            <div class="mini-bar"><div class="mini-fill" :style="{ width: Math.min(c.cpu_percent, 100) + '%', background: 'var(--accent)' }" /></div>
          </div>
          <div class="stat-item">
            <span class="stat-lbl">{{ t('docker.memory') }}</span>
            <span class="stat-val">{{ fmtMb(c.mem_usage_mb) }} / {{ fmtMb(c.mem_limit_mb) }}</span>
            <div class="mini-bar"><div class="mini-fill" :style="{ width: Math.min(c.mem_percent, 100) + '%', background: '#60a5fa' }" /></div>
          </div>
        </div>

        <div class="status-row">
          <span class="status-txt">{{ c.status }}</span>
          <span v-if="c.ports" class="ports-txt">{{ c.ports }}</span>
        </div>

        <div class="actions-row">
          <button
            v-if="c.state !== 'running'"
            class="act-btn act-start"
            :disabled="busy === c.id"
            @click="action(c, 'start')"
          >{{ t('docker.start') }}</button>
          <button
            v-if="c.state === 'running'"
            class="act-btn act-stop"
            :disabled="busy === c.id"
            @click="confirmStop(c)"
          >{{ t('docker.stop') }}</button>
          <button
            class="act-btn act-restart"
            :disabled="busy === c.id"
            @click="action(c, 'restart')"
          >{{ t('docker.restart') }}</button>
          <span v-if="actionMsg[c.id]" class="act-msg" :class="{ 'act-err': actionErr[c.id] }">{{ actionMsg[c.id] }}</span>
        </div>
      </div>
    </div>

    <!-- Confirm stop modal -->
    <div v-if="confirmTarget" class="modal-overlay" @click.self="confirmTarget = null">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">{{ t('docker.confirmStop') }}</span>
          <button class="close-btn" @click="confirmTarget = null">✕</button>
        </div>
        <div class="modal-body">
          <p class="confirm-msg">{{ t('docker.confirmStopMsg', { name: confirmTarget.name }) }}</p>
          <div class="modal-actions">
            <button class="btn-ghost" @click="confirmTarget = null">{{ t('common.cancel') }}</button>
            <button class="btn-danger" :disabled="busy === confirmTarget.id" @click="doStop">
              {{ busy === confirmTarget?.id ? '…' : t('docker.stop') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { dockerApi, type ContainerInfo } from '@/api/index'
import { useLocaleStore } from '@/stores/locale'

const { t } = useLocaleStore()

const containers = ref<ContainerInfo[]>([])
const loading = ref(false)
const error = ref('')
const busy = ref<string | null>(null)
const actionMsg = ref<Record<string, string>>({})
const actionErr = ref<Record<string, boolean>>({})
const confirmTarget = ref<ContainerInfo | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await dockerApi.list()
    containers.value = data
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to load containers'
  } finally {
    loading.value = false
  }
}

async function action(c: ContainerInfo, act: 'start' | 'stop' | 'restart') {
  busy.value = c.id
  actionMsg.value[c.id] = ''
  actionErr.value[c.id] = false
  try {
    const fn = act === 'start' ? dockerApi.start : act === 'stop' ? dockerApi.stop : dockerApi.restart
    const { data } = await fn(c.id)
    actionMsg.value[c.id] = data.success ? 'ok' : data.output
    actionErr.value[c.id] = !data.success
    await load()
  } catch (e: any) {
    actionMsg.value[c.id] = e.response?.data?.detail || 'Failed'
    actionErr.value[c.id] = true
  } finally {
    busy.value = null
  }
}

function confirmStop(c: ContainerInfo) { confirmTarget.value = c }
async function doStop() {
  if (!confirmTarget.value) return
  const c = confirmTarget.value
  confirmTarget.value = null
  await action(c, 'stop')
}

function stateBadge(state: string) {
  if (state === 'running') return 'badge-running'
  if (state === 'exited') return 'badge-exited'
  return 'badge-other'
}

function fmtMb(mb: number): string {
  if (mb >= 1024) return (mb / 1024).toFixed(1) + ' GB'
  return mb.toFixed(0) + ' MB'
}

onMounted(load)
</script>

<style scoped>
.docker-page { padding: 20px; display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.page-title { font-size: 16px; font-weight: 700; }
.page-subtitle { font-size: 11px; color: var(--fg-muted); margin-top: 2px; }
.refresh-btn { background: none; border: 1px solid var(--border); color: var(--fg-muted); font-family: var(--font); font-size: 11px; padding: 5px 12px; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); }
.refresh-btn:hover:not(:disabled) { border-color: var(--accent-border); color: var(--accent); }
.refresh-btn:disabled { opacity: 0.5; cursor: default; }
.state-msg { font-size: 12px; color: var(--fg-muted); padding: 20px 0; text-align: center; }
.state-msg.error { color: var(--danger); }
.state-msg.muted { color: var(--fg-dim); }

.container-list { display: flex; flex-direction: column; gap: 10px; }
.container-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; transition: border-color var(--transition); }
.container-card:hover { border-color: var(--border-hover, var(--fg-dim)); }

.card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.container-name { font-size: 13px; font-weight: 600; color: var(--fg); }
.container-image { font-size: 11px; color: var(--fg-muted); margin-top: 2px; }
.card-badges { display: flex; gap: 6px; flex-wrap: wrap; }

.state-badge { font-size: 10px; padding: 2px 8px; border-radius: 20px; font-weight: 600; letter-spacing: 0.04em; }
.badge-running { background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent-border); }
.badge-exited { background: var(--danger-dim); color: var(--danger); border: 1px solid rgba(255,68,68,0.3); }
.badge-other { background: var(--bg-input); color: var(--fg-muted); border: 1px solid var(--border); }
.id-badge { font-size: 10px; color: var(--fg-dim); font-family: monospace; padding: 2px 6px; background: var(--bg-input); border-radius: 3px; }

.stats-row { display: flex; gap: 20px; }
.stat-item { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.stat-lbl { font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg-dim); }
.stat-val { font-size: 11px; color: var(--fg); }
.mini-bar { height: 4px; background: var(--bg-subtle); border-radius: 2px; overflow: hidden; }
.mini-fill { height: 100%; border-radius: 2px; transition: width var(--bar-transition); }

.status-row { display: flex; gap: 10px; align-items: center; }
.status-txt { font-size: 11px; color: var(--fg-muted); }
.ports-txt { font-size: 10px; color: var(--fg-dim); font-family: monospace; }

.actions-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.act-btn { background: none; border: 1px solid var(--border); color: var(--fg-muted); font-family: var(--font); font-size: 11px; padding: 4px 12px; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); }
.act-btn:disabled { opacity: 0.5; cursor: default; }
.act-start:hover:not(:disabled) { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }
.act-stop:hover:not(:disabled) { border-color: rgba(255,68,68,0.4); color: var(--danger); background: var(--danger-dim); }
.act-restart:hover:not(:disabled) { border-color: rgba(100,180,255,0.4); color: #60a5fa; background: rgba(96,165,250,0.1); }
.act-msg { font-size: 10px; color: var(--accent); }
.act-err { color: var(--danger); }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 0; min-width: 320px; max-width: 440px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; border-bottom: 1px solid var(--border-subtle); }
.modal-title { font-size: 13px; font-weight: 600; }
.close-btn { background: none; border: none; color: var(--fg-dim); cursor: pointer; font-size: 14px; padding: 2px 6px; }
.modal-body { padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.confirm-msg { font-size: 12px; color: var(--fg-muted); line-height: 1.5; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; }
.btn-ghost { background: none; border: 1px solid var(--border); color: var(--fg-muted); font-family: var(--font); font-size: 11px; padding: 6px 14px; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); }
.btn-ghost:hover { border-color: var(--fg-dim); color: var(--fg); }
.btn-danger { background: var(--danger-dim); border: 1px solid rgba(255,68,68,0.4); color: var(--danger); font-family: var(--font); font-size: 11px; padding: 6px 14px; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); }
.btn-danger:disabled { opacity: 0.5; cursor: default; }
</style>
