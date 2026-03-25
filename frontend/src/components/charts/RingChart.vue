<template>
  <div ref="wrapEl" class="ring-wrap" :style="{ width: size + 'px', height: size + 'px' }">
    <Doughnut :data="chartData" :options="chartOptions" :plugins="[centerLabelPlugin]" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip } from 'chart.js'

ChartJS.register(ArcElement, Tooltip)

const props = withDefaults(defineProps<{
  value: number
  size?: number
  color?: string
  label?: string
}>(), {
  size: 72,
  color: '#00ff88',
  label: '',
})

const wrapEl = ref<HTMLElement | null>(null)

function getCssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

const chartData = computed(() => ({
  datasets: [{
    data: [props.value, 100 - props.value],
    backgroundColor: [props.color, getCssVar('--bg-subtle') || 'rgba(128,128,128,0.12)'],
    borderWidth: 0,
    hoverBackgroundColor: [props.color, getCssVar('--bg-subtle') || 'rgba(128,128,128,0.12)'],
  }],
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: false as const,
  cutout: '72%',
  plugins: {
    legend: { display: false },
    tooltip: { enabled: false },
  },
}))

const centerLabelPlugin = {
  id: 'centerLabel',
  beforeDraw(chart: ChartJS) {
    const { ctx, chartArea } = chart
    if (!chartArea) return
    const cx = (chartArea.left + chartArea.right) / 2
    const cy = (chartArea.top + chartArea.bottom) / 2
    const fgColor = getCssVar('--fg') || '#e0e0e0'
    ctx.save()
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = fgColor
    ctx.font = `600 ${Math.round(props.size * 0.22)}px JetBrains Mono, monospace`
    ctx.fillText(`${Math.round(props.value)}%`, cx, cy)
    ctx.restore()
  },
}
</script>

<style scoped>
.ring-wrap { position: relative; flex-shrink: 0; }
</style>
