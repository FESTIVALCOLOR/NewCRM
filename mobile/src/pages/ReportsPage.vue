<template>
  <q-page padding>
    <div class="row items-center justify-between q-mb-sm">
      <div class="text-subtitle1 text-weight-bold" style="color: #333">Отчёты и Статистика</div>
      <q-btn flat dense icon="picture_as_pdf" color="grey-7" @click="exportPDF"><q-tooltip>Экспорт PDF</q-tooltip></q-btn>
    </div>

    <!-- Фильтры -->
    <q-card class="is-card q-mb-md">
      <q-card-section class="q-pa-sm">
        <div class="row q-col-gutter-sm">
          <div class="col-4"><q-select v-model="filters.year" :options="years" label="Год" outlined dense @update:model-value="loadData" /></div>
          <div class="col-4"><q-select v-model="filters.quarter" :options="quarters" label="Квартал" outlined dense emit-value map-options @update:model-value="loadData" /></div>
          <div class="col-4"><q-select v-model="filters.month" :options="monthOpts" label="Месяц" outlined dense emit-value map-options @update:model-value="loadData" /></div>
        </div>
      </q-card-section>
    </q-card>

    <q-pull-to-refresh @refresh="onRefresh">

      <!-- ========== КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ ========== -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold">Ключевые показатели</div></q-card-section>
        <q-card-section>
          <div class="row q-col-gutter-xs q-mb-sm">
            <div class="col-4 col-md-2" v-for="kpi in kpiCards" :key="kpi.label">
              <div class="q-pa-xs" :style="{ borderLeft: `3px solid ${kpi.color}`, borderRadius: '6px', background: '#FAFAFA' }">
                <div class="text-subtitle1 text-weight-bold">{{ kpi.value }}</div>
                <div class="text-caption text-grey-7" style="font-size: 9px">{{ kpi.label }}</div>
              </div>
            </div>
          </div>
          <!-- По агентам -->
          <div class="row q-col-gutter-xs" v-if="agentKpi.length > 0">
            <div class="col-6" v-for="a in agentKpi" :key="a.label">
              <div class="q-pa-xs" :style="{ borderLeft: `3px solid ${a.color}`, borderRadius: '6px', background: '#FAFAFA' }">
                <div class="text-subtitle2 text-weight-bold">{{ a.value }}</div>
                <div class="text-caption text-grey-7" style="font-size: 9px">{{ a.label }}</div>
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- ========== КЛИЕНТЫ ========== -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Клиенты</div>
          <div class="row q-col-gutter-xs q-mb-md">
            <div class="col-4 col-md-2 text-center" v-for="m in clientMini" :key="m.label">
              <div class="text-subtitle1 text-weight-bold" :style="{ color: m.color || '#333' }">{{ m.value }}</div>
              <div class="text-caption text-grey-7" style="font-size: 9px">{{ m.label }}</div>
            </div>
          </div>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6">
              <div class="text-caption text-weight-bold text-center q-mb-xs">Динамика клиентов</div>
              <line-chart v-if="clientsDynamics" :labels="clientsDynamics.labels" :datasets="clientsDynamics.datasets" />
            </div>
            <div class="col-12 col-md-6" v-if="clientTypePie">
              <div class="text-caption text-weight-bold text-center q-mb-xs">Тип клиентов</div>
              <pie-chart :labels="clientTypePie.labels" :values="clientTypePie.values" />
            </div>
          </div>
          <div class="row q-col-gutter-md q-mt-sm">
            <div class="col-12 col-md-6" v-if="clientsByAgentChart">
              <div class="text-caption text-weight-bold q-mb-xs">Клиенты по агентам</div>
              <bar-chart :labels="clientsByAgentChart.labels" :datasets="clientsByAgentChart.datasets" horizontal />
            </div>
            <div class="col-12 col-md-6" v-if="newVsReturningChart">
              <div class="text-caption text-weight-bold q-mb-xs">Новые vs Повторные</div>
              <bar-chart :labels="newVsReturningChart.labels" :datasets="newVsReturningChart.datasets" />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- ========== ДОГОВОРЫ ========== -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Договоры</div>
          <div class="row q-col-gutter-xs q-mb-md">
            <div class="col-4 col-md-2 text-center" v-for="m in contractMini" :key="m.label">
              <div class="text-subtitle1 text-weight-bold" :style="{ color: m.color || '#333' }">{{ m.value }}</div>
              <div class="text-caption text-grey-7" style="font-size: 9px">{{ m.label }}</div>
            </div>
          </div>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6" v-if="contractsDynamics">
              <div class="text-caption text-weight-bold q-mb-xs">Договоры по месяцам</div>
              <bar-chart :labels="contractsDynamics.labels" :datasets="contractsDynamics.datasets" />
            </div>
            <div class="col-12 col-md-6" v-if="contractsAmountDynamics">
              <div class="text-caption text-weight-bold q-mb-xs">Стоимость по месяцам</div>
              <line-chart :labels="contractsAmountDynamics.labels" :datasets="contractsAmountDynamics.datasets" />
            </div>
          </div>
          <div class="row q-col-gutter-md q-mt-sm">
            <div class="col-12 col-md-6" v-if="projectTypePie">
              <div class="text-caption text-weight-bold text-center q-mb-xs">Типы проектов</div>
              <pie-chart :labels="projectTypePie.labels" :values="projectTypePie.values" />
            </div>
            <div class="col-12 col-md-6" v-if="topCitiesChart">
              <div class="text-caption text-weight-bold q-mb-xs">ТОП городов</div>
              <bar-chart :labels="topCitiesChart.labels" :datasets="topCitiesChart.datasets" horizontal />
            </div>
          </div>
          <div class="row q-col-gutter-md q-mt-sm">
            <div class="col-12 col-md-6" v-if="contractsByAgentChart">
              <div class="text-caption text-weight-bold q-mb-xs">Договоры по агентам</div>
              <bar-chart :labels="contractsByAgentChart.labels" :datasets="contractsByAgentChart.datasets" />
            </div>
            <div class="col-12 col-md-6" v-if="amountByAgentChart">
              <div class="text-caption text-weight-bold q-mb-xs">Стоимость по агентам</div>
              <bar-chart :labels="amountByAgentChart.labels" :datasets="amountByAgentChart.datasets" horizontal />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- ========== CRM АНАЛИТИКА ========== -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">CRM Аналитика</div>
          <q-tabs v-model="projectTab" dense active-color="dark" indicator-color="accent" no-caps align="left">
            <q-tab name="individual" label="Индивидуальные" />
            <q-tab name="template" label="Шаблонные" />
          </q-tabs>
          <div v-if="projectStats" class="q-mt-md">
            <div class="row q-col-gutter-xs q-mb-md">
              <div class="col-3" v-for="s in projectStatCards" :key="s.label">
                <div class="text-center q-pa-xs" :style="{ border: `1px solid ${s.color || '#E0E0E0'}`, borderRadius: '6px' }">
                  <div class="text-subtitle1 text-weight-bold">{{ s.value }}</div>
                  <div class="text-caption text-grey-7" style="font-size: 9px">{{ s.label }}</div>
                </div>
              </div>
            </div>
            <!-- Воронка -->
            <div class="q-mb-md" v-if="funnelChart">
              <div class="text-caption text-weight-bold q-mb-xs">Воронка проектов</div>
              <bar-chart :labels="funnelChart.labels" :datasets="funnelChart.datasets" horizontal />
            </div>
            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-6" v-if="cityChart">
                <div class="text-caption text-weight-bold q-mb-xs">По городам</div>
                <bar-chart :labels="cityChart.labels" :datasets="cityChart.datasets" horizontal />
              </div>
              <div class="col-12 col-md-6" v-if="agentChart">
                <div class="text-caption text-weight-bold q-mb-xs">По агентам</div>
                <bar-chart :labels="agentChart.labels" :datasets="agentChart.datasets" horizontal />
              </div>
            </div>
            <!-- Время стадий vs норматив -->
            <div class="q-mt-md" v-if="stageDurationsChart" style="overflow-x: auto">
              <div class="text-caption text-weight-bold q-mb-xs">Время стадий vs норматив — {{ projectTab === 'template' ? 'Шаблонный' : 'Индивидуальный' }}</div>
              <div style="min-width: 700px">
                <bar-chart :labels="stageDurationsChart.labels" :datasets="stageDurationsChart.datasets" :rotate-labels="90" :height="350" />
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- ========== АВТОРСКИЙ НАДЗОР ========== -->
      <q-card class="is-card q-mb-md" v-if="supervisionStats">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Авторский надзор</div>
          <div class="row q-col-gutter-xs q-mb-md">
            <div class="col-4 col-md-2 text-center" v-for="s in supervisionMini" :key="s.label">
              <div class="text-subtitle1 text-weight-bold" :style="{ color: s.color || '#333' }">{{ s.value }}</div>
              <div class="text-caption text-grey-7" style="font-size: 9px">{{ s.label }}</div>
            </div>
          </div>
          <div class="row q-col-gutter-md" v-if="supervisionByAgentChart">
            <div class="col-12 col-md-6">
              <div class="text-caption text-weight-bold q-mb-xs">Надзоры по агентам</div>
              <bar-chart :labels="supervisionByAgentChart.labels" :datasets="supervisionByAgentChart.datasets" horizontal />
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
const projectTab = ref('individual')

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
    { label: 'Средняя площадь', value: s.avg_area ? `${Math.round(s.avg_area)} м²` : '—', color: '#E67E22' }
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
        color: a.agent_color || '#999'
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
        { label: 'Повторные', data: raw.map(item => item.returning_clients || item.returning || 0), color: '#9B59B6' }
      ]
    }
  }
  const keys = Object.keys(raw).sort()
  if (keys.length === 0) return null
  return {
    labels: keys.map(k => { const p = k.split('-'); return p.length >= 2 ? months[parseInt(p[1]) - 1] || k : k }),
    datasets: [
      { label: 'Новые', data: keys.map(k => raw[k]?.new || raw[k]?.new_clients || 0), color: '#27AE60' },
      { label: 'Повторные', data: keys.map(k => raw[k]?.returning || raw[k]?.returning_clients || 0), color: '#9B59B6' }
    ]
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
    datasets: [{ label: 'Клиентов', data: ba.map(a => a.clients || 0), color: '#F39C12' }]
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
        { label: 'Повторные', data: raw.map(item => item.returning_clients || item.returning || 0), color: '#9B59B6' }
      ]
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
      { label: 'Шаблон.', data: months.map((_, i) => d[String(i + 1)]?.template_count || 0), color: '#C62828' }
    ]
  }
})

