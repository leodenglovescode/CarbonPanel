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

    <div v-if="!metrics.latest" class="loading">
      <span class="loading-dot" /><span class="loading-dot" /><span class="loading-dot" />
      <span class="loading-text">connecting…</span>
    </div>

    <!-- ── Normal mode ── -->
    <div v-else-if="!editMode" class="grid">
      <div class="grid-item span-6">
        <CpuWidget :cpu="metrics.latest.cpu" :history="metrics.cpuHistory" />
      </div>
      <div class="grid-item span-6">
        <RamWidget :mem="metrics.latest.memory" :history="metrics.memHistory" />
      </div>

      <div v-if="metrics.latest.gpu.available" class="grid-item span-6">
        <GpuWidget :gpu="metrics.latest.gpu" :history="metrics.gpuHistory" />
      </div>
      <div :class="['grid-item', metrics.latest.gpu.available ? 'span-6' : 'span-12']">
        <SystemWidget :system="metrics.latest.system" :cpu="metrics.latest.cpu" />
      </div>

      <div class="grid-item span-12">
        <DiskWidget :disks="metrics.latest.disks" />
      </div>

      <div class="grid-item span-12">
        <NetworkWidget
          :network="metrics.latest.network"
          :rx-history="metrics.netRxHistory"
          :tx-history="metrics.netTxHistory"
        />
      </div>

      <div v-if="metrics.latest.cpu.temps.length" class="grid-item span-6">
        <CpuTempWidget :temps="metrics.latest.cpu.temps" />
      </div>
      <div :class="['grid-item', metrics.latest.cpu.temps.length ? 'span-6' : 'span-12']">
        <BandwidthWidget :network="metrics.latest.network" />
      </div>

      <div class="grid-item span-12">
        <HistoryWidget :points="historyPoints" />
      </div>

      <div class="grid-item span-12">
        <ProcessListWidget
          :processes="metrics.latest.processes"
          @sort-change="onSortChange"
        />
      </div>
    </div>

    <!-- ── Edit mode grid ── -->
    <div
      v-else
      ref="gridEl"
      class="edit-grid"
      :style="{ height: editGridHeight + 'px' }"
    >
      <div
        v-for="w in visibleWidgets"
        :key="w.id"
        class="edit-widget"
        :class="{ 'is-active': drag?.id === w.id }"
        :style="widgetStyle(w.id)"
        @mousedown.left.prevent="startDrag(w.id, $event)"
      >
        <div class="widget-body">
          <component :is="w.comp" v-bind="w.props" />
        </div>
        <div class="handle tl" @mousedown.left.stop.prevent="startResize(w.id, 'tl', $event)" />
        <div class="handle tr" @mousedown.left.stop.prevent="startResize(w.id, 'tr', $event)" />
        <div class="handle bl" @mousedown.left.stop.prevent="startResize(w.id, 'bl', $event)" />
        <div class="handle br" @mousedown.left.stop.prevent="startResize(w.id, 'br', $event)" />
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

// Grid constants
const COLS = 12
const ROW_H = 30   // px per row unit
const GAP = 6      // px gap
const MIN_W = 3
const MIN_H = 3

const cellW = computed(() => {
  const w = gridW.value || 1200
  return (w - GAP * (COLS - 1)) / COLS
})

function toPixels(id: WidgetId) {
  const p = layoutStore.layout[id]
  const cw = cellW.value
  return {
    left:   p.col * (cw + GAP),
    top:    p.row * (ROW_H + GAP),
    width:  p.w  * cw  + (p.w - 1) * GAP,
    height: p.h  * ROW_H + (p.h - 1) * GAP,
  }
}

function widgetStyle(id: WidgetId) {
  const px = toPixels(id)
  return {
    left:   px.left   + 'px',
    top:    px.top    + 'px',
    width:  px.width  + 'px',
    height: px.height + 'px',
  }
}

const editGridHeight = computed(() => {
  let maxRow = 0
  for (const id of Object.keys(layoutStore.layout) as WidgetId[]) {
    const p = layoutStore.layout[id]
    const bottom = p.row + p.h
    if (bottom > maxRow) maxRow = bottom
  }
  return maxRow * (ROW_H + GAP) + 20
})

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

