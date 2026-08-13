<template>
  <aside
    id="app-sidebar"
    ref="sidebarEl"
    class="sidebar"
    :class="{ 'mobile-open': mobileOpen }"
    :inert="drawerHidden ? true : undefined"
    :aria-hidden="drawerHidden ? 'true' : undefined"
    @keydown="onKeydown"
  >
    <div class="sidebar-top">
      <div class="logo">
        <span class="bracket">[</span>Carbon<span class="accent">Panel</span><span class="bracket">]</span>
      </div>
      <button ref="closeButtonEl" class="mobile-close-btn" aria-label="Close menu" @click="$emit('close')">✕</button>
    </div>

    <nav class="nav">
      <router-link
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ active: isActive(item.to) }"
        @click="$emit('close')"
      >
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </nav>

    <div class="sidebar-bottom">
      <div v-if="system" class="hostname">{{ system.hostname }}</div>
      <div class="status-row">
        <span class="ws-dot" :class="connected ? 'ws-on' : 'ws-off'" :title="connected ? 'Live' : 'Reconnecting...'" />
        <span class="ws-label">{{ connected ? t('common.live') : t('common.reconnecting') }}</span>
      </div>
      <button class="logout-btn" @click="handleLogout">{{ t('common.logout') }}</button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useLocaleStore } from '@/stores/locale'
import type { SystemMetrics } from '@/types/metrics'

const props = defineProps<{ system?: SystemMetrics; connected?: boolean; mobileOpen?: boolean }>()
const emit = defineEmits<{ close: [] }>()

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { t } = useLocaleStore()
const sidebarEl = ref<HTMLElement | null>(null)
const closeButtonEl = ref<HTMLButtonElement | null>(null)
const isMobile = ref(false)
const drawerHidden = computed(() => isMobile.value && !props.mobileOpen)
let mediaQuery: MediaQueryList | null = null
let previousFocus: HTMLElement | null = null

function updateMobile(event: MediaQueryList | MediaQueryListEvent) {
  const leavingMobile = isMobile.value && !event.matches
  isMobile.value = event.matches
  if (leavingMobile && props.mobileOpen) {
    previousFocus?.focus()
    previousFocus = null
    emit('close')
  }
}

function focusableElements(): HTMLElement[] {
  if (!sidebarEl.value) return []
  return Array.from(sidebarEl.value.querySelectorAll<HTMLElement>(
    'button:not(:disabled), a[href], [tabindex]:not([tabindex="-1"])',
  ))
}

function onKeydown(event: KeyboardEvent) {
  if (!isMobile.value || !props.mobileOpen) return
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
    return
  }
  if (event.key !== 'Tab') return
  const items = focusableElements()
  if (!items.length) return
  const first = items[0]
  const last = items[items.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(() => props.mobileOpen, async (open) => {
  if (!isMobile.value) return
  if (open) {
    previousFocus = document.activeElement as HTMLElement | null
    await nextTick()
    closeButtonEl.value?.focus()
  } else if (previousFocus) {
    await nextTick()
    previousFocus.focus()
    previousFocus = null
  }
})

onMounted(() => {
  mediaQuery = window.matchMedia('(max-width: 640px)')
  updateMobile(mediaQuery)
  mediaQuery.addEventListener('change', updateMobile)
})
onUnmounted(() => {
  mediaQuery?.removeEventListener('change', updateMobile)
  previousFocus?.focus()
})

const navItems = computed(() => [
  { to: '/', label: t('nav.stats') },
  { to: '/sites', label: t('nav.sites') },
  { to: '/system-services', label: t('nav.systemServices') },
  { to: '/disks', label: t('nav.disks') },
  { to: '/apps', label: t('nav.apps') },
  { to: '/docker', label: t('nav.docker') },
  { to: '/logs', label: t('nav.logs') },
  { to: '/cron', label: t('nav.cron') },
  { to: '/sessions', label: t('nav.sessions') },
  { to: '/settings', label: t('nav.settings') },
])

function isActive(to: string) {
  if (to === '/') return route.path === '/'
  return route.path.startsWith(to)
}

async function handleLogout() {
  try {
    await authApi.logout()
  } catch {
    // best-effort — clear local state and redirect either way
  }
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.sidebar {
  width: 178px;
  flex-shrink: 0;
  background: color-mix(in srgb, var(--bg-card) 72%, transparent);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.sidebar-top {
  height: 42px;
  padding: 0 14px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.logo { font-size: 13px; font-weight: 700; letter-spacing: -0.02em; }
.bracket { color: var(--fg-dim); }
.accent { color: var(--accent); }

.mobile-close-btn {
  display: none;
  background: none;
  border: none;
  color: var(--fg-dim);
  font-size: 14px;
  cursor: pointer;
  padding: 4px 6px;
  line-height: 1;
  transition: color var(--transition);
}
.mobile-close-btn:hover, .mobile-close-btn:focus-visible { color: var(--fg); }

.nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 8px 0;
  gap: 1px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 8px 14px;
  font-size: 12px;
  font-weight: 500;
  color: var(--fg-muted);
  text-decoration: none;
  border-left: 2px solid transparent;
  transition: background var(--transition), color var(--transition), border-color var(--transition);
}
.nav-item:hover { background: var(--bg-hover); color: var(--fg); }
.nav-item.active {
  background: var(--accent-dim);
  color: var(--accent);
  border-left-color: var(--accent);
}

.nav-label { letter-spacing: 0.02em; }

.sidebar-bottom {
  padding: 12px 14px;
  border-top: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  gap: 7px;
}

.hostname { font-size: 10px; color: var(--fg-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.status-row { display: flex; align-items: center; gap: 6px; }
.ws-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.ws-on  { background: var(--accent); box-shadow: 0 0 5px var(--accent); }
.ws-off { background: var(--fg-dim); animation: blink 1.2s ease infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.2} }
.ws-label { font-size: 10px; color: var(--fg-dim); }

.logout-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-muted);
  font-family: var(--font);
  font-size: 11px;
  padding: 5px 0;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
  text-align: center;
}
.logout-btn:hover { border-color: var(--danger); color: var(--danger); }

@media (max-width: 640px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100%;
    z-index: 200;
    transform: translateX(-100%);
    transition: transform var(--transition-slow);
    box-shadow: none;
  }
  .sidebar.mobile-open {
    transform: translateX(0);
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5);
  }
  .mobile-close-btn { display: block; }
  .nav-item { padding: 12px 14px; font-size: 13px; }
}
</style>
