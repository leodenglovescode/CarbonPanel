import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type Theme = 'dark' | 'light'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>((localStorage.getItem('cp_theme') as Theme) ?? 'dark')

  function apply(t: Theme) {
    document.documentElement.setAttribute('data-theme', t)
  }

  function setTheme(t: Theme) {
    theme.value = t
    localStorage.setItem('cp_theme', t)
    apply(t)
  }

  function toggle() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  // Apply immediately on store init
  apply(theme.value)

  return { theme, setTheme, toggle }
})
