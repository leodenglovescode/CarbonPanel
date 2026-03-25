import { defineStore } from 'pinia'
import { ref } from 'vue'
import { sitesApi } from '@/api'
import type { SiteResponse, SiteCreate, SiteUpdate } from '@/types/sites'

export const useSitesStore = defineStore('sites', () => {
  const sites = ref<SiteResponse[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchSites() {
    loading.value = true
    error.value = null
    try {
      const res = await sitesApi.list()
      sites.value = res.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to load sites'
    } finally {
      loading.value = false
    }
  }

  async function createSite(data: SiteCreate): Promise<SiteResponse | null> {
    try {
      const res = await sitesApi.create(data)
      await fetchSites()
      return res.data
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to create site'
      return null
    }
  }

  async function updateSite(id: string, data: SiteUpdate): Promise<boolean> {
    try {
      await sitesApi.update(id, data)
      await fetchSites()
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to update site'
      return false
    }
  }

  async function deleteSite(id: string): Promise<boolean> {
    try {
      await sitesApi.delete(id)
      sites.value = sites.value.filter(s => s.id !== id)
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Failed to delete site'
      return false
    }
  }

  async function runAction(id: string, action: string): Promise<{ success: boolean; output: string }> {
    try {
      const res = await sitesApi.action(id, action)
      // Refresh status after action
      const updated = await sitesApi.get(id)
      const idx = sites.value.findIndex(s => s.id === id)
      if (idx !== -1) sites.value[idx] = updated.data
      return res.data
    } catch (e: any) {
      return { success: false, output: e.response?.data?.detail || 'Action failed' }
    }
  }

  return { sites, loading, error, fetchSites, createSite, updateSite, deleteSite, runAction }
})
