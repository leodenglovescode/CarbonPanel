<template>
  <div class="auth-layout">
    <Transition name="backdrop">
      <div v-if="sidebarOpen" class="mobile-backdrop" @click="sidebarOpen = false" />
    </Transition>
    <AppSidebar
      :system="metrics.latest?.system"
      :connected="metrics.connected"
      :mobile-open="sidebarOpen"
      @close="sidebarOpen = false"
    />
    <div class="main-column">
      <AppHeader
        :system="metrics.latest?.system"
        :load-avg="metrics.latest?.cpu.load_avg"
        :connected="metrics.connected"
        @menu="sidebarOpen = !sidebarOpen"
      />
      <main class="content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import { useMetricsStore } from '@/stores/metrics'

const metrics = useMetricsStore()
const sidebarOpen = ref(false)
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

.mobile-backdrop {
  display: none;
}

.backdrop-enter-active, .backdrop-leave-active { transition: opacity var(--transition-slow); }
.backdrop-enter-from, .backdrop-leave-to { opacity: 0; }

@media (max-width: 640px) {
  .mobile-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 150;
    background: rgba(0, 0, 0, 0.55);
  }
}
</style>
