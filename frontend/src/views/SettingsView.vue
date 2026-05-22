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
              type="button"
              :class="['theme-btn', { active: theme.theme === 'dark' }]"
              @click="theme.setTheme('dark')"
            >◑ Dark</button>
            <button
              type="button"
              :class="['theme-btn', { active: theme.theme === 'light' }]"
              @click="theme.setTheme('light')"
            >○ Light</button>
            <button
              type="button"
              :class="['theme-btn', { active: theme.theme === 'auto' }]"
              @click="theme.setTheme('auto')"
            >⟳ Auto</button>
          </div>
        </div>

        <!-- Stylistic Settings Section -->
        <div class="section">
          <div class="section-header stylistic-header">
            <span class="section-title">Stylistic Settings</span>
            <span :class="['badge', theme.hasStyleOverrides ? 'badge-green' : 'badge-gray']">
              {{ theme.hasStyleOverrides ? 'customized' : 'defaults' }}
            </span>
          </div>
          <p class="section-desc">
            Adjust visual styling only. Theme mode stays unchanged, and resetting here restores
            colors and typography without affecting any non-stylistic settings.
          </p>

          <div class="style-grid">
            <label v-for="field in colorFields" :key="field.key" class="style-field">
              <span class="style-lbl">{{ field.label }}</span>
              <div class="color-control">
                <input
                  type="color"
                  class="color-picker"
                  :value="theme.resolvedStyleSettings[field.key]"
                  @input="updateColorSetting(field.key, ($event.target as HTMLInputElement).value)"
                />
                <code class="color-value">{{ theme.resolvedStyleSettings[field.key] }}</code>
              </div>
            </label>
          </div>

          <div class="style-toggles">
            <div class="toggle-setting-row">
              <div>
                <span class="style-lbl">High contrast mode</span>
                <p class="style-toggle-desc">
                  Brighter text and darker backgrounds for night viewing.
                </p>
              </div>
              <button
                type="button"
                :class="['theme-btn', 'contrast-btn', { active: isHighContrast }]"
                @click="updateHighContrast(!isHighContrast)"
              >
                {{ isHighContrast ? 'on' : 'off' }}
              </button>
            </div>

            <div class="toggle-setting-row">
              <div>
                <span class="style-lbl">Animation level</span>
                <p class="style-toggle-desc">
                  Control how much motion is used for buttons, hovers, and page switches.
                </p>
              </div>
              <div class="theme-toggle-row animation-toggle-row">
                <button
                  type="button"
                  :class="['theme-btn', { active: selectedAnimationLevel === 'all' }]"
                  @click="updateAnimationLevel('all')"
                >
                  All Animations
                </button>
                <button
                  type="button"
                  :class="['theme-btn', { active: selectedAnimationLevel === 'reduced' }]"
                  @click="updateAnimationLevel('reduced')"
                >
                  Reduced Animations
                </button>
                <button
                  type="button"
                  :class="['theme-btn', { active: selectedAnimationLevel === 'none' }]"
                  @click="updateAnimationLevel('none')"
                >
                  No Animations
                </button>
              </div>
            </div>
          </div>

          <div class="typography-grid">
            <label class="style-field style-field-wide">
              <span class="style-lbl">Font</span>
              <select
                class="style-select"
                :value="theme.resolvedStyleSettings.font"
                @change="updateFont(($event.target as HTMLSelectElement).value)"
              >
                <option v-for="option in fontOptions" :key="option.label" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </label>

            <label class="style-field style-field-wide">
              <span class="style-lbl">Base font size</span>
              <div class="font-size-control">
                <input
                  type="range"
                  class="interval-slider"
                  :value="theme.resolvedStyleSettings.fontSize"
                  min="10"
                  max="18"
                  step="1"
                  @input="updateFontSize(parseInt(($event.target as HTMLInputElement).value))"
                />
                <span class="font-size-value">{{ theme.resolvedStyleSettings.fontSize }}px</span>
              </div>
            </label>
          </div>

          <div class="style-reset-row">
            <BaseButton
              variant="ghost"
              :disabled="!theme.hasStyleOverrides"
              @click="resetStyleSettings"
            >
              Return stylistic settings to defaults
            </BaseButton>
          </div>
        </div>

        <!-- Background Section -->
        <div class="section">
          <div class="section-header">
            <span class="section-title">Backgrounds</span>
            <span :class="['badge', bg.hasCustomBg ? 'badge-green' : 'badge-gray']">
              {{ bg.hasCustomBg ? 'customized' : 'defaults' }}
            </span>
          </div>
          <p class="section-desc">
            Set a gradient, image, or solid color behind the app and login screen. Blur creates a
            frosted-glass depth effect.
          </p>

          <!-- App background -->
          <div class="bg-block">
            <div class="bg-block-head">
              <span class="style-lbl">App Background</span>
              <button v-if="bg.isCustom(bg.appBg) || bg.appBgImage" class="reset-sm" @click="bg.resetAppBg()">reset</button>
            </div>

            <div class="bg-type-row">
              <button
                v-for="t in bgTypes"
                :key="t.key"
                :class="['type-btn', { active: bg.appBg.type === t.key }]"
                @click="bg.setAppBg({ type: t.key })"
              >{{ t.label }}</button>
            </div>

            <template v-if="bg.appBg.type === 'gradient'">
              <div class="gradient-preview" :style="{ background: bg.gradientPreview(bg.appBg) }" />
              <div class="style-grid">
                <label class="style-field">
                  <span class="style-lbl">From</span>
                  <div class="color-control">
                    <input type="color" class="color-picker" :value="bg.appBg.gradientStart"
                      @input="bg.setAppBg({ gradientStart: ($event.target as HTMLInputElement).value })" />
                    <code class="color-value">{{ bg.appBg.gradientStart }}</code>
                  </div>
                </label>
                <label class="style-field">
                  <span class="style-lbl">To</span>
                  <div class="color-control">
                    <input type="color" class="color-picker" :value="bg.appBg.gradientEnd"
                      @input="bg.setAppBg({ gradientEnd: ($event.target as HTMLInputElement).value })" />
                    <code class="color-value">{{ bg.appBg.gradientEnd }}</code>
                  </div>
                </label>
              </div>
              <label class="style-field">
                <span class="style-lbl">Angle — {{ bg.appBg.gradientAngle }}°</span>
                <input type="range" class="interval-slider" min="0" max="360" step="5"
                  :value="bg.appBg.gradientAngle"
                  @input="bg.setAppBg({ gradientAngle: parseInt(($event.target as HTMLInputElement).value) })" />
              </label>
            </template>

            <template v-if="bg.appBg.type === 'image'">
              <div v-if="bg.appBgImage" class="img-preview-row">
                <img :src="bg.appBgImage" class="img-thumb" alt="App background" />
                <button class="reset-sm danger-sm" @click="bg.setAppBgImage(null)">remove</button>
              </div>
              <div v-else class="upload-drop" @click="triggerUpload('app')">
                <span>click to upload image</span>
                <span class="upload-hint">JPG, PNG, WEBP · max 3 MB</span>
              </div>
              <input ref="appFileInput" type="file" accept="image/*" class="file-hidden"
                @change="handleUpload('app', $event)" />
              <p v-if="uploadError === 'app'" class="upload-error">Image too large — max 3 MB</p>
            </template>

            <label v-if="bg.appBg.type !== 'color'" class="style-field">
              <span class="style-lbl">Background blur — {{ bg.appBg.blur }}px</span>
              <input type="range" class="interval-slider" min="0" max="20" step="1"
                :value="bg.appBg.blur"
                @input="bg.setAppBg({ blur: parseInt(($event.target as HTMLInputElement).value) })" />
            </label>
          </div>

          <div class="bg-divider" />

          <!-- Login background -->
          <div class="bg-block">
            <div class="bg-block-head">
              <span class="style-lbl">Login Screen Background</span>
              <button v-if="bg.isCustom(bg.loginBg) || bg.loginBgImage" class="reset-sm" @click="bg.resetLoginBg()">reset</button>
            </div>

            <div class="bg-type-row">
              <button
                v-for="t in bgTypes"
                :key="t.key"
                :class="['type-btn', { active: bg.loginBg.type === t.key }]"
                @click="bg.setLoginBg({ type: t.key })"
              >{{ t.label }}</button>
            </div>

            <template v-if="bg.loginBg.type === 'gradient'">
              <div class="gradient-preview" :style="{ background: bg.gradientPreview(bg.loginBg) }" />
              <div class="style-grid">
                <label class="style-field">
                  <span class="style-lbl">From</span>
                  <div class="color-control">
                    <input type="color" class="color-picker" :value="bg.loginBg.gradientStart"
                      @input="bg.setLoginBg({ gradientStart: ($event.target as HTMLInputElement).value })" />
                    <code class="color-value">{{ bg.loginBg.gradientStart }}</code>
                  </div>
                </label>
                <label class="style-field">
                  <span class="style-lbl">To</span>
                  <div class="color-control">
                    <input type="color" class="color-picker" :value="bg.loginBg.gradientEnd"
                      @input="bg.setLoginBg({ gradientEnd: ($event.target as HTMLInputElement).value })" />
                    <code class="color-value">{{ bg.loginBg.gradientEnd }}</code>
                  </div>
                </label>
              </div>
              <label class="style-field">
                <span class="style-lbl">Angle — {{ bg.loginBg.gradientAngle }}°</span>
                <input type="range" class="interval-slider" min="0" max="360" step="5"
                  :value="bg.loginBg.gradientAngle"
                  @input="bg.setLoginBg({ gradientAngle: parseInt(($event.target as HTMLInputElement).value) })" />
              </label>
            </template>

            <template v-if="bg.loginBg.type === 'image'">
              <div v-if="bg.loginBgImage" class="img-preview-row">
                <img :src="bg.loginBgImage" class="img-thumb" alt="Login background" />
                <button class="reset-sm danger-sm" @click="bg.setLoginBgImage(null)">remove</button>
              </div>
              <div v-else class="upload-drop" @click="triggerUpload('login')">
                <span>click to upload image</span>
                <span class="upload-hint">JPG, PNG, WEBP · max 3 MB</span>
              </div>
              <input ref="loginFileInput" type="file" accept="image/*" class="file-hidden"
                @change="handleUpload('login', $event)" />
              <p v-if="uploadError === 'login'" class="upload-error">Image too large — max 3 MB</p>
            </template>

            <label v-if="bg.loginBg.type !== 'color'" class="style-field">
              <span class="style-lbl">Background blur — {{ bg.loginBg.blur }}px</span>
              <input type="range" class="interval-slider" min="0" max="20" step="1"
                :value="bg.loginBg.blur"
                @input="bg.setLoginBg({ blur: parseInt(($event.target as HTMLInputElement).value) })" />
            </label>
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
              type="button"
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

          <div class="disk-scope">
            <span class="style-lbl">Disk alert source</span>
            <div class="theme-toggle-row disk-scope-toggle">
              <button
                type="button"
                :class="['theme-btn', { active: alerts.diskScope === 'physical' }]"
                @click="alerts.setDiskScope('physical')"
              >
                Actual disks only
              </button>
              <button
                type="button"
                :class="['theme-btn', { active: alerts.diskScope === 'all' }]"
                @click="alerts.setDiskScope('all')"
              >
                All mounts
              </button>
            </div>
            <p class="disk-scope-note">
              Default is actual storage devices only, so virtual mounts like /snap do not trigger
              disk alerts unless you include all mounts.
            </p>
          </div>

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

        <div class="section">
          <div class="section-header">
            <span class="section-title">Version & Updates</span>
            <span
              :class="[
                'badge',
                versionInfo?.update_available ? 'badge-green' : 'badge-gray',
              ]"
            >
              {{
                versionInfo?.update_in_progress
                  ? 'installing'
                  : versionInfo?.update_available
                    ? 'update available'
                    : 'up to date'
              }}
            </span>
          </div>
          <p class="section-desc">
            CarbonPanel checks GitHub for new releases every day. You can also check manually and
            start an interactive update from here.
          </p>

          <div class="version-grid">
            <div class="info-row">
              <span class="info-lbl">Current</span>
              <span class="info-val">{{ versionInfo?.current_version ?? 'unknown' }}</span>
            </div>
            <div class="info-row">
              <span class="info-lbl">Latest</span>
              <span class="info-val">{{ versionInfo?.latest_version ?? 'not checked yet' }}</span>
            </div>
            <div class="info-row">
              <span class="info-lbl">Checked</span>
              <span class="info-val text-muted">{{ versionInfo?.checked_at ?? 'never' }}</span>
            </div>
            <div v-if="versionInfo?.error" class="info-row">
              <span class="info-lbl">Status</span>
              <span class="info-val text-muted">{{ versionInfo.error }}</span>
            </div>
          </div>

          <div class="version-actions">
            <BaseButton variant="ghost" :disabled="versionActionLoading" @click="checkForUpdates">
              {{ versionActionLoading ? 'Working…' : 'Check for Updates' }}
            </BaseButton>

            <!-- Docker mode: show pull command instead of install button -->
            <template v-if="versionInfo?.deployment_type === 'docker'">
              <div v-if="versionInfo?.update_available" class="docker-update-block">
                <span class="docker-update-label">Pull the latest image to update:</span>
                <div class="docker-pull-row">
                  <code class="docker-pull-cmd">{{ versionInfo.docker_pull_cmd }}</code>
                  <button class="copy-btn" @click="copyPullCmd(versionInfo.docker_pull_cmd!)">
                    {{ copied ? 'copied!' : 'copy' }}
                  </button>
                </div>
              </div>
            </template>

            <!-- Self-hosted mode: show install button -->
            <template v-else>
              <BaseButton
                variant="primary"
                :disabled="
                  versionActionLoading ||
                  !versionInfo?.update_available ||
                  !!versionInfo?.update_in_progress
                "
                @click="installUpdate"
              >
                {{
                  versionInfo?.update_in_progress
                    ? 'Installing…'
                    : versionActionLoading
                      ? 'Working…'
                      : 'Install Update'
                }}
              </BaseButton>
            </template>

            <a
              v-if="versionInfo?.notes_url || versionInfo?.release_url"
              class="version-link"
              :href="versionInfo?.notes_url || versionInfo?.release_url || '#'"
              target="_blank"
              rel="noreferrer"
            >
              View Release Notes
            </a>
          </div>

          <p v-if="versionSuccess" class="success-msg">{{ versionSuccess }}</p>
          <p v-if="versionError" class="error-msg">{{ versionError }}</p>
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
            <button type="button" class="toggle-link" @click="showChangeCreds = !showChangeCreds">
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
import { ref, computed, nextTick, onMounted } from 'vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import { useAuthStore } from '@/stores/auth'
import { useMetricsStore } from '@/stores/metrics'
import { useThemeStore, type AnimationLevel } from '@/stores/theme'
import { useAlertsStore } from '@/stores/alerts'
import { useBackgroundStore } from '@/stores/background'
import { useWebSocket } from '@/composables/useWebSocket'
import { settingsApi, systemApi, type SystemVersionResponse } from '@/api'
import QRCode from 'qrcode'

