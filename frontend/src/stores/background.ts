import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { backgroundImageApi } from '@/api/index'

export interface BgConfig {
  type: 'color' | 'gradient' | 'image'
  gradientAngle: number
  gradientStart: string
  gradientEnd: string
  blur: number
  brightness: number
  overlay: number
}

const DEFAULT_BG: BgConfig = {
  type: 'color',
  gradientAngle: 135,
  gradientStart: '#0d0d0d',
  gradientEnd: '#1a1a3e',
  blur: 0,
  brightness: 100,
  // Scrim strength (0-80) darkening/lightening custom backgrounds toward the
  // active theme's base color, so text and controls in glass cards stay
  // readable regardless of how bright the user's image/gradient is. Applied
  // by default so it doesn't rely on the user noticing a contrast problem;
  // the Settings slider lets them dial it down or up for their own image.
  overlay: 40,
}

const APP_BG_KEY = 'cp_bg_app'
const LOGIN_BG_KEY = 'cp_bg_login'
// The images themselves live server-side (see backgroundImageApi /
// backend/app/api/background_images.py) — a base64 copy of a multi-MB photo
// used to blow the browser's ~5-10MB localStorage quota, which silently
// broke the transparent-body toggle further down the call chain and made
// custom backgrounds render as a flat color instead of the photo. All that's
// kept client-side now is a small version counter used to cache-bust the URL.
const APP_BG_IMG_VERSION_KEY = 'cp_bg_app_img_v'
const LOGIN_BG_IMG_VERSION_KEY = 'cp_bg_login_img_v'
// Pre-migration keys — only read once, to carry an existing image over to
// server-side storage. Never written again after this version.
const LEGACY_APP_BG_IMG_KEY = 'cp_bg_app_img'
const LEGACY_LOGIN_BG_IMG_KEY = 'cp_bg_login_img'

function parseConfig(raw: unknown): BgConfig {
  if (!raw || typeof raw !== 'object') return { ...DEFAULT_BG }
  const p = raw as Record<string, unknown>
  return {
    type: ['color', 'gradient', 'image'].includes(p.type as string) ? (p.type as BgConfig['type']) : DEFAULT_BG.type,
    gradientAngle: typeof p.gradientAngle === 'number' ? p.gradientAngle : DEFAULT_BG.gradientAngle,
    gradientStart: typeof p.gradientStart === 'string' ? p.gradientStart : DEFAULT_BG.gradientStart,
    gradientEnd: typeof p.gradientEnd === 'string' ? p.gradientEnd : DEFAULT_BG.gradientEnd,
    blur: typeof p.blur === 'number' ? Math.min(20, Math.max(0, p.blur)) : DEFAULT_BG.blur,
    brightness: typeof p.brightness === 'number' ? Math.min(150, Math.max(30, p.brightness)) : DEFAULT_BG.brightness,
    overlay: typeof p.overlay === 'number' ? Math.min(80, Math.max(0, p.overlay)) : DEFAULT_BG.overlay,
  }
}

// Scrim color tracks the active theme (--fg is light-on-dark by default, dark-on-light
// under [data-theme="light"]) so the overlay always pushes custom backgrounds toward
// the base the theme's own text/border colors were tuned against.
function scrimLayer(overlay: number): string {
  const alpha = (overlay / 100).toFixed(2)
  return `linear-gradient(rgba(var(--bg-scrim-rgb), ${alpha}), rgba(var(--bg-scrim-rgb), ${alpha}))`
}

function loadConfig(key: string): BgConfig {
  try {
    return parseConfig(JSON.parse(localStorage.getItem(key) || 'null'))
  } catch {
    return { ...DEFAULT_BG }
  }
}

function loadVersion(key: string): number {
  const v = parseInt(localStorage.getItem(key) || '0', 10)
  return Number.isFinite(v) && v > 0 ? v : 0
}

function gradientCss(cfg: BgConfig): string {
  return `linear-gradient(${cfg.gradientAngle}deg, ${cfg.gradientStart}, ${cfg.gradientEnd})`
}

