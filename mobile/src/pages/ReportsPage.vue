<template>
  <q-page padding>
    <div class="row items-center justify-between q-mb-sm">
      <div class="text-subtitle1 text-weight-bold" style="color: #333">
        Отчёты и Статистика
      </div>
      <button type="button" class="rep-export-btn" :disabled="pdfLoading" @click="exportPDF">
        <q-spinner v-if="pdfLoading" size="14px" color="primary" />
        <span v-else>PDF</span>
      </button>
    </div>

    <!-- Фильтры -->
    <q-card class="is-card q-mb-md">
      <q-card-section class="q-pa-sm">
        <div class="row q-col-gutter-sm">
          <div class="col-4">
            <q-select
              v-model="filters.year"
              :options="years"
              label="Год"
              outlined
              dense
              @update:model-value="loadData"
            />
          </div>
          <div class="col-4">
            <q-select
              v-model="filters.quarter"
              :options="quarters"
              label="Квартал"
              outlined
              dense
              emit-value
              map-options
              @update:model-value="loadData"
            />
          </div>
          <div class="col-4">
            <q-select
              v-model="filters.month"
              :options="monthOpts"
              label="Месяц"
              outlined
              dense
              emit-value
              map-options
              @update:model-value="loadData"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-pull-to-refresh @refresh="onRefresh">
      <!-- ========== КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ ========== -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">
            Ключевые показатели
          </div>
        </q-card-section>
        <q-card-section>
          <div class="row q-col-gutter-xs q-mb-sm">
            <div v-for="kpi in kpiCards" :key="kpi.label" class="col-4 col-md-2">
              <div class="q-pa-xs" :style="{ borderLeft: `3px solid ${kpi.color}`, borderRadius: '6px', background: '#FAFAFA' }">
                <div class="text-subtitle1 text-weight-bold">
                  {{ kpi.value }}
                </div>
                <div class="text-caption text-grey-7" style="font-size: 9px">
                  {{ kpi.label }}
                </div>
              </div>
            </div>
          </div>
          <!-- По агентам -->
          <div v-if="agentKpi.length > 0" class="row q-col-gutter-xs">
            <div v-for="a in agentKpi" :key="a.label" class="col-6">
              <div class="q-pa-xs" :style="{ borderLeft: `3px solid ${a.color}`, borderRadius: '6px', background: '#FAFAFA' }">
                <div class="text-subtitle2 text-weight-bold">
                  {{ a.value }}
                </div>
                <div class="text-caption text-grey-7" style="font-size: 9px">
                  {{ a.label }}
                </div>
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- ========== КЛИЕНТЫ ========== -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">
            Клиенты
          </div>
          <div class="row q-col-gutter-xs q-mb-md">
            <div v-for="m in clientMini" :key="m.label" class="col-4 col-md-2 text-center">
              <div class="text-subtitle1 text-weight-bold" :style="{ color: m.color || '#333' }">
                {{ m.value }}
              </div>
              <div class="text-caption text-grey-7" style="font-size: 9px">
                {{ m.label }}
              </div>
            </div>
          </div>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6">
              <div class="text-caption text-weight-bold text-center q-mb-xs">
                Динамика клиентов
              </div>
              <line-chart v-if="clientsDynamics" :labels="clientsDynamics.labels" :datasets="clientsDynamics.datasets" />
            </div>
            <div v-if="clientTypePie" class="col-12 col-md-6">
              <div class="text-caption text-weight-bold text-center q-mb-xs">
                Тип клиентов
              </div>
              <pie-chart :labels="clientTypePie.labels" :values="clientTypePie.values" />
            </div>
          </div>
          <div class="row q-col-gutter-md q-mt-sm">
            <div v-if="clientsByAgentChart" class="col-12 col-md-6">
              <div class="text-caption text-weight-bold q-mb-xs">
                Клиенты по агентам
              </div>
              <bar-chart :labels="clientsByAgentChart.labels" :datasets="clientsByAgentChart.datasets" horizontal />
            </div>
            <div v-if="newVsReturningChart" class="col-12 col-md-6">
              <div class="text-caption text-weight-bold q-mb-xs">
                Новые vs Повторные
              </div>
              <bar-chart :labels="newVsReturningChart.labels" :datasets="newVsReturningChart.datasets" />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- ========== ДОГОВОРЫ ========== -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">
            Договоры
          </div>
          <div class="row q-col-gutter-xs q-mb-md">
            <div v-for="m in contractMini" :key="m.label" class="col-4 col-md-2 text-center">
              <div class="text-subtitle1 text-weight-bold" :style="{ color: m.color || '#333' }">
                {{ m.value }}
              </div>
              <div class="text-caption text-grey-7" style="font-size: 9px">
                {{ m.label }}
              </div>
            </div>
          </div>
          <div class="row q-col-gutter-md">
            <div v-if="contractsDynamics" class="col-12 col-md-6">
              <div class="text-caption text-weight-bold q-mb-xs">
                Договоры по месяцам
              </div>
              <bar-chart :labels="contractsDynamics.labels" :datasets="contractsDynamics.datasets" />
            </div>
            <div v-if="contractsAmountDynamics" class="col-12 col-md-6">
              <div class="text-caption text-weight-bold q-mb-xs">
                Стоимость по месяцам
              </div>
              <line-chart :labels="contractsAmountDynamics.labels" :datasets="contractsAmountDynamics.datasets" />
            </div>
          </div>
          <div class="row q-col-gutter-md q-mt-sm">
            <div v-if="projectTypePie" class="col-12 col-md-6">
              <div class="text-caption text-weight-bold text-center q-mb-xs">
                Типы проектов
              </div>
              <pie-chart :labels="projectTypePie.labels" :values="projectTypePie.values" />
            </div>
            <div v-if="topCitiesChart" class="col-12 col-md-6">
              <div class="text-caption text-weight-bold q-mb-xs">
                ТОП городов
              </div>
              <bar-chart :labels="topCitiesChart.labels" :datasets="topCitiesChart.datasets" horizontal />
            </div>
          </div>
          <div class="row q-col-gutter-md q-mt-sm">
            <div v-if="contractsByAgentChart" class="col-12 col-md-6">
              <div class="text-caption text-weight-bold q-mb-xs">
                Договоры по агентам
              </div>
              <bar-chart :labels="contractsByAgentChart.labels" :datasets="contractsByAgentChart.datasets" />
            </div>
            <div v-if="amountByAgentChart" class="col-12 col-md-6">
              <div class="text-caption text-weight-bold q-mb-xs">
                Стоимость по агентам
              </div>
              <bar-chart :labels="amountByAgentChart.labels" :datasets="amountByAgentChart.datasets" horizontal />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- ========== CRM АНАЛИТИКА ========== -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">
            CRM Аналитика
          </div>
          <q-tabs
            v-model="projectTab"
            dense
            active-color="dark"
            indicator-color="accent"
            no-caps
            align="left"
          >
            <q-tab name="individual" label="Индивидуальные" />
            <q-tab name="template" label="Шаблонные" />
          </q-tabs>
          <div v-if="projectStats" class="q-mt-md">
            <div class="row q-col-gutter-xs q-mb-md items-stretch">
              <div v-for="s in projectStatCards" :key="s.label" class="col-3" style="display: flex">
                <div class="text-center q-pa-xs" style="display: flex; flex-direction: column; justify-content: center; width: 100%" :style="{ border: `1px solid ${s.color || '#E0E0E0'}`, borderRadius: '6px' }">
                  <div class="text-subtitle1 text-weight-bold">
                    {{ s.value }}
                  </div>
                  <div class="text-caption text-grey-7" style="font-size: 9px">
                    {{ s.label }}
                  </div>
                </div>
              </div>
            </div>
            <!-- Воронка -->
            <div v-if="funnelChart" class="q-mb-md">
              <div class="text-caption text-weight-bold q-mb-xs">
                Воронка проектов
              </div>
              <bar-chart :labels="funnelChart.labels" :datasets="funnelChart.datasets" horizontal />
            </div>
            <div class="row q-col-gutter-md">
              <div v-if="cityChart" class="col-12 col-md-6">
                <div class="text-caption text-weight-bold q-mb-xs">
                  По городам
                </div>
                <bar-chart :labels="cityChart.labels" :datasets="cityChart.datasets" horizontal />
              </div>
              <div v-if="agentChart" class="col-12 col-md-6">
                <div class="text-caption text-weight-bold q-mb-xs">
                  По агентам
                </div>
                <bar-chart :labels="agentChart.labels" :datasets="agentChart.datasets" horizontal />
              </div>
            </div>
            <!-- Время стадий vs норматив -->
            <div v-if="stageDurationsChart" class="q-mt-md" style="overflow-x: auto">
              <div class="text-caption text-weight-bold q-mb-xs">
                Время стадий vs норматив — {{ projectTab === 'template' ? 'Шаблонный' : 'Индивидуальный' }}
              </div>
              <div style="min-width: 700px">
                <bar-chart
                  :labels="stageDurationsChart.labels"
                  :datasets="stageDurationsChart.datasets"
                  :groups="stageDurationsChart.groups"
                  :rotate-labels="90"
                  :height="370"
                />
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- ========== АВТОРСКИЙ НАДЗОР ========== -->
      <q-card v-if="supervisionStats" class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">
            Авторский надзор
          </div>
          <!-- Строка 1: общие показатели надзора -->
          <div class="row q-col-gutter-xs q-mb-xs">
            <div v-for="s in supervisionMini.slice(0, 4)" :key="s.label" class="col-3 text-center">
              <div class="text-subtitle1 text-weight-bold" :style="{ color: s.color || '#333' }">
                {{ s.value }}
              </div>
              <div class="text-caption text-grey-7" style="font-size: 9px">
                {{ s.label }}
              </div>
            </div>
          </div>
          <!-- Строка 2: статистика выездов -->
          <div class="row q-col-gutter-xs q-mb-md">
            <div v-for="s in supervisionMini.slice(4)" :key="s.label" class="col text-center">
              <div class="text-subtitle1 text-weight-bold" :style="{ color: s.color || '#333' }">
                {{ s.value }}
              </div>
              <div class="text-caption text-grey-7" style="font-size: 9px">
                {{ s.label }}
              </div>
            </div>
          </div>
          <div class="row q-col-gutter-md">
            <div v-if="supervisionByAgentChart" class="col-12 col-md-6">
              <div class="text-caption text-weight-bold q-mb-xs">
                Надзоры по агентам
              </div>
              <bar-chart :labels="supervisionByAgentChart.labels" :datasets="supervisionByAgentChart.datasets" horizontal />
            </div>
            <div v-if="supervisionByCityChart" class="col-12 col-md-6">
              <div class="text-caption text-weight-bold q-mb-xs">
                Выезды по городам
              </div>
              <bar-chart :labels="supervisionByCityChart.labels" :datasets="supervisionByCityChart.datasets" horizontal />
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-pull-to-refresh>
  </q-page>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { reportsApi, statisticsApi, dashboardApi } from 'src/services/api'
