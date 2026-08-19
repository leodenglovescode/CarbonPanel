<template>
  <div class="sparkline-wrap" :style="height ? { height: height + 'px' } : {}">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useThemeStore } from '@/stores/theme'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Filler,
  Tooltip,
} from 'chart.js'

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip)

const theme = useThemeStore()

function resolveColor(value: string): string {
  // Reading the resolved settings makes this recompute on a live theme change.
  void theme.resolvedStyleSettings
  const match = value.match(/^var\((--[^)]+)\)$/)
  if (!match) return value
  return getComputedStyle(document.documentElement).getPropertyValue(match[1]).trim() || value
}

function withAlpha(value: string, alpha: number): string {
  const hex = value.match(/^#([\da-f]{6})$/i)?.[1]
  if (!hex) return value
  const channels = [0, 2, 4].map(offset => Number.parseInt(hex.slice(offset, offset + 2), 16))
  return 'rgba(' + channels[0] + ', ' + channels[1] + ', ' + channels[2] + ', ' + alpha + ')'
}

const props = withDefaults(defineProps<{
  data: number[]
  color?: string
  height?: number  // omit to fill parent container
  maxY?: number
}>(), {
  color: 'var(--accent)',
  height: undefined,
  maxY: 100,
})

const chartData = computed(() => {
  const color = resolveColor(props.color)
  return {
    labels: props.data.map(() => ''),
    datasets: [{
      data: props.data,
      borderColor: color,
      borderWidth: 1.5,
      backgroundColor: withAlpha(color, 0.1),
      tension: 0.4,
      fill: true,
      pointRadius: 0,
      pointHoverRadius: 0,
    }],
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: false as const,
  scales: {
    x: { display: false },
    y: { display: false, min: 0, max: props.maxY },
  },
  plugins: { legend: { display: false }, tooltip: { enabled: false } },
}))
</script>

<style scoped>
.sparkline-wrap {
  width: 100%;
  height: 100%; /* fills parent when no inline height is set */
  min-height: 20px;
  position: relative;
}
</style>
