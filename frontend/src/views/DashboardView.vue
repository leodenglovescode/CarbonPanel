<template>
  <div class="dashboard" :class="{ 'edit-active': editMode }">

    <!-- Edit toolbar -->
    <Transition name="toolbar">
      <div v-if="editMode" class="edit-toolbar">
        <span class="edit-hint">Drag to move · corners to resize</span>
        <button class="tb-btn" @click="resetLayout">Reset</button>
        <button class="tb-btn tb-done" @click="exitEdit">Done</button>
      </div>
    </Transition>

    <!-- Edit button (normal mode) -->
    <button v-if="!editMode && metrics.latest" class="edit-fab" @click="enterEdit" title="Edit layout">
      ⊞
    </button>

    <div v-if="!metrics.latest && visibleWidgets.length === 0" class="loading">
      <span class="loading-dot" /><span class="loading-dot" /><span class="loading-dot" />
      <span class="loading-text">connecting…</span>
    </div>

    <!-- ── Unified grid (normal + edit mode) ── -->
    <div
      v-else
      ref="gridEl"
      class="grid"
      :class="{ 'grid-edit': editMode }"
    >
      <div
        v-for="w in sortedWidgets"
        :key="w.id"
        class="grid-item"
        :class="{ 'edit-widget': editMode, 'is-active': editMode && drag?.id === w.id }"
        :style="gridItemStyle(w.id)"
        @mousedown.left="editMode ? (($event as MouseEvent).preventDefault(), startDrag(w.id, $event)) : undefined"
      >
        <div class="widget-body" :class="{ 'no-pe': editMode }">
          <component :is="w.comp" v-bind="w.props" />
        </div>
        <template v-if="editMode">
          <div class="handle tl" @mousedown.left.stop.prevent="startResize(w.id, 'tl', $event)" />
          <div class="handle tr" @mousedown.left.stop.prevent="startResize(w.id, 'tr', $event)" />
          <div class="handle bl" @mousedown.left.stop.prevent="startResize(w.id, 'bl', $event)" />
          <div class="handle br" @mousedown.left.stop.prevent="startResize(w.id, 'br', $event)" />
        </template>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import CpuWidget from '@/components/widgets/CpuWidget.vue'
import RamWidget from '@/components/widgets/RamWidget.vue'
import GpuWidget from '@/components/widgets/GpuWidget.vue'
import DiskWidget from '@/components/widgets/DiskWidget.vue'
import NetworkWidget from '@/components/widgets/NetworkWidget.vue'
import ProcessListWidget from '@/components/widgets/ProcessListWidget.vue'
import SystemWidget from '@/components/widgets/SystemWidget.vue'
import CpuTempWidget from '@/components/widgets/CpuTempWidget.vue'
import HistoryWidget from '@/components/widgets/HistoryWidget.vue'
import BandwidthWidget from '@/components/widgets/BandwidthWidget.vue'
import BookmarksWidget from '@/components/widgets/BookmarksWidget.vue'
import { useMetricsStore } from '@/stores/metrics'
import { useWebSocket } from '@/composables/useWebSocket'
import { useLayoutStore, type WidgetId } from '@/stores/layout'
import { metricsApi, type HistoryPoint } from '@/api/index'

// ── Metrics ────────────────────────────────────────────────────────────────────

const metrics = useMetricsStore()
const { connect, sendPrefs } = useWebSocket()
const historyPoints = ref<HistoryPoint[]>([])

onMounted(async () => {
  connect()
  layoutStore.loadRemote()
  try {
    const { data } = await metricsApi.history()
    historyPoints.value = data
  } catch { /* ignore */ }
})

metrics.$subscribe(() => {
  if (!metrics.latest) return
  historyPoints.value.push({
    ts: metrics.latest.ts,
    cpu: metrics.latest.cpu.aggregate,
    mem: metrics.latest.memory.percent,
    gpu: metrics.latest.gpu.available && metrics.latest.gpu.devices.length
      ? metrics.latest.gpu.devices[0].utilization_percent
      : null,
  })
  if (historyPoints.value.length > 300) historyPoints.value.splice(0, 50)
})

function onSortChange(sort: 'cpu' | 'memory') {
  sendPrefs(sort, metrics.processLimit)
}

