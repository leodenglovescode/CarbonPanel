<template>
  <BaseModal :open="!!source" title="Set background photo" max-width="720px" @close="!busy && emit('close')">
    <fieldset class="destinations" :disabled="busy">
      <legend>Where should this photo appear?</legend>
      <label v-for="destination in backgroundTargets" :key="destination.key"><input v-model="targets" type="checkbox" :value="destination.key" /> {{ destination.label }}</label>
    </fieldset>
    <label class="crop-mode">Crop layout
      <select v-model="mode" :disabled="busy"><option value="shared">Same crop on every selected screen</option><option value="separate">Separate web and phone crops</option></select>
    </label>
    <p class="hint">Upload once. Drag to position the photo, then save all selected screens together.</p>
    <div v-if="mode === 'separate'" class="crop-tabs" role="group" aria-label="Edit crop">
      <button :class="{ active: active === 'web' }" :disabled="busy" @click="active = 'web'">Web crop · landscape</button>
      <button :class="{ active: active === 'phone' }" :disabled="busy" @click="active = 'phone'">Phone crop · portrait</button>
    </div>
    <div class="crop-preview" :style="{ aspectRatio: String(aspect), width: `min(100%, ${300 * aspect}px)` }" @pointerdown="startDrag" @pointermove="drag" @pointerup="stopDrag" @pointercancel="stopDrag">
      <canvas ref="canvas" aria-label="Cropped image preview" />
    </div>
    <fieldset class="controls" :disabled="busy">
      <label>Shape<select v-model="shape"><option value="original">Original</option><option value="16:9">Landscape · 16:9</option><option value="9:16">Portrait · 9:16</option><option value="1:1">Square · 1:1</option></select></label>
      <label>Output long edge<select v-model.number="size"><option :value="960">960 px</option><option :value="1920">1920 px</option><option :value="2560">2560 px</option></select></label>
      <label>Zoom · {{ zoom.toFixed(1) }}×<input v-model.number="zoom" type="range" min="1" max="4" step="0.05" /></label>
      <label>Horizontal position<input v-model.number="x" type="range" min="0" max="1" step="0.01" /></label>
      <label>Vertical position<input v-model.number="y" type="range" min="0" max="1" step="0.01" /></label>
    </fieldset>
    <p v-if="targets.includes('login')" class="hint">The web login photo is visible before sign-in.</p>
    <p v-if="mode === 'separate'" class="hint">Both crops use the original photo. Switching tabs keeps your adjustments; one save applies both.</p>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
    <div class="actions"><button :disabled="busy" @click="emit('close')">Cancel</button><button :disabled="busy || !image || !targets.length" class="primary" @click="save">{{ busy ? 'Saving…' : `Save to ${targets.length} ${targets.length === 1 ? 'screen' : 'screens'}` }}</button></div>
  </BaseModal>
</template>

