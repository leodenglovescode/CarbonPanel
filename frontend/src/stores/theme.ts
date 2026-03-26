import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type Theme = 'dark' | 'light' | 'auto'
type ResolvedTheme = 'dark' | 'light'

export interface StyleSettings {
  bg: string | null
  bgCard: string | null
  bgInput: string | null
  border: string | null
  fg: string | null
  fgMuted: string | null
  fgDim: string | null
  accent: string | null
  danger: string | null
  warning: string | null
  info: string | null
  font: string | null
  fontSize: number | null
  highContrast: boolean | null
}

export interface ResolvedStyleSettings {
  bg: string
  bgCard: string
  bgInput: string
  border: string
  fg: string
  fgMuted: string
  fgDim: string
  accent: string
  danger: string
  warning: string
  info: string
  font: string
  fontSize: number
  highContrast: boolean
}

const mq = window.matchMedia('(prefers-color-scheme: dark)')
const THEME_STORAGE_KEY = 'cp_theme'
const STYLE_STORAGE_KEY = 'cp_style_settings'
const DEFAULT_THEME: Theme = 'dark'

const DEFAULT_STYLE_SETTINGS: StyleSettings = {
  bg: null,
  bgCard: null,
  bgInput: null,
  border: null,
  fg: null,
  fgMuted: null,
  fgDim: null,
  accent: null,
  danger: null,
  warning: null,
  info: null,
  font: null,
  fontSize: null,
  highContrast: null,
}

const THEME_STYLE_DEFAULTS: Record<ResolvedTheme, ResolvedStyleSettings> = {
  dark: {
    bg: '#0d0d0d',
    bgCard: '#111111',
    bgInput: '#1a1a1a',
    border: '#222222',
    fg: '#e0e0e0',
    fgMuted: '#666666',
    fgDim: '#444444',
    accent: '#00ff88',
    danger: '#ff4444',
    warning: '#ffaa00',
    info: '#4488ff',
    font: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
    fontSize: 12,
    highContrast: false,
  },
  light: {
    bg: '#f0f0f0',
    bgCard: '#ffffff',
    bgInput: '#ebebeb',
    border: '#d8d8d8',
    fg: '#111111',
    fgMuted: '#555555',
    fgDim: '#999999',
    accent: '#00aa55',
    danger: '#dd2222',
    warning: '#cc8800',
    info: '#2266dd',
    font: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
    fontSize: 12,
    highContrast: false,
  },
}

function isTheme(value: string | null): value is Theme {
  return value === 'dark' || value === 'light' || value === 'auto'
}

function resolvedTheme(t: Theme): ResolvedTheme {
  if (t === 'auto') return mq.matches ? 'dark' : 'light'
  return t
}

function getThemeDefaults(t: Theme): ResolvedStyleSettings {
  return { ...THEME_STYLE_DEFAULTS[resolvedTheme(t)] }
}

function parseHexColor(color: string): [number, number, number] | null {
  let hex = color.trim().replace('#', '')
  if (!/^[\da-fA-F]{3}$|^[\da-fA-F]{6}$/.test(hex)) return null

  if (hex.length === 3) {
    hex = hex
      .split('')
      .map((char) => `${char}${char}`)
      .join('')
  }

  const value = Number.parseInt(hex, 16)
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
}

function toRgba(color: string, alpha: number): string {
  const rgb = parseHexColor(color)
  if (!rgb) return color
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`
}

function toHexColor(rgb: number[]): string {
  return `#${rgb.map((channel) => channel.toString(16).padStart(2, '0')).join('')}`
}

function lightenColor(color: string, amount: number): string {
  const rgb = parseHexColor(color)
  if (!rgb) return color

  const next = rgb.map((channel) => Math.round(channel + (255 - channel) * amount))
  return toHexColor(next)
}

function darkenColor(color: string, amount: number): string {
  const rgb = parseHexColor(color)
  if (!rgb) return color

  const next = rgb.map((channel) => Math.round(channel * (1 - amount)))
  return toHexColor(next)
}

