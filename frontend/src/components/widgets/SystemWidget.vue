<template>
  <BaseCard>
    <template #header>
      <span class="card-title">System</span>
      <span class="badge badge-green">online</span>
    </template>

    <div class="sys-layout">
      <div class="uptime-block">
        <div class="uptime-label">uptime</div>
        <div class="uptime-val">{{ formatUptime(system.uptime_seconds) }}</div>
      </div>

      <div class="load-block">
        <div class="load-label">load average</div>
        <div class="load-grid">
          <div v-for="(val, i) in system_load" :key="i" class="load-item">
            <span class="load-num" :class="loadColor(val)">{{ val.toFixed(2) }}</span>
            <span class="load-period">{{ ['1m', '5m', '15m'][i] }}</span>
          </div>
        </div>
      </div>

      <div class="host-block">
        <div class="host-label">hostname</div>
        <div class="host-val">{{ system.hostname }}</div>
      </div>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import BaseCard from '@/components/ui/BaseCard.vue'
import type { SystemMetrics, CpuMetrics } from '@/types/metrics'
import { computed } from 'vue'

const props = defineProps<{ system: SystemMetrics; cpu: CpuMetrics }>()

const system_load = computed(() => props.cpu.load_avg)

function formatUptime(s: number): string {
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  const parts = []
  if (d > 0) parts.push(`${d}d`)
  if (h > 0) parts.push(`${h}h`)
  parts.push(`${m}m`)
  return parts.join(' ')
}

function loadColor(val: number) {
  if (val > 2) return 'text-danger'
  if (val > 1) return 'text-warning'
  return 'text-accent'
}
</script>

<style scoped>
.card-title { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-muted); }

.sys-layout { display: flex; flex-direction: column; gap: 16px; }

.uptime-block, .load-block, .host-block {}
.uptime-label, .load-label, .host-label {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--fg-dim);
  margin-bottom: 4px;
}

.uptime-val { font-size: 22px; font-weight: 700; color: var(--accent); letter-spacing: -0.02em; }

.load-grid { display: flex; gap: 20px; }
.load-item { display: flex; flex-direction: column; gap: 2px; }
.load-num { font-size: 18px; font-weight: 700; letter-spacing: -0.02em; }
.load-period { font-size: 9px; color: var(--fg-dim); text-transform: uppercase; }

.host-val { font-size: 13px; font-weight: 600; color: var(--fg); }
</style>
