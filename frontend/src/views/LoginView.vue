<template>
  <div class="login-page" :style="loginPageStyle">
    <div v-if="bg.loginBgLayerVisible" class="login-bg-layer" :style="bg.loginBgLayerStyle" />
    <div class="login-box">
      <div class="login-logo">
        <span class="bracket">[</span>Carbon<span class="accent">Panel</span><span class="bracket">]</span>
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
        <button type="button" class="passkey-btn" :disabled="pkLoading" @click="handlePasskey">
          {{ pkLoading ? 'Waiting for key…' : '🔑 Sign in with passkey' }}
        </button>
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

// Auto-submit TOTP when 6 digits entered
watch(totpCode, (v) => { if (v.length === 6) handleTotp() })

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

const pkLoading = ref(false)

function b64urlToBuffer(b64: string): ArrayBuffer {
  const bin = atob(b64.replace(/-/g, '+').replace(/_/g, '/'))
  const buf = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i)
  return buf.buffer
}

function bufferToB64url(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf)
  let bin = ''
  for (let i = 0; i < bytes.byteLength; i++) bin += String.fromCharCode(bytes[i])
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
}

async function handlePasskey() {
  if (!username.value.trim()) {
    error.value = 'Enter your username first.'
    return
  }
  if (!window.isSecureContext || !navigator.credentials) {
    error.value = 'Passkeys require HTTPS. Access this panel over HTTPS or from localhost.'
    return
  }
  error.value = ''
  pkLoading.value = true
  try {
    const { data: opts } = await passkeysApi.loginBegin(username.value.trim())
    const sessionId = opts.session_id as string
    const pubKeyOpts: PublicKeyCredentialRequestOptions = {
      ...(opts as any),
      challenge: b64urlToBuffer((opts as any).challenge),
      allowCredentials: ((opts as any).allowCredentials || []).map((c: any) => ({
        ...c,
        id: b64urlToBuffer(c.id),
      })),
    }
    const cred = await navigator.credentials.get({ publicKey: pubKeyOpts }) as PublicKeyCredential
    if (!cred) throw new Error('No credential returned')
    const response = cred.response as AuthenticatorAssertionResponse
    const credJson = {
      id: cred.id,
      rawId: bufferToB64url(cred.rawId),
      type: cred.type,
      response: {
        clientDataJSON: bufferToB64url(response.clientDataJSON),
        authenticatorData: bufferToB64url(response.authenticatorData),
        signature: bufferToB64url(response.signature),
        userHandle: response.userHandle ? bufferToB64url(response.userHandle) : null,
      },
    }
    await passkeysApi.loginComplete(sessionId, credJson)
    await auth.loadUser()
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || 'Passkey login failed'
  } finally {
    pkLoading.value = false
  }
}

async function handleTotp() {
  if (totpCode.value.length !== 6) return
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
</script>

<style scoped>
.login-page {
  min-height: 100vh;
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
}

.login-box {
  width: 100%;
  max-width: 340px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.login-logo {
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

.passkey-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-muted);
  font-family: var(--font);
  font-size: 11px;
  padding: 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  width: 100%;
  text-align: center;
  transition: all var(--transition);
}
.passkey-btn:hover:not(:disabled) { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }
.passkey-btn:disabled { opacity: 0.5; cursor: not-allowed; }

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
