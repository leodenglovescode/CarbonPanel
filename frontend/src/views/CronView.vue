<template>
  <div class="cron-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('cron.title') }}</h1>
        <p class="page-subtitle">{{ entries.length }} job{{ entries.length !== 1 ? 's' : '' }}</p>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="loadAll">
        {{ loading ? t('common.refreshing') : t('common.refresh') }}
      </button>
    </div>

    <!-- Panel-managed jobs -->
    <div class="managed-section">
      <div class="managed-header">
        <span class="managed-title">{{ t('cron.managedTitle') }}</span>
        <button class="add-btn" @click="openCreateForm">{{ t('cron.newJob') }}</button>
      </div>

      <div v-if="managedLoading" class="state-msg">{{ t('common.loading') }}</div>
      <div v-else-if="!managedJobs.length" class="state-msg muted">{{ t('cron.noManagedJobs') }}</div>
      <div v-else class="managed-list">
        <div v-for="job in managedJobs" :key="job.id" class="managed-card">
          <div class="managed-info">
            <div class="managed-label">{{ job.label }}</div>
            <div class="managed-meta">
              <code class="managed-schedule">{{ describeCronSchedule(job.schedule) }}</code>
              <code class="managed-command">{{ job.command }}</code>
            </div>
          </div>
          <div class="managed-actions">
            <button class="managed-btn" @click="openEditForm(job)">{{ t('common.edit') }}</button>
            <button class="managed-btn managed-btn-danger" @click="confirmDeleteJob(job)">{{ t('common.delete') }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Read-only view of everything else already on the system -->
    <div class="section-label">{{ t('cron.systemTitle') }}</div>
    <div v-if="loading && !entries.length" class="state-msg">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="state-msg error">{{ error }}</div>
    <div v-else-if="!entries.length" class="state-msg muted">{{ t('cron.noJobs') }}</div>

    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>{{ t('cron.source') }}</th>
            <th>{{ t('cron.user') }}</th>
            <th>{{ t('cron.schedule') }}</th>
            <th>{{ t('cron.command') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(e, i) in entries" :key="i">
            <td class="source-cell">{{ shortSource(e.source) }}</td>
            <td class="user-cell">{{ e.user }}</td>
            <td class="schedule-cell"><code>{{ e.schedule }}</code></td>
            <td class="cmd-cell"><code>{{ e.command }}</code></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create / edit modal -->
    <div v-if="formOpen" class="modal-overlay" @click.self="closeForm">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">{{ editingId ? t('cron.editJob') : t('cron.newJob') }}</span>
          <button class="close-btn" @click="closeForm">✕</button>
        </div>
        <div class="modal-body">
          <label class="form-field">
            <span class="form-lbl">{{ t('cron.label') }}</span>
            <input v-model="form.label" class="form-input" :placeholder="t('cron.labelPlaceholder')" />
          </label>

          <label class="form-field">
            <span class="form-lbl">{{ t('cron.command') }}</span>
            <input v-model="form.command" class="form-input mono" placeholder="/path/to/script.sh" />
          </label>

          <div class="form-field">
            <span class="form-lbl">{{ t('cron.runLabel') }}</span>
            <div class="freq-row">
              <button
                v-for="f in FREQ_OPTIONS"
                :key="f.value"
                :class="['freq-btn', { active: freq === f.value }]"
                @click="freq = f.value"
              >{{ f.label }}</button>
            </div>
          </div>

          <label v-if="freq === 'minutes'" class="form-field">
            <span class="form-lbl">{{ t('cron.everyNMinutes') }}</span>
            <input v-model.number="everyN" type="number" min="1" max="59" class="form-input" />
          </label>

          <label v-if="freq === 'hourly'" class="form-field">
            <span class="form-lbl">{{ t('cron.atMinute') }}</span>
            <input v-model.number="atMinute" type="number" min="0" max="59" class="form-input" />
          </label>

          <label v-if="freq === 'daily' || freq === 'weekly' || freq === 'monthly'" class="form-field">
            <span class="form-lbl">{{ t('cron.atTime') }}</span>
            <input v-model="atTime" type="time" class="form-input" />
          </label>

          <label v-if="freq === 'weekly'" class="form-field">
            <span class="form-lbl">{{ t('cron.onDay') }}</span>
            <select v-model.number="weekday" class="form-input">
              <option v-for="d in WEEKDAYS" :key="d.value" :value="d.value">{{ d.label }}</option>
            </select>
          </label>

          <label v-if="freq === 'monthly'" class="form-field">
            <span class="form-lbl">{{ t('cron.dayOfMonth') }}</span>
            <input v-model.number="dayOfMonth" type="number" min="1" max="31" class="form-input" />
          </label>

          <label v-if="freq === 'custom'" class="form-field">
            <span class="form-lbl">{{ t('cron.cronExpression') }}</span>
            <input v-model="customSchedule" class="form-input mono" placeholder="0 2 * * *" />
          </label>

          <p class="schedule-preview">
            → {{ describeCronSchedule(builtSchedule) }} <code>{{ builtSchedule }}</code>
          </p>

          <p v-if="formError" class="error-msg">{{ formError }}</p>

          <div class="modal-actions">
            <button class="btn-ghost" @click="closeForm">{{ t('common.cancel') }}</button>
            <button class="btn-primary" :disabled="formSaving" @click="submitForm">
              {{ formSaving ? '…' : (editingId ? t('common.save') : t('cron.create')) }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api, { cronApi, type CronJob } from '@/api/index'
import { useLocaleStore } from '@/stores/locale'
import { useDialogStore } from '@/stores/dialog'

const { t } = useLocaleStore()
const dialog = useDialogStore()

// ── Read-only system crontab listing ────────────────────────────────────────

interface CronEntry { source: string; user: string; schedule: string; command: string }
const entries = ref<CronEntry[]>([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get<CronEntry[]>('/cron')
    entries.value = data
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to load cron jobs'
  } finally {
    loading.value = false
  }
}

function shortSource(s: string) {
  const parts = s.split('/')
  return parts[parts.length - 1] || s
}

// ── Panel-managed jobs ───────────────────────────────────────────────────────

const managedJobs = ref<CronJob[]>([])
const managedLoading = ref(false)

async function loadManaged() {
  managedLoading.value = true
  try {
    const { data } = await cronApi.listManaged()
    managedJobs.value = data
  } catch {
    // The read-only system listing above already surfaces a load error;
    // this section just shows empty rather than duplicating that message.
  } finally {
    managedLoading.value = false
  }
}

async function loadAll() {
  await Promise.all([load(), loadManaged()])
}

async function confirmDeleteJob(job: CronJob) {
  const confirmed = await dialog.confirm({
    title: t('cron.deleteJob'),
    message: `${t('cron.deleteJobMsg')} "${job.label}"?`,
    confirmLabel: t('common.delete'),
    variant: 'danger',
  })
  if (!confirmed) return
  try {
    await cronApi.delete(job.id)
    await loadManaged()
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Failed to delete cron job'
  }
}

// ── Create / edit form ───────────────────────────────────────────────────────

type Freq = 'minutes' | 'hourly' | 'daily' | 'weekly' | 'monthly' | 'custom'

const FREQ_OPTIONS: { value: Freq; label: string }[] = [
  { value: 'minutes', label: 'Every N min' },
  { value: 'hourly', label: 'Hourly' },
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'custom', label: 'Custom' },
]

const WEEKDAYS = [
  { value: 0, label: 'Sunday' },
  { value: 1, label: 'Monday' },
  { value: 2, label: 'Tuesday' },
  { value: 3, label: 'Wednesday' },
  { value: 4, label: 'Thursday' },
  { value: 5, label: 'Friday' },
  { value: 6, label: 'Saturday' },
]

const formOpen = ref(false)
const editingId = ref<string | null>(null)
const formSaving = ref(false)
const formError = ref('')
const form = ref({ label: '', command: '' })

const freq = ref<Freq>('daily')
const everyN = ref(5)
const atMinute = ref(0)
const atTime = ref('02:00')
const weekday = ref(1)
const dayOfMonth = ref(1)
const customSchedule = ref('0 2 * * *')

function parseTime(t: string): [number, number] {
  const [h, m] = t.split(':').map((x) => parseInt(x, 10))
  return [Number.isFinite(h) ? h : 0, Number.isFinite(m) ? m : 0]
}

const builtSchedule = computed(() => {
  switch (freq.value) {
    case 'minutes': {
      const n = Math.min(59, Math.max(1, everyN.value || 1))
      return `*/${n} * * * *`
    }
    case 'hourly': {
      const m = Math.min(59, Math.max(0, atMinute.value || 0))
      return `${m} * * * *`
    }
    case 'daily': {
      const [h, m] = parseTime(atTime.value)
      return `${m} ${h} * * *`
    }
    case 'weekly': {
      const [h, m] = parseTime(atTime.value)
      return `${m} ${h} * * ${weekday.value}`
    }
    case 'monthly': {
      const [h, m] = parseTime(atTime.value)
      const d = Math.min(31, Math.max(1, dayOfMonth.value || 1))
      return `${m} ${h} ${d} * *`
    }
    case 'custom':
      return customSchedule.value.trim()
    default:
      return ''
  }
})

// Reverse-engineers a friendly description from a raw 5-field cron string —
// used both for the live preview while building a schedule and for jobs
// already created (which are only ever stored as the raw cron string, same
// as the read-only system listing above). Falls back to the raw string for
// anything that doesn't match one of the presets this page can build.
function describeCronSchedule(schedule: string): string {
  const parts = schedule.trim().split(/\s+/)
  if (parts.length !== 5) return schedule
  const [min, hour, dom, month, dow] = parts
  const hhmm = (h: string, m: string) => `${h.padStart(2, '0')}:${m.padStart(2, '0')}`

  if (dom === '*' && month === '*' && dow === '*') {
    if (min.startsWith('*/') && hour === '*') return `Every ${min.slice(2)} minutes`
    if (/^\d+$/.test(min) && hour === '*') return `Every hour at :${min.padStart(2, '0')}`
    if (/^\d+$/.test(min) && /^\d+$/.test(hour)) return `Daily at ${hhmm(hour, min)}`
  }
  if (dom === '*' && month === '*' && /^\d$/.test(dow) && /^\d+$/.test(min) && /^\d+$/.test(hour)) {
    return `Every ${WEEKDAYS[Number(dow) % 7].label} at ${hhmm(hour, min)}`
  }
  if (/^\d+$/.test(dom) && month === '*' && dow === '*' && /^\d+$/.test(min) && /^\d+$/.test(hour)) {
    return `Monthly on day ${dom} at ${hhmm(hour, min)}`
  }
  return schedule
}

function resetForm() {
  form.value = { label: '', command: '' }
  freq.value = 'daily'
  everyN.value = 5
  atMinute.value = 0
  atTime.value = '02:00'
  weekday.value = 1
  dayOfMonth.value = 1
  customSchedule.value = '0 2 * * *'
  formError.value = ''
}

function openCreateForm() {
  resetForm()
  editingId.value = null
  formOpen.value = true
}

// Presets can only round-trip a handful of cron shapes — anything else
// (an existing custom expression) is edited as raw cron via the Custom tab
// rather than guessing at a lossy preset match.
function openEditForm(job: CronJob) {
  resetForm()
  editingId.value = job.id
  form.value = { label: job.label, command: job.command }

  const parts = job.schedule.trim().split(/\s+/)
  const [min, hour, dom, month, dow] = parts.length === 5 ? parts : ['*', '*', '*', '*', '*']
  if (dom === '*' && month === '*' && dow === '*' && min.startsWith('*/') && hour === '*') {
    freq.value = 'minutes'
    everyN.value = parseInt(min.slice(2), 10) || 5
  } else if (dom === '*' && month === '*' && dow === '*' && /^\d+$/.test(min) && hour === '*') {
    freq.value = 'hourly'
    atMinute.value = parseInt(min, 10) || 0
  } else if (dom === '*' && month === '*' && dow === '*' && /^\d+$/.test(min) && /^\d+$/.test(hour)) {
    freq.value = 'daily'
    atTime.value = `${hour.padStart(2, '0')}:${min.padStart(2, '0')}`
  } else if (dom === '*' && month === '*' && /^\d$/.test(dow) && /^\d+$/.test(min) && /^\d+$/.test(hour)) {
    freq.value = 'weekly'
    atTime.value = `${hour.padStart(2, '0')}:${min.padStart(2, '0')}`
    weekday.value = parseInt(dow, 10)
  } else if (/^\d+$/.test(dom) && month === '*' && dow === '*' && /^\d+$/.test(min) && /^\d+$/.test(hour)) {
    freq.value = 'monthly'
    atTime.value = `${hour.padStart(2, '0')}:${min.padStart(2, '0')}`
    dayOfMonth.value = parseInt(dom, 10)
  } else {
    freq.value = 'custom'
    customSchedule.value = job.schedule
  }

  formOpen.value = true
}

function closeForm() {
  formOpen.value = false
}

async function submitForm() {
  formError.value = ''
  if (!form.value.command.trim()) {
    formError.value = t('cron.commandRequired')
    return
  }
  formSaving.value = true
  try {
    const payload = { label: form.value.label, command: form.value.command, schedule: builtSchedule.value }
    if (editingId.value) {
      await cronApi.update(editingId.value, payload)
    } else {
      await cronApi.create(payload)
    }
    formOpen.value = false
    await loadManaged()
  } catch (e: any) {
    formError.value = e.response?.data?.detail || 'Failed to save cron job'
  } finally {
    formSaving.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.cron-page { padding: 20px; display: flex; flex-direction: column; gap: 14px; height: 100%; overflow-y: auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.page-title { font-size: 16px; font-weight: 700; }
.page-subtitle { font-size: 11px; color: var(--fg-muted); margin-top: 2px; }
.refresh-btn { background: none; border: 1px solid var(--border); color: var(--fg-muted); font-family: var(--font); font-size: 11px; padding: 5px 12px; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); }
.refresh-btn:hover:not(:disabled) { border-color: var(--accent-border); color: var(--accent); }
.refresh-btn:disabled { opacity: 0.5; cursor: default; }
.state-msg { font-size: 12px; color: var(--fg-muted); padding: 20px 0; text-align: center; }
.state-msg.error { color: var(--danger); }
.state-msg.muted { color: var(--fg-dim); }

.section-label { font-size: 10px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--fg-dim); margin-top: 4px; }

/* Panel-managed jobs */
.managed-section { display: flex; flex-direction: column; gap: 10px; }
.managed-header { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.managed-title { font-size: 13px; font-weight: 600; color: var(--fg); }
.add-btn { background: var(--accent-dim); border: 1px solid var(--accent-border); color: var(--accent); font-family: var(--font); font-size: 11px; padding: 5px 12px; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); flex-shrink: 0; }
.add-btn:hover { background: var(--accent); color: #000; }

.managed-list { display: flex; flex-direction: column; gap: 8px; }
.managed-card {
  background: color-mix(in srgb, var(--bg-card) 72%, transparent);
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  border: 1px solid var(--border); border-radius: var(--radius); padding: 10px 14px;
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  min-width: 0;
}
.managed-info { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1; }
.managed-label { font-size: 12px; font-weight: 600; color: var(--fg); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.managed-meta { display: flex; align-items: center; gap: 8px; min-width: 0; }
.managed-schedule { font-size: 10px; color: var(--accent); background: var(--accent-dim); padding: 2px 6px; border-radius: 3px; white-space: nowrap; flex-shrink: 0; }
.managed-command { font-size: 10px; color: var(--fg-muted); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; min-width: 0; }
.managed-actions { display: flex; gap: 6px; flex-shrink: 0; }
.managed-btn { background: none; border: 1px solid var(--border); color: var(--fg-muted); font-family: var(--font); font-size: 10px; padding: 4px 10px; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); }
.managed-btn:hover { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }
.managed-btn-danger:hover { border-color: rgba(255,68,68,0.4); color: var(--danger); background: var(--danger-dim); }

.table-wrap { overflow-x: auto; background: color-mix(in srgb, var(--bg-card) 72%, transparent); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); border: 1px solid var(--border); border-radius: var(--radius); }
table { width: 100%; border-collapse: collapse; }
thead th { font-size: 9px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--fg-dim); padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border-subtle); }
tbody tr:nth-child(even) { background: var(--bg-stripe); }
tbody tr:hover { background: var(--bg-hover); }
tbody td { font-size: 11px; padding: 8px 14px; color: var(--fg); border-bottom: 1px solid var(--border-row); }
tbody tr:last-child td { border-bottom: none; }

.source-cell { color: var(--fg-muted); max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-cell { color: var(--fg-muted); white-space: nowrap; }
.schedule-cell code { font-size: 11px; color: var(--accent); background: var(--accent-dim); padding: 2px 6px; border-radius: 3px; white-space: nowrap; }
.cmd-cell { max-width: 380px; }
.cmd-cell code { font-size: 11px; color: var(--fg); word-break: break-all; }

/* Create/edit modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 16px; box-sizing: border-box; }
.modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); width: 100%; max-width: 460px; max-height: 90vh; display: flex; flex-direction: column; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; border-bottom: 1px solid var(--border-subtle); flex-shrink: 0; }
.modal-title { font-size: 13px; font-weight: 600; }
.close-btn { background: none; border: none; color: var(--fg-dim); cursor: pointer; font-size: 14px; padding: 2px 6px; }
.modal-body { padding: 16px; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; }

.form-field { display: flex; flex-direction: column; gap: 5px; }
.form-lbl { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg-dim); }
.form-input {
  background: var(--bg-input); border: 1px solid var(--border); color: var(--fg);
  font-family: var(--font); font-size: 12px; padding: 7px 10px; border-radius: var(--radius-sm);
  outline: none; transition: border-color var(--transition); width: 100%; box-sizing: border-box;
}
.form-input:focus { border-color: var(--accent-border); }
.form-input.mono { font-family: monospace; }

.freq-row { display: flex; flex-wrap: wrap; gap: 6px; }
.freq-btn { background: none; border: 1px solid var(--border); color: var(--fg-muted); font-family: var(--font); font-size: 10px; padding: 5px 10px; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); }
.freq-btn:hover:not(.active) { border-color: var(--fg-dim); color: var(--fg); }
.freq-btn.active { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }

.schedule-preview { font-size: 11px; color: var(--fg-muted); }
.schedule-preview code { font-size: 10px; color: var(--accent); background: var(--accent-dim); padding: 2px 6px; border-radius: 3px; margin-left: 4px; }

.error-msg { font-size: 11px; color: var(--danger); padding: 6px 10px; background: var(--danger-dim); border-radius: var(--radius-sm); border: 1px solid rgba(255,68,68,0.2); }

.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 4px; }
.btn-ghost { background: none; border: 1px solid var(--border); color: var(--fg-muted); font-family: var(--font); font-size: 11px; padding: 6px 14px; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); }
.btn-ghost:hover { border-color: var(--fg-dim); color: var(--fg); }
.btn-primary { background: var(--accent); border: 1px solid var(--accent); color: #000; font-family: var(--font); font-size: 11px; font-weight: 600; padding: 6px 14px; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--transition); }
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: default; }

@media (max-width: 640px) {
  .cron-page { padding: 12px; gap: 10px; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 8px; }
  .table-wrap { font-size: 10px; }
  thead th { padding: 8px 10px; }
  tbody td { padding: 7px 10px; }
  .cmd-cell { max-width: 200px; }
  .managed-card { flex-direction: column; align-items: flex-start; }
  .managed-actions { width: 100%; }
  .managed-btn { flex: 1; }
}
</style>
