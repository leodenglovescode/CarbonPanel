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
            <span class="badge badge-gray">Always-on monitoring</span>
          </div>
          <p class="section-desc">Configure thresholds and severity for CPU, RAM, disks, GPUs, GPU temperature, and per-interface network throughput. The server sends configured notifications even when the dashboard is closed.</p>

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

          <div class="alert-rules">
            <div v-for="metric in alertMetrics" :key="metric.key" class="alert-rule">
              <div class="alert-rule-header">
                <div>
                  <span class="alert-rule-label">{{ metric.label }}</span>
                  <p class="alert-rule-desc">{{ metric.description }}</p>
                </div>
                <span
                  :class="[
                    'alert-severity-badge',
                    `severity-${alerts.severities[metric.key]}`,
                  ]"
                >{{ alerts.severities[metric.key] }}</span>
              </div>
              <div class="alert-rule-controls">
                <label class="alert-threshold-field">
                  <span class="style-lbl">Threshold</span>
                  <span class="alert-threshold-input-wrap">
                    <input
                      type="number"
                      class="alert-threshold-input"
                      :value="alerts.thresholds[metric.key]"
                      min="0"
                      :max="metric.max"
                      :step="metric.step"
                      @input="alerts.setThreshold(
                        metric.key,
                        Number.parseFloat(($event.target as HTMLInputElement).value),
                      )"
                    />
                    <span class="alert-threshold-unit">{{ metric.unit }}</span>
                  </span>
                  <span class="alert-off-note">
                    {{ alerts.thresholds[metric.key] === 0 ? 'Disabled' : 'Set to 0 to disable' }}
                  </span>
                </label>
                <div class="alert-severity-control">
                  <span class="style-lbl">Severity</span>
                  <div class="theme-toggle-row">
                    <button
                      v-for="severity in severityOptions"
                      :key="severity.value"
                      type="button"
                      :class="[
                        'theme-btn',
                        'severity-btn',
                        `severity-${severity.value}`,
                        { active: alerts.severities[metric.key] === severity.value },
                      ]"
                      @click="alerts.setSeverity(metric.key, severity.value)"
                    >{{ severity.label }}</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div id="section-version" class="section">
          <div class="section-header">
            <span class="section-title">Version & Updates</span>
            <span
              :class="[
                'badge',
                versionInfo?.update_available &&
                  !versionInfo?.update_in_progress &&
                  !versionInfo?.check_in_progress
                  ? 'badge-green'
                  : 'badge-gray',
              ]"
            >
              {{
                restarting || versionInfo?.restart_pending
                  ? 'Restarting'
                  : versionInfo?.update_in_progress
                    ? 'Installing'
                    : versionInfo?.check_in_progress
                      ? 'Checking'
                      : versionInfo?.update_available
                        ? 'Update available'
                        : 'Up to date'
              }}
            </span>
          </div>
          <p class="section-desc">
            CarbonPanel checks the installed GitHub branch for new commits every day. You can also
            check manually and start an interactive update from here.
          </p>

          <div class="version-grid">
            <div class="info-row">
              <span class="info-lbl">Current</span>
              <span class="info-val">
                {{ versionInfo?.current_version ?? 'Unknown' }}
                <span v-if="versionInfo?.current_commit" class="commit-id">
                  {{ versionInfo.current_commit.slice(0, 8) }}
                </span>
              </span>
            </div>
            <div class="info-row">
              <span class="info-lbl">Latest</span>
              <span class="info-val">
                {{ versionInfo?.latest_version ?? 'Not checked yet' }}
                <span v-if="versionInfo?.latest_commit" class="commit-id">
                  {{ versionInfo.latest_commit.slice(0, 8) }}
                </span>
              </span>
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

          <div
            v-if="restarting"
            :class="['restart-countdown', { 'restart-countdown-timeout': restartTimedOut }]"
          >
            <div class="restart-countdown-num">
              {{ restartTimedOut ? '!' : restartCountdown > 0 ? restartCountdown : '…' }}
            </div>
            <div class="restart-countdown-copy">
              <strong>
                {{ restartTimedOut ? 'Panel did not reconnect automatically' : 'Panel is restarting' }}
              </strong>
              <template v-if="restartTimedOut">
                <span>
                  The automatic wait has stopped. Reload now if the service is back, or retry the
                  connection checks without leaving this page.
                </span>
                <div class="restart-countdown-actions">
                  <BaseButton variant="ghost" @click="retryRestartConnection">Try again</BaseButton>
                  <BaseButton variant="primary" @click="reloadPanel">Reload now</BaseButton>
                </div>
              </template>
              <span v-else>
                Checking every 2 seconds
                {{ restartCountdown > 0 ? `· ${restartCountdown}s until manual controls appear.` : '· reconnecting…' }}
                This page will reload as soon as the updated backend answers.
              </span>
            </div>
          </div>

          <template v-else>
            <div class="version-actions">
              <BaseButton
                variant="ghost"
                :disabled="versionActionLoading || !!versionInfo?.update_in_progress"
                @click="checkForUpdates"
              >
                {{ versionInfo?.check_in_progress ? 'Checking…' : 'Check for Updates' }}
              </BaseButton>

              <BaseButton
                variant="primary"
                :disabled="
                  versionActionLoading ||
                    !versionInfo?.update_available ||
                    !!versionInfo?.update_in_progress ||
                    !!versionInfo?.check_in_progress
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
              <div class="update-progress-copy">
                <span class="update-progress-label">{{ updateStepLabel }}</span>
                <span class="update-progress-percent">{{ updateProgressPercent }}%</span>
              </div>
              <div
                class="update-progress-track"
                role="progressbar"
                :aria-valuenow="updateProgressPercent"
                aria-valuemin="0"
                aria-valuemax="100"
              >
                <div class="update-progress-fill" :style="{ width: updateProgressPercent + '%' }" />
              </div>
            </div>

            <p v-if="versionSuccess" class="success-msg">{{ versionSuccess }}</p>
            <p v-if="versionError" class="error-msg">{{ versionError }}</p>
          </template>

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
              <BaseInput
                v-model="setupPassword"
                label="Current Password"
                id="setup-password"
                type="password"
                autocomplete="current-password"
                required
              />
              <p v-if="setupError" class="error-msg">{{ setupError }}</p>
              <BaseButton
                variant="ghost"
                @click="startSetup"
                :disabled="setupLoading || !setupPassword"
              >
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
            <p class="section-desc">2FA is active. Re-enter your password and current code to disable it.</p>
            <form class="confirm-form" @submit.prevent="handleDisable">
              <BaseInput
                v-model="disablePassword"
                label="Current Password"
                id="disable-password"
                type="password"
                autocomplete="current-password"
                required
              />
              <BaseInput
                v-model="disableCode"
                label="Current TOTP Code"
                id="disable-code"
                placeholder="000000"
                inputmode="numeric"
                maxlength="6"
              />
              <p v-if="disableError" class="error-msg">{{ disableError }}</p>
              <BaseButton variant="danger" :disabled="!disablePassword || disableCode.length !== 6 || disableLoading">
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

        <!-- Notifications Section -->
        <div id="section-webhooks" class="section">
          <div class="section-header">
            <span class="section-title">{{ t('settings.webhooks') }}</span>
            <span class="badge badge-gray">{{ webhooks.length }} configured</span>
          </div>
          <p class="section-desc">{{ t('settings.webhooksDesc') }}</p>

          <div v-if="!webhooks.length" class="section-desc">{{ t('settings.noWebhooks') }}</div>

          <div v-for="wh in webhooks" :key="wh.id" class="webhook-row">
            <div class="webhook-info">
              <span class="webhook-label-line">
                <span class="webhook-label">{{ wh.label || channelKindLabel(wh.kind) }}</span>
                <span class="notification-kind">{{ channelKindLabel(wh.kind) }}</span>
              </span>
              <span class="webhook-url">{{ channelTarget(wh) }}</span>
              <div class="notification-event-chips">
                <button
                  v-for="event in webhookEventOptions"
                  :key="event.value"
                  type="button"
                  :class="['notification-event-chip', { active: wh.events.includes(event.value) }]"
                  :title="event.label"
                  @click="toggleWebhookEvent(wh, event.value)"
                >{{ event.short }}</button>
              </div>
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
            <div class="wh-events">
              <span class="style-lbl">{{ t('settings.notificationType') }}</span>
              <div class="theme-toggle-row">
                <button
                  v-for="kind in notificationKinds"
                  :key="kind.value"
                  type="button"
                  :class="['theme-btn', { active: newWebhookKind === kind.value }]"
                  @click="selectNotificationKind(kind.value)"
                >{{ kind.label }}</button>
              </div>
            </div>

            <BaseInput
              v-model="newWebhookLabel"
              :label="t('settings.webhookLabel')"
              id="wh-label"
              :placeholder="t('settings.notificationLabelPlaceholder')"
            />

            <BaseInput
              v-if="newWebhookKind === 'webhook'"
              v-model="newWebhookUrl"
              :label="t('settings.webhookUrl')"
              id="wh-url"
              placeholder="https://example.com/hooks/carbonpanel"
            />

            <template v-if="newWebhookKind === 'ntfy'">
              <BaseInput
                v-model="newWebhookUrl"
                :label="t('settings.ntfyServer')"
                id="ntfy-server"
                placeholder="http://127.0.0.1:8080"
              />
              <BaseInput
                v-model="newNtfyTopic"
                :label="t('settings.ntfyTopic')"
                id="ntfy-topic"
                placeholder="carbonpanel-alerts"
              />
              <BaseInput
                v-model="newNtfyToken"
                :label="t('settings.ntfyToken')"
                id="ntfy-token"
                type="password"
                :placeholder="t('settings.optionalToken')"
                autocomplete="new-password"
              />
              <p class="credential-note">{{ t('settings.credentialsEncrypted') }}</p>
            </template>

            <template v-if="newWebhookKind === 'email'">
              <div class="smtp-grid">
                <BaseInput
                  v-model="newSmtpHost"
                  :label="t('settings.smtpHost')"
                  id="smtp-host"
                  placeholder="smtp.example.com"
                />
                <BaseInput
                  v-model="newSmtpPort"
                  :label="t('settings.smtpPort')"
                  id="smtp-port"
                  type="number"
                  min="1"
                  max="65535"
                />
              </div>
              <div class="wh-events">
                <span class="style-lbl">{{ t('settings.smtpSecurity') }}</span>
                <div class="theme-toggle-row">
                  <button
                    v-for="mode in smtpSecurityModes"
                    :key="mode.value"
                    type="button"
                    :class="['theme-btn', { active: newSmtpSecurity === mode.value }]"
                    @click="selectSmtpSecurity(mode.value)"
                  >{{ mode.label }}</button>
                </div>
              </div>
              <div class="smtp-grid">
                <BaseInput
                  v-model="newEmailFrom"
                  :label="t('settings.emailFrom')"
                  id="email-from"
                  type="email"
                  placeholder="carbonpanel@example.com"
                />
                <BaseInput
                  v-model="newEmailTo"
                  :label="t('settings.emailTo')"
                  id="email-to"
                  type="email"
                  placeholder="admin@example.com"
                />
              </div>
              <div class="smtp-grid">
                <BaseInput
                  v-model="newSmtpUsername"
                  :label="t('settings.smtpUsername')"
                  id="smtp-username"
                  autocomplete="username"
                  :placeholder="t('settings.optionalUsername')"
                />
                <BaseInput
                  v-model="newSmtpPassword"
                  :label="t('settings.smtpPassword')"
                  id="smtp-password"
                  type="password"
                  autocomplete="new-password"
                  :placeholder="t('settings.optionalPassword')"
                />
              </div>
              <p class="credential-note">{{ t('settings.credentialsEncrypted') }}</p>
            </template>

            <div class="wh-events">
              <span class="style-lbl">{{ t('settings.webhookEvents') }}</span>
              <div class="theme-toggle-row">
                <button
                  v-for="ev in webhookEventOptions"
                  :key="ev.value"
                  type="button"
                  :class="['theme-btn', { active: newWebhookEvents.includes(ev.value) }]"
                  @click="toggleEvent(ev.value)"
                >{{ ev.label }}</button>
              </div>
            </div>
            <p v-if="webhookError" class="error-msg">{{ webhookError }}</p>
            <p v-if="webhookSuccess" class="success-msg">{{ webhookSuccess }}</p>
            <BaseButton variant="ghost" :disabled="!canAddNotification || webhookLoading" @click="addWebhook">
              {{ webhookLoading ? t('settings.saving') : t('settings.addWebhook') }}
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

        <!-- Paired Devices Section -->
        <div id="section-pairing" class="section">
          <div class="section-header">
            <span class="section-title">Paired Devices</span>
            <span class="badge badge-gray">{{ pairedCount }}</span>
          </div>
          <p class="section-desc">
            Pair the CarbonPanel Android app by scanning a QR code. The app gets its own
            long-lived token, revocable above at any time. Re-authenticate here to create
            the code; your password and 2FA code are never sent to the phone.
          </p>

          <div class="pair-endpoints">
            <div class="pair-subhead">Addresses to embed in the code</div>
            <p class="pair-hint">
              The phone tries these in order until one answers. Include an address that
              works away from home — a VPN/Tailscale address or a public domain — or the
              app will only work on your LAN.
            </p>
            <label
              v-for="ep in allEndpoints"
              :key="ep.url"
              class="pair-ep-row"
            >
              <input type="checkbox" :value="ep.url" v-model="selectedEndpoints" />
              <span class="pair-ep-url">{{ ep.url }}</span>
              <span :class="['pair-ep-kind', `kind-${ep.kind}`]">{{ endpointKindLabel(ep.kind) }}</span>
            </label>

            <div class="pair-add-row">
              <BaseInput
                v-model="newEndpoint"
                placeholder="https://panel.example.com"
                @keyup.enter="addEndpoint"
              />
              <button class="theme-btn" :disabled="!newEndpoint.trim()" @click="addEndpoint">
                Add
              </button>
            </div>
            <p v-if="endpointError" class="error-msg">{{ endpointError }}</p>
          </div>

          <div class="confirm-form">
            <BaseInput
              v-model="pairAuthPassword"
              label="Current Password"
              id="pair-password"
              type="password"
              autocomplete="current-password"
              required
            />
            <BaseInput
              v-if="auth.user?.totp_enabled"
              v-model="pairAuthTotp"
              label="Current TOTP Code"
              id="pair-totp"
              placeholder="000000"
              inputmode="numeric"
              maxlength="6"
              required
            />
          </div>

          <div class="pair-actions">
            <button
              class="theme-btn active"
              :disabled="pairingBusy || !selectedEndpoints.length || !pairAuthPassword || (auth.user?.totp_enabled && pairAuthTotp.length !== 6)"
              @click="startPairing"
            >
              {{ pairing ? 'New code' : 'Pair a device' }}
            </button>
            <button v-if="pairing" class="theme-btn" @click="cancelPairing">Done</button>
          </div>

          <div v-if="pairing" class="pair-panel" :class="{ 'pair-panel--done': pairStatus === 'claimed' }">
            <!-- Corner brackets frame the code the way a scanner viewfinder
                 does, so it reads as "point a camera here" rather than as a
                 decorative image. -->
            <div class="pair-qr-frame" :class="{ 'is-stale': pairStatus === 'expired' }">
              <span class="pair-corner pair-corner--tl" />
              <span class="pair-corner pair-corner--tr" />
              <span class="pair-corner pair-corner--bl" />
              <span class="pair-corner pair-corner--br" />
              <img
                class="pair-qr"
                :src="`data:image/png;base64,${pairing.qr_png_b64}`"
                alt="Pairing QR code"
              />
              <div v-if="pairStatus === 'claimed'" class="pair-qr-veil">✓</div>
              <div v-else-if="pairStatus === 'expired'" class="pair-qr-veil pair-qr-veil--stale">
                expired
              </div>
            </div>

            <div class="pair-side">
              <div class="pair-steps">
                <div class="pair-step"><i>1</i><span>Install the CarbonPanel app on your phone</span></div>
                <div class="pair-step"><i>2</i><span>Open it and tap <b>Scan pairing code</b></span></div>
                <div class="pair-step"><i>3</i><span>Point the camera at this code</span></div>
              </div>

              <div class="pair-status" :class="pairStatusClass">
                <template v-if="pairStatus === 'claimed'">
                  Paired with {{ pairedName || 'device' }} — it's ready to use.
                </template>
                <template v-else-if="pairStatus === 'expired'">
                  Code expired. Generate a new one to try again.
                </template>
                <template v-else>
                  <span class="pair-pulse" />Waiting for a device to scan…
                </template>
              </div>

              <!-- Time pressure is the point: the code is single-use and
                   short-lived, so the countdown is shown rather than left to
                   expire silently. -->
              <div v-if="pairStatus === 'pending'" class="pair-timer">
                <div class="pair-timer-bar">
                  <div class="pair-timer-fill" :style="{ width: pairTimerPct + '%' }" />
                </div>
                <span class="pair-timer-text">{{ pairCountdown }}s</span>
              </div>

              <div v-if="pairStatus !== 'claimed'" class="pair-manual">
                <span class="pair-manual-label">Can't scan? Type this code in the app</span>
                <code class="pair-code">{{ pairing.code }}</code>
              </div>
            </div>
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
              :disabled="proxySaving"
              @click="setProxyEnabled(true)"
            >On</button>
            <button
              :class="['theme-btn', { active: !proxy.enabled }]"
              :disabled="proxySaving"
              @click="setProxyEnabled(false)"
            >Off</button>
          </div>

          <div class="proxy-row">
            <span class="style-lbl">Type</span>
            <button
              :class="['theme-btn', { active: proxy.type === 'http' }]"
              :disabled="proxySaving"
              @click="setProxyType('http')"
            >HTTP</button>
            <button
              :class="['theme-btn', { active: proxy.type === 'socks5' }]"
              :disabled="proxySaving"
              @click="setProxyType('socks5')"
            >SOCKS5</button>
          </div>

          <div class="proxy-fields">
            <div class="proxy-field">
              <span class="style-lbl">Host</span>
              <BaseInput v-model="proxy.host" placeholder="127.0.0.1" @blur="saveProxy" />
            </div>
            <div class="proxy-field proxy-field-port">
              <span class="style-lbl">Port</span>
              <BaseInput v-model.number="proxy.port" type="number" placeholder="7890" @blur="saveProxy" />
            </div>
          </div>

          <p v-if="proxyError" class="error-msg">{{ proxyError }}</p>
          <p v-if="proxySuccess" class="success-msg">{{ proxySuccess }}</p>

          <div class="proxy-actions">
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
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import { useAuthStore } from '@/stores/auth'
import { useMetricsStore } from '@/stores/metrics'
import { useThemeStore, type AnimationLevel } from '@/stores/theme'
import { useAlertsStore, type AlertRuleKey, type AlertSeverity } from '@/stores/alerts'
import { useBackgroundStore } from '@/stores/background'
import { useDisplayPrefsStore } from '@/stores/displayPrefs'
import { useLocaleStore } from '@/stores/locale'
import { useDialogStore } from '@/stores/dialog'
import { useWebSocket } from '@/composables/useWebSocket'
import { settingsApi, systemApi, webhooksApi, proxyApi, devicesApi, pairingApi, backgroundImageApi, type SystemVersionResponse, type WebhookResponse, type WebhookCreate, type NotificationKind, type ProxyConfig, type DeviceInfo, type PairingEndpoint, type PairingStart } from '@/api'
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
  { id: 'section-pairing',    label: 'Paired Devices' },
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