// ── Layout store ───────────────────────────────────────────────────────────────

const layoutStore = useLayoutStore()

// ── Edit mode ─────────────────────────────────────────────────────────────────

const editMode = ref(false)
const gridEl = ref<HTMLElement | null>(null)
const gridW = ref(0)

// Grid constants — must match CSS (.grid { grid-auto-rows: 30px; gap: 6px })
const COLS = 12
const ROW_H = 30
const GAP = 6
const MIN_W = 3
const MIN_H = 3

// cellW is only used for drag-delta snapping; CSS grid handles actual sizing
const cellW = computed(() => {
  const w = gridW.value || 1200
  return (w - GAP * (COLS - 1)) / COLS
})

// Single placement function used by both normal and edit mode
function gridItemStyle(id: WidgetId) {
  const p = layoutStore.layout[id]
  return {
    gridColumn: `${p.col + 1} / span ${p.w}`,
    gridRow: `${p.row + 1} / span ${p.h}`,
  }
}

// ── Drag / resize ─────────────────────────────────────────────────────────────

interface DragState {
  type: 'drag' | 'resize'
  id: WidgetId
  corner?: 'tl' | 'tr' | 'bl' | 'br'
  mx0: number; my0: number
  col0: number; row0: number; w0: number; h0: number
}

const drag = ref<DragState | null>(null)

function startDrag(id: WidgetId, e: MouseEvent) {
  const p = layoutStore.layout[id]
  drag.value = {
    type: 'drag', id,
    mx0: e.clientX, my0: e.clientY,
    col0: p.col, row0: p.row, w0: p.w, h0: p.h,
  }
}

function startResize(id: WidgetId, corner: 'tl' | 'tr' | 'bl' | 'br', e: MouseEvent) {
  const p = layoutStore.layout[id]
  drag.value = {
    type: 'resize', id, corner,
    mx0: e.clientX, my0: e.clientY,
    col0: p.col, row0: p.row, w0: p.w, h0: p.h,
  }
}

// Returns true if `pos` for widget `id` would overlap any OTHER visible widget.
function hasOverlap(id: WidgetId, pos: { col: number; row: number; w: number; h: number }): boolean {
  const visibleIds = new Set(visibleWidgets.value.map(w => w.id))
  for (const [otherId, other] of Object.entries(layoutStore.layout) as [WidgetId, { col: number; row: number; w: number; h: number }][]) {
    if (otherId === id || !visibleIds.has(otherId)) continue
    const noOverlap =
      pos.col + pos.w <= other.col ||
      other.col + other.w <= pos.col ||
      pos.row + pos.h <= other.row ||
      other.row + other.h <= pos.row
    if (!noOverlap) return true
  }
  return false
}

function onMouseMove(e: MouseEvent) {
  const d = drag.value
  if (!d) return

  const cw = cellW.value
  const dcol = Math.round((e.clientX - d.mx0) / (cw + GAP))
  const drow = Math.round((e.clientY - d.my0) / (ROW_H + GAP))

  if (d.type === 'drag') {
    const proposed = {
      col: Math.max(0, Math.min(COLS - d.w0, d.col0 + dcol)),
      row: Math.max(0, d.row0 + drow),
      w: d.w0, h: d.h0,
    }
    if (!hasOverlap(d.id, proposed))
      layoutStore.update(d.id, { col: proposed.col, row: proposed.row })
    return
  }

  // Resize — build the full proposed rect then check overlap before committing
  let proposed: { col: number; row: number; w: number; h: number }

  switch (d.corner) {
    case 'br':
      proposed = {
        col: d.col0, row: d.row0,
        w: Math.max(MIN_W, Math.min(COLS - d.col0, d.w0 + dcol)),
        h: Math.max(MIN_H, d.h0 + drow),
      }
      break
    case 'bl': {
      const nc = Math.max(0, Math.min(d.col0 + d.w0 - MIN_W, d.col0 + dcol))
      proposed = { col: nc, row: d.row0, w: d.w0 + d.col0 - nc, h: Math.max(MIN_H, d.h0 + drow) }
      break
    }
    case 'tr': {
      const nr = Math.max(0, Math.min(d.row0 + d.h0 - MIN_H, d.row0 + drow))
      proposed = {
        col: d.col0, row: nr,
        w: Math.max(MIN_W, Math.min(COLS - d.col0, d.w0 + dcol)),
        h: d.h0 + d.row0 - nr,
      }
      break
    }
    case 'tl': {
      const nc = Math.max(0, Math.min(d.col0 + d.w0 - MIN_W, d.col0 + dcol))
      const nr = Math.max(0, Math.min(d.row0 + d.h0 - MIN_H, d.row0 + drow))
      proposed = { col: nc, row: nr, w: d.w0 + d.col0 - nc, h: d.h0 + d.row0 - nr }
      break
    }
    default: return
  }

  if (!hasOverlap(d.id, proposed)) layoutStore.update(d.id, proposed)
  // If overlap: keep current position — widget stays at last valid spot
}