const auth = useAuthStore()
const metrics = useMetricsStore()
const theme = useThemeStore()
const alerts = useAlertsStore()
const bg = useBackgroundStore()
const { sendInterval } = useWebSocket()

const bgTypes = [
  { key: 'color' as const, label: 'Color' },
  { key: 'gradient' as const, label: 'Gradient' },
  { key: 'image' as const, label: 'Image' },
]

const appFileInput = ref<HTMLInputElement | null>(null)
const loginFileInput = ref<HTMLInputElement | null>(null)
const uploadError = ref<'app' | 'login' | null>(null)

function triggerUpload(target: 'app' | 'login') {
  uploadError.value = null
  if (target === 'app') appFileInput.value?.click()
  else loginFileInput.value?.click()
}

function handleUpload(target: 'app' | 'login', event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (file.size > 3 * 1024 * 1024) {
    uploadError.value = target
    ;(event.target as HTMLInputElement).value = ''
    return
  }
  uploadError.value = null
  const reader = new FileReader()
  reader.onload = () => {
    const dataUrl = reader.result as string
    if (target === 'app') bg.setAppBgImage(dataUrl)
    else bg.setLoginBgImage(dataUrl)
  }
  reader.readAsDataURL(file)
  ;(event.target as HTMLInputElement).value = ''
}

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

