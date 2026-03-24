<template>
  <q-page padding>
    <!-- Заголовок + экспорт -->
    <div class="row items-center justify-between q-mb-sm">
      <div class="text-subtitle1 text-weight-bold" style="color: #333">Отчёты и Статистика</div>
      <q-btn flat dense icon="picture_as_pdf" color="grey-7" @click="exportPDF">
        <q-tooltip>Экспорт PDF</q-tooltip>
      </q-btn>
    </div>

    <!-- Фильтры -->
    <q-card class="is-card q-mb-md">
      <q-card-section class="q-pa-sm">
        <div class="row q-col-gutter-sm">
          <div class="col-4">
            <q-select v-model="filters.year" :options="years" label="Год" outlined dense @update:model-value="loadData" />
          </div>
          <div class="col-4">
            <q-select v-model="filters.quarter" :options="quarters" label="Квартал" outlined dense emit-value map-options @update:model-value="loadData" />
          </div>
          <div class="col-4">
            <q-select v-model="filters.month" :options="monthOpts" label="Месяц" outlined dense emit-value map-options @update:model-value="loadData" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-pull-to-refresh @refresh="onRefresh">
      <!-- KPI карточки (8 шт) -->
      <div class="row q-col-gutter-xs q-mb-md">
        <div class="col-6 col-md-3" v-for="kpi in kpiCards" :key="kpi.label">
          <q-card class="is-card" :style="{ borderLeft: `3px solid ${kpi.color}` }">
            <q-card-section class="q-pa-sm">
              <div class="text-h6 text-weight-bold">{{ kpi.value }}</div>
              <div class="text-caption text-grey-7" style="font-size: 10px">{{ kpi.label }}</div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Секция: Клиенты -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Клиенты</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-4 text-center" v-for="m in clientMini" :key="m.label">
              <div class="text-h6 text-weight-bold">{{ m.value }}</div>
              <div class="text-caption text-grey-7">{{ m.label }}</div>
            </div>
          </div>
          <!-- График: динамика клиентов -->
          <line-chart v-if="clientsDynamics" :labels="clientsDynamics.labels" :datasets="clientsDynamics.datasets" />
        </q-card-section>
      </q-card>

      <!-- Секция: Договоры -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Договоры</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-4 text-center" v-for="m in contractMini" :key="m.label">
              <div class="text-h6 text-weight-bold">{{ m.value }}</div>
              <div class="text-caption text-grey-7">{{ m.label }}</div>
            </div>
          </div>
          <!-- Pie: тип проекта -->
          <div class="row q-col-gutter-md" v-if="projectTypePie">
            <div class="col-12 col-md-6">
              <div class="text-caption text-weight-bold text-center q-mb-xs">Тип проекта</div>
              <pie-chart :labels="projectTypePie.labels" :values="projectTypePie.values" />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Секция: Воронка CRM -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Воронка CRM</div>
          <bar-chart v-if="funnelChart" :labels="funnelChart.labels" :datasets="funnelChart.datasets" horizontal />
        </q-card-section>
      </q-card>

      <!-- Секция: CRM аналитика -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Проекты</div>
          <q-tabs v-model="projectTab" dense active-color="dark" indicator-color="accent" no-caps align="left">
            <q-tab name="individual" label="Индивидуальные" />
            <q-tab name="template" label="Шаблонные" />
          </q-tabs>
          <div v-if="projectStats" class="q-mt-md">
            <div class="row q-col-gutter-sm">
              <div class="col-6" v-for="s in projectStatCards" :key="s.label">
                <div class="text-center q-pa-sm" :style="{ border: `1px solid ${s.color || '#E0E0E0'}`, borderRadius: '8px' }">
                  <div class="text-h6 text-weight-bold">{{ s.value }}</div>
                  <div class="text-caption text-grey-7">{{ s.label }}</div>
                </div>
              </div>
            </div>
            <!-- По городам -->
            <div class="q-mt-md" v-if="cityChart">
              <div class="text-caption text-weight-bold q-mb-xs" style="color: #333">По городам</div>
              <bar-chart :labels="cityChart.labels" :datasets="cityChart.datasets" horizontal />
            </div>
            <!-- По агентам -->
            <div class="q-mt-md" v-if="agentChart">
              <div class="text-caption text-weight-bold q-mb-xs" style="color: #333">По агентам</div>
              <bar-chart :labels="agentChart.labels" :datasets="agentChart.datasets" horizontal />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Секция: Динамика договоров по месяцам -->
      <q-card class="is-card q-mb-md" v-if="contractsDynamics">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">Договоры по месяцам</div>
          <bar-chart :labels="contractsDynamics.labels" :datasets="contractsDynamics.datasets" />
        </q-card-section>
      </q-card>

      <!-- Секция: Надзор -->
      <q-card class="is-card q-mb-md" v-if="supervisionStats">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Авторский надзор</div>
          <div class="row q-col-gutter-sm">
            <div class="col-6 text-center" v-for="s in supervisionMini" :key="s.label">
              <div class="text-h6 text-weight-bold">{{ s.value }}</div>
              <div class="text-caption text-grey-7">{{ s.label }}</div>
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-pull-to-refresh>
  </q-page>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { reportsApi, statisticsApi } from 'src/services/api'
