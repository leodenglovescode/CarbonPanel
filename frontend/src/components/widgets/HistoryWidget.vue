<template>
  <BaseCard>
    <template #header>
      <span class="card-title">{{ t('widgets.history') }}</span>
      <div class="header-tabs">
        <button v-for="tab in tabs" :key="tab" :class="['tab-btn', { active: activeTab === tab }]" @click="activeTab = tab">{{ tab }}</button>
      </div>
    </template>

    <div v-if="!points.length" class="no-data">Collecting data…</div>

    <div v-else class="chart-area">
      <svg :viewBox="`0 0 ${W} ${H}`" class="chart-svg" preserveAspectRatio="none">
        <defs>
          <linearGradient :id="`grad-${activeTab}`" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" :stop-color="lineColor" stop-opacity="0.3" />
            <stop offset="100%" :stop-color="lineColor" stop-opacity="0" />
          </linearGradient>
        </defs>
        <path :d="areaPath" :fill="`url(#grad-${activeTab})`" />
        <path :d="linePath" :stroke="lineColor" stroke-width="1.5" fill="none" />
      </svg>
      <div class="y-labels">
        <span>100%</span>
        <span>50%</span>
        <span>0%</span>
      </div>
    </div>

    <div class="legend">
      <span v-for="tab in tabs" :key="tab" class="legend-item">
        <span class="legend-dot" :style="{ background: colorFor(tab) }" />
        {{ tab }}
      </span>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import { useLocaleStore } from '@/stores/locale'

const { t } = useLocaleStore()

interface HistoryPoint { ts: number; cpu: number; mem: number; gpu?: number | null }
const props = defineProps<{ points: HistoryPoint[] }>()

const W = 400
const H = 80
const tabs = ['CPU', 'MEM', 'GPU'] as const
type Tab = typeof tabs[number]
const activeTab = ref<Tab>('CPU')

function colorFor(tab: Tab) {
  if (tab === 'CPU') return 'var(--accent)'
  if (tab === 'MEM') return '#60a5fa'
  return '#a78bfa'
}
const lineColor = computed(() => colorFor(activeTab.value))

const values = computed<number[]>(() => {
  return props.points.map(p => {
    if (activeTab.value === 'CPU') return p.cpu
    if (activeTab.value === 'MEM') return p.mem
    return p.gpu ?? 0
  })
})

function toPath(pts: number[], fill: boolean): string {
  if (!pts.length) return ''
  const n = pts.length
  const coords = pts.map((v, i) => {
    const x = (i / Math.max(n - 1, 1)) * W
    const y = H - (Math.max(0, Math.min(100, v)) / 100) * H
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  const line = 'M' + coords.join('L')
  if (!fill) return line
  const firstX = (0 / Math.max(n - 1, 1)) * W
  const lastX = ((n - 1) / Math.max(n - 1, 1)) * W
  return `${line}L${lastX.toFixed(1)},${H}L${firstX.toFixed(1)},${H}Z`
}

const linePath = computed(() => toPath(values.value, false))
const areaPath = computed(() => toPath(values.value, true))
</script>

<style scoped>
.card-title { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-muted); }
.header-tabs { display: flex; gap: 4px; }
.tab-btn { background: none; border: 1px solid var(--border); color: var(--fg-dim); font-family: var(--font); font-size: 9px; padding: 2px 7px; border-radius: 3px; cursor: pointer; transition: all var(--transition); }
.tab-btn.active { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }
.tab-btn:hover:not(.active) { color: var(--fg-muted); }

.no-data { font-size: 11px; color: var(--fg-dim); padding: 8px 0; }

.chart-area { position: relative; display: flex; gap: 6px; align-items: stretch; }
.chart-svg { flex: 1; height: 80px; display: block; min-width: 0; }
@container (max-width: 200px) { .chart-area, .legend { display: none; } }
.y-labels { display: flex; flex-direction: column; justify-content: space-between; font-size: 9px; color: var(--fg-dim); padding: 0; text-align: right; width: 28px; flex-shrink: 0; }

.legend { display: flex; gap: 12px; margin-top: 6px; }
.legend-item { display: flex; align-items: center; gap: 5px; font-size: 10px; color: var(--fg-muted); }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
</style>
