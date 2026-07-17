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
  <ConfirmDialog />
  <CommandPalette v-if="!isPublicRoute" />
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AuthLayout from '@/components/layout/AuthLayout.vue'
import ToastContainer from '@/components/ui/ToastContainer.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import CommandPalette from '@/components/layout/CommandPalette.vue'
import { systemApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useBackgroundStore } from '@/stores/background'
import { useDialogStore } from '@/stores/dialog'
import { useUserPrefsSync } from '@/composables/useUserPrefsSync'

const UPDATE_PROMPT_STORAGE_KEY = 'cp_update_prompt_version'

useThemeStore()
const bg = useBackgroundStore()
const dialog = useDialogStore()

const prefsSync = useUserPrefsSync()
prefsSync.startWatching()

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isPublicRoute = computed(() => !!route.meta.public)

async function maybePromptForUpdate() {
  // The Settings page has its own full check/install/progress UI — popping
  // this dialog on top of it double-notifies for the same event and, worse,
  // races it: a manual "Check for Updates" click there kicks off a real
  // multi-second GitHub check, and this route-change watcher would otherwise
  // read the update-status file mid-check and surface its own separate,
  // out-of-sync verdict.
  if (route.path === '/settings') return
  if (!auth.isAuthenticated || isPublicRoute.value) return

  try {
    const { data } = await systemApi.version()

    if (!data.latest_version || !data.update_available || data.update_in_progress) return

    if (localStorage.getItem(UPDATE_PROMPT_STORAGE_KEY) === data.latest_version) return

    const shouldInstall = await dialog.confirm({
      title: 'Update available',
      message: `CarbonPanel ${data.latest_version} is available.\n\nCurrent version: ${data.current_version ?? 'unknown'}\nInstall the update now?`,
      confirmLabel: 'Install',
    })

    if (!shouldInstall) {
      localStorage.setItem(UPDATE_PROMPT_STORAGE_KEY, data.latest_version)
      return
    }

    await systemApi.installUpdate()
    localStorage.removeItem(UPDATE_PROMPT_STORAGE_KEY)

    // Settings has the live progress bar + restart countdown — land there
    // instead of leaving the user on whatever page they were on with just a
    // one-off "refresh in a minute" message and no actual feedback loop.
    await router.push('/settings')
  } catch {
    // Intentionally ignore update prompt errors to avoid interrupting app usage.
  }
}

watch(
  () => auth.isAuthenticated,
  (authenticated) => {
    if (authenticated) {
      void prefsSync.load()
      bg.migrateLegacyImages()
    }
  },
  { immediate: true },
)

watch(
  [() => auth.isAuthenticated, () => route.fullPath],
  ([authenticated]) => {
    if (authenticated && !isPublicRoute.value) {
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