import PieChart from 'src/components/charts/PieChart.vue'
import BarChart from 'src/components/charts/BarChart.vue'
import LineChart from 'src/components/charts/LineChart.vue'

const currentYear = new Date().getFullYear()
const filters = ref({ year: currentYear, quarter: null, month: null })
const summary = ref(null)
const funnel = ref(null)
const projectStats = ref(null)
const supervisionStats = ref(null)
const clientsDynamicsRaw = ref(null)
const projectTab = ref('individual')

const years = Array.from({ length: 7 }, (_, i) => currentYear - i)
const quarters = [{ label: 'Все', value: null }, { label: 'Q1', value: 1 }, { label: 'Q2', value: 2 }, { label: 'Q3', value: 3 }, { label: 'Q4', value: 4 }]
const monthOpts = [{ label: 'Все', value: null }, ...Array.from({ length: 12 }, (_, i) => ({ label: new Date(2000, i).toLocaleDateString('ru-RU', { month: 'long' }), value: i + 1 }))]

function fmtMoney(v) {
  if (!v) return '0 ₽'
  if (v >= 1000000) return `${(v / 1000000).toFixed(1)}M ₽`
  if (v >= 1000) return `${(v / 1000).toFixed(0)}K ₽`
  return `${Math.round(v)} ₽`
}

const kpiCards = computed(() => {
  const s = summary.value || {}
  return [
    { label: 'Всего клиентов', value: s.total_clients ?? '—', color: '#ffd93c' },
    { label: 'Новых клиентов', value: s.new_clients ?? '—', color: '#27AE60' },
    { label: 'Повторных', value: s.returning_clients ?? '—', color: '#85C1E9' },
    { label: 'Договоров', value: s.total_contracts ?? '—', color: '#F39C12' },
    { label: 'Стоимость', value: fmtMoney(s.total_amount), color: '#E74C3C' },
    { label: 'Средний чек', value: fmtMoney(s.avg_amount), color: '#9B59B6' },
    { label: 'Площадь (м²)', value: s.total_area ? Math.round(s.total_area) : '—', color: '#1ABC9C' },
    { label: 'Ср. площадь', value: s.avg_area ? Math.round(s.avg_area) : '—', color: '#E67E22' }
  ]
})

const clientMini = computed(() => {
  const s = summary.value || {}
  return [
    { label: 'Физлица', value: s.total_clients ? Math.round((s.total_clients - (s.returning_clients || 0))) : '—' },
    { label: 'Новые', value: s.new_clients ?? '—' },
    { label: 'Повторные', value: s.returning_clients ?? '—' }
  ]
})

const contractMini = computed(() => {
  const s = summary.value || {}
  return [
    { label: 'Договоров', value: s.total_contracts ?? '—' },
    { label: 'Площадь', value: s.total_area ? `${Math.round(s.total_area)} м²` : '—' },
    { label: 'Ср. площадь', value: s.avg_area ? `${Math.round(s.avg_area)} м²` : '—' }
  ]
})

