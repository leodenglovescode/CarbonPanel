<template>
  <div class="services-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">System Services</h1>
        <p class="page-subtitle">
          Click stars to pin services. If you have starred services, the page opens on that tab by
          default.
        </p>
      </div>
      <div class="header-actions">
        <template v-if="activeTab === 'starred' && services.length > 1">
          <button
            v-if="!reorderMode"
            class="refresh-btn"
            :disabled="loading"
            @click="startReorder"
          >
            reorder
          </button>
          <template v-else>
            <button
              class="refresh-btn"
              :disabled="loading || reorderBusy"
              @click="saveReorder"
            >
              {{ reorderBusy ? 'saving…' : 'save order' }}
            </button>
            <button
              class="refresh-btn"
              :disabled="loading || reorderBusy"
              @click="cancelReorder"
            >
              cancel
            </button>
          </template>
        </template>
        <button
          class="refresh-btn"
          :disabled="loading || reorderBusy || reorderMode"
          @click="loadServices()"
        >
          {{ loading ? 'refreshing…' : 'refresh' }}
        </button>
      </div>
    </div>

    <div class="tabs-row">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="setTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="loading" class="state-msg">loading…</div>
    <div v-else-if="error" class="state-msg error">{{ error }}</div>
    <div v-else-if="services.length === 0" class="state-msg muted">
      {{ emptyStateMessage() }}
    </div>

    <div v-else class="services-grid">
      <div
        v-for="svc in services"
        :key="svc.service_name"
        class="service-card"
        :class="{
          reorderable: activeTab === 'starred' && reorderMode,
          dragging: draggedServiceName === svc.service_name,
          'drag-over':
            dragOverServiceName === svc.service_name && draggedServiceName !== svc.service_name,
        }"
        :draggable="activeTab === 'starred' && reorderMode"
        @dragstart="handleDragStart($event, svc.service_name)"
        @dragover.prevent="handleDragOver(svc.service_name)"
        @drop.prevent="handleDrop"
        @dragend="handleDragEnd"
      >
        <div class="card-top">
          <div class="title-row">
            <div class="title-main">
              <button
                class="star-btn"
                :class="{ starred: svc.starred }"
                :disabled="starBusyName === svc.service_name || reorderBusy || reorderMode"
                :title="svc.starred ? 'Remove star' : 'Add star'"
                @click="toggleStar(svc)"
              >
                {{ svc.starred ? '★' : '☆' }}
              </button>
              <div class="service-name">{{ svc.service_name }}</div>
              <span class="unit-type-badge" :class="unitTypeClass(svc.service_name)">
                {{ unitTypeLabel(svc.service_name) }}
              </span>
            </div>
            <span :class="['status-dot', statusClass(svc.active_state)]" />
          </div>
          <div v-if="svc.description" class="unit-name">{{ svc.description }}</div>
        </div>

        <div class="meta-grid">
          <div class="meta-item">
            <span class="meta-label">active</span>
            <span class="meta-value">{{ svc.active_state }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">substate</span>
            <span class="meta-value">{{ svc.sub_state }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">load</span>
            <span class="meta-value">{{ svc.load_state }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">unit file</span>
            <span class="meta-value">{{ svc.unit_file_state }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">pid</span>
            <span class="meta-value">{{ svc.pid ?? '—' }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">autostart</span>
            <span class="meta-value">{{ svc.autostart_enabled ? 'enabled' : 'disabled' }}</span>
          </div>
        </div>

        <div v-if="svc.uptime" class="uptime">since {{ svc.uptime }}</div>

        <div v-if="activeTab === 'starred' && reorderMode" class="reorder-row">
          <span class="drag-indicator" aria-hidden="true">⋮⋮</span>
          <span class="reorder-hint">drag card to reorder</span>
        </div>

        <div class="actions-row">
          <button
            v-for="act in actions"
            :key="act"
            class="action-btn"
            :class="`action-${act}`"
            :disabled="
              reorderMode ||
              reorderBusy ||
              busyKey === `${svc.service_name}:${act}` ||
              toggleBusyId === svc.service_name
            "
            @click="runAction(svc.service_name, act)"
          >
            {{ busyKey === `${svc.service_name}:${act}` ? '…' : act }}
          </button>
        </div>

        <div class="toggle-row">
          <label class="toggle-label" :class="{ disabled: !canToggleAutostart(svc) }">
            <input
              type="checkbox"
              :checked="svc.autostart_enabled"
              :disabled="
                reorderMode ||
                reorderBusy ||
                toggleBusyId === svc.service_name ||
                !!busyKey ||
                !canToggleAutostart(svc)
              "
              @change="toggleAutostart(svc.service_name, ($event.target as HTMLInputElement).checked)"
            />
            <span>start on boot</span>
          </label>
        </div>

        <div v-if="messages[svc.service_name]" class="service-message">
          {{ messages[svc.service_name] }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { sitesApi } from '@/api'
import type { SiteAction, SystemServiceResponse } from '@/types/sites'

const AUTOSTART_READONLY_STATES = new Set([
  'alias',
  'generated',
  'indirect',
  'masked',
  'masked-runtime',
  'static',
  'transient',
])

type ServiceTab = 'starred' | 'managed' | 'all'

const tabs: { key: ServiceTab; label: string }[] = [
  { key: 'starred', label: 'Starred' },
  { key: 'managed', label: 'Admin / User Created' },
  { key: 'all', label: 'All System Services' },
]

const activeTab = ref<ServiceTab>('starred')
const services = ref<SystemServiceResponse[]>([])
const loading = ref(false)
const error = ref('')
const busyKey = ref<string | null>(null)
const toggleBusyId = ref<string | null>(null)
const starBusyName = ref<string | null>(null)
const reorderMode = ref(false)
const reorderBusy = ref(false)
const draggedServiceName = ref<string | null>(null)
const dragOverServiceName = ref<string | null>(null)
const messages = ref<Record<string, string>>({})
const actions: SiteAction[] = ['start', 'stop', 'restart']

async function loadServices(tab: ServiceTab = activeTab.value) {
  loading.value = true
  error.value = ''
  try {
    const res = await sitesApi.listSystemServices(
      tab === 'all' || tab === 'starred',
      tab === 'starred',
    )
    services.value = res.data
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to load system services'
  } finally {
    loading.value = false
  }
}

async function loadInitialServices() {
  activeTab.value = 'starred'
  await loadServices('starred')

  if (services.value.length === 0) {
    activeTab.value = 'managed'
    await loadServices('managed')
  }
}

function setTab(tab: ServiceTab) {
  if (activeTab.value === tab) return
  activeTab.value = tab
  reorderMode.value = false
  clearDragState()
  messages.value = {}
  void loadServices(tab)
}

function clearDragState() {
  draggedServiceName.value = null
  dragOverServiceName.value = null
}

function startReorder() {
  clearDragState()
  reorderMode.value = true
}

async function cancelReorder() {
  reorderMode.value = false
  clearDragState()
  messages.value = {}
  await loadServices('starred')
}

function moveServiceToIndex(serviceName: string, targetIndex: number) {
  const index = services.value.findIndex((svc) => svc.service_name === serviceName)
  if (
    index === -1 ||
    targetIndex < 0 ||
    targetIndex >= services.value.length ||
    index === targetIndex
  ) {
    return
  }

  const nextServices = [...services.value]
  const [service] = nextServices.splice(index, 1)
  nextServices.splice(targetIndex, 0, service)
  services.value = nextServices
}

function handleDragStart(event: DragEvent, serviceName: string) {
  if (activeTab.value !== 'starred' || !reorderMode.value) return

  draggedServiceName.value = serviceName
  dragOverServiceName.value = serviceName

  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.dropEffect = 'move'
    event.dataTransfer.setData('text/plain', serviceName)
  }
}

function handleDragOver(serviceName: string) {
  if (activeTab.value !== 'starred' || !reorderMode.value || !draggedServiceName.value) return

  dragOverServiceName.value = serviceName
  const targetIndex = services.value.findIndex((svc) => svc.service_name === serviceName)
  if (targetIndex === -1) return

  moveServiceToIndex(draggedServiceName.value, targetIndex)
}

function handleDrop() {
  dragOverServiceName.value = null
}

function handleDragEnd() {
  clearDragState()
}

async function saveReorder() {
  reorderBusy.value = true
  error.value = ''

  try {
    await sitesApi.reorderStarredSystemServices(
      services.value.map((service) => service.service_name),
    )
    clearDragState()
    reorderMode.value = false
    await loadServices('starred')
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to reorder starred services'
  } finally {
    reorderBusy.value = false
  }
}

function emptyStateMessage() {
  if (activeTab.value === 'starred') {
    return 'no starred services yet'
  }

  return activeTab.value === 'all'
    ? 'no systemd services found'
    : 'no admin/user-created systemd services found'
}

async function runAction(serviceName: string, action: SiteAction) {
  busyKey.value = `${serviceName}:${action}`
  messages.value[serviceName] = ''
  try {
    const res = await sitesApi.systemServiceAction(serviceName, action)
    messages.value[serviceName] = res.data.success
      ? `${action} ok`
      : (res.data.output || `${action} failed`)
    await loadServices()
  } catch (e: any) {
    messages.value[serviceName] = e.response?.data?.detail || `${action} failed`
  } finally {
    busyKey.value = null
    setTimeout(() => {
      if (messages.value[serviceName]) messages.value[serviceName] = ''
    }, 4000)
  }
}

async function toggleAutostart(serviceName: string, enabled: boolean) {
  toggleBusyId.value = serviceName
  messages.value[serviceName] = ''
  try {
    const res = await sitesApi.setSystemServiceAutostart(serviceName, enabled)
    messages.value[serviceName] = res.data.success
      ? `autostart ${enabled ? 'enabled' : 'disabled'}`
      : (res.data.output || 'Autostart update failed')
    await loadServices()
  } catch (e: any) {
    messages.value[serviceName] = e.response?.data?.detail || 'Autostart update failed'
    await loadServices()
  } finally {
    toggleBusyId.value = null
    setTimeout(() => {
      if (messages.value[serviceName]) messages.value[serviceName] = ''
    }, 4000)
  }
}

async function toggleStar(service: SystemServiceResponse) {
  const nextStarred = !service.starred
  starBusyName.value = service.service_name
  messages.value[service.service_name] = ''

  try {
    const res = await sitesApi.setSystemServiceStar(service.service_name, nextStarred)
    messages.value[service.service_name] = res.data.success
      ? nextStarred
        ? 'starred'
        : 'unstarred'
      : (res.data.output || 'Star update failed')
    await loadServices()
  } catch (e: any) {
    messages.value[service.service_name] = e.response?.data?.detail || 'Star update failed'
  } finally {
    starBusyName.value = null
    setTimeout(() => {
      if (messages.value[service.service_name]) messages.value[service.service_name] = ''
    }, 4000)
  }
}

function unitType(serviceName: string) {
  return serviceName.split('.').pop() || 'unit'
}

function unitTypeLabel(serviceName: string) {
  const type = unitType(serviceName)

  if (type === 'service') return '⚙ service'
  if (type === 'timer') return '⏱ timer'

  return `◦ ${type}`
}

function unitTypeClass(serviceName: string) {
  return `unit-type-${unitType(serviceName)}`
}

function canToggleAutostart(service: SystemServiceResponse) {
  return !AUTOSTART_READONLY_STATES.has(service.unit_file_state)
}

function statusClass(state: string) {
  if (state === 'active') return 'dot-green'
  if (state === 'failed') return 'dot-red'
  if (state === 'inactive') return 'dot-gray'
  return 'dot-yellow'
}

onMounted(() => {
  void loadInitialServices()
})
</script>

<style scoped>
.services-page {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.page-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--fg);
}

.page-subtitle {
  margin-top: 4px;
  font-size: 11px;
  color: var(--fg-dim);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tabs-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tab-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-muted);
  font-family: var(--font);
  font-size: 11px;
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: all var(--transition);
}

.tab-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.tab-btn.active {
  border-color: var(--accent);
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 10%, transparent);
}

.refresh-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-muted);
  font-family: var(--font);
  font-size: 11px;
  padding: 5px 12px;
  border-radius: 3px;
  cursor: pointer;
  transition: all var(--transition);
}
.refresh-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.state-msg { font-size: 12px; color: var(--fg-muted); padding: 40px 0; text-align: center; }
.state-msg.error { color: var(--danger); }
.state-msg.muted { color: var(--fg-dim); }

