<template>
  <header class="header">
    <div class="header-left">
      <span v-if="system" class="host">{{ system.hostname }}</span>
    </div>

    <div class="header-center">
      <span v-if="system" class="uptime">up {{ formatUptime(system.uptime_seconds) }}</span>
      <span v-if="loadAvg" class="load">
        load <span class="mono">{{ loadAvg[0].toFixed(2) }}</span>
        <span class="text-muted"> / {{ loadAvg[1].toFixed(2) }} / {{ loadAvg[2].toFixed(2) }}</span>
      </span>
    </div>

    <div class="header-right">
      <span class="ws-dot" :class="connected ? 'ws-on' : 'ws-off'" :title="connected ? 'Connected' : 'Reconnecting…'" />
    </div>
  </header>
</template>

<script setup lang="ts">
import type { SystemMetrics } from '@/types/metrics'

defineProps<{
  system?: SystemMetrics
  loadAvg?: number[]
  connected?: boolean
}>()

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}d ${h}h ${m}m`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 42px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card);
  position: sticky;
  top: 0;
  z-index: 100;
  flex-shrink: 0;
}

.header-left, .header-right { display: flex; align-items: center; gap: 14px; }
.header-center { display: flex; align-items: center; gap: 16px; }

.host { font-size: 11px; color: var(--fg-muted); }

.uptime, .load { font-size: 11px; color: var(--fg-muted); }

.ws-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.ws-on { background: var(--accent); box-shadow: 0 0 6px var(--accent); }
.ws-off { background: var(--fg-dim); animation: blink 1.2s ease infinite; }

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

</style>
