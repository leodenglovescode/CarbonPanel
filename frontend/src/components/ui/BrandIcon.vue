<template>
  <span
    v-if="svg"
    class="brand-icon"
    v-html="svg"
    :title="slug ?? undefined"
    :style="{ width: px, height: px }"
  />
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { detectBrand, fetchBrandSvg } from '@/utils/brandIcons'

const props = defineProps<{ name: string; size?: number }>()

const slug = ref<string | null>(null)
const svg = ref<string | null>(null)
const px = computed(() => `${props.size ?? 14}px`)

async function load(name: string) {
  slug.value = detectBrand(name)
  svg.value = slug.value ? await fetchBrandSvg(slug.value) : null
}

onMounted(() => load(props.name))
watch(() => props.name, load)
</script>

<style scoped>
.brand-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  opacity: 0.85;
}
.brand-icon :deep(svg) {
  width: 100%;
  height: 100%;
}
</style>