function onMouseUp() {
  if (drag.value) {
    layoutStore.save()
    drag.value = null
  }
}

function enterEdit() {
  editMode.value = true
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
  if (gridEl.value) gridW.value = gridEl.value.clientWidth
}

function exitEdit() {
  editMode.value = false
  drag.value = null
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
}

function resetLayout() {
  layoutStore.reset()
}

// ResizeObserver keeps cellW accurate as the window resizes in edit mode
let ro: ResizeObserver | null = null
onMounted(() => {
  ro = new ResizeObserver(entries => {
    if (editMode.value) gridW.value = entries[0].contentRect.width
  })
})
onUnmounted(() => {
  ro?.disconnect()
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
})

// Attach/detach ResizeObserver when edit-grid mounts
import { watchEffect } from 'vue'
watchEffect(() => {
  if (editMode.value && gridEl.value && ro) {
    ro.observe(gridEl.value)
    gridW.value = gridEl.value.clientWidth
  } else if (!editMode.value && ro) {
    ro.disconnect()
  }
})

// ── Widget configs for edit mode ───────────────────────────────────────────────

const visibleWidgets = computed(() => {
  const m = metrics.latest
  const always = [
    { id: 'bookmarks' as WidgetId, comp: BookmarksWidget, props: {}, show: true },
  ]
  if (!m) return always.filter(w => w.show)
  return [
    ...always,
    { id: 'cpu'       as WidgetId, comp: CpuWidget,         props: { cpu: m.cpu, history: metrics.cpuHistory },                                              show: true },
    { id: 'ram'       as WidgetId, comp: RamWidget,         props: { mem: m.memory, history: metrics.memHistory },                                           show: true },
    { id: 'gpu'       as WidgetId, comp: GpuWidget,         props: { gpu: m.gpu, history: metrics.gpuHistory },                                              show: m.gpu.available },
    { id: 'system'    as WidgetId, comp: SystemWidget,      props: { system: m.system, cpu: m.cpu },                                                         show: true },
    { id: 'disk'      as WidgetId, comp: DiskWidget,        props: { disks: m.disks },                                                                       show: true },
    { id: 'network'   as WidgetId, comp: NetworkWidget,     props: { network: m.network, rxHistory: metrics.netRxHistory, txHistory: metrics.netTxHistory },  show: true },
    { id: 'cpuTemp'   as WidgetId, comp: CpuTempWidget,     props: { temps: m.cpu.temps },                                                                   show: m.cpu.temps.length > 0 },
    { id: 'bandwidth' as WidgetId, comp: BandwidthWidget,   props: { network: m.network },                                                                   show: true },
    { id: 'history'   as WidgetId, comp: HistoryWidget,     props: { points: historyPoints.value },                                                          show: true },
    { id: 'processes' as WidgetId, comp: ProcessListWidget, props: { processes: m.processes, onSortChange },                                                  show: true },
  ].filter(w => w.show)
})

// Sort by row then col so tab order matches visual order
const sortedWidgets = computed(() =>
  visibleWidgets.value.slice().sort((a, b) => {
    const la = layoutStore.layout[a.id]
    const lb = layoutStore.layout[b.id]
    return la.row !== lb.row ? la.row - lb.row : la.col - lb.col
  })
)
</script>

<style scoped>
.dashboard { padding: 12px; position: relative; }
.edit-active { padding-top: 0; }

