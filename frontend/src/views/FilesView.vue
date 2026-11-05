<template>
  <div class="files-page">
    <header class="page-heading"><div><h1>Files</h1><p>Browse, preview &amp; download · read only</p></div><button :disabled="loading" @click="open(listing?.path || '/')">Refresh</button></header>
    <form class="path-bar" @submit.prevent="open(pathInput)"><button type="button" :disabled="!listing?.parent || loading" aria-label="Parent directory" @click="listing?.parent && open(listing.parent)">↑ Up</button><label for="file-path" class="sr-only">Directory path</label><input id="file-path" v-model="pathInput" :disabled="loading" placeholder="/srv" spellcheck="false" /><button :disabled="loading">Open</button></form>
    <p class="access-note">Access follows the CarbonPanel service account's permissions. Files are served over the panel’s HTTPS connection.</p>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
    <nav v-if="listing" class="breadcrumbs" aria-label="Directory breadcrumbs"><button @click="open('/')">/</button><button v-for="crumb in breadcrumbs" :key="crumb.path" @click="open(crumb.path)">{{ crumb.name }}</button></nav>
    <div class="files-card" :aria-busy="loading">
      <div class="list-heading"><span>{{ loading ? 'Reading directory…' : `${listing?.total ?? 0} items` }}</span><label>Filter <input v-model="filter" placeholder="Name on this page" /></label></div>
      <div v-if="!entries.length && !loading" class="empty">{{ filter ? 'No matching files on this page.' : 'This directory is empty.' }}</div>
      <div v-for="entry in entries" :key="entry.path" class="file-row">
        <span class="file-kind" aria-hidden="true">{{ entry.directory ? 'DIR' : entry.kind === 'image' ? 'IMG' : entry.kind === 'video' ? 'VID' : entry.kind === 'markdown' ? 'MD' : entry.kind === 'text' ? 'TXT' : entry.kind === 'audio' ? 'AUD' : 'FILE' }}</span>
        <button class="file-name" :title="entry.name" @click="entry.directory ? open(entry.path) : preview(entry)">{{ entry.name }}<small v-if="entry.symlink">Link</small></button>
        <span class="file-size">{{ entry.directory ? '—' : size(entry.size) }}</span><time class="modified">{{ new Date(entry.modified * 1000).toLocaleDateString() }}</time>
        <a v-if="!entry.directory" :href="filesApi.contentUrl(entry.path, true)" :download="entry.name" class="download" :aria-label="`Download ${entry.name}`">↓<span> Download</span></a><span v-else class="directory-arrow">›</span>
      </div>
      <footer v-if="listing && (listing.offset > 0 || listing.has_more)" class="pagination"><button :disabled="loading || listing.offset === 0" @click="open(listing.path, Math.max(0, listing.offset - 200))">Previous</button><span>Page {{ Math.floor(listing.offset / 200) + 1 }}</span><button :disabled="loading || !listing.has_more" @click="open(listing.path, listing.offset + 200)">Next</button></footer>
    </div>
    <BaseModal :open="!!selected" :title="selected?.name || 'File preview'" max-width="1040px" @close="closePreview">
      <template v-if="selected"><div class="preview-actions"><span>{{ size(selected.size) }} · {{ selected.kind }}</span><a :href="filesApi.contentUrl(selected.path, true)" :download="selected.name">Download original</a></div><p v-if="previewError" role="alert" class="error">{{ previewError }}</p>
        <img v-if="selected.kind === 'image'" class="image-preview" :src="filesApi.contentUrl(selected.path)" :alt="selected.name" @error="mediaError" />
        <video v-else-if="selected.kind === 'video'" :key="selected.path" class="video-preview" :src="filesApi.contentUrl(selected.path)" controls playsinline preload="metadata" @error="mediaError" />
        <audio v-else-if="selected.kind === 'audio'" :key="selected.path" :src="filesApi.contentUrl(selected.path)" controls preload="metadata" @error="mediaError" />
        <iframe v-else-if="previewHtml" title="Read-only file preview" sandbox="" :srcdoc="previewHtml" class="text-preview" />
        <p v-else-if="previewLoading" role="status">Preparing preview…</p>
      </template>
    </BaseModal>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import { filesApi, type FileEntry, type FileListing } from '@/api/files'
