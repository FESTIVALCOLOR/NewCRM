<template>
  <q-page padding>
    <!-- Подвкладки по типам (как десктоп) -->
    <q-tabs v-model="paymentTab" dense active-color="dark" indicator-color="accent" no-caps class="q-mb-md" style="color: #666" align="left">
      <q-tab name="all" label="Все выплаты" />
      <q-tab name="individual" label="Индивидуальные" />
      <q-tab name="template" label="Шаблонные" />
      <q-tab name="supervision" label="Надзор" />
      <q-tab name="salary" label="Оклады" />
    </q-tabs>

    <!-- Фильтры (как десктоп: период, адрес, исполнитель, должность, агент, тип выплаты, статус) -->
    <q-card class="is-card q-mb-md">
      <q-card-section class="q-pa-sm">
        <!-- Строка 1: Период -->
        <div class="row q-col-gutter-xs q-mb-xs">
          <div class="col-4">
            <q-select v-model="filters.period" :options="periodOptions" label="Период" outlined dense emit-value map-options @update:model-value="onPeriodChange" />
          </div>
          <div class="col-4" v-if="filters.period !== 'all'">
            <q-select v-model="filters.year" :options="years" label="Год" outlined dense @update:model-value="loadData" />
          </div>
          <div class="col-4" v-if="filters.period === 'month'">
            <q-select v-model="filters.month" :options="monthOpts" label="Месяц" outlined dense emit-value map-options @update:model-value="loadData" />
          </div>
          <div class="col-4" v-if="filters.period === 'quarter'">
            <q-select v-model="filters.quarter" :options="quarterOpts" label="Квартал" outlined dense emit-value map-options @update:model-value="loadData" />
          </div>
        </div>
        <!-- Строка 2: Исполнитель, должность -->
        <div class="row q-col-gutter-xs q-mb-xs">
          <div class="col-6">
            <q-select v-model="filters.employee_id" :options="employeeOpts" label="Исполнитель" outlined dense emit-value map-options clearable @update:model-value="loadData" />
          </div>
          <div class="col-6">
            <q-select v-model="filters.is_paid" :options="paidOptions" label="Статус" outlined dense emit-value map-options @update:model-value="loadData" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Итого -->
    <q-card class="is-card q-mb-md" v-if="!loading">
      <q-card-section class="q-pa-md">
        <div class="row items-center justify-between">
          <div>
            <div class="text-caption" style="color: #888">Итого по фильтру</div>
            <div class="text-caption" style="color: #999">{{ payments.length }} записей</div>
          </div>
          <div class="text-h5 text-weight-bold" style="color: #333">{{ formatMoney(totalAmount) }}</div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Список -->
    <q-pull-to-refresh @refresh="onRefresh">
      <div v-if="loading">
        <q-card class="is-card q-mb-sm" v-for="n in 5" :key="n">
          <q-card-section><q-skeleton type="text" width="60%" /><q-skeleton type="text" width="40%" /></q-card-section>
        </q-card>
      </div>

      <template v-else>
        <q-card v-for="p in payments" :key="p.id || p.salary_id" class="is-card q-mb-sm">
          <q-card-section class="q-pa-md">
            <div class="row items-center justify-between q-mb-xs">
              <div style="flex: 1">
                <div class="text-weight-bold" style="font-size: 13px; color: #333">{{ p.employee_name || 'Без исполнителя' }}</div>
                <div class="text-caption" style="color: #888">{{ p.role || p.position || '' }}</div>
              </div>
              <div class="text-right">
                <div class="text-weight-bold" style="font-size: 14px" :style="{ color: p.is_paid ? '#27AE60' : '#333' }">
                  {{ formatMoney(p.final_amount || p.amount) }}
                </div>
                <q-badge :color="p.is_paid ? 'positive' : 'warning'" :label="p.is_paid ? 'Оплачено' : 'Ожидает'" dense />
              </div>
            </div>
            <div class="text-caption" style="color: #888" v-if="p.address">{{ p.address }}</div>
            <div class="row items-center q-gutter-xs text-caption" style="color: #999">
              <span v-if="p.contract_number">{{ p.contract_number }}</span>
              <span v-if="p.stage_name">| {{ p.stage_name }}</span>
              <span v-if="p.payment_subtype">| {{ p.payment_subtype }}</span>
              <span v-if="p.report_month">| {{ p.report_month }}</span>
              <q-space />
              <q-btn v-if="!p.is_paid && p.id" flat dense size="xs" icon="check_circle" color="positive" @click.stop="markPaid(p)">
                <q-tooltip>Отметить оплачено</q-tooltip>
              </q-btn>
              <q-btn v-if="p.id" flat dense size="xs" icon="delete" color="negative" @click.stop="deletePayment(p)">
                <q-tooltip>Удалить</q-tooltip>
              </q-btn>
            </div>
          </q-card-section>
        </q-card>

        <div v-if="payments.length === 0" class="text-center q-pa-xl" style="color: #999">
          <q-icon name="payments" size="48px" class="q-mb-sm" />
          <div>Нет платежей по фильтру</div>
        </div>
      </template>
    </q-pull-to-refresh>
  </q-page>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { paymentsApi, employeesApi } from 'src/services/api'

