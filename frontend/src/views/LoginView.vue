<template>
  <div class="login-page" :style="loginPageStyle">
    <div v-if="bg.loginBgLayerVisible" class="login-bg-layer" :style="bg.loginBgLayerStyle" />
    <div class="login-box">
      <div class="login-logo">
        <img src="/carbonpanel-mark.svg" width="40" height="40" alt="" />
        <span>Carbon<span class="accent">Panel</span></span>
      </div>
      <p class="login-sub">Server monitoring</p>

      <!-- Step 1: Username + Password -->
      <form v-if="step === 1" class="login-form" @submit.prevent="handleLogin">
        <BaseInput
          v-model="username"
          label="Username"
          id="username"
          placeholder="admin"
          autocomplete="username"
          autofocus
        />
        <BaseInput
          v-model="password"
          label="Password"
          id="password"
          type="password"
          placeholder="••••••••"
          autocomplete="current-password"
        />
        <p v-if="error" class="error-msg">{{ error }}</p>
        <BaseButton variant="primary" :disabled="loading" style="width:100%; justify-content:center">
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </BaseButton>
        <template v-if="passkeys.available">
          <div class="login-divider"><span>or</span></div>
          <button type="button" class="passkey-btn" :disabled="passkeyLoading" @click="handlePasskeyLogin">
            {{ passkeyLoading ? 'Waiting for passkey…' : 'Sign in with a passkey' }}
          </button>
        </template>
      </form>

      <!-- Step 2: TOTP -->
      <form v-else class="login-form" @submit.prevent="handleTotp">
        <div class="totp-info">
          <span class="badge badge-green">2FA required</span>
          <p class="totp-hint">Enter the 6-digit code from your authenticator app.</p>
        </div>
        <BaseInput
          v-model="totpCode"
          label="Authenticator Code"
          id="totp"
          placeholder="000000"
          inputmode="numeric"
          maxlength="6"
          autocomplete="one-time-code"
          autofocus
        />
        <p v-if="error" class="error-msg">{{ error }}</p>
        <div class="totp-actions">
          <button type="button" class="back-btn" @click="step = 1; error = ''">← back</button>
          <BaseButton variant="primary" :disabled="loading || totpCode.length !== 6" style="flex:1; justify-content:center">
            {{ loading ? 'Verifying…' : 'Verify' }}
          </BaseButton>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useBackgroundStore } from '@/stores/background'
import { authApi, passkeysApi } from '@/api'
import { getPasskey, passkeyAvailability } from '@/utils/passkeys'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const router = useRouter()
const auth = useAuthStore()
const bg = useBackgroundStore()

const loginPageStyle = computed(() => ({
  background: bg.loginBgLayerVisible ? 'transparent' : undefined,
}))

const step = ref<1 | 2>(1)
const username = ref('')
const password = ref('')
const totpCode = ref('')
const sessionToken = ref('')
const error = ref('')
const loading = ref(false)
const passkeyLoading = ref(false)
const passkeys = passkeyAvailability()

// Normalize pasted codes and auto-submit only a complete numeric token.
watch(totpCode, (value) => {
  const digits = value.replace(/\D/g, '').slice(0, 6)
  if (digits !== value) {
    totpCode.value = digits
    return
  }
  if (digits.length === 6 && !loading.value) void handleTotp()
})

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const res = await authApi.login(username.value, password.value)
    if (res.data.totp_required) {
      sessionToken.value = res.data.session_token!
      step.value = 2
    } else {
      await auth.loadUser()
      router.push('/')
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Login failed'
  } finally {
    loading.value = false
  }
}

async function handleTotp() {
  if (!/^\d{6}$/.test(totpCode.value) || loading.value) return
  error.value = ''
  loading.value = true
  try {
    await authApi.loginTotp(sessionToken.value, totpCode.value)
    await auth.loadUser()
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Invalid code'
    totpCode.value = ''
  } finally {
    loading.value = false
  }
}

async function handlePasskeyLogin() {
  if (passkeyLoading.value) return
  error.value = ''
  passkeyLoading.value = true
  try {
    const { data } = await passkeysApi.loginBegin()
    const credential = await getPasskey(data.public_key)
    await passkeysApi.loginComplete(data.challenge_id, credential)
    await auth.loadUser()
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || (
      e.name === 'NotAllowedError'
        ? 'Passkey sign-in was cancelled or no matching passkey was found.'
        : e.message || 'Passkey sign-in failed'
    )
  } finally {
    passkeyLoading.value = false
  }
}
</script>

<style scoped>
.login-page {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.login-bg-layer {
  position: absolute;
  inset: -30px;
  z-index: 0;
  background-size: cover;
  background-position: center;
}

.login-box {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 340px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.login-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 2px;
}
.bracket { color: var(--fg-dim); }
.accent { color: var(--accent); }
.login-sub { font-size: 11px; color: var(--fg-dim); margin-bottom: 24px; }

.login-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
}

.totp-info { display: flex; flex-direction: column; gap: 6px; }
.totp-hint { font-size: 11px; color: var(--fg-muted); }

.error-msg { font-size: 11px; color: var(--danger); padding: 6px 10px; background: var(--danger-dim); border-radius: var(--radius-sm); border: 1px solid rgba(255,68,68,0.2); }

.login-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--fg-dim);
  font-size: 10px;
}
.login-divider::before, .login-divider::after {
  content: '';
  height: 1px;
  flex: 1;
  background: var(--border);
}
.passkey-btn {
  width: 100%;
  padding: 9px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--fg-muted);
  font-family: var(--font);
  font-size: 11px;
  cursor: pointer;
  transition: all var(--transition);
}
.passkey-btn:hover:not(:disabled) {
  border-color: var(--accent-border);
  color: var(--accent);
  background: var(--accent-dim);
}
.passkey-btn:disabled { opacity: 0.5; cursor: default; }

.totp-actions { display: flex; gap: 10px; align-items: center; }
.back-btn {
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
.back-btn:hover { color: var(--accent); }
</style>
