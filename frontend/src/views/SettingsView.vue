<template>
  <div class="settings-page">
    <main class="settings-main">
      <div class="settings-container">
        <div class="page-title">
          <router-link to="/" class="back-link">← dashboard</router-link>
          <h1>Settings</h1>
        </div>

        <!-- Theme Section -->
        <div class="section">
          <div class="section-header">
            <span class="section-title">Appearance</span>
            <span :class="['badge', theme.theme === 'dark' ? 'badge-gray' : 'badge-green']">
              {{ theme.theme }}
            </span>
          </div>
          <p class="section-desc">Switch between dark and light mode.</p>
          <div class="theme-toggle-row">
            <button
              :class="['theme-btn', { active: theme.theme === 'dark' }]"
              @click="theme.setTheme('dark')"
            >◑ Dark</button>
            <button
              :class="['theme-btn', { active: theme.theme === 'light' }]"
              @click="theme.setTheme('light')"
            >○ Light</button>
            <button
              :class="['theme-btn', { active: theme.theme === 'auto' }]"
              @click="theme.setTheme('auto')"
            >⟳ Auto</button>
          </div>
        </div>

        <!-- Update Frequency Section -->
        <div class="section">
          <div class="section-header">
            <span class="section-title">Update Frequency</span>
            <span class="badge badge-green">{{ intervalLabel }}</span>
          </div>
          <p class="section-desc">How often the dashboard polls new metrics. Lower = more live, higher = less CPU overhead.</p>

          <div class="interval-control">
            <span class="interval-bound">0.4s</span>
            <input
              type="range"
              class="interval-slider"
              :value="metrics.updateInterval"
              min="0.4"
              max="30"
              step="0.2"
              @input="onSliderInput"
            />
            <span class="interval-bound">30s</span>
          </div>

          <div class="interval-presets">
            <button
              v-for="p in presets"
              :key="p.value"
              :class="['preset-btn', { active: metrics.updateInterval === p.value }]"
              @click="applyPreset(p.value)"
            >{{ p.label }}</button>
          </div>
        </div>

        <!-- Alerts Section -->
        <div class="section">
          <div class="section-header">
            <span class="section-title">Alert Thresholds</span>
            <span class="badge badge-gray">toast on exceed</span>
          </div>
          <p class="section-desc">Set a % threshold for CPU, RAM, or any disk. A toast notification fires when exceeded. Set to 0 to disable.</p>

          <div v-for="metric in alertMetrics" :key="metric.key" class="alert-row">
            <span class="alert-lbl">{{ metric.label }}</span>
            <input
              type="range"
              class="interval-slider"
              :value="alerts.thresholds[metric.key]"
              min="0"
              max="100"
              step="5"
              @input="e => alerts.setThreshold(metric.key, parseInt((e.target as HTMLInputElement).value))"
            />
            <span class="alert-val">
              {{ alerts.thresholds[metric.key] === 0 ? 'off' : alerts.thresholds[metric.key] + '%' }}
            </span>
          </div>
        </div>

        <!-- 2FA Section -->
        <div class="section">
          <div class="section-header">
            <span class="section-title">Two-Factor Authentication</span>
            <span :class="['badge', auth.user?.totp_enabled ? 'badge-green' : 'badge-gray']">
              {{ auth.user?.totp_enabled ? 'enabled' : 'disabled' }}
            </span>
          </div>

          <!-- Enable flow -->
          <template v-if="!auth.user?.totp_enabled">
            <p class="section-desc">Add an extra layer of security with a TOTP authenticator app (Google Authenticator, Authy, etc.)</p>

            <div v-if="!setupData" class="setup-start">
              <BaseButton variant="ghost" @click="startSetup" :disabled="setupLoading">
                {{ setupLoading ? 'Loading…' : 'Set up 2FA' }}
              </BaseButton>
            </div>

            <div v-else class="setup-flow">
              <div class="qr-block">
                <p class="step-label">1. Scan with your authenticator app</p>
                <canvas ref="qrCanvas" class="qr-canvas" />
                <details class="manual-entry">
                  <summary>Enter key manually</summary>
                  <code class="secret-key">{{ setupData.secret }}</code>
                </details>
              </div>

              <form class="confirm-form" @submit.prevent="handleEnable">
                <p class="step-label">2. Enter the 6-digit code to confirm</p>
                <BaseInput
                  v-model="confirmCode"
                  label="Code"
                  id="enable-code"
                  placeholder="000000"
                  inputmode="numeric"
                  maxlength="6"
                  autofocus
                />
                <p v-if="enableError" class="error-msg">{{ enableError }}</p>
                <BaseButton variant="primary" :disabled="confirmCode.length !== 6 || enableLoading">
                  {{ enableLoading ? 'Verifying…' : 'Enable 2FA' }}
                </BaseButton>
              </form>
            </div>
          </template>

          <!-- Disable flow -->
          <template v-else>
            <p class="section-desc">2FA is active. Enter your current code to disable it.</p>
            <form class="confirm-form" @submit.prevent="handleDisable">
              <BaseInput
                v-model="disableCode"
                label="Current TOTP Code"
                id="disable-code"
                placeholder="000000"
                inputmode="numeric"
                maxlength="6"
              />
              <p v-if="disableError" class="error-msg">{{ disableError }}</p>
              <BaseButton variant="danger" :disabled="disableCode.length !== 6 || disableLoading">
                {{ disableLoading ? 'Disabling…' : 'Disable 2FA' }}
              </BaseButton>
            </form>
          </template>
        </div>

        <!-- Account info + change credentials -->
        <div class="section">
          <div class="section-header">
            <span class="section-title">Account</span>
          </div>
          <div class="account-info">
            <div class="info-row">
              <span class="info-lbl">Username</span>
              <span class="info-val">{{ auth.user?.username }}</span>
            </div>
            <div class="info-row">
              <span class="info-lbl">User ID</span>
              <span class="info-val text-muted">{{ auth.user?.id }}</span>
            </div>
          </div>

          <div class="change-creds-toggle">
            <button class="toggle-link" @click="showChangeCreds = !showChangeCreds">
              {{ showChangeCreds ? '▲ hide' : '▼ change username / password' }}
            </button>
          </div>

          <form v-if="showChangeCreds" class="confirm-form" @submit.prevent="handleChangeCreds">
            <BaseInput
              v-model="credsForm.currentPassword"
              label="Current Password"
              id="current-password"
              type="password"
              placeholder="••••••••"
              required
            />
            <BaseInput
              v-model="credsForm.newUsername"
              label="New Username (optional)"
              id="new-username"
              :placeholder="auth.user?.username ?? ''"
            />
            <BaseInput
              v-model="credsForm.newPassword"
              label="New Password (optional, min 8 chars)"
              id="new-password"
              type="password"
              placeholder="••••••••"
            />
            <p v-if="credsError" class="error-msg">{{ credsError }}</p>
            <p v-if="credsSuccess" class="success-msg">{{ credsSuccess }}</p>
            <BaseButton
              variant="primary"
              :disabled="!credsForm.currentPassword || credsLoading"
            >
              {{ credsLoading ? 'Saving…' : 'Save Changes' }}
            </BaseButton>
          </form>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import { useAuthStore } from '@/stores/auth'
