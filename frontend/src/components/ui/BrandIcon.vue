<template>
  <span
    v-if="svg"
    class="brand-icon"
    :class="{ 'brand-icon--dark': isDark }"
    v-html="svg"
    :title="slug ?? undefined"
    :style="{ width: px, height: px }"
  />
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { detectBrand, fetchBrandSvg, DARK_SLUGS } from '@/utils/brandIcons'

const props = defineProps<{ name: string; size?: number }>()

const slug = ref<string | null>(null)
const svg = ref<string | null>(null)
const isDark = computed(() => !!slug.value && DARK_SLUGS.has(slug.value))
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
  border-radius: 3px;
}
.brand-icon :deep(svg) {
  width: 100%;
  height: 100%;
}
/* Dark-colored brand icons (black/near-black) need a light backing on dark backgrounds */
.brand-icon--dark {
  background: rgba(255, 255, 255, 0.15);
  padding: 2px;
  opacity: 1;
}
</style>