.services-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}

.service-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.service-card.reorderable {
  cursor: grab;
}

.service-card.reorderable * {
  user-select: none;
}

.service-card.reorderable:active {
  cursor: grabbing;
}

.service-card.dragging {
  opacity: 0.65;
  border-color: var(--accent);
}

.service-card.drag-over {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent) 35%, transparent);
}

.card-top {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.title-main {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.service-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--fg);
  word-break: break-all;
}

.unit-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 9px;
  line-height: 1.2;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--fg-muted);
  background: var(--bg-input);
  white-space: nowrap;
}

.unit-type-service {
  border-color: color-mix(in srgb, var(--accent) 35%, var(--border));
  color: var(--accent);
}

.unit-type-timer {
  border-color: color-mix(in srgb, var(--warning) 35%, var(--border));
  color: var(--warning);
}

.star-btn {
  background: none;
  border: none;
  padding: 0;
  color: var(--fg-dim);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  transition: color var(--transition), transform var(--transition);
}

.star-btn:hover:not(:disabled) {
  color: var(--warning);
  transform: scale(1.05);
}

.star-btn.starred {
  color: var(--warning);
}

.star-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.unit-name {
  font-size: 11px;
  color: var(--fg-dim);
  word-break: break-all;
}

.status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-green  { background: var(--accent); box-shadow: 0 0 4px var(--accent); }
.dot-red    { background: var(--danger); }
.dot-gray   { background: var(--fg-dim); }
.dot-yellow { background: var(--warning); }

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
}

.meta-label {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--fg-dim);
}

.meta-value {
  font-size: 11px;
  color: var(--fg);
}

.description,
.uptime {
  font-size: 11px;
  color: var(--fg-muted);
}

.drag-indicator {
  font-size: 12px;
  line-height: 1;
  color: var(--fg-dim);
  letter-spacing: -0.08em;
}

.reorder-hint {
  font-size: 11px;
  color: var(--fg-muted);
}

.reorder-row,
.actions-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.action-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-dim);
  font-family: var(--font);
  font-size: 10px;
  padding: 4px 14px;
  border-radius: 3px;
  cursor: pointer;
  transition: all var(--transition);
  text-transform: capitalize;
}
.action-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.action-start:hover:not(:disabled)   { border-color: var(--accent); color: var(--accent); }
.action-stop:hover:not(:disabled)    { border-color: var(--danger); color: var(--danger); }
.action-restart:hover:not(:disabled) { border-color: var(--warning); color: var(--warning); }

.toggle-row {
  display: flex;
  align-items: center;
}

.toggle-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--fg-muted);
  cursor: pointer;
}

.toggle-label.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.service-message {
  font-size: 11px;
  color: var(--fg-muted);
  min-height: 14px;
}
</style>