export const useBackgroundStore = defineStore('background', () => {
  const appBg = ref<BgConfig>(loadConfig(APP_BG_KEY))
  const loginBg = ref<BgConfig>(loadConfig(LOGIN_BG_KEY))
  const appBgImageVersion = ref<number>(loadVersion(APP_BG_IMG_VERSION_KEY))
  const loginBgImageVersion = ref<number>(loadVersion(LOGIN_BG_IMG_VERSION_KEY))

  // Public URLs for the compressed images, cache-busted by version so a
  // re-upload is picked up immediately instead of showing the old cached one.
  const appBgImage = computed(() => (appBgImageVersion.value > 0 ? `/api/v1/settings/background-image/app?v=${appBgImageVersion.value}` : null))
  const loginBgImage = computed(() => (loginBgImageVersion.value > 0 ? `/api/v1/settings/background-image/login?v=${loginBgImageVersion.value}` : null))

  // ── App background (applied via a Vue-rendered fixed layer in App.vue) ──────

  const appBgLayerVisible = computed(() => {
    const cfg = appBg.value
    if (cfg.type === 'gradient') return true
    if (cfg.type === 'image' && appBgImage.value) return true
    return false
  })

  const appBgLayerStyle = computed((): Record<string, string> => {
    const cfg = appBg.value
    const img = appBgImage.value
    const filter = [cfg.blur > 0 ? `blur(${cfg.blur}px)` : '', cfg.brightness !== 100 ? `brightness(${cfg.brightness}%)` : ''].filter(Boolean).join(' ')
    if (cfg.type === 'gradient') {
      return { backgroundImage: `${scrimLayer(cfg.overlay)}, ${gradientCss(cfg)}`, filter }
    }
    if (cfg.type === 'image' && img) {
      return { backgroundImage: `${scrimLayer(cfg.overlay)}, url("${img}")`, backgroundSize: 'cover', backgroundPosition: 'center', filter }
    }
    return {}
  })

  function applyAppBg() {
    // Make body transparent when a custom layer is active so the layer shows through
    if (appBgLayerVisible.value) {
      document.body.style.backgroundColor = 'transparent'
    } else {
      document.body.style.backgroundColor = ''
    }
  }

  function setAppBg(patch: Partial<BgConfig>) {
    appBg.value = { ...appBg.value, ...patch }
    localStorage.setItem(APP_BG_KEY, JSON.stringify(appBg.value))
    applyAppBg()
  }

  function setAppBgImageVersion(version: number | null) {
    appBgImageVersion.value = version ?? 0
    if (version) localStorage.setItem(APP_BG_IMG_VERSION_KEY, String(version))
    else localStorage.removeItem(APP_BG_IMG_VERSION_KEY)
    applyAppBg()
  }

  function resetAppBg() {
    const hadImage = appBgImageVersion.value > 0
    appBg.value = { ...DEFAULT_BG }
    appBgImageVersion.value = 0
    localStorage.removeItem(APP_BG_KEY)
    localStorage.removeItem(APP_BG_IMG_VERSION_KEY)
    applyAppBg()
    if (hadImage) backgroundImageApi.remove('app').catch(() => {})
  }

  // ── Login background (applied via Vue-rendered layer in LoginView) ─────────

  const loginBgLayerVisible = computed(() => {
    const cfg = loginBg.value
    if (cfg.type === 'gradient') return true
    if (cfg.type === 'image' && loginBgImage.value) return true
    return false
  })

  const loginBgLayerStyle = computed((): Record<string, string> => {
    const cfg = loginBg.value
    const img = loginBgImage.value
    let backgroundImage = ''
    if (cfg.type === 'gradient') backgroundImage = `${scrimLayer(cfg.overlay)}, ${gradientCss(cfg)}`
    else if (cfg.type === 'image' && img) backgroundImage = `${scrimLayer(cfg.overlay)}, url("${img}")`
    const style: Record<string, string> = {
      backgroundImage,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
    }
    const filter = [cfg.blur > 0 ? `blur(${cfg.blur}px)` : '', cfg.brightness !== 100 ? `brightness(${cfg.brightness}%)` : ''].filter(Boolean).join(' ')
    if (filter) style.filter = filter
    return style
  })

  function setLoginBg(patch: Partial<BgConfig>) {
    loginBg.value = { ...loginBg.value, ...patch }
    localStorage.setItem(LOGIN_BG_KEY, JSON.stringify(loginBg.value))
  }

  function setLoginBgImageVersion(version: number | null) {
    loginBgImageVersion.value = version ?? 0
    if (version) localStorage.setItem(LOGIN_BG_IMG_VERSION_KEY, String(version))
    else localStorage.removeItem(LOGIN_BG_IMG_VERSION_KEY)
  }

  function resetLoginBg() {
    const hadImage = loginBgImageVersion.value > 0
    loginBg.value = { ...DEFAULT_BG }
    loginBgImageVersion.value = 0
    localStorage.removeItem(LOGIN_BG_KEY)
    localStorage.removeItem(LOGIN_BG_IMG_VERSION_KEY)
    if (hadImage) backgroundImageApi.remove('login').catch(() => {})
  }

  // ── One-time migration from the old localStorage-blob storage ──────────────
  // Requires auth (the upload endpoint does), so this is called from App.vue
  // once the user is logged in — not from this store's own init.

  async function migrateLegacyImageIfPresent(target: 'app' | 'login') {
    const legacyKey = target === 'app' ? LEGACY_APP_BG_IMG_KEY : LEGACY_LOGIN_BG_IMG_KEY
    const dataUrl = localStorage.getItem(legacyKey)
    if (!dataUrl) return
    if (!dataUrl.startsWith('data:')) {
      localStorage.removeItem(legacyKey)
      return
    }
    try {
      const blob = await (await fetch(dataUrl)).blob()
      const file = new File([blob], `${target}-background`, { type: blob.type || 'image/png' })
      await backgroundImageApi.upload(target, file)
      if (target === 'app') setAppBgImageVersion(Date.now())
      else setLoginBgImageVersion(Date.now())
      localStorage.removeItem(legacyKey)
    } catch {
      // Leave the legacy key in place so this retries on next login instead
      // of silently dropping the user's configured image.
    }
  }

  function migrateLegacyImages() {
    void migrateLegacyImageIfPresent('app')
    void migrateLegacyImageIfPresent('login')
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

  function isCustom(cfg: BgConfig): boolean {
    return cfg.type !== 'color' || cfg.blur > 0 || cfg.brightness !== 100
  }

  const hasCustomBg = computed(() => isCustom(appBg.value) || isCustom(loginBg.value))

  function gradientPreview(cfg: BgConfig): string {
    return gradientCss(cfg)
  }

  // Apply on store init
  applyAppBg()

  function loadFromDb(data: {
    appBg?: unknown
    loginBg?: unknown
    appBgImageVersion?: number | null
    loginBgImageVersion?: number | null
  }) {
    if (data.appBg) {
      appBg.value = parseConfig(data.appBg)
      localStorage.setItem(APP_BG_KEY, JSON.stringify(appBg.value))
      applyAppBg()
    }
    if ('appBgImageVersion' in data) {
      setAppBgImageVersion(data.appBgImageVersion ?? null)
    }
    if (data.loginBg) {
      loginBg.value = parseConfig(data.loginBg)
      localStorage.setItem(LOGIN_BG_KEY, JSON.stringify(loginBg.value))
    }
    if ('loginBgImageVersion' in data) {
      setLoginBgImageVersion(data.loginBgImageVersion ?? null)
    }
  }

  return {
    appBg,
    loginBg,
    appBgImage,
    loginBgImage,
    appBgImageVersion,
    loginBgImageVersion,
    appBgLayerVisible,
    appBgLayerStyle,
    loginBgLayerVisible,
    loginBgLayerStyle,
    hasCustomBg,
    isCustom,
    gradientPreview,
    applyAppBg,
    setAppBg,
    setAppBgImageVersion,
    resetAppBg,
    setLoginBg,
    setLoginBgImageVersion,
    resetLoginBg,
    loadFromDb,
    migrateLegacyImages,
  }
})
