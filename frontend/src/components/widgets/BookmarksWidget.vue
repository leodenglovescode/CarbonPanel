<template>
  <BaseCard>
    <template #header>
      <span class="card-title">Quick Links</span>
      <button class="add-btn" @click="openAdd" title="Add bookmark">+</button>
    </template>

    <!-- Add / Edit form -->
    <div v-if="formOpen" class="bm-form" @click.stop>
      <div class="form-fields">
        <input v-model="formTitle" placeholder="Title" class="bm-input" @keydown.enter="submitForm" @keydown.escape="closeForm" />
        <input v-model="formUrl" placeholder="https://…" class="bm-input" @keydown.enter="submitForm" @keydown.escape="closeForm" />
        <input v-model="formIconUrl" placeholder="Icon URL (optional)" class="bm-input" @keydown.escape="closeForm" />
      </div>
      <div class="form-row">
        <button class="fm-cancel" @click="closeForm">Cancel</button>
        <button class="fm-save" @click="submitForm" :disabled="!formUrl.trim()">
          {{ editId ? 'Save' : 'Add' }}
        </button>
      </div>
    </div>

    <div v-else-if="!bookmarks.length" class="empty-state">
      No links yet — click <strong>+</strong> to add one.
    </div>

    <div v-else class="bm-grid">
      <div v-for="bm in bookmarks" :key="bm.id" class="bm-tile">
        <a :href="bm.url" target="_blank" rel="noopener noreferrer" class="bm-link" @click.stop>
          <div class="bm-icon-wrap">
            <img
              v-if="!iconErrors.has(bm.id)"
              class="bm-icon"
              :src="iconSrc(bm)"
              :alt="bm.title"
              @error="onIconError($event, bm)"
            />
            <div v-else class="bm-icon-fallback" :style="{ background: tileColor(bm.title) }">
              {{ bm.title.charAt(0).toUpperCase() }}
            </div>
          </div>
          <span class="bm-label">{{ bm.title }}</span>
        </a>
        <div class="bm-actions">
          <button class="bm-edit" @click.stop="openEdit(bm)" title="Edit">✎</button>
          <button class="bm-del" @click.stop="deleteBookmark(bm.id)" title="Remove">×</button>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import { bookmarksApi, type BookmarkInfo } from '@/api'

const bookmarks = ref<BookmarkInfo[]>([])
const iconErrors = reactive(new Set<string>())

const formOpen = ref(false)
const editId = ref<string | null>(null)
const formTitle = ref('')
const formUrl = ref('')
const formIconUrl = ref('')

onMounted(async () => {
  try {
    const { data } = await bookmarksApi.list()
    bookmarks.value = data
  } catch { /* silent */ }
})

function faviconUrl(url: string) {
  try {
    const domain = new URL(url).hostname
    return `https://www.google.com/s2/favicons?sz=64&domain_url=${domain}`
  } catch { return '' }
}

function iconSrc(bm: BookmarkInfo) {
  return bm.icon_url || faviconUrl(bm.url)
}

function onIconError(e: Event, bm: BookmarkInfo) {
  iconErrors.add(bm.id)
  ;(e.target as HTMLImageElement).style.display = 'none'
}

const PALETTE = ['#4f46e5','#0891b2','#059669','#d97706','#dc2626','#7c3aed','#db2777','#0284c7']
function tileColor(title: string) {
  let hash = 0
  for (let i = 0; i < title.length; i++) hash = (hash * 31 + title.charCodeAt(i)) & 0xffffffff
  return PALETTE[Math.abs(hash) % PALETTE.length]
}

function openAdd() {
  editId.value = null
  formTitle.value = ''
  formUrl.value = ''
  formIconUrl.value = ''
  formOpen.value = true
}

function openEdit(bm: BookmarkInfo) {
  editId.value = bm.id
  formTitle.value = bm.title
  formUrl.value = bm.url
  formIconUrl.value = bm.icon_url || ''
  formOpen.value = true
}

function closeForm() {
  formOpen.value = false
  editId.value = null
}

async function submitForm() {
  const url = formUrl.value.trim()
  if (!url) return
  const title = formTitle.value.trim() || url
  const icon_url = formIconUrl.value.trim() || null
  const sort_order = editId.value
    ? (bookmarks.value.find(b => b.id === editId.value)?.sort_order ?? 0)
    : bookmarks.value.length
  try {
    if (editId.value) {
      const { data } = await bookmarksApi.update(editId.value, { title, url, icon_url, sort_order })
      const idx = bookmarks.value.findIndex(b => b.id === editId.value)
      if (idx !== -1) bookmarks.value[idx] = data
    } else {
      const { data } = await bookmarksApi.create({ title, url, icon_url, sort_order })
      bookmarks.value.push(data)
    }
    closeForm()
  } catch { /* silent */ }
}

async function deleteBookmark(id: string) {
  try {
    await bookmarksApi.delete(id)
    bookmarks.value = bookmarks.value.filter(b => b.id !== id)
  } catch { /* silent */ }
}
</script>

<style scoped>
.card-title { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-muted); }

.add-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-dim);
  font-family: var(--font);
  font-size: 14px;
  line-height: 1;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition);
}
.add-btn:hover { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }

.empty-state { font-size: 11px; color: var(--fg-dim); padding: 4px 0; }

/* App-icon grid */
.bm-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-content: flex-start;
}

.bm-tile {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 68px;
}

.bm-link {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  color: var(--fg);
  width: 100%;
}

.bm-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--bg-subtle, rgba(128,128,128,0.08));
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  transition: border-color var(--transition), box-shadow var(--transition);
  flex-shrink: 0;
}
.bm-tile:hover .bm-icon-wrap {
  border-color: var(--accent-border);
  box-shadow: 0 0 0 2px var(--accent-border);
}

.bm-icon { width: 32px; height: 32px; object-fit: contain; }

.bm-icon-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  border-radius: 12px;
}

.bm-label {
  font-size: 10px;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
  color: var(--fg-muted);
}

/* Edit / Delete overlay buttons */
.bm-actions {
  position: absolute;
  top: -5px;
  right: 2px;
  display: none;
  gap: 2px;
}
.bm-tile:hover .bm-actions { display: flex; }

.bm-edit, .bm-del {
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--fg-dim);
  font-size: 10px;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  line-height: 1;
  transition: color var(--transition), border-color var(--transition);
}
.bm-edit:hover { color: var(--accent); border-color: var(--accent-border); }
.bm-del:hover { color: var(--danger); border-color: rgba(255,68,68,0.4); }

/* Inline add/edit form */
.bm-form { display: flex; flex-direction: column; gap: 8px; }
.form-fields { display: flex; flex-direction: column; gap: 6px; }
.bm-input {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--fg);
  font-family: var(--font);
  font-size: 11px;
  padding: 5px 8px;
  width: 100%;
  box-sizing: border-box;
  outline: none;
  transition: border-color var(--transition);
}
.bm-input:focus { border-color: var(--accent-border); }
.form-row { display: flex; gap: 6px; justify-content: flex-end; }
.fm-cancel, .fm-save {
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-muted);
  font-family: var(--font);
  font-size: 10px;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
}
.fm-cancel:hover { color: var(--fg); }
.fm-save { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }
.fm-save:hover { filter: brightness(1.1); }
.fm-save:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
