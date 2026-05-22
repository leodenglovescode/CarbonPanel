import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { type Locale, messages, resolveKey } from '@/i18n'

const STORAGE_KEY = 'cp_locale'

export const useLocaleStore = defineStore('locale', () => {
  const locale = ref<Locale>(
    (localStorage.getItem(STORAGE_KEY) as Locale | null) ?? 'en',
  )

  function setLocale(l: Locale) {
    locale.value = l
    localStorage.setItem(STORAGE_KEY, l)
  }

  const msgs = computed(() => messages[locale.value])

  function t(key: string, vars?: Record<string, string | number>): string {
    let str = resolveKey(msgs.value, key)
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        str = str.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
      }
    }
    return str
  }

  return { locale, setLocale, t }
})
