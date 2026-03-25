import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'

export interface UserInfo {
  id: string
  username: string
  totp_enabled: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('cp_token'))
  const user = ref<UserInfo | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  function setToken(t: string) {
    token.value = t
    localStorage.setItem('cp_token', t)
  }

  async function loadUser() {
    if (!token.value) return
    try {
      const res = await authApi.me()
      user.value = res.data
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('cp_token')
  }

  return { token, user, isAuthenticated, setToken, loadUser, logout }
})