const $q = useQuasar()
const payments = ref([])
const loading = ref(false)
const paymentTab = ref('all')
const employeeOpts = ref([])
const currentYear = new Date().getFullYear()

const filters = ref({
  period: 'all',
  year: currentYear,
  month: new Date().getMonth() + 1,
  quarter: Math.ceil((new Date().getMonth() + 1) / 3),
  employee_id: null,
  is_paid: null
})

const periodOptions = [
  { label: 'Все', value: 'all' },
  { label: 'Месяц', value: 'month' },
  { label: 'Квартал', value: 'quarter' },
  { label: 'Год', value: 'year' }
]

const years = Array.from({ length: 10 }, (_, i) => currentYear - i)
const monthOpts = Array.from({ length: 12 }, (_, i) => ({
  label: new Date(2000, i).toLocaleDateString('ru-RU', { month: 'long' }),
  value: i + 1
}))
const quarterOpts = [{ label: 'Q1', value: 1 }, { label: 'Q2', value: 2 }, { label: 'Q3', value: 3 }, { label: 'Q4', value: 4 }]
const paidOptions = [
  { label: 'Все', value: null },
  { label: 'Оплачено', value: true },
  { label: 'Ожидает', value: false }
]

const totalAmount = computed(() =>
  payments.value.reduce((sum, p) => sum + (p.final_amount || p.amount || 0), 0)
)

const paymentTypeMap = {
  all: '',
  individual: 'Индивидуальный',
  template: 'Шаблонный',
  supervision: 'Авторский надзор',
  salary: 'Оклад'
}

function formatMoney(v) {
  if (!v) return '0 ₽'
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(v)
}

function onPeriodChange() { loadData() }

async function loadData() {
  loading.value = true
  try {
    const params = {}
    const pt = paymentTypeMap[paymentTab.value]
    if (pt) params.payment_type = pt

    if (filters.value.period !== 'all') {
      params.year = filters.value.year
      if (filters.value.period === 'month') params.month = filters.value.month
    }
    if (filters.value.employee_id) params.employee_id = filters.value.employee_id
    if (filters.value.is_paid !== null) params.is_paid = filters.value.is_paid

    const { data } = await paymentsApi.getList(params)
    payments.value = data
  } catch { payments.value = [] }
  finally { loading.value = false }
}

async function markPaid(p) {
  try {
    await paymentsApi.markPaid(p.id)
    $q.notify({ type: 'positive', message: 'Оплачено' })
    p.is_paid = true
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function deletePayment(p) {
  $q.dialog({ title: 'Удалить?', message: `${p.employee_name} — ${formatMoney(p.final_amount || p.amount)}`, cancel: true }).onOk(async () => {
    try {
      await paymentsApi.delete(p.id)
      payments.value = payments.value.filter(x => x.id !== p.id)
      $q.notify({ type: 'positive', message: 'Удалено' })
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

watch(paymentTab, () => loadData())
function onRefresh(done) { loadData().finally(done) }

onMounted(async () => {
  loadData()
  try {
    const { data } = await employeesApi.getList()
    employeeOpts.value = data.filter(e => e.status === 'активный').map(e => ({ label: e.full_name, value: e.id }))
  } catch {}
})
</script>
