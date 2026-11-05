import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { backgroundApi, type BackgroundSettings, type BackgroundTarget, type BgConfig } from '@/api/backgrounds'
export type { BgConfig } from '@/api/backgrounds'

export const backgroundTargets: Array<{ key: BackgroundTarget; label: string }> = [
  { key: 'app', label: 'Web app' }, { key: 'login', label: 'Web login' },
  { key: 'android-app', label: 'Android app' },
]
export const defaultBackground: BgConfig = { type: 'color', gradientAngle: 135, gradientStart: '#0d0d0d', gradientEnd: '#1a1a3e', blur: 0, brightness: 100, overlay: 40, version: 0 }
const emptySettings = (): BackgroundSettings => ({ targets: Object.fromEntries(backgroundTargets.map(t => [t.key, { ...defaultBackground }])) as BackgroundSettings['targets'], surfaceTransparency: 0, configured: false, sourceVersion: 0 })

export const useBackgroundStore = defineStore('background', () => {
  const settings = ref<BackgroundSettings>(emptySettings())
  const ready = ref(false)
  const saving = ref(false)
  const error = ref('')
  const appBg = computed(() => settings.value.targets.app)
  const loginBg = computed(() => settings.value.targets.login)
  const appBgImageVersion = computed(() => appBg.value.version)
  const loginBgImageVersion = computed(() => loginBg.value.version)
  const imageUrl = (target: BackgroundTarget) => settings.value.targets[target].version > 0 ? `/api/v1/settings/background-image/${target}?v=${settings.value.targets[target].version}` : null
  const appBgImage = computed(() => imageUrl('app'))
  const loginBgImage = computed(() => imageUrl('login'))
  const gradientPreview = (cfg: BgConfig) => `linear-gradient(${cfg.gradientAngle}deg, ${cfg.gradientStart}, ${cfg.gradientEnd})`
  const visible = (cfg: BgConfig) => cfg.type === 'gradient' || (cfg.type === 'image' && cfg.version > 0)
  function layerStyle(target: BackgroundTarget): Record<string, string> {
    const cfg = settings.value.targets[target]
    const source = cfg.type === 'gradient' ? gradientPreview(cfg) : cfg.type === 'image' && imageUrl(target) ? `url("${imageUrl(target)}")` : ''
    if (!source) return {}
    const scrim = `rgba(var(--bg-scrim-rgb), ${cfg.overlay / 100})`
    return { backgroundImage: `linear-gradient(${scrim}, ${scrim}), ${source}`, backgroundSize: 'cover', backgroundPosition: 'center', filter: `blur(${cfg.blur}px) brightness(${cfg.brightness}%)` }
  }
  const appBgLayerVisible = computed(() => visible(appBg.value))
  const loginBgLayerVisible = computed(() => visible(loginBg.value))
  const appBgLayerStyle = computed(() => layerStyle('app'))
  const loginBgLayerStyle = computed(() => layerStyle('login'))
  const hasCustomBg = computed(() => backgroundTargets.some(t => settings.value.targets[t.key].type !== 'color'))
  function applyAppBg() {
    document.body.style.backgroundColor = appBgLayerVisible.value ? 'transparent' : ''
    document.documentElement.style.setProperty('--surface-opacity', `${100 - settings.value.surfaceTransparency}%`)
  }
  function accept(data: BackgroundSettings) { error.value = ''; settings.value = data; ready.value = true; applyAppBg() }
  function report(e: any) { error.value = typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Background settings could not be saved. Please retry.' }
  async function loadShared() {
    try { accept((await backgroundApi.get()).data) } catch (e) { report(e) }
  }
  // Serialize writes so fast slider changes cannot land on the server out of order.
  let pending = Promise.resolve()
  let writes = 0
  function save(patch: Parameters<typeof backgroundApi.save>[0]) {
    error.value = ''; writes++; saving.value = true
    pending = pending.then(async () => {
      try { await backgroundApi.save(patch) } catch (e) { report(e) }
    }).finally(() => { writes--; saving.value = writes > 0 })
    return pending
  }
  function setBackground(target: BackgroundTarget, patch: Partial<BgConfig>) {
    const cfg = { ...settings.value.targets[target], ...patch }
    settings.value.targets[target] = cfg
    applyAppBg()
    return save({ targets: { [target]: cfg } })
  }
  function setTransparency(value: number) {
    settings.value.surfaceTransparency = Math.min(90, Math.max(0, value))
    applyAppBg()
    return save({ surfaceTransparency: settings.value.surfaceTransparency })
  }
  async function applyImage(file: Blob, targets: BackgroundTarget[]) {
    await pending
    accept((await backgroundApi.apply(file, targets)).data)
  }
  async function applyCrops(source: Blob, web: Blob, android: Blob | null, targets: BackgroundTarget[]) {
    await pending
    accept((await backgroundApi.applyCrops(source, web, android, targets)).data)
  }
  async function copy(source: BackgroundTarget, targets: BackgroundTarget[]) {
    await pending
    accept((await backgroundApi.copy(source, targets)).data)
  }
  async function remove(target: BackgroundTarget) {
    await pending
    await backgroundApi.remove(target)
    await loadShared()
  }
  async function reset(target: BackgroundTarget) {
    await remove(target)
    await setBackground(target, { ...defaultBackground })
  }
  // Migrate old per-user display preferences once, only on an unconfigured server.
  async function loadFromDb(data: { appBg?: unknown; loginBg?: unknown }) {
    await loadShared()
    if (settings.value.configured || !ready.value) return
    const targets: Partial<Record<BackgroundTarget, BgConfig>> = {}
    for (const [target, value] of [['app', data.appBg], ['login', data.loginBg]] as const) {
      if (value && typeof value === 'object') targets[target] = { ...settings.value.targets[target], ...value }
    }
    if (Object.keys(targets).length) {
      try { accept((await backgroundApi.save({ targets })).data) } catch (e) { report(e) }
    }
  }
  async function migrateLegacyImages() {
    for (const target of ['app', 'login'] as const) {
      const key = `cp_bg_${target}_img`
      const legacy = localStorage.getItem(key)
      if (!legacy?.startsWith('data:')) continue
      try { await applyImage(await (await fetch(legacy)).blob(), [target]); localStorage.removeItem(key) } catch (e) { report(e) }
    }
  }
  return { settings, ready, saving, error, appBg, loginBg, appBgImage, loginBgImage, appBgImageVersion, loginBgImageVersion,
    appBgLayerVisible, loginBgLayerVisible, appBgLayerStyle, loginBgLayerStyle, hasCustomBg, imageUrl, gradientPreview, applyAppBg,
    setBackground, setTransparency, loadShared, applyImage, applyCrops, copy, remove, reset, loadFromDb, migrateLegacyImages }
})
