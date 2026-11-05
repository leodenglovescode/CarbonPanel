<template>
  <div>
    <p class="description">Choose a photo once, adjust its crop, and save it to the web app, web login, and Android app together.</p>
    <p v-if="bg.error || error" role="alert" class="error">{{ error || bg.error }} <button @click="bg.loadShared()">Reload</button></p>
    <div class="photo-toolbar">
      <button class="primary" :disabled="busy || !bg.ready" @click="pickPhoto()">Choose photo</button>
      <button v-if="bg.settings.sourceVersion" :disabled="busy" @click="adjustOriginal">Adjust last uploaded photo</button>
      <span class="hint">One upload · select screens and crops in the next step</span>
    </div>
    <p v-if="!bg.ready" role="status" class="description">Loading server backgrounds…</p>
    <div v-else class="screen-previews">
      <article v-for="item in backgroundTargets" :key="item.key" class="screen-card">
        <div class="preview" :style="previewStyle(item.key)"><span>{{ item.label }}</span></div>
        <div class="screen-caption"><span>{{ bg.settings.targets[item.key].type === 'color' ? 'Theme color' : bg.settings.targets[item.key].type === 'image' ? 'Photo' : 'Gradient' }}</span><button :aria-label="`Customize ${item.label}`" @click="customize(item.key)">Customize</button></div>
      </article>
    </div>
    <p class="hint">The Android server chooser has its own local photo in the phone’s App settings. Pairing does not have a login background.</p>
    <details ref="details" class="individual-settings">
      <summary>Settings for an individual screen</summary>
      <div class="editor-controls">
        <label>Screen<select v-model="target"><option v-for="item in backgroundTargets" :key="item.key" :value="item.key">{{ item.label }}</option></select></label>
        <label>Background<select :value="config.type" @change="bg.setBackground(target, { type: value($event) as BgConfig['type'] })"><option value="color">Theme color</option><option value="gradient">Gradient</option><option value="image">Photo</option></select></label>
        <template v-if="config.type === 'gradient'">
          <label>Start color<input type="color" :value="config.gradientStart" @change="bg.setBackground(target, { gradientStart: value($event) })" /></label>
          <label>End color<input type="color" :value="config.gradientEnd" @change="bg.setBackground(target, { gradientEnd: value($event) })" /></label>
          <label>Angle · {{ config.gradientAngle }}°<input type="range" min="0" max="360" :value="config.gradientAngle" @change="bg.setBackground(target, { gradientAngle: +value($event) })" /></label>
        </template>
        <div v-if="config.type === 'image'" class="actions"><button :disabled="busy" @click="pickPhoto([target])">Change this photo</button><button v-if="bg.imageUrl(target)" :disabled="busy" @click="cropExisting">Adjust this crop</button></div>
        <template v-if="config.type !== 'color'">
          <label v-for="control in controls" :key="control.key">{{ control.label }} · {{ config[control.key] }}{{ control.unit }}<input type="range" :min="control.min" :max="control.max" :value="config[control.key]" @change="bg.setBackground(target, { [control.key]: +value($event) })" /></label>
        </template>
        <div class="actions"><button :disabled="busy" @click="run(() => bg.copy(target, backgroundTargets.map(t => t.key)))">Use this background on all three screens</button><button :disabled="busy" @click="run(() => bg.reset(target))">Reset this screen</button></div>
      </div>
    </details>
    <p class="hint" role="status">{{ busy || bg.saving ? 'Saving to server…' : 'Photos and display settings are saved on this server.' }}</p>
    <input ref="fileInput" type="file" accept="image/*" hidden @change="choose" />
    <BackgroundCrop :source="cropSource" :initial-targets="cropTargets" @close="cropSource = null" />
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import api from '@/api'
import { backgroundApi, type BackgroundTarget, type BgConfig } from '@/api/backgrounds'
import { backgroundTargets, useBackgroundStore } from '@/stores/background'
import BackgroundCrop from './BackgroundCrop.vue'
const bg = useBackgroundStore(), target = ref<BackgroundTarget>('app')
const config = computed(() => bg.settings.targets[target.value])
const busy = ref(false), error = ref(''), fileInput = ref<HTMLInputElement | null>(null), cropSource = ref<Blob | null>(null)
const details = ref<HTMLDetailsElement | null>(null), cropTargets = ref<BackgroundTarget[] | undefined>()
const controls = [
  { key: 'blur' as const, label: 'Blur', min: 0, max: 20, unit: 'px' },
  { key: 'brightness' as const, label: 'Brightness', min: 30, max: 150, unit: '%' },
  { key: 'overlay' as const, label: 'Contrast overlay', min: 0, max: 80, unit: '%' },
]
function previewStyle(destination: BackgroundTarget) {
  const cfg = bg.settings.targets[destination]
  return { backgroundImage: cfg.type === 'gradient' ? bg.gradientPreview(cfg) : cfg.type === 'image' && bg.imageUrl(destination) ? `url("${bg.imageUrl(destination)}")` : undefined }
}
function value(e: Event) { return (e.target as HTMLInputElement).value }
function customize(destination: BackgroundTarget) { target.value = destination; if (details.value) { details.value.open = true; details.value.scrollIntoView({ block: 'nearest' }) } }
async function run(action: () => Promise<unknown>) { busy.value = true; error.value = ''; try { await action() } catch { error.value = 'The background could not be saved. Please try again.' } finally { busy.value = false } }
function pickPhoto(destinations?: BackgroundTarget[]) { cropTargets.value = destinations; fileInput.value?.click() }
function choose(e: Event) {
  const input = e.target as HTMLInputElement, file = input.files?.[0]; input.value = ''; error.value = ''
  if (!file) return
  if (file.size > 20 * 1024 * 1024) { error.value = 'Image too large — max 20 MB'; return }
  cropSource.value = file
}
async function adjustOriginal() { cropTargets.value = undefined; await run(async () => { cropSource.value = (await backgroundApi.source()).data }) }
async function cropExisting() { cropTargets.value = [target.value]; await run(async () => { cropSource.value = (await api.get(bg.imageUrl(target.value)!, { responseType: 'blob' })).data }) }
</script>
<style scoped>
.description { color: var(--fg-muted); font-size: 11px; line-height: 1.7; margin: 16px 0; }
.photo-toolbar, .actions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
button, select { font: 11px var(--font); padding: 9px 12px; color: var(--fg-muted); background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm); }
button { cursor: pointer; transition: color var(--transition), border-color var(--transition); }
button:hover, button.primary { color: var(--accent); border-color: var(--accent-border); } button.primary { background: var(--accent-dim); } button:disabled { opacity: .5; cursor: default; }
.screen-previews { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 20px; }
.screen-card { border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; min-width: 0; }
.preview { height: 140px; background: var(--bg); background-size: cover; background-position: center; display: flex; align-items: end; }
.preview span { width: 100%; padding: 10px; background: rgba(0,0,0,.65); color: #fff; font-size: 11px; }
.screen-caption { padding: 8px; display: flex; justify-content: space-between; align-items: center; gap: 8px; font-size: 10px; color: var(--fg-dim); } .screen-caption button { padding: 6px 8px; }
.individual-settings { border-top: 1px solid var(--border); margin-top: 16px; padding-top: 16px; }
summary { cursor: pointer; color: var(--fg-muted); font-size: 11px; }
.editor-controls { display: flex; flex-direction: column; gap: 16px; margin-top: 16px; }
label { display: flex; flex-direction: column; gap: 8px; color: var(--fg-muted); font-size: 11px; }
input[type=range] { width: 100%; accent-color: var(--accent); } input[type=color] { width: 48px; height: 28px; border: none; background: transparent; }
.hint { color: var(--fg-dim); font-size: 10px; line-height: 1.7; margin: 10px 0; }
.error { color: var(--danger); font-size: 11px; margin: 8px 0; }
@media(max-width: 600px) { .screen-previews { grid-template-columns: 1fr; } .preview { height: 120px; } }
</style>
