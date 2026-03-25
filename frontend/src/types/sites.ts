export type SiteType = 'nginx' | 'python' | 'wordpress' | 'nodejs'
export type ServiceManager = 'systemd' | 'pm2'
export type SiteAction = 'start' | 'stop' | 'restart'

export interface SiteStatus {
  status: string   // active | inactive | failed | unknown
  uptime: string | null
  pid: number | null
}

export interface SiteResponse {
  id: string
  name: string
  type: SiteType
  service_name: string
  service_manager: ServiceManager
  config_file_path: string | null
  log_paths: string[]
  description: string | null
  created_at: string
  updated_at: string
  status: SiteStatus | null
}

export interface SiteCreate {
  name: string
  type: SiteType
  service_name: string
  service_manager: ServiceManager
  config_file_path?: string
  log_paths?: string[]
  description?: string
}

export interface SiteUpdate extends Partial<SiteCreate> {}

export interface SiteActionResponse {
  success: boolean
  output: string
}

export interface ConfigReadResponse {
  content: string
  path: string
}
