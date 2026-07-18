<template>
  <div class="onboarding-page">
    <div class="onboarding-box">
      <div class="onboarding-logo">
        <span class="bracket">[</span>Carbon<span class="accent">Panel</span><span class="bracket">]</span>
      </div>

      <div class="step-track">
        <div
          v-for="(s, i) in STEPS"
          :key="s.title"
          :class="['step-dot', { active: i === step, done: i < step }]"
        />
      </div>
      <p class="step-label">Step {{ step + 1 }} of {{ STEPS.length }} — {{ STEPS[step].title }}</p>

      <!-- Step 0: Welcome -->
      <div v-if="step === 0" class="step-panel">
        <h1 class="step-heading">Welcome to CarbonPanel 👋</h1>
        <p class="step-desc">
          You're logged in with the credentials generated at install time. Let's spend a minute
          locking your account down before you head to the dashboard.
        </p>
        <div class="step-actions">
          <BaseButton variant="primary" style="width:100%; justify-content:center" @click="next">
            Get started
          </BaseButton>
        </div>
      </div>

      <!-- Step 1: Secure account -->
      <form v-else-if="step === 1" class="step-panel" @submit.prevent="saveAccount">
        <h1 class="step-heading">Secure your account</h1>
        <p class="step-desc">Set a password only you know. You can change your username here too.</p>

        <BaseInput
          v-model="currentPassword"
          label="Current password"
          id="ob-current-password"
          type="password"
          placeholder="the one from first-install.txt"
          autocomplete="current-password"
          autofocus
        />
        <BaseInput
          v-model="newUsername"
          label="New username (optional)"
          id="ob-new-username"
          :placeholder="auth.user?.username || 'admin'"
          autocomplete="username"
        />
        <BaseInput
          v-model="newPassword"
          label="New password"
          id="ob-new-password"
          type="password"
          placeholder="••••••••"
          autocomplete="new-password"
        />
        <BaseInput
          v-model="confirmPassword"
          label="Confirm new password"
          id="ob-confirm-password"
          type="password"
          placeholder="••••••••"
          autocomplete="new-password"
        />
        <p v-if="accountError" class="error-msg">{{ accountError }}</p>

        <div class="step-actions">
          <button type="button" class="skip-btn" @click="next">Skip for now</button>
          <BaseButton variant="primary" :disabled="accountLoading" style="flex:1; justify-content:center">
            {{ accountLoading ? 'Saving…' : 'Save & continue' }}
          </BaseButton>
        </div>
      </form>

      <!-- Step 2: 2FA -->
      <div v-else-if="step === 2" class="step-panel">
        <h1 class="step-heading">Two-factor authentication</h1>
        <p class="step-desc">Add a TOTP authenticator app (Google Authenticator, Authy, etc.) as a second factor.</p>

        <div v-if="!setupData" class="setup-start">
          <BaseButton variant="ghost" :disabled="setupLoading" @click="startTotpSetup">
            {{ setupLoading ? 'Loading…' : 'Set up 2FA' }}
          </BaseButton>
        </div>

        <div v-else class="setup-flow">
          <div class="qr-block">
            <p class="sub-label">1. Scan with your authenticator app</p>
            <canvas ref="qrCanvas" class="qr-canvas" />
            <details class="manual-entry">
              <summary>Enter key manually</summary>
              <code class="secret-key">{{ setupData.secret }}</code>
            </details>
          </div>
          <form class="confirm-form" @submit.prevent="confirmTotp">
            <p class="sub-label">2. Enter the 6-digit code to confirm</p>
            <BaseInput
              v-model="confirmCode"
              label="Code"
              id="ob-totp-code"
              placeholder="000000"
              inputmode="numeric"
              maxlength="6"
              autofocus
            />
            <BaseButton variant="primary" :disabled="confirmCode.length !== 6 || totpLoading" style="width:100%; justify-content:center">
              {{ totpLoading ? 'Verifying…' : 'Enable 2FA' }}
            </BaseButton>
          </form>
        </div>
        <p v-if="totpError" class="error-msg">{{ totpError }}</p>

        <div class="step-actions">
          <button type="button" class="skip-btn" @click="next">Skip for now</button>
        </div>
      </div>

      <!-- Step 3: Done -->
      <div v-else class="step-panel">
        <h1 class="step-heading">You're all set 🎉</h1>
        <p class="step-desc">Your account is ready. Head to the dashboard to see your server.</p>
        <div class="step-actions">
          <BaseButton variant="primary" :disabled="finishing" style="width:100%; justify-content:center" @click="finish">
            {{ finishing ? 'Finishing…' : 'Go to dashboard' }}
          </BaseButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi, settingsApi, type TOTPSetupResponse } from '@/api'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import QRCode from 'qrcode'

