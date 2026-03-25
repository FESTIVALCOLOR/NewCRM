<template>
  <q-page padding>
    <!-- Тип выплат -->
    <div class="row items-center q-mb-md" style="overflow-x: auto; flex-wrap: nowrap">
      <div class="toggle-pills-wide">
        <button v-for="t in paymentTabs" :key="t.value" :class="{ active: paymentTab === t.value }" @click="paymentTab = t.value">{{ t.label }}</button>
      </div>
    </div>

    <!-- Фильтры — расширенные как в десктопе -->
    <div class="row q-col-gutter-xs q-mb-xs">
      <div class="col"><q-select v-model="filters.period" :options="periodOptions" outlined dense emit-value map-options style="font-size: 12px" @update:model-value="loadData"><template v-slot:prepend><q-icon name="date_range" size="16px" /></template></q-select></div>
      <div class="col"><q-select v-model="filters.employee_id" :options="employeeOpts" outlined dense emit-value map-options clearable use-input input-debounce="200" @filter="filterEmployees" placeholder="Исполнитель" style="font-size: 12px" @update:model-value="onEmployeeFilter" @clear="filters.employee_id = null; loadData()"><template v-slot:prepend><q-icon name="person" size="16px" /></template></q-select></div>
      <div class="col-auto"><q-select v-model="filters.status" :options="statusOptions" outlined dense emit-value map-options style="font-size: 12px; min-width: 100px" @update:model-value="loadData"><template v-slot:prepend><q-icon name="filter_list" size="16px" /></template></q-select></div>
    </div>
    <!-- Строка 2: адрес, роль, агент -->
    <div class="row q-col-gutter-xs q-mb-md">
      <div class="col"><q-input v-model="filters.address" placeholder="Адрес" outlined dense clearable style="font-size: 12px" @update:model-value="loadData"><template v-slot:prepend><q-icon name="location_on" size="16px" /></template></q-input></div>
      <div class="col"><q-select v-model="filters.role" :options="roleOpts" outlined dense clearable label="Роль" style="font-size: 12px" @clear="filters.role = null; loadData()" @update:model-value="loadData"><template v-slot:prepend><q-icon name="badge" size="16px" /></template></q-select></div>
      <div class="col"><q-select v-model="filters.agent_type" :options="agentOpts" outlined dense clearable label="Агент" style="font-size: 12px" @clear="filters.agent_type = null; loadData()" @update:model-value="loadData"><template v-slot:prepend><q-icon name="business" size="16px" /></template></q-select></div>
    </div>

    <!-- Период -->
    <div v-if="filters.period !== 'all'" class="row q-col-gutter-xs q-mb-md">
      <div class="col"><q-select v-model="filters.year" :options="years" label="Год" outlined dense @update:model-value="loadData" /></div>
      <div class="col" v-if="filters.period === 'month'"><q-select v-model="filters.month" :options="monthOpts" label="Месяц" outlined dense emit-value map-options @update:model-value="loadData" /></div>
      <div class="col" v-if="filters.period === 'quarter'"><q-select v-model="filters.quarter" :options="quarterOpts" label="Квартал" outlined dense emit-value map-options @update:model-value="loadData" /></div>
    </div>

    <!-- Итого -->
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
              <div class="stat-pill pending">{{ toPayCount }} к оплате</div>
              <div class="stat-pill inwork">{{ inWorkCount }} в работе</div>
            </div>
            <div class="text-caption q-mt-xs" style="color: #999">{{ payments.length }} записей</div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Список -->
    <q-pull-to-refresh @refresh="onRefresh">
      <div v-if="loading">
        <q-card class="is-card q-mb-sm" v-for="n in 5" :key="n"><q-card-section><q-skeleton type="text" width="60%" /><q-skeleton type="text" width="40%" /></q-card-section></q-card>
      </div>

      <template v-else>
        <div v-for="group in groupedPayments" :key="group.employeeId" class="q-mb-md">
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
          <q-slide-transition>
            <div v-show="group.expanded">
              <q-card v-for="p in group.items" :key="p.id || p.salary_id" flat class="payment-card" :style="payRowStyle(p)">
                <q-card-section class="q-pa-sm">
                  <div class="row items-center no-wrap">
                    <div style="flex: 1; min-width: 0">
                      <div class="text-caption ellipsis" style="color: #888">
                        {{ p.contract_number || '' }}<span v-if="p.stage_name"> · {{ p.stage_name }}</span><span v-if="p.payment_subtype"> · {{ p.payment_subtype }}</span>
                      </div>
                      <div v-if="p.address" class="text-caption ellipsis" style="color: #aaa; font-size: 10px">{{ p.address }}</div>
                    </div>
                    <div class="text-right q-ml-sm" style="flex-shrink: 0">
                      <div class="row items-center justify-end no-wrap">
                        <div class="text-weight-bold" style="font-size: 13px" :style="{ color: p.is_paid ? '#27AE60' : '#333' }">{{ formatMoney(p.final_amount || p.amount) }}</div>
                        <div style="width: 1px; height: 16px; background: #ddd; margin: 0 6px"></div>
                        <div class="text-caption" :style="{ color: fmtMonth(p.report_month) !== 'в работе' ? '#333' : '#bbb' }">{{ fmtMonth(p.report_month) }}</div>
                      </div>
                      <div class="row items-center justify-end q-gutter-xs q-mt-xs" style="flex-wrap: wrap">
                        <!-- Статус -->
                        <q-btn v-if="p.is_paid || p.payment_status === 'paid'" unelevated dense size="xs" label="Оплачено" no-caps color="positive" style="font-size: 10px; padding: 2px 8px; border-radius: 4px" @click.stop="undoPaid(p)" />
                        <q-btn v-else-if="p.report_month || p.payment_status === 'to_pay'" unelevated dense size="xs" label="К оплате" no-caps color="warning" text-color="dark" style="font-size: 10px; padding: 2px 8px; border-radius: 4px" @click.stop="setPayStatus(p)" />
                        <q-btn v-else unelevated dense size="xs" label="В работе" no-caps color="grey-3" text-color="grey-7" style="font-size: 10px; padding: 2px 8px; border-radius: 4px" disable />
                        <!-- Действия -->
                        <q-btn v-if="!p.is_paid && (p.report_month || p.payment_status === 'to_pay')" outline dense size="xs" icon="check" label="Оплатить" no-caps color="positive" style="font-size: 10px; padding: 2px 8px; border-radius: 4px" @click.stop="markPaid(p)" />
                        <q-btn v-if="!p.is_paid && !p.report_month && p.payment_status !== 'to_pay'" outline dense size="xs" icon="schedule" label="К оплате" no-caps color="warning" style="font-size: 10px; padding: 2px 8px; border-radius: 4px" @click.stop="setPayStatus(p)" />
                        <q-btn outline dense size="xs" icon="delete_outline" no-caps color="negative" style="font-size: 10px; padding: 2px 6px; border-radius: 4px" @click.stop="deletePayment(p)" />
                      </div>
                    </div>
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </q-slide-transition>
        </div>

        <!-- Итого за год / за всё время -->
        <q-card v-if="payments.length > 0" class="is-card q-mt-md" style="border-left: 3px solid #ffd93c">
          <q-card-section class="q-pa-md">
            <div class="row justify-between q-mb-xs">
              <div class="text-caption" style="color: #888">Итого за год {{ filters.year || '' }}</div>
              <div class="text-weight-bold">{{ formatMoney(totalAmount) }}</div>
            </div>
            <div class="row justify-between">
              <div class="text-caption" style="color: #888">Всего записей</div>
              <div class="text-weight-bold">{{ payments.length }}</div>
            </div>
          </q-card-section>
        </q-card>

        <div v-if="payments.length === 0" class="text-center q-pa-xl" style="color: #999">
          <q-icon name="payments" size="48px" class="q-mb-sm" /><div>Нет платежей по фильтру</div>
        </div>
      </template>
    </q-pull-to-refresh>

    <!-- FAB создания (только для окладов) -->
    <q-page-sticky v-if="paymentTab === 'salary'" position="bottom-right" :offset="[18, 18]">
      <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="showCreateDialog = true" />
    </q-page-sticky>

    <!-- Диалог создания оклада -->
    <q-dialog v-model="showCreateDialog">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">Новый оклад</q-toolbar-title>
          <q-btn flat round dense icon="close" @click="showCreateDialog = false" />
        </q-toolbar>
        <q-card-section>
          <q-select v-model="newPay.employee_id" :options="employeeOpts" label="Сотрудник *" outlined dense emit-value map-options class="q-mb-sm" />
          <q-input v-model.number="newPay.amount" label="Сумма *" outlined dense type="number" prefix="₽" class="q-mb-sm" />
          <q-input v-model="newPay.report_month" label="Месяц" outlined dense type="month" class="q-mb-sm" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup no-caps />
          <q-btn unelevated label="Создать" style="background: #ffd93c; color: #333; border-radius: 4px" no-caps @click="createSalary" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { paymentsApi, salariesApi, employeesApi } from 'src/services/api'
