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
            @click="confirmAction(c, 'start')"
          >{{ t('docker.start') }}</button>
          <button
            v-if="c.state === 'running'"
            class="act-btn act-stop"
            :disabled="busy === c.id"
            @click="confirmAction(c, 'stop')"
          >{{ t('docker.stop') }}</button>
          <button
            class="act-btn act-restart"
            :disabled="busy === c.id"
            @click="confirmAction(c, 'restart')"
          >{{ t('docker.restart') }}</button>
          <span v-if="actionMsg[c.id]" class="act-msg" :class="{ 'act-err': actionErr[c.id] }">{{ actionMsg[c.id] }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { dockerApi, type ContainerInfo } from '@/api/index'
import { useLocaleStore } from '@/stores/locale'
import { useDialogStore } from '@/stores/dialog'

const { t } = useLocaleStore()
const dialog = useDialogStore()

const containers = ref<ContainerInfo[]>([])
const loading = ref(false)
const error = ref('')
const busy = ref<string | null>(null)
const actionMsg = ref<Record<string, string>>({})
const actionErr = ref<Record<string, boolean>>({})

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

const ACTION_CONFIRM: Record<'start' | 'stop' | 'restart', { title: string; message: (name: string) => string; confirmLabel: string; variant: 'primary' | 'danger' }> = {
  start: { title: 'Start container', message: (name) => `Start "${name}"?`, confirmLabel: 'Start', variant: 'primary' },
  stop: { title: 'Stop container', message: (name) => `Stop "${name}"? This will interrupt anything currently running inside it.`, confirmLabel: 'Stop', variant: 'danger' },
  restart: { title: 'Restart container', message: (name) => `Restart "${name}"? This will briefly interrupt it.`, confirmLabel: 'Restart', variant: 'primary' },
}

async function confirmAction(c: ContainerInfo, act: 'start' | 'stop' | 'restart') {
  const cfg = ACTION_CONFIRM[act]
  const confirmed = await dialog.confirm({
    title: cfg.title,
    message: cfg.message(c.name),
    confirmLabel: cfg.confirmLabel,
    variant: cfg.variant,
  })
  if (!confirmed) return
  await action(c, act)
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

.container-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 8px; align-items: start; }
.container-card {
  background: color-mix(in srgb, var(--bg-card) 72%, transparent);
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  border: 1px solid var(--border); border-radius: var(--radius); padding: 10px 12px;
  display: flex; flex-direction: column; gap: 6px; transition: border-color var(--transition);
  /* Grid items default to min-width:auto, same trap as flex items — without
     this, .ports-txt's white-space:nowrap content (arbitrarily long port
     mappings) forces its min-content width onto the whole card, growing it
     past the 1fr track instead of letting the inner ellipsis rules clip it. */
  min-width: 0;
}
.container-card:hover { border-color: var(--border-hover, var(--fg-dim)); }

.card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.card-info { min-width: 0; }
.container-name {
  font-size: 12px; font-weight: 600; color: var(--fg);
  overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
}
.container-image { font-size: 10px; color: var(--fg-muted); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 150px; }
.card-badges { display: flex; gap: 5px; flex-wrap: wrap; justify-content: flex-end; }

.state-badge { font-size: 10px; padding: 2px 8px; border-radius: 20px; font-weight: 600; letter-spacing: 0.04em; }
.badge-running { background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent-border); }
.badge-exited { background: var(--danger-dim); color: var(--danger); border: 1px solid rgba(255,68,68,0.3); }
.badge-other { background: var(--bg-input); color: var(--fg-muted); border: 1px solid var(--border); }
.id-badge { font-size: 10px; color: var(--fg-dim); font-family: monospace; padding: 2px 6px; background: var(--bg-input); border-radius: 3px; }

.stats-row { display: flex; gap: 12px; }
.stat-item { display: flex; flex-direction: column; gap: 3px; flex: 1; min-width: 0; }
.stat-lbl { font-size: 8px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg-dim); }
.stat-val {
  font-size: 10px; color: var(--fg);
  overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
}
.mini-bar { height: 3px; background: var(--bg-subtle); border-radius: 2px; overflow: hidden; }
.mini-fill { height: 100%; border-radius: 2px; transition: width var(--bar-transition); }

.status-row { display: flex; gap: 8px; align-items: center; }
.status-txt { font-size: 10px; color: var(--fg-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; flex-shrink: 1; }
.ports-txt { font-size: 9px; color: var(--fg-dim); font-family: monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; flex-shrink: 2; }

.actions-row { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.act-btn { background: none; border: 1px solid var(--border); color: var(--fg-muted); font-family: var(--font); font-size: 10px; padding: 3px 9px; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); }
.act-btn:disabled { opacity: 0.5; cursor: default; }
.act-start:hover:not(:disabled) { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }
.act-stop:hover:not(:disabled) { border-color: rgba(255,68,68,0.4); color: var(--danger); background: var(--danger-dim); }
.act-restart:hover:not(:disabled) { border-color: rgba(100,180,255,0.4); color: #60a5fa; background: rgba(96,165,250,0.1); }
.act-msg { font-size: 10px; color: var(--accent); overflow-wrap: anywhere; min-width: 0; }
.act-err { color: var(--danger); }

@media (max-width: 640px) {
  .docker-page { padding: 12px; gap: 10px; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 8px; }
  .container-list { grid-template-columns: 1fr; }
  .stats-row { gap: 12px; }
}
</style>
