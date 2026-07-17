import { watch } from 'vue'
import { useThemeStore } from '@/stores/theme'
import { useDisplayPrefsStore } from '@/stores/displayPrefs'
import { useAlertsStore } from '@/stores/alerts'
import { useBackgroundStore } from '@/stores/background'
import { useSiteTrafficStore } from '@/stores/siteTraffic'
import { userPrefsApi } from '@/api'

// Module-level so only one debounce timer exists regardless of how many times the composable is called
let _saveTimer: ReturnType<typeof setTimeout> | null = null
let _loading = false

export function useUserPrefsSync() {
  const theme = useThemeStore()
  const display = useDisplayPrefsStore()
  const alerts = useAlertsStore()
  const bg = useBackgroundStore()
  const siteTraffic = useSiteTrafficStore()

  function collect(): Record<string, unknown> {
    return {
      theme: theme.theme,
      styleSettings: { ...theme.styleSettings },
      displayPrefs: {
        ramUnit: display.ramUnit,
        networkUnit: display.networkUnit,
        storageUnit: display.storageUnit,
      },
      alerts: {
        cpu: alerts.thresholds.cpu,
        ram: alerts.thresholds.ram,
        disk: alerts.thresholds.disk,
        diskScope: alerts.diskScope,
      },
      background: {
        appBg: { ...bg.appBg },
        loginBg: { ...bg.loginBg },
        appBgImageVersion: bg.appBgImageVersion,
        loginBgImageVersion: bg.loginBgImageVersion,
      },
      siteTraffic: {
        selectedSiteId: siteTraffic.selectedSiteId,
      },
    }
  }

  function scheduleRemoteSave() {
    if (_loading) return
    if (_saveTimer) clearTimeout(_saveTimer)
    _saveTimer = setTimeout(async () => {
      try { await userPrefsApi.save(collect()) } catch { /* silent */ }
    }, 1500)
  }

  async function load() {
    _loading = true
    try {
      const { data } = await userPrefsApi.get()
      if (!data?.prefs || Object.keys(data.prefs).length === 0) return
      const p = data.prefs as Record<string, unknown>

      theme.loadFromDb({
        theme: p.theme,
        styleSettings: p.styleSettings,
      })
      if (p.displayPrefs) display.loadFromDb(p.displayPrefs as Record<string, string>)
      if (p.alerts) alerts.loadFromDb(p.alerts as Record<string, number | string>)
      if (p.background) bg.loadFromDb(p.background as Parameters<typeof bg.loadFromDb>[0])
      if (p.siteTraffic) siteTraffic.loadFromDb(p.siteTraffic as Parameters<typeof siteTraffic.loadFromDb>[0])
    } catch { /* silent — localStorage values stay */ } finally {
      _loading = false
    }
  }

  function startWatching() {
    watch(
      [
        () => theme.theme,
        () => JSON.stringify(theme.styleSettings),
        () => display.ramUnit,
        () => display.networkUnit,
        () => display.storageUnit,
        () => alerts.thresholds.cpu,
        () => alerts.thresholds.ram,
        () => alerts.thresholds.disk,
        () => alerts.diskScope,
        () => JSON.stringify(bg.appBg),
        () => JSON.stringify(bg.loginBg),
        () => bg.appBgImageVersion,
        () => bg.loginBgImageVersion,
        () => siteTraffic.selectedSiteId,
      ],
      scheduleRemoteSave,
    )
  }

  return { load, startWatching }
}
