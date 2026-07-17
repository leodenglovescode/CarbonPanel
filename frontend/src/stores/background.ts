import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

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
const APP_BG_IMG_KEY = 'cp_bg_app_img'
const LOGIN_BG_KEY = 'cp_bg_login'
const LOGIN_BG_IMG_KEY = 'cp_bg_login_img'

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

function loadImage(key: string): string | null {
  try { return localStorage.getItem(key) } catch { return null }
}

function gradientCss(cfg: BgConfig): string {
  return `linear-gradient(${cfg.gradientAngle}deg, ${cfg.gradientStart}, ${cfg.gradientEnd})`
}

export const useBackgroundStore = defineStore('background', () => {
  const appBg = ref<BgConfig>(loadConfig(APP_BG_KEY))
  const loginBg = ref<BgConfig>(loadConfig(LOGIN_BG_KEY))
  const appBgImage = ref<string | null>(loadImage(APP_BG_IMG_KEY))
  const loginBgImage = ref<string | null>(loadImage(LOGIN_BG_IMG_KEY))

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

  function setAppBgImage(dataUrl: string | null) {
    appBgImage.value = dataUrl
    if (dataUrl) localStorage.setItem(APP_BG_IMG_KEY, dataUrl)
    else localStorage.removeItem(APP_BG_IMG_KEY)
    applyAppBg()
  }

  function resetAppBg() {
    appBg.value = { ...DEFAULT_BG }
    appBgImage.value = null
    localStorage.removeItem(APP_BG_KEY)
    localStorage.removeItem(APP_BG_IMG_KEY)
    applyAppBg()
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
    else if (cfg.type === 'image' && img) backgroundImage = `${scrimLayer(cfg.overlay)}, url(${img})`
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

  function setLoginBgImage(dataUrl: string | null) {
    loginBgImage.value = dataUrl
    if (dataUrl) localStorage.setItem(LOGIN_BG_IMG_KEY, dataUrl)
    else localStorage.removeItem(LOGIN_BG_IMG_KEY)
  }

  function resetLoginBg() {
    loginBg.value = { ...DEFAULT_BG }
    loginBgImage.value = null
    localStorage.removeItem(LOGIN_BG_KEY)
    localStorage.removeItem(LOGIN_BG_IMG_KEY)
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
    appBgImage?: string | null
    loginBgImage?: string | null
  }) {
    if (data.appBg) {
      appBg.value = parseConfig(data.appBg)
      localStorage.setItem(APP_BG_KEY, JSON.stringify(appBg.value))
      applyAppBg()
    }
    if ('appBgImage' in data) {
      appBgImage.value = data.appBgImage ?? null
      if (data.appBgImage) localStorage.setItem(APP_BG_IMG_KEY, data.appBgImage)
      else localStorage.removeItem(APP_BG_IMG_KEY)
      applyAppBg()
    }
    if (data.loginBg) {
      loginBg.value = parseConfig(data.loginBg)
      localStorage.setItem(LOGIN_BG_KEY, JSON.stringify(loginBg.value))
    }
    if ('loginBgImage' in data) {
      loginBgImage.value = data.loginBgImage ?? null
      if (data.loginBgImage) localStorage.setItem(LOGIN_BG_IMG_KEY, data.loginBgImage)
      else localStorage.removeItem(LOGIN_BG_IMG_KEY)
    }
  }

  return {
    appBg,
    loginBg,
    appBgImage,
    loginBgImage,
    appBgLayerVisible,
    appBgLayerStyle,
    loginBgLayerVisible,
    loginBgLayerStyle,
    hasCustomBg,
    isCustom,
    gradientPreview,
    applyAppBg,
    setAppBg,
    setAppBgImage,
    resetAppBg,
    setLoginBg,
    setLoginBgImage,
    resetLoginBg,
    loadFromDb,
  }
})
