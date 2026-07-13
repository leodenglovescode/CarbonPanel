<template>
  <Teleport to="body">
    <div v-if="open" class="cp-overlay" @click.self="close">
      <div class="cp-panel">
        <input
          ref="inputEl"
          v-model="query"
          class="cp-input"
          placeholder="Search pages, settings, sites, containers…"
          @keydown="onKeydown"
        />
        <div class="cp-results">
          <template v-for="group in groupedResults" :key="group.label">
            <div class="cp-group-label">{{ group.label }}</div>
            <button
              v-for="item in group.items"
              :key="item.key"
              type="button"
              class="cp-item"
              :class="{ active: isActive(item) }"
              @mouseenter="hoverIndex = flatIndex(item)"
              @click="select(item)"
            >
              <span class="cp-item-label">{{ item.label }}</span>
              <span v-if="item.sub" class="cp-item-sub">{{ item.sub }}</span>
            </button>
          </template>
          <div v-if="!flatResults.length" class="cp-empty">No matches</div>
        </div>
        <div class="cp-footer">
          <span>↑↓ navigate</span><span>↵ select</span><span>esc close</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useLocaleStore } from '@/stores/locale'
import { sitesApi, dockerApi } from '@/api'

interface PaletteItem {
  key: string
  label: string
  sub?: string
  category: string
  go: () => void
}

const router = useRouter()
const { t } = useLocaleStore()

const open = ref(false)
const query = ref('')
const hoverIndex = ref(0)
const inputEl = ref<HTMLInputElement | null>(null)

const pages: PaletteItem[] = [
  { key: 'page-/', label: t('nav.stats'), category: 'Pages', go: () => router.push('/') },
  { key: 'page-/sites', label: t('nav.sites'), category: 'Pages', go: () => router.push('/sites') },
  { key: 'page-/system-services', label: t('nav.systemServices'), category: 'Pages', go: () => router.push('/system-services') },
  { key: 'page-/disks', label: t('nav.disks'), category: 'Pages', go: () => router.push('/disks') },
  { key: 'page-/apps', label: t('nav.apps'), category: 'Pages', go: () => router.push('/apps') },
  { key: 'page-/docker', label: t('nav.docker'), category: 'Pages', go: () => router.push('/docker') },
  { key: 'page-/logs', label: t('nav.logs'), category: 'Pages', go: () => router.push('/logs') },
  { key: 'page-/cron', label: t('nav.cron'), category: 'Pages', go: () => router.push('/cron') },
  { key: 'page-/sessions', label: t('nav.sessions'), category: 'Pages', go: () => router.push('/sessions') },
  { key: 'page-/settings', label: t('nav.settings'), category: 'Pages', go: () => router.push('/settings') },
]

function goSettings(id: string) {
  router.push({ path: '/settings', hash: `#${id}` })
}

// ponytail: mirrors SettingsView.vue's navSections — keep in sync if sections change there
const settingsSections: PaletteItem[] = [
  { key: 'set-appearance', label: 'Appearance', category: 'Settings', go: () => goSettings('section-appearance') },
  { key: 'set-style', label: 'Stylistic', category: 'Settings', go: () => goSettings('section-style') },
  { key: 'set-backgrounds', label: 'Backgrounds', category: 'Settings', go: () => goSettings('section-backgrounds') },
  { key: 'set-display', label: 'Display', category: 'Settings', go: () => goSettings('section-display') },
  { key: 'set-frequency', label: 'Frequency', category: 'Settings', go: () => goSettings('section-frequency') },
  { key: 'set-alerts', label: 'Alerts', category: 'Settings', go: () => goSettings('section-alerts') },
  { key: 'set-version', label: 'Version', category: 'Settings', go: () => goSettings('section-version') },
  { key: 'set-2fa', label: '2FA', category: 'Settings', go: () => goSettings('section-2fa') },
  { key: 'set-account', label: 'Account', category: 'Settings', go: () => goSettings('section-account') },
  { key: 'set-language', label: t('settings.language'), category: 'Settings', go: () => goSettings('section-language') },
  { key: 'set-webhooks', label: t('settings.webhooks'), category: 'Settings', go: () => goSettings('section-webhooks') },
  { key: 'set-devices', label: 'Sessions', category: 'Settings', go: () => goSettings('section-devices') },
  { key: 'set-passkeys', label: 'Passkeys', category: 'Settings', go: () => goSettings('section-passkeys') },
  { key: 'set-proxy', label: 'Proxy', category: 'Settings', go: () => goSettings('section-proxy') },
]

const sites = ref<{ id: string; name: string }[]>([])
const containers = ref<{ id: string; name: string }[]>([])
const services = ref<{ service_name: string }[]>([])
let dynamicLoaded = false

