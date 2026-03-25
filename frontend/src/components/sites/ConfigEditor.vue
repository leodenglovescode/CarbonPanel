<template>
  <div class="config-editor">
    <div class="editor-toolbar">
      <span class="editor-path">{{ configPath ?? 'no config path set' }}</span>
      <div class="toolbar-actions">
        <span v-if="saveMsg" :class="['save-msg', saveMsg.type]">{{ saveMsg.text }}</span>
        <button class="save-btn" :disabled="!configPath || saving" @click="save">
          {{ saving ? 'saving…' : 'save' }}
        </button>
      </div>
    </div>

    <div v-if="loadError" class="load-error">{{ loadError }}</div>

    <textarea
      v-if="configPath"
      v-model="content"
      class="editor-area"
      spellcheck="false"
      :placeholder="loading ? 'loading…' : ''"
    />
    <div v-else class="no-config">no config file path configured for this site</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { sitesApi } from '@/api'

const props = defineProps<{ siteId: string; configPath: string | null }>()

const content = ref('')
const loading = ref(false)
const saving = ref(false)
const loadError = ref('')
const saveMsg = ref<{ text: string; type: 'ok' | 'err' } | null>(null)

async function load() {
  if (!props.configPath) return
  loadError.value = ''
  loading.value = true
  try {
    const res = await sitesApi.getConfig(props.siteId)
    content.value = res.data.content
  } catch (e: any) {
    loadError.value = e.response?.data?.detail || 'Failed to load config'
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!props.configPath) return
  saving.value = true
  saveMsg.value = null
  try {
    await sitesApi.saveConfig(props.siteId, content.value)
    saveMsg.value = { text: 'saved', type: 'ok' }
    setTimeout(() => { saveMsg.value = null }, 2000)
  } catch (e: any) {
    saveMsg.value = { text: e.response?.data?.detail || 'save failed', type: 'err' }
  } finally {
    saving.value = false
  }
}

onMounted(() => load())
watch(() => props.siteId, () => load())
</script>

<style scoped>
.config-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 300px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 10px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card);
  flex-shrink: 0;
}

.editor-path { font-size: 10px; color: var(--fg-dim); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.toolbar-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }

.save-msg { font-size: 10px; }
.save-msg.ok { color: var(--accent); }
.save-msg.err { color: var(--danger); }

.save-btn {
  background: none;
  border: 1px solid var(--accent-border);
  color: var(--accent);
  font-family: var(--font);
  font-size: 10px;
  padding: 2px 10px;
  border-radius: 3px;
  cursor: pointer;
  transition: all var(--transition);
}
.save-btn:hover:not(:disabled) { background: var(--accent-dim); }
.save-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.load-error {
  font-size: 11px;
  color: var(--danger);
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  background: var(--danger-dim);
  flex-shrink: 0;
}

.editor-area {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--fg);
  font-family: var(--font);
  font-size: 11px;
  line-height: 1.6;
  padding: 10px;
  resize: none;
  outline: none;
  tab-size: 4;
}

.no-config {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--fg-dim);
}
</style>
