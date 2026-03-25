<template>
  <div class="sites-page">
    <div class="page-header">
      <h1 class="page-title">Sites</h1>
      <button class="add-btn" @click="showForm = true">+ add site</button>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSitesStore } from '@/stores/sites'
import SiteCard from '@/components/sites/SiteCard.vue'
import type { SiteType, ServiceManager } from '@/types/sites'

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

.page-header { display: flex; align-items: center; justify-content: space-between; }
.page-title { font-size: 16px; font-weight: 700; color: var(--fg); }

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

.state-msg { font-size: 12px; color: var(--fg-muted); padding: 40px 0; text-align: center; }
.state-msg.error { color: var(--danger); }
.state-msg.muted { color: var(--fg-dim); }

.sites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 10px;
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
