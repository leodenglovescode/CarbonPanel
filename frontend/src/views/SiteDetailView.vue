<template>
  <div class="detail-page">
    <div v-if="loading" class="state-msg">loading…</div>
    <div v-else-if="!site" class="state-msg error">site not found</div>

    <template v-else>
      <!-- Header -->
      <div class="detail-header">
        <div class="breadcrumb">
          <router-link to="/sites" class="back-link">← sites</router-link>
          <span class="sep">/</span>
          <span class="site-name-crumb">{{ site.name }}</span>
        </div>

        <div class="header-right">
          <button class="delete-btn" @click="confirmDelete">delete</button>
        </div>
      </div>

      <!-- Status bar -->
      <div class="status-bar">
        <span :class="['type-badge', `type-${site.type}`]">{{ site.type }}</span>
        <span :class="['status-dot', statusClass(site.status?.status)]" />
        <span class="status-text">{{ site.status?.status ?? 'unknown' }}</span>
        <span v-if="site.status?.uptime" class="meta">· {{ site.status.uptime }}</span>
        <span v-if="site.status?.pid" class="meta">pid {{ site.status.pid }}</span>
        <span class="meta-sep">·</span>
        <span class="svc-badge">{{ site.service_manager }}</span>
        <span class="svc-name">{{ site.service_name }}</span>
      </div>

      <!-- Actions -->
      <div class="actions-row">
        <button
          v-for="act in (['start', 'stop', 'restart'] as const)"
          :key="act"
          :class="['action-btn', `action-${act}`]"
          :disabled="actionLoading === act"
          @click="runAction(act)"
        >{{ actionLoading === act ? '…' : act }}</button>

        <span v-if="actionOutput" class="action-output">{{ actionOutput }}</span>
      </div>

      <!-- Tabs -->
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab"
          :class="['tab-btn', { active: activeTab === tab }]"
          @click="activeTab = tab"
        >{{ tab }}</button>
      </div>

      <!-- Tab content -->
      <div class="tab-content">
        <LogViewer
          v-if="activeTab === 'logs'"
          :site-id="site.id"
          :log-path="site.log_paths[0] ?? null"
        />
        <ConfigEditor
          v-else-if="activeTab === 'config'"
          :site-id="site.id"
          :config-path="site.config_file_path"
        />
      </div>
    </template>

    <!-- Delete confirm modal -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
      <div class="confirm-modal">
        <p class="confirm-msg">Delete <strong>{{ site?.name }}</strong>? This cannot be undone.</p>
        <div class="confirm-actions">
          <button class="btn-ghost" @click="showDeleteConfirm = false">cancel</button>
          <button class="btn-danger" :disabled="deleting" @click="doDelete">
            {{ deleting ? 'deleting…' : 'delete' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { sitesApi } from '@/api'
import { useSitesStore } from '@/stores/sites'
import LogViewer from '@/components/sites/LogViewer.vue'
import ConfigEditor from '@/components/sites/ConfigEditor.vue'
import type { SiteResponse } from '@/types/sites'

const route = useRoute()
const router = useRouter()
const store = useSitesStore()

const site = ref<SiteResponse | null>(null)
const loading = ref(true)
const actionLoading = ref<string | null>(null)
const actionOutput = ref('')
const activeTab = ref<'logs' | 'config'>('logs')
const tabs = ['logs', 'config'] as const
const showDeleteConfirm = ref(false)
const deleting = ref(false)

async function loadSite() {
  loading.value = true
  try {
    const res = await sitesApi.get(route.params.id as string)
    site.value = res.data
  } catch {
    site.value = null
  } finally {
    loading.value = false
  }
}

async function runAction(act: string) {
  if (!site.value) return
  actionLoading.value = act
  actionOutput.value = ''
  try {
    const res = await sitesApi.action(site.value.id, act)
    actionOutput.value = res.data.success ? '✓' : res.data.output.slice(0, 80)
    // Refresh status
    const updated = await sitesApi.get(site.value.id)
    site.value = updated.data
  } finally {
    actionLoading.value = null
    setTimeout(() => { actionOutput.value = '' }, 3000)
  }
}

function statusClass(s?: string) {
  if (s === 'active') return 'dot-green'
  if (s === 'failed') return 'dot-red'
  if (s === 'inactive') return 'dot-gray'
  return 'dot-yellow'
}

function confirmDelete() { showDeleteConfirm.value = true }

async function doDelete() {
  if (!site.value) return
  deleting.value = true
  try {
    await store.deleteSite(site.value.id)
    router.push('/sites')
  } finally {
    deleting.value = false
    showDeleteConfirm.value = false
  }
}

onMounted(() => loadSite())
</script>

<style scoped>
.detail-page {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
  box-sizing: border-box;
}

.state-msg { font-size: 12px; color: var(--fg-muted); padding: 40px 0; text-align: center; }
.state-msg.error { color: var(--danger); }

/* Header */
.detail-header { display: flex; align-items: center; justify-content: space-between; }
.breadcrumb { display: flex; align-items: center; gap: 6px; font-size: 12px; }
.back-link { color: var(--fg-muted); text-decoration: none; transition: color var(--transition); }
.back-link:hover { color: var(--accent); }
.sep { color: var(--fg-dim); }
.site-name-crumb { color: var(--fg); font-weight: 600; }
.delete-btn {
  background: none; border: 1px solid var(--border); color: var(--fg-dim);
  font-family: var(--font); font-size: 10px; padding: 3px 10px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition);
}
.delete-btn:hover { border-color: var(--danger); color: var(--danger); }

/* Status bar */
.status-bar { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.type-badge {
  font-size: 9px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  padding: 2px 7px; border-radius: 3px; flex-shrink: 0;
}
.type-nginx     { background: rgba(96,165,250,0.15); color: #60a5fa; border: 1px solid rgba(96,165,250,0.3); }
.type-python    { background: rgba(250,204,21,0.12); color: #facc15; border: 1px solid rgba(250,204,21,0.3); }
.type-wordpress { background: rgba(45,212,191,0.12); color: #2dd4bf; border: 1px solid rgba(45,212,191,0.3); }
.type-nodejs    { background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent-border); }

.status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.dot-green  { background: var(--accent); box-shadow: 0 0 4px var(--accent); }
.dot-red    { background: var(--danger); }
.dot-gray   { background: var(--fg-dim); }
.dot-yellow { background: var(--warning); }
.status-text { font-size: 11px; color: var(--fg-muted); }
.meta { font-size: 10px; color: var(--fg-dim); }
.meta-sep { color: var(--fg-dim); }
.svc-badge {
  font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em;
  padding: 1px 5px; border-radius: 2px;
  background: var(--bg-badge); color: var(--fg-dim); border: 1px solid var(--border);
}
.svc-name { font-size: 11px; color: var(--fg-muted); }

/* Actions */
.actions-row { display: flex; align-items: center; gap: 6px; }
.action-btn {
  background: none; border: 1px solid var(--border); color: var(--fg-dim);
  font-family: var(--font); font-size: 10px; padding: 4px 16px;
  border-radius: 3px; cursor: pointer; transition: all var(--transition);
  text-transform: capitalize;
}
.action-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.action-start:hover:not(:disabled)   { border-color: var(--accent); color: var(--accent); }
.action-stop:hover:not(:disabled)    { border-color: var(--danger); color: var(--danger); }
.action-restart:hover:not(:disabled) { border-color: var(--warning); color: var(--warning); }
.action-output { font-size: 11px; color: var(--fg-muted); }

/* Tabs */
.tabs { display: flex; gap: 2px; border-bottom: 1px solid var(--border); }
.tab-btn {
  background: none; border: none; border-bottom: 2px solid transparent;
  color: var(--fg-dim); font-family: var(--font); font-size: 11px;
  padding: 6px 14px; cursor: pointer; transition: all var(--transition);
  margin-bottom: -1px;
}
.tab-btn:hover { color: var(--fg-muted); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }

/* Tab content */
.tab-content { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.tab-content > * { flex: 1; min-height: 0; }

/* Delete modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.confirm-modal {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 20px; width: 340px; max-width: 95vw;
  display: flex; flex-direction: column; gap: 16px;
}
.confirm-msg { font-size: 13px; color: var(--fg); }
.confirm-actions { display: flex; justify-content: flex-end; gap: 8px; }
.btn-ghost {
  background: none; border: 1px solid var(--border); color: var(--fg-dim);
  font-family: var(--font); font-size: 11px; padding: 5px 12px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition);
}
.btn-ghost:hover { border-color: var(--fg-dim); color: var(--fg); }
.btn-danger {
  background: var(--danger-dim); border: 1px solid var(--danger); color: var(--danger);
  font-family: var(--font); font-size: 11px; padding: 5px 12px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition);
}
.btn-danger:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
