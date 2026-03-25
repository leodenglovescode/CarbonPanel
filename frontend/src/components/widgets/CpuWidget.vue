<template>
  <BaseCard>
    <template #header>
      <span class="card-title">CPU</span>
      <div class="header-right">
        <span class="badge badge-gray">{{ cpu.per_core.length }} cores</span>
        <span class="badge badge-gray">{{ cpu.frequency_mhz.toFixed(0) }} MHz</span>
        <span :class="['badge', pctBadge(cpu.aggregate)]">{{ cpu.aggregate.toFixed(1) }}%</span>
      </div>
    </template>

    <div class="cpu-layout">
      <RingChart :value="cpu.aggregate" :size="88" />

      <div class="cpu-stats">
        <div class="agg-bar-wrap">
          <div class="bar-track">
            <div class="bar-fill" :style="{ width: cpu.aggregate + '%', background: barColor(cpu.aggregate) }" />
          </div>
        </div>

        <div class="load-row">
          <div v-for="(val, i) in cpu.load_avg" :key="i" class="load-item">
            <span class="load-val" :class="loadColor(val)">{{ val?.toFixed(2) }}</span>
            <span class="load-lbl">{{ ['1m','5m','15m'][i] }}</span>
          </div>
          <div class="load-item load-sep">
            <span class="load-val">{{ cpu.per_core.filter(p => p > 5).length }}</span>
            <span class="load-lbl">active</span>
          </div>
        </div>
      </div>
    </div>

    <div class="sparkline-row">
      <Sparkline :data="history" :height="30" />
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import BaseCard from '@/components/ui/BaseCard.vue'
import RingChart from '@/components/charts/RingChart.vue'
import Sparkline from '@/components/charts/Sparkline.vue'
import type { CpuMetrics } from '@/types/metrics'

defineProps<{ cpu: CpuMetrics; history: number[] }>()

function barColor(pct: number) {
  if (pct < 60) return 'var(--accent)'
  if (pct < 85) return 'var(--warning)'
  return 'var(--danger)'
}
function pctBadge(pct: number) {
  if (pct < 60) return 'badge badge-green'
  if (pct < 85) return 'badge badge-yellow'
  return 'badge badge-red'
}
function loadColor(val: number) {
  if (val > 2) return 'text-danger'
  if (val > 1) return 'text-warning'
  return ''
}
</script>

<style scoped>
.card-title { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-muted); }
.header-right { display: flex; align-items: center; gap: 5px; }

.cpu-layout { display: flex; gap: 16px; align-items: center; }

.cpu-stats { flex: 1; display: flex; flex-direction: column; gap: 12px; min-width: 0; }

.agg-bar-wrap {}
.bar-track {
  height: 8px;
  background: rgba(128,128,128,0.1);
  border-radius: 4px;
  overflow: hidden;
  cursor: default;
}
.bar-track:hover { background: rgba(128,128,128,0.15); }
.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width var(--bar-transition), background var(--transition);
}

.load-row { display: flex; gap: 18px; align-items: flex-end; }
.load-item { display: flex; flex-direction: column; gap: 1px; }
.load-sep { border-left: 1px solid var(--border); padding-left: 18px; }
.load-val { font-size: 16px; font-weight: 700; color: var(--fg); letter-spacing: -0.02em; }
.load-lbl { font-size: 9px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: 0.06em; }

.sparkline-row { margin-top: 10px; }
</style>
