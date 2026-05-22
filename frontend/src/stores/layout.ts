import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface WidgetPos { col: number; row: number; w: number; h: number }

export type WidgetId =
  | 'cpu' | 'ram' | 'gpu' | 'system'
  | 'disk' | 'network' | 'cpuTemp' | 'bandwidth'
  | 'history' | 'processes'

const STORAGE_KEY = 'cp_dashboard_layout'

export const DEFAULT_LAYOUT: Record<WidgetId, WidgetPos> = {
  cpu:       { col: 0, row: 0,  w: 6,  h: 9  },
  ram:       { col: 6, row: 0,  w: 6,  h: 9  },
  gpu:       { col: 0, row: 10, w: 6,  h: 9  },
  system:    { col: 6, row: 10, w: 6,  h: 9  },
  disk:      { col: 0, row: 20, w: 12, h: 5  },
  network:   { col: 0, row: 26, w: 12, h: 6  },
  cpuTemp:   { col: 0, row: 33, w: 6,  h: 6  },
  bandwidth: { col: 6, row: 33, w: 6,  h: 6  },
  history:   { col: 0, row: 40, w: 12, h: 6  },
  processes: { col: 0, row: 47, w: 12, h: 11 },
}

export const useLayoutStore = defineStore('layout', () => {
  const stored: Partial<Record<WidgetId, WidgetPos>> = (() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') }
    catch { return {} }
  })()

  const layout = ref<Record<WidgetId, WidgetPos>>(
    Object.fromEntries(
      (Object.keys(DEFAULT_LAYOUT) as WidgetId[]).map(id => [
        id,
        stored[id] ?? DEFAULT_LAYOUT[id],
      ]),
    ) as Record<WidgetId, WidgetPos>,
  )

  function update(id: WidgetId, pos: Partial<WidgetPos>) {
    layout.value[id] = { ...layout.value[id], ...pos }
  }

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout.value))
  }

  function reset() {
    layout.value = { ...DEFAULT_LAYOUT }
    save()
  }

  return { layout, update, save, reset }
})
