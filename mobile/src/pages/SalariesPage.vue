<template>
  <q-page padding>
    <!-- Фильтры -->
    <q-card class="is-card q-mb-md">
      <q-card-section class="q-pa-sm">
        <div class="row q-col-gutter-sm">
          <div class="col-6">
            <q-select v-model="filters.payment_type" :options="paymentTypes" label="Тип" outlined dense emit-value map-options @update:model-value="loadData" />
          </div>
          <div class="col-6">
            <q-select v-model="filters.year" :options="years" label="Год" outlined dense @update:model-value="loadData" />
          </div>
          <div class="col-6">
            <q-select v-model="filters.month" :options="months" label="Месяц" outlined dense emit-value map-options @update:model-value="loadData" />
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
          <div class="text-caption text-grey-7">Итого по фильтру</div>
          <div class="text-h6 text-weight-bold">{{ formatMoney(totalAmount) }}</div>
        </div>
        <div class="text-caption text-grey-5">{{ payments.length }} записей</div>
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
        <q-card
          v-for="p in payments"
          :key="p.id || p.salary_id"
          class="is-card q-mb-sm"
        >
          <q-card-section class="q-pa-md">
            <div class="row items-center justify-between q-mb-xs">
              <div class="text-subtitle2 text-weight-bold">{{ p.employee_name || 'Без исполнителя' }}</div>
              <div class="text-weight-bold" :class="p.is_paid ? 'text-positive' : 'text-warning'">
                {{ formatMoney(p.final_amount || p.amount) }}
              </div>
            </div>
            <div class="text-caption text-grey-7 q-mb-xs">
              {{ p.address || p.project_type || 'Оклад' }}
            </div>
            <div class="row items-center q-gutter-sm text-caption text-grey-5">
              <q-badge :color="p.is_paid ? 'positive' : 'warning'" :label="p.is_paid ? 'Оплачено' : 'Ожидает'" dense />
              <span v-if="p.stage_name">{{ p.stage_name }}</span>
              <span v-if="p.report_month">{{ p.report_month }}</span>
              <span v-if="p.payment_subtype">{{ p.payment_subtype }}</span>
              <q-space />
              <q-btn v-if="!p.is_paid && p.id" flat dense size="sm" icon="check" color="positive" @click.stop="markPaid(p)" />
              <q-btn v-if="p.id" flat dense size="sm" icon="delete" color="negative" @click.stop="deletePayment(p)" />
            </div>
          </q-card-section>
        </q-card>

        <div v-if="payments.length === 0" class="text-center q-pa-xl text-grey-5">
          <q-icon name="payments" size="48px" class="q-mb-sm" />
          <div>Нет платежей по фильтру</div>
        </div>
      </template>
    </q-pull-to-refresh>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { paymentsApi } from 'src/services/api'

const $q = useQuasar()
const payments = ref([])
const loading = ref(false)
const currentYear = new Date().getFullYear()

const filters = ref({
  payment_type: '',
  year: currentYear,
  month: null,
  is_paid: null
})

const paymentTypes = [
  { label: 'Все', value: '' },
  { label: 'Индивидуальные', value: 'Индивидуальный' },
  { label: 'Шаблонные', value: 'Шаблонный' },
  { label: 'Авторский надзор', value: 'Авторский надзор' },
  { label: 'Оклады', value: 'Оклад' }
]

const years = Array.from({ length: 10 }, (_, i) => currentYear - i)

const months = [
  { label: 'Все', value: null },
  ...Array.from({ length: 12 }, (_, i) => ({
    label: new Date(2000, i).toLocaleDateString('ru-RU', { month: 'long' }),
    value: i + 1
  }))
]

const paidOptions = [
  { label: 'Все', value: null },
  { label: 'Оплачено', value: true },
  { label: 'Ожидает', value: false }
]

const totalAmount = computed(() =>
  payments.value.reduce((sum, p) => sum + (p.final_amount || p.amount || 0), 0)
)

function formatMoney(amount) {
  if (!amount) return '0 ₽'
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(amount)
}

async function loadData() {
  loading.value = true
  try {
    const params = { year: filters.value.year }
    if (filters.value.payment_type) params.payment_type = filters.value.payment_type
    if (filters.value.month) params.month = filters.value.month
    if (filters.value.is_paid !== null) params.is_paid = filters.value.is_paid
    const { data } = await paymentsApi.getList(params)
    payments.value = data
  } catch { payments.value = [] }
  finally { loading.value = false }
}

async function markPaid(p) {
  try {
    await paymentsApi.markPaid(p.id)
    $q.notify({ type: 'positive', message: 'Отмечено как оплачено' })
    p.is_paid = true
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function deletePayment(p) {
  $q.dialog({ title: 'Удалить платёж?', message: `${p.employee_name || ''} — ${formatMoney(p.final_amount || p.amount)}`, cancel: true }).onOk(async () => {
    try {
      await paymentsApi.delete(p.id)
      payments.value = payments.value.filter(x => x.id !== p.id)
      $q.notify({ type: 'positive', message: 'Платёж удалён' })
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

function onRefresh(done) { loadData().finally(done) }

onMounted(() => loadData())
</script>
