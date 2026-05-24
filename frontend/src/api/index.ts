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
  version: () => api.get<SystemVersionResponse>('/system/version', { timeout: 10_000 }),
  checkUpdates: () => api.post<{ success: boolean; message: string }>('/system/check-updates', null, { timeout: 10_000 }),
  installUpdate: () => api.post<{ success: boolean; message: string }>('/system/install-update'),
}

export interface SmartResult {
  model: string
  serial: string
  firmware: string
  health: string        // "PASSED" | "FAILED" | "UNKNOWN"
  temperature_c: number | null
  power_on_hours: number | null
  reallocated_sectors: number | null
  pending_sectors: number | null
  uncorrectable_errors: number | null
  last_checked: string
  error: string | null
}

export interface DiskInfo {
  device: string
  mountpoint: string
  extra_mounts: string[]
  physical_device: string
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
  smart: SmartResult | null
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
  refreshSmart: () => api.post<SmartResult[]>('/disks/smart/refresh'),
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

export interface ContainerInfo {
  id: string
  name: string
  image: string
  status: string
  state: string
  ports: string
  created: string
  cpu_percent: number
  mem_usage_mb: number
  mem_limit_mb: number
  mem_percent: number
}

export interface WebhookResponse {
  id: string
  label: string
  url: string
  enabled: boolean
  events: string[]
}

export interface WebhookCreate {
  label?: string
  url: string
  enabled?: boolean
  events?: string[]
}

export type HistoryPoint = import('@/types/metrics').HistoryPoint

export const dockerApi = {
  list: () => api.get<ContainerInfo[]>('/docker/containers'),
  start: (id: string) => api.post<ApiActionResponse>(`/docker/containers/${id}/start`),
  stop: (id: string) => api.post<ApiActionResponse>(`/docker/containers/${id}/stop`),
  restart: (id: string) => api.post<ApiActionResponse>(`/docker/containers/${id}/restart`),
}

export const processesApi = {
  kill: (pid: number, force = false) =>
    api.post<{ success: boolean; message: string }>(`/processes/${pid}/kill`, { force }),
}

export const webhooksApi = {
  list: () => api.get<WebhookResponse[]>('/webhooks'),
  create: (data: WebhookCreate) => api.post<WebhookResponse>('/webhooks', data),
  update: (id: string, data: Partial<WebhookCreate>) => api.put<WebhookResponse>(`/webhooks/${id}`, data),
  delete: (id: string) => api.delete(`/webhooks/${id}`),
  trigger: (event: string, metric: string, value: number, threshold: number) =>
    api.post('/webhooks/trigger', { event, metric, value, threshold }),
}

export const metricsApi = {
  history: () => api.get<HistoryPoint[]>('/metrics/history'),
}

export interface ProxyConfig {
  enabled: boolean
  type: 'http' | 'socks5'
  host: string
  port: number
}

export const proxyApi = {
  get: () => api.get<ProxyConfig>('/settings/proxy'),
  update: (config: ProxyConfig) => api.put<ProxyConfig>('/settings/proxy', config),
  test: () => api.post<{ success: boolean; message: string }>('/settings/proxy/test'),
}

export interface DeviceInfo {
  id: string
  name: string
  ip_address: string | null
  last_seen: string
  created_at: string
}

export const devicesApi = {
  list: () => api.get<DeviceInfo[]>('/devices'),
  revoke: (id: string) => api.delete(`/devices/${id}`),
}

export interface BookmarkInfo {
  id: string
  title: string
  url: string
  icon_url: string | null
  sort_order: number
}

export const bookmarksApi = {
  list: () => api.get<BookmarkInfo[]>('/bookmarks'),
  create: (data: Omit<BookmarkInfo, 'id'>) => api.post<BookmarkInfo>('/bookmarks', data),
  update: (id: string, data: Omit<BookmarkInfo, 'id'>) => api.put<BookmarkInfo>(`/bookmarks/${id}`, data),
  delete: (id: string) => api.delete(`/bookmarks/${id}`),
}

export const dashboardApi = {
  getLayout: () => api.get<{ layout: Record<string, object> } | null>('/dashboard/layout'),
  saveLayout: (layout: Record<string, object>) => api.put('/dashboard/layout', { layout }),
}

export interface PasskeyCredential {
  id: string
  device_name: string
}

export const passkeysApi = {
  registerBegin: () => api.post('/auth/passkey/register/begin'),
  registerComplete: (credential: object, device_name: string) =>
    api.post('/auth/passkey/register/complete', { credential, device_name }),
  list: () => api.get<PasskeyCredential[]>('/auth/passkey/credentials'),
  delete: (id: string) => api.delete(`/auth/passkey/credentials/${id}`),
  loginBegin: (username: string) =>
    api.post<Record<string, unknown>>('/auth/passkey/login/begin', { username }),
  loginComplete: (session_id: string, credential: object) =>
    api.post<{ access_token: string }>('/auth/passkey/login/complete', { session_id, credential }),
}

export const userPrefsApi = {
  get: () => api.get<{ prefs: Record<string, unknown> }>('/settings/preferences'),
  save: (prefs: Record<string, unknown>) => api.put('/settings/preferences', { prefs }),
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
