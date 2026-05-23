<template>
  <div :style="{ position: 'relative', height: height + 'px' }">
    <Bar :data="chartData" :options="chartOptions" :plugins="chartPlugins" />
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
  height: { type: Number, default: 220 },
  // [{label: 'Стадия 1: ...', startIndex: 0, endIndex: 7}, ...]
  groups: { type: Array, default: () => [] },
})

// Кастомный плагин для рисования разделителей и подписей стадий
const stageSeparatorsPlugin = {
  id: 'stageSeparators',
  afterDraw(chart) {
    if (!props.groups?.length) return
    const { ctx, chartArea, scales } = chart
    if (!scales.x) return
    const grps = props.groups

    grps.forEach((group, gi) => {
      const startPx = scales.x.getPixelForValue(group.startIndex)
      const endPx = scales.x.getPixelForValue(group.endIndex)
      const midPx = (startPx + endPx) / 2

      // Вертикальный разделитель перед группой (кроме первой)
      if (gi > 0) {
        const prevEndPx = scales.x.getPixelForValue(grps[gi - 1].endIndex)
        const sepX = (prevEndPx + startPx) / 2
        ctx.save()
        ctx.strokeStyle = '#bbb'
        ctx.lineWidth = 1.5
        ctx.setLineDash([5, 3])
        ctx.beginPath()
        ctx.moveTo(sepX, chartArea.top)
        ctx.lineTo(sepX, chart.height - 18)
        ctx.stroke()
        ctx.setLineDash([])
        ctx.restore()
      }

      // Подпись стадии у нижнего края canvas
      ctx.save()
      ctx.fillStyle = '#555'
      ctx.font = 'bold 9px Arial, sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(group.label, midPx, chart.height - 4)
      ctx.restore()
    })
  },
}

const chartPlugins = [stageSeparatorsPlugin]

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.datasets.map(ds => ({
    label: ds.label,
    data: ds.data,
    backgroundColor: ds.color || '#ffd93c',
    borderRadius: 4,
    barThickness: props.horizontal ? 16 : undefined,
  })),
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: props.horizontal ? 'y' : 'x',
  layout: {
    // Дополнительный отступ снизу для подписей групп
    padding: { bottom: props.groups?.length ? 22 : 0 },
  },
  plugins: {
    legend: { display: props.datasets.length > 1, position: 'bottom', labels: { font: { size: 11 } } },
  },
  scales: {
    x: {
      stacked: props.stacked,
      grid: { display: false },
      ticks: {
        font: { size: props.rotateLabels ? 8 : 10 },
        maxRotation: props.rotateLabels || 0,
        minRotation: props.rotateLabels || 0,
      },
    },
    y: { stacked: props.stacked, grid: { color: '#f0f0f0' }, ticks: { font: { size: 10 } } },
  },
}))
</script>