function onMouseMove(e: MouseEvent) {
  const d = drag.value
  if (!d) return

  const cw = cellW.value
  const dcol = Math.round((e.clientX - d.mx0) / (cw + GAP))
  const drow = Math.round((e.clientY - d.my0) / (ROW_H + GAP))

  if (d.type === 'drag') {
    layoutStore.update(d.id, {
      col: Math.max(0, Math.min(COLS - d.w0, d.col0 + dcol)),
      row: Math.max(0, d.row0 + drow),
    })
    return
  }

  // Resize
  switch (d.corner) {
    case 'br':
      layoutStore.update(d.id, {
        w: Math.max(MIN_W, Math.min(COLS - d.col0, d.w0 + dcol)),
        h: Math.max(MIN_H, d.h0 + drow),
      })
      break
    case 'bl': {
      const nc = Math.max(0, Math.min(d.col0 + d.w0 - MIN_W, d.col0 + dcol))
      layoutStore.update(d.id, {
        col: nc, w: d.w0 + d.col0 - nc,
        h: Math.max(MIN_H, d.h0 + drow),
      })
      break
    }
    case 'tr': {
      const nr = Math.max(0, Math.min(d.row0 + d.h0 - MIN_H, d.row0 + drow))
      layoutStore.update(d.id, {
        row: nr, h: d.h0 + d.row0 - nr,
        w: Math.max(MIN_W, Math.min(COLS - d.col0, d.w0 + dcol)),
      })
      break
    }
    case 'tl': {
      const nc = Math.max(0, Math.min(d.col0 + d.w0 - MIN_W, d.col0 + dcol))
      const nr = Math.max(0, Math.min(d.row0 + d.h0 - MIN_H, d.row0 + drow))
      layoutStore.update(d.id, {
        col: nc, row: nr,
        w: d.w0 + d.col0 - nc,
        h: d.h0 + d.row0 - nr,
      })
      break
    }
  }
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
  // Measure container width after render
  requestAnimationFrame(() => {
    if (gridEl.value) gridW.value = gridEl.value.clientWidth
  })
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
  if (!m) return []
  return [
    { id: 'cpu'       as WidgetId, comp: CpuWidget,         props: { cpu: m.cpu, history: metrics.cpuHistory },                                            show: true },
    { id: 'ram'       as WidgetId, comp: RamWidget,         props: { mem: m.memory, history: metrics.memHistory },                                         show: true },
    { id: 'gpu'       as WidgetId, comp: GpuWidget,         props: { gpu: m.gpu, history: metrics.gpuHistory },                                            show: m.gpu.available },
    { id: 'system'    as WidgetId, comp: SystemWidget,      props: { system: m.system, cpu: m.cpu },                                                       show: true },
    { id: 'disk'      as WidgetId, comp: DiskWidget,        props: { disks: m.disks },                                                                     show: true },
    { id: 'network'   as WidgetId, comp: NetworkWidget,     props: { network: m.network, rxHistory: metrics.netRxHistory, txHistory: metrics.netTxHistory }, show: true },
    { id: 'cpuTemp'   as WidgetId, comp: CpuTempWidget,     props: { temps: m.cpu.temps },                                                                 show: m.cpu.temps.length > 0 },
    { id: 'bandwidth' as WidgetId, comp: BandwidthWidget,   props: { network: m.network },                                                                 show: true },
    { id: 'history'   as WidgetId, comp: HistoryWidget,     props: { points: historyPoints.value },                                                        show: true },
    { id: 'processes' as WidgetId, comp: ProcessListWidget, props: { processes: m.processes, onSortChange },                                               show: true },
  ].filter(w => w.show)
})
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

/* Normal grid */
.grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 10px; }
.span-6 { grid-column: span 6; }
.span-12 { grid-column: span 12; }
.grid-item { min-width: 0; }
@media (max-width: 900px) { .span-6 { grid-column: span 12; } }

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

/* Edit grid */
.edit-grid {
  position: relative;
  width: 100%;
  user-select: none;
}

/* Individual widget in edit mode */
.edit-widget {
  position: absolute;
  border: 1.5px dashed var(--accent-border);
  border-radius: var(--radius);
  box-sizing: border-box;
  cursor: move;
  transition: box-shadow 80ms, border-color 80ms;
  overflow: visible;
}
.edit-widget:hover { border-color: var(--accent); }
.edit-widget.is-active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-border), var(--shadow-card-hover);
  z-index: 20;
}

/* Widget inner content: disable pointer events while editing */
.widget-body {
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: hidden;
  border-radius: calc(var(--radius) - 2px);
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
.edit-widget:hover .handle,
.edit-widget.is-active .handle { opacity: 1; }
.handle.tl { top: -6px;    left: -6px;    cursor: nwse-resize; }
.handle.tr { top: -6px;    right: -6px;   cursor: nesw-resize; }
.handle.bl { bottom: -6px; left: -6px;    cursor: nesw-resize; }
.handle.br { bottom: -6px; right: -6px;   cursor: nwse-resize; }
.handle:hover { transform: scale(1.3); }
</style>
