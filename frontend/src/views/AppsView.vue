<template>
  <div class="apps-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">App Management</h1>
        <p class="page-subtitle">{{ filteredApps.length }} listening port{{ filteredApps.length !== 1 ? 's' : '' }}</p>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="load">
        {{ loading ? 'Scanning...' : 'Refresh' }}
      </button>
    </div>

    <div class="filter-row">
      <div class="tabs-row">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
          <span class="tab-count">{{ tabCount(tab.key) }}</span>
        </button>
      </div>
      <div class="search-wrap">
        <input
          v-model="search"
          class="search-input"
          placeholder="Filter by port, name, label..."
        />
      </div>
    </div>

    <div v-if="loading" class="state-msg">Scanning ports...</div>
    <div v-else-if="error" class="state-msg error">{{ error }}</div>
    <div v-else-if="filteredApps.length === 0" class="state-msg muted">No apps match this filter</div>

    <div v-else class="app-table">
      <div class="table-head">
        <span class="col-port">port</span>
        <span class="col-proto">proto</span>
        <span class="col-label">label</span>
        <span class="col-process">process</span>
        <span class="col-user">user</span>
        <span class="col-pid">pid</span>
        <span class="col-actions"></span>
      </div>

      <div
        v-for="app in filteredApps"
        :key="`${app.port}-${app.protocol}`"
        class="app-row"
        :class="{ expanded: expandedKey === appKey(app) }"
      >
        <div class="row-main">
          <span class="col-port">
            <span class="port-num">{{ app.port }}</span>
          </span>
          <span class="col-proto">
            <span :class="['proto-badge', app.protocol === 'tcp' ? 'proto-tcp' : 'proto-udp']">
              {{ app.protocol }}
            </span>
          </span>
          <span class="col-label">
            <span v-if="editingPort === app.port" class="label-edit" @click.stop>
              <input
                v-model="editLabel"
                class="label-input"
                @keyup.enter="saveLabel(app)"
                @keyup.escape="cancelEdit"
                :ref="el => { if (el) (el as HTMLInputElement).focus() }"
              />
              <button class="label-save-btn" @click.stop="saveLabel(app)">save</button>
              <button class="label-cancel-btn" @click.stop="cancelEdit">✕</button>
            </span>
            <button
              v-else
              type="button"
              class="label-display"
              :aria-label="`Edit label for port ${app.port}`"
              @click.stop="startEdit(app)"
            >
              <span v-if="app.custom_label" class="custom-label">{{ app.custom_label }}</span>
              <span v-else-if="app.auto_label" class="auto-label">{{ app.auto_label }}</span>
              <span v-else class="no-label">+ Label</span>
            </button>
          </span>
          <span class="col-process">
            <span class="process-name" :title="app.cmdline">{{ app.process_name || '—' }}</span>
          </span>
          <span class="col-user">{{ app.user || '—' }}</span>
          <span class="col-pid">{{ app.pid ?? '—' }}</span>
          <span class="col-actions">
            <button
              type="button"
              class="expand-btn"
              :aria-label="expandedKey === appKey(app) ? `Hide details for port ${app.port}` : `Show details for port ${app.port}`"
              :aria-expanded="expandedKey === appKey(app)"
              @click="toggleExpand(app)"
            >›</button>
            <button
              v-if="app.pid"
              class="kill-btn"
              :disabled="killBusy === app.port"
              :title="`Kill ${app.process_name} (PID ${app.pid})`"
              @click.stop="confirmKill(app)"
            >
              kill
            </button>
          </span>
        </div>

        <Transition name="expand">
          <div v-if="expandedKey === appKey(app)" class="row-detail">
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">cmdline</span>
                <span class="detail-val">{{ app.cmdline || '—' }}</span>
              </div>
              <div v-if="app.auto_label && app.custom_label" class="detail-item">
                <span class="detail-label">autodetected</span>
                <span class="detail-val">{{ app.auto_label }}</span>
              </div>
            </div>
            <div class="detail-actions">
              <button
                v-if="app.custom_label"
                class="action-sm danger-sm"
                @click="removeLabel(app)"
              >
                remove label
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { appsApi } from '@/api/index'
import type { AppInfo } from '@/api/index'
import { useDialogStore } from '@/stores/dialog'

const dialog = useDialogStore()
const apps = ref<AppInfo[]>([])
const loading = ref(false)
const error = ref('')
const activeTab = ref<'all' | 'tcp' | 'udp' | 'labeled'>('all')
const search = ref('')
const expandedKey = ref<string | null>(null)
const editingPort = ref<number | null>(null)
const editLabel = ref('')
const killBusy = ref<number | null>(null)

const tabs = [
  { key: 'all' as const, label: 'All' },
  { key: 'tcp' as const, label: 'TCP' },
  { key: 'udp' as const, label: 'UDP' },
  { key: 'labeled' as const, label: 'Labeled' },
]

