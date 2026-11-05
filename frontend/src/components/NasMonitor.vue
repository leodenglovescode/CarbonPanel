<template>
  <section id="nas-monitor" class="nas-monitor" aria-label="NAS storage overview">
    <header class="overview-header">
      <div>
        <h2>Storage overview</h2>
        <p class="subtitle">RAID arrays, volume groups &amp; cooling</p>
      </div>
      <div class="refresh-controls">
        <span class="updated-at" aria-live="polite">{{ updatedLabel }}</span>
        <button class="refresh-button" :disabled="busy" @click="refresh">
          <svg :class="{ spinning: busy }" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <path d="M20 7v5h-5M4 17v-5h5" /><path d="M6.1 7a7 7 0 0 1 11.5-1L20 9M4 15l2.4 3A7 7 0 0 0 17.9 17" />
          </svg>
          {{ busy ? 'Refreshing…' : 'Refresh' }}
        </button>
      </div>
    </header>

    <p v-if="error" role="alert" class="notice error-notice">{{ error }}</p>
    <div v-if="!data" class="initial-state" role="status">
      {{ busy ? 'Reading storage information…' : 'Storage information is not available yet.' }}
    </div>

    <template v-else>
      <div class="storage-grid">
        <section class="storage-panel" aria-label="RAID arrays">
          <header class="panel-header">
            <span class="section-mark" aria-hidden="true">MD</span>
            <div class="panel-heading"><h3>RAID arrays</h3><span>Linux software RAID</span></div>
            <span class="count-badge">{{ data.raid.arrays.length }}</span>
          </header>
          <div class="panel-body">
            <div v-if="!data.raid.arrays.length" class="empty-state">
              <strong>No arrays detected</strong>
              <p>Linux MD arrays will appear here. Hardware RAID controllers are not included.</p>
            </div>
            <article v-for="array in data.raid.arrays" :key="array.device" class="array-card">
              <div class="item-heading">
                <div class="item-identity">
                  <strong class="device-name" :title="array.device">{{ array.device }}</strong>
                  <span class="level-badge">{{ raidLevel(array.level) }}</span>
                </div>
                <span class="status-badge" :class="`tone-${arrayHealth(array).tone}`">
                  <span class="status-dot" />{{ arrayHealth(array).label }}
                </span>
              </div>
              <dl class="array-stats">
                <div><dt>Usable capacity</dt><dd>{{ bytes(array.size_bytes) }}</dd></div>
                <div><dt>Member devices</dt><dd>{{ array.members.length }}<span v-if="array.raid_disks != null"> · {{ array.raid_disks }} slots</span></dd></div>
                <div><dt>Degraded devices</dt><dd :class="{ 'danger-text': (array.degraded ?? 0) > 0 }">{{ array.degraded ?? 'Unknown' }}</dd></div>
              </dl>

              <div v-if="syncActive(array)" class="sync-progress">
                <div class="progress-caption"><span>{{ humanize(array.sync_action) }}</span><strong>{{ array.sync_percent == null ? 'In progress' : `${array.sync_percent.toFixed(1)}%` }}</strong></div>
                <div v-if="array.sync_percent != null" class="progress-track" role="progressbar" :aria-label="`${array.device} synchronization`" :aria-valuenow="clampPercent(array.sync_percent)" aria-valuemin="0" aria-valuemax="100">
                  <span class="progress-fill sync-fill" :style="{ width: `${clampPercent(array.sync_percent)}%` }" />
                </div>
              </div>
              <div class="members-heading"><span>Array members</span><span class="quiet">{{ syncCaption(array) }}</span></div>
              <div v-if="!array.members.length" class="small-empty">No member details reported.</div>
              <div v-for="member in array.members" :key="member.device" class="member-row">
                <svg class="drive-icon" width="17" height="19" viewBox="0 0 20 22" fill="none" stroke="currentColor" stroke-width="1.2" aria-hidden="true"><rect x="3" y="2" width="14" height="18" rx="2" /><circle cx="10" cy="9" r="3" /><path d="m10 9 3 4M6 17h3m3 0h2" /></svg>
                <div class="member-identity"><span :title="member.device">{{ member.device }}</span><small>{{ slotLabel(member.slot) }}</small></div>
                <span class="member-state" :class="`tone-${memberTone(member.state)}`">{{ humanize(member.state) }}</span>
              </div>
              <details class="technical-details">
                <summary>Array details</summary>
                <dl class="detail-list"><div><dt>Kernel state</dt><dd>{{ array.state || 'Not reported' }}</dd></div><div><dt>Sync action</dt><dd>{{ array.sync_action || 'Not reported' }}</dd></div></dl>
              </details>
            </article>
            <details v-if="data.raid.errors.length" class="diagnostics"><summary>Monitoring warnings ({{ data.raid.errors.length }})</summary><p v-for="message in data.raid.errors" :key="message">{{ message }}</p></details>
          </div>
        </section>

        <section class="storage-panel" aria-label="LVM volume groups">
          <header class="panel-header">
            <span class="section-mark lvm-mark" aria-hidden="true">VG</span>
            <div class="panel-heading"><h3>Volume groups</h3><span>LVM storage allocation</span></div>
            <span class="count-badge">{{ data.lvm.volume_groups.length }}</span>
          </header>
          <div class="panel-body">
            <div v-if="!data.lvm.volume_groups.length" class="empty-state"><strong>No volume groups detected</strong><p>Available LVM devices and logical volumes are listed below.</p></div>
            <article v-for="vg in data.lvm.volume_groups" :key="vg.vg_name" class="volume-group">
              <div class="item-heading">
                <strong class="device-name" :title="vg.vg_name">{{ vg.vg_name }}</strong>
                <span class="neutral-badge">{{ vg.lv_count || '?' }} {{ vg.lv_count === '1' ? 'volume' : 'volumes' }}</span>
              </div>
              <div class="allocation-caption"><div><span class="metric-label">Allocated</span><strong>{{ bytes(allocatedBytes(vg)) }}<small> / {{ bytes(vg.vg_size) }}</small></strong></div><div class="allocation-free"><span class="metric-label">Unallocated</span><span>{{ bytes(vg.vg_free) }}</span></div></div>
              <div v-if="allocationPercent(vg) != null" class="progress-track allocation-track" role="progressbar" :aria-label="`${vg.vg_name} capacity allocated to logical volumes`" :aria-valuenow="allocationPercent(vg) ?? undefined" aria-valuemin="0" aria-valuemax="100"><span class="progress-fill" :style="{ width: `${allocationPercent(vg)}%` }" /></div>
              <p class="allocation-hint">Volume allocation · filesystem usage is shown in the disk list</p>

              <div class="volumes-heading">Logical volumes</div>
              <div v-if="!groupVolumes(vg.vg_name).length" class="small-empty">No logical volumes reported for this group.</div>
              <div v-for="lv in groupVolumes(vg.vg_name)" :key="lv.lv_name" class="logical-volume">
                <div class="logical-volume-main"><span class="volume-symbol" aria-hidden="true">LV</span><div class="volume-identity"><strong>{{ lv.lv_name }}</strong><span :title="lv.lv_path">{{ lv.lv_path || `${lv.vg_name}/${lv.lv_name}` }}</span></div><strong class="volume-size">{{ bytes(lv.lv_size) }}</strong></div>
                <p v-if="lv.pool_lv || hasValue(lv.data_percent) || hasValue(lv.metadata_percent)" class="volume-allocation"><span v-if="lv.pool_lv">Pool {{ lv.pool_lv }}</span><span v-if="hasValue(lv.data_percent)">Data {{ lv.data_percent }}%</span><span v-if="hasValue(lv.metadata_percent)">Metadata {{ lv.metadata_percent }}%</span></p>
              </div>
              <details class="technical-details">
                <summary>Devices &amp; technical details</summary>
                <dl class="detail-list"><div><dt>Group attributes</dt><dd>{{ vg.vg_attr || 'Not reported' }}</dd></div><div><dt>Physical volume count</dt><dd>{{ vg.pv_count || 'Not reported' }}</dd></div></dl>
                <div v-for="pv in groupDevices(vg.vg_name)" :key="pv.pv_name" class="device-detail"><strong>{{ pv.pv_name }}</strong><span>{{ bytes(pv.pv_size) }} total · {{ bytes(pv.pv_free) }} unallocated</span><code>{{ pv.pv_attr }}</code></div>
                <div v-for="lv in groupVolumes(vg.vg_name)" :key="lv.lv_name" class="device-detail"><strong>{{ lv.lv_name }}</strong><span v-if="lv.devices">Backing devices: {{ lv.devices }}</span><code>{{ lv.lv_attr }}</code></div>
              </details>
            </article>
            <div v-for="pv in ungroupedDevices" :key="pv.pv_name" class="ungrouped-item"><strong>{{ pv.pv_name }}</strong><span>{{ pv.vg_name || 'No volume group' }} · {{ bytes(pv.pv_size) }} total · {{ bytes(pv.pv_free) }} unallocated</span><code>{{ pv.pv_attr }}</code></div>
            <div v-for="lv in ungroupedVolumes" :key="`${lv.vg_name}/${lv.lv_name}`" class="ungrouped-item"><strong>{{ lv.vg_name }}/{{ lv.lv_name }}</strong><span>{{ lv.lv_path }} · {{ bytes(lv.lv_size) }}</span><span v-if="lv.pool_lv">Pool {{ lv.pool_lv }}</span><span v-if="hasValue(lv.data_percent)">Data {{ lv.data_percent }}%</span><span v-if="hasValue(lv.metadata_percent)">Metadata {{ lv.metadata_percent }}%</span><span v-if="lv.devices">Backing devices: {{ lv.devices }}</span><code>{{ lv.lv_attr }}</code></div>
            <details v-if="data.lvm.errors.length" class="diagnostics"><summary>Monitoring warnings ({{ data.lvm.errors.length }})</summary><p v-for="message in data.lvm.errors" :key="message">{{ message }}</p></details>
          </div>
        </section>
      </div>

      <section class="cooling-panel" aria-label="Fan and PWM readings">
        <div class="cooling-heading"><span class="section-mark fan-mark" aria-hidden="true">FAN</span><div><h3>Cooling</h3><p v-if="!data.fans.chips.length">No fan or PWM readings are exposed by this system.</p><p v-else>{{ channelCount }} sensor {{ channelCount === 1 ? 'channel' : 'channels' }} reported</p></div><span v-if="!data.fans.chips.length" class="neutral-badge cooling-empty">Not reported</span></div>
        <div v-if="data.fans.chips.length" class="sensor-grid">
          <article v-for="chip in data.fans.chips" :key="chip.id" class="sensor-chip"><div class="sensor-chip-heading"><strong>{{ chip.name }}</strong><small>{{ chip.id }}</small></div><div v-for="channel in chip.channels" :key="channel.name" class="sensor-row"><span>{{ channel.label }}<small v-if="channel.enable != null">Mode {{ channel.enable }}</small></span><strong :class="{ 'danger-text': channel.fault === 1 }">{{ channel.value ?? '—' }} <small>{{ channel.kind === 'fan' ? 'RPM' : '/ 255 PWM' }}</small><small v-if="channel.fault === 1" class="sensor-fault">Sensor fault</small></strong></div></article>
        </div>
        <details v-if="data.fans.errors.length" class="diagnostics"><summary>Monitoring warnings ({{ data.fans.errors.length }})</summary><p v-for="message in data.fans.errors" :key="message">{{ message }}</p></details>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import api from '@/api'

