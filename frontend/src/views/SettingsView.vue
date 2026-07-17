<template>
  <div class="settings-page">
    <main ref="mainEl" class="settings-main">
      <div class="settings-container">
        <div class="page-title">
          <router-link to="/" class="back-link">← dashboard</router-link>
          <h1>Settings</h1>
        </div>

        <nav class="settings-nav">
          <button v-for="s in navSections" :key="s.id" class="nav-pill" @click="scrollTo(s.id)">
            {{ s.label }}
          </button>
        </nav>

        <!-- Theme Section -->
        <div id="section-appearance" class="section">
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
        <div id="section-style" class="section">
          <div class="section-header stylistic-header">
            <span class="section-title">Stylistic Settings</span>
            <span :class="['badge', theme.hasStyleOverrides ? 'badge-green' : 'badge-gray']">
              {{ theme.hasStyleOverrides ? 'Customized' : 'Defaults' }}
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
                {{ isHighContrast ? 'On' : 'Off' }}
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
        <div id="section-backgrounds" class="section">
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
              <button v-if="bg.isCustom(bg.appBg) || bg.appBgImage" class="reset-sm" @click="bg.resetAppBg()">Reset</button>
            </div>

            <div class="bg-type-row">
              <button
                v-for="bgType in bgTypes"
                :key="bgType.key"
                :class="['type-btn', { active: bg.appBg.type === bgType.key }]"
                @click="bg.setAppBg({ type: bgType.key })"
              >{{ bgType.label }}</button>
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
                <button class="reset-sm danger-sm" :disabled="uploading === 'app'" @click="removeImage('app')">Remove</button>
              </div>
              <div v-else class="upload-drop" :class="{ disabled: uploading === 'app' }" @click="uploading !== 'app' && triggerUpload('app')">
                <span>{{ uploading === 'app' ? 'Uploading…' : 'Click to upload image' }}</span>
                <span class="upload-hint">JPG, PNG, WEBP · max 20 MB · compressed automatically</span>
              </div>
              <input ref="appFileInput" type="file" accept="image/*" class="file-hidden"
                @change="handleUpload('app', $event)" />
              <p v-if="uploadError === 'app'" class="upload-error">{{ uploadErrorMsg }}</p>
            </template>

            <label v-if="bg.appBg.type !== 'color'" class="style-field">
              <span class="style-lbl">Background blur — {{ bg.appBg.blur }}px</span>
              <input type="range" class="interval-slider" min="0" max="20" step="1"
                :value="bg.appBg.blur"
                @input="bg.setAppBg({ blur: parseInt(($event.target as HTMLInputElement).value) })" />
            </label>

            <label v-if="bg.appBg.type !== 'color'" class="style-field">
              <span class="style-lbl">Background brightness — {{ bg.appBg.brightness }}%</span>
              <input type="range" class="interval-slider" min="30" max="150" step="5"
                :value="bg.appBg.brightness"
                @input="bg.setAppBg({ brightness: parseInt(($event.target as HTMLInputElement).value) })" />
            </label>

            <label v-if="bg.appBg.type !== 'color'" class="style-field">
              <span class="style-lbl">Text contrast overlay — {{ bg.appBg.overlay }}%</span>
              <input type="range" class="interval-slider" min="0" max="80" step="5"
                :value="bg.appBg.overlay"
                @input="bg.setAppBg({ overlay: parseInt(($event.target as HTMLInputElement).value) })" />
              <span class="style-hint">Dims the background so text and controls stay readable. Raise this if a bright image washes out the UI.</span>
            </label>
          </div>

          <div class="bg-divider" />

          <!-- Login background -->
          <div class="bg-block">
            <div class="bg-block-head">
              <span class="style-lbl">Login Screen Background</span>
              <button v-if="bg.isCustom(bg.loginBg) || bg.loginBgImage" class="reset-sm" @click="bg.resetLoginBg()">Reset</button>
            </div>

            <div class="bg-type-row">
              <button
                v-for="bgType in bgTypes"
                :key="bgType.key"
                :class="['type-btn', { active: bg.loginBg.type === bgType.key }]"
                @click="bg.setLoginBg({ type: bgType.key })"
              >{{ bgType.label }}</button>
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
                <button class="reset-sm danger-sm" :disabled="uploading === 'login'" @click="removeImage('login')">Remove</button>
              </div>
              <div v-else class="upload-drop" :class="{ disabled: uploading === 'login' }" @click="uploading !== 'login' && triggerUpload('login')">
                <span>{{ uploading === 'login' ? 'Uploading…' : 'Click to upload image' }}</span>
                <span class="upload-hint">JPG, PNG, WEBP · max 20 MB · compressed automatically</span>
              </div>
              <input ref="loginFileInput" type="file" accept="image/*" class="file-hidden"
                @change="handleUpload('login', $event)" />
              <p v-if="uploadError === 'login'" class="upload-error">{{ uploadErrorMsg }}</p>
            </template>

            <label v-if="bg.loginBg.type !== 'color'" class="style-field">
              <span class="style-lbl">Background blur — {{ bg.loginBg.blur }}px</span>
              <input type="range" class="interval-slider" min="0" max="20" step="1"
                :value="bg.loginBg.blur"
                @input="bg.setLoginBg({ blur: parseInt(($event.target as HTMLInputElement).value) })" />
            </label>

            <label v-if="bg.loginBg.type !== 'color'" class="style-field">
              <span class="style-lbl">Background brightness — {{ bg.loginBg.brightness }}%</span>
              <input type="range" class="interval-slider" min="30" max="150" step="5"
                :value="bg.loginBg.brightness"
                @input="bg.setLoginBg({ brightness: parseInt(($event.target as HTMLInputElement).value) })" />
            </label>

            <label v-if="bg.loginBg.type !== 'color'" class="style-field">
              <span class="style-lbl">Text contrast overlay — {{ bg.loginBg.overlay }}%</span>
              <input type="range" class="interval-slider" min="0" max="80" step="5"
                :value="bg.loginBg.overlay"
                @input="bg.setLoginBg({ overlay: parseInt(($event.target as HTMLInputElement).value) })" />
              <span class="style-hint">Dims the background so the logo and login form stay readable. Raise this if a bright image washes out the text.</span>
            </label>
          </div>
        </div>

        <!-- Display Preferences Section -->
        <div id="section-display" class="section">
          <div class="section-header">
            <span class="section-title">Display Preferences</span>
            <span class="badge badge-gray">Units</span>
          </div>
          <p class="section-desc">Choose how memory and network speed are displayed across the dashboard.</p>

          <div class="display-pref-row">
            <div>
              <span class="style-lbl">RAM unit</span>
              <p class="style-toggle-desc">Show memory values in gigabytes or megabytes.</p>
            </div>
            <div class="theme-toggle-row">
              <button
                type="button"
                :class="['theme-btn', { active: displayPrefs.ramUnit === 'gb' }]"
                @click="displayPrefs.setRamUnit('gb')"
              >GB</button>
              <button
                type="button"
                :class="['theme-btn', { active: displayPrefs.ramUnit === 'mb' }]"
                @click="displayPrefs.setRamUnit('mb')"
              >MB</button>
            </div>
          </div>

          <div class="display-pref-row">
            <div>
              <span class="style-lbl">Network speed unit</span>
              <p class="style-toggle-desc">MB/s = megabytes per second. Mbps = megabits per second (8× larger value).</p>
            </div>
            <div class="theme-toggle-row">
              <button
                type="button"
                :class="['theme-btn', { active: displayPrefs.networkUnit === 'mb_s' }]"
                @click="displayPrefs.setNetworkUnit('mb_s')"
              >MB/s</button>
              <button
                type="button"
                :class="['theme-btn', { active: displayPrefs.networkUnit === 'mbps' }]"
                @click="displayPrefs.setNetworkUnit('mbps')"
              >Mbps</button>
            </div>
          </div>

          <div class="display-pref-row">
            <div>
              <span class="style-lbl">Storage unit</span>
              <p class="style-toggle-desc">GB always shows gigabytes. TB auto switches to terabytes when a disk reaches 1 TB. Always TB forces terabytes everywhere.</p>
            </div>
            <div class="theme-toggle-row">
              <button
                type="button"
                :class="['theme-btn', { active: displayPrefs.storageUnit === 'gb' }]"
                @click="displayPrefs.setStorageUnit('gb')"
              >GB</button>
              <button
                type="button"
                :class="['theme-btn', { active: displayPrefs.storageUnit === 'auto_tb' }]"
                @click="displayPrefs.setStorageUnit('auto_tb')"
              >TB auto</button>
              <button
                type="button"
                :class="['theme-btn', { active: displayPrefs.storageUnit === 'tb' }]"
                @click="displayPrefs.setStorageUnit('tb')"
              >Always TB</button>
            </div>
          </div>
        </div>

        <!-- Update Frequency Section -->
        <div id="section-frequency" class="section">
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
        <div id="section-alerts" class="section">
          <div class="section-header">
            <span class="section-title">Alert Thresholds</span>
            <span class="badge badge-gray">Toast on exceed</span>
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
              {{ alerts.thresholds[metric.key] === 0 ? 'Off' : alerts.thresholds[metric.key] + '%' }}
            </span>
          </div>
        </div>

        <div id="section-version" class="section">
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
                  ? 'Installing'
                  : versionInfo?.update_available
                    ? 'Update available'
                    : 'Up to date'
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
              <span class="info-val">{{ versionInfo?.current_version ?? 'Unknown' }}</span>
            </div>
            <div class="info-row">
              <span class="info-lbl">Latest</span>
              <span class="info-val">{{ versionInfo?.latest_version ?? 'Not checked yet' }}</span>
            </div>
            <div class="info-row">
              <span class="info-lbl">Checked</span>
              <span class="info-val text-muted">{{ versionInfo?.checked_at ?? 'Never' }}</span>
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

          <div v-if="installing" class="update-progress">
            <div class="update-progress-track">
              <div class="update-progress-fill" :style="{ width: updateProgressPercent + '%' }" />
            </div>
            <span class="update-progress-label">{{ updateStepLabel }}</span>
          </div>

          <p v-if="versionSuccess" class="success-msg">{{ versionSuccess }}</p>
          <p v-if="versionError" class="error-msg">{{ versionError }}</p>

          <div class="log-box-wrap">
            <div class="log-box-header">
              <span class="log-box-title">Service Logs</span>
              <span v-if="logsLoading" class="log-box-hint">refreshing…</span>
              <button class="log-refresh-btn" :disabled="logsLoading" @click="fetchServiceLogs">↺</button>
            </div>
            <div ref="logsBox" class="log-box">
              <template v-if="serviceLogs.length">
                <div v-for="(line, i) in serviceLogs" :key="i" class="log-line">{{ line }}</div>
              </template>
              <div v-else class="log-empty">no logs yet — run a check or update to see output here</div>
            </div>
          </div>
        </div>

        <!-- 2FA Section -->
        <div id="section-2fa" class="section">
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
        <div id="section-account" class="section">
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

        <!-- Language Section -->
        <div id="section-language" class="section">
          <div class="section-header">
            <span class="section-title">{{ t('settings.language') }}</span>
            <span class="badge badge-gray">{{ locale.locale.toUpperCase() }}</span>
          </div>
          <p class="section-desc">{{ t('settings.languageDesc') }}</p>
          <div class="theme-toggle-row">
            <button
              type="button"
              :class="['theme-btn', { active: locale.locale === 'en' }]"
              @click="locale.setLocale('en')"
            >English</button>
            <button
              type="button"
              :class="['theme-btn', { active: locale.locale === 'zh' }]"
              @click="locale.setLocale('zh')"
            >中文</button>
          </div>
        </div>

        <!-- Webhooks Section -->
        <div id="section-webhooks" class="section">
          <div class="section-header">
            <span class="section-title">{{ t('settings.webhooks') }}</span>
            <span class="badge badge-gray">{{ webhooks.length }} configured</span>
          </div>
          <p class="section-desc">{{ t('settings.webhooksDesc') }}</p>

          <div v-if="!webhooks.length" class="section-desc">{{ t('settings.noWebhooks') }}</div>

          <div v-for="wh in webhooks" :key="wh.id" class="webhook-row">
            <div class="webhook-info">
              <span class="webhook-label">{{ wh.label || 'Webhook' }}</span>
              <span class="webhook-url">{{ wh.url }}</span>
            </div>
            <div class="webhook-actions">
              <button
                :class="['theme-btn', 'wh-toggle', { active: wh.enabled }]"
                @click="toggleWebhook(wh)"
              >{{ wh.enabled ? t('common.enabled') : t('common.disabled') }}</button>
              <button class="theme-btn wh-test" @click="testWebhook(wh)">{{ t('settings.testWebhook') }}</button>
              <button class="theme-btn wh-del" @click="deleteWebhook(wh.id)">{{ t('common.delete') }}</button>
            </div>
          </div>

          <div class="webhook-add-form">
            <BaseInput
              v-model="newWebhookUrl"
              :label="t('settings.webhookUrl')"
              id="wh-url"
              placeholder="https://discord.com/api/webhooks/..."
            />
            <BaseInput
              v-model="newWebhookLabel"
              :label="t('settings.webhookLabel')"
              id="wh-label"
              placeholder="My webhook"
            />
            <div class="wh-events">
              <span class="style-lbl">{{ t('settings.webhookEvents') }}</span>
              <div class="theme-toggle-row">
                <button
                  v-for="ev in webhookEventOptions"
                  :key="ev.value"
                  :class="['theme-btn', { active: newWebhookEvents.includes(ev.value) }]"
                  @click="toggleEvent(ev.value)"
                >{{ ev.label }}</button>
              </div>
            </div>
            <p v-if="webhookError" class="error-msg">{{ webhookError }}</p>
            <p v-if="webhookSuccess" class="success-msg">{{ webhookSuccess }}</p>
            <BaseButton variant="ghost" :disabled="!newWebhookUrl || webhookLoading" @click="addWebhook">
              {{ webhookLoading ? 'Saving…' : t('settings.addWebhook') }}
            </BaseButton>
          </div>
        </div>

        <!-- Proxy Section -->
        <!-- Devices Section -->
        <div id="section-devices" class="section">
          <div class="section-header">
            <span class="section-title">Active Sessions</span>
            <span class="badge badge-gray">{{ devices.length }}</span>
          </div>
          <p class="section-desc">
            Devices currently signed in. Revoking a session immediately invalidates that login token.
          </p>
          <div v-if="devicesLoading" class="section-loading">Loading…</div>
          <div v-else-if="!devices.length" class="section-empty">No active sessions.</div>
          <div v-else class="device-list">
            <div v-for="dev in devices" :key="dev.id" class="device-row">
              <div class="device-info">
                <span class="device-name">{{ dev.name }}</span>
                <span class="device-meta">{{ dev.ip_address || 'unknown IP' }} · last seen {{ fmtDate(dev.last_seen) }}</span>
              </div>
              <button class="revoke-btn" @click="revokeDevice(dev.id)">Revoke</button>
            </div>
          </div>
          <p v-if="devicesError" class="error-msg">{{ devicesError }}</p>
        </div>

        <!-- Passkeys Section -->
        <div id="section-passkeys" class="section">
          <div class="section-header">
            <span class="section-title">Passkeys</span>
            <span class="badge badge-gray">{{ passkeys.length }}</span>
          </div>
          <p class="section-desc">
            Sign in with a hardware key, Face ID, or fingerprint — no password needed.
          </p>
          <div v-if="passkeysLoading" class="section-loading">Loading…</div>
          <div v-else-if="!passkeys.length" class="section-empty">No passkeys registered.</div>
          <div v-else class="device-list">
            <div v-for="pk in passkeys" :key="pk.id" class="device-row">
              <span class="device-name">{{ pk.device_name }}</span>
              <button class="revoke-btn" @click="deletePasskey(pk.id)">Remove</button>
            </div>
          </div>
          <p v-if="passkeysError" class="error-msg">{{ passkeysError }}</p>
          <p v-if="passkeysSuccess" class="success-msg">{{ passkeysSuccess }}</p>
          <div class="passkey-add-row">
            <input v-model="newPasskeyName" placeholder="Device label (e.g. YubiKey 5)" class="pk-name-input" />
            <BaseButton variant="ghost" :disabled="pkRegistering" @click="registerPasskey">
              {{ pkRegistering ? 'Registering…' : 'Register passkey' }}
            </BaseButton>
          </div>
        </div>

        <div id="section-proxy" class="section">
          <div class="section-header">
            <span class="section-title">Outbound Proxy</span>
            <span :class="['badge', proxy.enabled ? 'badge-green' : 'badge-gray']">
              {{ proxy.enabled ? 'enabled' : 'disabled' }}
            </span>
          </div>
          <p class="section-desc">
            Route update checks through an HTTP or SOCKS5 proxy (e.g. Clash on 7890).
            Useful if GitHub is blocked on your network.
          </p>

          <div class="proxy-row">
            <span class="style-lbl">Enable proxy</span>
            <button
              :class="['theme-btn', { active: proxy.enabled }]"
              @click="proxy.enabled = true"
            >On</button>
            <button
              :class="['theme-btn', { active: !proxy.enabled }]"
              @click="proxy.enabled = false"
            >Off</button>
          </div>

          <div class="proxy-row">
            <span class="style-lbl">Type</span>
            <button
              :class="['theme-btn', { active: proxy.type === 'http' }]"
              @click="proxy.type = 'http'"
            >HTTP</button>
            <button
              :class="['theme-btn', { active: proxy.type === 'socks5' }]"
              @click="proxy.type = 'socks5'"
            >SOCKS5</button>
          </div>

          <div class="proxy-fields">
            <div class="proxy-field">
              <span class="style-lbl">Host</span>
              <BaseInput v-model="proxy.host" placeholder="127.0.0.1" />
            </div>
            <div class="proxy-field proxy-field-port">
              <span class="style-lbl">Port</span>
              <BaseInput v-model.number="proxy.port" type="number" placeholder="7890" />
            </div>
          </div>

          <p v-if="proxyError" class="error-msg">{{ proxyError }}</p>
          <p v-if="proxySuccess" class="success-msg">{{ proxySuccess }}</p>

          <div class="proxy-actions">
            <BaseButton variant="ghost" :disabled="proxySaving" @click="saveProxy">
              {{ proxySaving ? 'Saving…' : 'Save' }}
            </BaseButton>
            <BaseButton variant="ghost" :disabled="proxyTesting" @click="testProxy">
              {{ proxyTesting ? 'Testing…' : 'Test connection' }}
            </BaseButton>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import { useAuthStore } from '@/stores/auth'
