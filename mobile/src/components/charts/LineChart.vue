<template>
  <div style="position: relative; height: 220px">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler } from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler)

const props = defineProps({
  labels: { type: Array, required: true },
  datasets: { type: Array, required: true },
})

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.datasets.map(ds => ({
    label: ds.label,
    data: ds.data,
    borderColor: ds.color || 'var(--fc-accent)',
    backgroundColor: (ds.color || 'var(--fc-accent)') + '20',
    fill: true,
    tension: 0.3,
    pointRadius: 3,
    pointBackgroundColor: ds.color || 'var(--fc-accent)',
  })),
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: true, position: 'bottom', labels: { font: { size: 11 } } },
  },
  scales: {
    x: { grid: { display: false }, ticks: { font: { size: 10 } } },
    y: { grid: { color: 'var(--fc-tab-hover)' }, ticks: { font: { size: 10 } } },
  },
}
</script>