const alertMetrics: Array<{
  key: AlertRuleKey
  label: string
  description: string
  unit: string
  step: number
  max?: number
}> = [
  { key: 'cpu', label: 'CPU usage', description: 'Aggregate utilization across all CPU cores.', unit: '%', step: 5, max: 100 },
  { key: 'ram', label: 'RAM usage', description: 'Percentage of physical memory currently in use.', unit: '%', step: 5, max: 100 },
  { key: 'disk', label: 'Disk usage', description: 'Used capacity on each selected mount.', unit: '%', step: 5, max: 100 },
  { key: 'gpuUsage', label: 'GPU utilization', description: 'Utilization on each detected NVIDIA GPU.', unit: '%', step: 5, max: 100 },
  { key: 'gpuTemp', label: 'GPU temperature', description: 'Temperature on each detected NVIDIA GPU.', unit: '°C', step: 5, max: 150 },
  { key: 'networkRx', label: 'Network receive', description: 'Inbound throughput on each non-loopback interface.', unit: 'MB/s', step: 0.1 },
  { key: 'networkTx', label: 'Network transmit', description: 'Outbound throughput on each non-loopback interface.', unit: 'MB/s', step: 0.1 },
]

const severityOptions: Array<{ value: AlertSeverity; label: string }> = [
  { value: 'info', label: 'Info' },
  { value: 'warning', label: 'Warning' },
  { value: 'critical', label: 'Critical' },
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

// True network-level failure (request never got a response — backend process
// down/restarting) vs. a normal HTTP error response from a live server. Only
// the former means "the panel is mid-restart," which is what the reconnect
// countdown below reacts to.
function isNetworkFailure(e: any): boolean {
  return !e.response
}

// Returns whether the backend was actually reachable (a network failure
// means "no response at all," not "responded with an error").
async function loadVersionInfo(): Promise<boolean> {
  versionError.value = ''

  try {
    const res = await systemApi.version()
    versionInfo.value = res.data
    if (res.data.error) {
      versionError.value = res.data.error
    }
    return true
  } catch (e: any) {
    versionError.value = e.response?.data?.detail || 'Failed to load version status'
    return !isNetworkFailure(e)
  }
}

async function checkForUpdates() {
  if (versionInfo.value?.update_in_progress) return

  versionActionLoading.value = true
  versionError.value = ''
  versionSuccess.value = ''

  try {
    const { data } = await systemApi.checkUpdates()
    const expectedCheckId = data.check_id
    versionSuccess.value = data.message || 'Checking for updates…'

    let matchedRequest = false
    const deadline = Date.now() + 90_000
    while (Date.now() < deadline) {
      await wait(1000)
      const [reachable] = await Promise.all([loadVersionInfo(), fetchServiceLogs()])
      if (!reachable) {
        throw new Error('Backend became unreachable during the update check')
      }

      const info = versionInfo.value
      if (!info || info.check_id !== expectedCheckId) continue
      matchedRequest = true
      if (
        info.check_state === 'queued' ||
        info.check_state === 'running' ||
        info.check_in_progress
      ) {
        continue
      }
      break
    }

    const info = versionInfo.value
    if (!matchedRequest || info?.check_id !== expectedCheckId) {
      versionSuccess.value = ''
      versionError.value = 'The updater did not acknowledge this check. No version result was assumed.'
    } else if (info.check_state === 'failed' || info.status === 'check_failed') {
      versionSuccess.value = ''
      versionError.value = info.error || 'Update check failed — GitHub was unreachable.'
    } else if (info.check_state !== 'succeeded') {
      versionSuccess.value = ''
      versionError.value = 'The update check is still running. Its result will appear here when it finishes.'
    } else if (info.update_available) {
      versionSuccess.value = 'Update available!'
    } else {
      versionSuccess.value = 'Already up to date.'
    }
  } catch (e: any) {
    const detail = e.response?.data?.detail || e.response?.data?.message
    const network = e.code === 'ECONNABORTED'
      ? 'Request timed out — backend may be unreachable'
      : e.message
        ? `Update check failed: ${e.message}`
        : null
    versionError.value = detail || network || 'Failed to start update check'
  } finally {
    versionActionLoading.value = false
  }
}

const installing = ref(false)

// This value comes directly from the updater status file. It advances only
// when the server enters a real phase; old journal entries and browser timers
// cannot move it.
const updateProgressPercent = computed(() => {
  const value = versionInfo.value?.progress_percent
  if (typeof value !== 'number' || !Number.isFinite(value)) return 1
  return Math.min(100, Math.max(0, Math.round(value)))
})

const updateStepLabel = computed(() =>
  versionInfo.value?.progress_label || 'Waiting for updater status',
)

// ── Restart countdown ────────────────────────────────────────────────────
// The updater announces the restart immediately before it stops the backend.
// Probe throughout the countdown and reload as soon as the new backend reports
// that the operation completed (or after an observed disconnect/reconnect).
// Never reset the countdown indefinitely: after one bounded window, give the
// user explicit retry/reload controls.
const restarting = ref(false)
const restartCountdown = ref(0)
const restartTimedOut = ref(false)
let restartCountdownTimer: ReturnType<typeof setInterval> | null = null
let restartProbeTimer: ReturnType<typeof setTimeout> | null = null
let restartProbeInFlight = false
let restartDeadline = 0
let restartOperationId: string | null = null
let restartObservedOffline = false
let restartGeneration = 0

function stopRestartCountdown() {
  restartGeneration += 1
  if (restartCountdownTimer) {
    clearInterval(restartCountdownTimer)
    restartCountdownTimer = null
  }
  if (restartProbeTimer) {
    clearTimeout(restartProbeTimer)
    restartProbeTimer = null
  }
  restartProbeInFlight = false
}

function reloadPanel() {
  stopRestartCountdown()
  const url = new URL(window.location.href)
  url.searchParams.set('_restart', Date.now().toString())
  window.location.replace(url.toString())
}

async function probeRestart(generation: number) {
  if (!restarting.value || restartTimedOut.value || generation !== restartGeneration) return
  if (restartProbeInFlight) return

  restartProbeInFlight = true
  const reachable = await loadVersionInfo()
  restartProbeInFlight = false

  if (!restarting.value || generation !== restartGeneration) return

  if (!reachable) {
    restartObservedOffline = true
  } else {
    const info = versionInfo.value
    const operationMatches = !restartOperationId || info?.operation_id === restartOperationId
    const operationFinished = Boolean(
      info &&
        operationMatches &&
        !info.restart_pending &&
        (info.operation_state === 'succeeded' || info.restart_performed),
    )

    if (restartObservedOffline || operationFinished) {
      reloadPanel()
      return
    }
  }

  if (Date.now() >= restartDeadline) {
    stopRestartCountdown()
    restartCountdown.value = 0
    restartTimedOut.value = true
    return
  }

  restartProbeTimer = setTimeout(() => void probeRestart(generation), 2000)
}

function startRestartCountdown(seconds = 60, operationId: string | null = null) {
  if (restarting.value && !restartTimedOut.value) return

  stopRestartCountdown()
  restarting.value = true
  restartTimedOut.value = false
  restartCountdown.value = seconds
  restartDeadline = Date.now() + seconds * 1000
  restartOperationId = operationId ?? versionInfo.value?.operation_id ?? null
  restartObservedOffline = false
  const generation = restartGeneration

  restartCountdownTimer = setInterval(() => {
    if (restartCountdown.value > 0) {
      restartCountdown.value -= 1
    }
  }, 1000)

  void probeRestart(generation)
}

function retryRestartConnection() {
  startRestartCountdown(60, restartOperationId)
}

onUnmounted(stopRestartCountdown)

async function pollInstallProgress(operationId: string) {
  installing.value = true
  let matchedRequest = false
  const deadline = Date.now() + 20 * 60_000

  while (Date.now() < deadline && !restarting.value) {
    const [reachable] = await Promise.all([loadVersionInfo(), fetchServiceLogs()])
    if (!reachable) {
      startRestartCountdown(60, operationId)
      return
    }

    const info = versionInfo.value
    if (!info || info.operation_id !== operationId) {
      await wait(1000)
      continue
    }
    matchedRequest = true

    if (info.restart_pending) {
      versionSuccess.value = 'The new release is ready. The backend is restarting now.'
      startRestartCountdown(60, operationId)
      return
    }
    if (info.operation_state === 'failed') {
      versionSuccess.value = ''
      versionError.value = info.error || info.progress_label || 'Update failed.'
      installing.value = false
      return
    }
    if (info.operation_state === 'succeeded') {
      if (info.restart_performed) {
        versionSuccess.value = 'Update installed. Reconnecting to the restarted panel…'
        startRestartCountdown(60, operationId)
      } else {
        versionSuccess.value = info.progress_label || 'Already up to date.'
        installing.value = false
        await loadVersionInfo()
      }
      return
    }
    if (
      info.operation_state === 'queued' ||
      info.operation_state === 'running' ||
      info.update_in_progress
    ) {
      await wait(2000)
      continue
    }

    versionSuccess.value = ''
    versionError.value = 'The updater stopped without reporting a final result.'
    installing.value = false
    return
  }

  if (!restarting.value) {
    versionSuccess.value = ''
    versionError.value = matchedRequest
      ? 'The update is still running after 20 minutes. Check the service logs below.'
      : 'The updater did not acknowledge this installation request.'
    installing.value = false
  }
}

async function installUpdate() {
  if (
    !versionInfo.value?.update_available ||
    versionInfo.value.update_in_progress ||
    versionInfo.value.check_in_progress
  ) return

  const targetVersion = versionInfo.value.latest_version ?? 'the latest version'
  const confirmed = await dialog.confirm({
    title: 'Install update',
    message: `Install CarbonPanel ${targetVersion} now? Live server progress will remain visible, followed by an automatic reconnect.`,
    confirmLabel: 'Install',
  })

  if (!confirmed) return

  versionActionLoading.value = true
  versionError.value = ''
  versionSuccess.value = ''
  installing.value = true

  try {
    const { data } = await systemApi.installUpdate()
    versionSuccess.value = data.message || 'Installing update…'
    await pollInstallProgress(data.operation_id)
  } catch (e: any) {
    const detail = e.response?.data?.detail || e.response?.data?.message
    const network = e.code === 'ECONNABORTED'
      ? 'Request timed out — backend may be unreachable'
      : e.message ? `Network error: ${e.message}` : null
    versionError.value = detail || network || 'Failed to start update installation'
    installing.value = false
  } finally {
    versionActionLoading.value = false
  }
}

const setupData = ref<{ secret: string; otpauth_uri: string } | null>(null)
const setupLoading = ref(false)
const setupPassword = ref('')
const setupError = ref('')
const qrCanvas = ref<HTMLCanvasElement | null>(null)

const confirmCode = ref('')
const enableLoading = ref(false)
const enableError = ref('')

const disablePassword = ref('')
const disableCode = ref('')
const disableLoading = ref(false)
const disableError = ref('')

async function startSetup() {
  if (!setupPassword.value) return
  setupLoading.value = true
  setupError.value = ''
  try {
    const res = await settingsApi.setup2fa(setupPassword.value)
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
    setupError.value = e.response?.data?.detail || 'Could not start 2FA setup'
  } finally {
    setupLoading.value = false
  }
}

async function handleEnable() {
  if (confirmCode.value.length !== 6) return
  enableError.value = ''
  enableLoading.value = true
  try {
    await settingsApi.enable2fa(setupPassword.value, confirmCode.value)
    await auth.loadUser()
    setupData.value = null
    setupPassword.value = ''
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
    await settingsApi.disable2fa(disablePassword.value, disableCode.value)
    await auth.loadUser()
    disablePassword.value = ''
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

// Notifications
type SmtpSecurity = 'starttls' | 'ssl' | 'none'

const webhooks = ref<WebhookResponse[]>([])
const newWebhookKind = ref<NotificationKind>('ntfy')
const newWebhookUrl = ref('http://127.0.0.1:8080')
const newWebhookLabel = ref('')
const newNtfyTopic = ref('carbonpanel-alerts')
const newNtfyToken = ref('')
const newSmtpHost = ref('')
const newSmtpPort = ref('587')
const newSmtpSecurity = ref<SmtpSecurity>('starttls')
const newSmtpUsername = ref('')
const newSmtpPassword = ref('')
const newEmailFrom = ref('')
const newEmailTo = ref('')
const newWebhookEvents = ref<string[]>([
  'alert.cpu',
  'alert.ram',
  'alert.disk',
  'alert.gpu',
  'alert.gpu_temperature',
  'alert.network_rx',
  'alert.network_tx',
])
const webhookLoading = ref(false)
const webhookError = ref('')
const webhookSuccess = ref('')

const notificationKinds: { value: NotificationKind; label: string }[] = [
  { value: 'ntfy', label: 'ntfy' },
  { value: 'email', label: 'Email' },
  { value: 'webhook', label: 'Webhook' },
]
const smtpSecurityModes: { value: SmtpSecurity; label: string }[] = [
  { value: 'starttls', label: 'STARTTLS' },
  { value: 'ssl', label: 'SSL/TLS' },
  { value: 'none', label: 'None (local)' },
]
const webhookEventOptions = [
  { value: 'alert.cpu', label: 'CPU usage', short: 'CPU' },
  { value: 'alert.ram', label: 'RAM usage', short: 'RAM' },
  { value: 'alert.disk', label: 'Disk usage', short: 'Disk' },
  { value: 'alert.gpu', label: 'GPU utilization', short: 'GPU' },
  { value: 'alert.gpu_temperature', label: 'GPU temperature', short: 'Temp' },
  { value: 'alert.network_rx', label: 'Network receive', short: 'RX' },
  { value: 'alert.network_tx', label: 'Network transmit', short: 'TX' },
]

const canAddNotification = computed(() => {
  if (!newWebhookEvents.value.length) return false
  if (newWebhookKind.value === 'webhook') return Boolean(newWebhookUrl.value.trim())
  if (newWebhookKind.value === 'ntfy') {
    return Boolean(newWebhookUrl.value.trim() && newNtfyTopic.value.trim())
  }
  return Boolean(
    newSmtpHost.value.trim() &&
    newSmtpPort.value &&
    newEmailFrom.value.trim() &&
    newEmailTo.value.trim() &&
    Boolean(newSmtpUsername.value) === Boolean(newSmtpPassword.value),
  )
})

function channelKindLabel(kind: NotificationKind) {
  if (kind === 'ntfy') return 'ntfy'
  return kind === 'email' ? 'Email' : 'Webhook'
}

function channelTarget(channel: WebhookResponse) {
  if (channel.kind === 'ntfy') return `${channel.url} / ${channel.topic}`
  if (channel.kind === 'email') {
    return `${channel.email_to} via ${channel.smtp_host}:${channel.smtp_port}`
  }
  return channel.url
}

function selectNotificationKind(kind: NotificationKind) {
  newWebhookKind.value = kind
  webhookError.value = ''
  webhookSuccess.value = ''
  if (kind === 'ntfy' && !newWebhookUrl.value) {
    newWebhookUrl.value = 'http://127.0.0.1:8080'
  } else if (kind === 'email') {
    newWebhookUrl.value = ''
  }
}

function selectSmtpSecurity(mode: SmtpSecurity) {
  const oldDefault = ['25', '465', '587'].includes(newSmtpPort.value)
  newSmtpSecurity.value = mode
  if (oldDefault) {
    newSmtpPort.value = mode === 'ssl' ? '465' : mode === 'starttls' ? '587' : '25'
  }
}

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
  if (!canAddNotification.value) return
  webhookLoading.value = true
  try {
    const payload: WebhookCreate = {
      kind: newWebhookKind.value,
      label: newWebhookLabel.value,
      events: newWebhookEvents.value,
    }
    if (newWebhookKind.value === 'webhook') {
      payload.url = newWebhookUrl.value.trim()
    } else if (newWebhookKind.value === 'ntfy') {
      payload.url = newWebhookUrl.value.trim()
      payload.topic = newNtfyTopic.value.trim()
      if (newNtfyToken.value) payload.token = newNtfyToken.value
    } else {
      payload.smtp_host = newSmtpHost.value.trim()
      payload.smtp_port = Number.parseInt(newSmtpPort.value, 10)
      payload.smtp_security = newSmtpSecurity.value
      payload.email_from = newEmailFrom.value.trim()
      payload.email_to = newEmailTo.value.trim()
      if (newSmtpUsername.value) payload.smtp_username = newSmtpUsername.value
      if (newSmtpPassword.value) payload.smtp_password = newSmtpPassword.value
    }
    await webhooksApi.create(payload)
    newWebhookLabel.value = ''
    newNtfyToken.value = ''
    newSmtpPassword.value = ''
    webhookSuccess.value = t('settings.notificationAdded')
    await loadWebhooks()
  } catch (e: any) {
    webhookError.value = e.response?.data?.detail || t('settings.notificationSaveFailed')
  } finally {
    webhookLoading.value = false
  }
}

async function toggleWebhook(wh: WebhookResponse) {
  webhookError.value = ''
  try {
    await webhooksApi.update(wh.id, { enabled: !wh.enabled })
    await loadWebhooks()
  } catch (e: any) {
    webhookError.value = e.response?.data?.detail || t('settings.notificationSaveFailed')
  }
}

async function toggleWebhookEvent(wh: WebhookResponse, event: string) {
  webhookError.value = ''
  webhookSuccess.value = ''
  const events = wh.events.includes(event)
    ? wh.events.filter((value) => value !== event)
    : [...wh.events, event]
  if (!events.length) {
    webhookError.value = 'Each notification channel must subscribe to at least one event.'
    return
  }
  try {
    await webhooksApi.update(wh.id, { events })
    await loadWebhooks()
  } catch (e: any) {
    webhookError.value = e.response?.data?.detail || t('settings.notificationSaveFailed')
  }
}

async function deleteWebhook(id: string) {
  const confirmed = await dialog.confirm({
    title: t('settings.deleteNotification'),
    message: t('settings.deleteNotificationConfirm'),
    confirmLabel: t('common.delete'),
    variant: 'danger',
  })
  if (!confirmed) return
  await webhooksApi.delete(id)
  await loadWebhooks()
}

async function testWebhook(wh: WebhookResponse) {
  webhookError.value = ''
  webhookSuccess.value = ''
  try {
    await webhooksApi.test(wh.id)
    webhookSuccess.value = t('settings.notificationTestSent')
  } catch (e: any) {
    webhookError.value = e.response?.data?.detail || t('settings.notificationTestFailed')
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

// ── Pairing ────────────────────────────────────────────────────────────────────

const discoveredEndpoints = ref<PairingEndpoint[]>([])
const extraEndpoints = ref<string[]>([])
const selectedEndpoints = ref<string[]>([])
const newEndpoint = ref('')
const endpointError = ref('')
const pairing = ref<PairingStart | null>(null)
const pairAuthPassword = ref('')
const pairAuthTotp = ref('')
const pairingBusy = ref(false)
const pairStatus = ref<'pending' | 'claimed' | 'expired'>('pending')
const pairedName = ref<string | null>(null)
const pairCountdown = ref(0)
let pairPoll: ReturnType<typeof setInterval> | null = null
let pairTick: ReturnType<typeof setInterval> | null = null

const pairedCount = computed(() => devices.value.filter(d => d.kind === 'android').length)

// Manually-added URLs the server hasn't detected on an interface still belong
// in the list — they're usually the only ones that work from outside the LAN.
const allEndpoints = computed<PairingEndpoint[]>(() => {
  const seen = new Set(discoveredEndpoints.value.map(e => e.url))
  const extras = extraEndpoints.value
    .filter(u => !seen.has(u))
    .map(u => ({ url: u, kind: 'custom' as const, label: 'Configured manually' }))
  return [...extras, ...discoveredEndpoints.value]
})

const pairStatusClass = computed(() => ({
  'pair-ok': pairStatus.value === 'claimed',
  'pair-stale': pairStatus.value === 'expired',
}))

// Drains as the code ages. Guarded against a zero expires_in so a bad
// response can't produce a NaN width.
const pairTimerPct = computed(() => {
  const total = pairing.value?.expires_in || 0
  if (total <= 0) return 0
  return Math.max(0, Math.min(100, (pairCountdown.value / total) * 100))
})

function endpointKindLabel(kind: string) {
  switch (kind) {
    case 'overlay': return 'VPN — works anywhere'
    case 'custom':  return 'manual'
    case 'current': return 'this browser'
    case 'lan':     return 'LAN only'
    case 'public':  return 'public'
    default:        return kind
  }
}

async function loadEndpoints() {
  try {
    const { data } = await pairingApi.endpoints()
    discoveredEndpoints.value = data.discovered
    extraEndpoints.value = data.extra
    if (!selectedEndpoints.value.length) {
      // Default to everything reachable off-LAN plus the address that's
      // demonstrably working right now.
      selectedEndpoints.value = allEndpoints.value
        .filter(e => e.kind !== 'public')
        .map(e => e.url)
    }
  } catch { /* section just stays empty */ }
}

async function addEndpoint() {
  const url = newEndpoint.value.trim().replace(/\/+$/, '')
  if (!url) return
  endpointError.value = ''
  try {
    const { data } = await pairingApi.setEndpoints([...extraEndpoints.value, url])
    extraEndpoints.value = data.extra
    discoveredEndpoints.value = data.discovered
    if (!selectedEndpoints.value.includes(url)) selectedEndpoints.value.push(url)
    newEndpoint.value = ''
  } catch (e: any) {
    endpointError.value = e.response?.data?.detail || 'Could not save that address.'
  }
}

function stopPairPolling() {
  if (pairPoll) { clearInterval(pairPoll); pairPoll = null }
  if (pairTick) { clearInterval(pairTick); pairTick = null }
}

async function startPairing() {
  pairingBusy.value = true
  endpointError.value = ''
  stopPairPolling()
  try {
    const { data } = await pairingApi.start(
      selectedEndpoints.value,
      pairAuthPassword.value,
      pairAuthTotp.value || undefined,
    )
    pairing.value = data
    pairStatus.value = 'pending'
    pairedName.value = null
    pairCountdown.value = data.expires_in
    pairAuthPassword.value = ''
    pairAuthTotp.value = ''

    pairTick = setInterval(() => {
      if (pairCountdown.value > 0) pairCountdown.value--
    }, 1000)

    pairPoll = setInterval(async () => {
      if (!pairing.value) return
      try {
        const { data: s } = await pairingApi.status(pairing.value.code)
        pairStatus.value = s.status
        if (s.status === 'claimed') {
          pairedName.value = s.device_name
          stopPairPolling()
          void loadDevices()
        } else if (s.status === 'expired') {
          stopPairPolling()
        }
      } catch { /* keep polling */ }
    }, 2000)
  } catch (e: any) {
    endpointError.value = e.response?.data?.detail || 'Could not start pairing.'
  } finally {
    pairingBusy.value = false
  }
}

function cancelPairing() {
  stopPairPolling()
  pairing.value = null
}

onUnmounted(stopPairPolling)

function fmtDate(iso: string) {
  try {
    return new Date(iso).toLocaleString()
  } catch { return iso }
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
  } catch (e: any) {
    // Was previously a silent no-op — a failed fetch here looked identical
    // to "no proxy configured," which is exactly backwards for a feature
    // whose entire point is "make requests work when the network is
    // unreliable." Surface it instead of quietly showing the default.
    proxyError.value = e.response?.data?.detail || 'Failed to load proxy settings.'
  }
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

// Every other settings section in this page auto-saves the instant you
// change something — Proxy used to be the one exception, requiring a
// separate "Save" click after toggling. That mismatch is exactly what led
// to "I turned it on but it's still off": the toggle alone never reached
// the server. These wrappers make on/off and type auto-save immediately,
// same as clicking Save used to; host/port auto-save on blur instead of on
// every keystroke (see the @blur binding in the template).
function setProxyEnabled(enabled: boolean) {
  proxy.value.enabled = enabled
  void saveProxy()
}

function setProxyType(type: ProxyConfig['type']) {
  proxy.value.type = type
  void saveProxy()
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

onMounted(async () => {
  void loadWebhooks()
  void loadProxy()
  void loadDevices()
  void loadEndpoints()

  await Promise.all([loadVersionInfo(), fetchServiceLogs()])
  // An install kicked off from this page (or another tab/session) can still
  // be running server-side after this component remounts — resume showing
  // live progress instead of a blank slate.
  const operationId = versionInfo.value?.operation_id
  const operationState = versionInfo.value?.operation_state
  if (
    operationId &&
    (versionInfo.value?.update_in_progress ||
      operationState === 'queued' ||
      operationState === 'running')
  ) {
    installing.value = true
    if (versionInfo.value?.restart_pending) startRestartCountdown(60, operationId)
    else void pollInstallProgress(operationId)
  }
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

.commit-id {
  margin-left: 5px;
  color: var(--fg-dim);
  font-size: 10px;
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
.webhook-label-line { display: flex; align-items: center; gap: 7px; }
.webhook-label { font-size: 11px; font-weight: 500; color: var(--fg); }
.notification-kind { font-size: 9px; color: var(--accent); text-transform: uppercase; letter-spacing: 0.06em; }
.webhook-url { font-size: 10px; color: var(--fg-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.notification-event-chips { display: flex; flex-wrap: wrap; gap: 3px; margin-top: 4px; }
.notification-event-chip {
  padding: 2px 5px;
  color: var(--fg-dim);
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 999px;
  font: 8px var(--font);
  cursor: pointer;
  transition: color var(--transition), border-color var(--transition), background var(--transition);
}
.notification-event-chip:hover { color: var(--fg-muted); border-color: var(--fg-dim); }
.notification-event-chip.active {
  color: var(--accent);
  border-color: var(--accent-border);
  background: var(--accent-dim);
}
.webhook-actions { display: flex; gap: 6px; flex-shrink: 0; }
.wh-toggle.active { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }
.wh-del:hover { border-color: rgba(255,68,68,0.4); color: var(--danger); }
.wh-test:hover { border-color: rgba(100,180,255,0.4); color: #60a5fa; }
.webhook-add-form { display: flex; flex-direction: column; gap: 10px; padding-top: 6px; border-top: 1px solid var(--border-subtle); }
.wh-events { display: flex; flex-direction: column; gap: 6px; }
.smtp-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 10px; }
.credential-note { margin: -3px 0 0; color: var(--fg-dim); font-size: 9.5px; line-height: 1.45; }
@media (max-width: 640px) { .smtp-grid { grid-template-columns: 1fr; } }

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
.theme-btn:disabled { opacity: 0.5; cursor: default; }
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
  flex-direction: column;
  gap: 7px;
  margin-top: 4px;
  animation: slide-in 150ms ease;
}
.update-progress-copy {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.update-progress-track {
  width: 100%;
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
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 11px;
  color: var(--fg-muted);
  white-space: nowrap;
}
.update-progress-percent {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
}

.restart-countdown {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px;
  border-radius: var(--radius);
  border: 1px solid var(--accent-border);
  background: var(--accent-dim);
  animation: slide-in 150ms ease;
}
.restart-countdown-num {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 2px solid var(--accent-border);
  color: var(--accent);
  font-size: 15px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.restart-countdown-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.restart-countdown-copy strong { font-size: 12px; color: var(--fg); }
.restart-countdown-copy span { font-size: 11px; color: var(--fg-muted); line-height: 1.5; }
.restart-countdown-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 7px; }
.restart-countdown-timeout {
  border-color: color-mix(in srgb, var(--warning) 45%, transparent);
  background: var(--warning-dim);
}
.restart-countdown-timeout .restart-countdown-num {
  border-color: color-mix(in srgb, var(--warning) 45%, transparent);
  color: var(--warning);
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

.alert-rules { display: flex; flex-direction: column; gap: 10px; }
.alert-rule {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}
.alert-rule-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.alert-rule-label { font-size: 11px; font-weight: 600; color: var(--fg); }
.alert-rule-desc {
  margin: 3px 0 0;
  font-size: 9.5px;
  line-height: 1.45;
  color: var(--fg-dim);
}
.alert-rule-controls {
  display: grid;
  grid-template-columns: minmax(120px, 0.75fr) minmax(260px, 1.25fr);
  gap: 12px;
  align-items: end;
}
.alert-threshold-field,
.alert-severity-control {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.alert-threshold-input-wrap {
  display: flex;
  align-items: center;
  overflow: hidden;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  transition: border-color var(--transition);
}
.alert-threshold-input-wrap:focus-within { border-color: var(--accent); }
.alert-threshold-input {
  width: 100%;
  min-width: 0;
  padding: 7px 8px;
  color: var(--fg);
  background: transparent;
  border: 0;
  outline: 0;
  font: 11px var(--font);
}
.alert-threshold-unit {
  padding: 0 8px;
  color: var(--fg-dim);
  font-size: 10px;
  white-space: nowrap;
}
.alert-off-note { color: var(--fg-dim); font-size: 9px; }
.alert-severity-badge {
  flex-shrink: 0;
  padding: 2px 6px;
  border: 1px solid;
  border-radius: 999px;
  font-size: 8.5px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.alert-severity-badge.severity-info { color: #60a5fa; border-color: color-mix(in srgb, #60a5fa 40%, transparent); }
.alert-severity-badge.severity-warning { color: var(--warning); border-color: color-mix(in srgb, var(--warning) 40%, transparent); }
.alert-severity-badge.severity-critical { color: var(--danger); border-color: color-mix(in srgb, var(--danger) 40%, transparent); }
.severity-btn.active.severity-info { color: #60a5fa; border-color: color-mix(in srgb, #60a5fa 50%, transparent); background: color-mix(in srgb, #60a5fa 10%, transparent); }
.severity-btn.active.severity-warning { color: var(--warning); border-color: color-mix(in srgb, var(--warning) 50%, transparent); background: var(--warning-dim); }
.severity-btn.active.severity-critical { color: var(--danger); border-color: color-mix(in srgb, var(--danger) 50%, transparent); background: var(--danger-dim); }
@media (max-width: 640px) {
  .alert-rule-controls { grid-template-columns: 1fr; }
}

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

/* Devices section */
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

/* Paired devices / QR pairing */
.pair-endpoints { margin-top: 4px; }
.pair-subhead { font-size: 11px; color: var(--fg-muted); margin-bottom: 4px; }
.pair-hint { font-size: 10px; color: var(--fg-dim); line-height: 1.5; margin: 0 0 8px; }
.pair-ep-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  margin-bottom: 4px;
  cursor: pointer;
  transition: border-color var(--transition);
}
.pair-ep-row:hover { border-color: var(--accent); }
.pair-ep-url {
  font-size: 11px; color: var(--fg); flex: 1;
  min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
}
.pair-ep-kind {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
  flex-shrink: 0;
  color: var(--fg-dim);
  background: var(--bg-card);
  border: 1px solid var(--border);
}
.pair-ep-kind.kind-overlay { color: var(--accent); border-color: var(--accent); }
.pair-ep-kind.kind-lan { color: var(--warning); border-color: var(--warning); }
.pair-add-row { display: flex; gap: 8px; margin-top: 8px; align-items: center; }
.pair-add-row > :first-child { flex: 1; }
.pair-actions { display: flex; gap: 8px; margin-top: 12px; }
.pair-panel {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  margin-top: 12px;
  padding: 18px;
  background:
    radial-gradient(120% 100% at 0% 0%, rgba(0, 255, 136, 0.05), transparent 60%),
    var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  transition: border-color var(--transition), background var(--transition);
}
.pair-panel--done { border-color: var(--accent); }

/* Viewfinder framing — corner brackets around the code. */
.pair-qr-frame {
  position: relative;
  flex-shrink: 0;
  padding: 10px;
  border-radius: var(--radius);
  background: #fff;
}
.pair-corner {
  position: absolute;
  width: 16px; height: 16px;
  border: 2px solid var(--accent);
  transition: border-color var(--transition);
}
.pair-corner--tl { top: -3px; left: -3px;  border-right: none; border-bottom: none; border-radius: 5px 0 0 0; }
.pair-corner--tr { top: -3px; right: -3px; border-left: none;  border-bottom: none; border-radius: 0 5px 0 0; }
.pair-corner--bl { bottom: -3px; left: -3px;  border-right: none; border-top: none; border-radius: 0 0 0 5px; }
.pair-corner--br { bottom: -3px; right: -3px; border-left: none;  border-top: none; border-radius: 0 0 5px 0; }
.pair-qr-frame.is-stale .pair-corner { border-color: var(--warning); }

.pair-qr {
  display: block;
  width: 168px; height: 168px;
  image-rendering: pixelated;   /* keep the modules crisp when upscaled */
  border-radius: 2px;
}
/* Covers the code once it can no longer be used, so nobody scans a dead one. */
.pair-qr-veil {
  position: absolute; inset: 10px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(10, 14, 13, 0.88);
  color: var(--accent);
  font-size: 44px;
  border-radius: 2px;
}
.pair-qr-veil--stale { color: var(--warning); font-size: 13px; letter-spacing: 1px; }

.pair-side {
  display: flex; flex-direction: column; gap: 14px;
  min-width: 0; flex: 1;
}

.pair-steps { display: flex; flex-direction: column; gap: 8px; }
.pair-step {
  display: flex; align-items: flex-start; gap: 10px;
  font-size: 11px; color: var(--fg-muted); line-height: 1.5;
}
.pair-step i {
  flex-shrink: 0;
  width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: rgba(0, 255, 136, 0.14);
  color: var(--accent);
  font-style: normal; font-size: 10px;
}
.pair-step b { color: var(--fg); font-weight: 500; }

.pair-status {
  display: flex; align-items: center; gap: 7px;
  font-size: 11px; color: var(--fg-muted);
}
.pair-status.pair-ok { color: var(--accent); }
.pair-status.pair-stale { color: var(--warning); }
.pair-pulse {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--accent);
  animation: pair-pulse 1.6s ease-in-out infinite;
}
@keyframes pair-pulse {
  0%, 100% { opacity: 1;   transform: scale(1); }
  50%      { opacity: 0.35; transform: scale(0.72); }
}
/* Respect a reduced-motion preference rather than pulsing regardless. */
@media (prefers-reduced-motion: reduce) {
  .pair-pulse { animation: none; }
}

.pair-timer { display: flex; align-items: center; gap: 8px; }
.pair-timer-bar {
  flex: 1; height: 3px;
  background: var(--bg-card);
  border-radius: 2px; overflow: hidden;
}
.pair-timer-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width 1s linear;
}
.pair-timer-text { font-size: 10px; color: var(--fg-dim); min-width: 26px; text-align: right; }

.pair-manual { display: flex; flex-direction: column; gap: 5px; }
.pair-manual-label { font-size: 10px; color: var(--fg-dim); }
.pair-code {
  font-family: var(--font);
  font-size: 20px;
  letter-spacing: 4px;
  color: var(--fg);
  background: var(--bg-card);
  border: 1px dashed var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  text-align: center;
  user-select: all;   /* one click selects the whole code for copying */
}

@media (max-width: 560px) {
  .pair-panel { flex-direction: column; }
}
</style>
