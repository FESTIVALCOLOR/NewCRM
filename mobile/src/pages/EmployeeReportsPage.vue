<template>
  <q-page padding>
    <!-- Фильтры -->
    <q-card class="is-card q-mb-md">
      <q-card-section class="q-pa-sm">
        <div class="row q-col-gutter-xs items-center">
          <div class="col"><q-select v-model="filters.year" :options="years" label="Год" outlined dense @update:model-value="loadData" /></div>
          <div class="col"><q-select v-model="filters.quarter" :options="quarters" label="Квартал" outlined dense emit-value map-options @update:model-value="loadData" /></div>
          <div class="col"><q-select v-model="filters.month" :options="monthOpts" label="Месяц" outlined dense emit-value map-options @update:model-value="loadData" /></div>
          <div class="col-auto"><q-btn unelevated icon="refresh" label="Сброс" no-caps style="background: #ffd93c; color: #333; height: 40px; border-radius: 4px" @click="resetFilters" /></div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Тип проекта -->
    <q-tabs v-model="projectTab" dense active-color="dark" indicator-color="accent" no-caps class="q-mb-md" style="color: #666" align="left">
      <q-tab name="individual" label="Индивидуальные" />
      <q-tab name="template" label="Шаблонные" />
      <q-tab name="supervision" label="Авт. надзор" />
    </q-tabs>

    <q-pull-to-refresh @refresh="onRefresh">
      <!-- KPI -->
      <div class="row q-col-gutter-xs q-mb-md" v-if="dashboard">
        <div class="col-4" v-for="kpi in dashboardKpi" :key="kpi.label">
          <q-card class="is-card">
            <q-card-section class="q-pa-sm text-center">
              <div class="text-h6 text-weight-bold" style="color: #333">{{ kpi.value }}</div>
              <div class="text-caption" style="color: #888; font-size: 10px">{{ kpi.label }}</div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Нагрузка исполнителей (bar chart) -->
      <q-card class="is-card q-mb-md" v-if="executorLoad.length > 0">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">Нагрузка исполнителей</div>
          <bar-chart :labels="executorLoad.map(e => e.name.split(' ')[0])" :datasets="[{ label: 'Стадий', data: executorLoad.map(e => e.active_stages), color: '#ffd93c' }]" />
        </q-card-section>
      </q-card>

      <!-- Роли (вкладки) -->
      <q-tabs v-model="roleTab" dense active-color="dark" indicator-color="accent" no-caps class="q-mb-md" style="color: #666" align="left">
        <q-tab v-for="r in roleTabs" :key="r.code" :name="r.code" :label="r.label" />
      </q-tabs>

      <!-- Список сотрудников по роли -->
      <q-card class="is-card q-mb-md" v-if="roleEmployees.length > 0">
        <q-list separator>
          <q-item v-for="emp in roleEmployees" :key="emp.id || emp.name" clickable v-ripple>
            <q-item-section avatar>
              <q-avatar size="36px" color="grey-3" text-color="grey-8">{{ emp.full_name?.[0] || emp.name?.[0] || '?' }}</q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-medium" style="color: #333">{{ emp.full_name || emp.name }}</q-item-label>
              <q-item-label caption style="color: #888">{{ emp.position || '' }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="text-right">
                <div class="text-weight-bold" style="color: #333">{{ emp.completion_rate?.toFixed(0) || emp.kpi || '—' }}%</div>
                <div class="text-caption" style="color: #888">{{ emp.completed_stages || emp.completed || 0 }}/{{ emp.total_stages || emp.total || 0 }}</div>
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Сравнительный график KPI -->
      <q-card class="is-card q-mb-md" v-if="roleEmployees.length > 0">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">Сравнение KPI</div>
          <bar-chart
            :labels="roleEmployees.map(e => (e.full_name || e.name || '').split(' ')[0])"
            :datasets="[{ label: 'KPI %', data: roleEmployees.map(e => e.completion_rate || e.kpi || 0), color: '#27AE60' }]"
            horizontal
          />
        </q-card-section>
      </q-card>

      <div v-if="!dashboard && !loading" class="text-center q-pa-xl" style="color: #999">
        <q-icon name="analytics" size="48px" class="q-mb-sm" />
        <div>Нет данных</div>
      </div>
    </q-pull-to-refresh>
  </q-page>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { statisticsApi } from 'src/services/api'
import BarChart from 'src/components/charts/BarChart.vue'

const currentYear = new Date().getFullYear()
const filters = ref({ year: currentYear, quarter: null, month: null })
const projectTab = ref('individual')
const roleTab = ref('executor')
const dashboard = ref(null)
const executorLoad = ref([])
const roleEmployees = ref([])
const loading = ref(false)

const years = Array.from({ length: 7 }, (_, i) => currentYear - i)
const quarters = [{ label: 'Все', value: null }, { label: 'Q1', value: 1 }, { label: 'Q2', value: 2 }, { label: 'Q3', value: 3 }, { label: 'Q4', value: 4 }]
const monthOpts = [{ label: 'Все', value: null }, ...Array.from({ length: 12 }, (_, i) => ({ label: new Date(2000, i).toLocaleDateString('ru-RU', { month: 'short' }), value: i + 1 }))]

const ROLE_TABS = {
  individual: [{ code: 'sdp', label: 'СДП' }, { code: 'gap', label: 'ГАП' }, { code: 'manager', label: 'Менеджер' }, { code: 'executor', label: 'Исполнитель' }],
  template: [{ code: 'gap', label: 'ГАП' }, { code: 'manager', label: 'Менеджер' }, { code: 'executor', label: 'Исполнитель' }],
  supervision: [{ code: 'supervisor', label: 'Надзиратель' }, { code: 'gap', label: 'ГАП' }]
}

const roleTabs = computed(() => ROLE_TABS[projectTab.value] || ROLE_TABS.individual)

const dashboardKpi = computed(() => {
  const d = dashboard.value || {}
  return [
    { label: 'Сотрудников', value: d.active_employees ?? roleEmployees.value.length ?? '—' },
    { label: 'Выполнение', value: d.avg_completion ? `${d.avg_completion.toFixed(0)}%` : '—' },
    { label: 'Проектов', value: d.active_crm_cards ?? '—' }
  ]
})

async function loadData() {
  loading.value = true
  const params = { year: filters.value.year }
  if (filters.value.quarter) params.quarter = filters.value.quarter
  if (filters.value.month) params.month = filters.value.month

  const pt = projectTab.value === 'template' ? 'Шаблонный' : projectTab.value === 'supervision' ? 'Авторский надзор' : 'Индивидуальный'

  const [dashR, empR, projR] = await Promise.allSettled([
    statisticsApi.getDashboard(params),
    statisticsApi.getEmployees(params),
    statisticsApi.getProjects({ ...params, project_type: pt })
  ])

  if (dashR.status === 'fulfilled') dashboard.value = dashR.value.data

  // Сотрудники — фильтрация по roleTab
  if (empR.status === 'fulfilled' && Array.isArray(empR.value.data)) {
    const allEmps = empR.value.data
    // Фильтруем по роли
    const rt = roleTab.value
    let filtered = allEmps
    if (rt === 'sdp') filtered = allEmps.filter(e => e.position?.includes('СДП'))
    else if (rt === 'gap') filtered = allEmps.filter(e => e.position?.includes('ГАП') || e.position?.includes('руководитель'))
    else if (rt === 'manager') filtered = allEmps.filter(e => e.position?.toLowerCase().includes('менеджер'))
    else if (rt === 'executor') filtered = allEmps.filter(e => e.position?.includes('Дизайнер') || e.position?.includes('Чертёжник') || e.position?.includes('дизайнер') || e.position?.includes('чертёжник'))
    else if (rt === 'supervisor') filtered = allEmps.filter(e => e.position?.includes('ДАН') || e.position?.includes('надзор'))

    roleEmployees.value = filtered.sort((a, b) => b.completion_rate - a.completion_rate)

    // Нагрузка — все сотрудники с назначенными стадиями
    executorLoad.value = allEmps.filter(e => e.total_stages > 0)
      .sort((a, b) => (b.total_stages - b.completed_stages) - (a.total_stages - a.completed_stages))
      .slice(0, 10)
      .map(e => ({ name: e.full_name, active_stages: e.total_stages - e.completed_stages }))
  }

  if (projR.status === 'fulfilled') {
    const data = projR.value.data
    if (data?.by_stages && executorLoad.value.length === 0) {
      executorLoad.value = Object.entries(data.by_stages).map(([name, count]) => ({ name, active_stages: count })).sort((a, b) => b.active_stages - a.active_stages).slice(0, 10)
    }
  }

  loading.value = false
}

function resetFilters() {
  filters.value = { year: currentYear, quarter: null, month: null }
  loadData()
}

watch([projectTab, roleTab], () => loadData())
function onRefresh(done) { loadData().finally(done) }
onMounted(() => loadData())
</script>
