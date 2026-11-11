<template>
  <div class="files-page">
    <header class="page-heading">
      <div><h1>Files <span class="read-only">Read only</span></h1><p>Browse folders, preview files, and download originals.</p></div>
    </header>
    <section class="browser" aria-label="File browser">
      <aside class="places" aria-label="Locations">
        <h2>Locations</h2>
        <button :class="{ active: directory === '/' }" @click="navigate('/')"><FileIcon name="directory" />Server root</button>
        <button v-for="place in places" :key="place" :class="{ active: directory === place }" :title="place" @click="navigate(place)"><FileIcon name="directory" /><span>{{ place }}</span></button>
        <p>Folders and files available to the CarbonPanel service account.</p>
      </aside>
      <div class="browser-main">
        <div class="location-bar">
          <button class="icon-button history-button" :disabled="!canBack" title="Back" aria-label="Back to previous folder" @click="router.back()">←</button>
          <button class="icon-button history-button" :disabled="!canForward" title="Forward" aria-label="Forward to next folder" @click="router.forward()">→</button>
          <button class="icon-button" :disabled="!parent || loading" title="Parent folder" aria-label="Parent folder" @click="parent && navigate(parent)"><FileIcon name="up" /></button>
          <nav class="breadcrumbs" aria-label="Folder path">
            <button :aria-current="currentPath === '/' ? 'location' : undefined" @click="navigate('/')">Server</button>
            <template v-for="(crumb, index) in breadcrumbs" :key="crumb.path"><span aria-hidden="true">/</span><button :aria-current="index === breadcrumbs.length - 1 ? 'location' : undefined" :title="crumb.path" @click="navigate(crumb.path)">{{ crumb.name }}</button></template>
          </nav>
          <button class="icon-button" :disabled="loading" title="Refresh folder" aria-label="Refresh folder" @click="load"><FileIcon name="refresh" /></button>
        </div>
        <form class="path-editor" @submit.prevent="navigate(pathInput)">
          <label for="folder-path">Path</label>
          <input id="folder-path" v-model="pathInput" aria-label="Current folder path" :aria-invalid="!!error" :aria-describedby="error ? 'folder-path-error' : undefined" placeholder="/srv/storage" spellcheck="false" autocomplete="off" autocapitalize="off" required @keydown.esc="pathInput = currentPath" />
          <button class="primary" :disabled="loading">{{ loading ? 'Opening…' : 'Go' }}</button>
        </form>
        <p v-if="error" id="folder-path-error" class="path-error" role="alert">{{ error }}</p>
        <div class="toolbar">
          <label class="search-field"><FileIcon name="search" /><input v-model="filter" maxlength="200" aria-label="Search this folder" placeholder="Search this folder…" /><button v-if="filter" class="icon-button" aria-label="Clear search" @click="filter = ''"><FileIcon name="close" /></button></label>
          <div class="view-options">
            <label class="sort"><span class="sr-only">Sort files</span><select v-model="sort"><option value="name">Name A–Z</option><option value="modified">Newest first</option><option value="size">Largest first</option><option value="kind">File type</option></select></label>
            <button class="hidden-toggle" :aria-pressed="showHidden" @click="showHidden = !showHidden">Hidden files</button>
            <div class="view-switch" role="group" aria-label="File view">
              <button :aria-pressed="view === 'list'" title="List view" aria-label="List view" @click="view = 'list'"><FileIcon name="list" /></button>
              <button :aria-pressed="view === 'grid'" title="Grid view" aria-label="Grid view" @click="view = 'grid'"><FileIcon name="grid" /></button>
            </div>
          </div>
        </div>
        <div class="folder-status" role="status" aria-live="polite"><span>{{ loading ? 'Loading folder…' : error ? 'Folder unavailable' : `${listing?.total ?? 0} ${search ? 'matching items' : 'items'}` }}</span><span v-if="!loading && !error">Folders first</span></div>
        <div class="file-area" :aria-busy="loading">
          <div v-if="error" class="empty-state" role="alert"><FileIcon name="directory" /><h2>Couldn’t open this folder</h2><p>{{ error }}</p><button @click="load">Try again</button></div>
          <div v-else-if="!loading && !listing?.entries.length" class="empty-state"><FileIcon :name="search ? 'search' : 'directory'" /><h2>{{ search ? 'No matching files' : 'This folder is empty' }}</h2><p>{{ search ? 'Try another name. Search covers this folder, not its subfolders.' : showHidden ? 'There are no files or folders here.' : 'Hidden files are off. You can show them from the toolbar.' }}</p><button v-if="filter" @click="filter = ''">Clear search</button></div>
          <template v-else-if="listing">
            <div v-if="view === 'list'" class="column-labels"><span>Name</span><span>Size</span><span>Modified</span><span class="sr-only">Actions</span></div>
            <div :class="view === 'grid' ? 'file-grid' : 'file-list'">
              <article v-for="entry in listing.entries" :key="entry.path" class="file-item" :class="[`kind-${entry.kind}`, { folder: entry.directory, tile: view === 'grid' }]">
                <button class="file-open" :title="entry.directory ? `Open ${entry.name}` : `Preview ${entry.name}`" :aria-label="entry.directory ? `Open ${entry.name}` : `Preview ${entry.name}`" @click="entry.directory ? navigate(entry.path) : preview(entry)">
                  <span class="file-art" :class="{ 'thumbnail-loading': view === 'grid' && thumbnail(entry) && !loadedImages.has(entry.path) && !failedImages.has(entry.path) }"><FileIcon :name="entry.directory ? 'directory' : entry.kind" /><img v-if="view === 'grid' && thumbnail(entry) && !failedImages.has(entry.path)" :src="filesApi.contentUrl(entry.path)" alt="" loading="lazy" decoding="async" :class="{ ready: loadedImages.has(entry.path) }" @load="loadedImages.add(entry.path)" @error="failedImages.add(entry.path)" /></span>
                  <span class="file-label"><span class="file-name">{{ entry.name }}</span><small>{{ entry.directory ? 'Folder' : label(entry) }}<span v-if="entry.symlink"> · Link</span></small></span>
                </button>
                <span class="file-size">{{ entry.directory ? '—' : size(entry.size) }}</span>
                <time class="modified" :title="date(entry.modified, true)">{{ date(entry.modified) }}</time>
                <button v-if="!entry.directory" class="download-button" :disabled="!!downloadBusy" :aria-label="`Download ${entry.name}`" @click="download(entry)"><FileIcon name="download" /><span>{{ downloadBusy === entry.path ? 'Preparing…' : 'Download' }}</span></button><span v-else class="folder-arrow" aria-hidden="true">›</span>
              </article>
            </div>
          </template>
        </div>
        <footer class="browser-footer"><span>{{ listing && !loading && !error ? `${listing.total ? listing.offset + 1 : 0}–${listing.offset + listing.entries.length} of ${listing.total}` : 'Read-only access' }}</span><div v-if="listing && !loading && !error && (listing.offset > 0 || listing.has_more)" class="pagination"><button :disabled="listing.offset === 0" @click="offset = Math.max(0, offset - 200)">Previous</button><span>Page {{ Math.floor(offset / 200) + 1 }}</span><button :disabled="!listing.has_more" @click="offset += 200">Next</button></div><span v-else>Read only</span></footer>
      </div>
    </section>
    <p v-if="notice" class="notice" role="status">{{ notice }}<button aria-label="Dismiss notification" @click="notice = ''">×</button></p>
    <BaseModal :open="!!selected" :title="selected?.name || 'Preview'" max-width="1120px" @close="closePreview">
      <template v-if="selected">
        <div class="preview-actions"><span>{{ label(selected) }} · {{ size(selected.size) }}</span><div><button :disabled="selectedIndex <= 0" aria-label="Previous file" @click="stepPreview(-1)">← Previous</button><button :disabled="selectedIndex < 0 || selectedIndex >= previewFiles.length - 1" aria-label="Next file" @click="stepPreview(1)">Next →</button><button class="primary" :disabled="!!downloadBusy" @click="download(selected)"><FileIcon name="download" />{{ downloadBusy === selected.path ? 'Preparing…' : 'Download' }}</button></div></div>
        <p v-if="previewError" class="preview-error" role="alert">{{ previewError }}</p>
        <div class="preview-stage">
          <div v-if="previewLoading" class="preview-loader" role="status"><span class="spinner" />{{ buffering ? 'Buffering…' : 'Loading preview…' }}</div>
          <img v-if="selected.kind === 'image'" :key="selected.path" class="image-preview" :class="{ ready: !previewLoading }" :src="filesApi.contentUrl(selected.path)" :alt="selected.name" @load="previewLoading = false" @error="mediaError" />
          <video v-else-if="selected.kind === 'video'" :key="selected.path" :src="filesApi.contentUrl(selected.path)" controls playsinline preload="metadata" @loadedmetadata="previewLoading = false" @canplay="previewLoading = false" @waiting="buffering = true; previewLoading = true" @playing="previewLoading = false" @error="mediaError" />
          <audio v-else-if="selected.kind === 'audio'" :key="selected.path" :src="filesApi.contentUrl(selected.path)" controls preload="metadata" @loadedmetadata="previewLoading = false" @canplay="previewLoading = false" @waiting="buffering = true; previewLoading = true" @playing="previewLoading = false" @error="mediaError" />
          <iframe v-else-if="previewHtml" title="Read-only file preview" sandbox="" :srcdoc="previewHtml" @load="previewLoading = false" />
          <div v-else-if="!previewLoading && !previewError" class="empty-state"><FileIcon name="file" /><h2>Preview isn’t available</h2><p>Download this file to open it in a compatible app.</p></div>
        </div>
        <p class="preview-path">{{ selected.path }}</p>
      </template>
    </BaseModal>
  </div>