<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import { backgroundTargets, useBackgroundStore } from '@/stores/background'
import type { BackgroundTarget } from '@/api/backgrounds'
import { cropRectangle } from '@/utils/imageCrop'
const props = defineProps<{ source: Blob | null; initialTargets?: BackgroundTarget[] }>()
const emit = defineEmits<{ close: [] }>()
const bg = useBackgroundStore()
const canvas = ref<HTMLCanvasElement | null>(null)
const image = ref<HTMLImageElement | null>(null)
interface Crop { shape: string; zoom: number; x: number; y: number; size: number }
const defaults = (shape = 'original'): Crop => ({ shape, zoom: 1, x: 0.5, y: 0.5, size: 1920 })
const crops = ref({ shared: defaults(), web: defaults('16:9'), phone: defaults('9:16') })
const mode = ref<'shared' | 'separate'>('shared'), active = ref<'web' | 'phone'>('web')
const current = computed(() => crops.value[mode.value === 'shared' ? 'shared' : active.value])
function field<K extends keyof Crop>(key: K) { return computed({ get: () => current.value[key], set: (value: Crop[K]) => { current.value[key] = value } }) }
const shape = field('shape'), zoom = field('zoom'), x = field('x'), y = field('y'), size = field('size')
const targets = ref<BackgroundTarget[]>([])
const busy = ref(false), error = ref('')
function cropAspect(crop: Crop) { return crop.shape === 'original' ? image.value ? image.value.naturalWidth / image.value.naturalHeight : 16 / 9 : crop.shape === '16:9' ? 16 / 9 : crop.shape === '9:16' ? 9 / 16 : 1 }
const aspect = computed(() => cropAspect(current.value))
let objectUrl = '', generation = 0
watch(() => props.source, source => {
  const currentGeneration = ++generation
  if (objectUrl) URL.revokeObjectURL(objectUrl)
  image.value = null; error.value = ''
  crops.value = { shared: defaults(), web: defaults('16:9'), phone: defaults('9:16') }
  mode.value = 'shared'; active.value = 'web'
  targets.value = props.initialTargets?.slice() ?? backgroundTargets.map(t => t.key)
  if (!source) return
  objectUrl = URL.createObjectURL(source)
  const img = new Image()
  img.onload = async () => {
    if (currentGeneration !== generation) return
    if (img.naturalWidth * img.naturalHeight > 40_000_000) { error.value = 'Please use an image smaller than 40 megapixels.'; return }
    image.value = img; await nextTick(); paint()
  }
  img.onerror = () => { if (currentGeneration === generation) error.value = 'This image could not be opened. Try a JPEG, PNG, or WebP image.' }
  img.src = objectUrl
})
function render(output: HTMLCanvasElement, cropSettings: Crop, longEdge: number) {
  const img = image.value
  if (!img) return
  const crop = cropRectangle(img.naturalWidth, img.naturalHeight, cropAspect(cropSettings), cropSettings.zoom, cropSettings.x, cropSettings.y)
  const scale = Math.min(1, longEdge / Math.max(crop.width, crop.height))
  output.width = Math.max(1, Math.round(crop.width * scale)); output.height = Math.max(1, Math.round(crop.height * scale))
  const ctx = output.getContext('2d')!
  ctx.fillStyle = '#111111'; ctx.fillRect(0, 0, output.width, output.height)
  ctx.drawImage(img, crop.x, crop.y, crop.width, crop.height, 0, 0, output.width, output.height)
}
function paint() { if (canvas.value) render(canvas.value, current.value, 720) }
watch([current, aspect, zoom, x, y], paint, { flush: 'post' })
let pointer: { id: number; x: number; y: number; startX: number; startY: number } | null = null
function startDrag(e: PointerEvent) { if (busy.value) return; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); pointer = { id: e.pointerId, x: e.clientX, y: e.clientY, startX: x.value, startY: y.value } }
function drag(e: PointerEvent) {
  if (!pointer || pointer.id !== e.pointerId || !image.value) return
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect(), img = image.value
  const crop = cropRectangle(img.naturalWidth, img.naturalHeight, aspect.value, zoom.value, x.value, y.value)
  const dx = (img.naturalWidth - crop.width) * rect.width / crop.width, dy = (img.naturalHeight - crop.height) * rect.height / crop.height
  if (dx > 0) x.value = Math.max(0, Math.min(1, pointer.startX - (e.clientX - pointer.x) / dx))
  if (dy > 0) y.value = Math.max(0, Math.min(1, pointer.startY - (e.clientY - pointer.y) / dy))
}
function stopDrag() { pointer = null }
function encode(crop: Crop, edge = crop.size) {
  const output = document.createElement('canvas'); render(output, crop, edge)
  return new Promise<Blob>((resolve, reject) => output.toBlob(b => b ? resolve(b) : reject(new Error('Could not encode image')), 'image/jpeg', 0.85))
}
async function save() {
  busy.value = true; error.value = ''
  try {
    const original = await encode(defaults(), 2560)
    const web = await encode(mode.value === 'shared' ? crops.value.shared : crops.value.web)
    const phone = mode.value === 'separate' ? await encode(crops.value.phone) : null
    await bg.applyCrops(original, web, phone, targets.value)
    emit('close')
  } catch { error.value = 'The photo could not be saved. Your crop settings are kept here; try again.' } finally { busy.value = false }
}
onUnmounted(() => { generation++; if (objectUrl) URL.revokeObjectURL(objectUrl) })
</script>

<style scoped>
.hint { color: var(--fg-muted); font-size: 11px; line-height: 1.6; margin: 12px 0; }
.destinations { margin: 0 0 16px; padding: 12px; border: 1px solid var(--border); display: flex; flex-wrap: wrap; gap: 16px; }
legend { color: var(--fg); font-size: 11px; padding: 0 4px; } .destinations label { flex-direction: row; align-items: center; }
.crop-preview { max-height: 300px; margin: 12px auto 16px; overflow: hidden; background: var(--bg-input); cursor: grab; touch-action: none; display: flex; justify-content: center; }
.crop-preview canvas { display: block; max-width: 100%; max-height: 300px; object-fit: contain; }
.controls { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; border: 0; padding: 0; }
label { display: flex; flex-direction: column; gap: 8px; font-size: 11px; color: var(--fg-muted); min-width: 0; }
select, button { font: inherit; color: var(--fg); background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 8px; }
input[type=range] { width: 100%; accent-color: var(--accent); } input[type=checkbox] { accent-color: var(--accent); }
.actions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; margin-top: 16px; }
button { cursor: pointer; transition: border-color var(--transition); } button:hover { border-color: var(--accent); } button:disabled { opacity: .5; cursor: default; }
.primary, button.active { color: var(--accent); border-color: var(--accent-border); } .error { color: var(--danger); font-size: 11px; margin: 8px 0; }
.crop-tabs { display: flex; gap: 8px; }
@media(max-width: 480px) { .controls { grid-template-columns: 1fr; } }
</style>
