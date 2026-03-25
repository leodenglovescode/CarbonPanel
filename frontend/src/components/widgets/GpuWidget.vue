<template>
  <BaseCard>
    <template #header>
      <span class="card-title">GPU</span>
      <span class="badge badge-gray">{{ gpu.devices.length }} device{{ gpu.devices.length !== 1 ? 's' : '' }}</span>
    </template>

    <div v-for="dev in gpu.devices" :key="dev.index" class="gpu-device">
      <div class="dev-header">
        <span class="dev-name">{{ dev.name }}</span>
        <span :class="['badge', tempBadge(dev.temperature_c)]">{{ dev.temperature_c }}°C</span>
      </div>

      <div class="dev-metrics">
        <RingChart :value="dev.utilization_percent" :size="72" />
        <div class="dev-stats">
          <div class="stat-row">
            <span class="stat-lbl">util</span>
            <div class="bar-track">
              <div class="bar-fill util" :style="{ width: dev.utilization_percent + '%' }" />
            </div>
            <span class="stat-val">{{ dev.utilization_percent.toFixed(0) }}%</span>
          </div>
          <div class="stat-row">
            <span class="stat-lbl">vram</span>
            <div class="bar-track">
              <div class="bar-fill vram" :style="{ width: (dev.memory_used_mb / dev.memory_total_mb * 100) + '%' }" />
            </div>
            <span class="stat-val">{{ fmt(dev.memory_used_mb) }} / {{ fmt(dev.memory_total_mb) }} MB</span>
          </div>
          <div class="stat-row">
            <span class="stat-lbl">pwr</span>
            <span class="stat-plain">{{ dev.power_draw_w.toFixed(0) }} W</span>
          </div>
        </div>
      </div>

      <div class="sparkline-row">
        <Sparkline :data="history" :height="28" color="#a78bfa" />
      </div>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import BaseCard from '@/components/ui/BaseCard.vue'
import RingChart from '@/components/charts/RingChart.vue'
import Sparkline from '@/components/charts/Sparkline.vue'
import type { GpuMetrics } from '@/types/metrics'

defineProps<{ gpu: GpuMetrics; history: number[] }>()

function tempBadge(t: number) {
  if (t < 70) return 'badge badge-green'
  if (t < 85) return 'badge badge-yellow'
  return 'badge badge-red'
}
function fmt(mb: number) { return mb >= 1024 ? (mb / 1024).toFixed(1) + ' GB' : mb.toFixed(0) + ' MB' }
</script>

<style scoped>
.card-title { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-muted); }
.gpu-device + .gpu-device { margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--border-subtle); }

.dev-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.dev-name { font-size: 11px; color: var(--fg); font-weight: 500; }

.dev-metrics { display: flex; gap: 14px; align-items: center; }
.dev-stats { flex: 1; display: flex; flex-direction: column; gap: 6px; min-width: 0; }

.stat-row { display: flex; align-items: center; gap: 7px; }
.stat-lbl { font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg-dim); width: 26px; flex-shrink: 0; }
.bar-track { flex: 1; height: 5px; background: var(--bg-subtle); border-radius: 2px; overflow: hidden; transition: background var(--transition); }
.bar-fill { height: 100%; border-radius: 2px; transition: width var(--bar-transition); }
.bar-fill.util { background: #a78bfa; }
.bar-fill.vram { background: #60a5fa; }
.stat-val { font-size: 10px; color: var(--fg-muted); white-space: nowrap; }
.stat-plain { font-size: 11px; color: var(--fg); }

.sparkline-row { margin-top: 10px; }
</style>
