import api from '@/api'

export type BackgroundTarget = 'app' | 'login' | 'android-app' | 'android-login'
export interface BgConfig {
  type: 'color' | 'gradient' | 'image'
  gradientAngle: number
  gradientStart: string
  gradientEnd: string
  blur: number
  brightness: number
  overlay: number
  version: number
}
export interface BackgroundSettings {
  targets: Record<BackgroundTarget, BgConfig>
  surfaceTransparency: number
  configured: boolean
}
export const backgroundApi = {
  get: () => api.get<BackgroundSettings>('/settings/background-image/config'),
  save: (patch: { targets?: Partial<Record<BackgroundTarget, BgConfig>>; surfaceTransparency?: number }) => api.put<BackgroundSettings>('/settings/background-image/config', patch),
  apply: (file: Blob, targets: BackgroundTarget[]) => {
    const body = new FormData()
    body.append('file', file, 'background.jpg')
    return api.post<BackgroundSettings>(`/settings/background-image/apply?${targets.map(t => `targets=${t}`).join('&')}`, body)
  },
  copy: (source: BackgroundTarget, targets: BackgroundTarget[]) => api.post<BackgroundSettings>('/settings/background-image/copy', { source, targets }),
  remove: (target: BackgroundTarget) => api.delete(`/settings/background-image/${target}`),
}
