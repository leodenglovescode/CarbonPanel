import { defineStore } from 'pinia'
import { ref } from 'vue'

export type Theme = 'dark' | 'light' | 'auto'

const mq = window.matchMedia('(prefers-color-scheme: dark)')

function resolvedTheme(t: Theme): 'dark' | 'light' {
  if (t === 'auto') return mq.matches ? 'dark' : 'light'
  return t
}

function applyTheme(t: Theme) {
  document.documentElement.setAttribute('data-theme', resolvedTheme(t))
}

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>((localStorage.getItem('cp_theme') as Theme) ?? 'dark')

  // Apply on OS preference change when set to auto
  mq.addEventListener('change', () => {
    if (theme.value === 'auto') applyTheme('auto')
  })

  function setTheme(t: Theme) {
    theme.value = t
    localStorage.setItem('cp_theme', t)
    applyTheme(t)
  }

  // Apply immediately on store init
  applyTheme(theme.value)

  return { theme, setTheme }
})