function appKey(a: AppInfo) {
  return `${a.port}-${a.protocol}`
}

function tabCount(key: string) {
  if (key === 'all') return apps.value.length
  if (key === 'tcp') return apps.value.filter(a => a.protocol === 'tcp').length
  if (key === 'udp') return apps.value.filter(a => a.protocol === 'udp').length
  if (key === 'labeled') return apps.value.filter(a => a.custom_label || a.auto_label).length
  return 0
}

const filteredApps = computed(() => {
  let list = apps.value
  if (activeTab.value === 'tcp') list = list.filter(a => a.protocol === 'tcp')
  else if (activeTab.value === 'udp') list = list.filter(a => a.protocol === 'udp')
  else if (activeTab.value === 'labeled') list = list.filter(a => a.custom_label || a.auto_label)

  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(a =>
      String(a.port).includes(q) ||
      a.process_name.toLowerCase().includes(q) ||
      (a.custom_label || '').toLowerCase().includes(q) ||
      (a.auto_label || '').toLowerCase().includes(q) ||
      (a.user || '').toLowerCase().includes(q),
    )
  }
  return list
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await appsApi.list()
    apps.value = data
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to scan ports'
  } finally {
    loading.value = false
  }
}

function toggleExpand(app: AppInfo) {
  const k = appKey(app)
  expandedKey.value = expandedKey.value === k ? null : k
}

function startEdit(app: AppInfo) {
  editingPort.value = app.port
  editLabel.value = app.custom_label || ''
}

function cancelEdit() {
  editingPort.value = null
  editLabel.value = ''
}

async function saveLabel(app: AppInfo) {
  const label = editLabel.value.trim()
  if (!label) {
    await removeLabel(app)
    cancelEdit()
    return
  }
  try {
    await appsApi.setLabel(app.port, label)
    app.custom_label = label
    cancelEdit()
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to save label'
  }
}

async function removeLabel(app: AppInfo) {
  try {
    await appsApi.deleteLabel(app.port)
    app.custom_label = null
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to remove label'
  }
}

async function confirmKill(app: AppInfo) {
  const confirmed = await dialog.confirm({
    title: 'Kill Process',
    message: `Send SIGTERM to ${app.process_name} (PID ${app.pid}) on port ${app.port}?`,
    confirmLabel: 'Kill process',
    variant: 'danger',
  })
  if (confirmed) await doKill(app)
}

async function doKill(app: AppInfo) {
  killBusy.value = app.port
  try {
    const { data } = await appsApi.kill(app.port)
    if (!data.success) {
      await dialog.alert({ title: 'Kill failed', message: data.output || 'The process could not be stopped.', variant: 'danger' })
    }
    await load()
  } catch (e: any) {
    await dialog.alert({ title: 'Kill failed', message: e.response?.data?.detail || 'Kill failed', variant: 'danger' })
  } finally {
    killBusy.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.apps-page { padding: 20px; display: flex; flex-direction: column; gap: 16px; }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; }
.page-title { font-size: 16px; font-weight: 700; color: var(--fg); }
.page-subtitle { font-size: 11px; color: var(--fg-dim); margin-top: 3px; }

.refresh-btn {
  background: none; border: 1px solid var(--border); color: var(--fg-muted);
  font-family: var(--font); font-size: 11px; padding: 5px 12px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition);
}
.refresh-btn:hover:not(:disabled) { border-color: var(--fg-dim); color: var(--fg); }
.refresh-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.filter-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.tabs-row { display: flex; gap: 4px; }
.tab-btn {
  background: none; border: 1px solid var(--border); color: var(--fg-muted);
  font-family: var(--font); font-size: 11px; padding: 5px 10px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition); display: flex; align-items: center; gap: 6px;
}
.tab-btn:hover { background: var(--bg-hover); color: var(--fg); }
.tab-btn.active { background: var(--accent-dim); color: var(--accent); border-color: var(--accent-border); }
.tab-count {
  font-size: 9px; background: var(--bg-badge); border-radius: 8px;
  padding: 1px 5px; color: var(--fg-dim);
}
.tab-btn.active .tab-count { color: var(--accent); background: rgba(0,255,136,0.12); }

.search-wrap { flex: 1; max-width: 240px; }
.search-input {
  width: 100%; background: var(--bg-input); border: 1px solid var(--border);
  color: var(--fg); font-family: var(--font); font-size: 11px; padding: 5px 8px;
  border-radius: var(--radius-sm); outline: none; transition: border-color var(--transition);
}
.search-input:focus { border-color: var(--accent-border); }
.search-input::placeholder { color: var(--fg-dim); }

.state-msg { font-size: 12px; color: var(--fg-muted); padding: 40px 0; text-align: center; }
.state-msg.error { color: var(--danger); }
.state-msg.muted { color: var(--fg-dim); }

