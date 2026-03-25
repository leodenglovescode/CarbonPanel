<template>
  <div class="dashboard">
    <div v-if="!metrics.latest" class="loading">
      <span class="loading-dot" /><span class="loading-dot" /><span class="loading-dot" />
      <span class="loading-text">connecting…</span>
    </div>

    <div v-else class="grid">
      <div class="grid-item span-6">
        <CpuWidget :cpu="metrics.latest.cpu" :history="metrics.cpuHistory" />
      </div>
      <div class="grid-item span-6">
        <RamWidget :mem="metrics.latest.memory" :history="metrics.memHistory" />
      </div>

      <div v-if="metrics.latest.gpu.available" class="grid-item span-6">
        <GpuWidget :gpu="metrics.latest.gpu" :history="metrics.gpuHistory" />
      </div>
      <div :class="['grid-item', metrics.latest.gpu.available ? 'span-6' : 'span-12']">
        <SystemWidget :system="metrics.latest.system" :cpu="metrics.latest.cpu" />
      </div>

      <div class="grid-item span-12">
        <DiskWidget :disks="metrics.latest.disks" />
      </div>

      <div class="grid-item span-12">
        <NetworkWidget
          :network="metrics.latest.network"
          :rx-history="metrics.netRxHistory"
          :tx-history="metrics.netTxHistory"
        />
      </div>

      <div class="grid-item span-12">
        <ProcessListWidget
          :processes="metrics.latest.processes"
          @sort-change="onSortChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import CpuWidget from '@/components/widgets/CpuWidget.vue'
import RamWidget from '@/components/widgets/RamWidget.vue'
import GpuWidget from '@/components/widgets/GpuWidget.vue'
import DiskWidget from '@/components/widgets/DiskWidget.vue'
import NetworkWidget from '@/components/widgets/NetworkWidget.vue'
import ProcessListWidget from '@/components/widgets/ProcessListWidget.vue'
import SystemWidget from '@/components/widgets/SystemWidget.vue'
import { useMetricsStore } from '@/stores/metrics'
import { useWebSocket } from '@/composables/useWebSocket'

const metrics = useMetricsStore()
const { connect, sendPrefs } = useWebSocket()

onMounted(() => connect())

function onSortChange(sort: 'cpu' | 'memory') {
  sendPrefs(sort, metrics.processLimit)
}
</script>

<style scoped>
.dashboard { padding: 12px; }

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  gap: 6px;
  color: var(--fg-dim);
  font-size: 12px;
}
.loading-dot {
  width: 6px; height: 6px;
  background: var(--accent);
  border-radius: 50%;
  animation: pulse 1s ease infinite;
}
.loading-dot:nth-child(2) { animation-delay: 0.2s; }
.loading-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.1; } }
.loading-text { margin-left: 8px; }

.grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 10px; }
.span-6 { grid-column: span 6; }
.span-12 { grid-column: span 12; }
.grid-item { min-width: 0; }

@media (max-width: 900px) { .span-6 { grid-column: span 12; } }
</style>