function sanitizeStyleSettings(value: unknown): StyleSettings {
  if (!value || typeof value !== 'object') {
    return { ...DEFAULT_STYLE_SETTINGS }
  }

  const raw = value as Record<string, unknown>

  return {
    bg: typeof raw.bg === 'string' && raw.bg.trim() ? raw.bg : null,
    bgCard: typeof raw.bgCard === 'string' && raw.bgCard.trim() ? raw.bgCard : null,
    bgInput: typeof raw.bgInput === 'string' && raw.bgInput.trim() ? raw.bgInput : null,
    border: typeof raw.border === 'string' && raw.border.trim() ? raw.border : null,
    fg: typeof raw.fg === 'string' && raw.fg.trim() ? raw.fg : null,
    fgMuted: typeof raw.fgMuted === 'string' && raw.fgMuted.trim() ? raw.fgMuted : null,
    fgDim: typeof raw.fgDim === 'string' && raw.fgDim.trim() ? raw.fgDim : null,
    accent: typeof raw.accent === 'string' && raw.accent.trim() ? raw.accent : null,
    danger: typeof raw.danger === 'string' && raw.danger.trim() ? raw.danger : null,
    warning: typeof raw.warning === 'string' && raw.warning.trim() ? raw.warning : null,
    info: typeof raw.info === 'string' && raw.info.trim() ? raw.info : null,
    font: typeof raw.font === 'string' && raw.font.trim() ? raw.font : null,
    fontSize:
      typeof raw.fontSize === 'number' && Number.isFinite(raw.fontSize)
        ? Math.min(18, Math.max(10, Math.round(raw.fontSize)))
        : null,
    highContrast: typeof raw.highContrast === 'boolean' ? raw.highContrast : null,
  }
}

function getResolvedStyleSettings(
  t: Theme,
  styleSettings: StyleSettings,
): ResolvedStyleSettings {
  const defaults = getThemeDefaults(t)

  return {
    bg: styleSettings.bg ?? defaults.bg,
    bgCard: styleSettings.bgCard ?? defaults.bgCard,
    bgInput: styleSettings.bgInput ?? defaults.bgInput,
    border: styleSettings.border ?? defaults.border,
    fg: styleSettings.fg ?? defaults.fg,
    fgMuted: styleSettings.fgMuted ?? defaults.fgMuted,
    fgDim: styleSettings.fgDim ?? defaults.fgDim,
    accent: styleSettings.accent ?? defaults.accent,
    danger: styleSettings.danger ?? defaults.danger,
    warning: styleSettings.warning ?? defaults.warning,
    info: styleSettings.info ?? defaults.info,
    font: styleSettings.font ?? defaults.font,
    fontSize: styleSettings.fontSize ?? defaults.fontSize,
    highContrast: styleSettings.highContrast ?? defaults.highContrast,
  }
}

function getAppliedStyleSettings(t: Theme, styleSettings: StyleSettings): ResolvedStyleSettings {
  const resolved = getResolvedStyleSettings(t, styleSettings)

  if (!resolved.highContrast) {
    return resolved
  }

  return {
    ...resolved,
    bg: darkenColor(resolved.bg, 0.7),
    bgCard: darkenColor(resolved.bgCard, 0.6),
    bgInput: darkenColor(resolved.bgInput, 0.5),
    border: lightenColor(resolved.border, 0.2),
    fg: lightenColor(resolved.fg, 0.45),
    fgMuted: lightenColor(resolved.fgMuted, 0.55),
    fgDim: lightenColor(resolved.fgDim, 0.6),
    accent: lightenColor(resolved.accent, 0.15),
    danger: lightenColor(resolved.danger, 0.15),
    warning: lightenColor(resolved.warning, 0.15),
    info: lightenColor(resolved.info, 0.15),
  }
}

function applyTheme(t: Theme) {
  document.documentElement.setAttribute('data-theme', resolvedTheme(t))
}

