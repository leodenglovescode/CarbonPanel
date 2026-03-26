<template>
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
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AuthLayout from '@/components/layout/AuthLayout.vue'
import ToastContainer from '@/components/ui/ToastContainer.vue'
import { useThemeStore } from '@/stores/theme'

useThemeStore()

const route = useRoute()
const isPublicRoute = computed(() => !!route.meta.public)
</script>