import { useReferencesStore } from 'src/stores/references'

const $q = useQuasar()
const refsStore = useReferencesStore()
const payments = ref([])
const loading = ref(false)
const allEmployees = ref([])
const paymentTab = ref('all')
const employeeOpts = ref([])
const currentYear = new Date().getFullYear()
const showCreateDialog = ref(false)
const newPay = ref({ employee_id: null, amount: null, report_month: '' })

const paymentTabs = [
  { label: 'Все', value: 'all' }, { label: 'Инд.', value: 'individual' },
  { label: 'Шабл.', value: 'template' }, { label: 'Надзор', value: 'supervision' },
  { label: 'Оклады', value: 'salary' }
]

const filters = ref({ period: 'all', year: currentYear, month: new Date().getMonth() + 1, quarter: Math.ceil((new Date().getMonth() + 1) / 3), employee_id: null, status: null, address: '', role: null, agent_type: null })

const roleOpts = computed(() => {
  const roles = new Set(allEmployees.value.map(e => e.position).filter(Boolean))
  return [...roles].sort().map(r => ({ label: r, value: r }))
})
const agentOpts = computed(() => refsStore.agentNames())

function onEmployeeFilter(val) {
  // При выборе null (сброс) или disable item — пропускаем
  if (val === null || val === undefined) { filters.value.employee_id = null }
  loadData()
}

