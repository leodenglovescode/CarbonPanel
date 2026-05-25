<template>
  <div class="sites-page">
    <div class="page-header">
      <h1 class="page-title">Sites</h1>
      <div class="header-actions">
        <button class="add-btn secondary" @click="openDiscover">⟳ from nginx</button>
        <button class="add-btn" @click="showForm = true">+ add site</button>
      </div>
    </div>

    <div v-if="store.loading" class="state-msg">loading…</div>
    <div v-else-if="store.error" class="state-msg error">{{ store.error }}</div>
    <div v-else-if="store.sites.length === 0" class="state-msg muted">
      no sites registered yet — add one to get started
    </div>

    <div v-else class="sites-grid">
      <SiteCard v-for="site in store.sites" :key="site.id" :site="site" />
    </div>

    <!-- Add Site Modal -->
    <div v-if="showForm" class="modal-overlay" @click.self="cancelForm">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">Add Site</span>
          <button class="close-btn" @click="cancelForm">✕</button>
        </div>

        <form class="modal-body" @submit.prevent="submitForm">
          <div class="form-row">
            <label class="form-label">Name</label>
            <input v-model="form.name" class="form-input" placeholder="My Site" required />
          </div>

          <div class="form-row">
            <label class="form-label">Type</label>
            <select v-model="form.type" class="form-input">
              <option value="nginx">nginx</option>
              <option value="python">python</option>
              <option value="wordpress">wordpress</option>
              <option value="nodejs">nodejs</option>
            </select>
          </div>

          <div class="form-row">
            <label class="form-label">Service Manager</label>
            <select v-model="form.service_manager" class="form-input">
              <option value="systemd">systemd</option>
              <option value="pm2">pm2</option>
            </select>
          </div>

          <div class="form-row">
            <label class="form-label">Service Name</label>
            <input
              v-model="form.service_name"
              class="form-input"
              :placeholder="form.service_manager === 'systemd' ? 'nginx.service' : 'my-app'"
              required
            />
          </div>

          <div class="form-row">
            <label class="form-label">Config File</label>
            <input v-model="form.config_file_path" class="form-input" placeholder="/etc/nginx/nginx.conf" />
          </div>

          <div class="form-row">
            <label class="form-label">Log Paths</label>
            <input v-model="logPathsRaw" class="form-input" placeholder="/var/log/nginx/access.log, /var/log/nginx/error.log" />
            <span class="form-hint">comma-separated</span>
          </div>

          <div class="form-row">
            <label class="form-label">Description</label>
            <input v-model="form.description" class="form-input" placeholder="optional" />
          </div>

          <p v-if="formError" class="form-error">{{ formError }}</p>

          <div class="modal-actions">
            <button type="button" class="btn-ghost" @click="cancelForm">cancel</button>
            <button type="submit" class="btn-primary" :disabled="submitting">
              {{ submitting ? 'saving…' : 'add site' }}
            </button>
          </div>
        </form>
      </div>
    </div>
    <!-- Discover nginx modal -->
    <div v-if="showDiscover" class="modal-overlay" @click.self="showDiscover = false">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">Discover nginx sites</span>
          <button class="close-btn" @click="showDiscover = false">✕</button>
        </div>
        <div class="modal-body">
          <div v-if="discoverLoading" class="state-msg">scanning…</div>
          <div v-else-if="discoverError" class="state-msg error">{{ discoverError }}</div>
          <div v-else-if="!discoverData?.nginx_available" class="state-msg muted">
            /etc/nginx/sites-available not found on this server
          </div>
          <div v-else-if="!discoverData.candidates.length" class="state-msg muted">
            no config files found in /etc/nginx/sites-available
          </div>
          <template v-else>
            <p class="discover-hint">
              Select configs to import as sites. Already-registered configs are pre-checked and
              will be skipped.
            </p>
            <div class="candidate-list">
              <label
                v-for="c in discoverData.candidates"
                :key="c.config_file_path"
                class="candidate-row"
              >
                <input
                  type="checkbox"
                  :value="c.config_file_path"
                  v-model="selectedPaths"
                  :disabled="c.already_exists"
                  class="cand-check"
                />
                <div class="cand-info">
                  <span class="cand-name">{{ c.name }}</span>
                  <span class="cand-path">{{ c.config_file_path }}</span>
                  <span v-if="c.already_exists" class="cand-exists">already added</span>
                  <span v-else-if="c.server_names.length" class="cand-meta">
                    {{ c.server_names.join(', ') }}
                  </span>
                </div>
              </label>
            </div>
            <p v-if="importError" class="form-error">{{ importError }}</p>
            <div class="modal-actions">
              <button class="btn-ghost" @click="showDiscover = false">cancel</button>
              <button
                class="btn-primary"
                :disabled="importing || !selectedPaths.length"
                @click="doImport"
              >
                {{ importing ? 'importing…' : `import ${selectedPaths.length}` }}
              </button>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSitesStore } from '@/stores/sites'
import SiteCard from '@/components/sites/SiteCard.vue'
import { sitesApi } from '@/api/index'
import type { SiteType, ServiceManager, NginxDiscoverResponse } from '@/types/sites'

const store = useSitesStore()

onMounted(() => store.fetchSites())

const showForm = ref(false)
const submitting = ref(false)
const formError = ref('')
const logPathsRaw = ref('')

const defaultForm = () => ({
  name: '',
  type: 'nginx' as SiteType,
  service_manager: 'systemd' as ServiceManager,
  service_name: '',
  config_file_path: '',
  description: '',
})

const form = ref(defaultForm())

