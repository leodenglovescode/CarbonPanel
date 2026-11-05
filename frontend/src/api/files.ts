import api from '@/api'
export interface FileEntry {
  name: string; path: string; directory: boolean; symlink: boolean
  size: number | null; modified: number; kind: string
}
export interface FileListing {
  path: string; parent: string | null; entries: FileEntry[]; total: number; offset: number; has_more: boolean
}
export const filesApi = {
  list: (path: string, offset = 0, signal?: AbortSignal) => api.get<FileListing>('/files', { params: { path, offset }, signal }),
  preview: (path: string, signal?: AbortSignal) => api.get<string>('/files/preview', { params: { path }, responseType: 'text', signal }),
  contentUrl: (path: string, download = false) => `/api/v1/files/content?${new URLSearchParams({ path, download: String(download) })}`,
}
