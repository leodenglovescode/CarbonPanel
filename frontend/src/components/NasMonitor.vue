<template>
  <section id="nas-monitor" class="nas-monitor" aria-label="NAS monitoring">
    <div class="heading"><h2>RAID, LVM &amp; Fans</h2><button :disabled="busy" @click="refresh">{{ busy ? 'Refreshing…' : 'Refresh NAS' }}</button></div>
    <p class="hint">Read-only monitoring · refreshes every 30 seconds</p>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
    <template v-if="data">
      <h3>Linux software RAID</h3>
      <p v-if="!data.raid.arrays.length" class="hint">No Linux MD arrays detected. Hardware RAID and vendor storage controllers are not reported here.</p>
      <article v-for="array in data.raid.arrays" :key="array.device">
        <strong>{{ array.device }} · {{ array.level || 'Unknown level' }}</strong>
        <p :class="{ error: (array.degraded ?? 0) > 0 }">
          {{ array.state || 'Unknown state' }} · {{ bytes(array.size_bytes) }} · {{ array.raid_disks ?? '?' }} slots ·
          {{ array.degraded == null ? 'Degraded count unknown' : `${array.degraded} missing/degraded` }}
        </p>
        <p>Sync: {{ array.sync_action || 'Not reported' }}<span v-if="array.sync_percent != null"> · {{ array.sync_percent }}%</span></p>
        <ul><li v-for="member in array.members" :key="member.device">{{ member.device }} · {{ member.state || 'Unknown' }} · slot {{ member.slot ?? '?' }}</li></ul>
      </article>
      <p v-for="message in data.raid.errors" :key="message" class="error">{{ message }}</p>
      <h3>LVM</h3>
      <p v-if="!data.lvm.volume_groups.length && !data.lvm.errors.length" class="hint">No LVM volume groups detected.</p>
      <article v-for="vg in data.lvm.volume_groups" :key="vg.vg_name">
        <strong>{{ vg.vg_name }}</strong>
        <p>{{ bytes(vg.vg_size) }} total · {{ bytes(vg.vg_free) }} free · {{ vg.pv_count }} physical volumes · {{ vg.lv_count }} logical volumes · {{ vg.vg_attr }}</p>
      </article>
      <article v-for="pv in data.lvm.physical_volumes" :key="pv.pv_name">
        <strong>{{ pv.pv_name }}</strong>
        <p>{{ pv.vg_name || 'No volume group' }} · {{ bytes(pv.pv_size) }} total · {{ bytes(pv.pv_free) }} free · {{ pv.pv_attr }}</p>
      </article>
      <article v-for="lv in data.lvm.logical_volumes" :key="`${lv.vg_name}/${lv.lv_name}`">
        <strong>{{ lv.vg_name }}/{{ lv.lv_name }}</strong>
        <p>{{ lv.lv_path }} · {{ bytes(lv.lv_size) }} · {{ lv.lv_attr }}</p>
        <p v-if="lv.pool_lv">Pool: {{ lv.pool_lv }}</p>
        <p v-if="lv.data_percent">Data allocation: {{ lv.data_percent }}%</p>
        <p v-if="lv.metadata_percent">Metadata allocation: {{ lv.metadata_percent }}%</p>
        <p v-if="lv.devices">Devices: {{ lv.devices }}</p>
      </article>
      <p v-for="message in data.lvm.errors" :key="message" class="error">{{ message }}</p>
      <h3>Fans &amp; PWM</h3>
      <p v-if="!data.fans.chips.length" class="hint">No fan/PWM channels exposed by this kernel. The NAS may use a vendor driver or controller.</p>
      <article v-for="chip in data.fans.chips" :key="chip.id">
        <strong>{{ chip.name }} ({{ chip.id }})</strong>
        <p v-for="channel in chip.channels" :key="channel.name" :class="{ error: channel.fault === 1 }">
          {{ channel.label }}: {{ channel.value ?? 'Unavailable' }} {{ channel.kind === 'fan' ? 'RPM' : '/ 255 PWM' }}
          <span v-if="channel.enable != null"> · enable mode {{ channel.enable }}</span>
          <span v-if="channel.fault === 1"> · sensor fault</span>
        </p>
      </article>
      <p v-for="message in data.fans.errors" :key="message" class="error">{{ message }}</p>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import api from '@/api'

interface NasInventory {
  raid: { arrays: Array<{
    device: string; level: string | null; state: string | null; size_bytes: number | null
    raid_disks: number | null; degraded: number | null; sync_action: string | null; sync_percent: number | null
    members: Array<{ device: string; state: string | null; slot: string | null }>
  }>; errors: string[] }
  lvm: { physical_volumes: Record<string, string>[]; volume_groups: Record<string, string>[]; logical_volumes: Record<string, string>[]; errors: string[] }
  fans: { chips: Array<{ id: string; name: string; channels: Array<{
    name: string; label: string; kind: string; value: number | null; enable: number | null; fault: number | null
  }> }>; errors: string[] }
}
const data = ref<NasInventory | null>(null)
const busy = ref(false)
const error = ref('')
let timer: ReturnType<typeof setInterval> | undefined
let controller: AbortController | undefined
async function refresh() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  controller = new AbortController()
  try {
    data.value = (await api.get<NasInventory>('/disks/nas', { signal: controller.signal })).data
  } catch (e: any) {
    if (!controller.signal.aborted) error.value = e.response?.data?.detail || 'NAS monitoring could not be refreshed. Displayed readings may be stale.'
  } finally { busy.value = false }
}
function bytes(value: string | number | null) {
  if (value == null || value === '') return 'Unknown capacity'
  const number = Number(value)
  return Number.isFinite(number) ? `${(number / 1024 ** 3).toFixed(2)} GiB` : 'Unknown capacity'
}
onMounted(() => { refresh(); timer = setInterval(refresh, 30_000) })
onUnmounted(() => { clearInterval(timer); controller?.abort() })
</script>

<style scoped>
.nas-monitor { padding: 16px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg-card); overflow-wrap: anywhere; }
.heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
h2 { font-size: 14px; } h3 { font-size: 12px; margin: 16px 0 8px; }
article { border-top: 1px solid var(--border); padding: 10px 0; font-size: 12px; }
p, li { font-size: 11px; line-height: 1.6; color: var(--fg-muted); } ul { padding-left: 18px; }
.hint { color: var(--fg-dim); } .error { color: var(--danger); }
button { background: none; color: var(--fg-muted); border: 1px solid var(--border); border-radius: var(--radius-sm); font-family: var(--font); cursor: pointer; padding: 5px 10px; transition: color var(--transition), border-color var(--transition); }
button:hover { color: var(--accent); border-color: var(--accent); } button:disabled { opacity: .5; cursor: wait; }
</style>
