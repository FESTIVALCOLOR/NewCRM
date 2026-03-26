<template>
  <div :style="{ position: 'relative', height: height + 'px' }">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Legend } from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const props = defineProps({
  labels: { type: Array, required: true },
  datasets: { type: Array, required: true },
  horizontal: { type: Boolean, default: false },
  stacked: { type: Boolean, default: false },
  rotateLabels: { type: Number, default: 0 },
  height: { type: Number, default: 220 }
})

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.datasets.map(ds => ({
    label: ds.label,
    data: ds.data,
    backgroundColor: ds.color || '#ffd93c',
    borderRadius: 4,
    barThickness: props.horizontal ? 16 : undefined
  }))
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: props.horizontal ? 'y' : 'x',
  plugins: {
    legend: { display: props.datasets.length > 1, position: 'bottom', labels: { font: { size: 11 } } }
  },
  scales: {
    x: {
      stacked: props.stacked,
      grid: { display: false },
      ticks: {
        font: { size: props.rotateLabels ? 8 : 10 },
        maxRotation: props.rotateLabels || 0,
        minRotation: props.rotateLabels || 0
      }
    },
    y: { stacked: props.stacked, grid: { color: '#f0f0f0' }, ticks: { font: { size: 10 } } }
  }
}))
</script>
