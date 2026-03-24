<template>
  <q-page padding>
    <!-- Тип выплат — pill toggle вместо вкладок -->
    <div class="row items-center q-mb-md" style="overflow-x: auto; flex-wrap: nowrap; gap: 0">
      <div class="toggle-pills-wide">
        <button v-for="t in paymentTabs" :key="t.value" :class="{ active: paymentTab === t.value }" @click="paymentTab = t.value">
          {{ t.label }}
        </button>
      </div>
    </div>

    <!-- Фильтры — одна компактная строка -->
    <div class="row q-col-gutter-xs q-mb-md">
      <div class="col">
        <q-select v-model="filters.period" :options="periodOptions" outlined dense emit-value map-options
          style="font-size: 12px" @update:model-value="loadData">
          <template v-slot:prepend><q-icon name="date_range" size="16px" /></template>
        </q-select>
      </div>
      <div class="col">
        <q-select v-model="filters.employee_id" :options="employeeOpts" outlined dense emit-value map-options clearable
          placeholder="Исполнитель" style="font-size: 12px" @update:model-value="loadData">
          <template v-slot:prepend><q-icon name="person" size="16px" /></template>
        </q-select>
      </div>
      <div class="col-auto">
        <q-select v-model="filters.is_paid" :options="paidOptions" outlined dense emit-value map-options
          style="font-size: 12px; min-width: 90px" @update:model-value="loadData">
          <template v-slot:prepend><q-icon name="filter_list" size="16px" /></template>
        </q-select>
      </div>
    </div>

    <!-- Период (если не "Все") -->
    <div v-if="filters.period !== 'all'" class="row q-col-gutter-xs q-mb-md">
      <div class="col">
        <q-select v-model="filters.year" :options="years" label="Год" outlined dense @update:model-value="loadData" />
      </div>
      <div class="col" v-if="filters.period === 'month'">
        <q-select v-model="filters.month" :options="monthOpts" label="Месяц" outlined dense emit-value map-options @update:model-value="loadData" />
      </div>
      <div class="col" v-if="filters.period === 'quarter'">
        <q-select v-model="filters.quarter" :options="quarterOpts" label="Квартал" outlined dense emit-value map-options @update:model-value="loadData" />
      </div>
    </div>

    <!-- Итоговая карточка -->
    <q-card class="is-card q-mb-md summary-card" v-if="!loading">
      <q-card-section class="q-pa-md">
        <div class="row items-end justify-between">
          <div>
            <div class="text-caption" style="color: #888">Итого</div>
            <div class="text-h5 text-weight-bold" style="color: #333">{{ formatMoney(totalAmount) }}</div>
          </div>
          <div class="text-right">
            <div class="row q-gutter-sm">
              <div class="stat-pill paid">{{ paidCount }} оплачено</div>
              <div class="stat-pill pending">{{ pendingCount }} ожидает</div>
            </div>
            <div class="text-caption q-mt-xs" style="color: #999">{{ payments.length }} записей</div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Список — сгруппирован по исполнителям -->
    <q-pull-to-refresh @refresh="onRefresh">
      <div v-if="loading">
        <q-card class="is-card q-mb-sm" v-for="n in 5" :key="n">
          <q-card-section><q-skeleton type="text" width="60%" /><q-skeleton type="text" width="40%" /></q-card-section>
        </q-card>
      </div>

      <template v-else>
        <!-- Группы по исполнителям -->
        <div v-for="group in groupedPayments" :key="group.employeeId" class="q-mb-md">
          <!-- Заголовок группы -->
          <div class="employee-group-header" @click="group.expanded = !group.expanded">
            <q-avatar size="28px" color="grey-3" text-color="grey-8">{{ group.initial }}</q-avatar>
            <div style="flex: 1; margin-left: 8px">
              <div class="text-weight-bold" style="font-size: 13px; color: #333">{{ group.name }}</div>
              <div class="text-caption" style="color: #888">{{ group.role }}</div>
            </div>
            <div class="text-right">
              <div class="text-weight-bold" style="font-size: 14px; color: #333">{{ formatMoney(group.total) }}</div>
              <div class="text-caption" style="color: #999">{{ group.items.length }} выплат</div>
            </div>
            <q-icon :name="group.expanded ? 'expand_less' : 'expand_more'" color="grey-5" size="20px" class="q-ml-xs" />
          </div>

          <!-- Платежи внутри группы -->
          <q-slide-transition>
            <div v-show="group.expanded">
              <q-card v-for="p in group.items" :key="p.id || p.salary_id" flat class="payment-card">
                <q-card-section class="q-pa-sm">
                  <div class="row items-center no-wrap">
                    <!-- Левая часть: инфо -->
                    <div style="flex: 1; min-width: 0">
                      <div class="text-caption ellipsis" style="color: #888">
                        {{ p.contract_number || '' }}
                        <span v-if="p.stage_name"> · {{ p.stage_name }}</span>
                        <span v-if="p.payment_subtype"> · {{ p.payment_subtype }}</span>
                      </div>
                      <div v-if="p.address" class="text-caption ellipsis" style="color: #aaa; font-size: 10px">{{ p.address }}</div>
                      <div v-if="p.report_month" class="text-caption" style="color: #bbb; font-size: 10px">{{ p.report_month }}</div>
                    </div>
                    <!-- Правая часть: сумма + действия -->
                    <div class="text-right q-ml-sm" style="flex-shrink: 0">
                      <div class="text-weight-bold" style="font-size: 13px" :style="{ color: p.is_paid ? '#27AE60' : '#333' }">
                        {{ formatMoney(p.final_amount || p.amount) }}
                      </div>
                      <div class="row items-center justify-end q-gutter-xs q-mt-xs">
                        <q-badge :color="p.is_paid ? 'positive' : 'warning'" :label="p.is_paid ? 'Опл.' : 'Ожид.'" dense style="font-size: 9px" />
                        <q-btn v-if="!p.is_paid && p.id" flat round dense size="xs" icon="check" color="positive" @click.stop="markPaid(p)" />
                        <q-btn v-if="p.id" flat round dense size="xs" icon="delete_outline" color="grey-5" @click.stop="deletePayment(p)" />
                      </div>
                    </div>
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </q-slide-transition>
        </div>

        <div v-if="payments.length === 0" class="text-center q-pa-xl" style="color: #999">
          <q-icon name="payments" size="48px" class="q-mb-sm" />
          <div>Нет платежей по фильтру</div>
        </div>
      </template>
    </q-pull-to-refresh>

    <!-- FAB создания -->
    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="showCreateDialog = true" />
    </q-page-sticky>

    <!-- Диалог создания -->
    <q-dialog v-model="showCreateDialog">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">Новый платёж</q-toolbar-title>
          <q-btn flat round dense icon="close" @click="showCreateDialog = false" />
        </q-toolbar>
        <q-card-section>
          <q-select v-model="newPay.employee_id" :options="employeeOpts" label="Исполнитель *" outlined dense emit-value map-options class="q-mb-sm" />
          <q-select v-model="newPay.payment_subtype" :options="['Аванс', 'Доплата', 'Полная оплата', 'Оклад']" label="Тип" outlined dense class="q-mb-sm" />
          <q-input v-model.number="newPay.amount" label="Сумма *" outlined dense type="number" prefix="₽" class="q-mb-sm" />
          <q-input v-model="newPay.report_month" label="Месяц" outlined dense type="month" class="q-mb-sm" />
          <q-input v-model="newPay.comments" label="Комментарий" outlined dense class="q-mb-sm" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup no-caps />
          <q-btn unelevated label="Создать" style="background: #ffd93c; color: #333; border-radius: 4px" no-caps @click="createNewPayment" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, reactive, watch, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { paymentsApi, employeesApi } from 'src/services/api'