import { useMetricsStore } from '@/stores/metrics'
import { useThemeStore } from '@/stores/theme'
import { useAlertsStore } from '@/stores/alerts'
import { useWebSocket } from '@/composables/useWebSocket'
import { settingsApi } from '@/api'
import QRCode from 'qrcode'

const auth = useAuthStore()
const metrics = useMetricsStore()
const theme = useThemeStore()
const alerts = useAlertsStore()
const { sendInterval } = useWebSocket()

const alertMetrics = [
  { key: 'cpu'  as const, label: 'CPU' },
  { key: 'ram'  as const, label: 'RAM' },
  { key: 'disk' as const, label: 'Disk' },
]

const presets = [
  { label: '0.4s', value: 0.4 },
  { label: '1s',   value: 1 },
  { label: '2s',   value: 2 },
  { label: '5s',   value: 5 },
  { label: '10s',  value: 10 },
  { label: '30s',  value: 30 },
]

const intervalLabel = computed(() => {
  const v = metrics.updateInterval
  return v < 1 ? `${v.toFixed(1)}s` : `${v % 1 === 0 ? v.toFixed(0) : v.toFixed(1)}s`
})

function onSliderInput(e: Event) {
  const val = parseFloat((e.target as HTMLInputElement).value)
  metrics.setUpdateInterval(val)
  sendInterval(val)
}

