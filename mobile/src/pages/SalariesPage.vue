<template>
  <q-page padding>
    <!-- Тип выплат -->
    <div class="row items-center q-mb-md" style="overflow-x: auto; flex-wrap: nowrap">
      <div class="toggle-pills-wide">
        <button v-for="t in paymentTabs" :key="t.value" :class="{ active: paymentTab === t.value }" @click="paymentTab = t.value">
          {{ t.label }}
        </button>
      </div>
      <q-btn
        v-if="isSuperuser"
        flat
        dense
        no-caps
        label="Пересчёт"
        color="orange"
        style="font-size: 11px"
        @click="recalculatePayments"
      />
    </div>

    <!-- Фильтры — расширенные как в десктопе -->
    <div class="row q-col-gutter-xs q-mb-xs">
      <div class="col">
        <q-select
          v-model="filters.period"
          :options="periodOptions"
          outlined
          dense
          emit-value
          map-options
          style="font-size: 12px"
          @update:model-value="loadData"
        >
          <template #prepend>
            <q-icon name="date_range" size="16px" />
          </template>
        </q-select>
      </div>
      <div class="col" style="min-width: 0; overflow: hidden">
        <q-select
          v-model="filters.employee_id"
          :options="employeeOpts"
          outlined
          dense
          emit-value
          map-options
          clearable
          use-input
          input-debounce="200"
          placeholder="Исполнитель"
          style="font-size: 12px; min-width: 0"
          @filter="filterEmployees"
          @update:model-value="onEmployeeFilter"
          @clear="filters.employee_id = null; loadData()"
        >
          <template #prepend>
            <q-icon name="person" size="16px" />
          </template>
        </q-select>
      </div>
      <div class="col-auto">
        <q-select
          v-model="filters.status"
          :options="statusOptions"
          outlined
          dense
          emit-value
          map-options
          style="font-size: 12px; min-width: 100px"
          @update:model-value="loadData"
        >
          <template #prepend>
            <q-icon name="filter_list" size="16px" />
          </template>
        </q-select>
      </div>
      <div class="col-auto">
        <q-select
          v-model="filters.payment_type"
          :options="paymentTypeOptions"
          label="Тип выплаты"
          outlined
          dense
          emit-value
          map-options
          style="font-size: 12px; min-width: 100px"
          @update:model-value="loadData"
        >
          <template #prepend>
            <q-icon name="payment" size="16px" />
          </template>
        </q-select>
      </div>
    </div>
    <!-- Строка 2: адрес, роль, агент -->
    <div class="row q-col-gutter-xs q-mb-md">
      <div class="col">
        <q-input
          v-model="filters.address"
          placeholder="Адрес"
          outlined
          dense
          clearable
          style="font-size: 12px"
          @update:model-value="loadData"
        >
          <template #prepend>
            <q-icon name="location_on" size="16px" />
          </template>
        </q-input>
      </div>
      <div class="col">
        <q-select
          v-model="filters.role"
          :options="roleOpts"
          outlined
          dense
          clearable
          emit-value
          map-options
          label="Роль"
          style="font-size: 12px"
          @clear="filters.role = null; loadData()"
          @update:model-value="loadData"
        >
          <template #prepend>
            <q-icon name="badge" size="16px" />
          </template>
        </q-select>
      </div>
      <div class="col">
        <q-select
          v-model="filters.agent_type"
          :options="agentOpts"
          outlined
          dense
          clearable
          label="Агент"
          style="font-size: 12px"
          @clear="filters.agent_type = null; loadData()"
          @update:model-value="loadData"
        >
          <template #prepend>
            <q-icon name="business" size="16px" />
          </template>
        </q-select>
      </div>
      <div class="col-auto" style="display: flex; align-items: stretch">
        <q-btn
          outline
          dense
          no-caps
          label="Сбросить"
          color="grey"
          style="font-size: 12px; border-color: #bdbdbd; border-radius: 4px; min-width: 80px"
          @click="resetFilters"
        />
      </div>
    </div>

    <!-- Период -->
    <div v-if="filters.period !== 'all'" class="row q-col-gutter-xs q-mb-md">
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
      <div v-if="filters.period === 'month'" class="col">
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
      <div v-if="filters.period === 'quarter'" class="col">
        <q-select
          v-model="filters.quarter"
          :options="quarterOpts"
          label="Квартал"
          outlined
          dense
          emit-value
          map-options
          @update:model-value="loadData"
        />
      </div>
    </div>

    <!-- Итого -->
    <q-card v-if="!loading" class="is-card q-mb-md summary-card">
      <q-card-section class="q-pa-md">
        <div class="row items-end justify-between">
          <div>
            <div class="text-caption" style="color: #888">
              Итого
            </div>
            <div class="text-h5 text-weight-bold" style="color: #333">
              {{ formatMoney(totalAmount) }}
            </div>
          </div>
          <div class="text-right">
            <div class="row q-gutter-sm">
              <div class="stat-pill paid">
                {{ paidCount }} оплачено
              </div>
              <div class="stat-pill pending">
                {{ toPayCount }} к оплате
              </div>
              <div class="stat-pill inwork">
                {{ inWorkCount }} в работе
              </div>
            </div>
            <div class="text-caption q-mt-xs" style="color: #999">
              {{ payments.length }} записей
            </div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Список -->
    <q-pull-to-refresh @refresh="onRefresh">
      <div v-if="loading">
        <q-card v-for="n in 5" :key="n" class="is-card q-mb-sm">
          <q-card-section><q-skeleton type="text" width="60%" /><q-skeleton type="text" width="40%" /></q-card-section>
        </q-card>
      </div>

      <template v-else>
        <div v-for="group in groupedPayments" :key="group.employeeId" class="q-mb-md">
          <div class="employee-group-header" @click="expandedGroups[group.employeeId] = !expandedGroups[group.employeeId]">
            <q-avatar size="28px" color="grey-3" text-color="grey-8">
              {{ group.initial }}
            </q-avatar>
            <div style="flex: 1; margin-left: 8px">
              <div class="text-weight-bold" style="font-size: 13px; color: #333">
                {{ group.name }}
              </div>
              <div class="text-caption" style="color: #888">
                {{ group.role }}
              </div>
            </div>
            <div class="text-right">
              <div class="text-weight-bold" style="font-size: 14px; color: #333">
                {{ formatMoney(group.total) }}
              </div>
              <div class="text-caption" style="color: #999">
                {{ group.items.length }} выплат
              </div>
            </div>
            <q-icon :name="expandedGroups[group.employeeId] ? 'expand_less' : 'expand_more'" color="grey-5" size="20px" class="q-ml-xs" />
          </div>
          <q-slide-transition>
            <div v-show="expandedGroups[group.employeeId]">
              <q-card
                v-for="p in group.items"
                :key="p.id || p.salary_id"
                flat
                class="payment-card"
                :style="payRowStyle(p)"
              >
                <q-card-section class="q-pa-sm">
                  <div class="row items-center no-wrap">
                    <div style="flex: 1; min-width: 0">
                      <div class="text-caption ellipsis" style="color: #888">
                        {{ p.contract_number || '' }}<span v-if="p.stage_name"> · {{ p.stage_name }}</span><span v-if="p.payment_subtype"> · {{ p.payment_subtype }}</span>
                      </div>
                      <div v-if="p.address" class="text-caption ellipsis" style="color: #aaa; font-size: 10px">
                        {{ p.address }}
                      </div>
                    </div>
                    <div class="text-right q-ml-sm" style="flex-shrink: 0">
                      <div class="row items-center justify-end no-wrap">
                        <div class="text-weight-bold" style="font-size: 13px" :style="{ color: p.is_paid ? '#27AE60' : '#333' }">
                          {{ formatMoney(p.final_amount || p.amount) }}
                        </div>
                        <div style="width: 1px; height: 16px; background: #ddd; margin: 0 6px" />
                        <div class="text-caption" :style="{ color: fmtMonth(p.report_month) !== 'в работе' ? '#333' : '#bbb' }">
                          {{ fmtMonth(p.report_month) }}
                        </div>
                      </div>
                      <div class="row items-center justify-end q-gutter-xs q-mt-xs" style="flex-wrap: wrap">
                        <!-- Статус (только информация, не кнопка) -->
                        <q-chip
                          v-if="p.is_paid || p.payment_status === 'paid'"
                          dense
                          color="positive"
                          text-color="white"
                          style="font-size: 10px; height: 20px; padding: 0 8px; border-radius: 4px; cursor: default"
                        >
                          Оплачено
                        </q-chip>
                        <q-chip
                          v-else-if="p.payment_status === 'to_pay'"
                          dense
                          color="warning"
                          text-color="dark"
                          style="font-size: 10px; height: 20px; padding: 0 8px; border-radius: 4px; cursor: default"
                        >
                          К оплате
                        </q-chip>
                        <q-chip
                          v-else
                          dense
                          color="grey-3"
                          text-color="grey-7"
                          style="font-size: 10px; height: 20px; padding: 0 8px; border-radius: 4px; cursor: default"
                        >
                          В работе
                        </q-chip>
                        <!-- Кнопка действия по статусу -->
                        <q-btn
                          v-if="can('salaries.mark_paid') && (p.is_paid || p.payment_status === 'paid')"
                          outline
                          dense
                          size="xs"
                          label="Снять оплату"
                          no-caps
                          color="grey-7"
                          style="font-size: 10px; padding: 2px 8px; border-radius: 4px"
                          @click.stop="undoPaid(p)"
                        />
                        <q-btn
                          v-else-if="can('salaries.mark_paid') && p.payment_status === 'to_pay'"
                          outline
                          dense
                          size="xs"
                          icon="check"
                          label="Оплатить"
                          no-caps
                          color="positive"
                          style="font-size: 10px; padding: 2px 8px; border-radius: 4px"
                          @click.stop="markPaid(p)"
                        />
                        <q-btn
                          v-else-if="can('salaries.mark_to_pay') && !p.is_paid && p.payment_status !== 'paid'"
                          outline
                          dense
                          size="xs"
                          label="К оплате"
                          no-caps
                          color="warning"
                          style="font-size: 10px; padding: 2px 8px; border-radius: 4px"
                          @click.stop="setPayStatus(p)"
                        />
                        <q-btn
                          v-if="can('salaries.update')"
                          outline
                          dense
                          size="xs"
                          icon="edit"
                          no-caps
                          color="grey-7"
                          style="font-size: 10px; padding: 2px 6px; border-radius: 4px"
                          @click.stop="openEditDialog(p)"
                        />
                        <q-btn
                          v-if="can('salaries.delete')"
                          outline
                          dense
                          size="xs"
                          icon="delete_outline"
                          no-caps
                          color="negative"
                          style="font-size: 10px; padding: 2px 6px; border-radius: 4px"
                          @click.stop="deletePayment(p)"
                        />
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
              <div class="text-caption" style="color: #888">
                Итого за год {{ filters.year || '' }}
              </div>
              <div class="text-weight-bold">
                {{ formatMoney(totalAmount) }}
              </div>
            </div>
            <div class="row justify-between">
              <div class="text-caption" style="color: #888">
                Всего записей
              </div>
              <div class="text-weight-bold">
                {{ payments.length }}
              </div>
            </div>
          </q-card-section>
        </q-card>

        <div v-if="payments.length === 0" class="text-center q-pa-xl" style="color: #999">
          <q-icon name="payments" size="48px" class="q-mb-sm" /><div>Нет платежей по фильтру</div>
        </div>
      </template>
    </q-pull-to-refresh>

    <!-- FAB создания платежа -->
    <q-page-sticky v-if="can('salaries.create') || can('crm_cards.payments')" position="bottom-right" :offset="[18, 18]">
      <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="openCreatePayment" />
    </q-page-sticky>

    <!-- Диалог создания оклада -->
    <q-dialog v-model="showCreateDialog">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            Новый оклад
          </q-toolbar-title>
          <q-btn
            flat
            round
            dense
            icon="close"
            @click="showCreateDialog = false"
          />
        </q-toolbar>
        <q-card-section>
          <q-select
            v-model="newPay.employee_id"
            :options="employeeOpts"
            label="Сотрудник *"
            outlined
            dense
            emit-value
            map-options
            class="q-mb-sm"
          />
          <q-input
            v-model.number="newPay.amount"
            label="Сумма *"
            outlined
            dense
            type="number"
            prefix="₽"
            class="q-mb-sm"
          />
          <q-input
            v-model="newPay.report_month"
            label="Месяц"
            outlined
            dense
            type="month"
            class="q-mb-sm"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps />
          <q-btn
            unelevated
            label="Создать"
            style="background: #ffd93c; color: #333; border-radius: 4px"
            no-caps
            @click="createSalary"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог редактирования платежа -->
    <q-dialog v-model="showEditDialog">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            Редактировать платёж
          </q-toolbar-title>
          <q-btn
            flat
            round
            dense
            icon="close"
            @click="showEditDialog = false"
          />
        </q-toolbar>
        <q-card-section>
          <div class="text-caption q-mb-sm" style="color: #888">
            {{ editPay.employee_name }}
          </div>
          <q-input
            v-model.number="editPay.final_amount"
            label="Сумма *"
            outlined
            dense
            type="number"
            prefix="₽"
            class="q-mb-sm"
          />
          <q-input
            v-model="editPay.report_month"
            label="Месяц отчёта"
            outlined
            dense
            type="month"
            class="q-mb-sm"
          />
          <q-select
            v-model="editPay.payment_type"
            :options="editPaymentTypeOpts"
            label="Тип"
            outlined
            dense
            emit-value
            map-options
            class="q-mb-sm"
          />
          <q-input
            v-model="editPay.comment"
            label="Комментарий"
            outlined
            dense
            type="textarea"
            autogrow
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps />
          <q-btn
            unelevated
            label="Сохранить"
            style="background: #ffd93c; color: #333; border-radius: 4px"
            no-caps
            :loading="editSaving"
            @click="saveEdit"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
    <!-- Диалог создания произвольного платежа -->
    <q-dialog v-model="showCreatePaymentDialog">
      <q-card style="min-width: 340px; border-radius: 8px">
        <q-card-section>
          <div class="text-subtitle1 text-weight-bold" style="color: #333">
            Новый платёж
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-select
            v-model="newPayment.employee_id"
            :options="employeeOpts"
            label="Сотрудник *"
            outlined
            dense
            emit-value
            map-options
            class="q-mb-sm"
          />
          <q-input
            v-model="newPayment.amount"
            label="Сумма *"
            outlined
            dense
            type="number"
            class="q-mb-sm"
          />
          <q-select
            v-model="newPayment.payment_type"
            :options="['Аванс', 'Доплата', 'Полная оплата']"
            label="Тип выплаты"
            outlined
            dense
            class="q-mb-sm"
          />
          <q-input
            v-model="newPayment.role"
            label="Роль (необязательно)"
            outlined
            dense
            class="q-mb-sm"
          />
          <q-input
            v-model="newPayment.stage_name"
            label="Стадия (необязательно)"
            outlined
            dense
            class="q-mb-sm"
          />
          <q-input
            v-model="newPayment.report_month"
            label="Месяц отчёта"
            outlined
            dense
            type="month"
            class="q-mb-sm"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps />
          <q-btn
            unelevated
            color="positive"
            label="Создать"
            no-caps
            @click="createPayment"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { paymentsApi, salariesApi, employeesApi } from 'src/services/api'