async function loadDynamic() {
  if (dynamicLoaded) return
  dynamicLoaded = true
  const [sitesRes, containersRes, servicesRes] = await Promise.allSettled([
    sitesApi.list(),
    dockerApi.list(),
    sitesApi.listSystemServices(),
  ])
  if (sitesRes.status === 'fulfilled') sites.value = sitesRes.value.data
  if (containersRes.status === 'fulfilled') containers.value = containersRes.value.data
  if (servicesRes.status === 'fulfilled') services.value = servicesRes.value.data
}

const dynamicItems = computed<PaletteItem[]>(() => [
  ...sites.value.map((s): PaletteItem => ({
    key: `site-${s.id}`, label: s.name, sub: 'Site', category: 'Sites',
    go: () => router.push({ name: 'site-detail', params: { id: s.id } }),
  })),
  ...containers.value.map((c): PaletteItem => ({
    key: `container-${c.id}`, label: c.name, sub: 'Container', category: 'Docker',
    go: () => router.push('/docker'),
  })),
  ...services.value.map((s): PaletteItem => ({
    key: `service-${s.service_name}`, label: s.service_name, sub: 'Service', category: 'System Services',
    go: () => router.push('/system-services'),
  })),
])

const allItems = computed<PaletteItem[]>(() => [...pages, ...settingsSections, ...dynamicItems.value])

const flatResults = computed<PaletteItem[]>(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return [...pages, ...settingsSections]
  return allItems.value
    .filter((i) => i.label.toLowerCase().includes(q) || i.category.toLowerCase().includes(q))
    .sort((a, b) => {
      const aStarts = a.label.toLowerCase().startsWith(q) ? 0 : 1
      const bStarts = b.label.toLowerCase().startsWith(q) ? 0 : 1
      return aStarts - bStarts
    })
    .slice(0, 30)
})

const groupedResults = computed(() => {
  const groups = new Map<string, PaletteItem[]>()
  for (const item of flatResults.value) {
    if (!groups.has(item.category)) groups.set(item.category, [])
    groups.get(item.category)!.push(item)
  }
  return Array.from(groups.entries()).map(([label, items]) => ({ label, items }))
})

function flatIndex(item: PaletteItem): number {
  return flatResults.value.findIndex((i) => i.key === item.key)
}

function isActive(item: PaletteItem): boolean {
  return flatResults.value[hoverIndex.value]?.key === item.key
}

function select(item: PaletteItem) {
  item.go()
  close()
}

async function openPalette() {
  open.value = true
  void loadDynamic()
  await nextTick()
  inputEl.value?.focus()
}

function close() {
  open.value = false
  query.value = ''
  hoverIndex.value = 0
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    hoverIndex.value = Math.min(hoverIndex.value + 1, flatResults.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    hoverIndex.value = Math.max(hoverIndex.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const item = flatResults.value[hoverIndex.value]
    if (item) select(item)
  } else if (e.key === 'Escape') {
    close()
  }
}

watch(query, () => { hoverIndex.value = 0 })

function onGlobalKeydown(e: KeyboardEvent) {
  if (e.key.toLowerCase() === 'k' && (e.metaKey || e.ctrlKey)) {
    e.preventDefault()
    if (open.value) close()
    else void openPalette()
  }
}

onMounted(() => window.addEventListener('keydown', onGlobalKeydown))
onUnmounted(() => window.removeEventListener('keydown', onGlobalKeydown))
</script>

<style scoped>
.cp-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  padding-top: 12vh;
}

.cp-panel {
  width: min(560px, 92vw);
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  background: color-mix(in srgb, var(--bg-card) 90%, transparent);
  backdrop-filter: blur(14px);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-card-hover);
  overflow: hidden;
}

.cp-input {
  width: 100%;
  padding: 14px 16px;
  background: none;
  border: none;
  border-bottom: 1px solid var(--border);
  color: var(--fg);
  font-family: var(--font);
  font-size: 14px;
  outline: none;
}
.cp-input::placeholder { color: var(--fg-dim); }

.cp-results { overflow-y: auto; padding: 6px; flex: 1; }

.cp-group-label {
  font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--fg-dim); padding: 8px 10px 4px;
}

.cp-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--fg);
  font-family: var(--font);
  font-size: 12px;
  text-align: left;
  cursor: pointer;
}
.cp-item.active { background: var(--accent-dim); color: var(--accent); }
.cp-item-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cp-item-sub { font-size: 10px; color: var(--fg-dim); flex-shrink: 0; }
.cp-item.active .cp-item-sub { color: var(--accent); opacity: 0.8; }

.cp-empty { padding: 20px; text-align: center; color: var(--fg-dim); font-size: 12px; }

.cp-footer {
  display: flex; gap: 14px; padding: 8px 14px;
  border-top: 1px solid var(--border);
  font-size: 10px; color: var(--fg-dim);
}
</style>