function filterEmployees(val, update) {
  const all = allEmployees.value.filter(e => e.status === 'активный')
  const makeOpts = (list) => {
    const byPos = {}
    for (const e of list) { const pos = e.position || 'Прочие'; if (!byPos[pos]) byPos[pos] = []; byPos[pos].push(e) }
    const opts = []
    for (const [pos, emps] of Object.entries(byPos).sort((a, b) => a[0].localeCompare(b[0]))) {
      opts.push({ label: `── ${pos} ──`, value: `__header_${pos}`, disable: true })
      for (const e of emps) opts.push({ label: e.full_name, value: e.id })
    }
    return opts
  }
  if (!val) { update(() => { employeeOpts.value = makeOpts(all) }); return }
  const q = val.toLowerCase()
  update(() => { employeeOpts.value = makeOpts(all.filter(e => (e.full_name || '').toLowerCase().includes(q))) })
}

const periodOptions = [{ label: 'Все', value: 'all' }, { label: 'Месяц', value: 'month' }, { label: 'Квартал', value: 'quarter' }, { label: 'Год', value: 'year' }]
const statusOptions = [{ label: 'Все', value: null }, { label: 'В работе', value: 'in_work' }, { label: 'К оплате', value: 'to_pay' }, { label: 'Оплачено', value: 'paid' }]
const years = Array.from({ length: 10 }, (_, i) => currentYear - i)
const monthOpts = Array.from({ length: 12 }, (_, i) => ({ label: new Date(2000, i).toLocaleDateString('ru-RU', { month: 'long' }), value: i + 1 }))
const quarterOpts = [{ label: 'Q1', value: 1 }, { label: 'Q2', value: 2 }, { label: 'Q3', value: 3 }, { label: 'Q4', value: 4 }]
const paymentTypeMap = { all: '', individual: 'Индивидуальный', template: 'Шаблонный', supervision: 'Авторский надзор', salary: 'Оклад' }

const totalAmount = computed(() => payments.value.reduce((sum, p) => sum + (p.final_amount || p.amount || 0), 0))
const paidCount = computed(() => payments.value.filter(p => p.is_paid).length)
const toPayCount = computed(() => payments.value.filter(p => !p.is_paid && p.report_month).length)
const inWorkCount = computed(() => payments.value.filter(p => !p.is_paid && !p.report_month).length)

const groupedPayments = computed(() => {
  const map = {}
  for (const p of payments.value) {
    const key = p.employee_id || p.employee_name || 'unknown'
    if (!map[key]) { map[key] = { employeeId: key, name: p.employee_name || 'Без исполнителя', role: p.role || p.position || '', initial: (p.employee_name || '?')[0], total: 0, items: [], expanded: true } }
    map[key].items.push(p); map[key].total += p.final_amount || p.amount || 0
  }
  return Object.values(map).sort((a, b) => b.total - a.total)
})