const listing = ref<FileListing | null>(null), pathInput = ref('/'), filter = ref(''), error = ref(''), loading = ref(false)
const selected = ref<FileEntry | null>(null), previewHtml = ref(''), previewError = ref(''), previewLoading = ref(false)
let directoryController: AbortController | undefined, previewController: AbortController | undefined
const entries = computed(() => listing.value?.entries.filter(e => e.name.toLowerCase().includes(filter.value.toLowerCase())) ?? [])
const breadcrumbs = computed(() => { const parts = listing.value?.path.split('/').filter(Boolean) ?? []; return parts.map((name, index) => ({ name, path: '/' + parts.slice(0, index + 1).join('/') })) })
function detail(e: any) {
  if (typeof e.response?.data?.detail === 'string') return e.response.data.detail
  try { return JSON.parse(e.response?.data).detail || 'This path could not be read.' } catch { return 'This path could not be read.' }
}
async function open(path: string, offset = 0) {
  directoryController?.abort(); const controller = new AbortController(); directoryController = controller
  loading.value = true; error.value = ''
  try { const { data } = await filesApi.list(path, offset, controller.signal); listing.value = data; pathInput.value = data.path; filter.value = '' }
  catch (e) { if (!controller.signal.aborted) error.value = detail(e) }
  finally { if (!controller.signal.aborted) loading.value = false }
}
async function preview(entry: FileEntry) {
  closePreview(); selected.value = entry
  if (['image', 'video', 'audio'].includes(entry.kind)) return
  const controller = new AbortController(); previewController = controller; previewLoading.value = true
  try { previewHtml.value = (await filesApi.preview(entry.path, controller.signal)).data }
  catch (e) { if (!controller.signal.aborted) previewError.value = detail(e) }
  finally { if (!controller.signal.aborted) previewLoading.value = false }
}
function closePreview() { previewController?.abort(); selected.value = null; previewHtml.value = ''; previewError.value = ''; previewLoading.value = false }
function mediaError() { previewError.value = 'This media could not be played. The file may be unreadable or use a codec your browser does not support. You can download the original.' }
function size(value: number | null) { if (value == null) return '—'; const i = value > 0 ? Math.min(4, Math.max(0, Math.floor(Math.log(value) / Math.log(1024)))) : 0; return `${(value / 1024 ** i).toLocaleString(undefined, { maximumFractionDigits: 1 })} ${['B', 'KiB', 'MiB', 'GiB', 'TiB'][i]}` }
onMounted(() => { void open('/') })
onUnmounted(() => { directoryController?.abort(); previewController?.abort() })
</script>
<style scoped>
.files-page { padding: 24px; max-width: 1500px; margin: auto; width: 100%; }
.page-heading { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 20px; } h1 { font-size: 18px; } .page-heading p { color: var(--fg-muted); font-size: 11px; margin-top: 6px; }
button, input, a.download, .preview-actions a { font: 11px var(--font); color: var(--fg); border: 1px solid var(--border); background: var(--bg-input); padding: 9px 12px; border-radius: var(--radius-sm); }
button, a { cursor: pointer; transition: color var(--transition), border-color var(--transition); } button:hover, a:hover { color: var(--accent); border-color: var(--accent-border); } button:disabled { opacity: .4; cursor: default; }
.path-bar { display: flex; gap: 8px; } .path-bar input { flex: 1; min-width: 0; } .access-note { font-size: 10px; color: var(--fg-dim); margin: 12px 0 18px; line-height: 1.6; }
.breadcrumbs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; } .breadcrumbs button { background: none; border-color: transparent; padding: 5px 8px; overflow-wrap: anywhere; }
.files-card { background: var(--surface-panel); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
.list-heading { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 12px 16px; color: var(--fg-dim); font-size: 10px; border-bottom: 1px solid var(--border); } .list-heading input { width: 170px; margin-left: 8px; }
.file-row { display: flex; align-items: center; gap: 14px; padding: 8px 16px; border-bottom: 1px solid var(--border-row); } .file-kind { width: 34px; flex-shrink: 0; color: var(--accent); font-size: 9px; } .file-name { flex: 1; min-width: 0; text-align: left; background: none; border-color: transparent; padding: 8px 0; overflow-wrap: anywhere; } .file-name small { font-size: 9px; color: var(--fg-dim); margin-left: 8px; }
.file-size, .modified { font-size: 10px; color: var(--fg-muted); flex-shrink: 0; width: 85px; text-align: right; } a.download { text-decoration: none; background: none; font-size: 10px; } .directory-arrow { width: 98px; text-align: right; color: var(--fg-dim); }
.pagination { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; font-size: 10px; color: var(--fg-muted); } .empty { padding: 40px 16px; text-align: center; color: var(--fg-dim); font-size: 11px; } .error { color: var(--danger); font-size: 11px; line-height: 1.6; margin: 12px 0; }
.preview-actions { display: flex; flex-wrap: wrap; gap: 12px; justify-content: space-between; align-items: center; font-size: 10px; color: var(--fg-muted); margin-bottom: 16px; }.preview-actions a { color: var(--accent); text-decoration: none; }
.image-preview { display: block; max-width: 100%; max-height: 65dvh; margin: auto; object-fit: contain; } .video-preview { width: 100%; max-height: 65dvh; } .text-preview { width: 100%; height: 60dvh; border: 1px solid var(--border); border-radius: var(--radius-sm); } audio { width: 100%; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
@media(max-width: 640px) { .files-page { padding: 16px; } .modified { display: none; } .file-row { gap: 8px; padding: 8px 12px; } .download span { display: none; } .directory-arrow { width: 32px; } .file-size { width: 65px; } .list-heading { flex-wrap: wrap; } }
</style>
