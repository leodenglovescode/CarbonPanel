<template>
  <BaseModal :open="!!source" title="Crop & resize background" max-width="680px" @close="!busy && emit('close')">
    <p class="hint">Drag the image or use the position sliders. The saved crop is stored on your server.</p>
    <div class="crop-preview" :style="{ aspectRatio: String(aspect), width: `min(100%, ${320 * aspect}px)` }" @pointerdown="startDrag" @pointermove="drag" @pointerup="stopDrag" @pointercancel="stopDrag">
      <canvas ref="canvas" aria-label="Cropped image preview" />
    </div>
    <div class="controls">
      <label>Shape<select v-model="shape"><option value="original">Original</option><option value="16:9">Desktop · 16:9</option><option value="9:16">Phone · 9:16</option><option value="1:1">Square · 1:1</option></select></label>
      <label>Output long edge<select v-model.number="size"><option :value="960">960 px</option><option :value="1920">1920 px</option><option :value="2560">2560 px</option></select></label>
      <label>Zoom · {{ zoom.toFixed(1) }}×<input v-model.number="zoom" type="range" min="1" max="4" step="0.05" /></label>
      <label>Horizontal position<input v-model.number="x" type="range" min="0" max="1" step="0.01" /></label>
      <label>Vertical position<input v-model.number="y" type="range" min="0" max="1" step="0.01" /></label>
    </div>
    <fieldset><legend>Apply this crop to</legend><label v-for="destination in backgroundTargets" :key="destination.key"><input v-model="targets" type="checkbox" :value="destination.key" /> {{ destination.label }}</label></fieldset>
    <p class="hint">Login backgrounds are visible before sign-in. Images are fitted to each screen; a portrait crop also works on the web.</p>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
    <div class="actions"><button :disabled="busy" @click="targets = backgroundTargets.map(t => t.key)">Select all four</button><button :disabled="busy || !image || !targets.length" class="primary" @click="save">{{ busy ? 'Saving…' : 'Save & apply' }}</button></div>
  </BaseModal>
</template>