function formatMoney(v) { if (!v) return '0 ₽'; return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(v) }
function fmtMonth(m) {
  if (!m) return 'в работе'
  try { const [y, mo] = m.split('-'); const months = ['январь','февраль','март','апрель','май','июнь','июль','август','сентябрь','октябрь','ноябрь','декабрь']; return `${months[parseInt(mo)-1]} ${y}` } catch { return m }
}
function payRowStyle(p) {
  if (p.is_paid || p.payment_status === 'paid') return { background: '#E8F5E9' }
  if (p.report_month || p.payment_status === 'to_pay') return { background: '#FFF8E1' }
  return {}
}

async function loadData() {
  loading.value = true
  try {
    const params = {}
    // НЕ передаём payment_type на сервер — фильтруем на клиенте для корректной работы вкладок
    if (filters.value.period !== 'all') {
      params.year = filters.value.year
      if (filters.value.period === 'month') params.month = filters.value.month
    } else {
      // При "Все" — загружаем за текущий год + без месяца
      params.year = currentYear
      params.include_null_month = true
    }
    if (filters.value.employee_id) params.employee_id = filters.value.employee_id
    if (filters.value.status === 'paid') params.is_paid = true
    else if (filters.value.status === 'to_pay') params.is_paid = false
    // Всегда включаем платежи без месяца (в работе)
    if (!params.include_null_month) params.include_null_month = true
    // Загружаем без payment_type фильтра на сервере — фильтруем на клиенте для надёжности
    const { data } = await paymentsApi.getList(params)
    let filtered = data || []

    // Фильтр по вкладкам — по project_type (не payment_type!)
    if (paymentTab.value === 'salary') {
      filtered = filtered.filter(p => p.source === 'Оклад')
    } else if (paymentTab.value === 'individual') {
      filtered = filtered.filter(p => p.project_type === 'Индивидуальный' && p.source !== 'Оклад')
    } else if (paymentTab.value === 'template') {
      filtered = filtered.filter(p => p.project_type === 'Шаблонный' && p.source !== 'Оклад')
    } else if (paymentTab.value === 'supervision') {
      filtered = filtered.filter(p => (p.project_type === 'Авторский надзор' || p.project_type === 'Надзор') && p.source !== 'Оклад')
    }

    // Фильтр по адресу
    if (filters.value.address) {
      const q = filters.value.address.toLowerCase()
      filtered = filtered.filter(p => (p.address || '').toLowerCase().includes(q))
    }
    // Фильтр по роли (сравниваем с role и position)
    if (filters.value.role) filtered = filtered.filter(p => (p.role || '').includes(filters.value.role) || (p.position || '').includes(filters.value.role))
    // Фильтр по агенту
    if (filters.value.agent_type) filtered = filtered.filter(p => (p.agent_type || '').includes(filters.value.agent_type))
    // Фильтр по статусу
    if (filters.value.status === 'in_work') filtered = filtered.filter(p => !p.is_paid && !p.report_month)
    else if (filters.value.status === 'to_pay') filtered = filtered.filter(p => !p.is_paid && p.report_month)
    else if (filters.value.status === 'paid') filtered = filtered.filter(p => p.is_paid)

    payments.value = filtered
  } catch { payments.value = [] } finally { loading.value = false }
}

async function undoPaid(p) {
  $q.dialog({ title: 'Снять статус оплаты?', message: p.employee_name, cancel: { label: 'Нет', flat: true, noCaps: true }, ok: { label: 'Да', noCaps: true, color: 'negative' } }).onOk(async () => {
    try {
      if (p.source === 'Оклад') await salariesApi.update(p.id, { payment_status: 'pending' })
      else if (p.id) await paymentsApi.update(p.id, { is_paid: false, payment_status: 'pending' })
      p.is_paid = false
      $q.notify({ type: 'info', message: 'Статус оплаты снят' })
    } catch (err) { const d = err.response?.data?.detail; $q.notify({ type: 'negative', message: typeof d === 'string' ? d : 'Ошибка' }) }
  })
}

async function markPaid(p) {
  try {
    if (p.source === 'Оклад') {
      // Оклад — обновляем через salaries API (id = salary id)
      await salariesApi.update(p.id, { payment_status: 'paid' })
    } else if (p.id) {
      // Платёж — используем mark-paid с employee_id
      await paymentsApi.markPaid(p.id, p.employee_id)
    }
    p.is_paid = true
    p.payment_status = 'paid'
    $q.notify({ type: 'positive', message: 'Оплачено' })
  } catch (err) {
    const d = err.response?.data?.detail
    $q.notify({ type: 'negative', message: typeof d === 'string' ? d : JSON.stringify(d || 'Ошибка') })
  }
}

