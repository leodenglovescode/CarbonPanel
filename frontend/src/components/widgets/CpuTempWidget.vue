<template>
  <BaseCard>
    <template #header>
      <span class="card-title">{{ t('widgets.cpuTemp') }}</span>
      <span v-if="visibleTemps.length" :class="['badge', maxTempBadge]">{{ maxTemp.toFixed(0) }}°C</span>
    </template>

    <div v-if="!temps.length" class="no-data">No thermal sensors detected.</div>

    <div v-else class="temp-list">
      <div v-for="(temp, i) in visibleTemps" :key="i" class="temp-row">
        <div class="temp-label" :title="temp.label">{{ temp.label }}</div>
        <div class="temp-bar-wrap">
          <div class="temp-bar-track">
            <div
              class="temp-bar-fill"
              :style="{ width: barWidth(temp) + '%', background: barColor(temp.temp_c) }"
            />
          </div>
        </div>
        <div class="temp-val" :style="{ color: barColor(temp.temp_c) }">{{ temp.temp_c.toFixed(0) }}°C</div>
      </div>

      <button v-if="extraCount > 0 || expanded" class="show-more" @click="expanded = !expanded">
        {{ expanded ? '▲ Show less' : `▼ +${extraCount} more` }}
      </button>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import type { CpuTemp } from '@/types/metrics'
import { useLocaleStore } from '@/stores/locale'

const { t } = useLocaleStore()
const props = defineProps<{ temps: CpuTemp[] }>()
const expanded = ref(false)

// "Package" or "Tdie" or similar = the top-level aggregate sensor per chip
const _PACKAGE_KEYWORDS = /package|tdie|tctl|composite|physical/i

const packageTemps = computed(() =>
  props.temps.filter(t => _PACKAGE_KEYWORDS.test(t.label) || _PACKAGE_KEYWORDS.test(t.sensor)),
)

// Default view: package temps only. If none exist, show one entry per sensor (not every core).
const defaultTemps = computed<CpuTemp[]>(() => {
  if (packageTemps.value.length) return packageTemps.value
  // Fall back to one representative per sensor name (first reading)
  const seen = new Set<string>()
  return props.temps.filter(t => {
    if (seen.has(t.sensor)) return false
    seen.add(t.sensor)
    return true
  })
})

const extraTemps = computed(() =>
  props.temps.filter(t => !defaultTemps.value.includes(t)),
)

const extraCount = computed(() => extraTemps.value.length)

const visibleTemps = computed(() =>
  expanded.value ? props.temps : defaultTemps.value,
)

const maxTemp = computed(() =>
  visibleTemps.value.length ? Math.max(...visibleTemps.value.map(t => t.temp_c)) : 0,
)

const maxTempBadge = computed(() => {
  const m = maxTemp.value
  if (m < 60) return 'badge badge-green'
  if (m < 80) return 'badge badge-yellow'
  return 'badge badge-red'
})

function barWidth(temp: CpuTemp): number {
  const max = temp.critical_c ?? temp.high_c ?? 100
  return Math.min((temp.temp_c / max) * 100, 100)
}

function barColor(c: number): string {
  if (c < 60) return 'var(--accent)'
  if (c < 80) return 'var(--warning)'
  return 'var(--danger)'
}
</script>

<style scoped>
.card-title { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-muted); }
.no-data { font-size: 11px; color: var(--fg-dim); padding: 8px 0; }
.temp-list { display: flex; flex-direction: column; gap: 7px; }
.temp-row { display: flex; align-items: center; gap: 8px; }
.temp-label { font-size: 10px; color: var(--fg-muted); width: 90px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.temp-bar-wrap { flex: 1; }
.temp-bar-track { height: 5px; background: var(--bg-subtle); border-radius: 2px; overflow: hidden; }
.temp-bar-fill { height: 100%; border-radius: 2px; transition: width var(--bar-transition), background var(--transition); }
.temp-val { font-size: 11px; font-variant-numeric: tabular-nums; width: 38px; text-align: right; flex-shrink: 0; }
.show-more { background: none; border: none; color: var(--fg-dim); font-family: var(--font); font-size: 10px; padding: 2px 0; cursor: pointer; text-align: left; transition: color var(--transition); }
.show-more:hover { color: var(--accent); }
</style>
