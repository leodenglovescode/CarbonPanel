<template>
  <div class="sparkline-wrap" :style="height ? { height: height + 'px' } : {}">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
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

const props = withDefaults(defineProps<{
  data: number[]
  color?: string
  height?: number  // omit to fill parent container
  maxY?: number
}>(), {
  color: '#00ff88',
  maxY: 100,
})

const chartData = computed(() => ({
  labels: props.data.map(() => ''),
  datasets: [{
    data: props.data,
    borderColor: props.color,
    borderWidth: 1.5,
    backgroundColor: props.color + '18',
    tension: 0.4,
    fill: true,
    pointRadius: 0,
    pointHoverRadius: 0,
  }],
}))

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