function applyPreset(val: number) {
  metrics.setUpdateInterval(val)
  sendInterval(val)
}

const setupData = ref<{ secret: string; otpauth_uri: string } | null>(null)
const setupLoading = ref(false)
const qrCanvas = ref<HTMLCanvasElement | null>(null)

const confirmCode = ref('')
const enableLoading = ref(false)
const enableError = ref('')

const disableCode = ref('')
const disableLoading = ref(false)
const disableError = ref('')

async function startSetup() {
  setupLoading.value = true
  try {
    const res = await settingsApi.setup2fa()
    setupData.value = res.data
    await nextTick()
    if (qrCanvas.value) {
      const style = getComputedStyle(document.documentElement)
      const fg = style.getPropertyValue('--fg').trim() || '#e0e0e0'
      const bg = style.getPropertyValue('--bg-card').trim() || '#111111'
      await QRCode.toCanvas(qrCanvas.value, res.data.otpauth_uri, {
        width: 180,
        color: { dark: fg, light: bg },
      })
    }
  } finally {
    setupLoading.value = false
  }
}

async function handleEnable() {
  if (confirmCode.value.length !== 6) return
  enableError.value = ''
  enableLoading.value = true
  try {
    await settingsApi.enable2fa(confirmCode.value)
    await auth.loadUser()
    setupData.value = null
    confirmCode.value = ''
  } catch (e: any) {
    enableError.value = e.response?.data?.detail || 'Invalid code'
    confirmCode.value = ''
  } finally {
    enableLoading.value = false
  }
}

async function handleDisable() {
  if (disableCode.value.length !== 6) return
  disableError.value = ''
  disableLoading.value = true
  try {
    await settingsApi.disable2fa(disableCode.value)
    await auth.loadUser()
    disableCode.value = ''
  } catch (e: any) {
    disableError.value = e.response?.data?.detail || 'Invalid code'
    disableCode.value = ''
  } finally {
    disableLoading.value = false
  }
}

// Change credentials
const showChangeCreds = ref(false)
const credsLoading = ref(false)
const credsError = ref('')
const credsSuccess = ref('')
const credsForm = ref({ currentPassword: '', newUsername: '', newPassword: '' })

async function handleChangeCreds() {
  credsError.value = ''
  credsSuccess.value = ''
  if (!credsForm.value.newUsername && !credsForm.value.newPassword) {
    credsError.value = 'Enter a new username or password'
    return
  }
  credsLoading.value = true
  try {
    await settingsApi.changeProfile(
      credsForm.value.currentPassword,
      credsForm.value.newUsername || undefined,
      credsForm.value.newPassword || undefined,
    )
    await auth.loadUser()
    credsSuccess.value = 'Changes saved successfully'
    credsForm.value = { currentPassword: '', newUsername: '', newPassword: '' }
  } catch (e: any) {
    credsError.value = e.response?.data?.detail || 'Failed to save changes'
  } finally {
    credsLoading.value = false
  }
}
</script>

<style scoped>
.settings-page { height: 100%; display: flex; flex-direction: column; }
.settings-main { flex: 1; overflow-y: auto; padding: 20px; display: flex; justify-content: center; }
.settings-container { width: 100%; max-width: 600px; display: flex; flex-direction: column; gap: 20px; }

