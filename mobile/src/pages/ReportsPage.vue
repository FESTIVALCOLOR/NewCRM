<template>
  <q-page padding>
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
      <!-- KPI карточки -->
      <div class="row q-col-gutter-sm q-mb-md">
        <div class="col-6 col-md-4" v-for="kpi in kpiCards" :key="kpi.label">
          <q-card class="is-card">
            <q-card-section class="q-pa-md">
              <div class="row items-center justify-between q-mb-xs">
                <q-icon :name="kpi.icon" size="20px" :style="{ color: kpi.borderColor }" />
                <div class="text-h6 text-weight-bold">{{ kpi.value }}</div>
              </div>
              <div class="text-caption text-grey-7">{{ kpi.label }}</div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Секция: Клиенты -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle1 text-weight-bold q-mb-sm">Клиенты</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-4" v-for="m in clientMini" :key="m.label">
              <div class="text-center">
                <div class="text-h6 text-weight-bold">{{ m.value }}</div>
                <div class="text-caption text-grey-7">{{ m.label }}</div>
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Секция: Договоры -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle1 text-weight-bold q-mb-sm">Договоры</div>
          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col-4" v-for="m in contractMini" :key="m.label">
              <div class="text-center">
                <div class="text-h6 text-weight-bold">{{ m.value }}</div>
                <div class="text-caption text-grey-7">{{ m.label }}</div>
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Секция: Воронка CRM -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle1 text-weight-bold q-mb-sm">Воронка CRM</div>
          <div v-if="funnel">
            <div v-for="(count, stage) in funnel.funnel" :key="stage" class="q-mb-sm">
              <div class="row items-center justify-between q-mb-xs">
                <span class="text-caption">{{ stage }}</span>
                <span class="text-weight-bold">{{ count }}</span>
              </div>
              <q-linear-progress
                :value="funnel.total ? count / funnel.total : 0"
                color="accent"
                track-color="grey-3"
                style="height: 8px; border-radius: 4px"
              />
            </div>
          </div>
          <div v-else class="text-center text-grey-5 q-py-md">Нет данных</div>
        </q-card-section>
      </q-card>

      <!-- Секция: CRM аналитика -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle1 text-weight-bold q-mb-sm">Проекты</div>
          <q-tabs v-model="projectTab" dense active-color="dark" indicator-color="accent" no-caps align="left">
            <q-tab name="individual" label="Индивидуальные" />
            <q-tab name="template" label="Шаблонные" />
          </q-tabs>
          <div v-if="projectStats" class="q-mt-md">
            <div class="row q-col-gutter-sm">
              <div class="col-6" v-for="s in projectStatCards" :key="s.label">
                <div class="text-center q-pa-sm" style="border: 1px solid #E0E0E0; border-radius: 8px">
                  <div class="text-h6 text-weight-bold">{{ s.value }}</div>
                  <div class="text-caption text-grey-7">{{ s.label }}</div>
                </div>
              </div>
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

const currentYear = new Date().getFullYear()
const filters = ref({ year: currentYear, quarter: null, month: null })
const summary = ref(null)
const funnel = ref(null)
const projectStats = ref(null)
const projectTab = ref('individual')
const loading = ref(false)

const years = Array.from({ length: 7 }, (_, i) => currentYear - i)
const quarters = [{ label: 'Все', value: null }, { label: 'Q1', value: 1 }, { label: 'Q2', value: 2 }, { label: 'Q3', value: 3 }, { label: 'Q4', value: 4 }]
const monthOpts = [{ label: 'Все', value: null }, ...Array.from({ length: 12 }, (_, i) => ({ label: new Date(2000, i).toLocaleDateString('ru-RU', { month: 'long' }), value: i + 1 }))]

const kpiCards = computed(() => {
  const s = summary.value || {}
  return [
    { label: 'Всего клиентов', value: s.total_clients ?? '—', icon: 'people', borderColor: '#ffd93c' },
    { label: 'Новых клиентов', value: s.new_clients ?? '—', icon: 'person_add', borderColor: '#27AE60' },
    { label: 'Повторных', value: s.returning_clients ?? '—', icon: 'replay', borderColor: '#85C1E9' },
    { label: 'Всего договоров', value: s.total_contracts ?? '—', icon: 'description', borderColor: '#F39C12' },
    { label: 'Общая стоимость', value: s.total_amount ? formatMoney(s.total_amount) : '—', icon: 'payments', borderColor: '#E74C3C' },
    { label: 'Средний чек', value: s.avg_amount ? formatMoney(s.avg_amount) : '—', icon: 'trending_up', borderColor: '#9B59B6' }
  ]
})

const clientMini = computed(() => {
  const s = summary.value || {}
  return [
    { label: 'Всего', value: s.total_clients ?? '—' },
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

const projectStatCards = computed(() => {
  const p = projectStats.value || {}
  return [
    { label: 'Всего', value: p.total_orders ?? '—' },
    { label: 'Активных', value: p.active ?? '—' },
    { label: 'Завершённых', value: p.completed ?? '—' },
    { label: 'Просроченных', value: p.overdue ?? '—' }
  ]
})

function formatMoney(v) {
  if (!v) return '0 ₽'
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(v)
}

async function loadData() {
  loading.value = true
  const params = { year: filters.value.year }
  if (filters.value.quarter) params.quarter = filters.value.quarter
  if (filters.value.month) params.month = filters.value.month

  const [sumRes, funnelRes, projRes] = await Promise.allSettled([
    reportsApi.getSummary(params),
    reportsApi.getFunnel(params),
    reportsApi.getCrmAnalytics({ ...params, project_type: projectTab.value === 'template' ? 'Шаблонный' : 'Индивидуальный' })
  ])

  if (sumRes.status === 'fulfilled') summary.value = sumRes.value.data
  if (funnelRes.status === 'fulfilled') funnel.value = funnelRes.value.data
  if (projRes.status === 'fulfilled') projectStats.value = projRes.value.data
  loading.value = false
}

watch(projectTab, () => loadData())

function onRefresh(done) { loadData().finally(done) }

onMounted(() => loadData())
</script>