const clientsDynamics = computed(() => {
  const raw = clientsDynamicsRaw.value
  if (!raw || typeof raw !== 'object') return null
  const keys = Object.keys(raw).sort()
  if (keys.length === 0) return null
  return {
    labels: keys.map(k => { const [, m] = k.split('-'); return new Date(2000, parseInt(m) - 1).toLocaleDateString('ru-RU', { month: 'short' }) }),
    datasets: [
      { label: 'Новые', data: keys.map(k => raw[k]?.new || 0), color: '#27AE60' },
      { label: 'Повторные', data: keys.map(k => raw[k]?.returning || 0), color: '#85C1E9' }
    ]
  }
})

const projectTypePie = computed(() => {
  const s = summary.value
  if (!s || !s.total_contracts) return null
  const ind = s.total_contracts - (s.returning_clients || 0)
  const tmpl = s.returning_clients || 0
  return { labels: ['Индивидуальные', 'Шаблонные'], values: [ind, tmpl] }
})

const funnelChart = computed(() => {
  if (!funnel.value?.funnel) return null
  const f = funnel.value.funnel
  const labels = Object.keys(f)
  return {
    labels,
    datasets: [{ label: 'Проектов', data: labels.map(k => f[k]), color: '#ffd93c' }]
  }
})

const projectStatCards = computed(() => {
  const p = projectStats.value || {}
  return [
    { label: 'Всего', value: p.total_orders ?? '—', color: '#ffd93c' },
    { label: 'Активных', value: p.active ?? '—', color: '#27AE60' },
    { label: 'Завершённых', value: p.completed ?? '—', color: '#85C1E9' },
    { label: 'Просроченных', value: p.overdue ?? '—', color: '#E74C3C' }
  ]
})

const cityChart = computed(() => {
  const p = projectStats.value
  if (!p?.by_cities) return null
  const entries = Object.entries(p.by_cities).sort((a, b) => b[1] - a[1]).slice(0, 8)
  return {
    labels: entries.map(([k]) => k),
    datasets: [{ label: 'Проектов', data: entries.map(([, v]) => v), color: '#85C1E9' }]
  }
})

const agentChart = computed(() => {
  const p = projectStats.value
  if (!p?.by_agents) return null
  const entries = Object.entries(p.by_agents).sort((a, b) => b[1] - a[1]).slice(0, 8)
  return {
    labels: entries.map(([k]) => k),
    datasets: [{ label: 'Проектов', data: entries.map(([, v]) => v), color: '#ffd93c' }]
  }
})

const contractsDynamics = computed(() => {
  const s = summary.value
  if (!s) return null
  // Используем данные из summary — если есть monthly_data
  return null // Пока нет monthly_data в summary, будет добавлено при наличии API
})

const supervisionMini = computed(() => {
  const s = supervisionStats.value || {}
  return [
    { label: 'Всего', value: s.total_orders ?? '—' },
    { label: 'Активных', value: s.active ?? '—' },
    { label: 'Завершённых', value: s.completed ?? '—' },
    { label: 'Просроченных', value: s.overdue ?? '—' }
  ]
})

async function loadData() {
  const params = { year: filters.value.year }
  if (filters.value.quarter) params.quarter = filters.value.quarter
  if (filters.value.month) params.month = filters.value.month

  const pt = projectTab.value === 'template' ? 'Шаблонный' : 'Индивидуальный'

  const [sumR, funnelR, projR, dynR, supR] = await Promise.allSettled([
    reportsApi.getSummary(params),
    reportsApi.getFunnel(params),
    reportsApi.getCrmAnalytics({ ...params, project_type: pt }),
    reportsApi.getClientsDynamics({ year: filters.value.year }),
    statisticsApi.getProjects({ ...params, project_type: 'Авторский надзор' })
  ])

  if (sumR.status === 'fulfilled') summary.value = sumR.value.data
  if (funnelR.status === 'fulfilled') funnel.value = funnelR.value.data
  if (projR.status === 'fulfilled') projectStats.value = projR.value.data
  if (dynR.status === 'fulfilled') clientsDynamicsRaw.value = dynR.value.data
  if (supR.status === 'fulfilled') supervisionStats.value = supR.value.data
}

function exportPDF() {
  // На мобильных — используем системный print (сохранение как PDF)
  window.print()
}

watch(projectTab, () => loadData())
function onRefresh(done) { loadData().finally(done) }
onMounted(() => loadData())
</script>
