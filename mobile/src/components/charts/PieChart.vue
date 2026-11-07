<template>
  <div style="position: relative; height: 220px">
    <Pie :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useQuasar } from 'quasar'
import { Pie } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend)

const props = defineProps({
  labels: { type: Array, required: true },
  values: { type: Array, required: true },
  colors: { type: Array, default: () => ['#ffd93c', '#F39C12', '#27AE60', '#E74C3C', '#85C1E9', '#9B59B6', '#1ABC9C', '#E67E22'] },
  title: { type: String, default: '' },
})

const $q = useQuasar()
const textColor = computed(() => $q.dark.isActive ? '#C0C0C0' : '#555555')

const chartData = computed(() => ({
  labels: props.labels,
  datasets: [{
    data: props.values,
    backgroundColor: props.colors.slice(0, props.values.length),
    borderWidth: 1,
    borderColor: $q.dark.isActive ? '#1E1E1E' : '#fff',
  }],
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 12, color: textColor.value } },
    title: { display: false },
  },
}))
</script>