import PieChart from 'src/components/charts/PieChart.vue'
import BarChart from 'src/components/charts/BarChart.vue'
import LineChart from 'src/components/charts/LineChart.vue'

const currentYear = new Date().getFullYear()
const filters = ref({ year: currentYear, quarter: null, month: null })
const summary = ref(null)
const funnel = ref(null)
const projectStats = ref(null)
const contractsDashboard = ref(null)
const supervisionStats = ref(null)
const clientsDynamicsRaw = ref(null)
const contractsByPeriodRaw = ref(null)
const crmDetailed = ref(null)
const supervisionDetailed = ref(null)
const projectTab = ref('individual')
const pdfLoading = ref(false)

const years = Array.from({ length: 7 }, (_, i) => currentYear - i)
const quarters = [{ label: 'Все', value: null }, { label: 'Q1', value: 1 }, { label: 'Q2', value: 2 }, { label: 'Q3', value: 3 }, { label: 'Q4', value: 4 }]
const monthOpts = [{ label: 'Все', value: null }, ...Array.from({ length: 12 }, (_, i) => ({ label: new Date(2000, i).toLocaleDateString('ru-RU', { month: 'long' }), value: i + 1 }))]

function fmtMoney(v) {
  if (!v) return '0 ₽'
  if (v >= 1000000) return `${(v / 1000000).toFixed(1)}M ₽`
  if (v >= 1000) return `${Math.round(v / 1000)}K ₽`
  return `${new Intl.NumberFormat('ru-RU').format(Math.round(v))} ₽`
}

// ========== KPI ==========
const kpiCards = computed(() => {
  const s = summary.value || {}
  return [
    { label: 'Всего клиентов', value: s.total_clients ?? '—', color: '#ffd93c' },
    { label: 'Новых клиентов', value: s.new_clients ?? '—', color: '#27AE60' },
    { label: 'Повторных', value: s.returning_clients ?? '—', color: '#85C1E9' },
    { label: 'Всего договоров', value: s.total_contracts ?? '—', color: '#F39C12' },
    { label: 'Общая стоимость', value: fmtMoney(s.total_amount), color: '#E74C3C' },
    { label: 'Средний чек', value: fmtMoney(s.avg_amount), color: '#9B59B6' },
    { label: 'Общая площадь', value: s.total_area ? `${Math.round(s.total_area)} м²` : '—', color: '#1ABC9C' },
    { label: 'Средняя площадь', value: s.avg_area ? `${Math.round(s.avg_area)} м²` : '—', color: '#E67E22' },
  ]
})

