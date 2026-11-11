<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path v-for="(path, index) in paths" :key="index" :d="path" />
  </svg>
</template>
<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ name: string }>()
const shapes: Record<string, string[]> = {
  directory: ['M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10H3Z'],
  image: ['M4 3h16v18H4Z', 'M4 16l5-5 4 4 3-3 4 4', 'M15 7h.01'],
  video: ['M3 5h13v14H3Z', 'M16 10l5-3v10l-5-3Z'],
  audio: ['M9 18V5l11-2v13', 'M9 14c-8-1-8 7 0 4', 'M20 12c-8-1-8 7 0 4'],
  text: ['M5 3h10l4 4v14H5Z', 'M9 11h6M9 15h6'],
  markdown: ['M4 4h16v16H4Z', 'M7 15V9l3 3 3-3v6M17 9v6'],
  file: ['M5 3h10l4 4v14H5Z', 'M15 3v5h4'],
  list: ['M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01'],
  grid: ['M3 3h7v7H3ZM14 3h7v7h-7ZM3 14h7v7H3ZM14 14h7v7h-7Z'],
  download: ['M12 3v12m-5-5 5 5 5-5', 'M4 16v5h16v-5'],
  refresh: ['M20 7v5h-5', 'M20 12a8 8 0 1 0-2 6'],
  up: ['M12 20V4m-6 6 6-6 6 6'],
  search: ['M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z', 'm15 15 6 6'],
  path: ['M8 5 2 12l6 7M16 5l6 7-6 7M14 3l-4 18'],
  close: ['m6 6 12 12M6 18 18 6'],
}
const paths = computed(() => shapes[props.name] || shapes.file)
</script>
