<template>
  <BaseCard>
    <template #header>
      <span class="card-title">Site Traffic</span>
      <select v-model="selectedId" class="site-select" @change="onSiteChange">
        <option value="">select a site…</option>
        <option v-for="s in sites" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
    </template>

    <div v-if="!sites.length" class="empty-state">No sites configured yet.</div>
    <div v-else-if="!selectedId" class="empty-state">Pick a site above to see its traffic.</div>
    <div v-else-if="error" class="empty-state error">{{ error }}</div>
    <div v-else-if="!traffic" class="empty-state">loading…</div>
    <template v-else>
      <div class="headline">
        <div class="stat">
          <span class="stat-val">{{ traffic.total_requests }}</span>
          <span class="stat-lbl">requests / {{ traffic.window_minutes }}m</span>
        </div>
        <div class="stat">
          <span class="stat-val">{{ fmtBytes(traffic.total_bytes) }}</span>
          <span class="stat-lbl">served</span>
        </div>
      </div>

      <div class="status-row">
        <span class="status-badge s2xx">{{ traffic.status_2xx }} 2xx</span>
        <span class="status-badge s3xx">{{ traffic.status_3xx }} 3xx</span>
        <span class="status-badge s4xx">{{ traffic.status_4xx }} 4xx</span>
        <span class="status-badge s5xx">{{ traffic.status_5xx }} 5xx</span>
      </div>

      <div class="sparkline-row">
        <Sparkline :data="counts" :height="40" :max-y="sparkMax" color="var(--accent)" />
      </div>

      <div v-if="traffic.top_paths.length" class="top-row">
        <span class="top-lbl">Top paths</span>
        <span v-for="p in traffic.top_paths.slice(0, 3)" :key="p.value" class="top-chip" :title="p.value">
          {{ p.value }} <b>{{ p.count }}</b>
        </span>
      </div>
      <div v-if="traffic.top_ips.length" class="top-row">
        <span class="top-lbl">Top IPs</span>
        <span v-for="ip in traffic.top_ips.slice(0, 3)" :key="ip.value" class="top-chip">
          {{ ip.value }} <b>{{ ip.count }}</b>
        </span>
      </div>
    </template>
  </BaseCard>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import Sparkline from '@/components/charts/Sparkline.vue'
import { sitesApi } from '@/api'
import type { SiteResponse, SiteTrafficResponse } from '@/types/sites'
import { useSiteTrafficStore } from '@/stores/siteTraffic'
import { useMetricsStore } from '@/stores/metrics'
import { useAlertsStore } from '@/stores/alerts'

// ponytail: fixed threshold instead of a new settings slider — bump to a
// configurable one if a per-site error-rate control is actually requested
const ERROR_RATE_ALERT_PERCENT = 25
const ERROR_RATE_ALERT_MIN_REQUESTS = 20

const metrics = useMetricsStore()
const alerts = useAlertsStore()
const trafficStore = useSiteTrafficStore()
const sites = ref<SiteResponse[]>([])
const selectedId = ref(trafficStore.selectedSiteId || '')
const traffic = ref<SiteTrafficResponse | null>(null)
const error = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

const counts = computed(() => traffic.value?.requests_per_minute.map(b => b.count) ?? [])
const sparkMax = computed(() => Math.max(...counts.value, 1) * 1.2)

function fmtBytes(n: number): string {
  if (n >= 1024 * 1024) return (n / (1024 * 1024)).toFixed(1) + ' MB'
  if (n >= 1024) return (n / 1024).toFixed(1) + ' KB'
  return n + ' B'
}

async function loadTraffic() {
  if (!selectedId.value) {
    traffic.value = null
    return
  }
  try {
    const { data } = await sitesApi.traffic(selectedId.value)
    traffic.value = data
    error.value = ''
    checkErrorRate(data)
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to load traffic'
  }
}

function checkErrorRate(data: SiteTrafficResponse) {
  if (data.total_requests < ERROR_RATE_ALERT_MIN_REQUESTS) return
  const rate = (data.status_5xx / data.total_requests) * 100
  if (rate < ERROR_RATE_ALERT_PERCENT) return
  const name = sites.value.find(s => s.id === data.site_id)?.name || data.site_id
  alerts.fire(
    `site_5xx_${data.site_id}`,
    `${name}: ${rate.toFixed(0)}% of requests are 5xx (${data.status_5xx}/${data.total_requests})`,
    'danger',
    { event: 'alert.site_5xx', metric: `site:${data.site_id}:5xx_rate`, value: rate, threshold: ERROR_RATE_ALERT_PERCENT },
  )
}

function onSiteChange() {
  trafficStore.setSelectedSiteId(selectedId.value || null)
  traffic.value = null
  void loadTraffic()
}

watch(() => trafficStore.selectedSiteId, (id) => {
  if (id !== selectedId.value) selectedId.value = id || ''
})

function restartPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(loadTraffic, metrics.updateInterval * 1000)
}

// Same update-interval slider that drives the live metrics WS — one setting for all "live" widgets
watch(() => metrics.updateInterval, restartPolling)

onMounted(async () => {
  try {
    const { data } = await sitesApi.list()
    sites.value = data
    if (selectedId.value && !data.some(s => s.id === selectedId.value)) selectedId.value = ''
  } catch { /* silent */ }
  void loadTraffic()
  restartPolling()
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.card-title { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-muted); }

.site-select {
  background: var(--bg-input); border: 1px solid var(--border); color: var(--fg);
  font-family: var(--font); font-size: 10px; padding: 3px 6px; border-radius: var(--radius-sm);
  outline: none; cursor: pointer; max-width: 120px;
}
.site-select:focus { border-color: var(--accent-border); }

.empty-state { font-size: 11px; color: var(--fg-dim); padding: 4px 0; }
.empty-state.error { color: var(--danger); }

.headline { display: flex; gap: 20px; margin-bottom: 10px; }
.stat { display: flex; flex-direction: column; gap: 2px; }
.stat-val { font-size: 18px; font-weight: 700; color: var(--fg); letter-spacing: -0.02em; }
.stat-lbl { font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg-dim); }

.status-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
.status-badge { font-size: 9px; font-weight: 600; padding: 2px 7px; border-radius: 20px; }
.s2xx { background: var(--accent-dim); color: var(--accent); }
.s3xx { background: rgba(68,136,255,0.1); color: var(--info); }
.s4xx { background: var(--warning-dim); color: var(--warning); }
.s5xx { background: var(--danger-dim); color: var(--danger); }

.sparkline-row { margin-top: 4px; }

.top-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.top-lbl { font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg-dim); flex-shrink: 0; }
.top-chip {
  font-size: 10px; color: var(--fg-muted); background: var(--bg-input);
  border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 1px 6px;
  max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.top-chip b { color: var(--fg); font-weight: 600; }

@container (max-width: 200px) { .status-row, .sparkline-row, .top-row { display: none; } }
</style>