const agentKpi = computed(() => {
  const ba = summary.value?.by_agent || []
  if (ba.length === 0) return []
  // Строки: Клиенты, Договоры, Площадь. Столбцы: агенты (слева направо)
  const rows = [
    { key: 'clients', label: 'Клиенты', fmt: v => v ?? 0 },
    { key: 'contracts', label: 'Договоры', fmt: (v, a) => `${v ?? 0} / ${fmtMoney(a.amount)}` },
    { key: 'area', label: 'Площадь', fmt: v => v ? `${Math.round(v)} м²` : '0' },
  ]
  const items = []
  for (const row of rows) {
    for (const a of ba) {
      items.push({
        label: `${row.label} — ${a.agent_name}`,
        value: row.fmt(a[row.key], a),
        color: a.agent_color || '#999',
      })
    }
  }
  return items
})

// ========== КЛИЕНТЫ ==========
const clientMini = computed(() => {
  const s = summary.value || {}
  const ba = s.by_agent || []
  const fromAgents = ba.reduce((sum, a) => sum + (a.clients || 0), 0)
  return [
    { label: 'Всего', value: s.total_clients ?? '—', color: '#F39C12' },
    { label: 'Физлица', value: s.total_clients ? (s.total_clients - (s.returning_clients || 0)) : '—' },
    { label: 'Юрлица', value: 0 },
    { label: 'Новых', value: s.new_clients ?? '—', color: '#27AE60' },
    { label: 'Повторных', value: s.returning_clients ?? '—', color: '#9B59B6' },
    { label: 'От агентов', value: fromAgents || '—', color: '#E74C3C' },
  ]
})

const clientsDynamics = computed(() => {
  const raw = clientsDynamicsRaw.value
  if (!raw || typeof raw !== 'object') return null
  const months = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек']
  if (Array.isArray(raw)) {
    if (raw.length === 0) return null
    return {
      labels: raw.map(item => { const m = String(item.month || item.period || '').split('-'); return m.length >= 2 ? months[parseInt(m[1]) - 1] || m[1] : m[0] }),
      datasets: [
        { label: 'Новые', data: raw.map(item => item.new_clients || item.new || 0), color: '#27AE60' },
        { label: 'Повторные', data: raw.map(item => item.returning_clients || item.returning || 0), color: '#9B59B6' },
      ],
    }
  }
  const keys = Object.keys(raw).sort()
  if (keys.length === 0) return null
  return {
    labels: keys.map(k => { const p = k.split('-'); return p.length >= 2 ? months[parseInt(p[1]) - 1] || k : k }),
    datasets: [
      { label: 'Новые', data: keys.map(k => raw[k]?.new || raw[k]?.new_clients || 0), color: '#27AE60' },
      { label: 'Повторные', data: keys.map(k => raw[k]?.returning || raw[k]?.returning_clients || 0), color: '#9B59B6' },
    ],
  }
})

const clientTypePie = computed(() => {
  const d = contractsDashboard.value
  if (!d) return null
  return { labels: ['Индивидуальные', 'Шаблонные'], values: [d.individual_orders || 0, d.template_orders || 0] }
})

const clientsByAgentChart = computed(() => {
  const ba = summary.value?.by_agent || []
  if (ba.length === 0) return null
  return {
    labels: ba.map(a => a.agent_name),
    datasets: [{ label: 'Клиентов', data: ba.map(a => a.clients || 0), color: '#F39C12' }],
  }
})

const newVsReturningChart = computed(() => {
  const raw = clientsDynamicsRaw.value
  if (!raw) return null
  const months = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек']
  if (Array.isArray(raw) && raw.length > 0) {
    return {
      labels: raw.map((_, i) => months[i] || `M${i + 1}`),
      datasets: [
        { label: 'Новые', data: raw.map(item => item.new_clients || item.new || 0), color: '#27AE60' },
        { label: 'Повторные', data: raw.map(item => item.returning_clients || item.returning || 0), color: '#9B59B6' },
      ],
    }
  }
  return null
})

// ========== ДОГОВОРЫ ==========
const contractMini = computed(() => {
  const s = summary.value || {}
  const cd = contractsDashboard.value || {}
  return [
    { label: 'Всего', value: s.total_contracts ?? '—', color: '#F39C12' },
    { label: 'Индивидуальных', value: cd.individual_orders ?? '—', color: '#F57C00' },
    { label: 'Шаблонных', value: cd.template_orders ?? '—', color: '#C62828' },
    { label: 'Стоимость всего', value: fmtMoney(s.total_amount), color: '#F57C00' },
    { label: 'Сумма инд.', value: fmtMoney(cd.individual_amount), color: '#F57C00' },
    { label: 'Сумма шабл.', value: fmtMoney(cd.template_amount), color: '#C62828' },
  ]
})

const projectTypePie = computed(() => {
  const d = contractsDashboard.value
  if (!d || (!d.individual_orders && !d.template_orders)) return null
  return { labels: ['Индивидуальные', 'Шаблонные'], values: [d.individual_orders || 0, d.template_orders || 0] }
})

const contractsDynamics = computed(() => {
  const d = contractsByPeriodRaw.value
  if (!d) return null
  const months = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек']
  return {
    labels: months,
    datasets: [
      { label: 'Индивид.', data: months.map((_, i) => d[String(i + 1)]?.count || 0), color: '#F39C12' },
      { label: 'Шаблон.', data: months.map((_, i) => d[String(i + 1)]?.template_count || 0), color: '#C62828' },
    ],
  }
})

const contractsAmountDynamics = computed(() => {
  const d = contractsByPeriodRaw.value
  if (!d) return null
  const months = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек']
  return {
    labels: months,
    datasets: [{ label: 'Стоимость', data: months.map((_, i) => d[String(i + 1)]?.amount || 0), color: '#F39C12' }],
  }
})

const topCitiesChart = computed(() => {
  const p = projectStats.value
  if (p?.by_cities) {
    const entries = Object.entries(p.by_cities).sort((a, b) => b[1] - a[1]).slice(0, 8)
    if (entries.length > 0) return {
      labels: entries.map(([k]) => k),
      datasets: [{ label: 'Договоров', data: entries.map(([, v]) => v), color: '#F39C12' }],
    }
  }
  return null
})

const contractsByAgentChart = computed(() => {
  const ba = summary.value?.by_agent || []
  if (ba.length === 0) return null
  return {
    labels: ba.map(a => a.agent_name),
    datasets: [{ label: 'Договоров', data: ba.map(a => a.contracts || 0), color: '#3498DB' }],
  }
})

const amountByAgentChart = computed(() => {
  const ba = summary.value?.by_agent || []
  if (ba.length === 0) return null
  return {
    labels: ba.map(a => a.agent_name),
    datasets: [{ label: 'Стоимость', data: ba.map(a => a.amount || 0), color: '#F39C12' }],
  }
})