const $q = useQuasar()
const payments = ref([])
const loading = ref(false)
const paymentTab = ref('all')
const employeeOpts = ref([])
const currentYear = new Date().getFullYear()
const showCreateDialog = ref(false)
const newPay = ref({ employee_id: null, payment_subtype: 'Аванс', amount: null, report_month: '', comments: '' })

const paymentTabs = [
  { label: 'Все', value: 'all' },
  { label: 'Инд.', value: 'individual' },
  { label: 'Шабл.', value: 'template' },
  { label: 'Надзор', value: 'supervision' },
  { label: 'Оклады', value: 'salary' }
]

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
  { label: 'Опл.', value: true },
  { label: 'Ожид.', value: false }
]

const paymentTypeMap = {
  all: '', individual: 'Индивидуальный', template: 'Шаблонный', supervision: 'Авторский надзор', salary: 'Оклад'
}

const totalAmount = computed(() => payments.value.reduce((sum, p) => sum + (p.final_amount || p.amount || 0), 0))
const paidCount = computed(() => payments.value.filter(p => p.is_paid).length)
const pendingCount = computed(() => payments.value.filter(p => !p.is_paid).length)

// Группировка по исполнителям
const groupedPayments = computed(() => {
  const map = {}
  for (const p of payments.value) {
    const key = p.employee_id || p.employee_name || 'unknown'
    if (!map[key]) {
      map[key] = {
        employeeId: key,
        name: p.employee_name || 'Без исполнителя',
        role: p.role || p.position || '',
        initial: (p.employee_name || '?')[0],
        total: 0,
        items: [],
        expanded: true
      }
    }
    map[key].items.push(p)
    map[key].total += p.final_amount || p.amount || 0
  }
  return Object.values(map).sort((a, b) => b.total - a.total)
})