interface RaidArray {
  device: string; level: string | null; state: string | null; size_bytes: number | null
  raid_disks: number | null; degraded: number | null; sync_action: string | null; sync_percent: number | null
  members: Array<{ device: string; state: string | null; slot: string | null }>
}
type LvmRow = Record<string, string>
interface NasInventory {
  raid: { arrays: RaidArray[]; errors: string[] }
  lvm: { physical_volumes: LvmRow[]; volume_groups: LvmRow[]; logical_volumes: LvmRow[]; errors: string[] }
  fans: { chips: Array<{ id: string; name: string; channels: Array<{
    name: string; label: string; kind: string; value: number | null; enable: number | null; fault: number | null
  }> }>; errors: string[] }
}
const data = ref<NasInventory | null>(null)
const busy = ref(false)
const error = ref('')
const updatedAt = ref<Date | null>(null)
const updatedLabel = computed(() => updatedAt.value
  ? `Updated ${updatedAt.value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · every 30s`
  : 'Auto refresh · 30s')
const channelCount = computed(() => data.value?.fans.chips.reduce((n, chip) => n + chip.channels.length, 0) ?? 0)
const ungroupedDevices = computed(() => data.value?.lvm.physical_volumes.filter(pv => !hasGroup(pv.vg_name)) ?? [])
const ungroupedVolumes = computed(() => data.value?.lvm.logical_volumes.filter(lv => !hasGroup(lv.vg_name)) ?? [])
let timer: ReturnType<typeof setInterval> | undefined
let controller: AbortController | undefined
async function refresh() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  controller = new AbortController()
  try {
    data.value = (await api.get<NasInventory>('/disks/nas', { signal: controller.signal })).data
    updatedAt.value = new Date()
  } catch (e: any) {
    if (!controller.signal.aborted) error.value = e.response?.data?.detail || 'NAS monitoring could not be refreshed. Displayed readings may be stale.'
  } finally { busy.value = false }
}
function hasValue(value: string | undefined) { return value != null && value.trim() !== '' }
function numeric(value: string | number | null | undefined): number | null {
  if (value == null || String(value).trim() === '') return null
  const number = Number(value)
  return Number.isFinite(number) && number >= 0 ? number : null
}
function bytes(value: string | number | null) {
  const number = numeric(value)
  if (number == null) return 'Not reported'
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']
  const index = number > 0 ? Math.max(0, Math.min(Math.floor(Math.log(number) / Math.log(1024)), units.length - 1)) : 0
  return `${(number / 1024 ** index).toLocaleString(undefined, { maximumFractionDigits: index > 0 ? 2 : 0 })} ${units[index]}`
}
function allocatedBytes(vg: LvmRow): number | null {
  const total = numeric(vg.vg_size), free = numeric(vg.vg_free)
  return total == null || free == null || free > total ? null : total - free
}
function allocationPercent(vg: LvmRow): number | null {
  const allocated = allocatedBytes(vg), total = numeric(vg.vg_size)
  return allocated == null || !total ? null : clampPercent(allocated / total * 100)
}
function clampPercent(value: number) { return Math.max(0, Math.min(100, value)) }
function hasGroup(name: string) { return data.value?.lvm.volume_groups.some(vg => vg.vg_name === name) ?? false }
function groupVolumes(name: string) { return data.value?.lvm.logical_volumes.filter(lv => lv.vg_name === name) ?? [] }
function groupDevices(name: string) { return data.value?.lvm.physical_volumes.filter(pv => pv.vg_name === name) ?? [] }
function humanize(value: string | null) { return value ? value.replaceAll('_', ' ').replaceAll(',', ' · ') : 'Not reported' }
function raidLevel(level: string | null) { return level ? level.toUpperCase().replace(/^RAID(\d)/, 'RAID $1') : 'Unknown level' }
function slotLabel(slot: string | null) { return slot != null && /^\d+$/.test(slot) ? `Slot ${slot}` : 'Slot not assigned' }
function memberTone(state: string | null) {
  const flags = state?.split(',').map(flag => flag.trim()) ?? []
  if (flags.includes('faulty') || flags.includes('blocked')) return 'danger'
  return flags.includes('in_sync') ? 'healthy' : 'muted'
}
function syncActive(array: RaidArray) { return ['recover', 'resync', 'reshape', 'check', 'repair'].includes(array.sync_action ?? '') }
function syncCaption(array: RaidArray) {
  if (syncActive(array)) return 'Sync in progress'
  if (array.sync_action === 'idle') return 'No sync in progress'
  return array.sync_action === 'frozen' ? 'Synchronization paused' : 'Sync state not reported'
}
function arrayHealth(array: RaidArray) {
  if ((array.degraded ?? 0) > 0) return { label: 'Degraded', tone: 'danger' }
  if (array.members.some(member => memberTone(member.state) === 'danger')) return { label: 'Needs attention', tone: 'danger' }
  if (array.state === 'broken') return { label: 'Broken', tone: 'danger' }
  if (['inactive', 'suspended', 'clear'].includes(array.state ?? '')) return { label: humanize(array.state), tone: 'warning' }
  if (syncActive(array)) return { label: ['recover', 'resync', 'reshape'].includes(array.sync_action!) ? 'Rebuilding' : humanize(array.sync_action), tone: 'warning' }
  if (array.sync_action === 'frozen') return { label: 'Sync paused', tone: 'warning' }
  if (array.state === 'readonly') return { label: 'Read only', tone: 'warning' }
  if (array.degraded === 0 && ['clean', 'active', 'active-idle', 'read-auto'].includes(array.state ?? '')) return { label: 'Healthy', tone: 'healthy' }
  return { label: array.state ? humanize(array.state) : 'Status unknown', tone: 'muted' }
}
onMounted(() => { refresh(); timer = setInterval(refresh, 30_000) })
onUnmounted(() => { clearInterval(timer); controller?.abort() })
</script>