// ========== CRM ==========
const funnelChart = computed(() => {
  if (!funnel.value?.funnel) return null
  const f = funnel.value.funnel
  const labels = Object.keys(f)
  return { labels, datasets: [{ label: 'Проектов', data: labels.map(k => f[k]), color: '#ffd93c' }] }
})

const projectStatCards = computed(() => {
  const p = projectStats.value || {}
  const d = crmDetailed.value || {}
  const ots = d.on_time_stats || {}
  // Серверные поля: projects_pct, stages_pct, avg_deviation_days
  const projectsPct = ots.projects_pct ?? ots.projects_on_time_pct
  const stagesPct = ots.stages_pct ?? ots.stages_on_time_pct
  const avgDev = ots.avg_deviation_days ?? ots.avg_deviation
  return [
    { label: 'Проектов в срок', value: projectsPct !== null && projectsPct !== undefined ? `${projectsPct}%` : (p.total_orders ?? '—'), color: '#27AE60' },
    { label: 'Стадий в срок', value: stagesPct !== null && stagesPct !== undefined ? `${stagesPct}%` : '—', color: '#F39C12' },
    { label: 'Ср. отклонение', value: avgDev !== null && avgDev !== undefined ? `${Number(avgDev).toFixed(1)} дн.` : '—', color: '#E74C3C' },
    { label: 'На паузе', value: d.paused_count ?? p.paused ?? '—', color: '#9B59B6' },
  ]
})

const cityChart = computed(() => {
  const p = projectStats.value
  if (!p?.by_cities) return null
  const entries = Object.entries(p.by_cities).sort((a, b) => b[1] - a[1]).slice(0, 8)
  if (entries.length === 0) return null
  return { labels: entries.map(([k]) => k), datasets: [{ label: 'Проектов', data: entries.map(([, v]) => v), color: '#85C1E9' }] }
})

const agentChart = computed(() => {
  const p = projectStats.value
  if (!p?.by_agents) return null
  const entries = Object.entries(p.by_agents).sort((a, b) => b[1] - a[1]).slice(0, 8)
  if (entries.length === 0) return null
  return { labels: entries.map(([k]) => k), datasets: [{ label: 'Проектов', data: entries.map(([, v]) => v), color: '#ffd93c' }] }
})

const stageDurationsChart = computed(() => {
  const p = crmDetailed.value
  if (!p?.stage_durations) return null
  const durations = (p.stage_durations || []).filter(d => !d.stage?.toUpperCase().startsWith('ДАТА НАЧАЛА'))
  if (durations.length === 0) return null

  // Группируем по stage_code префиксу (S1_, S2_... для индивидуальных или T1_, T2_... для шаблонных).
  // Название берём из stage_groups сервера если есть, иначе "Стадия N".
  const serverGroups = Object.fromEntries((p.stage_groups || []).map(sg => [sg.code, sg.name]))
  const groupMap = new Map()
  durations.forEach((d, i) => {
    const sc = d.stage_code || ''
    const m = sc.match(/^([ST]\d+)_/)
    if (!m) return
    const key = m[1] // "S1", "S2", "T1", "T2", ...
    if (!groupMap.has(key)) {
      const num = key.slice(1)
      groupMap.set(key, {
        label: serverGroups[key] || `Стадия ${num}`,
        startIndex: i,
        endIndex: i,
      })
    } else {
      groupMap.get(key).endIndex = i
    }
  })
  const groups = [...groupMap.values()]

  return {
    labels: durations.map(d => (d.stage || '').substring(0, 20)),
    datasets: [
      { label: 'Норматив', data: durations.map(d => d.norm_days || 0), color: '#4CAF50' },
      { label: 'Факт (дни)', data: durations.map(d => d.avg_actual_days ?? d.actual_days ?? 0), color: '#F39C12' },
    ],
    groups,
  }
})

// ========== НАДЗОР ==========
const supervisionMini = computed(() => {
  const s = supervisionStats.value || {}
  const sd = supervisionDetailed.value || {}
  const v = sd.visits || {}
  const avgVisits = v.avg_per_card ?? (sd.total && sd.site_visits ? (sd.site_visits / sd.total).toFixed(1) : '—')
  return [
    { label: 'Всего надзоров', value: s.total_orders ?? '—', color: '#27AE60' },
    { label: 'Активных', value: s.active ?? '—', color: '#F39C12' },
    { label: 'По индивид.', value: s.by_individual ?? '—', color: '#F57C00' },
    { label: 'По шаблонным', value: s.by_template ?? '—', color: '#C62828' },
    { label: 'Всего выездов', value: v.total ?? sd.site_visits ?? '—', color: '#E67E22' },
    { label: 'На объект', value: v.on_site ?? '—', color: '#27AE60' },
    { label: 'К поставщикам', value: v.supplier ?? '—', color: '#3498DB' },
    { label: 'Просрочено выездов', value: v.overdue ?? '—', color: '#E74C3C' },
    { label: 'Ср. выездов/надзор', value: avgVisits, color: '#9B59B6' },
  ]
})

// Надзоры по агентам — из supervision-analytics (включает агентов с 0)
const supervisionByAgentChart = computed(() => {
  const sd = supervisionDetailed.value
  if (sd?.by_agent?.length > 0) {
    const items = sd.by_agent.filter(a => a.count > 0 || true) // все агенты, включая 0
    return {
      labels: items.map(a => a.agent_name),
      datasets: [{ label: 'Надзоров', data: items.map(a => a.count), color: '#F39C12' }],
    }
  }
  // Fallback: старый формат из statistics/supervision
  const s = supervisionStats.value || {}
  const ba = s.by_agents || {}
  const entries = Object.entries(ba)
  if (entries.length === 0) return null
  return {
    labels: entries.map(([k]) => k),
    datasets: [{ label: 'Надзоров', data: entries.map(([, v]) => v), color: '#F39C12' }],
  }
})

// Надзоры по городам (из supervision-analytics)
const supervisionByCityChart = computed(() => {
  const sd = supervisionDetailed.value
  // Пробуем visits.by_city (с разбивкой по типу), затем by_city (общий)
  const vcities = sd?.visits?.by_city
  if (vcities?.length) {
    return {
      labels: vcities.slice(0, 10).map(e => e.city),
      datasets: [
        { label: 'На объект', data: vcities.slice(0, 10).map(e => e.on_site), color: '#27AE60' },
        { label: 'К поставщикам', data: vcities.slice(0, 10).map(e => e.supplier), color: '#3498DB' },
      ],
    }
  }
  if (!sd?.by_city?.length) return null
  const entries = sd.by_city.slice(0, 10)
  return {
    labels: entries.map(e => e.city),
    datasets: [{ label: 'Надзоров', data: entries.map(e => e.count), color: '#85C1E9' }],
  }
})

