<template>
  <q-page padding>
    <!-- Фильтры -->
    <q-card class="is-card q-mb-md">
      <q-card-section class="q-pa-sm">
        <div class="row q-col-gutter-sm items-center">
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

    <!-- Подвкладки типов проектов -->
    <q-tabs v-model="projectTab" dense active-color="dark" indicator-color="accent" no-caps class="q-mb-md text-grey-7" align="left">
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
              <div class="text-h6 text-weight-bold">{{ kpi.value }}</div>
              <div class="text-caption text-grey-7" style="font-size: 10px">{{ kpi.label }}</div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Нагрузка исполнителей -->
      <q-card class="is-card q-mb-md" v-if="executorLoad.length > 0">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Нагрузка исполнителей</div>
          <bar-chart
            :labels="executorLoad.map(e => e.name.split(' ')[0])"
            :datasets="[{ label: 'Активных стадий', data: executorLoad.map(e => e.active_stages), color: '#ffd93c' }]"
          />
        </q-card-section>
      </q-card>

      <!-- Список сотрудников с KPI -->
      <q-card class="is-card q-mb-md" v-if="employeeStats.length > 0">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Статистика сотрудников</div>
        </q-card-section>
        <q-list separator>
          <q-item v-for="emp in employeeStats" :key="emp.id">
            <q-item-section avatar>
              <q-avatar size="36px" color="grey-3" text-color="grey-8">
                {{ emp.full_name ? emp.full_name[0] : '?' }}
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-medium">{{ emp.full_name }}</q-item-label>
              <q-item-label caption>{{ emp.position }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="text-right">
                <div class="text-weight-bold">{{ emp.completion_rate?.toFixed(0) || '—' }}%</div>
                <div class="text-caption text-grey-5">{{ emp.completed_stages }}/{{ emp.total_stages }}</div>
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <div v-if="!dashboard && !loading" class="text-center q-pa-xl text-grey-5">
        <q-icon name="analytics" size="48px" class="q-mb-sm" />
        <div>Нет данных за выбранный период</div>
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
const dashboard = ref(null)
const employeeStats = ref([])
const executorLoad = ref([])
const loading = ref(false)

const years = Array.from({ length: 7 }, (_, i) => currentYear - i)
const quarters = [{ label: 'Все', value: null }, { label: 'Q1', value: 1 }, { label: 'Q2', value: 2 }, { label: 'Q3', value: 3 }, { label: 'Q4', value: 4 }]
const monthOpts = [{ label: 'Все', value: null }, ...Array.from({ length: 12 }, (_, i) => ({ label: new Date(2000, i).toLocaleDateString('ru-RU', { month: 'long' }), value: i + 1 }))]

const dashboardKpi = computed(() => {
  const d = dashboard.value || {}
  return [
    { label: 'Сотрудников', value: d.active_employees ?? employeeStats.value.length ?? '—' },
    { label: 'Ср. выполнение', value: d.avg_completion ? `${d.avg_completion.toFixed(0)}%` : '—' },
    { label: 'Активных', value: d.active_crm_cards ?? '—' }
  ]
})

async function loadData() {
  loading.value = true
  const params = { year: filters.value.year }
  if (filters.value.quarter) params.quarter = filters.value.quarter
  if (filters.value.month) params.month = filters.value.month

  const [dashR, empR, loadR] = await Promise.allSettled([
    statisticsApi.getDashboard(params),
    statisticsApi.getProjects({ ...params, project_type: projectTab.value === 'template' ? 'Шаблонный' : projectTab.value === 'supervision' ? 'Авторский надзор' : 'Индивидуальный' }),
    statisticsApi.getProjects({ ...params }).then(r => r) // executor load через statistics
  ])

  if (dashR.status === 'fulfilled') dashboard.value = dashR.value.data
  if (empR.status === 'fulfilled') {
    const data = empR.value.data
    // Если это массив — это статистика сотрудников
    if (Array.isArray(data)) {
      employeeStats.value = data
    }
  }

  // Загрузка нагрузки исполнителей
  try {
    const { data } = await statisticsApi.getProjects({ year: filters.value.year })
    if (data?.by_stages) {
      executorLoad.value = Object.entries(data.by_stages).map(([name, count]) => ({
        name, active_stages: count
      })).sort((a, b) => b.active_stages - a.active_stages).slice(0, 10)
    }
  } catch { /* ignore */ }

  loading.value = false
}

watch(projectTab, () => loadData())
function onRefresh(done) { loadData().finally(done) }
onMounted(() => loadData())
</script>
