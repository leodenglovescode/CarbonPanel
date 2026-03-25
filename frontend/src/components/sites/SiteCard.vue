<template>
  <div class="site-card" @click="$router.push(`/sites/${site.id}`)">
    <div class="card-header">
      <div class="card-title-row">
        <span class="site-name">{{ site.name }}</span>
        <span :class="['type-badge', `type-${site.type}`]">{{ site.type }}</span>
      </div>
      <div class="status-row">
        <span :class="['status-dot', statusClass(site.status?.status)]" />
        <span class="status-text">{{ site.status?.status ?? 'unknown' }}</span>
        <span v-if="site.status?.uptime" class="uptime">· {{ site.status.uptime }}</span>
        <span v-if="site.status?.pid" class="pid">pid {{ site.status.pid }}</span>
      </div>
    </div>

    <div class="service-info">
      <span class="service-label">{{ site.service_manager }}</span>
      <span class="service-name">{{ site.service_name }}</span>
    </div>

    <div v-if="site.description" class="description">{{ site.description }}</div>

    <div class="actions" @click.stop>
      <button
        v-for="act in actions"
        :key="act"
        :class="['action-btn', `action-${act}`]"
        :disabled="actionLoading === act"
        @click="runAction(act)"
      >{{ actionLoading === act ? '…' : act }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useSitesStore } from '@/stores/sites'
import type { SiteResponse } from '@/types/sites'

const props = defineProps<{ site: SiteResponse }>()
const store = useSitesStore()
const actionLoading = ref<string | null>(null)
const actions = ['start', 'stop', 'restart'] as const

async function runAction(act: string) {
  actionLoading.value = act
  await store.runAction(props.site.id, act)
  actionLoading.value = null
}

function statusClass(s?: string) {
  if (s === 'active') return 'dot-green'
  if (s === 'failed') return 'dot-red'
  if (s === 'inactive') return 'dot-gray'
  return 'dot-yellow'
}
</script>

<style scoped>
.site-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px;
  cursor: pointer;
  transition: border-color var(--transition), background var(--transition);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.site-card:hover { border-color: var(--accent-border); background: var(--bg-card-hover); }

.card-header { display: flex; flex-direction: column; gap: 5px; }
.card-title-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.site-name { font-size: 13px; font-weight: 600; color: var(--fg); }

.type-badge {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 2px 7px;
  border-radius: 3px;
  flex-shrink: 0;
}
.type-nginx     { background: rgba(96,165,250,0.15); color: #60a5fa; border: 1px solid rgba(96,165,250,0.3); }
.type-python    { background: rgba(250,204,21,0.12); color: #facc15; border: 1px solid rgba(250,204,21,0.3); }
.type-wordpress { background: rgba(45,212,191,0.12); color: #2dd4bf; border: 1px solid rgba(45,212,191,0.3); }
.type-nodejs    { background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent-border); }

.status-row { display: flex; align-items: center; gap: 5px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.dot-green  { background: var(--accent); box-shadow: 0 0 4px var(--accent); }
.dot-red    { background: var(--danger); }
.dot-gray   { background: var(--fg-dim); }
.dot-yellow { background: var(--warning); }
.status-text { font-size: 11px; color: var(--fg-muted); }
.uptime, .pid { font-size: 10px; color: var(--fg-dim); }

.service-info { display: flex; align-items: center; gap: 6px; }
.service-label {
  font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em;
  padding: 1px 5px; border-radius: 2px;
  background: var(--bg-badge); color: var(--fg-dim); border: 1px solid var(--border);
}
.service-name { font-size: 11px; color: var(--fg-muted); }

.description { font-size: 10px; color: var(--fg-dim); line-height: 1.4; }

.actions { display: flex; gap: 5px; }
.action-btn {
  flex: 1;
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-dim);
  font-family: var(--font);
  font-size: 10px;
  padding: 4px 0;
  border-radius: 3px;
  cursor: pointer;
  transition: all var(--transition);
  text-transform: capitalize;
}
.action-btn:hover:not(:disabled) { color: var(--fg); border-color: var(--fg-dim); }
.action-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.action-start:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.action-stop:hover:not(:disabled) { border-color: var(--danger); color: var(--danger); }
.action-restart:hover:not(:disabled) { border-color: var(--warning); color: var(--warning); }
</style>