.page-title { display: flex; align-items: center; gap: 14px; }
.page-title h1 { font-size: 16px; font-weight: 700; }
.back-link { font-size: 11px; color: var(--fg-muted); text-decoration: none; transition: color var(--transition); }
.back-link:hover { color: var(--accent); }

.section {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  transition: border-color var(--transition), background var(--transition);
}

.section-header { display: flex; align-items: center; gap: 10px; }
.section-title { font-size: 12px; font-weight: 600; color: var(--fg); }
.section-desc { font-size: 11px; color: var(--fg-muted); line-height: 1.6; }

/* Theme toggle */
.theme-toggle-row { display: flex; gap: 8px; }
.theme-btn {
  flex: 1;
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-dim);
  font-family: var(--font);
  font-size: 11px;
  padding: 7px 0;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
  letter-spacing: 0.04em;
}
.theme-btn:hover:not(.active) { border-color: var(--fg-dim); color: var(--fg-muted); }
.theme-btn.active {
  border-color: var(--accent-border);
  color: var(--accent);
  background: var(--accent-dim);
}

.setup-flow { display: flex; flex-direction: column; gap: 18px; }

.qr-block { display: flex; flex-direction: column; gap: 8px; }
.step-label { font-size: 11px; font-weight: 500; color: var(--fg); }
.qr-canvas { border-radius: 6px; }

.manual-entry { margin-top: 4px; }
.manual-entry summary { font-size: 10px; color: var(--fg-muted); cursor: pointer; }
.secret-key {
  display: block;
  margin-top: 6px;
  padding: 8px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--accent);
  word-break: break-all;
  letter-spacing: 0.05em;
}

.confirm-form, .setup-start { display: flex; flex-direction: column; gap: 10px; }

.error-msg {
  font-size: 11px;
  color: var(--danger);
  padding: 6px 10px;
  background: var(--danger-dim);
  border-radius: var(--radius-sm);
  animation: slide-in 150ms ease;
}
.success-msg {
  font-size: 11px;
  color: var(--accent);
  padding: 6px 10px;
  background: var(--accent-dim);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-sm);
  animation: slide-in 150ms ease;
}

@keyframes slide-in {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}

.interval-control { display: flex; align-items: center; gap: 10px; }
.interval-bound { font-size: 10px; color: var(--fg-dim); width: 26px; flex-shrink: 0; }
.interval-slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  border-radius: 2px;
  background: var(--border);
  outline: none;
  cursor: pointer;
  transition: background var(--transition);
}
.interval-slider:hover { background: var(--fg-dim); }
.interval-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  border: 2px solid var(--bg-card);
  transition: transform var(--transition), box-shadow var(--transition);
}
.interval-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 0 8px rgba(0,255,136,0.4);
}
.interval-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  border: 2px solid var(--bg-card);
}

.interval-presets { display: flex; gap: 6px; flex-wrap: wrap; }
.preset-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-dim);
  font-family: var(--font);
  font-size: 10px;
  padding: 3px 10px;
  border-radius: 3px;
  cursor: pointer;
  transition: all var(--transition);
}
.preset-btn:hover:not(.active) { color: var(--fg-muted); border-color: var(--fg-dim); }
.preset-btn.active { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }

.account-info { display: flex; flex-direction: column; gap: 8px; }
.info-row { display: flex; gap: 10px; align-items: center; }
.info-lbl { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg-dim); width: 80px; flex-shrink: 0; }
.info-val { font-size: 12px; color: var(--fg); }

.change-creds-toggle { }
.toggle-link {
  background: none;
  border: none;
  color: var(--fg-muted);
  font-family: var(--font);
  font-size: 11px;
  cursor: pointer;
  padding: 0;
  transition: color var(--transition);
}
.toggle-link:hover { color: var(--accent); }

.alert-row { display: flex; align-items: center; gap: 10px; }
.alert-lbl { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--fg-dim); width: 34px; flex-shrink: 0; }
.alert-val { font-size: 11px; color: var(--fg-muted); width: 28px; text-align: right; flex-shrink: 0; }
</style>
