<template>
  <div class="auth-layout">
    <AppSidebar
      :system="metrics.latest?.system"
      :connected="metrics.connected"
    />
    <div class="main-column">
      <AppHeader
        :system="metrics.latest?.system"
        :load-avg="metrics.latest?.cpu.load_avg"
        :connected="metrics.connected"
      />
      <main class="content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import { useMetricsStore } from '@/stores/metrics'

const metrics = useMetricsStore()
</script>

<style scoped>
.auth-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.main-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.content {
  flex: 1;
  overflow-y: auto;
}
</style>
