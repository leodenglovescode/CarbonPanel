import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import type {
  SiteCreate,
  SiteUpdate,
  SiteResponse,
  SiteActionResponse,
  ConfigReadResponse,
  SystemServiceResponse,
  SiteAction,
} from '@/types/sites'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
})

api.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
    }
    return Promise.reject(err)
  },
)

export default api

export interface LoginResponse {
  access_token?: string
  token_type?: string
  totp_required?: boolean
  session_token?: string
}

export interface UserInfo {
  id: string
  username: string
  totp_enabled: boolean
}

export interface TOTPSetupResponse {
  secret: string
  otpauth_uri: string
  qr_png_b64: string
}

export const authApi = {
  login: (username: string, password: string) =>
    api.post<LoginResponse>('/auth/login', { username, password }),
  loginTotp: (session_token: string, totp_code: string) =>
    api.post<{ access_token: string }>('/auth/login/totp', { session_token, totp_code }),
  me: () => api.get<UserInfo>('/auth/me'),
  logout: () => api.post('/auth/logout'),
}

export const settingsApi = {
  setup2fa: () => api.get<TOTPSetupResponse>('/settings/2fa/setup'),
  enable2fa: (totp_code: string) => api.post('/settings/2fa/enable', { totp_code }),
  disable2fa: (totp_code: string) => api.post('/settings/2fa/disable', { totp_code }),
  changeProfile: (current_password: string, new_username?: string, new_password?: string) =>
    api.put('/settings/profile', { current_password, new_username, new_password }),
}

export const sitesApi = {
  list: () => api.get<SiteResponse[]>('/sites'),
  get: (id: string) => api.get<SiteResponse>(`/sites/${id}`),
  create: (data: SiteCreate) => api.post<SiteResponse>('/sites', data),
  update: (id: string, data: SiteUpdate) => api.put<SiteResponse>(`/sites/${id}`, data),
  delete: (id: string) => api.delete(`/sites/${id}`),
  action: (id: string, action: SiteAction) =>
    api.post<SiteActionResponse>(`/sites/${id}/action`, { action }),
  getConfig: (id: string) => api.get<ConfigReadResponse>(`/sites/${id}/config`),
  saveConfig: (id: string, content: string) =>
    api.put(`/sites/${id}/config`, { content }),
  listSystemServices: (includeAll = false, starredOnly = false) =>
    api.get<SystemServiceResponse[]>('/sites/system-services', {
      params: {
        include_all: includeAll,
        starred_only: starredOnly,
      },
    }),
  systemServiceAction: (serviceName: string, action: SiteAction) =>
    api.post<SiteActionResponse>(
      `/sites/system-services/${encodeURIComponent(serviceName)}/action`,
      { action },
    ),
  setSystemServiceAutostart: (serviceName: string, enabled: boolean) =>
    api.post<SiteActionResponse>(
      `/sites/system-services/${encodeURIComponent(serviceName)}/autostart`,
      { enabled },
    ),
  setSystemServiceStar: (serviceName: string, starred: boolean) =>
    api.post<SiteActionResponse>(
      `/sites/system-services/${encodeURIComponent(serviceName)}/star`,
      { starred },
    ),
  reorderStarredSystemServices: (serviceNames: string[]) =>
    api.post<SiteActionResponse>('/sites/system-services/starred/reorder', {
      service_names: serviceNames,
    }),
}
