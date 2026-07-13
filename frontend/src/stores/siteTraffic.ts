import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'cp_site_traffic'

function loadSelected(): string | null {
  try { return localStorage.getItem(STORAGE_KEY) } catch { return null }
}

export const useSiteTrafficStore = defineStore('siteTraffic', () => {
  const selectedSiteId = ref<string | null>(loadSelected())

  function setSelectedSiteId(id: string | null) {
    selectedSiteId.value = id
    if (id) localStorage.setItem(STORAGE_KEY, id)
    else localStorage.removeItem(STORAGE_KEY)
  }

  function loadFromDb(data: { selectedSiteId?: string | null }) {
    if ('selectedSiteId' in data) {
      selectedSiteId.value = data.selectedSiteId ?? null
      if (data.selectedSiteId) localStorage.setItem(STORAGE_KEY, data.selectedSiteId)
      else localStorage.removeItem(STORAGE_KEY)
    }
  }

  return { selectedSiteId, setSelectedSiteId, loadFromDb }
})
