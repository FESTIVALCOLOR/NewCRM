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
          <div class="col-auto">
            <button type="button" class="reset-btn" @click="resetFilters">
              <q-icon name="refresh" size="18px" />
              <span>Сброс</span>
            </button>
          </div>
          <div class="col-auto">
            <button type="button" class="emp-pdf-btn" :disabled="pdfLoading || loading" @click="exportPDF">
              <q-spinner v-if="pdfLoading" size="14px" />
              <span v-else>PDF</span>
            </button>
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
const pdfLoading = ref(false)
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
  if (survR.status === 'fulfilled') surveyStats.value = survR.value.data || null
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
  ]
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
  if (!emp || projectTab.value !== 'supervision') return false
  const pos = emp.position || ''
  const isDan = pos === 'ДАН' || pos === 'Дизайнер авторского надзора'
  const isManager = pos.toLowerCase().includes('менеджер')
  return isDan || isManager
}

async function exportPDF() {
  pdfLoading.value = true
  const popup = window.open('', '_blank', 'width=1200,height=800')
  if (!popup) { pdfLoading.value = false; return }
  try { popup.moveTo(0, 0); popup.resizeTo(screen.width, screen.height) } catch(_e) {}
  popup.document.write('<!DOCTYPE html><html><head><meta charset="utf-8"><title>Загрузка...</title></head><body style="font-family:Arial;padding:40px;color:#555;text-align:center"><p style="font-size:18px">&#8987; Формирование отчёта...</p></body></html>')
  popup.document.close()

  try {
    const params = { year: filters.value.year }
    if (filters.value.quarter) params.quarter = filters.value.quarter
    if (filters.value.month) params.month = filters.value.month

    const [indR, tmplR, supR, survIndR, survTmplR, survSupR] = await Promise.allSettled([
      statisticsApi.getEmployees({ ...params, project_type: 'individual' }),
      statisticsApi.getEmployees({ ...params, project_type: 'template' }),
      statisticsApi.getEmployees({ ...params, project_type: 'supervision' }),
      surveyApi.getStats({ project_type: 'individual' }),
      surveyApi.getStats({ project_type: 'template' }),
      surveyApi.getStats({ project_type: 'supervision' }),
    ])

    const indEmps  = indR.status   === 'fulfilled' ? (indR.value.data   || []) : []
    const tmplEmps = tmplR.status  === 'fulfilled' ? (tmplR.value.data  || []) : []
    const supEmps  = supR.status   === 'fulfilled' ? (supR.value.data   || []) : []
    const survInd  = survIndR.status  === 'fulfilled' ? survIndR.value.data  : null
    const survTmpl = survTmplR.status === 'fulfilled' ? survTmplR.value.data : null
    const survSup  = survSupR.status  === 'fulfilled' ? survSupR.value.data  : null

    const _MONTHS = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек']
    let periodLabel = String(filters.value.year)
    if (filters.value.month) periodLabel += ' · ' + _MONTHS[filters.value.month - 1]
    else if (filters.value.quarter) periodLabel += ' · Q' + filters.value.quarter

    function shortN(n) { if (!n) return '?'; const p = n.split(' '); return p.length >= 2 ? p[0] + ' ' + p[1] : n }
    function kHex(v) { if (v === null || v === undefined) return '#888'; if (v >= 8) return '#27AE60'; if (v >= 6) return '#F39C12'; return '#E74C3C' }

    function filterRole(emps, rt, pt) {
      if (rt === 'sdp') return emps.filter(e => e.position?.includes('СДП'))
      if (rt === 'gap') return emps.filter(e => e.position?.includes('ГАП'))
      if (rt === 'manager') return emps.filter(e => e.position?.toLowerCase().includes('менеджер'))
      if (rt === 'dan') return emps.filter(e => e.position === 'ДАН' || e.position === 'Дизайнер авторского надзора')
      if (rt === 'visualization') return emps.filter(e => e.position === 'Дизайнер')
      if (rt === 'executor') {
        if (pt === 'tmpl') return emps.filter(e => e.position?.includes('Чертёжник'))
        return emps.filter(e => ['Дизайнер','Чертёжник','Замерщик'].some(p => e.position?.includes(p)) && e.position !== 'ДАН' && e.position !== 'Дизайнер авторского надзора')
      }
      return []
    }

    const cd = {}
    const sections = [
      { title: 'Индивидуальные',  key: 'ind',  emps: indEmps,  survey: survInd,  roles: ROLE_TABS.individual },
      { title: 'Шаблонные',       key: 'tmpl', emps: tmplEmps, survey: survTmpl, roles: ROLE_TABS.template },
      { title: 'Авторский надзор', key: 'sup',  emps: supEmps,  survey: survSup,  roles: ROLE_TABS.supervision },
    ]

    let body = ''
    for (const sec of sections) {
      const { title, key, emps, survey, roles } = sec
      if (!emps.length) continue

      const loadData = emps.filter(e => e.total_stages > 0)
        .sort((a, b) => (b.total_stages - b.completed_stages) - (a.total_stages - a.completed_stages))
        .slice(0, 12)
      if (loadData.length) {
        cd[`load_${key}`] = {
          labels: loadData.map(e => shortN(e.full_name)),
          data:   loadData.map(e => e.total_stages - e.completed_stages),
        }
      }

      const totalEmps = emps.length
      const avgKpi = totalEmps ? (emps.reduce((s, e) => s + (e.completion_rate || 0), 0) / totalEmps).toFixed(0) : '—'
      const activeEmps = emps.filter(e => e.total_stages > 0).length
      const kpiRowHtml = [
        { label: 'Сотрудников', value: totalEmps },
        { label: 'Ср. KPI', value: totalEmps ? `${avgKpi}%` : '—' },
        { label: 'С активными этапами', value: activeEmps },
      ].map(k =>
        '<td style="text-align:center;padding:8px 14px;border:1px solid #eee">' +
        `<div style="font-size:20px;font-weight:700;color:#333">${k.value}</div>` +
        `<div style="font-size:9px;color:#888;margin-top:2px">${k.label}</div></td>`,
      ).join('')

      let roleHtml = ''
      for (const role of roles) {
        const rEmps = filterRole(emps, role.code, key).sort((a, b) => b.completion_rate - a.completion_rate)
        if (!rEmps.length) continue

        const kpiKey = `kpi_${key}_${role.code}`
        cd[kpiKey] = {
          labels: rEmps.map(e => shortN(e.full_name || e.name)),
          data:   rEmps.map(e => Math.round(e.completion_rate || 0)),
        }

        const empRows = rEmps.map((e, i) => {
          const kpi = e.completion_rate || 0
          const clr = kHex(kpi / 10)
          const scores = empSurveyScores(e).filter(s => s.value !== null && s.value !== undefined)
            .map(s => `${s.label}: ${s.value.toFixed(1)}/${s.scale}`).join(' · ')
          let visits = ''
          if (key === 'sup') {
            const isDanPos = e.position === 'ДАН' || e.position === 'Дизайнер авторского надзора'
            const isMgrPos = e.position?.toLowerCase().includes('менеджер')
            if (isDanPos || isMgrPos) {
              visits = ` | На объект: ${e.visits_object ?? 0}  К поставщику: ${e.visits_supplier ?? 0}`
              if ((e.visits_overdue ?? 0) > 0) visits += `  Просрочено: ${e.visits_overdue}`
            }
          }
          return `<tr style="background:${i % 2 ? '#fff' : '#fafafa'}">` +
            `<td style="padding:5px 8px">${e.full_name || e.name || ''}</td>` +
            `<td style="padding:5px 8px;color:#888;font-size:10px">${e.position || ''}</td>` +
            `<td style="padding:5px 8px;text-align:right;font-weight:700;color:${clr}">${kpi.toFixed(0)}%</td>` +
            `<td style="padding:5px 8px;text-align:right">${e.completed_stages || 0}/${e.total_stages || 0}</td>` +
            `<td style="padding:5px 8px;font-size:9px;color:#666">${scores}${visits}</td></tr>`
        }).join('')

        const canvH = Math.max(60, rEmps.length * 24)
        roleHtml += `<div class="ct">${role.label} — сравнение KPI</div>
        <canvas id="${kpiKey}" width="700" height="${canvH}" style="break-inside:avoid;margin-bottom:6px"></canvas>
        <table style="width:100%;border-collapse:collapse;font-size:11px;margin-bottom:14px">
          <thead><tr style="background:#f5f5f5">
            <th style="padding:5px 8px;text-align:left">Сотрудник</th>
            <th style="padding:5px 8px;text-align:left">Должность</th>
            <th style="padding:5px 8px;text-align:right">KPI%</th>
            <th style="padding:5px 8px;text-align:right">Этапы</th>
            <th style="padding:5px 8px;text-align:left">Оценки клиентов</th>
          </tr></thead><tbody>${empRows}</tbody></table>`
      }

      let survHtml = ''
      if (survey) {
        const kpis = [
          { label: 'NPS', value: survey.avg_nps, scale: 10 },
          { label: 'CSAT', value: survey.avg_csat, scale: 5 },
          { label: 'Дизайн', value: survey.avg_design, scale: 5 },
          { label: 'Сроки', value: survey.avg_deadline, scale: 5 },
          { label: 'Общение', value: survey.avg_communication, scale: 5 },
          { label: 'Ожидания', value: survey.avg_expectations, scale: 5 },
          { label: 'Надзор', value: survey.avg_supervision, scale: 5 },
        ].filter(k => k.value !== null && k.value !== undefined)
        if (kpis.length) {
          const cells = kpis.map(k =>
            '<td style="text-align:center;padding:6px 10px;border:1px solid #eee">' +
            `<div style="font-size:15px;font-weight:700;color:${kHex(k.value)}">${k.value.toFixed(1)}</div>` +
            `<div style="font-size:9px;color:#888">${k.label} / ${k.scale}</div></td>`,
          ).join('')
          survHtml = `<div class="ct">Опросы клиентов (${survey.completed}/${survey.total} завершено)</div>
          <table style="border-collapse:collapse;margin-bottom:14px"><tr>${cells}</tr></table>`
        }
      }

      const loadCanvH = Math.max(60, loadData.length * 24)
      body += `<h2 style="margin:24px 0 8px;font-size:15px;color:#333;border-bottom:2px solid #eee;padding-bottom:4px">${title}</h2>
      <table style="border-collapse:collapse;margin-bottom:10px"><tr>${kpiRowHtml}</tr></table>
      ${loadData.length ? `<div class="ct">Нагрузка исполнителей (активных стадий)</div>
      <canvas id="load_${key}" width="700" height="${loadCanvH}" style="break-inside:avoid;margin-bottom:12px"></canvas>` : ''}
      ${roleHtml}${survHtml}`
    }

    let chartCalls = ''
    for (const sec of sections) {
      if (cd[`load_${sec.key}`]) {
        chartCalls += `try{hBar('load_${sec.key}',cd.load_${sec.key}.labels,cd.load_${sec.key}.data,'Стадий','#ffd93c');}catch(e){}\n`
      }
      for (const role of sec.roles) {
        const k = `kpi_${sec.key}_${role.code}`
        if (cd[k]) {
          chartCalls += `try{hBar('${k}',cd.${k.replace(/-/g,'_')}.labels,cd.${k.replace(/-/g,'_')}.data,'KPI%','#27AE60');}catch(e){}\n`
        }
      }
    }
    // cd keys don't have dashes, use bracket access
    chartCalls = ''
    for (const sec of sections) {
      if (cd[`load_${sec.key}`]) {
        chartCalls += `try{hBar('load_${sec.key}',cd['load_${sec.key}'].labels,cd['load_${sec.key}'].data,'Стадий','#ffd93c');}catch(e){}\n`
      }
      for (const role of sec.roles) {
        const k = `kpi_${sec.key}_${role.code}`
        if (cd[k]) {
          chartCalls += `try{hBar('${k}',cd['${k}'].labels,cd['${k}'].data,'KPI%','#27AE60');}catch(e){}\n`
        }
      }
    }

    const now = new Date().toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
    const cdJson = JSON.stringify(cd)

    const html = `<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
    <title>Отчёты по сотрудникам</title>
    <style>
      body { font-family: Arial, sans-serif; padding: 16px; color: #333; font-size: 12px; }
      h1 { font-size: 18px; margin: 0 0 3px; }
      .sub { color: #888; font-size: 11px; margin-bottom: 14px; }
      .ct { font-size: 11px; color: #555; font-weight: bold; margin: 10px 0 4px; }
      canvas { display: block; max-width: 100%; break-inside: avoid; }
      @page { size: A4 portrait; margin: 10mm; }
      @media print { body { padding: 0; } }
    </style></head><body>
    <h1>Отчёты по сотрудникам</h1>
    <div class="sub">${periodLabel} &nbsp;·&nbsp; Сформирован: ${now}</div>
    ${body}
    <` + 'script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"><' + `/script>
    <` + `script>
    var __cd = ${cdJson};
    var ROPTS = { animation: false, responsive: false, maintainAspectRatio: false };
    function mkScales() { return { x: { beginAtZero: true, ticks: { font: { size: 8 } } }, y: { ticks: { font: { size: 8 } } } }; }
    function hBar(id, labels, data, label, color) {
      var el = document.getElementById(id); if (!el) return;
      new Chart(el, { type: 'bar', data: { labels: labels, datasets: [{ label: label, data: data, backgroundColor: color || '#3498DB' }] },
        options: Object.assign({}, ROPTS, { indexAxis: 'y', plugins: { legend: { display: false } }, scales: mkScales() }) });
    }
    window.addEventListener('load', function() {
      var cd = __cd;
      ${chartCalls}
      setTimeout(function() { try { window.focus(); window.print(); } catch(e2) {} }, 900);
    });
    <` + `/script>
    </body></html>`

    popup.document.open()
    popup.document.write(html)
    popup.document.close()
  } catch (err) {
    try { popup.document.body.innerHTML = '<p style="padding:20px;color:#c00">Ошибка: ' + (err.message || err) + '</p>' } catch(_e2) {}
  }
  pdfLoading.value = false
}

function resetFilters() {
  filters.value = { year: currentYear, quarter: null, month: null }
  loadData()
}

watch([projectTab, roleTab], () => loadData())
function onRefresh(done) { loadData().finally(done) }
onMounted(() => loadData())
</script>

<style scoped>
.reset-btn {
  height: 40px;
  padding: 0 12px;
  background: #ffd93c;
  color: #333;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  font-family: inherit;
  outline: none;
}

.reset-btn:hover {
  background: #f0c800;
}

.emp-pdf-btn {
  height: 40px;
  padding: 0 14px;
  border: 1px solid #2196f3;
  border-radius: 4px;
  background: white;
  color: #2196f3;
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  outline: none;
  white-space: nowrap;
}

.emp-pdf-btn:hover { background: #e3f2fd; }
.emp-pdf-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