async function setPayStatus(p) {
  try {
    // Toggle: если уже к оплате (есть report_month) → снять (убрать report_month)
    if (p.report_month) {
      if (p.source === 'Оклад') await salariesApi.update(p.id, { report_month: '', payment_status: 'pending' })
      else if (p.id) await paymentsApi.update(p.id, { report_month: '' })
      p.report_month = null
      $q.notify({ type: 'info', message: 'Статус снят' })
    } else {
      const now = new Date()
      const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
      if (p.source === 'Оклад') await salariesApi.update(p.id, { report_month: month, payment_status: 'to_pay' })
      else if (p.id) await paymentsApi.update(p.id, { report_month: month })
      p.report_month = month
      $q.notify({ type: 'positive', message: 'К оплате' })
    }
  } catch (err) {
    const d = err.response?.data?.detail
    $q.notify({ type: 'negative', message: typeof d === 'string' ? d : 'Ошибка' })
  }
}

async function deletePayment(p) {
  $q.dialog({ title: 'Удалить?', message: `${p.employee_name} — ${formatMoney(p.final_amount || p.amount)}`, cancel: { label: 'Нет', flat: true, noCaps: true }, ok: { label: 'Да', noCaps: true, color: 'negative' } }).onOk(async () => {
    try {
      if (p.source === 'Оклад') await salariesApi.delete(p.id)
      else if (p.id) await paymentsApi.delete(p.id)
      payments.value = payments.value.filter(x => x.id !== p.id)
      $q.notify({ type: 'positive', message: 'Удалено' })
    } catch (err) {
      const d = err.response?.data?.detail
      $q.notify({ type: 'negative', message: typeof d === 'string' ? d : 'Ошибка удаления' })
    }
  })
}

async function createSalary() {
  if (!newPay.value.employee_id || !newPay.value.amount) { $q.notify({ type: 'warning', message: 'Заполните сотрудника и сумму' }); return }
  // report_month обязателен, формат YYYY-MM
  const month = newPay.value.report_month || `${currentYear}-${String(new Date().getMonth() + 1).padStart(2, '0')}`
  try {
    await salariesApi.create({
      employee_id: newPay.value.employee_id,
      amount: parseFloat(newPay.value.amount),
      payment_type: 'Оклад',
      report_month: month
    })
    $q.notify({ type: 'positive', message: 'Оклад создан' }); showCreateDialog.value = false; loadData()
  } catch (err) {
    const detail = err.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : JSON.stringify(detail || 'Ошибка создания')
    $q.notify({ type: 'negative', message: msg })
  }
}

watch(paymentTab, () => loadData())
function onRefresh(done) { loadData().finally(done) }

onMounted(async () => {
  loadData()
  try {
    const { data } = await employeesApi.getList()
    allEmployees.value = data || []
    employeeOpts.value = data.filter(e => e.status === 'активный').map(e => ({ label: `${e.full_name} (${e.position || ''})`, value: e.id }))
  } catch {}
})
</script>

<style scoped>
.toggle-pills-wide { display: inline-flex; border: 1px solid #d9d9d9; border-radius: 6px; overflow: hidden; width: 100% }
.toggle-pills-wide button { flex: 1; border: none; background: #F5F5F5; color: #888; font-size: 12px; padding: 7px 6px; cursor: pointer; transition: all 0.2s; font-family: inherit; white-space: nowrap }
.toggle-pills-wide button.active { background: white; color: #333; font-weight: bold; box-shadow: 0 1px 3px rgba(0,0,0,0.08) }
.toggle-pills-wide button + button { border-left: 1px solid #d9d9d9 }
.summary-card { border-left: 3px solid #ffd93c }
.stat-pill { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold }
.stat-pill.paid { background: #E8F8F5; color: #27AE60 }
.stat-pill.pending { background: #FFF8E1; color: #F39C12 }
.stat-pill.inwork { background: #F5F5F5; color: #888 }
.employee-group-header { display: flex; align-items: center; padding: 8px 12px; background: white; border: 1px solid #E0E0E0; border-radius: 8px 8px 0 0; cursor: pointer }
.payment-card { border: none; border-left: 1px solid #E0E0E0; border-right: 1px solid #E0E0E0; border-bottom: 1px solid #F0F0F0; border-radius: 0 }
.payment-card:last-child { border-radius: 0 0 8px 8px; border-bottom: 1px solid #E0E0E0 }
</style>