import { useMetricsStore } from '@/stores/metrics'
import { useThemeStore, type AnimationLevel } from '@/stores/theme'
import { useAlertsStore } from '@/stores/alerts'
import { useBackgroundStore } from '@/stores/background'
import { useDisplayPrefsStore } from '@/stores/displayPrefs'
import { useLocaleStore } from '@/stores/locale'
import { useDialogStore } from '@/stores/dialog'
import { useWebSocket } from '@/composables/useWebSocket'
import { settingsApi, systemApi, webhooksApi, proxyApi, devicesApi, passkeysApi, backgroundImageApi, type SystemVersionResponse, type WebhookResponse, type ProxyConfig, type DeviceInfo, type PasskeyCredential } from '@/api'
import QRCode from 'qrcode'

const auth = useAuthStore()
const metrics = useMetricsStore()
const theme = useThemeStore()
const alerts = useAlertsStore()
const bg = useBackgroundStore()
const displayPrefs = useDisplayPrefsStore()
const locale = useLocaleStore()
const dialog = useDialogStore()
const { t } = locale
const { sendInterval } = useWebSocket()

const mainEl = ref<HTMLElement | null>(null)

const navSections = [
  { id: 'section-appearance', label: 'Appearance' },
  { id: 'section-style',      label: 'Stylistic' },
  { id: 'section-backgrounds',label: 'Backgrounds' },
  { id: 'section-display',    label: 'Display' },
  { id: 'section-frequency',  label: 'Frequency' },
  { id: 'section-alerts',     label: 'Alerts' },
  { id: 'section-version',    label: 'Version' },
  { id: 'section-2fa',        label: '2FA' },
  { id: 'section-account',    label: 'Account' },
  { id: 'section-language',   label: t('settings.language') },
  { id: 'section-webhooks',   label: t('settings.webhooks') },
  { id: 'section-devices',    label: 'Sessions' },
  { id: 'section-passkeys',   label: 'Passkeys' },
  { id: 'section-proxy',      label: 'Proxy' },
]

