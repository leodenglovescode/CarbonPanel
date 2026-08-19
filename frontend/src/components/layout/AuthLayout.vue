<template>
  <div class="auth-layout">
    <Transition name="backdrop">
      <div v-if="sidebarOpen" class="mobile-backdrop" aria-hidden="true" @click="closeSidebar" />
    </Transition>
    <AppSidebar
      :system="metrics.latest?.system"
      :connected="metrics.connected"
      :mobile-open="sidebarOpen"
      @close="closeSidebar"
    />
    <div class="main-column">
      <AppHeader
        :system="metrics.latest?.system"
        :load-avg="metrics.latest?.cpu.load_avg"
        :connected="metrics.connected"
        :menu-open="sidebarOpen"
        @menu="toggleSidebar"
      />
      <main class="content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'
import { useMetricsStore } from '@/stores/metrics'
import { useWebSocket } from '@/composables/useWebSocket'

const metrics = useMetricsStore()
const { connect, disconnect } = useWebSocket()
const sidebarOpen = ref(false)
let previousOverflow = ''

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}
function closeSidebar() {
  sidebarOpen.value = false
}

watch(sidebarOpen, (open) => {
  if (open) {
    previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = previousOverflow
  }
})

onMounted(connect)
onUnmounted(() => {
  disconnect()
  document.body.style.overflow = previousOverflow
})
</script>

<style scoped>
.auth-layout {
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.main-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  container-type: inline-size;
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