import { api } from 'src/boot/axios'
import { useReferencesStore } from 'src/stores/references'
import { usePermission } from 'src/composables/usePermission'
import { useOptimistic } from 'src/composables/useOptimistic'

const { can, isSuperuser } = usePermission()
const { optimistic } = useOptimistic()

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
const showEditDialog = ref(false)
const editSaving = ref(false)
const editPay = ref({ id: null, employee_name: '', final_amount: null, report_month: '', payment_type: '', comment: '', source: '' })
const showCreatePaymentDialog = ref(false)
const newPayment = ref({
  employee_id: null,
  amount: '',
  payment_type: 'Полная оплата',
  stage_name: '',
  role: '',
  report_month: '',
  contract_id: null,
  crm_card_id: null,
})
// Состояние развёрнутости групп (ключ — employeeId, значение — bool)
const expandedGroups = ref({})
const editPaymentTypeOpts = [
  { label: 'Индивидуальный', value: 'Индивидуальный' },
  { label: 'Шаблонный', value: 'Шаблонный' },
  { label: 'Авторский надзор', value: 'Авторский надзор' },
  { label: 'Оклад', value: 'Оклад' },
]

const paymentTabs = [
  { label: 'Все', value: 'all' }, { label: 'Инд.', value: 'individual' },
  { label: 'Шабл.', value: 'template' }, { label: 'Надзор', value: 'supervision' },
  { label: 'Оклады', value: 'salary' },
]

