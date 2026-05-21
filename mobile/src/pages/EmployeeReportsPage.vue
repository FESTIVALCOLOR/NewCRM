<template>
  <q-page padding>
    <!-- Фильтры -->
    <q-card class="is-card q-mb-md">
      <q-card-section class="q-pa-sm">
        <div class="row q-col-gutter-xs items-center">
          <div class="col">
            <q-select
              v-model="filters.year"
              :options="years"
              label="Год"
              outlined
              dense
              @update:model-value="loadData"
            />
          </div>
          <div class="col">
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
          <div class="col">
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
          <div class="col-auto" style="display: flex; align-items: stretch">
            <q-btn
              unelevated
              icon="refresh"
              label="Сброс"
              no-caps
              style="background: #ffd93c; color: #333; border-radius: 4px; min-height: 100%"
              @click="resetFilters"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Тип проекта -->
    <q-tabs
      v-model="projectTab"
      dense
      active-color="dark"
      indicator-color="accent"
      no-caps
      class="q-mb-md"
      style="color: #666"
      align="left"
    >
      <q-tab name="individual" label="Индивидуальные" />
      <q-tab name="template" label="Шаблонные" />
      <q-tab name="supervision" label="Авт. надзор" />
    </q-tabs>

    <q-pull-to-refresh @refresh="onRefresh">
      <!-- KPI -->
      <div v-if="dashboard" class="row q-col-gutter-xs q-mb-md">
        <div v-for="kpi in dashboardKpi" :key="kpi.label" class="col-4">
          <q-card class="is-card">
            <q-card-section class="q-pa-sm text-center">
              <div class="text-h6 text-weight-bold" style="color: #333">
                {{ kpi.value }}
              </div>
              <div class="text-caption" style="color: #888; font-size: 10px">
                {{ kpi.label }}
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Нагрузка исполнителей (bar chart) -->
      <q-card v-if="executorLoad.length > 0" class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">
            Нагрузка исполнителей
          </div>
          <bar-chart :labels="executorLoad.map(e => e.name.split(' ').slice(0, 2).join(' '))" :datasets="[{ label: 'Стадий', data: executorLoad.map(e => e.active_stages), color: '#ffd93c' }]" />
        </q-card-section>
      </q-card>

      <!-- Роли (вкладки) -->
      <q-tabs
        v-model="roleTab"
        dense
        active-color="dark"
        indicator-color="accent"
        no-caps
        class="q-mb-md"
        style="color: #666"
        align="left"
      >
        <q-tab v-for="r in roleTabs" :key="r.code" :name="r.code" :label="r.label" />
      </q-tabs>

      <!-- Список сотрудников по роли -->
      <q-card v-if="roleEmployees.length > 0" class="is-card q-mb-md">
        <q-list separator>
          <q-item
            v-for="emp in roleEmployees"
            :key="emp.id || emp.name"
            v-ripple
            clickable
            @click="selectedEmp = emp"
          >
            <q-item-section avatar>
              <q-avatar size="36px" color="grey-3" text-color="grey-8">
                {{ emp.full_name?.[0] || emp.name?.[0] || '?' }}
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-medium" style="color: #333">
                {{ emp.full_name || emp.name }}
              </q-item-label>
              <q-item-label caption style="color: #888">
                {{ emp.position || '' }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="text-right">
                <div class="text-weight-bold" style="color: #333">
                  {{ emp.completion_rate?.toFixed(0) || emp.kpi || '—' }}%
                </div>
                <div class="text-caption" style="color: #888">
                  {{ emp.completed_stages || emp.completed || 0 }}/{{ emp.total_stages || emp.total || 0 }}
                </div>
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Сравнительный график KPI -->
      <q-card v-if="roleEmployees.length > 0" class="is-card q-mb-md">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">
            Сравнение KPI
          </div>
          <bar-chart
            :labels="roleEmployees.map(e => (e.full_name || e.name || '').split(' ').slice(0, 2).join(' '))"
            :datasets="[{ label: 'KPI %', data: roleEmployees.map(e => e.completion_rate || e.kpi || 0), color: '#27AE60' }]"
            horizontal
          />
        </q-card-section>
      </q-card>

      <!-- Опросы клиентов — KPI качества -->
      <q-card v-if="surveyStats" class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">
            Качество проектов (опросы клиентов)
          </div>
          <div class="text-caption" style="color: #888">
            {{ surveyStats.completed }}/{{ surveyStats.total }} завершённых опросов
          </div>
        </q-card-section>
        <q-card-section>
          <div class="row q-col-gutter-sm">
            <div v-for="kpi in surveyKpis" :key="kpi.label" class="col-6 col-sm-4">
              <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px">
                <div class="text-caption" style="color: #888; font-size: 10px">
                  {{ kpi.label }}
                </div>
                <div class="text-weight-bold q-mt-xs" :style="{ color: kpiColor(kpi.value), fontSize: '18px' }">
                  {{ kpi.value != null ? kpi.value.toFixed(1) : '—' }}
                </div>
                <div class="text-caption" style="color: #ccc; font-size: 9px">
                  из {{ kpi.scale }}
                </div>
              </q-card>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <div v-if="!dashboard && !loading" class="text-center q-pa-xl" style="color: #999">
        <q-icon name="analytics" size="48px" class="q-mb-sm" />
        <div>Нет данных</div>
      </div>
    </q-pull-to-refresh>

    <!-- Диалог деталей сотрудника -->
    <q-dialog v-model="empDialog" position="bottom">
      <q-card v-if="selectedEmp" style="width: 100%; max-width: 600px; border-radius: 16px 16px 0 0">
        <q-card-section class="q-pb-none">
          <div class="row items-center q-mb-sm">
            <q-avatar size="48px" color="grey-3" text-color="grey-8" class="q-mr-md">
              {{ selectedEmp.full_name?.[0] || '?' }}
            </q-avatar>
            <div>
              <div class="text-subtitle1 text-weight-bold" style="color: #333">
                {{ selectedEmp.full_name || selectedEmp.name }}
              </div>
              <div class="text-caption" style="color: #888">
                {{ selectedEmp.position }}
              </div>
            </div>
            <q-space />
            <q-btn flat round icon="close" @click="selectedEmp = null" />
          </div>
        </q-card-section>
        <q-card-section>
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px">
                <div class="text-caption" style="color: #888; font-size: 10px">
                  KPI выполнения
                </div>
                <div class="text-h6 text-weight-bold q-mt-xs" :style="{ color: kpiColor((selectedEmp.completion_rate || 0) / 10) }">
                  {{ selectedEmp.completion_rate?.toFixed(0) || '—' }}%
                </div>
              </q-card>
            </div>
            <div class="col-6">
              <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px">
                <div class="text-caption" style="color: #888; font-size: 10px">
                  Этапы
                </div>
                <div class="text-h6 text-weight-bold q-mt-xs" style="color: #333">
                  {{ selectedEmp.completed_stages || 0 }}/{{ selectedEmp.total_stages || 0 }}
                </div>
              </q-card>
            </div>
          </div>
          <q-linear-progress
            v-if="selectedEmp.total_stages > 0"
            :value="(selectedEmp.completed_stages || 0) / selectedEmp.total_stages"
            color="positive"
            class="q-mt-sm"
            rounded
            style="height: 8px"
          />
          <div v-if="empSurveyScores(selectedEmp).length" class="q-mt-sm">
            <div class="row q-gutter-xs">
              <div v-for="sc in empSurveyScores(selectedEmp)" :key="sc.label" class="col">
                <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px; min-width: 60px">
                  <div class="text-caption" style="color: #888; font-size: 10px">
                    {{ sc.label }}
                  </div>
                  <div class="text-weight-bold q-mt-xs" :style="{ color: sc.value != null ? kpiColor(sc.value) : '#ccc', fontSize: '18px' }">
                    {{ sc.value != null ? sc.value.toFixed(1) : '—' }}
                  </div>
                  <div class="text-caption" style="color: #ccc; font-size: 9px">
                    из {{ sc.scale }}
                  </div>
                </q-card>
              </div>
            </div>
          </div>
          <!-- Выезды на объекты (ДАН и Менеджер) -->
          <div v-if="showVisitStats(selectedEmp)" class="q-mt-md">
            <div class="text-caption q-mb-xs" style="color: #666; font-weight: 600; font-size: 11px">
              Выезды на объекты
            </div>
            <div class="row q-gutter-xs">
              <div class="col">
                <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px">
                  <div class="text-caption" style="color: #888; font-size: 10px">
                    На объект
                  </div>
                  <div class="text-weight-bold q-mt-xs" style="font-size: 18px; color: #333">
                    {{ selectedEmp.visits_object ?? 0 }}
                  </div>
                </q-card>
              </div>
              <div class="col">
                <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px">
                  <div class="text-caption" style="color: #888; font-size: 10px">
                    К поставщику
                  </div>
                  <div class="text-weight-bold q-mt-xs" style="font-size: 18px; color: #333">
                    {{ selectedEmp.visits_supplier ?? 0 }}
                  </div>
                </q-card>
              </div>
              <div class="col">
                <q-card flat bordered class="q-pa-sm text-center" style="border-radius: 8px">
                  <div class="text-caption" style="color: #888; font-size: 10px">
                    Просрочено
                  </div>
                  <div
                    class="text-weight-bold q-mt-xs"
                    :style="{ fontSize: '18px', color: (selectedEmp.visits_overdue ?? 0) > 0 ? '#E74C3C' : '#27AE60' }"
                  >
                    {{ selectedEmp.visits_overdue ?? 0 }}
                  </div>
                </q-card>
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { statisticsApi, surveyApi } from 'src/services/api'
import BarChart from 'src/components/charts/BarChart.vue'

const currentYear = new Date().getFullYear()
const filters = ref({ year: currentYear, quarter: null, month: null })
const projectTab = ref('individual')
const roleTab = ref('executor')
const dashboard = ref(null)
const executorLoad = ref([])
const roleEmployees = ref([])
const loading = ref(false)
const surveyStats = ref(null)
const selectedEmp = ref(null)
const empDialog = computed({
  get: () => !!selectedEmp.value,
  set: (v) => { if (!v) selectedEmp.value = null },
})

const years = Array.from({ length: 7 }, (_, i) => currentYear - i)
const quarters = [{ label: 'Все', value: null }, { label: 'Q1', value: 1 }, { label: 'Q2', value: 2 }, { label: 'Q3', value: 3 }, { label: 'Q4', value: 4 }]
const monthOpts = [{ label: 'Все', value: null }, ...Array.from({ length: 12 }, (_, i) => ({ label: new Date(2000, i).toLocaleDateString('ru-RU', { month: 'short' }), value: i + 1 }))]

const ROLE_TABS = {
  individual: [{ code: 'sdp', label: 'СДП' }, { code: 'gap', label: 'ГАП' }, { code: 'manager', label: 'Менеджер' }, { code: 'executor', label: 'Исполнитель' }],
  template: [{ code: 'gap', label: 'ГАП' }, { code: 'manager', label: 'Менеджер' }, { code: 'executor', label: 'Чертёжник' }, { code: 'visualization', label: 'Визуализация' }],
  supervision: [{ code: 'dan', label: 'ДАН' }, { code: 'manager', label: 'Менеджер' }],
}

const roleTabs = computed(() => ROLE_TABS[projectTab.value] || ROLE_TABS.individual)

const dashboardKpi = computed(() => {
  const d = dashboard.value || {}
  return [
    { label: 'Сотрудников', value: d.active_employees ?? roleEmployees.value.length ?? '—' },
    { label: 'Выполнение', value: d.avg_completion ? `${d.avg_completion.toFixed(0)}%` : '—' },
    { label: 'Проектов', value: d.active_crm_cards ?? '—' },
  ]
})

async function loadData() {
  loading.value = true
  const params = { year: filters.value.year }
  if (filters.value.quarter) params.quarter = filters.value.quarter
  if (filters.value.month) params.month = filters.value.month

  const pt = projectTab.value === 'template' ? 'Шаблонный' : projectTab.value === 'supervision' ? 'Авторский надзор' : 'Индивидуальный'
  const PT_ENG = { 'Индивидуальный': 'individual', 'Шаблонный': 'template', 'Авторский надзор': 'supervision' }

  const [dashR, empR, projR, survR] = await Promise.allSettled([
    statisticsApi.getDashboard(params),
    statisticsApi.getEmployees({ ...params, project_type: projectTab.value }),
    statisticsApi.getProjects({ ...params, project_type: pt }),
    surveyApi.getStats({ project_type: PT_ENG[pt] || 'individual' }),
  ])

  if (dashR.status === 'fulfilled') dashboard.value = dashR.value.data
  if (survR.status === 'fulfilled') surveyStats.value = survR.value.data?.total > 0 ? survR.value.data : null
  else surveyStats.value = null

  // Сотрудники — фильтрация по roleTab
  if (empR.status === 'fulfilled' && Array.isArray(empR.value.data)) {
    const allEmps = empR.value.data
    // Фильтруем по роли
    const rt = roleTab.value
    let filtered = allEmps
    if (rt === 'sdp') filtered = allEmps.filter(e => e.position?.includes('СДП'))
    else if (rt === 'gap') filtered = allEmps.filter(e => e.position?.includes('ГАП'))
    else if (rt === 'manager') filtered = allEmps.filter(e => e.position?.toLowerCase().includes('менеджер'))
    else if (rt === 'dan') filtered = allEmps.filter(e => e.position === 'ДАН' || e.position === 'Дизайнер авторского надзора')
    else if (rt === 'visualization') filtered = allEmps.filter(e => e.position === 'Дизайнер')
    else if (rt === 'executor') {
      if (projectTab.value === 'template') {
        filtered = allEmps.filter(e => e.position?.includes('Чертёжник'))
      } else {
        filtered = allEmps.filter(e => ['Дизайнер', 'Чертёжник', 'Замерщик'].some(p => e.position?.includes(p)) && e.position !== 'ДАН' && e.position !== 'Дизайнер авторского надзора')
      }
    }

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

const surveyKpis = computed(() => {
  const s = surveyStats.value || {}
  return [
    { label: 'NPS', value: s.avg_nps, scale: 10 },
    { label: 'CSAT', value: s.avg_csat, scale: 5 },
    { label: 'Дизайн', value: s.avg_design, scale: 5 },
    { label: 'Сроки', value: s.avg_deadline, scale: 5 },
    { label: 'Общение', value: s.avg_communication, scale: 5 },
    { label: 'Ожидания', value: s.avg_expectations, scale: 5 },
    { label: 'Надзор', value: s.avg_supervision, scale: 5 },
  ].filter(k => k.value != null)
})

function empSurveyScores(emp) {
  if (!emp) return []
  const pos = emp.position || ''
  const isDan = pos === 'ДАН' || pos === 'Дизайнер авторского надзора'
  const isDesigner = pos === 'Дизайнер'
  const isDraftsman = pos === 'Чертёжник'
  const isSdp = pos === 'СДП'
  const isGap = pos === 'ГАП'
  const isManager = pos.toLowerCase().includes('менеджер')
  const scores = []
  // NPS и CSAT — для всех ролей
  scores.push({ label: 'NPS', value: emp.avg_nps ?? null, scale: 10 })
  scores.push({ label: 'CSAT', value: emp.avg_csat ?? null, scale: 5 })
  // Дизайн: Дизайнер, СДП, ДАН
  if (isDesigner || isSdp || isDan) scores.push({ label: 'Дизайн', value: emp.avg_design ?? null, scale: 5 })
  // Сроки: Менеджер, СДП, ДАН
  if (isManager || isSdp || isDan) scores.push({ label: 'Сроки', value: emp.avg_deadline ?? null, scale: 5 })
  // Общение: только Менеджер
  if (isManager) scores.push({ label: 'Общение', value: emp.avg_communication ?? null, scale: 5 })
  // Ожидания: ГАП, Менеджер, Чертёжник, ДАН
  if (isGap || isManager || isDraftsman || isDan) scores.push({ label: 'Ожидания', value: emp.avg_expectations ?? null, scale: 5 })
  // Надзор: только ДАН
  if (isDan) scores.push({ label: 'Надзор', value: emp.avg_supervision ?? null, scale: 5 })
  return scores
}

function kpiColor(v) {
  if (v == null) return '#888'
  if (v >= 8) return '#27AE60'
  if (v >= 6) return '#F39C12'
  return '#E74C3C'
}

function showVisitStats(emp) {
  if (!emp) return false
  const pos = emp.position || ''
  const isDan = pos === 'ДАН' || pos === 'Дизайнер авторского надзора'
  const isManager = pos.toLowerCase().includes('менеджер')
  return isDan || isManager
}

function resetFilters() {
  filters.value = { year: currentYear, quarter: null, month: null }
  loadData()
}

watch([projectTab, roleTab], () => loadData())
function onRefresh(done) { loadData().finally(done) }
onMounted(() => loadData())
</script>
