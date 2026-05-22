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

export interface SystemVersionResponse {
  configured: boolean
  repo_url: string
  current_version: string | null
  current_commit: string | null
  current_source_type: string | null
  installed_at: string | null
  latest_version: string | null
  latest_commit: string | null
  latest_source_type: string | null
  checked_at: string | null
  update_available: boolean
  update_in_progress: boolean
  status: string
  error: string | null
  release_url: string | null
  notes_url: string | null
  deployment_type: 'docker' | 'self-hosted' | null
  docker_pull_cmd: string | null
}

export const systemApi = {
  version: () => api.get<SystemVersionResponse>('/system/version'),
  checkUpdates: () => api.post<{ success: boolean; message: string }>('/system/check-updates'),
  installUpdate: () => api.post<{ success: boolean; message: string }>('/system/install-update'),
}

export interface DiskInfo {
  device: string
  mountpoint: string
  fstype: string
  opts: string
  total_gb: number
  used_gb: number
  free_gb: number
  usage_percent: number
  read_mb_s: number
  write_mb_s: number
  is_removable: boolean
  is_virtual: boolean
  can_unmount: boolean
  bus_type: string
}

export interface AppInfo {
  port: number
  protocol: string
  pid: number | null
  process_name: string
  user: string
  cmdline: string
  auto_label: string
  custom_label: string | null
}

export interface ApiActionResponse {
  success: boolean
  output: string
}

export const disksApi = {
  list: () => api.get<DiskInfo[]>('/disks'),
  unmount: (mountpoint: string) => api.post<ApiActionResponse>('/disks/unmount', { mountpoint }),
  check: (mountpoint: string) => api.post<ApiActionResponse>('/disks/check', { mountpoint }),
}

export const appsApi = {
  list: () => api.get<AppInfo[]>('/apps'),
  setLabel: (port: number, label: string) =>
    api.put<ApiActionResponse>(`/apps/${port}/label`, { label }),
  deleteLabel: (port: number) =>
    api.delete<ApiActionResponse>(`/apps/${port}/label`),
  kill: (port: number) =>
    api.post<ApiActionResponse>(`/apps/${port}/kill`),
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