function cancelForm() {
  showForm.value = false
  form.value = defaultForm()
  logPathsRaw.value = ''
  formError.value = ''
}

// ── nginx discovery ────────────────────────────────────────────
const showDiscover = ref(false)
const discoverLoading = ref(false)
const discoverError = ref('')
const discoverData = ref<NginxDiscoverResponse | null>(null)
const selectedPaths = ref<string[]>([])
const importing = ref(false)
const importError = ref('')

async function openDiscover() {
  showDiscover.value = true
  discoverLoading.value = true
  discoverError.value = ''
  discoverData.value = null
  selectedPaths.value = []
  try {
    const { data } = await sitesApi.discoverNginx()
    discoverData.value = data
    selectedPaths.value = data.candidates
      .filter(c => !c.already_exists)
      .map(c => c.config_file_path)
  } catch (e: any) {
    discoverError.value = e.response?.data?.detail || 'Failed to scan nginx'
  } finally {
    discoverLoading.value = false
  }
}

async function doImport() {
  importing.value = true
  importError.value = ''
  try {
    await sitesApi.importNginx(selectedPaths.value)
    showDiscover.value = false
    await store.fetchSites()
  } catch (e: any) {
    importError.value = e.response?.data?.detail || 'Import failed'
  } finally {
    importing.value = false
  }
}

async function submitForm() {
  formError.value = ''
  submitting.value = true
  try {
    const log_paths = logPathsRaw.value
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)

    await store.createSite({
      name: form.value.name,
      type: form.value.type,
      service_manager: form.value.service_manager,
      service_name: form.value.service_name,
      config_file_path: form.value.config_file_path || undefined,
      log_paths: log_paths.length ? log_paths : undefined,
      description: form.value.description || undefined,
    })
    cancelForm()
  } catch (e: any) {
    formError.value = e.response?.data?.detail || 'Failed to create site'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.sites-page { padding: 20px; display: flex; flex-direction: column; gap: 16px; }

.page-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.page-title { font-size: 16px; font-weight: 700; color: var(--fg); }
.header-actions { display: flex; gap: 8px; }

.add-btn {
  background: none;
  border: 1px solid var(--accent-border);
  color: var(--accent);
  font-family: var(--font);
  font-size: 11px;
  padding: 5px 12px;
  border-radius: 3px;
  cursor: pointer;
  transition: all var(--transition);
}
.add-btn:hover { background: var(--accent-dim); }
.add-btn.secondary { border-color: var(--border); color: var(--fg-muted); }
.add-btn.secondary:hover { border-color: var(--fg-dim); color: var(--fg); background: none; }

.state-msg { font-size: 12px; color: var(--fg-muted); padding: 40px 0; text-align: center; }
.state-msg.error { color: var(--danger); }
.state-msg.muted { color: var(--fg-dim); }

.sites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 10px;
}

/* Discover modal specifics */
.discover-hint { font-size: 11px; color: var(--fg-muted); line-height: 1.5; }

.candidate-list { display: flex; flex-direction: column; gap: 4px; max-height: 300px; overflow-y: auto; }
.candidate-row {
  display: flex; align-items: flex-start; gap: 10px; padding: 8px 10px;
  border: 1px solid var(--border); border-radius: var(--radius-sm); cursor: pointer;
  transition: border-color var(--transition);
}
.candidate-row:has(.cand-check:not(:disabled)):hover { border-color: var(--accent-border); }
.candidate-row:has(.cand-check:disabled) { opacity: 0.5; cursor: default; }
.cand-check { margin-top: 2px; flex-shrink: 0; accent-color: var(--accent); }
.cand-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.cand-name { font-size: 12px; font-weight: 600; color: var(--fg); }
.cand-path { font-size: 10px; color: var(--fg-dim); font-family: monospace; word-break: break-all; }
.cand-exists { font-size: 10px; color: var(--accent); }
.cand-meta { font-size: 10px; color: var(--fg-muted); }

@media (max-width: 640px) {
  .sites-page { padding: 12px; gap: 12px; }
  .sites-grid { grid-template-columns: 1fr; }
  .header-actions { flex-wrap: wrap; }
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  width: 440px;
  max-width: 95vw;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
}
.modal-title { font-size: 13px; font-weight: 600; }
.close-btn {
  background: none; border: none; color: var(--fg-dim); font-size: 12px;
  cursor: pointer; padding: 2px 4px; line-height: 1;
}
.close-btn:hover { color: var(--fg); }

.modal-body { padding: 16px; display: flex; flex-direction: column; gap: 12px; }

.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg-dim); }
.form-input {
  background: var(--bg-input);
  border: 1px solid var(--border);
  color: var(--fg);
  font-family: var(--font);
  font-size: 12px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  outline: none;
  transition: border-color var(--transition);
}
.form-input:focus { border-color: var(--accent-border); }
.form-hint { font-size: 10px; color: var(--fg-dim); }

.form-error { font-size: 11px; color: var(--danger); padding: 6px 10px; background: var(--danger-dim); border-radius: var(--radius-sm); }

.modal-actions { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }

.btn-ghost {
  background: none; border: 1px solid var(--border); color: var(--fg-dim);
  font-family: var(--font); font-size: 11px; padding: 5px 12px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition);
}
.btn-ghost:hover { border-color: var(--fg-dim); color: var(--fg); }

.btn-primary {
  background: var(--accent-dim); border: 1px solid var(--accent-border); color: var(--accent);
  font-family: var(--font); font-size: 11px; padding: 5px 14px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition);
}
.btn-primary:hover:not(:disabled) { background: rgba(0,255,136,0.15); }
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