</template>
<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BaseModal from '@/components/ui/BaseModal.vue'
import FileIcon from '@/components/ui/FileIcon.vue'
import { filesApi, type FileEntry, type FileListing, type FileQuery } from '@/api/files'
import { useMetricsStore } from '@/stores/metrics'
const metrics = useMetricsStore()
const route = useRoute(), router = useRouter()
const initialPath = typeof route.query.path === 'string' ? route.query.path : '/'
const canBack = computed(() => String(window.history.state?.back || '').split('?')[0] === '/files')
const canForward = computed(() => String(window.history.state?.forward || '').split('?')[0] === '/files')
function stored(key: string, fallback: string) { try { return localStorage.getItem(key) || fallback } catch { return fallback } }
function savedView(): 'list' | 'grid' { try { return localStorage.getItem('cp_files_view') === 'grid' ? 'grid' : 'list' } catch { return 'list' } }
const view = ref(savedView())
watch(view, value => { try { localStorage.setItem('cp_files_view', value) } catch { /* Storage is optional. */ } })
const listing = ref<FileListing | null>(null), directory = ref(initialPath), offset = ref(0)
const filter = ref(''), search = ref(''), sort = ref<FileQuery['sort']>(['name', 'modified', 'size', 'kind'].includes(stored('cp_files_sort', 'name')) ? stored('cp_files_sort', 'name') as FileQuery['sort'] : 'name'), showHidden = ref(stored('cp_files_hidden', 'false') === 'true')
const loading = ref(false), error = ref(''), notice = ref(''), pathInput = ref(initialPath)
const failedImages = ref(new Set<string>()), loadedImages = ref(new Set<string>())
const selected = ref<FileEntry | null>(null), previewHtml = ref(''), previewError = ref(''), previewLoading = ref(false), buffering = ref(false), downloadBusy = ref('')
let directoryController: AbortController | undefined, previewController: AbortController | undefined, downloadController: AbortController | undefined, filterTimer: ReturnType<typeof setTimeout> | undefined
const currentPath = computed(() => loading.value || error.value ? directory.value : listing.value?.path || directory.value)
const parent = computed(() => currentPath.value === '/' ? null : currentPath.value.split('/').slice(0, -1).join('/') || '/')
const breadcrumbs = computed(() => { const parts = currentPath.value.split('/').filter(Boolean); return parts.map((name, i) => ({ name, path: '/' + parts.slice(0, i + 1).join('/') })) })
const places = computed(() => [...new Set((metrics.latest?.disks || []).map(d => d.mountpoint))].filter(p => p !== '/' && !/^\/(?:snap|var\/lib\/snapd\/snap|proc|sys|dev)(?:\/|$)/.test(p)))
const previewFiles = computed(() => listing.value?.entries.filter(e => !e.directory) || [])
const selectedIndex = computed(() => previewFiles.value.findIndex(e => e.path === selected.value?.path))
watch(filter, value => { clearTimeout(filterTimer); filterTimer = setTimeout(() => { offset.value = 0; search.value = value.trim() }, 250) })
watch([sort, showHidden], () => { offset.value = 0; try { localStorage.setItem('cp_files_sort', sort.value || 'name'); localStorage.setItem('cp_files_hidden', String(showHidden.value)) } catch { /* Storage is optional. */ } })
watch(() => route.query.path, value => {
  directory.value = typeof value === 'string' ? value : '/'
  pathInput.value = directory.value
  filter.value = ''; search.value = ''; offset.value = 0
})
watch([directory, offset, search, sort, showHidden], load, { immediate: true })
function detail(e: any) { if (e.response?.status === 404) return 'This path does not exist. Check the path and try again.'; if (typeof e.response?.data?.detail === 'string') return e.response.data.detail; if (e.response?.status === 403) return 'The CarbonPanel service account cannot read this path.'; return e.message || 'This path could not be read.' }
function navigate(path: string) { const target = path.trim(); if (!target) return; if (target !== directory.value) { void router.push({ name: 'files', query: { path: target } }); return } filter.value = ''; search.value = ''; offset.value = 0; void load() }
async function load() {
  directoryController?.abort(); const controller = new AbortController(); directoryController = controller; loading.value = true; error.value = ''
  try { const { data } = await filesApi.list(directory.value, offset.value, controller.signal, { search: search.value, sort: sort.value, descending: sort.value === 'modified' || sort.value === 'size', show_hidden: showHidden.value }); if (controller.signal.aborted) return; listing.value = data; pathInput.value = data.path; failedImages.value = new Set(); loadedImages.value = new Set() }
  catch (e) { if (!controller.signal.aborted) error.value = detail(e) }
  finally { if (!controller.signal.aborted) loading.value = false }
}
async function preview(entry: FileEntry) {
  closePreview(); selected.value = entry
  if (entry.kind === 'file') return
  previewLoading.value = true
  if (['image', 'video', 'audio'].includes(entry.kind)) return
  const controller = new AbortController(); previewController = controller
  try { const result = await filesApi.preview(entry.path, controller.signal); if (!controller.signal.aborted) previewHtml.value = result.data }
  catch (e) { if (!controller.signal.aborted) { previewError.value = detail(e); previewLoading.value = false } }
}
function stepPreview(delta: number) { const file = previewFiles.value[selectedIndex.value + delta]; if (file) void preview(file) }
function closePreview() { previewController?.abort(); selected.value = null; previewHtml.value = ''; previewError.value = ''; previewLoading.value = false; buffering.value = false }
function mediaError() { previewLoading.value = false; previewError.value = 'This format could not be displayed. Download the original to open it in another app.' }
async function download(entry: FileEntry) {
  if (downloadBusy.value) return
  downloadController?.abort(); const controller = new AbortController(); downloadController = controller; downloadBusy.value = entry.path
  try {
    await filesApi.checkDownload(entry.path, controller.signal)
    if (controller.signal.aborted) return
    const link = document.createElement('a'); link.href = filesApi.contentUrl(entry.path, true); link.download = entry.name; document.body.append(link); link.click(); link.remove()
    notice.value = `Download handed to your browser: ${entry.name}. Check your browser’s downloads for progress.`
  } catch (e) { if (!controller.signal.aborted) notice.value = `Download could not start: ${detail(e)}` }
  finally { if (!controller.signal.aborted) downloadBusy.value = '' }
}
function thumbnail(entry: FileEntry) { return entry.kind === 'image' && (entry.size || 0) <= 8 * 1024 * 1024 }
function label(entry: FileEntry) { return ({ image: 'Image', video: 'Video', audio: 'Audio', markdown: 'Markdown', text: 'Text / code', directory: 'Folder' } as Record<string, string>)[entry.kind] || 'File' }
function date(value: number, full = false) { return value ? full ? new Date(value * 1000).toLocaleString() : new Date(value * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : '—' }
function size(value: number | null) { if (value == null) return '—'; const i = value > 0 ? Math.min(4, Math.floor(Math.log(value) / Math.log(1024))) : 0; return `${(value / 1024 ** i).toLocaleString(undefined, { maximumFractionDigits: 1 })} ${['B', 'KiB', 'MiB', 'GiB', 'TiB'][i]}` }
onUnmounted(() => { clearTimeout(filterTimer); directoryController?.abort(); previewController?.abort(); downloadController?.abort() })
</script>
<style scoped>
.files-page { padding: 28px; max-width: 1600px; margin: auto; width: 100%; }
.page-heading { margin-bottom: 22px; } h1 { display: flex; align-items: center; gap: 14px; font-size: 22px; } .page-heading p { margin-top: 8px; font-size: 12px; color: var(--fg-muted); }
.read-only { color: var(--accent); background: var(--accent-dim); border: 1px solid var(--accent-border); font-size: 10px; font-weight: 400; padding: 5px 8px; border-radius: var(--radius-sm); }
button, input, select { font: 12px var(--font); color: var(--fg); } button { cursor: pointer; border: 1px solid var(--border); border-radius: var(--radius-sm); background: transparent; padding: 9px 12px; transition: background var(--transition), color var(--transition), border-color var(--transition); } button:hover:not(:disabled) { background: var(--accent-dim); color: var(--accent); } button:disabled { opacity: .4; cursor: default; } button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
svg { width: 18px; height: 18px; flex-shrink: 0; } input, select { background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 10px 12px; min-width: 0; } .primary { background: var(--accent-dim); color: var(--accent); border-color: var(--accent-border); }
.browser { display: grid; grid-template-columns: 190px minmax(0, 1fr); background: var(--surface-panel); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow-card); overflow: hidden; min-height: 590px; }
.places { padding: 24px 12px; border-right: 1px solid var(--border); background: color-mix(in srgb, var(--bg) 25%, transparent); } .places h2 { font-size: 10px; text-transform: uppercase; letter-spacing: .12em; color: var(--fg-dim); margin: 0 12px 14px; } .places button { display: flex; align-items: center; gap: 10px; width: 100%; text-align: left; border-color: transparent; margin-bottom: 6px; } .places button span { overflow: hidden; text-overflow: ellipsis; } .places .active { background: var(--accent-dim); color: var(--accent); } .places p { font-size: 10px; line-height: 1.8; margin: 32px 12px; color: var(--fg-dim); }
.browser-main { min-width: 0; display: flex; flex-direction: column; } .location-bar { display: flex; align-items: center; gap: 8px; padding: 14px 18px; border-bottom: 1px solid var(--border); } .icon-button { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; padding: 8px; flex-shrink: 0; } .breadcrumbs { flex: 1; min-width: 0; overflow-x: auto; display: flex; align-items: center; gap: 3px; white-space: nowrap; } .breadcrumbs button { border: 0; padding: 10px 8px; color: var(--fg-muted); } .breadcrumbs [aria-current] { color: var(--fg); font-weight: 600; } .breadcrumbs > span { color: var(--fg-dim); }
.path-editor { display: flex; align-items: center; gap: 12px; padding: 12px 18px; border-bottom: 1px solid var(--border); font-size: 11px; } .path-editor input { flex: 1; min-width: 0; } .path-error { padding: 10px 18px; font-size: 11px; line-height: 1.6; color: var(--danger); overflow-wrap: anywhere; }
.toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; padding: 18px; } .search-field { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 180px; background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--radius); padding: 0 10px; color: var(--fg-muted); } .search-field input { width: 100%; background: transparent; border: 0; padding: 12px 0; } .search-field .icon-button { width: 28px; height: 28px; padding: 5px; border: 0; } .view-options { display: flex; gap: 10px; align-items: center; } .sort select { height: 40px; } .hidden-toggle { font-size: 10px; height: 40px; } [aria-pressed="true"] { background: var(--accent-dim); color: var(--accent); border-color: var(--accent-border); } .view-switch { display: flex; border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 3px; } .view-switch button { display: flex; padding: 7px; border: 0; }
.folder-status { padding: 0 20px 14px; display: flex; justify-content: space-between; color: var(--fg-dim); font-size: 10px; } .file-area { flex: 1; min-height: 350px; } .column-labels, .file-item { display: grid; grid-template-columns: minmax(0, 1fr) 80px 130px 112px; align-items: center; gap: 16px; padding: 0 20px; } .column-labels { border-block: 1px solid var(--border); background: color-mix(in srgb, var(--bg) 25%, transparent); color: var(--fg-dim); font-size: 10px; padding-block: 12px; } .column-labels > :nth-child(2), .column-labels > :nth-child(3) { text-align: right; } .file-item { border-bottom: 1px solid var(--border-row); } .file-item:hover { background: color-mix(in srgb, var(--accent) 4%, transparent); } .file-open { border: 0; border-radius: 0; display: flex; align-items: center; gap: 14px; text-align: left; min-width: 0; padding: 15px 0; } .file-open:hover:not(:disabled) { background: transparent; } .file-art { display: flex; align-items: center; justify-content: center; position: relative; width: 36px; height: 40px; flex-shrink: 0; color: var(--fg-muted); } .file-art svg { width: 28px; height: 28px; } .folder .file-art { color: var(--accent); } .kind-image .file-art, .kind-video .file-art { color: var(--info); } .file-label { min-width: 0; } .file-name { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; line-height: 1.6; } .file-label small { display: block; font-size: 10px; color: var(--fg-dim); margin-top: 3px; } .file-size, .modified { font-size: 10px; color: var(--fg-muted); text-align: right; } .download-button { display: flex; align-items: center; justify-content: center; gap: 7px; border-color: transparent; font-size: 10px; } .download-button svg { width: 15px; height: 15px; } .folder-arrow { text-align: right; color: var(--fg-dim); padding-right: 10px; }
.file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(155px, 1fr)); gap: 12px; padding: 8px 18px 20px; } .file-item.tile { gap: 0; display: flex; flex-direction: column; position: relative; border: 1px solid var(--border); border-radius: var(--radius); padding: 0; overflow: hidden; } .tile .file-open { width: 100%; display: flex; flex-direction: column; gap: 10px; padding: 14px 12px 8px; } .tile .file-art { width: 100%; height: 90px; border-radius: var(--radius-sm); overflow: hidden; background: color-mix(in srgb, var(--bg) 30%, transparent); } .tile .file-art svg { width: 44px; height: 44px; } .file-art img { position: absolute; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity var(--transition); } .file-art img.ready { opacity: 1; } .thumbnail-loading { animation: pulse 1.3s ease-in-out infinite; } .tile .file-label { width: 100%; text-align: center; } .tile .file-name { white-space: normal; overflow-wrap: anywhere; height: 38px; line-height: 19px; overflow: hidden; } .tile .file-label small { margin-top: 5px; } .tile .modified, .tile .folder-arrow { display: none; } .tile .file-size { margin: 3px 0 10px; } .tile .download-button { width: 100%; margin-top: auto; border-top: 1px solid var(--border); border-radius: 0; padding: 10px; } .tile.folder { padding-bottom: 14px; } .tile.folder .file-size { display: none; }
.browser-footer { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 14px 20px; border-top: 1px solid var(--border); color: var(--fg-dim); font-size: 10px; } .pagination { display: flex; align-items: center; gap: 12px; } .pagination button { font-size: 10px; } .empty-state { min-height: 320px; padding: 50px 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; text-align: center; } .empty-state > svg { width: 42px; height: 42px; color: var(--fg-dim); } .empty-state h2 { font-size: 14px; } .empty-state p { max-width: 400px; font-size: 11px; line-height: 1.8; color: var(--fg-muted); }
.notice { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-top: 14px; padding: 14px; background: var(--surface-panel); border: 1px solid var(--border); border-radius: var(--radius); font-size: 11px; line-height: 1.7; } .notice button { border: 0; } .preview-actions { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; color: var(--fg-muted); font-size: 11px; margin-bottom: 16px; } .preview-actions > div { display: flex; gap: 8px; } .preview-actions button { display: inline-flex; align-items: center; gap: 8px; font-size: 11px; } .preview-stage { min-height: 300px; position: relative; display: flex; justify-content: center; align-items: center; } .preview-stage img { display: block; max-width: 100%; max-height: 65dvh; object-fit: contain; } .image-preview { opacity: 0; transition: opacity var(--transition); } .image-preview.ready { opacity: 1; } .preview-stage video { width: 100%; max-height: 65dvh; } .preview-stage audio { width: 100%; } .preview-stage iframe { width: 100%; height: 62dvh; border: 1px solid var(--border); border-radius: var(--radius); } .preview-loader { position: absolute; z-index: 1; pointer-events: none; display: flex; align-items: center; gap: 12px; padding: 14px 18px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg-card); font-size: 12px; } .spinner { width: 18px; height: 18px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin .7s linear infinite; } .preview-error { font-size: 12px; line-height: 1.8; color: var(--danger); margin-bottom: 12px; } .preview-path { font-size: 10px; color: var(--fg-dim); margin-top: 14px; overflow-wrap: anywhere; } .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
@keyframes pulse { 50% { opacity: .35; } } @keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinner, .thumbnail-loading { animation: none; } }
@media(max-width: 1050px) { .browser { grid-template-columns: 150px minmax(0, 1fr); } .column-labels, .file-item { grid-template-columns: minmax(0, 1fr) 75px 100px; gap: 10px; } .column-labels > :nth-child(3), .modified { display: none; } }
@media(max-width: 700px) { .icon-button { width: 44px; height: 44px; } .breadcrumbs button { min-height: 44px; } .view-switch button { min-width: 40px; min-height: 40px; } .history-button { display: none; } .files-page { padding: 16px; } .browser { display: block; border-radius: var(--radius); } .places { display: none; } .toolbar { padding: 12px; gap: 10px; } .search-field { flex-basis: 100%; } .view-options { width: 100%; justify-content: space-between; } .hidden-toggle { display: block; } .location-bar { padding: 10px; gap: 4px; } .path-editor { padding: 12px; flex-wrap: wrap; } .path-editor label { width: 100%; } .column-labels, .file-item { grid-template-columns: minmax(0, 1fr) 64px 44px; padding-inline: 12px; gap: 8px; } .download-button { padding: 10px; min-height: 44px; } .download-button > span { display: none; } .file-open { gap: 8px; } .file-name { font-size: 11px; } .file-art { width: 28px; } .file-art svg { width: 24px; height: 24px; } .file-grid { grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); padding-inline: 12px; } .tile .download-button > span { display: inline; } .browser-footer { flex-wrap: wrap; padding: 12px; } .preview-actions > div { flex-wrap: wrap; } }
</style>