const colorFields = [
  { key: 'bg', label: 'App background' },
  { key: 'bgCard', label: 'Card background' },
  { key: 'bgInput', label: 'Input background' },
  { key: 'border', label: 'Border' },
  { key: 'fg', label: 'Primary text' },
  { key: 'fgMuted', label: 'Muted text' },
  { key: 'fgDim', label: 'Dim text' },
  { key: 'accent', label: 'Accent' },
  { key: 'warning', label: 'Warning' },
  { key: 'danger', label: 'Danger' },
  { key: 'info', label: 'Info' },
] as const

type StyleColorKey = typeof colorFields[number]['key']

const fontOptions = [
  { label: 'JetBrains Mono', value: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace" },
  { label: 'Fira Code', value: "'Fira Code', 'JetBrains Mono', 'Cascadia Code', monospace" },
  { label: 'Cascadia Code', value: "'Cascadia Code', 'JetBrains Mono', 'Fira Code', monospace" },
  { label: 'System Sans', value: "Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" },
  { label: 'System Serif', value: "Georgia, 'Times New Roman', serif" },
]

const intervalLabel = computed(() => {
  const v = metrics.updateInterval
  return v < 1 ? `${v.toFixed(1)}s` : `${v % 1 === 0 ? v.toFixed(0) : v.toFixed(1)}s`
})

const isHighContrast = computed(() => theme.resolvedStyleSettings.highContrast)
const selectedAnimationLevel = computed<AnimationLevel>(
  () => theme.resolvedStyleSettings.animationLevel,
)

function onSliderInput(e: Event) {
  const val = parseFloat((e.target as HTMLInputElement).value)
  metrics.setUpdateInterval(val)
  sendInterval(val)
}

function applyPreset(val: number) {
  metrics.setUpdateInterval(val)
  sendInterval(val)
}

function updateColorSetting(key: StyleColorKey, value: string) {
  theme.setStyleSetting(key, value)
}

function updateHighContrast(value: boolean) {
  theme.setStyleSetting('highContrast', value)
}

function updateAnimationLevel(value: 'all' | 'reduced' | 'none') {
  theme.setStyleSetting('animationLevel', value)
}

function updateFont(value: string) {
  theme.setStyleSetting('font', value)
}

function updateFontSize(value: number) {
  theme.setStyleSetting('fontSize', Math.min(18, Math.max(10, value)))
}

function resetStyleSettings() {
  theme.resetStyleSettings()
}

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

const versionInfo = ref<SystemVersionResponse | null>(null)
const versionActionLoading = ref(false)
const versionError = ref('')
const versionSuccess = ref('')
const copied = ref(false)

function copyPullCmd(cmd: string) {
  navigator.clipboard.writeText(cmd).then(() => {
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  })
}

async function loadVersionInfo() {
  versionError.value = ''

  try {
    const res = await systemApi.version()
    versionInfo.value = res.data
  } catch (e: any) {
    versionError.value = e.response?.data?.detail || 'Failed to load version status'
  }
}

async function checkForUpdates() {
  versionActionLoading.value = true
  versionError.value = ''
  versionSuccess.value = ''

  try {
    await systemApi.checkUpdates()
    versionSuccess.value = 'Update check started. Refreshing status...'
    await wait(1200)
    await loadVersionInfo()
  } catch (e: any) {
    versionError.value = e.response?.data?.detail || 'Failed to start update check'
  } finally {
    versionActionLoading.value = false
  }
}

async function installUpdate() {
  if (!versionInfo.value?.update_available || versionInfo.value.update_in_progress) return

  const targetVersion = versionInfo.value.latest_version ?? 'the latest version'
  const confirmed = window.confirm(
    `Install CarbonPanel ${targetVersion} now? The app will restart automatically during the update.`,
  )

  if (!confirmed) return

  versionActionLoading.value = true
  versionError.value = ''
  versionSuccess.value = ''

  try {
    await systemApi.installUpdate()
    versionSuccess.value =
      'Update installation started. CarbonPanel will restart automatically. Refresh this page in about a minute.'
    await wait(1200)
    await loadVersionInfo()
  } catch (e: any) {
    versionError.value = e.response?.data?.detail || 'Failed to start update installation'
  } finally {
    versionActionLoading.value = false
  }
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

onMounted(() => {
  void loadVersionInfo()
})
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

.stylistic-header {
  justify-content: space-between;
  flex-wrap: wrap;
}

.style-grid,
.typography-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.style-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.style-field-wide {
  grid-column: 1 / -1;
}

.style-lbl {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--fg-dim);
}

.color-control,
.font-size-control {
  display: flex;
  align-items: center;
  gap: 10px;
}

.color-picker {
  width: 42px;
  height: 28px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: transparent;
  cursor: pointer;
}

.color-value {
  font-size: 11px;
  color: var(--fg-muted);
}

.style-select {
  width: 100%;
  background: var(--bg-input);
  border: 1px solid var(--border);
  color: var(--fg);
  font-family: var(--font);
  font-size: 11px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  outline: none;
}

.style-select:focus {
  border-color: var(--accent);
}

.font-size-value {
  min-width: 38px;
  text-align: right;
  font-size: 11px;
  color: var(--fg-muted);
}

.style-toggles {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.toggle-setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

.style-toggle-desc {
  margin-top: 4px;
  font-size: 11px;
  color: var(--fg-muted);
  line-height: 1.5;
}

.contrast-btn {
  flex: 0 0 auto;
  min-width: 72px;
  padding-inline: 14px;
}

.animation-toggle-row {
  width: 100%;
}

.style-reset-row {
  display: flex;
  justify-content: flex-start;
}

.version-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.version-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.version-link {
  color: var(--accent);
  text-decoration: none;
  font-size: 11px;
  transition: color var(--transition);
}

.version-link:hover {
  color: var(--fg);
}

.docker-update-block {
  display: flex; flex-direction: column; gap: 6px;
  padding: 10px 12px;
  background: var(--accent-dim);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-sm);
}

.docker-update-label { font-size: 10px; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em; }

.docker-pull-row { display: flex; align-items: center; gap: 8px; }

.docker-pull-cmd {
  flex: 1; font-family: var(--font); font-size: 11px; color: var(--fg);
  background: var(--bg-input); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 5px 8px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.copy-btn {
  flex-shrink: 0; background: none; border: 1px solid var(--accent-border);
  color: var(--accent); font-family: var(--font); font-size: 10px;
  padding: 4px 10px; border-radius: 3px; cursor: pointer;
  transition: all var(--transition);
}
.copy-btn:hover { background: var(--accent-dim); }

.disk-scope {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.disk-scope-toggle {
  width: 100%;
}

.disk-scope-note {
  font-size: 11px;
  color: var(--fg-muted);
  line-height: 1.5;
}

@media (max-width: 640px) {
  .style-grid,
  .typography-grid {
    grid-template-columns: 1fr;
  }

  .toggle-setting-row {
    flex-direction: column;
    align-items: stretch;
  }
}

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

/* Background settings */
.bg-block { display: flex; flex-direction: column; gap: 10px; }
.bg-block-head { display: flex; align-items: center; justify-content: space-between; }
.bg-divider { height: 1px; background: var(--border-subtle); margin: 4px 0; }

.bg-type-row { display: flex; gap: 6px; }
.type-btn {
  flex: 1; background: none; border: 1px solid var(--border); color: var(--fg-dim);
  font-family: var(--font); font-size: 11px; padding: 6px 0; border-radius: var(--radius-sm);
  cursor: pointer; transition: all var(--transition); text-align: center;
}
.type-btn:hover:not(.active) { border-color: var(--fg-dim); color: var(--fg-muted); }
.type-btn.active { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }

.gradient-preview {
  height: 40px; border-radius: var(--radius-sm); border: 1px solid var(--border);
  transition: all var(--transition);
}

.upload-drop {
  border: 1px dashed var(--border); border-radius: var(--radius-sm);
  padding: 20px; display: flex; flex-direction: column; align-items: center; gap: 4px;
  cursor: pointer; transition: all var(--transition); color: var(--fg-muted); font-size: 11px;
}
.upload-drop:hover { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }
.upload-hint { font-size: 10px; color: var(--fg-dim); }

.img-preview-row { display: flex; align-items: center; gap: 10px; }
.img-thumb {
  width: 80px; height: 48px; object-fit: cover; border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}

.file-hidden { display: none; }

.reset-sm {
  background: none; border: 1px solid var(--border); color: var(--fg-dim);
  font-family: var(--font); font-size: 10px; padding: 3px 8px; border-radius: 3px;
  cursor: pointer; transition: all var(--transition);
}
.reset-sm:hover { border-color: var(--fg-dim); color: var(--fg); }
.danger-sm { border-color: rgba(255,68,68,0.3); color: var(--danger); }
.danger-sm:hover { background: var(--danger-dim); border-color: rgba(255,68,68,0.5); }

.upload-error { font-size: 11px; color: var(--danger); }
</style>
