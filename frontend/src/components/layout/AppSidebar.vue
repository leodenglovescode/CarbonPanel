<template>
  <aside class="sidebar">
    <div class="sidebar-top">
      <div class="logo">
        <span class="bracket">[</span>carbon<span class="accent">panel</span><span class="bracket">]</span>
      </div>
    </div>

    <nav class="nav">
      <router-link
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ active: isActive(item.to) }"
      >
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </nav>

    <div class="sidebar-bottom">
      <div v-if="system" class="hostname">{{ system.hostname }}</div>
      <div class="status-row">
        <span class="ws-dot" :class="connected ? 'ws-on' : 'ws-off'" :title="connected ? 'Live' : 'Reconnecting...'" />
        <span class="ws-label">{{ connected ? 'live' : 'reconnecting' }}</span>
      </div>
      <button class="logout-btn" @click="handleLogout">logout</button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { SystemMetrics } from '@/types/metrics'

defineProps<{ system?: SystemMetrics; connected?: boolean }>()

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const navItems = [
  { to: '/', label: 'Stats' },
  { to: '/sites', label: 'Sites' },
  { to: '/system-services', label: 'System Services' },
  { to: '/settings', label: 'Settings' },
]

function isActive(to: string) {
  if (to === '/') return route.path === '/'
  return route.path.startsWith(to)
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.sidebar {
  width: 178px;
  flex-shrink: 0;
  background: var(--bg-card);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.sidebar-top {
  padding: 16px 14px 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.logo { font-size: 13px; font-weight: 700; letter-spacing: -0.02em; }
.bracket { color: var(--fg-dim); }
.accent { color: var(--accent); }

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
</style>
