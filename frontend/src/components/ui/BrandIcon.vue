<template>
  <!--
    Rendered as <img>, never v-html. An SVG loaded through <img> runs in an
    image context where scripts and event handlers are inert, so a compromised
    or MITM'd icon CDN can't reach the DOM. The previous version fetched the
    markup and injected it behind a regex sanitizer that turned out to be
    bypassable via `<img/onerror=...>` — slash is a valid attribute separator.
  -->
  <img
    v-if="src"
    class="brand-icon"
    :class="{ 'brand-icon--dark': isDark }"
    :src="src"
    :alt="slug ?? ''"
    :title="slug ?? undefined"
    :width="size ?? 14"
    :height="size ?? 14"
    loading="lazy"
    decoding="async"
    referrerpolicy="no-referrer"
    @error="tryNextSource"
  />
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { detectBrand, brandIconUrls, DARK_SLUGS } from '@/utils/brandIcons'

const props = defineProps<{ name: string; size?: number }>()

const slug = ref<string | null>(null)
const sources = ref<string[]>([])
const index = ref(0)

const src = computed(() => sources.value[index.value] ?? null)
const isDark = computed(() => !!slug.value && DARK_SLUGS.has(slug.value))

/** Falls through to the next CDN when one 404s or is unreachable. */
function tryNextSource() {
  if (index.value < sources.value.length - 1) index.value++
  else sources.value = [] // give up quietly rather than showing a broken image
}

function load(name: string) {
  slug.value = detectBrand(name)
  sources.value = slug.value ? brandIconUrls(slug.value) : []
  index.value = 0
}

onMounted(() => load(props.name))
watch(() => props.name, load)
</script>

<style scoped>
.brand-icon {
  display: inline-block;
  flex-shrink: 0;
  object-fit: contain;
  opacity: 0.85;
  border-radius: 3px;
}
/* Dark-colored brand icons (black/near-black) need a light backing on dark backgrounds */
.brand-icon--dark {
  background: rgba(255, 255, 255, 0.15);
  padding: 2px;
  opacity: 1;
}
</style>
