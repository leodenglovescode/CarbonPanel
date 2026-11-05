import api from '@/api'

export type BackgroundTarget = 'app' | 'login' | 'android-app'
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
  sourceVersion: number
}
export const backgroundApi = {
  get: () => api.get<BackgroundSettings>('/settings/background-image/config'),
  save: (patch: { targets?: Partial<Record<BackgroundTarget, BgConfig>>; surfaceTransparency?: number }) => api.put<BackgroundSettings>('/settings/background-image/config', patch),
  apply: (file: Blob, targets: BackgroundTarget[]) => {
    const body = new FormData()
    body.append('file', file, 'background.jpg')
    return api.post<BackgroundSettings>(`/settings/background-image/apply?${targets.map(t => `targets=${t}`).join('&')}`, body)
  },
  applyCrops: (source: Blob, web: Blob, android: Blob | null, targets: BackgroundTarget[]) => {
    const body = new FormData()
    body.append('source', source, 'original.jpg')
    body.append('web', web, 'web.jpg')
    if (android) body.append('android', android, 'phone.jpg')
    return api.post<BackgroundSettings>(`/settings/background-image/apply-crops?${targets.map(t => `targets=${t}`).join('&')}`, body)
  },
  source: () => api.get<Blob>('/settings/background-image/source', { responseType: 'blob' }),
  copy: (source: BackgroundTarget, targets: BackgroundTarget[]) => api.post<BackgroundSettings>('/settings/background-image/copy', { source, targets }),
  remove: (target: BackgroundTarget) => api.delete(`/settings/background-image/${target}`),
}