<style scoped>
.nas-monitor { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.overview-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 2px 0; }
h2 { color: var(--fg); font-size: 14px; font-weight: 600; } h3 { color: var(--fg); font-size: 12px; font-weight: 600; }
.subtitle { color: var(--fg-dim); font-size: 10px; margin-top: 4px; }
.refresh-controls { display: flex; align-items: center; gap: 12px; }
.updated-at { font-size: 9px; color: var(--fg-dim); }
.refresh-button { display: inline-flex; align-items: center; gap: 7px; background: var(--bg-card); color: var(--fg-muted); border: 1px solid var(--border); border-radius: var(--radius-sm); font-family: var(--font); font-size: 10px; cursor: pointer; padding: 7px 10px; transition: color var(--transition), border-color var(--transition); }
.refresh-button:hover:not(:disabled) { color: var(--accent); border-color: var(--accent-border); } .refresh-button:disabled { opacity: .5; cursor: wait; }
.refresh-button:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.storage-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; align-items: start; }
.storage-panel, .cooling-panel { min-width: 0; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow-card); }
.panel-header { display: flex; align-items: center; gap: 10px; padding: 14px 16px; border-bottom: 1px solid var(--border); }
.section-mark { display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; width: 30px; height: 30px; color: var(--accent); background: var(--accent-dim); border: 1px solid var(--accent-border); border-radius: var(--radius-sm); font-size: 10px; font-weight: 600; }
.lvm-mark { color: var(--info); background: color-mix(in srgb, var(--info) 9%, transparent); border-color: color-mix(in srgb, var(--info) 20%, transparent); }
.fan-mark { color: var(--fg-muted); background: var(--bg-badge); border-color: var(--border); font-size: 8px; }
.panel-heading { flex: 1; min-width: 0; } .panel-heading > span { display: block; margin-top: 3px; color: var(--fg-dim); font-size: 9px; }
.count-badge { min-width: 22px; padding: 2px 6px; text-align: center; color: var(--fg-muted); background: var(--bg-badge); border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 10px; }
.panel-body { padding: 0 16px; }
.array-card, .volume-group { padding: 16px 0 0; } .array-card + .array-card, .volume-group + .volume-group { border-top: 1px solid var(--border); }
.item-heading, .item-identity { display: flex; align-items: center; gap: 9px; min-width: 0; } .item-heading { justify-content: space-between; flex-wrap: wrap; }
.device-name { color: var(--fg); font-size: 12px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.level-badge, .neutral-badge { color: var(--fg-muted); background: var(--bg-badge); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 2px 6px; font-size: 9px; white-space: nowrap; }
.status-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 9px; padding: 3px 7px; border-radius: var(--radius-sm); background: var(--bg-badge); text-transform: capitalize; }
.status-dot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.tone-healthy { color: var(--accent); } .status-badge.tone-healthy { background: var(--accent-dim); }
.tone-danger, .danger-text { color: var(--danger); } .status-badge.tone-danger { background: var(--danger-dim); }
.tone-warning { color: var(--warning); } .status-badge.tone-warning { background: var(--warning-dim); } .tone-muted { color: var(--fg-dim); }
.array-stats { display: grid; grid-template-columns: 1.25fr 1fr 1fr; gap: 12px; padding: 19px 0; }
.array-stats dt, .metric-label { display: block; color: var(--fg-dim); font-size: 9px; line-height: 1.5; margin-bottom: 5px; }
.array-stats dd { color: var(--fg); font-size: 17px; font-weight: 500; } .array-stats dd.danger-text { color: var(--danger); } .array-stats dd > span { font-size: 12px; color: var(--fg-dim); }
.members-heading, .volumes-heading { color: var(--fg-muted); font-size: 9px; padding: 10px 0; border-top: 1px solid var(--border); }
.members-heading { display: flex; justify-content: space-between; gap: 8px; } .quiet { color: var(--fg-dim); font-size: 8px; text-align: right; }
.member-row { display: flex; align-items: center; gap: 10px; padding: 9px 0; } .member-row + .member-row { border-top: 1px solid var(--border-subtle); }
.drive-icon { color: var(--fg-dim); flex-shrink: 0; } .member-identity { flex: 1; min-width: 0; }
.member-identity > span { display: block; color: var(--fg); font-size: 11px; overflow: hidden; text-overflow: ellipsis; }
.member-identity small { color: var(--fg-dim); font-size: 9px; display: block; margin-top: 3px; }
.member-state { font-size: 9px; text-align: right; text-transform: capitalize; max-width: 50%; overflow-wrap: anywhere; }
.technical-details { margin-top: 8px; border-top: 1px solid var(--border); color: var(--fg-muted); font-size: 10px; }
summary { cursor: pointer; padding: 11px 0; color: var(--fg-dim); font-size: 9px; transition: color var(--transition); } summary:hover { color: var(--fg); }
.detail-list > div { display: flex; justify-content: space-between; gap: 12px; padding: 5px 0; } .detail-list dt { color: var(--fg-dim); } .detail-list dd { text-align: right; overflow-wrap: anywhere; min-width: 0; }
.detail-list { padding-bottom: 8px; } .device-detail { display: flex; flex-direction: column; gap: 4px; padding: 9px 0; border-top: 1px solid var(--border-subtle); overflow-wrap: anywhere; }
.device-detail strong { color: var(--fg); font-size: 10px; } .device-detail span, .device-detail code { color: var(--fg-dim); font-size: 9px; }
.allocation-caption { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; padding: 19px 0 10px; }
.allocation-caption strong { color: var(--fg); font-size: 17px; font-weight: 500; } .allocation-caption strong small { color: var(--fg-dim); font-size: 10px; font-weight: 400; }
.allocation-free { text-align: right; color: var(--fg-muted); font-size: 11px; flex-shrink: 0; }
.progress-track { height: 5px; background: var(--bg-subtle); border-radius: var(--radius-sm); overflow: hidden; } .progress-fill { display: block; height: 100%; background: var(--info); border-radius: inherit; transition: width var(--bar-transition); }
.allocation-hint { color: var(--fg-dim); font-size: 8px; line-height: 1.5; padding: 7px 0 14px; }
.sync-progress { padding-bottom: 16px; } .progress-caption { display: flex; justify-content: space-between; gap: 8px; color: var(--warning); font-size: 10px; margin-bottom: 7px; text-transform: capitalize; } .sync-fill { background: var(--warning); }
.logical-volume { padding: 10px 0; } .logical-volume + .logical-volume { border-top: 1px solid var(--border-subtle); }
.logical-volume-main { display: flex; align-items: center; gap: 10px; } .volume-symbol { color: var(--info); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 4px; font-size: 8px; }
.volume-identity { display: flex; flex: 1; flex-direction: column; gap: 4px; min-width: 0; } .volume-identity strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--fg); font-size: 11px; font-weight: 500; } .volume-identity > span { color: var(--fg-dim); font-size: 9px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.volume-size { color: var(--fg-muted); font-size: 11px; font-weight: 400; white-space: nowrap; } .volume-allocation { display: flex; flex-wrap: wrap; gap: 10px; font-size: 9px; color: var(--fg-dim); padding: 8px 0 0 34px; }
.ungrouped-item { display: flex; flex-direction: column; gap: 5px; font-size: 10px; padding: 12px 0; border-top: 1px solid var(--border); color: var(--fg-muted); overflow-wrap: anywhere; }
.ungrouped-item span, .ungrouped-item code { color: var(--fg-dim); font-size: 9px; }
.cooling-panel { padding: 14px 16px; } .cooling-heading { display: flex; align-items: center; gap: 10px; } .cooling-heading > div { flex: 1; min-width: 0; } .cooling-heading p { color: var(--fg-dim); font-size: 10px; line-height: 1.5; margin-top: 4px; }
.sensor-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)); gap: 12px; margin-top: 14px; }
.sensor-chip { background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 12px; min-width: 0; } .sensor-chip-heading { display: flex; justify-content: space-between; gap: 10px; font-size: 10px; color: var(--fg-muted); margin-bottom: 7px; } .sensor-chip-heading strong { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .sensor-chip-heading small { color: var(--fg-dim); font-size: 9px; }
.sensor-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 8px 0; color: var(--fg-muted); font-size: 10px; } .sensor-row + .sensor-row { border-top: 1px solid var(--border); } .sensor-row strong { color: var(--fg); font-size: 14px; font-weight: 500; text-align: right; } .sensor-row strong.danger-text { color: var(--danger); } .sensor-row small { font-size: 9px; color: var(--fg-dim); font-weight: 400; } .sensor-row > span { min-width: 0; overflow-wrap: anywhere; } .sensor-row > span small { display: block; margin-top: 4px; } .sensor-row .sensor-fault { display: block; color: var(--danger); margin-top: 4px; }
.empty-state { padding: 22px 0; } .empty-state strong { color: var(--fg-muted); font-size: 11px; font-weight: 500; } .empty-state p { color: var(--fg-dim); font-size: 10px; line-height: 1.7; margin-top: 6px; max-width: 45ch; } .small-empty { font-size: 10px; color: var(--fg-dim); padding: 12px 0; }
.diagnostics { color: var(--warning); border-top: 1px solid var(--border); } .diagnostics summary { color: var(--warning); } .diagnostics p { color: var(--fg-muted); font-size: 10px; line-height: 1.6; padding: 0 0 8px; overflow-wrap: anywhere; }
.notice { padding: 10px 12px; border-radius: var(--radius-sm); font-size: 11px; line-height: 1.6; } .error-notice { color: var(--danger); border: 1px solid color-mix(in srgb, var(--danger) 25%, var(--border)); background: var(--danger-dim); }
.initial-state { border: 1px dashed var(--border); border-radius: var(--radius); padding: 24px; color: var(--fg-dim); font-size: 11px; text-align: center; }
.spinning { animation: nas-spin 1s linear infinite; } @keyframes nas-spin { to { transform: rotate(360deg); } }
@media (max-width: 850px) { .storage-grid { grid-template-columns: 1fr; } .updated-at { display: none; } }
@media (max-width: 480px) { .overview-header { align-items: flex-start; } .subtitle { font-size: 9px; max-width: 25ch; line-height: 1.5; } .panel-header { padding: 12px; } .panel-body { padding: 0 12px; } .array-stats { gap: 8px; } .array-stats dd { font-size: 14px; } .array-stats dt { font-size: 8px; } .allocation-caption strong { font-size: 15px; } .allocation-caption strong small { display: block; margin-top: 4px; } .cooling-panel { padding: 12px; } .cooling-empty { display: none; } .allocation-hint { max-width: 38ch; } }
@media (prefers-reduced-motion: reduce) { .spinning { animation: none; } .progress-fill { transition: none; } }
</style>
