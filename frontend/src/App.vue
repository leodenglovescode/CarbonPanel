<template>
  <Teleport to="body">
    <div v-if="bg.appBgLayerVisible" class="app-bg-layer" :style="bg.appBgLayerStyle" />
  </Teleport>
  <router-view v-if="!isPublicRoute" v-slot="{ Component }">
    <AuthLayout>
      <Transition name="route-fade" mode="out-in">
        <component :is="Component" :key="route.fullPath" />
      </Transition>
    </AuthLayout>
  </router-view>
  <router-view v-else v-slot="{ Component }">
    <Transition name="route-fade" mode="out-in">
      <component :is="Component" :key="route.fullPath" />
    </Transition>
  </router-view>
  <ToastContainer />
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import AuthLayout from '@/components/layout/AuthLayout.vue'
import ToastContainer from '@/components/ui/ToastContainer.vue'
import { systemApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useBackgroundStore } from '@/stores/background'
import { useUserPrefsSync } from '@/composables/useUserPrefsSync'

const UPDATE_PROMPT_STORAGE_KEY = 'cp_update_prompt_version'

useThemeStore()
const bg = useBackgroundStore()

const prefsSync = useUserPrefsSync()
prefsSync.startWatching()

const route = useRoute()
const auth = useAuthStore()
const isPublicRoute = computed(() => !!route.meta.public)

async function maybePromptForUpdate() {
  if (!auth.token || isPublicRoute.value) return

  try {
    const { data } = await systemApi.version()

    if (!data.latest_version || !data.update_available || data.update_in_progress) return

    if (localStorage.getItem(UPDATE_PROMPT_STORAGE_KEY) === data.latest_version) return

    const shouldInstall = window.confirm(
      `CarbonPanel ${data.latest_version} is available.\n\nCurrent version: ${data.current_version ?? 'unknown'}\nInstall the update now?`,
    )

    if (!shouldInstall) {
      localStorage.setItem(UPDATE_PROMPT_STORAGE_KEY, data.latest_version)
      return
    }

    await systemApi.installUpdate()
    localStorage.removeItem(UPDATE_PROMPT_STORAGE_KEY)

    window.alert(
      'CarbonPanel has started installing the update. The app will restart automatically. Refresh this page in about a minute.',
    )
  } catch {
    // Intentionally ignore update prompt errors to avoid interrupting app usage.
  }
}

watch(
  () => auth.token,
  (token) => {
    if (token) void prefsSync.load()
  },
  { immediate: true },
)

watch(
  [() => auth.token, () => route.fullPath],
  ([token]) => {
    if (token && !isPublicRoute.value) {
      void maybePromptForUpdate()
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.app-bg-layer {
  position: fixed;
  inset: -30px;
  z-index: 0;
  pointer-events: none;
}
</style>