const router = useRouter()
const auth = useAuthStore()

const STEPS = [
  { title: 'Welcome' },
  { title: 'Secure your account' },
  { title: 'Two-factor auth' },
  { title: 'All set' },
]
const step = ref(0)

function next() {
  if (step.value < STEPS.length - 1) step.value++
}

// Step 1: account
const currentPassword = ref('')
const newUsername = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const accountError = ref('')
const accountLoading = ref(false)

async function saveAccount() {
  accountError.value = ''
  if (!currentPassword.value) {
    accountError.value = 'Enter your current password.'
    return
  }
  if (!newUsername.value && !newPassword.value) {
    accountError.value = 'Set a new username or password, or skip for now.'
    return
  }
  if (newPassword.value && newPassword.value !== confirmPassword.value) {
    accountError.value = 'Passwords do not match.'
    return
  }
  if (newPassword.value && newPassword.value.length < 8) {
    accountError.value = 'New password must be at least 8 characters.'
    return
  }
  accountLoading.value = true
  try {
    await settingsApi.changeProfile(
      currentPassword.value,
      newUsername.value || undefined,
      newPassword.value || undefined,
    )
    await auth.loadUser()
    next()
  } catch (e: any) {
    accountError.value = e.response?.data?.detail || 'Failed to save changes.'
  } finally {
    accountLoading.value = false
  }
}

// Step 2: 2FA
const setupData = ref<TOTPSetupResponse | null>(null)
const setupLoading = ref(false)
const qrCanvas = ref<HTMLCanvasElement | null>(null)
const confirmCode = ref('')
const totpError = ref('')
const totpLoading = ref(false)

async function startTotpSetup() {
  setupLoading.value = true
  totpError.value = ''
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
  } catch (e: any) {
    totpError.value = e.response?.data?.detail || 'Failed to start 2FA setup.'
  } finally {
    setupLoading.value = false
  }
}

async function confirmTotp() {
  if (confirmCode.value.length !== 6) return
  totpError.value = ''
  totpLoading.value = true
  try {
    await settingsApi.enable2fa(confirmCode.value)
    await auth.loadUser()
    next()
  } catch (e: any) {
    totpError.value = e.response?.data?.detail || 'Invalid code.'
    confirmCode.value = ''
  } finally {
    totpLoading.value = false
  }
}

// Finish
const finishing = ref(false)
async function finish() {
  finishing.value = true
  try {
    await authApi.completeOnboarding()
    await auth.loadUser()
    router.push('/')
  } finally {
    finishing.value = false
  }
}
</script>

<style scoped>
.onboarding-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  padding: 20px;
}

.onboarding-box {
  width: 100%;
  max-width: 380px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.onboarding-logo {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 12px;
}
.bracket { color: var(--fg-dim); }
.accent { color: var(--accent); }

.step-track { display: flex; gap: 6px; margin-bottom: 6px; }
.step-dot {
  width: 28px;
  height: 3px;
  border-radius: 2px;
  background: var(--border);
  transition: background var(--transition);
}
.step-dot.done { background: var(--accent); opacity: 0.5; }
.step-dot.active { background: var(--accent); }

.step-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-bottom: 18px;
}

.step-panel {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
}

.step-heading { font-size: 16px; font-weight: 700; margin: 0; }
.step-desc { font-size: 12px; color: var(--fg-muted); line-height: 1.5; margin: 0; }
.sub-label { font-size: 11px; color: var(--fg-muted); margin: 0 0 8px; }

.step-actions { display: flex; gap: 10px; align-items: center; margin-top: 4px; }

.skip-btn {
  background: none;
  border: none;
  color: var(--fg-muted);
  font-family: var(--font);
  font-size: 11px;
  cursor: pointer;
  padding: 0;
  transition: color var(--transition);
  white-space: nowrap;
}
.skip-btn:hover { color: var(--accent); }

.setup-flow { display: flex; flex-direction: column; gap: 16px; }
.qr-block { display: flex; flex-direction: column; align-items: center; gap: 8px; text-align: center; }
.qr-canvas { border-radius: var(--radius-sm); }
.manual-entry { font-size: 10px; color: var(--fg-dim); }
.manual-entry summary { cursor: pointer; }
.secret-key { display: block; margin-top: 6px; word-break: break-all; font-size: 10px; color: var(--fg-muted); }
.confirm-form { display: flex; flex-direction: column; gap: 10px; }

.error-msg { font-size: 11px; color: var(--danger); padding: 6px 10px; background: var(--danger-dim); border-radius: var(--radius-sm); border: 1px solid rgba(255,68,68,0.2); }
.success-msg { font-size: 11px; color: var(--accent); padding: 6px 10px; background: var(--accent-dim); border-radius: var(--radius-sm); border: 1px solid var(--accent-border); }
</style>
