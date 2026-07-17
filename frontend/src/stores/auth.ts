import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'

export interface UserInfo {
  id: string
  username: string
  totp_enabled: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  // Whether we've asked the backend (via /auth/me) whether the session cookie
  // is valid yet — the router guard uses this to bootstrap auth state once
  // per page load instead of on every navigation.
  const authChecked = ref(false)

  const isAuthenticated = computed(() => !!user.value)

  async function loadUser() {
    try {
      const res = await authApi.me()
      user.value = res.data
    } catch {
      user.value = null
    } finally {
      authChecked.value = true
    }
  }

  function logout() {
    user.value = null
  }

  return { user, isAuthenticated, authChecked, loadUser, logout }
})