/* Table */
.app-table { display: flex; flex-direction: column; gap: 2px; }

.table-head {
  display: grid;
  grid-template-columns: 60px 54px 1fr 140px 100px 60px 96px;
  padding: 6px 12px;
  font-size: 9px; text-transform: uppercase; letter-spacing: 0.07em; color: var(--fg-dim);
}

@media (max-width: 640px) {
  .apps-page { padding: 12px; gap: 12px; }
  .filter-row { flex-direction: column; align-items: stretch; }
  .search-wrap { max-width: 100%; }
  .table-head { grid-template-columns: 58px 50px 1fr 1fr 80px; padding: 6px 10px; }
  .row-main { grid-template-columns: 58px 50px 1fr 1fr 80px; padding: 8px 10px; }
  .col-user, .col-pid { display: none; }
  .process-name { max-width: 100%; }
}

.app-row {
  background: color-mix(in srgb, var(--bg-card) 72%, transparent);
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm); overflow: hidden;
  transition: border-color var(--transition);
}
.app-row:hover { border-color: var(--accent-border); }
.app-row.expanded { border-color: var(--accent-border); }

.row-main {
  display: grid;
  grid-template-columns: 60px 54px 1fr 140px 100px 60px 96px;
  align-items: center; padding: 6px 12px;
  transition: background var(--transition);
}
.row-main:hover { background: var(--bg-hover); }

.col-label { min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }

.col-port .port-num { font-size: 13px; font-weight: 700; color: var(--accent); }

.proto-badge {
  font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
  padding: 2px 6px; border-radius: 3px;
}
.proto-tcp { background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent-border); }
.proto-udp { background: rgba(68,136,255,0.1); color: var(--info); border: 1px solid rgba(68,136,255,0.25); }

.label-display {
  max-width: 100%; padding: 0; border: 0; background: none; color: inherit;
  font: inherit; text-align: left; cursor: pointer;
}
.label-display:focus-visible { outline: 1px solid var(--accent); outline-offset: 2px; }
.custom-label { font-size: 11px; font-weight: 600; color: var(--fg); }
.auto-label { font-size: 11px; color: var(--fg-muted); font-style: italic; }
.no-label { font-size: 10px; color: var(--fg-dim); }
.no-label:hover { color: var(--accent); }

.label-edit { display: flex; align-items: center; gap: 4px; }
.label-input {
  background: var(--bg-input); border: 1px solid var(--accent-border); color: var(--fg);
  font-family: var(--font); font-size: 11px; padding: 3px 6px;
  border-radius: var(--radius-sm); outline: none; width: 120px;
}
.label-save-btn, .label-cancel-btn {
  background: none; border: none; font-family: var(--font); font-size: 10px;
  cursor: pointer; padding: 2px 4px;
}
.label-save-btn { color: var(--accent); }
.label-cancel-btn { color: var(--fg-dim); }

.process-name { font-size: 12px; color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 130px; display: block; }
.col-user { font-size: 11px; color: var(--fg-muted); }
.col-pid { font-size: 11px; color: var(--fg-dim); }

.col-actions { display: flex; align-items: center; justify-content: flex-end; gap: 4px; }
.expand-btn {
  width: 26px; height: 26px; padding: 0; border: 0; border-radius: 3px;
  background: none; color: var(--fg-dim); font: 18px/1 var(--font); cursor: pointer;
}
.expand-btn:hover, .expand-btn:focus-visible { color: var(--accent); background: var(--accent-dim); }

.kill-btn {
  background: none; border: 1px solid rgba(255,68,68,0.3); color: var(--danger);
  font-family: var(--font); font-size: 10px; padding: 3px 8px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition);
}
.kill-btn:hover:not(:disabled) { background: var(--danger-dim); }
.kill-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* Detail panel */
.row-detail {
  border-top: 1px solid var(--border-subtle); padding: 10px 12px;
  background: var(--bg-subtle); display: flex; flex-direction: column; gap: 8px;
}
.detail-grid { display: flex; flex-direction: column; gap: 6px; }
.detail-item { display: flex; gap: 12px; align-items: baseline; }
.detail-label { font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg-dim); min-width: 80px; flex-shrink: 0; }
.detail-val { font-size: 11px; color: var(--fg-muted); word-break: break-all; }
.detail-actions { display: flex; gap: 8px; }

.action-sm {
  background: none; border: 1px solid var(--border); color: var(--fg-muted);
  font-family: var(--font); font-size: 10px; padding: 3px 8px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition);
}
.action-sm:hover { border-color: var(--fg-dim); color: var(--fg); }
.danger-sm:hover { border-color: rgba(255,68,68,0.3); color: var(--danger); background: var(--danger-dim); }

/* Transition */
.expand-enter-active, .expand-leave-active { transition: all var(--transition); overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 200px; }

</style>
