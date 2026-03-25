<template>
  <BaseCard>
    <template #header>
      <span class="card-title">Disk</span>
      <span class="badge badge-gray">{{ disks.length }} partition{{ disks.length !== 1 ? 's' : '' }}</span>
    </template>

    <div class="disk-summary">
      <div class="summary-top">
        <div class="space-numbers">
          <span class="used-val">{{ total.used.toFixed(1) }}</span>
          <span class="sep"> / </span>
          <span class="total-val">{{ total.total.toFixed(1) }} GB</span>
        </div>
        <span :class="['badge', pctBadge(total.pct)]">{{ total.pct.toFixed(1) }}%</span>
      </div>

      <div class="bar-track">
        <div class="bar-fill" :style="{ width: total.pct + '%', background: barColor(total.pct) }" />
      </div>

      <div class="io-totals">
        <span class="io-item io-read">
          <span class="io-arrow">↑</span>
          <span class="io-val">{{ total.read.toFixed(2) }}</span>
          <span class="io-unit">MB/s read</span>
        </span>
        <span class="io-item io-write">
          <span class="io-arrow">↓</span>
          <span class="io-val">{{ total.write.toFixed(2) }}</span>
          <span class="io-unit">MB/s write</span>
        </span>
      </div>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import type { DiskMetrics } from '@/types/metrics'

const props = defineProps<{ disks: DiskMetrics[] }>()

const total = computed(() => {
  let used = 0, totalGb = 0, read = 0, write = 0
  for (const d of props.disks) {
    used += d.used_gb
    totalGb += d.total_gb
    read += d.read_mb_s
    write += d.write_mb_s
  }
  const pct = totalGb > 0 ? (used / totalGb) * 100 : 0
  return { used, total: totalGb, pct, read, write }
})

function barColor(pct: number) {
  if (pct < 70) return 'var(--accent)'
  if (pct < 85) return 'var(--warning)'
  return 'var(--danger)'
}
function pctBadge(pct: number) {
  if (pct < 70) return 'badge badge-green'
  if (pct < 85) return 'badge badge-yellow'
  return 'badge badge-red'
}
</script>

<style scoped>
.card-title { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-muted); }

.disk-summary { display: flex; flex-direction: column; gap: 10px; }

.summary-top { display: flex; justify-content: space-between; align-items: baseline; }

.space-numbers { display: flex; align-items: baseline; gap: 2px; }
.used-val { font-size: 20px; font-weight: 700; color: var(--accent); }
.sep { color: var(--fg-dim); }
.total-val { font-size: 13px; color: var(--fg-muted); }

.bar-track { height: 8px; background: var(--bg-subtle); border-radius: 4px; overflow: hidden; transition: background var(--transition); }
.bar-track:hover { background: var(--bg-hover); }
.bar-fill { height: 100%; border-radius: 4px; transition: width var(--bar-transition), background var(--transition); }

.io-totals { display: flex; gap: 20px; }
.io-item { display: flex; align-items: center; gap: 4px; }
.io-arrow { font-size: 10px; }
.io-val { font-size: 14px; font-weight: 600; }
.io-unit { font-size: 10px; color: var(--fg-dim); }
.io-read .io-arrow, .io-read .io-val { color: var(--accent); }
.io-write .io-arrow, .io-write .io-val { color: #60a5fa; }
</style>
