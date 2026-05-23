<template>
  <BaseCard>
    <template #header>
      <span class="card-title">{{ t('widgets.bandwidth') }}</span>
      <span class="badge badge-gray">{{ network.length }} iface{{ network.length !== 1 ? 's' : '' }}</span>
    </template>

    <div v-if="!network.length" class="no-data">No interfaces.</div>

    <div v-else class="bw-list">
      <div v-for="iface in visibleNetwork" :key="iface.interface" class="bw-row">
        <div class="iface-name">{{ iface.interface }}</div>
        <div class="bw-bars">
          <div class="bw-bar-item">
            <span class="bw-lbl rx">↓ rx</span>
            <div class="bar-track">
              <div class="bar-fill rx-fill" :style="{ width: rxPct(iface) + '%' }" />
            </div>
            <span class="bw-val">{{ fmtTotal(iface.rx_total_mb) }}</span>
          </div>
          <div class="bw-bar-item">
            <span class="bw-lbl tx">↑ tx</span>
            <div class="bar-track">
              <div class="bar-fill tx-fill" :style="{ width: txPct(iface) + '%' }" />
            </div>
            <span class="bw-val">{{ fmtTotal(iface.tx_total_mb) }}</span>
          </div>
        </div>
      </div>

      <button v-if="extraCount > 0 || expanded" class="show-more" @click="expanded = !expanded">
        {{ expanded ? '▲ show less' : `▼ +${extraCount} more` }}
      </button>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import type { NetworkMetrics } from '@/types/metrics'
import { useLocaleStore } from '@/stores/locale'

const { t } = useLocaleStore()
const props = defineProps<{ network: NetworkMetrics[] }>()

const _LIMIT = 3
const expanded = ref(false)
const visibleNetwork = computed(() => expanded.value ? props.network : props.network.slice(0, _LIMIT))
const extraCount = computed(() => Math.max(0, props.network.length - _LIMIT))

const maxTotal = computed(() =>
  Math.max(...props.network.map(n => Math.max(n.rx_total_mb, n.tx_total_mb)), 1),
)

function rxPct(iface: NetworkMetrics) { return (iface.rx_total_mb / maxTotal.value) * 100 }
function txPct(iface: NetworkMetrics) { return (iface.tx_total_mb / maxTotal.value) * 100 }

function fmtTotal(mb: number) {
  if (mb >= 1024 * 1024) return (mb / (1024 * 1024)).toFixed(2) + ' TB'
  if (mb >= 1024) return (mb / 1024).toFixed(1) + ' GB'
  return mb.toFixed(0) + ' MB'
}
</script>

<style scoped>
.card-title { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-muted); }
.no-data { font-size: 11px; color: var(--fg-dim); }
.bw-list { display: flex; flex-direction: column; gap: 12px; }
.bw-row { display: flex; flex-direction: column; gap: 6px; }
.iface-name { font-size: 11px; font-weight: 600; color: var(--fg); }
.bw-bars { display: flex; flex-direction: column; gap: 5px; }
.bw-bar-item { display: flex; align-items: center; gap: 8px; }
.bw-lbl { font-size: 9px; font-weight: 600; width: 26px; flex-shrink: 0; }
.bw-lbl.rx { color: var(--accent); }
.bw-lbl.tx { color: #60a5fa; }
.bar-track { flex: 1; height: 6px; background: var(--bg-subtle); border-radius: 3px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.rx-fill { background: var(--accent); }
.tx-fill { background: #60a5fa; }
.bw-val { font-size: 10px; color: var(--fg-muted); width: 64px; text-align: right; flex-shrink: 0; font-variant-numeric: tabular-nums; }
@container (max-width: 180px) { .bw-val { display: none; } }
@container (max-width: 130px) { .bw-bars { display: none; } }
.show-more { background: none; border: none; color: var(--fg-dim); font-family: var(--font); font-size: 10px; padding: 2px 0; cursor: pointer; text-align: left; transition: color var(--transition); }
.show-more:hover { color: var(--accent); }
</style>
