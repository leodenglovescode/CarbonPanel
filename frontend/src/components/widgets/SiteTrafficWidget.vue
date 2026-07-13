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

const POLL_MS = 15000

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
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to load traffic'
  }
}

function onSiteChange() {
  trafficStore.setSelectedSiteId(selectedId.value || null)
  traffic.value = null
  void loadTraffic()
}

watch(() => trafficStore.selectedSiteId, (id) => {
  if (id !== selectedId.value) selectedId.value = id || ''
})

onMounted(async () => {
  try {
    const { data } = await sitesApi.list()
    sites.value = data
    if (selectedId.value && !data.some(s => s.id === selectedId.value)) selectedId.value = ''
  } catch { /* silent */ }
  void loadTraffic()
  pollTimer = setInterval(loadTraffic, POLL_MS)
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
@container (max-width: 200px) { .status-row, .sparkline-row { display: none; } }
</style>
