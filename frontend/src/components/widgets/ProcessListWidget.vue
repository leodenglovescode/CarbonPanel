<template>
  <BaseCard>
    <template #header>
      <span class="card-title">Processes</span>
      <div class="header-right">
        <span class="badge badge-gray">top 2</span>
        <button
          v-for="s in ['cpu', 'memory']"
          :key="s"
          :class="['sort-btn', { active: currentSort === s }]"
          @click="setSort(s as 'cpu' | 'memory')"
        >{{ s }}</button>
      </div>
    </template>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>PID</th>
            <th>Name</th>
            <th>User</th>
            <th class="num" @click="setSort('cpu')">
              CPU% <span v-if="currentSort === 'cpu'" class="sort-arrow">▼</span>
            </th>
            <th class="num" @click="setSort('memory')">
              RAM (MB) <span v-if="currentSort === 'memory'" class="sort-arrow">▼</span>
            </th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in visibleProcesses" :key="p.pid">
            <td class="pid">{{ p.pid }}</td>
            <td class="name">{{ p.name }}</td>
            <td class="user text-muted">{{ p.user }}</td>
            <td class="num" :class="cpuColor(p.cpu_percent)">{{ p.cpu_percent.toFixed(1) }}</td>
            <td class="num text-muted">{{ p.memory_mb.toFixed(0) }}</td>
            <td>
              <span :class="['status-dot', statusClass(p.status)]" />
              <span class="status-txt">{{ p.status }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import type { ProcessMetrics } from '@/types/metrics'
import { useMetricsStore } from '@/stores/metrics'

const props = defineProps<{ processes: ProcessMetrics[] }>()
const emit = defineEmits<{ sortChange: [sort: 'cpu' | 'memory'] }>()

const visibleProcesses = computed(() => props.processes.slice(0, 2))

const store = useMetricsStore()
const currentSort = store.processSort

function setSort(s: 'cpu' | 'memory') {
  store.processSort = s
  emit('sortChange', s)
}

function cpuColor(pct: number) {
  if (pct > 50) return 'text-danger'
  if (pct > 20) return 'text-warning'
  return ''
}
function statusClass(status: string) {
  if (status === 'running') return 'dot-green'
  if (status === 'sleeping') return 'dot-gray'
  return 'dot-yellow'
}
</script>

<style scoped>
.card-title { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-muted); }
.header-right { display: flex; align-items: center; gap: 6px; }

.sort-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--fg-dim);
  font-family: var(--font);
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 3px;
  cursor: pointer;
  transition: all var(--transition);
}
.sort-btn.active { border-color: var(--accent-border); color: var(--accent); background: var(--accent-dim); }
.sort-btn:hover:not(.active) { color: var(--fg-muted); border-color: var(--fg-dim); }

.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
thead th {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fg-dim);
  padding: 4px 8px;
  text-align: left;
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}
thead th:hover { color: var(--fg-muted); }
.sort-arrow { color: var(--accent); }

tbody tr { transition: background var(--transition); }
tbody tr:nth-child(even) { background: rgba(255,255,255,0.015); }
tbody tr:hover { background: rgba(255,255,255,0.04); }
tbody td {
  font-size: 11px;
  padding: 4px 8px;
  color: var(--fg);
  border-bottom: 1px solid rgba(255,255,255,0.03);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}

.pid { color: var(--fg-dim); font-size: 10px; }
.name { font-weight: 500; }
.user { max-width: 80px; }
.num { text-align: right; font-variant-numeric: tabular-nums; }

.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 5px;
  vertical-align: middle;
}
.dot-green { background: var(--accent); }
.dot-gray { background: var(--fg-dim); }
.dot-yellow { background: var(--warning); }
.status-txt { font-size: 10px; color: var(--fg-muted); vertical-align: middle; }
</style>