const contractsAmountDynamics = computed(() => {
  const d = contractsByPeriodRaw.value
  if (!d) return null
  const months = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек']
  return {
    labels: months,
    datasets: [{ label: 'Стоимость', data: months.map((_, i) => d[String(i + 1)]?.amount || 0), color: '#F39C12' }]
  }
})

const topCitiesChart = computed(() => {
  const ba = summary.value?.by_agent || []
  // Берём города из contractsDashboard или считаем из проектов
  const p = projectStats.value
  if (p?.by_cities) {
    const entries = Object.entries(p.by_cities).sort((a, b) => b[1] - a[1]).slice(0, 8)
    if (entries.length > 0) return {
      labels: entries.map(([k]) => k),
      datasets: [{ label: 'Договоров', data: entries.map(([, v]) => v), color: '#F39C12' }]
    }
  }
  return null
})

const contractsByAgentChart = computed(() => {
  const ba = summary.value?.by_agent || []
  if (ba.length === 0) return null
  return {
    labels: ba.map(a => a.agent_name),
    datasets: [{ label: 'Договоров', data: ba.map(a => a.contracts || 0), color: '#3498DB' }]
  }
})

const amountByAgentChart = computed(() => {
  const ba = summary.value?.by_agent || []
  if (ba.length === 0) return null
  return {
    labels: ba.map(a => a.agent_name),
    datasets: [{ label: 'Стоимость', data: ba.map(a => a.amount || 0), color: '#F39C12' }]
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
  return [
    { label: 'Проектов в срок', value: ots.projects_on_time_pct != null ? `${ots.projects_on_time_pct}%` : (p.total_orders ?? '—'), color: '#27AE60' },
    { label: 'Стадий в срок', value: ots.stages_on_time_pct != null ? `${ots.stages_on_time_pct}%` : '—', color: '#F39C12' },
    { label: 'Ср. отклонение', value: ots.avg_deviation ? `${Number(ots.avg_deviation).toFixed(1)} дн.` : '—', color: '#E74C3C' },
    { label: 'На паузе', value: d.paused_count ?? p.paused ?? '—', color: '#9B59B6' }
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
  // stage_durations приходят из /dashboard/reports/crm-analytics (не из /statistics/projects)
  const p = crmDetailed.value
  if (!p?.stage_durations) return null
  const durations = (p.stage_durations || []).filter(d => !d.stage?.toUpperCase().startsWith('ДАТА НАЧАЛА'))
  if (durations.length === 0) return null
  return {
    labels: durations.map(d => (d.stage || '').substring(0, 20)),
    datasets: [
      { label: 'Норматив', data: durations.map(d => d.norm_days || 0), color: '#4CAF50' },
      { label: 'Факт (дни)', data: durations.map(d => d.actual_days || 0), color: '#F39C12' }
    ]
  }
})

// ========== НАДЗОР ==========
const supervisionMini = computed(() => {
  const s = supervisionStats.value || {}
  const ba = s.by_agents || {}
  const agentItems = Object.entries(ba).map(([name, count]) => ({ label: `Надзоры — ${name}`, value: count, color: '#E67E22' }))
  return [
    { label: 'Всего надзоров', value: s.total_orders ?? '—', color: '#27AE60' },
    { label: 'Активных', value: s.active ?? '—', color: '#F39C12' },
    { label: 'По индивид.', value: s.by_individual ?? '—', color: '#F57C00' },
    { label: 'По шаблонным', value: s.by_template ?? '—', color: '#C62828' },
    ...agentItems
  ]
})

const supervisionByAgentChart = computed(() => {
  const s = supervisionStats.value || {}
  const ba = s.by_agents || {}
  const entries = Object.entries(ba)
  if (entries.length === 0) return null
  return {
    labels: entries.map(([k]) => k),
    datasets: [{ label: 'Надзоров', data: entries.map(([, v]) => v), color: '#F39C12' }]
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

  const [sumR, funnelR, projR, dynR, supR, contR, cbyPR, crmDetR] = await Promise.allSettled([
    reportsApi.getSummary(params),
    reportsApi.getFunnel(params),
    reportsApi.getCrmAnalytics({ ...params, project_type: pt }),
    reportsApi.getClientsDynamics({ year: filters.value.year }),
    statisticsApi.getProjects({ ...params, project_type: 'Авторский надзор' }),
    dashboardApi.getContracts(params),
    statisticsApi.getContractsByPeriod({ year: filters.value.year }),
    reportsApi.getCrmAnalyticsDetailed({ ...params, project_type: pt })
  ])

  console.log('[Reports] Results:', {
    sum: sumR?.status, funnel: funnelR?.status, proj: projR?.status,
    dyn: dynR?.status, sup: supR?.status, cont: contR?.status,
    cbyP: cbyPR?.status, crmDet: crmDetR?.status
  })
  ;[sumR, funnelR, projR, dynR, supR, contR, cbyPR, crmDetR].forEach((r, i) => {
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
}

function exportPDF() { window.print() }
watch(projectTab, () => loadData())
function onRefresh(done) { loadData().finally(done) }
onMounted(() => loadData())
</script>

<style>
@media print {
  /* Убираем навигацию, header, footer */
  .q-header, .q-footer, .q-drawer, .q-page-sticky,
  [class*="bottom-bar"], nav, footer { display: none !important; }

  /* Контент на всю ширину */
  .q-page { padding: 0 !important; margin: 0 !important; }
  .q-page-container { padding: 0 !important; margin-left: 0 !important; }
  .q-layout { min-height: auto !important; }
  body, html { margin: 0; padding: 0; }

  /* Карточки без теней и рамок */
  .is-card { box-shadow: none !important; border: 1px solid #E0E0E0 !important; break-inside: avoid; }

  /* Графики по центру */
  canvas { max-width: 100% !important; display: block !important; margin: 0 auto !important; }

  /* KPI и мини-карточки — ровная сетка по центру */
  .q-page .row {
    display: flex !important;
    flex-wrap: wrap !important;
    justify-content: center !important;
  }
  .q-page .row > [class*="col-"] {
    flex: 0 0 auto !important;
    text-align: center !important;
  }
  /* KPI блоки — фиксированная ширина для равномерности */
  .q-page .row > .col-4,
  .q-page .row > .col-6 {
    width: 30% !important;
    max-width: 30% !important;
    padding: 4px !important;
  }
  .q-page .row > .col-3 {
    width: 24% !important;
    max-width: 24% !important;
  }
  .q-page .row > .col-12 {
    width: 48% !important;
    max-width: 48% !important;
  }

  /* Карточки с серым фоном как в программе */
  .is-card { box-shadow: none !important; border: 1px solid #E0E0E0 !important; background: #FAFAFA !important; break-inside: avoid; margin-bottom: 8px !important; }
  .q-card-section { padding: 8px !important; }

  /* Шрифты для печати */
  .text-h6 { font-size: 14px !important; }
  .text-subtitle1 { font-size: 12px !important; }
  .text-subtitle2 { font-size: 11px !important; }
  .text-caption { font-size: 9px !important; }

  /* Landscape A4 */
  @page { size: A4 landscape; margin: 8mm; }
}
</style>