function scrollTo(id: string) {
  const target = document.getElementById(id)
  const container = mainEl.value
  if (!target || !container) return
  const delta = target.getBoundingClientRect().top - container.getBoundingClientRect().top
  container.scrollBy({ top: delta - 16, behavior: 'smooth' })
}

// Lets the command palette (or any external link) jump straight to a section via #section-id
const route = useRoute()
watch(() => route.hash, (hash) => {
  if (!hash) return
  nextTick(() => scrollTo(hash.slice(1)))
}, { immediate: true })

const bgTypes = [
  { key: 'color' as const, label: 'Color' },
  { key: 'gradient' as const, label: 'Gradient' },
  { key: 'image' as const, label: 'Image' },
]

const appFileInput = ref<HTMLInputElement | null>(null)
const loginFileInput = ref<HTMLInputElement | null>(null)
const uploadError = ref<'app' | 'login' | null>(null)
const uploadErrorMsg = ref('')
const uploading = ref<'app' | 'login' | null>(null)

function triggerUpload(target: 'app' | 'login') {
  uploadError.value = null
  if (target === 'app') appFileInput.value?.click()
  else loginFileInput.value?.click()
}

async function handleUpload(target: 'app' | 'login', event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  input.value = ''

  if (file.size > 20 * 1024 * 1024) {
    uploadError.value = target
    uploadErrorMsg.value = 'Image too large — max 20 MB'
    return
  }

  uploadError.value = null
  uploading.value = target
  try {
    await backgroundImageApi.upload(target, file)
    const version = Date.now()
    if (target === 'app') bg.setAppBgImageVersion(version)
    else bg.setLoginBgImageVersion(version)
  } catch (e: any) {
    uploadError.value = target
    uploadErrorMsg.value = e.response?.data?.detail || 'Upload failed'
  } finally {
    uploading.value = null
  }
}

