import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dashboardApi } from '@/api'

export interface WidgetPos { col: number; row: number; w: number; h: number }

export type WidgetId =
  | 'cpu' | 'ram' | 'gpu' | 'system'
  | 'disk' | 'network' | 'cpuTemp' | 'bandwidth'
  | 'history' | 'processes' | 'bookmarks' | 'siteTraffic'

const STORAGE_KEY = 'cp_dashboard_layout'
const HIDDEN_STORAGE_KEY = 'cp_dashboard_hidden'

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

function loadHidden(): Set<WidgetId> {
  try {
    const raw = JSON.parse(localStorage.getItem(HIDDEN_STORAGE_KEY) || '[]')
    const known = new Set(Object.keys(DEFAULT_LAYOUT))
    return new Set(Array.isArray(raw) ? raw.filter((id) => known.has(id)) : [])
  } catch {
    return new Set()
  }
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
  const hidden = ref<Set<WidgetId>>(loadHidden())

  async function loadRemote() {
    try {
      const { data } = await dashboardApi.getLayout()
      if (data?.layout) {
        const raw = data.layout as Record<string, unknown>
        layout.value = mergeWithDefaults(raw as Partial<Record<WidgetId, WidgetPos>>)
        localStorage.setItem(STORAGE_KEY, JSON.stringify(layout.value))

        const known = new Set(Object.keys(DEFAULT_LAYOUT))
        const hiddenIds = Array.isArray(raw.hiddenWidgets)
          ? (raw.hiddenWidgets as string[]).filter((id) => known.has(id))
          : []
        hidden.value = new Set(hiddenIds as WidgetId[])
        localStorage.setItem(HIDDEN_STORAGE_KEY, JSON.stringify(hiddenIds))
      }
    } catch { /* keep localStorage fallback */ }
  }

  function update(id: WidgetId, pos: Partial<WidgetPos>) {
    layout.value[id] = { ...layout.value[id], ...pos }
  }

  function toggleHidden(id: WidgetId) {
    const next = new Set(hidden.value)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    hidden.value = next
    save()
  }

  async function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout.value))
    const hiddenIds = Array.from(hidden.value)
    localStorage.setItem(HIDDEN_STORAGE_KEY, JSON.stringify(hiddenIds))
    try {
      await dashboardApi.saveLayout({ ...layout.value, hiddenWidgets: hiddenIds } as Record<string, object>)
    } catch { /* local save succeeded */ }
  }

  function reset() {
    layout.value = { ...DEFAULT_LAYOUT }
    hidden.value = new Set()
    save()
  }

  return { layout, hidden, loadRemote, update, save, reset, toggleHidden }
})