const filters = ref({ period: 'all', year: currentYear, month: new Date().getMonth() + 1, quarter: Math.ceil((new Date().getMonth() + 1) / 3), employee_id: null, status: null, address: '', role: null, agent_type: null, payment_type: null })

const paymentTypeOptions = [
  { label: 'Все типы', value: null },
  { label: 'Аванс', value: 'Аванс' },
  { label: 'Доплата', value: 'Доплата' },
  { label: 'Полная оплата', value: 'Полная оплата' },
  { label: 'Оклад', value: 'Оклад' },
]

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

function resetFilters() {
  filters.value = {
    period: 'all', year: currentYear, month: new Date().getMonth() + 1,
    quarter: Math.ceil((new Date().getMonth() + 1) / 3),
    employee_id: null, status: null, address: '', role: null, agent_type: null, payment_type: null,
  }
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
const toPayCount = computed(() => payments.value.filter(p => !p.is_paid && p.payment_status === 'to_pay').length)
const inWorkCount = computed(() => payments.value.filter(p => !p.is_paid && p.payment_status !== 'to_pay').length)

const groupedPayments = computed(() => {
  const map = {}
  for (const p of payments.value) {
    const key = p.employee_id || p.employee_name || 'unknown'
    if (!map[key]) {
      // Состояние expanded берём из реактивного объекта (по умолчанию развёрнуто)
      // eslint-disable-next-line vue/no-side-effects-in-computed-properties
      if (!(key in expandedGroups.value)) expandedGroups.value[key] = true
      map[key] = { employeeId: key, name: p.employee_name || 'Без исполнителя', role: p.role || p.position || '', initial: (p.employee_name || '?')[0], total: 0, items: [] }
    }
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
  if (p.payment_status === 'to_pay') return { background: '#FFF8E1' }
  return {}
}

async function recalculatePayments() {
  $q.dialog({
    title: 'Пересчёт по тарифам',
    message: 'Пересчитать все платежи по текущим тарифам? Это обновит calculated_amount для всех незакрытых платежей.',
    cancel: { label: 'Отмена', flat: true, noCaps: true },
    ok: { label: 'Пересчитать', noCaps: true, color: 'warning' },
  }).onOk(async () => {
    try {
      await api.post('/api/v1/payments/recalculate')
      $q.notify({ type: 'positive', message: 'Пересчёт выполнен' })
      loadData()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка пересчёта' })
    }
  })
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
    // Статус фильтруем на клиенте — серверный is_paid ненадёжен (NULL vs false)
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
    // Фильтр по статусу (серверные значения: 'paid', 'to_pay', 'pending'/null)
    if (filters.value.status === 'in_work') filtered = filtered.filter(p => !p.is_paid && p.payment_status !== 'paid' && p.payment_status !== 'to_pay')
    else if (filters.value.status === 'to_pay') filtered = filtered.filter(p => !p.is_paid && p.payment_status === 'to_pay')
    else if (filters.value.status === 'paid') filtered = filtered.filter(p => p.is_paid || p.payment_status === 'paid')
    // Фильтр по типу выплаты
    if (filters.value.payment_type) {
      filtered = filtered.filter(p => p.payment_type === filters.value.payment_type || p.payment_subtype === filters.value.payment_type)
    }

    payments.value = filtered
  } catch { payments.value = [] } finally { loading.value = false }
}

async function undoPaid(p) {
  $q.dialog({ title: 'Снять статус оплаты?', message: p.employee_name, cancel: { label: 'Нет', flat: true, noCaps: true }, ok: { label: 'Да', noCaps: true, color: 'negative' } }).onOk(async () => {
    try {
      if (p.source === 'Оклад') await salariesApi.update(p.id, { payment_status: 'pending' })
      else if (p.id) await paymentsApi.update(p.id, { payment_status: 'pending', is_paid: false })
      p.is_paid = false
      p.payment_status = 'pending'
      $q.notify({ type: 'info', message: 'Статус оплаты снят' })
    } catch (err) { const d = err.response?.data?.detail; $q.notify({ type: 'negative', message: typeof d === 'string' ? d : 'Ошибка' }) }
  })
}

async function markPaid(p) {
  // Оптимистичное обновление — мгновенно меняем статус и цвет
  await optimistic(
    () => {
      const snapshot = { is_paid: p.is_paid, payment_status: p.payment_status }
      p.is_paid = true
      p.payment_status = 'paid'
      return snapshot
    },
    () => {
      if (p.source === 'Оклад') return salariesApi.update(p.id, { payment_status: 'paid' })
      if (p.id) return paymentsApi.markPaid(p.id, p.employee_id)
      return Promise.resolve()
    },
    (snapshot) => {
      p.is_paid = snapshot.is_paid
      p.payment_status = snapshot.payment_status
    },
    'Оплачено',
  )
}

async function setPayStatus(p) {
  try {
    // Toggle: если уже к оплате (есть report_month) → снять (убрать report_month)
    if (p.report_month) {
      if (p.source === 'Оклад') await salariesApi.update(p.id, { report_month: '', payment_status: 'pending' })
      else if (p.id) await paymentsApi.update(p.id, { payment_status: 'pending', report_month: '' })
      p.report_month = null
      p.payment_status = 'pending'
      $q.notify({ type: 'info', message: 'Статус снят' })
    } else {
      const now = new Date()
      const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
      if (p.source === 'Оклад') await salariesApi.update(p.id, { report_month: month, payment_status: 'to_pay' })
      else if (p.id) await paymentsApi.update(p.id, { payment_status: 'to_pay', report_month: month })
      p.report_month = month
      p.payment_status = 'to_pay'
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
  // report_month передаём только если пользователь указал, иначе — статус "в работе" (pending)
  const payload = {
    employee_id: newPay.value.employee_id,
    amount: parseFloat(newPay.value.amount),
    payment_type: 'Оклад',
    payment_status: 'pending',
  }
  if (newPay.value.report_month) payload.report_month = newPay.value.report_month
  try {
    await salariesApi.create(payload)
    $q.notify({ type: 'positive', message: 'Оклад создан' }); showCreateDialog.value = false; loadData()
  } catch (err) {
    const detail = err.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : JSON.stringify(detail || 'Ошибка создания')
    $q.notify({ type: 'negative', message: msg })
  }
}

function openCreatePayment() {
  if (paymentTab.value === 'salary') {
    showCreateDialog.value = true  // Старая логика для окладов
  } else {
    showCreatePaymentDialog.value = true  // Новый диалог для произвольных платежей
  }
}

async function createPayment() {
  if (!newPayment.value.employee_id || !newPayment.value.amount) {
    $q.notify({ type: 'warning', message: 'Заполните сотрудника и сумму' })
    return
  }
  try {
    await paymentsApi.create({
      employee_id: newPayment.value.employee_id,
      calculated_amount: parseFloat(newPayment.value.amount),
      final_amount: parseFloat(newPayment.value.amount),
      payment_type: newPayment.value.payment_type,
      payment_status: 'pending',
      stage_name: newPayment.value.stage_name || null,
      role: newPayment.value.role || null,
      report_month: newPayment.value.report_month || null,
      contract_id: newPayment.value.contract_id || null,
      crm_card_id: newPayment.value.crm_card_id || null,
    })
    $q.notify({ type: 'positive', message: 'Платёж создан' })
    showCreatePaymentDialog.value = false
    newPayment.value = { employee_id: null, amount: '', payment_type: 'Полная оплата', stage_name: '', role: '', report_month: '', contract_id: null, crm_card_id: null }
    loadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка создания платежа' })
  }
}

function openEditDialog(p) {
  editPay.value = {
    id: p.id || p.salary_id,
    employee_name: p.employee_name || '',
    final_amount: p.final_amount || p.amount || 0,
    report_month: p.report_month || '',
    payment_type: p.payment_type || p.source || '',
    comment: p.comment || '',
    source: p.source || '',
  }
  showEditDialog.value = true
}

async function saveEdit() {
  if (!editPay.value.final_amount) { $q.notify({ type: 'warning', message: 'Укажите сумму' }); return }
  editSaving.value = true
  try {
    const data = {
      final_amount: parseFloat(editPay.value.final_amount),
      amount: parseFloat(editPay.value.final_amount),
      report_month: editPay.value.report_month || null,
      payment_type: editPay.value.payment_type,
      comment: editPay.value.comment || null,
    }
    if (editPay.value.source === 'Оклад') {
      await salariesApi.update(editPay.value.id, data)
    } else {
      await paymentsApi.update(editPay.value.id, data)
    }
    $q.notify({ type: 'positive', message: 'Платёж обновлён' })
    showEditDialog.value = false
    loadData()
  } catch (err) {
    const d = err.response?.data?.detail
    $q.notify({ type: 'negative', message: typeof d === 'string' ? d : JSON.stringify(d || 'Ошибка сохранения') })
  } finally { editSaving.value = false }
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
/* Единая высота фильтров */
.q-col-gutter-xs .q-field--outlined .q-field__control { min-height: 40px; height: 40px; }
/* Кнопка сбросить — ровно как фильтры */
.sal-reset-btn { font-size: 12px !important; height: 100% !important; min-height: 40px !important; border: 1px solid #bdbdbd !important; border-radius: 4px !important; min-width: 90px; padding: 0 12px !important; }
</style>
