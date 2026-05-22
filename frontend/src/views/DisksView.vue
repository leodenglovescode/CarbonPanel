<template>
  <div class="disks-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Disk Management</h1>
        <p class="page-subtitle">
          {{ filteredDisks.length }} partition{{ filteredDisks.length !== 1 ? 's' : '' }} shown
          <span v-if="activeTab === 'all'" class="virtual-hint">· includes virtual/loop</span>
        </p>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="load">
        {{ loading ? 'refreshing...' : 'refresh' }}
      </button>
    </div>

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

    <div v-if="loading" class="state-msg">loading...</div>
    <div v-else-if="error" class="state-msg error">{{ error }}</div>
    <div v-else-if="filteredDisks.length === 0" class="state-msg muted">no disks in this filter</div>

    <div v-else class="disk-list">
      <div
        v-for="disk in filteredDisks"
        :key="disk.device + disk.mountpoint"
        class="disk-card"
        :class="{ expanded: expandedKey === diskKey(disk) }"
      >
        <div class="disk-main" @click="toggleExpand(disk)">
          <div class="disk-left">
            <div class="disk-device">{{ disk.device }}</div>
            <div class="disk-meta">
              <span class="meta-badge">{{ disk.fstype }}</span>
              <span v-if="disk.is_removable" class="meta-badge badge-removable">removable</span>
              <span class="disk-mount">→ {{ disk.mountpoint }}</span>
            </div>
          </div>

          <div class="disk-right">
            <div class="disk-usage-row">
              <span class="usage-numbers">
                <span class="used-val">{{ disk.used_gb.toFixed(1) }}</span>
                <span class="sep"> / {{ disk.total_gb.toFixed(1) }} GB</span>
              </span>
              <span :class="['pct-badge', pctClass(disk.usage_percent)]">
                {{ disk.usage_percent.toFixed(1) }}%
              </span>
            </div>
            <div class="bar-track">
              <div
                class="bar-fill"
                :style="{ width: disk.usage_percent + '%', background: barColor(disk.usage_percent) }"
              />
            </div>
            <div class="io-row">
              <span class="io-item io-read">
                <span class="io-arrow">↑</span>
                <span>{{ metricsRead(disk.device).toFixed(2) }} MB/s</span>
              </span>
              <span class="io-item io-write">
                <span class="io-arrow">↓</span>
                <span>{{ metricsWrite(disk.device).toFixed(2) }} MB/s</span>
              </span>
            </div>
          </div>

          <div class="expand-arrow" :class="{ rotated: expandedKey === diskKey(disk) }">›</div>
        </div>

        <Transition name="expand">
          <div v-if="expandedKey === diskKey(disk)" class="disk-actions">
            <div class="actions-header">Actions</div>
            <div class="action-row">
              <button
                class="action-btn"
                :disabled="actionBusy === diskKey(disk) || disk.mountpoint === '/'"
                :title="disk.mountpoint === '/' ? 'Cannot unmount root' : 'Unmount this partition'"
                @click="confirmUnmount(disk)"
              >
                unmount
              </button>
              <button
                class="action-btn"
                :disabled="actionBusy === diskKey(disk)"
                @click="runCheck(disk)"
              >
                check filesystem
              </button>
            </div>
            <div v-if="actionOutput[diskKey(disk)]" class="action-output" :class="{ 'output-error': actionError[diskKey(disk)] }">
              <pre>{{ actionOutput[diskKey(disk)] }}</pre>
            </div>
          </div>
        </Transition>
      </div>
    </div>

    <!-- Confirm unmount modal -->
    <div v-if="confirmDisk" class="modal-overlay" @click.self="confirmDisk = null">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">Unmount Disk</span>
          <button class="close-btn" @click="confirmDisk = null">✕</button>
        </div>
        <div class="modal-body">
          <p class="confirm-msg">
            Unmount <span class="confirm-highlight">{{ confirmDisk.mountpoint }}</span>?
            Any running processes using this disk will lose access.
          </p>
          <div class="modal-actions">
            <button class="btn-ghost" @click="confirmDisk = null">cancel</button>
            <button class="btn-danger" :disabled="actionBusy !== null" @click="doUnmount">
              {{ actionBusy ? 'unmounting...' : 'unmount' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { disksApi } from '@/api/index'
import { useMetricsStore } from '@/stores/metrics'
import type { DiskInfo } from '@/api/index'

const metricsStore = useMetricsStore()

const disks = ref<DiskInfo[]>([])
const loading = ref(false)
const error = ref('')
const activeTab = ref<'physical' | 'all' | 'removable'>('physical')
const expandedKey = ref<string | null>(null)
const confirmDisk = ref<DiskInfo | null>(null)
const actionBusy = ref<string | null>(null)
const actionOutput = ref<Record<string, string>>({})
const actionError = ref<Record<string, boolean>>({})

const tabs = [
  { key: 'physical' as const, label: 'Physical' },
  { key: 'all' as const, label: 'All' },
  { key: 'removable' as const, label: 'Removable' },
]

function diskKey(d: DiskInfo) {
  return `${d.device}:${d.mountpoint}`
}

function tabCount(key: string) {
  if (key === 'all') return disks.value.length
  if (key === 'physical') return disks.value.filter(d => !d.is_virtual).length
  if (key === 'removable') return disks.value.filter(d => d.is_removable).length
  return disks.value.length
}

const filteredDisks = computed(() => {
  if (activeTab.value === 'physical') return disks.value.filter(d => !d.is_virtual)
  if (activeTab.value === 'removable') return disks.value.filter(d => d.is_removable)
  return disks.value
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await disksApi.list()
    disks.value = data
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to load disks'
  } finally {
    loading.value = false
  }
}

function toggleExpand(disk: DiskInfo) {
  const k = diskKey(disk)
  expandedKey.value = expandedKey.value === k ? null : k
}

function barColor(pct: number) {
  if (pct < 70) return 'var(--accent)'
  if (pct < 85) return 'var(--warning)'
  return 'var(--danger)'
}

function pctClass(pct: number) {
  if (pct < 70) return 'badge-green'
  if (pct < 85) return 'badge-yellow'
  return 'badge-red'
}

function metricsRead(device: string): number {
  const d = metricsStore.latest?.disks?.find(
    m => m.device === device || device.startsWith(m.device)
  )
  return d?.read_mb_s ?? 0
}

function metricsWrite(device: string): number {
  const d = metricsStore.latest?.disks?.find(
    m => m.device === device || device.startsWith(m.device)
  )
  return d?.write_mb_s ?? 0
}

function confirmUnmount(disk: DiskInfo) {
  confirmDisk.value = disk
}

async function doUnmount() {
  if (!confirmDisk.value) return
  const disk = confirmDisk.value
  const k = diskKey(disk)
  actionBusy.value = k
  actionOutput.value[k] = ''
  actionError.value[k] = false
  try {
    const { data } = await disksApi.unmount(disk.mountpoint)
    actionOutput.value[k] = data.output
    actionError.value[k] = !data.success
    confirmDisk.value = null
    await load()
  } catch (e: any) {
    actionOutput.value[k] = e.response?.data?.detail || 'Unmount failed'
    actionError.value[k] = true
    confirmDisk.value = null
  } finally {
    actionBusy.value = null
  }
}

async function runCheck(disk: DiskInfo) {
  const k = diskKey(disk)
  actionBusy.value = k
  actionOutput.value[k] = 'Running fsck...'
  actionError.value[k] = false
  try {
    const { data } = await disksApi.check(disk.mountpoint)
    actionOutput.value[k] = data.output
    actionError.value[k] = !data.success
  } catch (e: any) {
    actionOutput.value[k] = e.response?.data?.detail || 'Check failed'
    actionError.value[k] = true
  } finally {
    actionBusy.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.disks-page { padding: 20px; display: flex; flex-direction: column; gap: 16px; }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; }
.page-title { font-size: 16px; font-weight: 700; color: var(--fg); }
.page-subtitle { font-size: 11px; color: var(--fg-dim); margin-top: 3px; }
.virtual-hint { color: var(--fg-dim); font-style: italic; }

.refresh-btn {
  background: none; border: 1px solid var(--border); color: var(--fg-muted);
  font-family: var(--font); font-size: 11px; padding: 5px 12px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition);
}
.refresh-btn:hover:not(:disabled) { border-color: var(--fg-dim); color: var(--fg); }
.refresh-btn:disabled { opacity: 0.4; cursor: not-allowed; }

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

.state-msg { font-size: 12px; color: var(--fg-muted); padding: 40px 0; text-align: center; }
.state-msg.error { color: var(--danger); }
.state-msg.muted { color: var(--fg-dim); }

.disk-list { display: flex; flex-direction: column; gap: 8px; }

.disk-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  transition: border-color var(--transition), box-shadow var(--transition);
}
.disk-card:hover { border-color: var(--accent-border); box-shadow: var(--shadow-card-hover); }
.disk-card.expanded { border-color: var(--accent-border); }

.disk-main {
  display: flex; align-items: center; gap: 16px;
  padding: 14px 16px; cursor: pointer;
}

.disk-left { min-width: 180px; }
.disk-device { font-size: 13px; font-weight: 600; color: var(--fg); margin-bottom: 4px; }
.disk-meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.meta-badge {
  font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;
  background: var(--bg-badge); border: 1px solid var(--border); color: var(--fg-muted);
  padding: 1px 6px; border-radius: 3px;
}
.badge-removable { color: var(--warning); border-color: rgba(255,170,0,0.3); background: var(--warning-dim); }
.disk-mount { font-size: 10px; color: var(--fg-dim); }

.disk-right { flex: 1; display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.disk-usage-row { display: flex; align-items: baseline; justify-content: space-between; }
.usage-numbers { font-size: 12px; }
.used-val { font-weight: 700; color: var(--accent); font-size: 14px; }
.sep { color: var(--fg-dim); }
.pct-badge {
  font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 3px;
}
.badge-green { background: var(--accent-dim); color: var(--accent); }
.badge-yellow { background: var(--warning-dim); color: var(--warning); }
.badge-red { background: var(--danger-dim); color: var(--danger); }

.bar-track { height: 6px; background: var(--bg-subtle); border-radius: 3px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; transition: width var(--bar-transition), background var(--transition); }

.io-row { display: flex; gap: 16px; }
.io-item { display: flex; align-items: center; gap: 4px; font-size: 10px; color: var(--fg-muted); }
.io-read .io-arrow, .io-read { color: var(--accent); }
.io-write .io-arrow { color: #60a5fa; }
.io-write { color: #60a5fa; }

.expand-arrow {
  font-size: 18px; color: var(--fg-dim); transition: transform var(--transition);
  flex-shrink: 0; user-select: none;
}
.expand-arrow.rotated { transform: rotate(90deg); color: var(--accent); }

/* Actions panel */
.disk-actions {
  border-top: 1px solid var(--border-subtle);
  padding: 12px 16px;
  background: var(--bg-subtle);
  display: flex; flex-direction: column; gap: 10px;
}
.actions-header { font-size: 9px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--fg-dim); }
.action-row { display: flex; gap: 8px; }

.action-btn {
  background: none; border: 1px solid var(--border); color: var(--fg-muted);
  font-family: var(--font); font-size: 11px; padding: 5px 12px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition);
}
.action-btn:hover:not(:disabled) { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }
.action-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.action-output {
  background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-sm);
  padding: 8px 10px; max-height: 160px; overflow-y: auto;
}
.action-output pre {
  font-family: var(--font); font-size: 10px; color: var(--fg-muted);
  white-space: pre-wrap; word-break: break-all;
}
.output-error pre { color: var(--danger); }

/* Transition */
.expand-enter-active, .expand-leave-active { transition: all var(--transition); overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 400px; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius); width: 380px; max-width: 95vw;
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; border-bottom: 1px solid var(--border);
}
.modal-title { font-size: 13px; font-weight: 600; }
.close-btn { background: none; border: none; color: var(--fg-dim); font-size: 12px; cursor: pointer; padding: 2px 4px; }
.close-btn:hover { color: var(--fg); }
.modal-body { padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.confirm-msg { font-size: 12px; color: var(--fg-muted); line-height: 1.6; }
.confirm-highlight { color: var(--fg); font-weight: 600; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
.btn-ghost {
  background: none; border: 1px solid var(--border); color: var(--fg-dim);
  font-family: var(--font); font-size: 11px; padding: 5px 12px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition);
}
.btn-ghost:hover { border-color: var(--fg-dim); color: var(--fg); }
.btn-danger {
  background: var(--danger-dim); border: 1px solid rgba(255,68,68,0.3); color: var(--danger);
  font-family: var(--font); font-size: 11px; padding: 5px 14px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition);
}
.btn-danger:hover:not(:disabled) { background: rgba(255,68,68,0.2); }
.btn-danger:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
