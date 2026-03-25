<template>
  <BaseCard>
    <template #header>
      <span class="card-title">Memory</span>
      <span :class="['badge', pctBadge(mem.percent)]">{{ mem.percent.toFixed(1) }}%</span>
    </template>

    <div class="mem-summary">
      <span class="mem-val">{{ fmt(mem.used_mb) }}</span>
      <span class="mem-sep"> / </span>
      <span class="mem-total">{{ fmt(mem.total_mb) }}</span>
      <span class="mem-unit">MB</span>
    </div>

    <div class="bar-track big">
      <div class="bar-fill used" :style="{ width: mem.percent + '%' }" />
    </div>

    <div class="mem-stats">
      <div class="stat">
        <span class="stat-lbl">used</span>
        <span class="stat-val text-accent">{{ fmt(mem.used_mb) }} MB</span>
      </div>
      <div class="stat">
        <span class="stat-lbl">free</span>
        <span class="stat-val">{{ fmt(mem.free_mb) }} MB</span>
      </div>
      <div class="stat">
        <span class="stat-lbl">total</span>
        <span class="stat-val">{{ fmt(mem.total_mb) }} MB</span>
      </div>
    </div>

    <div v-if="mem.swap_total_mb > 0" class="swap-row">
      <span class="swap-lbl">swap</span>
      <div class="bar-track swap">
        <div class="bar-fill swap-fill" :style="{ width: swapPct + '%' }" />
      </div>
      <span class="swap-val">{{ fmt(mem.swap_used_mb) }} / {{ fmt(mem.swap_total_mb) }} MB</span>
    </div>

    <div class="sparkline-row">
      <Sparkline :data="history" :height="30" />
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import Sparkline from '@/components/charts/Sparkline.vue'
import type { MemoryMetrics } from '@/types/metrics'

const props = defineProps<{ mem: MemoryMetrics; history: number[] }>()

const swapPct = computed(() =>
  props.mem.swap_total_mb > 0
    ? (props.mem.swap_used_mb / props.mem.swap_total_mb) * 100
    : 0,
)

function fmt(mb: number) { return mb.toFixed(0) }
function pctBadge(pct: number) {
  if (pct < 70) return 'badge badge-green'
  if (pct < 85) return 'badge badge-yellow'
  return 'badge badge-red'
}
</script>

<style scoped>
.card-title { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-muted); }

.mem-summary { display: flex; align-items: baseline; gap: 2px; margin-bottom: 8px; }
.mem-val { font-size: 20px; font-weight: 700; color: var(--accent); }
.mem-sep { color: var(--fg-dim); }
.mem-total { font-size: 14px; font-weight: 500; color: var(--fg-muted); }
.mem-unit { font-size: 10px; color: var(--fg-dim); margin-left: 3px; }

.bar-track {
  background: rgba(128,128,128,0.1);
  border-radius: 3px;
  overflow: hidden;
  transition: background var(--transition);
}
.bar-track:hover { background: rgba(128,128,128,0.15); }
.bar-track.big { height: 7px; margin-bottom: 10px; }
.bar-fill.used { height: 100%; background: var(--accent); border-radius: 3px; transition: width var(--bar-transition); }

.mem-stats { display: flex; gap: 14px; margin-bottom: 8px; }
.stat { display: flex; flex-direction: column; gap: 1px; }
.stat-lbl { font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg-dim); }
.stat-val { font-size: 11px; color: var(--fg); }

.swap-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.swap-lbl { font-size: 10px; color: var(--fg-dim); width: 28px; flex-shrink: 0; }
.bar-track.swap { flex: 1; height: 5px; }
.bar-fill.swap-fill { height: 100%; background: var(--info, #4488ff); border-radius: 2px; transition: width var(--bar-transition); }
.swap-val { font-size: 10px; color: var(--fg-muted); white-space: nowrap; }

.sparkline-row { margin-top: 4px; }
</style>
