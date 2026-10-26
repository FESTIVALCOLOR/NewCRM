<template>
  <div style="position: relative; height: 220px">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useQuasar } from 'quasar'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler } from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler)

const props = defineProps({
  labels: { type: Array, required: true },
  datasets: { type: Array, required: true },
})

const $q = useQuasar()
const textColor = computed(() => $q.dark.isActive ? '#C0C0C0' : '#555555')
const gridColor = computed(() => $q.dark.isActive ? '#2E2E2E' : '#F0F0F0')

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.datasets.map(ds => ({
    label: ds.label,
    data: ds.data,
    borderColor: ds.color || '#ffd93c',
    backgroundColor: (ds.color || '#ffd93c') + '20',
    fill: true,
    tension: 0.3,
    pointRadius: 3,
    pointBackgroundColor: ds.color || '#ffd93c',
  })),
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: true, position: 'bottom', labels: { font: { size: 11 }, color: textColor.value } },
  },
  scales: {
    x: { grid: { display: false }, ticks: { color: textColor.value, font: { size: 10 } } },
    y: { grid: { color: gridColor.value }, ticks: { color: textColor.value, font: { size: 10 } } },
  },
}))
</script>