function formatMoney(v) {
  if (!v) return '0 ₽'
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(v)
}

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
    p.is_paid = true
    $q.notify({ type: 'positive', message: 'Оплачено' })
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

async function createNewPayment() {
  if (!newPay.value.employee_id || !newPay.value.amount) {
    $q.notify({ type: 'warning', message: 'Заполните исполнителя и сумму' })
    return
  }
  try {
    if (newPay.value.payment_subtype === 'Оклад') {
      const { salariesApi } = await import('src/services/api')
      await salariesApi.create({
        employee_id: newPay.value.employee_id,
        amount: newPay.value.amount,
        report_month: newPay.value.report_month || null,
        comments: newPay.value.comments
      })
    } else {
      await paymentsApi.create({
        employee_id: newPay.value.employee_id,
        payment_subtype: newPay.value.payment_subtype,
        amount: newPay.value.amount,
        final_amount: newPay.value.amount,
        report_month: newPay.value.report_month || null,
        is_paid: false
      })
    }
    $q.notify({ type: 'positive', message: 'Платёж создан' })
    showCreateDialog.value = false
    loadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
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

<style scoped>
/* Toggle pills wide */
.toggle-pills-wide {
  display: inline-flex;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  overflow: hidden;
  width: 100%;
}
.toggle-pills-wide button {
  flex: 1;
  border: none;
  background: #F5F5F5;
  color: #888;
  font-size: 12px;
  padding: 7px 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
  white-space: nowrap;
}
.toggle-pills-wide button.active {
  background: white;
  color: #333;
  font-weight: bold;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.toggle-pills-wide button + button {
  border-left: 1px solid #d9d9d9;
}

/* Summary card */
.summary-card {
  border-left: 3px solid #ffd93c;
}

/* Stat pills */
.stat-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: bold;
}
.stat-pill.paid {
  background: #E8F8F5;
  color: #27AE60;
}
.stat-pill.pending {
  background: #FFF8E1;
  color: #F39C12;
}

/* Employee group */
.employee-group-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: white;
  border: 1px solid #E0E0E0;
  border-radius: 8px 8px 0 0;
  cursor: pointer;
}

/* Payment card inside group */
.payment-card {
  border: none;
  border-left: 1px solid #E0E0E0;
  border-right: 1px solid #E0E0E0;
  border-bottom: 1px solid #F0F0F0;
  border-radius: 0;
  background: #FAFAFA;
}
.payment-card:last-child {
  border-radius: 0 0 8px 8px;
  border-bottom: 1px solid #E0E0E0;
}
</style>