<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import { backgroundTargets, useBackgroundStore } from '@/stores/background'
import type { BackgroundTarget } from '@/api/backgrounds'
import { cropRectangle } from '@/utils/imageCrop'
const props = defineProps<{ source: Blob | null; target: BackgroundTarget }>()
const emit = defineEmits<{ close: [] }>()
const bg = useBackgroundStore()
const canvas = ref<HTMLCanvasElement | null>(null)
const image = ref<HTMLImageElement | null>(null)
const shape = ref('original'), zoom = ref(1), x = ref(0.5), y = ref(0.5), size = ref(1920)
const targets = ref<BackgroundTarget[]>([])
const busy = ref(false), error = ref('')
const aspect = computed(() => shape.value === 'original' ? image.value ? image.value.naturalWidth / image.value.naturalHeight : 16 / 9 : shape.value === '16:9' ? 16 / 9 : shape.value === '9:16' ? 9 / 16 : 1)
let objectUrl = '', generation = 0
watch(() => props.source, async source => {
  const current = ++generation
  if (objectUrl) URL.revokeObjectURL(objectUrl)
  image.value = null; error.value = ''; zoom.value = 1; x.value = 0.5; y.value = 0.5
  targets.value = [props.target]; shape.value = props.target.startsWith('android') ? '9:16' : 'original'
  if (!source) return
  objectUrl = URL.createObjectURL(source)
  const img = new Image()
  img.onload = async () => { if (current !== generation) return; if (img.naturalWidth * img.naturalHeight > 40_000_000) { error.value = 'This image is too large to crop. Please use an image smaller than 40 megapixels.'; return }; image.value = img; await nextTick(); paint() }
  img.onerror = () => { if (current === generation) error.value = 'This image could not be opened. Try a JPEG, PNG, or WebP image.' }
  img.src = objectUrl
})
function render(output: HTMLCanvasElement, longEdge: number) {
  const img = image.value
  if (!img) return
  const crop = cropRectangle(img.naturalWidth, img.naturalHeight, aspect.value, zoom.value, x.value, y.value)
  // Never upscale the source crop.
  const scale = Math.min(1, longEdge / Math.max(crop.width, crop.height))
  output.width = Math.max(1, Math.round(crop.width * scale)); output.height = Math.max(1, Math.round(crop.height * scale))
  const ctx = output.getContext('2d')!
  ctx.fillStyle = '#111111'; ctx.fillRect(0, 0, output.width, output.height)
  ctx.drawImage(img, crop.x, crop.y, crop.width, crop.height, 0, 0, output.width, output.height)
}
function paint() { if (canvas.value) render(canvas.value, 720) }
watch([aspect, zoom, x, y], paint, { flush: 'post' })
let pointer: { id: number; x: number; y: number; startX: number; startY: number } | null = null
function startDrag(e: PointerEvent) { if (busy.value) return; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); pointer = { id: e.pointerId, x: e.clientX, y: e.clientY, startX: x.value, startY: y.value } }
function drag(e: PointerEvent) {
  if (!pointer || pointer.id !== e.pointerId || !image.value) return
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const img = image.value, crop = cropRectangle(img.naturalWidth, img.naturalHeight, aspect.value, zoom.value, x.value, y.value)
  const dx = (img.naturalWidth - crop.width) * rect.width / crop.width
  const dy = (img.naturalHeight - crop.height) * rect.height / crop.height
  if (dx > 0) x.value = Math.max(0, Math.min(1, pointer.startX - (e.clientX - pointer.x) / dx))
  if (dy > 0) y.value = Math.max(0, Math.min(1, pointer.startY - (e.clientY - pointer.y) / dy))
}
function stopDrag() { pointer = null }
async function save() {
  busy.value = true; error.value = ''
  try {
    const output = document.createElement('canvas'); render(output, size.value)
    const blob = await new Promise<Blob>((resolve, reject) => output.toBlob(b => b ? resolve(b) : reject(new Error('Could not encode image')), 'image/jpeg', 0.9))
    await bg.applyImage(blob, targets.value)
    emit('close')
  } catch { error.value = 'The crop could not be saved. Check the server connection and try again.' } finally { busy.value = false }
}
onUnmounted(() => { generation++; if (objectUrl) URL.revokeObjectURL(objectUrl) })
</script>

<style scoped>
.hint { color: var(--fg-muted); font-size: 11px; line-height: 1.6; margin-bottom: 12px; }
.crop-preview { width: 100%; max-height: 320px; margin: 0 auto 16px; overflow: hidden; background: var(--bg-input); cursor: grab; touch-action: none; display: flex; justify-content: center; }
.crop-preview canvas { display: block; max-width: 100%; max-height: 320px; object-fit: contain; }
.controls { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
label { display: flex; flex-direction: column; gap: 8px; font-size: 11px; color: var(--fg-muted); min-width: 0; }
select, button { font: inherit; color: var(--fg); background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 8px; }
input[type=range] { width: 100%; accent-color: var(--accent); }
fieldset { margin: 18px 0 12px; padding: 12px; border: 1px solid var(--border); display: flex; flex-wrap: wrap; gap: 14px; }
legend { color: var(--fg); font-size: 11px; padding: 0 4px; }
fieldset label { flex-direction: row; align-items: center; } input[type=checkbox] { accent-color: var(--accent); }
.actions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }
button { cursor: pointer; transition: border-color var(--transition); } button:hover { border-color: var(--accent); } button:disabled { opacity: .5; cursor: default; }
.primary { color: var(--accent); border-color: var(--accent-border); } .error { color: var(--danger); font-size: 11px; margin: 8px 0; }
@media(max-width: 480px) { .controls { grid-template-columns: 1fr; } }
</style>