// ========== ЗАГРУЗКА ДАННЫХ ==========
async function loadData() {
  console.log('[Reports] Loading... filters:', JSON.stringify(filters.value))
  const { api: axCheck } = await import('src/boot/axios')
  console.log('[Reports] Token:', !!axCheck.defaults.headers.common['Authorization'])
  const params = { year: filters.value.year }
  if (filters.value.quarter) params.quarter = filters.value.quarter
  if (filters.value.month) params.month = filters.value.month
  const pt = projectTab.value === 'template' ? 'Шаблонный' : 'Индивидуальный'

  const [sumR, funnelR, projR, dynR, supR, contR, cbyPR, crmDetR, supDetR] = await Promise.allSettled([
    reportsApi.getSummary(params),
    reportsApi.getFunnel(params),
    reportsApi.getCrmAnalytics({ ...params, project_type: pt }),
    reportsApi.getClientsDynamics({ year: filters.value.year }),
    statisticsApi.getSupervision(params),
    dashboardApi.getContracts(params),
    statisticsApi.getContractsByPeriod({ year: filters.value.year }),
    reportsApi.getCrmAnalyticsDetailed({ ...params, project_type: pt }),
    reportsApi.getSupervisionAnalytics(params),
  ])

  console.log('[Reports] Results:', {
    sum: sumR?.status, funnel: funnelR?.status, proj: projR?.status,
    dyn: dynR?.status, sup: supR?.status, cont: contR?.status,
    cbyP: cbyPR?.status, crmDet: crmDetR?.status, supDet: supDetR?.status,
  })
  ;[sumR, funnelR, projR, dynR, supR, contR, cbyPR, crmDetR, supDetR].forEach((r, i) => {
    if (r.status === 'rejected') console.error(`[Reports] Request ${i} failed:`, r.reason?.response?.status, r.reason?.message)
  })

  if (sumR.status === 'fulfilled') summary.value = sumR.value.data
  else console.error('Reports summary error:', sumR.reason?.response?.status, sumR.reason?.message)
  if (funnelR.status === 'fulfilled') funnel.value = funnelR.value.data
  else console.error('Reports funnel error:', funnelR.reason?.response?.status, funnelR.reason?.message)
  if (projR.status === 'fulfilled') projectStats.value = projR.value.data
  else console.error('Reports projects error:', projR.reason?.response?.status, projR.reason?.message)
  if (dynR.status === 'fulfilled') clientsDynamicsRaw.value = dynR.value.data
  else console.error('Reports clients dynamics error:', dynR.reason?.response?.status, dynR.reason?.message)
  if (supR.status === 'fulfilled') supervisionStats.value = supR.value.data
  else console.error('Reports supervision error:', supR.reason?.response?.status, supR.reason?.message)
  if (contR.status === 'fulfilled') contractsDashboard.value = contR.value.data
  else console.error('Reports contracts error:', contR.reason?.response?.status, contR.reason?.message)
  if (cbyPR.status === 'fulfilled') contractsByPeriodRaw.value = cbyPR.value.data
  else console.error('Reports contracts by period error:', cbyPR.reason?.response?.status, cbyPR.reason?.message)
  if (crmDetR.status === 'fulfilled') crmDetailed.value = crmDetR.value.data
  else console.error('Reports CRM detailed error:', crmDetR.reason?.response?.status, crmDetR.reason?.message)
  if (supDetR.status === 'fulfilled') supervisionDetailed.value = supDetR.value.data
  else console.error('Reports supervision detailed error:', supDetR.reason?.response?.status, supDetR.reason?.message)
}

