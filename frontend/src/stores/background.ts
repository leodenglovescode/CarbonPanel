import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface BgConfig {
  type: 'color' | 'gradient' | 'image'
  gradientAngle: number
  gradientStart: string
  gradientEnd: string
  blur: number
}

const DEFAULT_BG: BgConfig = {
  type: 'color',
  gradientAngle: 135,
  gradientStart: '#0d0d0d',
  gradientEnd: '#1a1a3e',
  blur: 0,
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
  }
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

  // ── App background (applied via body::before using CSS custom props) ──────

  function applyAppBg() {
    const cfg = appBg.value
    const img = appBgImage.value
    const root = document.documentElement

    if (cfg.type === 'gradient') {
      root.style.setProperty('--app-bg-image', gradientCss(cfg))
      root.style.setProperty('--app-bg-blur', cfg.blur > 0 ? `${cfg.blur}px` : '0px')
      document.body.style.background = 'transparent'
    } else if (cfg.type === 'image' && img) {
      root.style.setProperty('--app-bg-image', `url(${img})`)
      root.style.setProperty('--app-bg-blur', cfg.blur > 0 ? `${cfg.blur}px` : '0px')
      document.body.style.background = 'transparent'
    } else {
      root.style.setProperty('--app-bg-image', 'none')
      root.style.setProperty('--app-bg-blur', '0px')
      document.body.style.background = ''
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
    if (cfg.type === 'gradient') backgroundImage = gradientCss(cfg)
    else if (cfg.type === 'image' && img) backgroundImage = `url(${img})`
    const style: Record<string, string> = {
      backgroundImage,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
    }
    if (cfg.blur > 0) style.filter = `blur(${cfg.blur}px)`
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
    return cfg.type !== 'color' || cfg.blur > 0
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
