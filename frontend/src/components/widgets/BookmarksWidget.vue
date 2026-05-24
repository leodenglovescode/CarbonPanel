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
      <div
        v-for="bm in bookmarks"
        :key="bm.id"
        class="bm-tile"
      >
        <a :href="bm.url" target="_blank" rel="noopener noreferrer" class="bm-link" @click.stop>
          <img
            class="bm-icon"
            :src="iconSrc(bm)"
            :alt="bm.title"
            @error="onIconError($event, bm)"
          />
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
import { ref, onMounted } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import { bookmarksApi, type BookmarkInfo } from '@/api'

const bookmarks = ref<BookmarkInfo[]>([])

const formOpen = ref(false)
const editId = ref<string | null>(null)
const formTitle = ref('')
const formUrl = ref('')
const formIconUrl = ref('')

const iconErrors = ref(new Set<string>())

onMounted(async () => {
  try {
    const { data } = await bookmarksApi.list()
    bookmarks.value = data
  } catch { /* silent */ }
})

function faviconUrl(url: string) {
  try {
    const domain = new URL(url).hostname
    return `https://www.google.com/s2/favicons?sz=32&domain_url=${domain}`
  } catch { return '' }
}

function iconSrc(bm: BookmarkInfo) {
  if (bm.icon_url) return bm.icon_url
  if (!iconErrors.value.has(bm.id)) return faviconUrl(bm.url)
  return ''
}

function onIconError(e: Event, bm: BookmarkInfo) {
  iconErrors.value.add(bm.id)
  ;(e.target as HTMLImageElement).style.display = 'none'
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
  } catch { /* TODO: show error */ }
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

.bm-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.bm-tile {
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--bg-subtle, rgba(128,128,128,0.06));
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 4px 6px;
  transition: border-color var(--transition);
}
.bm-tile:hover { border-color: var(--accent-border); }

.bm-link {
  display: flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  color: var(--fg);
  min-width: 0;
}

.bm-icon { width: 16px; height: 16px; object-fit: contain; flex-shrink: 0; }

.bm-label {
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.bm-actions { display: flex; gap: 2px; margin-left: 2px; }
.bm-edit, .bm-del {
  background: none;
  border: none;
  color: var(--fg-dim);
  font-size: 11px;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
  transition: color var(--transition);
}
.bm-edit:hover { color: var(--accent); }
.bm-del:hover { color: var(--danger); }

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