/* Loading */
.loading { display: flex; align-items: center; justify-content: center; height: 200px; gap: 6px; color: var(--fg-dim); font-size: 12px; }
.loading-dot { width: 6px; height: 6px; background: var(--accent); border-radius: 50%; animation: pulse 1s ease infinite; }
.loading-dot:nth-child(2) { animation-delay: 0.2s; }
.loading-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.1; } }
.loading-text { margin-left: 8px; }

/* Shared grid — used in both normal and edit mode */
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: 30px;
  gap: 6px;
}
.grid-item { min-width: 0; overflow: hidden; }
@media (max-width: 900px) {
  .grid-item { grid-column: 1 / -1 !important; grid-row: auto !important; }
}

@media (max-width: 640px) {
  .dashboard { padding: 8px; padding-bottom: 80px; }
  .edit-fab { bottom: 16px; right: 16px; }
  .edit-toolbar { padding: 8px 10px; gap: 8px; }
  .edit-hint { font-size: 10px; }

  /* Break the height:100% chain — let cards size to their own content */
  .grid { grid-auto-rows: auto; }
  .grid-item { overflow: visible; }
  .widget-body { height: auto !important; overflow: visible; }
  .widget-body :deep(.card) { height: auto !important; }
  .widget-body :deep(.card-body) {
    flex: none !important;
    min-height: 120px !important;
    overflow: auto !important;
  }
  /* Give sparklines and chart areas an explicit pixel height so charts render */
  .widget-body :deep(.sparkline-wrap) { height: 48px !important; min-height: 48px !important; }
  .widget-body :deep(.chart-area) { min-height: 80px !important; }
}

/* Edit mode overlay on the same grid */
.grid-edit { user-select: none; }
.grid-edit .grid-item {
  overflow: visible;   /* allow resize handles to extend outside the cell */
  position: relative;
  border: 1.5px dashed var(--accent-border);
  border-radius: var(--radius);
  box-sizing: border-box;
  cursor: move;
  transition: box-shadow 80ms, border-color 80ms;
}
.grid-edit .grid-item:hover { border-color: var(--accent); }
.grid-edit .grid-item.is-active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-border), var(--shadow-card-hover);
  z-index: 20;
}

/* Edit FAB */
.edit-fab {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 50;
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--fg-muted);
  font-family: var(--font);
  font-size: 18px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-card);
  transition: all var(--transition);
}
.edit-fab:hover { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }

/* Edit toolbar */
.edit-toolbar {
  position: sticky;
  top: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  margin-bottom: 10px;
  background: var(--bg-card);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius);
  box-shadow: 0 0 0 1px var(--accent-border);
}
.edit-hint { font-size: 11px; color: var(--fg-muted); flex: 1; }
.tb-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-muted);
  font-family: var(--font);
  font-size: 11px;
  padding: 4px 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
}
.tb-btn:hover { border-color: var(--fg-dim); color: var(--fg); }
.tb-done { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }
.tb-done:hover { background: var(--accent-dim); filter: brightness(1.1); }

.toolbar-enter-active, .toolbar-leave-active { transition: opacity 150ms, transform 150ms; }
.toolbar-enter-from, .toolbar-leave-to { opacity: 0; transform: translateY(-6px); }

/* Widget body — always present so card height matches the grid cell in both modes */
.widget-body {
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: calc(var(--radius) - 2px);
}
/* Disable interaction only while editing */
.no-pe { pointer-events: none; }

/* Force BaseCard to fill the cell and flex its body */
.widget-body :deep(.card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.widget-body :deep(.card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

/* Corner resize handles */
.handle {
  position: absolute;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--accent);
  border: 2px solid var(--bg-card);
  z-index: 10;
  opacity: 0;
  transition: opacity var(--transition), transform var(--transition);
}
.grid-edit .grid-item:hover .handle,
.grid-edit .grid-item.is-active .handle { opacity: 1; }
.handle.tl { top: -6px;    left: -6px;    cursor: nwse-resize; }
.handle.tr { top: -6px;    right: -6px;   cursor: nesw-resize; }
.handle.bl { bottom: -6px; left: -6px;    cursor: nesw-resize; }
.handle.br { bottom: -6px; right: -6px;   cursor: nwse-resize; }
.handle:hover { transform: scale(1.3); }
</style>
