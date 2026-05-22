import { defineStore } from 'pinia'
import { ref } from 'vue'

export type RamUnit = 'gb' | 'mb'
export type NetworkUnit = 'mb_s' | 'mbps'
export type StorageUnit = 'gb' | 'auto_tb' | 'tb'

const STORAGE_KEY = 'cp_display_prefs'

export const useDisplayPrefsStore = defineStore('displayPrefs', () => {
  const stored = (() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') } catch { return {} }
  })()

  const ramUnit = ref<RamUnit>(stored.ramUnit ?? 'gb')
  const networkUnit = ref<NetworkUnit>(stored.networkUnit ?? 'mb_s')
  const storageUnit = ref<StorageUnit>(stored.storageUnit ?? 'gb')

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      ramUnit: ramUnit.value,
      networkUnit: networkUnit.value,
      storageUnit: storageUnit.value,
    }))
  }

  function setRamUnit(unit: RamUnit) { ramUnit.value = unit; save() }
  function setNetworkUnit(unit: NetworkUnit) { networkUnit.value = unit; save() }
  function setStorageUnit(unit: StorageUnit) { storageUnit.value = unit; save() }

  function fmtStorage(gb: number): string {
    if (storageUnit.value === 'tb') return (gb / 1024).toFixed(2) + ' TB'
    if (storageUnit.value === 'auto_tb' && gb >= 1024) return (gb / 1024).toFixed(2) + ' TB'
    return gb.toFixed(1) + ' GB'
  }

  return { ramUnit, networkUnit, storageUnit, setRamUnit, setNetworkUnit, setStorageUnit, fmtStorage }
})