async function exportPDF() {
  pdfLoading.value = true
  // Open popup BEFORE any await — popup blockers only allow this in synchronous click context
  const w = window.open('', '_blank', 'width=1200,height=800')
  if (!w) { pdfLoading.value = false; return }
  try { w.moveTo(0, 0); w.resizeTo(screen.width, screen.height) } catch(e) {}
  w.document.write('<!DOCTYPE html><html><head><meta charset="utf-8"><title>Загрузка...</title></head><body style="font-family:Arial;padding:40px;color:#555;text-align:center"><p style="font-size:18px">⏳ Формирование отчёта...</p></body></html>')
  w.document.close()

  try {
    const params = { year: filters.value.year }
    if (filters.value.quarter) params.quarter = filters.value.quarter
    if (filters.value.month) params.month = filters.value.month

    const [indStatR, tmplStatR, indDetR, tmplDetR] = await Promise.allSettled([
      reportsApi.getCrmAnalytics({ ...params, project_type: 'Индивидуальный' }),
      reportsApi.getCrmAnalytics({ ...params, project_type: 'Шаблонный' }),
      reportsApi.getCrmAnalyticsDetailed({ ...params, project_type: 'Индивидуальный' }),
      reportsApi.getCrmAnalyticsDetailed({ ...params, project_type: 'Шаблонный' }),
    ])

    const indStat = indStatR.status === 'fulfilled' ? indStatR.value.data : null
    const tmplStat = tmplStatR.status === 'fulfilled' ? tmplStatR.value.data : null
    const indDet = indDetR.status === 'fulfilled' ? indDetR.value.data : null
    const tmplDet = tmplDetR.status === 'fulfilled' ? tmplDetR.value.data : null

    const yr = filters.value.year
    const qLabel = filters.value.quarter ? `Q${filters.value.quarter}` : ''
    const mLabel = filters.value.month ? monthOpts.find(m => m.value === filters.value.month)?.label : ''
    const period = [yr, qLabel, mLabel].filter(Boolean).join(' / ')
    const now = new Date().toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })

    const kpiGrid = (items) =>
      `<div class="kpi-grid">${items.map(k =>
        `<div class="kpi-card" style="border-left-color:${k.color || '#aaa'}">
          <div class="kpi-val">${k.value}</div><div class="kpi-lbl">${k.label}</div>
        </div>`).join('')}</div>`

    const horzTable = (items) =>
      `<table><tr>${items.map(m => `<th class="tc">${m.label}</th>`).join('')}</tr>
      <tr>${items.map(m => `<td class="tc fw" style="color:${m.color || '#333'}">${m.value}</td>`).join('')}</tr></table>`

    const listTable = (cols, rows) =>
      `<table><tr>${cols.map(c => `<th${c.r ? ' class="num"' : ''}>${c.label}</th>`).join('')}</tr>
      ${rows.map(r => `<tr>${cols.map(c => `<td${c.r ? ' class="num"' : ''}>${r[c.key] ?? ''}</td>`).join('')}</tr>`).join('')}</table>`

    const computeStatCards = (stat, det) => {
      const p = stat || {}
      const d = det || {}
      const ots = d.on_time_stats || {}
      const projectsPct = ots.projects_pct ?? ots.projects_on_time_pct
      const stagesPct = ots.stages_pct ?? ots.stages_on_time_pct
      const avgDev = ots.avg_deviation_days ?? ots.avg_deviation
      return [
        { label: 'Проектов в срок', value: projectsPct != null ? `${projectsPct}%` : (p.total_orders ?? '—'), color: '#27AE60' },
        { label: 'Стадий в срок', value: stagesPct != null ? `${stagesPct}%` : '—', color: '#F39C12' },
        { label: 'Ср. отклонение', value: avgDev != null ? `${Number(avgDev).toFixed(1)} дн.` : '—', color: '#E74C3C' },
        { label: 'На паузе', value: d.paused_count ?? p.paused ?? '—', color: '#9B59B6' },
      ]
    }

    const computeStageDurations = (det) => {
      if (!det?.stage_durations) return null
      const durs = det.stage_durations.filter(d => !d.stage?.toUpperCase().startsWith('ДАТА НАЧАЛА'))
      if (!durs.length) return null
      return {
        labels: durs.map(d => (d.stage || '').substring(0, 22)),
        norm: durs.map(d => d.norm_days || 0),
        fact: durs.map(d => d.avg_actual_days ?? d.actual_days ?? 0),
      }
    }

    // Collect chart data for inline script
    const chartData = {}

    const clientDyn = clientsDynamics.value
    if (clientDyn) chartData.clientDyn = { labels: clientDyn.labels, new: clientDyn.datasets[0].data, ret: clientDyn.datasets[1].data }

    if (contractsDashboard.value) chartData.clientTypePie = { labels: ['Индивидуальные', 'Шаблонные'], values: [contractsDashboard.value.individual_orders || 0, contractsDashboard.value.template_orders || 0] }

    const conDyn = contractsDynamics.value
    if (conDyn) chartData.conDyn = { labels: conDyn.labels, ind: conDyn.datasets[0].data, tmpl: conDyn.datasets[1].data }

    const fc = funnelChart.value
    if (fc) chartData.funnel = { labels: fc.labels, data: fc.datasets[0].data }

    const indSD = computeStageDurations(indDet)
    if (indSD) chartData.indStages = indSD
    if (indStat?.by_cities) { const e = Object.entries(indStat.by_cities).sort((a, b) => b[1] - a[1]).slice(0, 8); if (e.length) chartData.indCities = { labels: e.map(([k]) => k), data: e.map(([, v]) => v) } }
    if (indStat?.by_agents) { const e = Object.entries(indStat.by_agents).sort((a, b) => b[1] - a[1]).slice(0, 8); if (e.length) chartData.indAgents = { labels: e.map(([k]) => k), data: e.map(([, v]) => v) } }

    const tmplSD = computeStageDurations(tmplDet)
    if (tmplSD) chartData.tmplStages = tmplSD
    if (tmplStat?.by_cities) { const e = Object.entries(tmplStat.by_cities).sort((a, b) => b[1] - a[1]).slice(0, 8); if (e.length) chartData.tmplCities = { labels: e.map(([k]) => k), data: e.map(([, v]) => v) } }
    if (tmplStat?.by_agents) { const e = Object.entries(tmplStat.by_agents).sort((a, b) => b[1] - a[1]).slice(0, 8); if (e.length) chartData.tmplAgents = { labels: e.map(([k]) => k), data: e.map(([, v]) => v) } }

    const sba = supervisionByAgentChart.value
    if (sba) chartData.supAgent = { labels: sba.labels, data: sba.datasets[0].data }
    const sbc = supervisionByCityChart.value
    if (sbc) chartData.supCity = { labels: sbc.labels, datasets: sbc.datasets.map(d => ({ label: d.label, data: d.data, color: d.color })) }

    // Build body HTML — таблицы + компактные графики рядом
    const funnelH = chartData.funnel ? Math.max(120, chartData.funnel.labels.length * 24 + 40) : 120
    const indStH = chartData.indStages ? Math.max(150, chartData.indStages.labels.length * 22 + 50) : 150
    const tmplStH = chartData.tmplStages ? Math.max(150, chartData.tmplStages.labels.length * 22 + 50) : 150
    const indCitH = chartData.indCities ? Math.max(100, chartData.indCities.labels.length * 20 + 30) : 100
    const tmplCitH = chartData.tmplCities ? Math.max(100, chartData.tmplCities.labels.length * 20 + 30) : 100
    const supAgH = chartData.supAgent ? Math.max(100, chartData.supAgent.labels.length * 20 + 30) : 100

    let body = ''

    // ---- KPI ----
    body += `<h2>Ключевые показатели</h2>${kpiGrid(kpiCards.value)}`
    if (agentKpi.value.length > 0) {
      body += `<h3>По агентам</h3>${listTable([{ key: 'label', label: 'Показатель' }, { key: 'value', label: 'Значение', r: true }], agentKpi.value)}`
    }

    // ---- Клиенты ----
    body += `<h2>Клиенты</h2>${horzTable(clientMini.value)}`
    if (chartData.clientDyn || chartData.clientTypePie) {
      body += '<div class="cr">'
      if (chartData.clientDyn) body += '<div><div class="ct">Динамика клиентов</div><canvas id="clientDyn" width="360" height="150" style="display:block;max-width:100%;height:150px"></canvas></div>'
      if (chartData.clientTypePie) body += '<div><div class="ct">Тип проектов</div><canvas id="clientTypePie" width="260" height="150" style="display:block;max-width:260px;height:150px"></canvas></div>'
      body += '</div>'
    }
    const cba = clientsByAgentChart.value
    if (cba) body += `<h3>Клиенты по агентам</h3>${listTable([{ key: 'label', label: 'Агент' }, { key: 'val', label: 'Клиентов', r: true }], cba.labels.map((l, i) => ({ label: l, val: cba.datasets[0].data[i] })))}`

    // ---- Договоры ----
    body += `<h2>Договоры</h2>${horzTable(contractMini.value)}`
    if (chartData.conDyn) body += '<div class="ct">Договоры по месяцам</div><canvas id="conDyn" width="700" height="140" style="display:block;max-width:100%;height:140px"></canvas>'
    const amtDyn = contractsAmountDynamics.value
    if (amtDyn) {
      body += `<h3>Стоимость по месяцам</h3><table><tr><th>Месяц</th><th class="num">Стоимость</th></tr>${amtDyn.labels.map((l, i) => `<tr><td>${l}</td><td class="num">${fmtMoney(amtDyn.datasets[0].data[i] || 0)}</td></tr>`).join('')}</table>`
    }
    const tc = topCitiesChart.value
    if (tc) body += `<h3>ТОП городов</h3>${listTable([{ key: 'label', label: 'Город' }, { key: 'val', label: 'Договоров', r: true }], tc.labels.map((l, i) => ({ label: l, val: tc.datasets[0].data[i] })))}`
    const cbA = contractsByAgentChart.value
    const abA = amountByAgentChart.value
    if (cbA) {
      const cols = [{ key: 'label', label: 'Агент' }, { key: 'cnt', label: 'Договоров', r: true }]
      if (abA) cols.push({ key: 'amt', label: 'Стоимость', r: true })
      body += `<h3>Договоры по агентам</h3>${listTable(cols, cbA.labels.map((l, i) => ({ label: l, cnt: cbA.datasets[0].data[i], amt: abA ? fmtMoney(abA.datasets[0].data[i] || 0) : '' })))}`
    }

    // ---- CRM Индивидуальные ----
    const indCards = computeStatCards(indStat, indDet)
    body += `<h2>CRM Аналитика — Индивидуальные</h2>${kpiGrid(indCards)}`
    if (chartData.funnel) body += `<div class="ct">Воронка проектов</div><canvas id="funnel" width="700" height="${funnelH}" style="display:block;max-width:100%;height:${funnelH}px"></canvas>`
    if (chartData.indStages) body += `<div class="ct">Длительность этапов — норматив vs факт (дни)</div><canvas id="indStages" width="700" height="${indStH}" style="display:block;max-width:100%;height:${indStH}px"></canvas>`
    if (chartData.indCities || chartData.indAgents) {
      body += '<div class="cr">'
      if (chartData.indCities) body += `<div><div class="ct">По городам</div><canvas id="indCities" width="350" height="${indCitH}" style="display:block;max-width:100%;height:${indCitH}px"></canvas></div>`
      if (chartData.indAgents) body += '<div><div class="ct">По агентам</div><canvas id="indAgents" width="350" height="120" style="display:block;max-width:100%;height:120px"></canvas></div>'
      body += '</div>'
    }

    // ---- CRM Шаблонные ----
    const tmplCards = computeStatCards(tmplStat, tmplDet)
    body += `<h2>CRM Аналитика — Шаблонные</h2>${kpiGrid(tmplCards)}`
    if (chartData.tmplStages) body += `<div class="ct">Длительность этапов — норматив vs факт (дни)</div><canvas id="tmplStages" width="700" height="${tmplStH}" style="display:block;max-width:100%;height:${tmplStH}px"></canvas>`
    if (chartData.tmplCities || chartData.tmplAgents) {
      body += '<div class="cr">'
      if (chartData.tmplCities) body += `<div><div class="ct">По городам</div><canvas id="tmplCities" width="350" height="${tmplCitH}" style="display:block;max-width:100%;height:${tmplCitH}px"></canvas></div>`
      if (chartData.tmplAgents) body += '<div><div class="ct">По агентам</div><canvas id="tmplAgents" width="350" height="120" style="display:block;max-width:100%;height:120px"></canvas></div>'
      body += '</div>'
    }

    // ---- Надзор ----
    body += `<h2>Авторский надзор</h2>${horzTable(supervisionMini.value)}`
    if (chartData.supAgent || chartData.supCity) {
      body += '<div class="cr">'
      if (chartData.supAgent) body += `<div><div class="ct">Надзоры по агентам</div><canvas id="supAgent" width="350" height="${supAgH}" style="display:block;max-width:100%;height:${supAgH}px"></canvas></div>`
      if (chartData.supCity) body += '<div><div class="ct">Выезды по городам</div><canvas id="supCity" width="350" height="160" style="display:block;max-width:100%;height:160px"></canvas></div>'
      body += '</div>'
    }
    const sba2 = supervisionByAgentChart.value
    if (sba2) body += `<h3>По агентам (таблица)</h3>${listTable([{ key: 'label', label: 'Агент' }, { key: 'val', label: 'Надзоров', r: true }], sba2.labels.map((l, i) => ({ label: l, val: sba2.datasets[0].data[i] })))}`
    const sbc2 = supervisionByCityChart.value
    if (sbc2) {
      body += `<h3>Выезды по городам (таблица)</h3><table><tr><th>Город</th>${sbc2.datasets.map(d => `<th class="num">${d.label}</th>`).join('')}</tr>${sbc2.labels.map((l, i) => `<tr><td>${l}</td>${sbc2.datasets.map(d => `<td class="num">${d.data[i] || 0}</td>`).join('')}</tr>`).join('')}</table>`
    }

    const cdJson = JSON.stringify(chartData).replace(/<\//g, '<\\/')

    const fullHtml = `<!DOCTYPE html><html><head>
  <meta charset="utf-8">
  <title>Отчёт — ${period}</title>
  <style>
    body { font-family: Arial, sans-serif; font-size: 11px; color: #222; margin: 20px; }
    h1 { font-size: 16px; margin: 0 0 4px; }
    .sub { color: #888; font-size: 10px; margin-bottom: 16px; }
    h2 { font-size: 13px; margin: 18px 0 6px; border-bottom: 2px solid #333; padding-bottom: 3px; }
    h3 { font-size: 11px; margin: 10px 0 4px; color: #555; }
    table { border-collapse: collapse; width: 100%; margin-bottom: 10px; break-inside: avoid; }
    th { background: #f0f0f0; text-align: left; padding: 4px 8px; border: 1px solid #ccc; font-size: 10px; }
    td { padding: 3px 8px; border: 1px solid #eee; font-size: 10px; }
    .num { text-align: right; } .tc { text-align: center; } .fw { font-weight: bold; }
    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 10px; break-inside: avoid; }
    .kpi-card { border-left: 3px solid #aaa; background: #fafafa; padding: 5px 8px; border-radius: 4px; }
    .kpi-val { font-size: 15px; font-weight: bold; } .kpi-lbl { font-size: 9px; color: #777; }
    .cr { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 8px; break-inside: avoid; }
    .ct { font-size: 10px; color: #555; font-weight: bold; margin: 8px 0 3px; }
    canvas { display: block; max-width: 100%; margin-bottom: 8px; break-inside: avoid; }
    @media print { @page { size: A4 portrait; margin: 10mm; } body { margin: 0; } }
  </style>
</head><body>
  <h1>Отчёты и Статистика</h1>
  <div class="sub">Период: ${period} &nbsp;·&nbsp; Сформирован: ${now}</div>
  ${body}
  <` + 'script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"><' + `/script>
  <` + `script>
  var __cd = ${cdJson};
  var ROPTS = { animation: false, responsive: false, maintainAspectRatio: false };
  var PieDL = {
    id: 'pieDL',
    afterDraw: function(chart) {
      if (chart.config.type !== 'pie') return;
      var ctx = chart.ctx, ds = chart.data.datasets[0], meta = chart.getDatasetMeta(0);
      var total = ds.data.reduce(function(a,b){return a+b;},0); if (!total) return;
      meta.data.forEach(function(arc, i) {
        var val = ds.data[i]; if (!val) return;
        var pct = Math.round(val/total*100); if (pct < 3) return;
        var angle = (arc.startAngle + arc.endAngle) / 2, r = arc.outerRadius * 0.65;
        var x = arc.x + r * Math.cos(angle), y = arc.y + r * Math.sin(angle);
        ctx.save(); ctx.fillStyle = '#fff'; ctx.font = 'bold 10px sans-serif';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(val, x, y - 6); ctx.fillText(pct + '%', x, y + 7); ctx.restore();
      });
    }
  };
  function mkScales(ix, sm) { return { x: { beginAtZero: true, ticks: { font: { size: sm||8 } } }, y: { ticks: { font: { size: sm||8 } } } }; }
  function hBar(id, labels, data, label, color) {
    var el = document.getElementById(id); if (!el) return;
    new Chart(el, { type: 'bar', data: { labels: labels, datasets: [{ label: label, data: data, backgroundColor: color || '#3498DB' }] },
      options: Object.assign({}, ROPTS, { indexAxis: 'y', plugins: { legend: { display: false } }, scales: mkScales('y') }) });
  }
  function hBar2(id, labels, datasets) {
    var el = document.getElementById(id); if (!el) return;
    new Chart(el, { type: 'bar', data: { labels: labels, datasets: datasets.map(function(d) { return { label: d.label, data: d.data, backgroundColor: d.color || '#3498DB' }; }) },
      options: Object.assign({}, ROPTS, { indexAxis: 'y', plugins: { legend: { display: true, labels: { font: { size: 9 }, boxWidth: 10 } } }, scales: mkScales('y') }) });
  }
  function vBar(id, labels, datasets) {
    var el = document.getElementById(id); if (!el) return;
    new Chart(el, { type: 'bar', data: { labels: labels, datasets: datasets.map(function(d) { return { label: d.label, data: d.data, backgroundColor: d.color || '#3498DB' }; }) },
      options: Object.assign({}, ROPTS, { plugins: { legend: { display: datasets.length > 1, labels: { font: { size: 9 }, boxWidth: 10 } } }, scales: { x: { ticks: { font: { size: 8 } } }, y: { beginAtZero: true, ticks: { font: { size: 9 } } } } }) });
  }
  function lineChart(id, labels, datasets) {
    var el = document.getElementById(id); if (!el) return;
    new Chart(el, { type: 'line', data: { labels: labels, datasets: datasets.map(function(d) { return { label: d.label, data: d.data, borderColor: d.color || '#3498DB', backgroundColor: (d.color||'#3498DB')+'33', fill: false, tension: 0.3 }; }) },
      options: Object.assign({}, ROPTS, { plugins: { legend: { display: datasets.length > 1, labels: { font: { size: 9 }, boxWidth: 10 } } }, scales: { y: { beginAtZero: true, ticks: { font: { size: 9 } } }, x: { ticks: { font: { size: 9 } } } } }) });
  }
  function pieChart(id, labels, values) {
    var el = document.getElementById(id); if (!el) return;
    new Chart(el, { type: 'pie', plugins: [PieDL],
      data: { labels: labels, datasets: [{ data: values, backgroundColor: ['#F39C12','#C62828','#27AE60','#3498DB','#9B59B6','#E74C3C'] }] },
      options: Object.assign({}, ROPTS, { plugins: { legend: { labels: { font: { size: 9 } } } } }) });
  }
  window.addEventListener('load', function() {
    var cd = __cd;
    try { if (cd.clientDyn) lineChart('clientDyn', cd.clientDyn.labels, [{ label: 'Новые', data: cd.clientDyn.new, color: '#27AE60' }, { label: 'Повторные', data: cd.clientDyn.ret, color: '#9B59B6' }]); } catch(e) {}
    try { if (cd.clientTypePie) pieChart('clientTypePie', cd.clientTypePie.labels, cd.clientTypePie.values); } catch(e) {}
    try { if (cd.conDyn) vBar('conDyn', cd.conDyn.labels, [{ label: 'Индивид.', data: cd.conDyn.ind, color: '#F39C12' }, { label: 'Шаблон.', data: cd.conDyn.tmpl, color: '#C62828' }]); } catch(e) {}
    try { if (cd.funnel) hBar('funnel', cd.funnel.labels, cd.funnel.data, 'Проектов', '#F39C12'); } catch(e) {}
    try { if (cd.indStages) hBar2('indStages', cd.indStages.labels, [{ label: 'Норматив', data: cd.indStages.norm, color: '#4CAF50' }, { label: 'Факт', data: cd.indStages.fact, color: '#F39C12' }]); } catch(e) {}
    try { if (cd.indCities) hBar('indCities', cd.indCities.labels, cd.indCities.data, 'Проектов', '#85C1E9'); } catch(e) {}
    try { if (cd.indAgents) hBar('indAgents', cd.indAgents.labels, cd.indAgents.data, 'Проектов', '#ffd93c'); } catch(e) {}
    try { if (cd.tmplStages) hBar2('tmplStages', cd.tmplStages.labels, [{ label: 'Норматив', data: cd.tmplStages.norm, color: '#4CAF50' }, { label: 'Факт', data: cd.tmplStages.fact, color: '#C62828' }]); } catch(e) {}
    try { if (cd.tmplCities) hBar('tmplCities', cd.tmplCities.labels, cd.tmplCities.data, 'Проектов', '#85C1E9'); } catch(e) {}
    try { if (cd.tmplAgents) hBar('tmplAgents', cd.tmplAgents.labels, cd.tmplAgents.data, 'Проектов', '#C62828'); } catch(e) {}
    try { if (cd.supAgent) hBar('supAgent', cd.supAgent.labels, cd.supAgent.data, 'Надзоров', '#F39C12'); } catch(e) {}
    try { if (cd.supCity) vBar('supCity', cd.supCity.labels, cd.supCity.datasets); } catch(e) {}
    setTimeout(function() { try { window.focus(); window.print(); } catch(e2) {} }, 900);
  });
  <` + `/script>
</body></html>`

    w.document.open()
    w.document.write(fullHtml)
    w.document.close()

  } catch(e) {
    console.error('exportPDF error:', e)
  } finally {
    pdfLoading.value = false
  }
}
watch(projectTab, () => loadData())
watch(filters, () => loadData(), { deep: true })
function onRefresh(done) { loadData().finally(done) }

onMounted(() => loadData())
</script>

<style scoped>
.rep-export-btn {
  height: 26px;
  padding: 0 10px;
  border: 1px solid #2196f3;
  border-radius: 4px;
  background: white;
  color: #2196f3;
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
  flex-shrink: 0;
  outline: none;
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: center;
}
.rep-export-btn:hover { background: #e3f2fd; }
.rep-export-btn:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
