<template>
  <div>
    <p class="description">Choose separate backgrounds for the web and Android, or apply one image everywhere. Images, crops, and display settings are saved on this server.</p>
    <p v-if="bg.error || error" role="alert" class="error">{{ error || bg.error }} <button @click="bg.loadShared()">Reload</button></p>
    <div class="destinations" role="group" aria-label="Background destination">
      <button v-for="item in backgroundTargets" :key="item.key" :class="{ active: target === item.key }" @click="target = item.key">{{ item.label }}</button>
    </div>
    <div v-if="!bg.ready" class="description">Loading server backgrounds…</div>
    <template v-else>
      <div class="background-editor">
        <div class="preview" :class="{ portrait: target.startsWith('android') }" :style="previewStyle"><span>{{ backgroundTargets.find(t => t.key === target)?.label }}</span></div>
        <div class="editor-controls">
          <div class="types"><button v-for="type in ['color', 'gradient', 'image'] as const" :key="type" :class="{ active: config.type === type }" @click="bg.setBackground(target, { type })">{{ type === 'color' ? 'Theme color' : type === 'image' ? 'Image' : 'Gradient' }}</button></div>
          <template v-if="config.type === 'gradient'">
            <label>Start color<input type="color" :value="config.gradientStart" @change="bg.setBackground(target, { gradientStart: value($event) })" /></label>
            <label>End color<input type="color" :value="config.gradientEnd" @change="bg.setBackground(target, { gradientEnd: value($event) })" /></label>
            <label>Angle · {{ config.gradientAngle }}°<input type="range" min="0" max="360" :value="config.gradientAngle" @change="bg.setBackground(target, { gradientAngle: +value($event) })" /></label>
          </template>
          <template v-if="config.type === 'image'">
            <button :disabled="busy" @click="fileInput?.click()">Upload & crop image</button>
            <div v-if="bg.imageUrl(target)" class="actions"><button :disabled="busy" @click="cropExisting">Adjust saved crop</button><button :disabled="busy" @click="run(() => bg.remove(target))">Remove image</button></div>
            <p class="hint">JPEG, PNG, WebP, and other supported images · up to 20 MB. Login images are visible before sign-in.</p>
          </template>
          <template v-if="config.type !== 'color'">
            <label v-for="control in controls" :key="control.key">{{ control.label }} · {{ config[control.key] }}{{ control.unit }}<input type="range" :min="control.min" :max="control.max" :value="config[control.key]" @change="bg.setBackground(target, { [control.key]: +value($event) })" /></label>
          </template>
        </div>
      </div>
      <div class="reuse"><strong>Reuse this background</strong><p class="hint">Copies the saved image and its display settings. Each destination can still be changed separately.</p><div class="actions"><button :disabled="busy" @click="reuseWeb">Use for both web screens</button><button :disabled="busy" @click="reusePhone">Use for both Android screens</button><button :disabled="busy" class="accent" @click="run(() => bg.copy(target, backgroundTargets.map(t => t.key)))">Apply to all four</button><button :disabled="busy" @click="run(() => bg.reset(target))">Reset this screen</button></div></div>
      <p class="hint" role="status">{{ busy || bg.saving ? 'Saving to server…' : 'Changes are saved to the server automatically.' }}</p>
    </template>
    <input ref="fileInput" type="file" accept="image/*" hidden @change="choose" />
    <BackgroundCrop :source="cropSource" :target="target" @close="cropSource = null" />
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import api from '@/api'
import { backgroundTargets, useBackgroundStore } from '@/stores/background'
import type { BackgroundTarget } from '@/api/backgrounds'
import BackgroundCrop from './BackgroundCrop.vue'
const bg = useBackgroundStore(), target = ref<BackgroundTarget>('app')
const config = computed(() => bg.settings.targets[target.value])
const busy = ref(false), error = ref(''), fileInput = ref<HTMLInputElement | null>(null), cropSource = ref<Blob | null>(null)
const controls = [
  { key: 'blur' as const, label: 'Blur', min: 0, max: 20, unit: 'px' },
  { key: 'brightness' as const, label: 'Brightness', min: 30, max: 150, unit: '%' },
  { key: 'overlay' as const, label: 'Contrast overlay', min: 0, max: 80, unit: '%' },
]
const previewStyle = computed(() => ({ backgroundImage: config.value.type === 'gradient' ? bg.gradientPreview(config.value) : config.value.type === 'image' && bg.imageUrl(target.value) ? `url("${bg.imageUrl(target.value)}")` : undefined }))
function value(e: Event) { return (e.target as HTMLInputElement).value }
async function run(action: () => Promise<unknown>) { busy.value = true; error.value = ''; try { await action() } catch { error.value = 'The background could not be saved. Please try again.' } finally { busy.value = false } }
function choose(e: Event) {
  const input = e.target as HTMLInputElement, file = input.files?.[0]; input.value = ''; error.value = ''
  if (!file) return
  if (file.size > 20 * 1024 * 1024) { error.value = 'Image too large — max 20 MB'; return }
  cropSource.value = file
}
async function cropExisting() { await run(async () => { cropSource.value = (await api.get(bg.imageUrl(target.value)!, { responseType: 'blob' })).data }) }
function reuseWeb() { return run(() => bg.copy(target.value, ['app', 'login'])) }
function reusePhone() { return run(() => bg.copy(target.value, ['android-app', 'android-login'])) }
</script>
<style scoped>
.description { color: var(--fg-muted); font-size: 11px; line-height: 1.7; margin: 16px 0; }
.destinations, .types, .actions { display: flex; flex-wrap: wrap; gap: 8px; }
.destinations { padding-bottom: 16px; border-bottom: 1px solid var(--border); }
button { font: 11px var(--font); padding: 9px 12px; color: var(--fg-muted); background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm); cursor: pointer; transition: color var(--transition), border-color var(--transition); }
button:hover, button.active, button.accent { color: var(--accent); border-color: var(--accent-border); } button:disabled { opacity: .5; cursor: default; }
.background-editor { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr); gap: 24px; padding: 20px 0; align-items: start; }
.preview { width: 100%; aspect-ratio: 16/10; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg); background-size: cover; background-position: center; display: flex; align-items: end; overflow: hidden; }
.preview.portrait { aspect-ratio: 9/16; max-height: 340px; max-width: 192px; margin: auto; }
.preview span { width: 100%; padding: 12px; background: rgba(0,0,0,.65); color: #fff; font-size: 11px; }
.editor-controls { display: flex; flex-direction: column; gap: 16px; }
label { display: flex; flex-direction: column; gap: 8px; color: var(--fg-muted); font-size: 11px; }
input[type=range] { width: 100%; accent-color: var(--accent); } input[type=color] { width: 48px; height: 28px; border: none; background: transparent; }
.hint { color: var(--fg-dim); font-size: 10px; line-height: 1.7; margin: 8px 0; }
.reuse { padding: 16px 0; border-top: 1px solid var(--border); } .reuse strong { font-size: 11px; } .error { color: var(--danger); font-size: 11px; margin: 8px 0; }
@media(max-width: 640px) { .background-editor { grid-template-columns: 1fr; } }
</style>
