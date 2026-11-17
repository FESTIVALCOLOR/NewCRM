<template>
  <div :style="{ position: 'relative', height: height + 'px' }">
    <Bar :data="chartData" :options="chartOptions" :plugins="chartPlugins" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useQuasar } from 'quasar'
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

const $q = useQuasar()

// Canvas не поддерживает CSS var() — резолвим в реальные цвета через тему
const textColor = computed(() => $q.dark.isActive ? '#C0C0C0' : '#555555')
const mutedColor = computed(() => $q.dark.isActive ? '#787878' : '#999999')
const gridColor = computed(() => $q.dark.isActive ? '#2E2E2E' : '#F0F0F0')

// Плагин: горизонтальная линия-скобка под каждой группой стадий + подпись
const stageSeparatorsPlugin = {
  id: 'stageSeparators',
  afterDraw(chart) {
    if (!props.groups?.length) return
    const { ctx, scales } = chart
    if (!scales.x) return
    const grps = props.groups

    // Шаг между центрами баров — для вычисления границ группы
    const step =
      grps.length > 0 && chart.data.labels.length > 1
        ? Math.abs(scales.x.getPixelForValue(1) - scales.x.getPixelForValue(0))
        : 20
    const halfStep = step / 2

    // Линии рисуются в нижнем padding: chart.height - padding..chart.height
    const lineY = chart.height - 26 // горизонтальная линия
    const capH = 5 // высота вертикальных концевых засечек
    const textY = chart.height - 8 // подпись

    grps.forEach(group => {
      const startPx = scales.x.getPixelForValue(group.startIndex) - halfStep * 0.85
      const endPx = scales.x.getPixelForValue(group.endIndex) + halfStep * 0.85
      const midPx = (startPx + endPx) / 2

      // Горизонтальная линия с вертикальными засечками на концах
      ctx.save()
      ctx.strokeStyle = mutedColor.value  // реальный цвет, не CSS var
      ctx.lineWidth = 1.5
      ctx.beginPath()
      // левая засечка
      ctx.moveTo(startPx, lineY - capH)
      ctx.lineTo(startPx, lineY)
      // основная линия
      ctx.lineTo(endPx, lineY)
      // правая засечка
      ctx.lineTo(endPx, lineY - capH)
      ctx.stroke()
      ctx.restore()

      // Подпись стадии по центру
      ctx.save()
      ctx.fillStyle = textColor.value  // реальный цвет, не CSS var
      ctx.font = 'bold 9px Arial, sans-serif'
      ctx.textAlign = 'center'
      // Обрезаем до 28 символов
      const label = group.label.length > 28 ? group.label.substring(0, 27) + '…' : group.label
      ctx.fillText(label, midPx, textY)
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
    backgroundColor: Array.isArray(ds.color) ? ds.color : (ds.color || '#ffd93c'),
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
    padding: { bottom: props.groups?.length ? 36 : 0 },
  },
  plugins: {
    legend: {
      display: props.datasets.length > 1,
      position: 'bottom',
      labels: { font: { size: 11 }, color: textColor.value },
    },
  },
  scales: {
    x: {
      stacked: props.stacked,
      grid: { display: false },
      ticks: {
        color: textColor.value,
        font: { size: props.rotateLabels ? 8 : 10 },
        maxRotation: props.rotateLabels || 0,
        minRotation: props.rotateLabels || 0,
      },
    },
    y: {
      stacked: props.stacked,
      grid: { color: gridColor.value },
      ticks: { color: textColor.value, font: { size: 10 } },
    },
  },
}))
</script>