function applyStyleSettings(t: Theme, styleSettings: StyleSettings) {
  const themeKind = resolvedTheme(t)
  const resolved = getAppliedStyleSettings(t, styleSettings)
  const effectiveDark = themeKind === 'dark' || resolved.highContrast
  const rootStyle = document.documentElement.style

  rootStyle.setProperty('--bg', resolved.bg)
  rootStyle.setProperty('--bg-card', resolved.bgCard)
  rootStyle.setProperty('--bg-card-hover', effectiveDark ? lightenColor(resolved.bgCard, 0.04) : darkenColor(resolved.bgCard, 0.03))
  rootStyle.setProperty('--bg-input', resolved.bgInput)
  rootStyle.setProperty('--border', resolved.border)
  rootStyle.setProperty('--border-subtle', effectiveDark ? lightenColor(resolved.bgInput, 0.03) : darkenColor(resolved.bgInput, 0.03))
  rootStyle.setProperty('--fg', resolved.fg)
  rootStyle.setProperty('--fg-muted', resolved.fgMuted)
  rootStyle.setProperty('--fg-dim', resolved.fgDim)
  rootStyle.setProperty('--accent', resolved.accent)
  rootStyle.setProperty('--danger', resolved.danger)
  rootStyle.setProperty('--warning', resolved.warning)
  rootStyle.setProperty('--info', resolved.info)
  rootStyle.setProperty('--font', resolved.font)
  rootStyle.setProperty('--font-size', `${resolved.fontSize}px`)
  rootStyle.setProperty('--accent-dim', toRgba(resolved.accent, 0.1))
  rootStyle.setProperty('--accent-border', toRgba(resolved.accent, effectiveDark ? 0.2 : 0.25))
  rootStyle.setProperty('--danger-dim', toRgba(resolved.danger, effectiveDark ? 0.1 : 0.08))
  rootStyle.setProperty('--warning-dim', toRgba(resolved.warning, 0.1))
  rootStyle.setProperty('--accent-hover', lightenColor(resolved.accent, effectiveDark ? 0.2 : 0.12))
  rootStyle.setProperty('--bg-subtle', effectiveDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)')
  rootStyle.setProperty('--bg-hover', effectiveDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.05)')
  rootStyle.setProperty('--bg-stripe', effectiveDark ? 'rgba(255,255,255,0.015)' : 'rgba(0,0,0,0.025)')
  rootStyle.setProperty('--border-row', effectiveDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.06)')
  rootStyle.setProperty('--bg-badge', effectiveDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)')
  rootStyle.setProperty('--shadow-card', effectiveDark ? '0 2px 12px rgba(0,0,0,0.55)' : '0 2px 8px rgba(0,0,0,0.08)')
  rootStyle.setProperty(
    '--shadow-card-hover',
    effectiveDark
      ? `0 4px 20px rgba(0,0,0,0.75), 0 0 0 1px ${toRgba(resolved.accent, 0.12)}`
      : `0 4px 16px rgba(0,0,0,0.14), 0 0 0 1px ${toRgba(resolved.accent, 0.12)}`,
  )
}

function loadTheme(): Theme {
  const saved = localStorage.getItem(THEME_STORAGE_KEY)
  return isTheme(saved) ? saved : DEFAULT_THEME
}

function loadStyleSettings(): StyleSettings {
  const saved = localStorage.getItem(STYLE_STORAGE_KEY)
  if (!saved) return { ...DEFAULT_STYLE_SETTINGS }

  try {
    return sanitizeStyleSettings(JSON.parse(saved))
  } catch {
    return { ...DEFAULT_STYLE_SETTINGS }
  }
}

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>(loadTheme())
  const styleSettings = ref<StyleSettings>(loadStyleSettings())

  const defaultStyleSettings = computed(() => getThemeDefaults(theme.value))
  const resolvedStyleSettings = computed(() =>
    getResolvedStyleSettings(theme.value, styleSettings.value),
  )
  const hasStyleOverrides = computed(() =>
    Object.values(styleSettings.value).some((value) => value !== null),
  )

  function persistStyleSettings() {
    if (hasStyleOverrides.value) {
      localStorage.setItem(STYLE_STORAGE_KEY, JSON.stringify(styleSettings.value))
      return
    }

    localStorage.removeItem(STYLE_STORAGE_KEY)
  }

  mq.addEventListener('change', () => {
    if (theme.value === 'auto') {
      applyTheme('auto')
      applyStyleSettings('auto', styleSettings.value)
    }
  })

  function setTheme(t: Theme) {
    theme.value = t
    localStorage.setItem(THEME_STORAGE_KEY, t)
    applyTheme(t)
    applyStyleSettings(t, styleSettings.value)
  }

  function setStyleSetting<K extends keyof StyleSettings>(key: K, value: StyleSettings[K]) {
    styleSettings.value = {
      ...styleSettings.value,
      [key]: value,
    }
    persistStyleSettings()
    applyStyleSettings(theme.value, styleSettings.value)
  }

  function resetStyleSettings() {
    styleSettings.value = { ...DEFAULT_STYLE_SETTINGS }
    persistStyleSettings()
    applyStyleSettings(theme.value, styleSettings.value)
  }

  applyTheme(theme.value)
  applyStyleSettings(theme.value, styleSettings.value)

  return {
    theme,
    styleSettings,
    defaultStyleSettings,
    resolvedStyleSettings,
    hasStyleOverrides,
    setTheme,
    setStyleSetting,
    resetStyleSettings,
  }
})
