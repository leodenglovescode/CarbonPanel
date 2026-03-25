<template>
  <div class="login-page">
    <div class="login-box">
      <div class="login-logo">
        <span class="bracket">[</span>carbon<span class="accent">panel</span><span class="bracket">]</span>
      </div>
      <p class="login-sub">server monitoring</p>

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
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const router = useRouter()
const auth = useAuthStore()

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
      auth.setToken(res.data.access_token!)
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
  if (totpCode.value.length !== 6) return
  error.value = ''
  loading.value = true
  try {
    const res = await authApi.loginTotp(sessionToken.value, totpCode.value)
    auth.setToken(res.data.access_token)
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
