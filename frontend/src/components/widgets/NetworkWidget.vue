<template>
  <BaseCard>
    <template #header>
      <span class="card-title">Network</span>
      <span class="badge badge-gray">{{ network.length }} interface{{ network.length !== 1 ? 's' : '' }}</span>
      <span v-if="network.length > 2" class="badge badge-gray">showing top 2</span>
    </template>

    <div class="net-list">
      <div v-for="iface in visibleNetwork" :key="iface.interface" class="net-row">
        <span class="iface-name">{{ iface.interface }}</span>

        <div class="rate-group">
          <span class="rate rx">
            <span class="arrow">↓</span>
            <span class="rate-val">{{ fmtRate(iface.rx_mb_s) }}</span>
            <span class="rate-unit">MB/s</span>
          </span>
          <span class="rate tx">
            <span class="arrow">↑</span>
            <span class="rate-val">{{ fmtRate(iface.tx_mb_s) }}</span>
            <span class="rate-unit">MB/s</span>
          </span>
        </div>

        <div class="sparklines">
          <Sparkline :data="rxHistory[iface.interface] || []" :height="22" color="#00ff88" :maxY="sparkMax(iface.interface, 'rx')" />
          <Sparkline :data="txHistory[iface.interface] || []" :height="22" color="#60a5fa" :maxY="sparkMax(iface.interface, 'tx')" />
        </div>

        <div class="totals">
          <span class="total rx-total">{{ fmtTotal(iface.rx_total_mb) }} rx</span>
          <span class="total tx-total">{{ fmtTotal(iface.tx_total_mb) }} tx</span>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import Sparkline from '@/components/charts/Sparkline.vue'
import type { NetworkMetrics } from '@/types/metrics'

const props = defineProps<{
  network: NetworkMetrics[]
  rxHistory: Record<string, number[]>
  txHistory: Record<string, number[]>
}>()

const visibleNetwork = computed(() => props.network.slice(0, 2))

function fmtRate(mb: number) { return mb.toFixed(2) }
function fmtTotal(mb: number) {
  if (mb >= 1024) return (mb / 1024).toFixed(1) + ' GB'
  return mb.toFixed(0) + ' MB'
}
function sparkMax(iface: string, dir: 'rx' | 'tx') {
  const hist = dir === 'rx' ? props.rxHistory[iface] : props.txHistory[iface]
  if (!hist?.length) return 1
  return Math.max(...hist, 1) * 1.2
}
</script>

<style scoped>
.card-title { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-muted); }

.net-list { display: flex; flex-direction: column; gap: 10px; }
.net-row {
  display: grid;
  grid-template-columns: 90px auto 1fr 140px;
  align-items: center;
  gap: 14px;
  padding: 5px 0;
}
.net-row + .net-row { border-top: 1px solid var(--border-subtle); }

.iface-name { font-size: 11px; font-weight: 600; color: var(--fg); }

.rate-group { display: flex; gap: 12px; }
.rate { display: flex; align-items: center; gap: 3px; }
.arrow { font-size: 10px; }
.rate-val { font-size: 13px; font-weight: 600; }
.rate-unit { font-size: 9px; color: var(--fg-dim); }
.rx .arrow, .rx .rate-val { color: var(--accent); }
.tx .arrow, .tx .rate-val { color: #60a5fa; }

.sparklines { display: flex; flex-direction: column; gap: 2px; min-width: 0; }

.totals { display: flex; flex-direction: column; gap: 2px; text-align: right; }
.total { font-size: 10px; }
.rx-total { color: var(--fg-muted); }
.tx-total { color: var(--fg-dim); }
</style>