async function removeImage(target: 'app' | 'login') {
  uploadError.value = null
  try {
    await backgroundImageApi.remove(target)
    if (target === 'app') bg.setAppBgImageVersion(null)
    else bg.setLoginBgImageVersion(null)
  } catch (e: any) {
    uploadError.value = target
    uploadErrorMsg.value = e.response?.data?.detail || 'Failed to remove image'
  }
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

const serviceLogs = ref<string[]>([])
const logsLoading = ref(false)
const logsBox = ref<HTMLElement | null>(null)

async function fetchServiceLogs() {
  logsLoading.value = true
  try {
    const res = await systemApi.serviceLogs()
    serviceLogs.value = res.data.lines
    await nextTick()
    if (logsBox.value) logsBox.value.scrollTop = logsBox.value.scrollHeight
  } catch {
    // silently ignore — not critical
  } finally {
    logsLoading.value = false
  }
}

async function loadVersionInfo() {
  versionError.value = ''

  try {
    const res = await systemApi.version()
    versionInfo.value = res.data
    if (res.data.error) {
      versionError.value = res.data.error
    }
  } catch (e: any) {
    versionError.value = e.response?.data?.detail || 'Failed to load version status'
  }
}

async function checkForUpdates() {
  versionActionLoading.value = true
  versionError.value = ''
  versionSuccess.value = ''
  await fetchServiceLogs()

  try {
    const res = await systemApi.checkUpdates()
    versionSuccess.value = res.data.message || 'Checking for updates…'

    // Poll until the check service finishes (up to 45s)
    const deadline = Date.now() + 45_000
    while (Date.now() < deadline) {
      await wait(2000)
      await Promise.all([loadVersionInfo(), fetchServiceLogs()])
      const info = versionInfo.value
      if (!info?.check_in_progress) break
    }
    await fetchServiceLogs()

    if (versionInfo.value?.update_available) {
      versionSuccess.value = 'Update available!'
    } else if (!versionInfo.value?.check_in_progress) {
      versionSuccess.value = 'Already up to date.'
    }
  } catch (e: any) {
    const detail = e.response?.data?.detail || e.response?.data?.message
    const network = e.code === 'ECONNABORTED'
      ? 'Request timed out — backend may be unreachable'
      : e.message
        ? `Network error: ${e.message}`
        : null
    versionError.value = detail || network || 'Failed to start update check'
  } finally {
    versionActionLoading.value = false
  }
}

// Named steps install_or_update() logs, in order — used to turn the plain
// log tail into real progress instead of an indeterminate spinner. Not a
// fabricated percentage: each entry only lights up once its matching line
// has actually appeared in the polled service logs.
const UPDATE_STEPS = [
  { match: 'sniffing for port squatters', label: 'Checking port availability' },
  { match: 'grabbing system dependencies', label: 'Installing system dependencies' },
  { match: 'conjuring the carbonpanel service account', label: 'Setting up service account' },
  { match: 'staking out territory on disk', label: 'Preparing install directories' },
  { match: 'locking in your secrets', label: 'Writing configuration' },
  { match: "asking github what's poppin", label: 'Checking GitHub for the latest version' },
  { match: 'yanking the code down', label: 'Cloning release' },
  { match: "teaching python what's what", label: 'Installing backend dependencies' },
  { match: 'bundling the frontend heat', label: 'Building frontend' },
  { match: 'deploying the new release', label: 'Deploying & restarting services' },
] as const

const installing = ref(false)

const updateStepIndex = computed(() => {
  if (!installing.value) return -1
  let idx = -1
  for (const line of serviceLogs.value) {
    for (let i = 0; i < UPDATE_STEPS.length; i++) {
      if (line.includes(UPDATE_STEPS[i].match)) idx = Math.max(idx, i)
    }
  }
  return idx
})

const updateProgressPercent = computed(() =>
  updateStepIndex.value >= 0
    ? Math.round(((updateStepIndex.value + 1) / UPDATE_STEPS.length) * 100)
    : 4,
)

const updateStepLabel = computed(() =>
  updateStepIndex.value >= 0 ? UPDATE_STEPS[updateStepIndex.value].label : 'Starting…',
)

async function installUpdate() {
  if (!versionInfo.value?.update_available || versionInfo.value.update_in_progress) return

  const targetVersion = versionInfo.value.latest_version ?? 'the latest version'
  const confirmed = await dialog.confirm({
    title: 'Install update',
    message: `Install CarbonPanel ${targetVersion} now? The app will restart automatically during the update.`,
    confirmLabel: 'Install',
  })

  if (!confirmed) return

  versionActionLoading.value = true
  installing.value = true
  versionError.value = ''
  versionSuccess.value = ''

  await fetchServiceLogs()

  try {
    await systemApi.installUpdate()
    versionSuccess.value = 'Installing update…'

    // Poll until the update service finishes — a fresh venv + npm build can
    // take a few minutes, unlike the 45s check-for-updates poll above.
    const deadline = Date.now() + 6 * 60_000
    await wait(1200)
    while (Date.now() < deadline) {
      await Promise.all([loadVersionInfo(), fetchServiceLogs()])
      if (!versionInfo.value?.update_in_progress) break
      await wait(3000)
    }
    await fetchServiceLogs()

    versionSuccess.value = versionInfo.value?.update_in_progress
      ? 'Still installing — check back in a bit.'
      : versionInfo.value?.update_available
        ? 'Update finished, but a newer version is already available — check again.'
        : "Update installed — you're on the latest version."
  } catch (e: any) {
    const detail = e.response?.data?.detail || e.response?.data?.message
    const network = e.code === 'ECONNABORTED'
      ? 'Request timed out — backend may be unreachable'
      : e.message ? `Network error: ${e.message}` : null
    versionError.value = detail || network || 'Failed to start update installation'
  } finally {
    versionActionLoading.value = false
    installing.value = false
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

// Webhooks
const webhooks = ref<WebhookResponse[]>([])
const newWebhookUrl = ref('')
const newWebhookLabel = ref('')
const newWebhookEvents = ref<string[]>(['alert.cpu', 'alert.ram', 'alert.disk'])
const webhookLoading = ref(false)
const webhookError = ref('')
const webhookSuccess = ref('')

const webhookEventOptions = [
  { value: 'alert.cpu', label: 'CPU' },
  { value: 'alert.ram', label: 'RAM' },
  { value: 'alert.disk', label: 'Disk' },
]

function toggleEvent(ev: string) {
  const idx = newWebhookEvents.value.indexOf(ev)
  if (idx === -1) newWebhookEvents.value.push(ev)
  else newWebhookEvents.value.splice(idx, 1)
}

async function loadWebhooks() {
  try {
    const { data } = await webhooksApi.list()
    webhooks.value = data
  } catch { /* ignore */ }
}

async function addWebhook() {
  webhookError.value = ''
  webhookSuccess.value = ''
  if (!newWebhookUrl.value) return
  webhookLoading.value = true
  try {
    await webhooksApi.create({ url: newWebhookUrl.value, label: newWebhookLabel.value, events: newWebhookEvents.value })
    newWebhookUrl.value = ''
    newWebhookLabel.value = ''
    webhookSuccess.value = 'Webhook added.'
    await loadWebhooks()
  } catch (e: any) {
    webhookError.value = e.response?.data?.detail || 'Failed to save webhook'
  } finally {
    webhookLoading.value = false
  }
}

async function toggleWebhook(wh: WebhookResponse) {
  await webhooksApi.update(wh.id, { enabled: !wh.enabled })
  await loadWebhooks()
}

async function deleteWebhook(id: string) {
  const confirmed = await dialog.confirm({
    title: 'Delete webhook',
    message: 'Delete this webhook? This cannot be undone.',
    confirmLabel: 'Delete',
    variant: 'danger',
  })
  if (!confirmed) return
  await webhooksApi.delete(id)
  await loadWebhooks()
}

async function testWebhook(wh: WebhookResponse) {
  try {
    await webhooksApi.trigger('test', 'manual', 0, 0)
    webhookSuccess.value = `Test sent to ${wh.url}`
  } catch (e: any) {
    webhookError.value = e.response?.data?.detail || 'Test failed'
  }
}

// ── Devices ────────────────────────────────────────────────────────────────────

const devices = ref<DeviceInfo[]>([])
const devicesLoading = ref(false)
const devicesError = ref('')

async function loadDevices() {
  devicesLoading.value = true
  try {
    const { data } = await devicesApi.list()
    devices.value = data
  } catch { /* ignore */ } finally {
    devicesLoading.value = false
  }
}

async function revokeDevice(id: string) {
  try {
    await devicesApi.revoke(id)
    devices.value = devices.value.filter(d => d.id !== id)
  } catch (e: any) {
    devicesError.value = e.response?.data?.detail || 'Failed to revoke session.'
  }
}

function fmtDate(iso: string) {
  try {
    return new Date(iso).toLocaleString()
  } catch { return iso }
}

// ── Passkeys ───────────────────────────────────────────────────────────────────

const passkeys = ref<PasskeyCredential[]>([])
const passkeysLoading = ref(false)
const passkeysError = ref('')
const passkeysSuccess = ref('')
const pkRegistering = ref(false)
const newPasskeyName = ref('')

async function loadPasskeys() {
  passkeysLoading.value = true
  try {
    const { data } = await passkeysApi.list()
    passkeys.value = data
  } catch { /* ignore */ } finally {
    passkeysLoading.value = false
  }
}

async function deletePasskey(id: string) {
  try {
    await passkeysApi.delete(id)
    passkeys.value = passkeys.value.filter(p => p.id !== id)
  } catch (e: any) {
    passkeysError.value = e.response?.data?.detail || 'Failed to remove passkey.'
  }
}

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

async function registerPasskey() {
  passkeysError.value = ''
  passkeysSuccess.value = ''
  if (!window.isSecureContext || !navigator.credentials) {
    passkeysError.value = 'Passkeys require HTTPS. Access this panel over HTTPS or from localhost.'
    return
  }
  pkRegistering.value = true
  try {
    const { data: opts } = await passkeysApi.registerBegin()
    // Convert base64url fields to ArrayBuffer
    const pubKeyOpts: PublicKeyCredentialCreationOptions = {
      ...(opts as any),
      challenge: b64urlToBuffer((opts as any).challenge),
      user: {
        ...(opts as any).user,
        id: b64urlToBuffer((opts as any).user.id),
      },
      excludeCredentials: ((opts as any).excludeCredentials || []).map((c: any) => ({
        ...c,
        id: b64urlToBuffer(c.id),
      })),
    }
    const cred = await navigator.credentials.create({ publicKey: pubKeyOpts }) as PublicKeyCredential
    if (!cred) throw new Error('No credential returned')
    const response = cred.response as AuthenticatorAttestationResponse
    const credJson = {
      id: cred.id,
      rawId: bufferToB64url(cred.rawId),
      type: cred.type,
      response: {
        clientDataJSON: bufferToB64url(response.clientDataJSON),
        attestationObject: bufferToB64url(response.attestationObject),
      },
    }
    await passkeysApi.registerComplete(credJson, newPasskeyName.value || 'Passkey')
    passkeysSuccess.value = 'Passkey registered successfully.'
    newPasskeyName.value = ''
    await loadPasskeys()
  } catch (e: any) {
    passkeysError.value = e.response?.data?.detail || e.message || 'Registration failed.'
  } finally {
    pkRegistering.value = false
  }
}

// ── Proxy ──────────────────────────────────────────────────────────────────────

const proxy = ref<ProxyConfig>({ enabled: false, type: 'http', host: '127.0.0.1', port: 7890 })
const proxySaving = ref(false)
const proxyTesting = ref(false)
const proxyError = ref('')
const proxySuccess = ref('')

async function loadProxy() {
  try {
    const { data } = await proxyApi.get()
    proxy.value = data
  } catch { /* ignore — defaults remain */ }
}

async function saveProxy() {
  proxySaving.value = true
  proxyError.value = ''
  proxySuccess.value = ''
  try {
    await proxyApi.update(proxy.value)
    proxySuccess.value = 'Proxy settings saved.'
  } catch (e: any) {
    proxyError.value = e.response?.data?.detail || 'Failed to save proxy settings.'
  } finally {
    proxySaving.value = false
  }
}

async function testProxy() {
  proxyTesting.value = true
  proxyError.value = ''
  proxySuccess.value = ''
  try {
    await proxyApi.update(proxy.value)
    const { data } = await proxyApi.test()
    if (data.success) {
      proxySuccess.value = data.message
    } else {
      proxyError.value = data.message
    }
  } catch (e: any) {
    proxyError.value = e.response?.data?.detail || 'Test failed.'
  } finally {
    proxyTesting.value = false
  }
}

onMounted(() => {
  void loadVersionInfo()
  void fetchServiceLogs()
  void loadWebhooks()
  void loadProxy()
  void loadDevices()
  void loadPasskeys()
})
</script>

<style scoped>
.settings-page { height: 100%; display: flex; flex-direction: column; }
.settings-main { flex: 1; overflow-y: auto; padding: 20px; display: flex; justify-content: center; }
.settings-container { width: 100%; max-width: 600px; display: flex; flex-direction: column; gap: 20px; }

.page-title { display: flex; align-items: center; gap: 14px; }

.settings-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 14px;
  background: color-mix(in srgb, var(--bg-card) 72%, transparent);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  position: sticky;
  top: 0;
  z-index: 10;
}
.nav-pill {
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-dim);
  font-family: var(--font);
  font-size: 10px;
  letter-spacing: 0.04em;
  padding: 4px 10px;
  border-radius: 20px;
  cursor: pointer;
  transition: all var(--transition);
  white-space: nowrap;
}
.nav-pill:hover { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }
.page-title h1 { font-size: 16px; font-weight: 700; }
.back-link { font-size: 11px; color: var(--fg-muted); text-decoration: none; transition: color var(--transition); }
.back-link:hover { color: var(--accent); }

.section {
  background: color-mix(in srgb, var(--bg-card) 72%, transparent);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
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

.style-hint {
  font-size: 10px;
  color: var(--fg-dim);
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

.log-box-wrap {
  margin-top: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}
.log-box-header {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px;
  background: color-mix(in srgb, var(--bg) 60%, var(--bg-card));
  border-bottom: 1px solid var(--border);
}
.log-box-title { font-size: 10px; font-weight: 600; color: var(--fg-muted); text-transform: uppercase; letter-spacing: 0.06em; flex: 1; }
.log-box-hint { font-size: 10px; color: var(--fg-dim); }
.log-refresh-btn {
  background: none; border: none; color: var(--fg-dim); font-size: 13px;
  cursor: pointer; padding: 0 2px; line-height: 1;
  transition: color var(--transition);
}
.log-refresh-btn:hover:not(:disabled) { color: var(--accent); }
.log-refresh-btn:disabled { opacity: 0.4; cursor: default; }
.log-box {
  height: 180px; overflow-y: auto;
  background: var(--bg); padding: 8px 10px;
  font-family: var(--font); font-size: 10.5px; line-height: 1.55;
}
.log-line { color: var(--fg-muted); white-space: pre-wrap; word-break: break-all; }
.log-empty { color: var(--fg-dim); font-size: 10.5px; padding: 4px 0; }

.webhook-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 12px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  flex-wrap: wrap;
}
.webhook-info { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
.webhook-label { font-size: 11px; font-weight: 500; color: var(--fg); }
.webhook-url { font-size: 10px; color: var(--fg-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.webhook-actions { display: flex; gap: 6px; flex-shrink: 0; }
.wh-toggle.active { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }
.wh-del:hover { border-color: rgba(255,68,68,0.4); color: var(--danger); }
.wh-test:hover { border-color: rgba(100,180,255,0.4); color: #60a5fa; }
.webhook-add-form { display: flex; flex-direction: column; gap: 10px; padding-top: 6px; border-top: 1px solid var(--border-subtle); }
.wh-events { display: flex; flex-direction: column; gap: 6px; }

.display-pref-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

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
  .settings-main { padding: 12px; }
  .settings-nav { gap: 4px; padding: 8px 10px; }
  .nav-pill { font-size: 9px; padding: 3px 8px; }

  .style-grid,
  .typography-grid {
    grid-template-columns: 1fr;
  }

  .toggle-setting-row {
    flex-direction: column;
    align-items: stretch;
  }

  .display-pref-row {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .proxy-fields { flex-direction: column; }
  .proxy-field-port { max-width: 100%; }

  .passkey-add-row { flex-direction: column; align-items: stretch; }

  .version-actions { flex-direction: column; align-items: stretch; }
  .version-link { text-align: center; }
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

.update-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
  animation: slide-in 150ms ease;
}
.update-progress-track {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  overflow: hidden;
}
.update-progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width var(--bar-transition);
}
.update-progress-label {
  font-size: 11px;
  color: var(--fg-muted);
  white-space: nowrap;
  flex-shrink: 0;
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
.info-val { font-size: 12px; color: var(--fg); min-width: 0; overflow-wrap: anywhere; }

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
.upload-drop.disabled { cursor: default; opacity: 0.6; }
.upload-drop.disabled:hover { border-color: var(--border); color: var(--fg-muted); background: none; }
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

/* Proxy section */
.proxy-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.proxy-row .style-lbl { width: 64px; flex-shrink: 0; }
.proxy-fields { display: flex; gap: 10px; margin-bottom: 10px; }
.proxy-field { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.proxy-field-port { max-width: 110px; }
.proxy-actions { display: flex; gap: 8px; margin-top: 10px; }

/* Devices / Passkeys sections */
.section-loading { font-size: 11px; color: var(--fg-dim); }
.section-empty { font-size: 11px; color: var(--fg-dim); }
.device-list { display: flex; flex-direction: column; gap: 8px; }
.device-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  gap: 10px;
}
.device-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.device-name {
  font-size: 12px; color: var(--fg);
  min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
}
.device-meta { font-size: 10px; color: var(--fg-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.revoke-btn {
  background: none;
  border: 1px solid rgba(255,68,68,0.3);
  color: var(--danger);
  font-family: var(--font);
  font-size: 10px;
  padding: 3px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
  white-space: nowrap;
  flex-shrink: 0;
}
.revoke-btn:hover { background: var(--danger-dim); border-color: rgba(255,68,68,0.5); }

.passkey-add-row { display: flex; align-items: center; gap: 8px; margin-top: 12px; }
.pk-name-input {
  flex: 1;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--fg);
  font-family: var(--font);
  font-size: 11px;
  padding: 6px 10px;
  outline: none;
  transition: border-color var(--transition);
}
.pk-name-input:focus { border-color: var(--accent-border); }
</style>
