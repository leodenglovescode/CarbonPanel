<template>
  <AuthLayout v-if="!isPublicRoute">
    <router-view />
  </AuthLayout>
  <router-view v-else />
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
