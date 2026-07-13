import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dashboardApi } from '@/api'

export interface WidgetPos { col: number; row: number; w: number; h: number }

export type WidgetId =
  | 'cpu' | 'ram' | 'gpu' | 'system'
  | 'disk' | 'network' | 'cpuTemp' | 'bandwidth'
  | 'history' | 'processes' | 'bookmarks' | 'siteTraffic'

const STORAGE_KEY = 'cp_dashboard_layout'

export const DEFAULT_LAYOUT: Record<WidgetId, WidgetPos> = {
  bookmarks:    { col: 0, row: 0,  w: 12, h: 5  },
  cpu:          { col: 0, row: 5,  w: 6,  h: 7  },
  ram:          { col: 6, row: 5,  w: 6,  h: 7  },
  gpu:          { col: 0, row: 12, w: 6,  h: 7  },
  system:       { col: 6, row: 12, w: 6,  h: 7  },
  disk:         { col: 0, row: 19, w: 12, h: 5  },
  network:      { col: 0, row: 24, w: 12, h: 6  },
  siteTraffic:  { col: 0, row: 30, w: 12, h: 6  },
  cpuTemp:      { col: 0, row: 36, w: 6,  h: 6  },
  bandwidth:    { col: 6, row: 36, w: 6,  h: 6  },
  history:      { col: 0, row: 42, w: 12, h: 6  },
  processes:    { col: 0, row: 48, w: 12, h: 11 },
}

function mergeWithDefaults(stored: Partial<Record<WidgetId, WidgetPos>>): Record<WidgetId, WidgetPos> {
  return Object.fromEntries(
    (Object.keys(DEFAULT_LAYOUT) as WidgetId[]).map(id => [
      id,
      stored[id] ?? DEFAULT_LAYOUT[id],
    ]),
  ) as Record<WidgetId, WidgetPos>
}

export const useLayoutStore = defineStore('layout', () => {
  const layout = ref<Record<WidgetId, WidgetPos>>(
    mergeWithDefaults((() => {
      try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') }
      catch { return {} }
    })()),
  )

  async function loadRemote() {
    try {
      const { data } = await dashboardApi.getLayout()
      if (data?.layout) {
        layout.value = mergeWithDefaults(data.layout as Partial<Record<WidgetId, WidgetPos>>)
        localStorage.setItem(STORAGE_KEY, JSON.stringify(layout.value))
      }
    } catch { /* keep localStorage fallback */ }
  }

  function update(id: WidgetId, pos: Partial<WidgetPos>) {
    layout.value[id] = { ...layout.value[id], ...pos }
  }

  async function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout.value))
    try {
      await dashboardApi.saveLayout(layout.value as Record<string, object>)
    } catch { /* local save succeeded */ }
  }

  function reset() {
    layout.value = { ...DEFAULT_LAYOUT }
    save()
  }

  return { layout, loadRemote, update, save, reset }
})
