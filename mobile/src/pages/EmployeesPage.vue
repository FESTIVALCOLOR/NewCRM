<template>
  <q-page padding>
    <q-pull-to-refresh @refresh="onRefresh">
      <!-- Фильтры по отделам -->
      <div class="row q-gutter-xs q-mb-md" style="overflow-x: auto; flex-wrap: nowrap">
        <q-btn
          v-for="dept in departments"
          :key="dept"
          :label="dept"
          :outline="activeDept !== dept"
          :unelevated="activeDept === dept"
          :color="activeDept === dept ? 'accent' : 'grey-7'"
          :text-color="activeDept === dept ? 'dark' : undefined"
          dense
          no-caps
          size="sm"
          @click="filterByDept(dept)"
        />
      </div>

      <div class="text-caption text-grey-7 q-mb-sm">Сотрудников: {{ filtered.length }}</div>

      <div v-if="loading">
        <q-card class="is-card q-mb-sm" v-for="n in 5" :key="n">
          <q-item><q-item-section avatar><q-skeleton type="circle" size="40px" /></q-item-section>
          <q-item-section><q-skeleton type="text" width="60%" /><q-skeleton type="text" width="40%" /></q-item-section></q-item>
        </q-card>
      </div>

      <q-card class="is-card" v-else-if="filtered.length > 0">
        <q-list separator>
          <q-item v-for="emp in filtered" :key="emp.id" clickable v-ripple @click="openEmployee(emp)">
            <q-item-section avatar>
              <q-avatar :color="statusColor(emp.status)" text-color="white" size="40px">
                {{ emp.full_name ? emp.full_name[0] : '?' }}
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-medium">{{ emp.full_name }}</q-item-label>
              <q-item-label caption>
                {{ emp.position }}{{ emp.secondary_position ? ' / ' + emp.secondary_position : '' }}
              </q-item-label>
              <q-item-label caption>{{ emp.department }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge
                :color="statusColor(emp.status)"
                :label="emp.status"
                dense
              />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <div v-else class="text-center q-pa-xl text-grey-5">
        <q-icon name="badge" size="48px" class="q-mb-sm" />
        <div>Нет сотрудников</div>
      </div>
    </q-pull-to-refresh>

    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-btn fab icon="person_add" color="accent" text-color="dark" @click="showCreate = true" />
    </q-page-sticky>

    <!-- Диалог просмотра/редактирования -->
    <q-dialog v-model="showDetail" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card v-if="selected">
        <q-toolbar class="bg-white text-dark" style="border-bottom: 1px solid #E0E0E0">
          <q-btn flat round dense icon="close" @click="showDetail = false" />
          <q-toolbar-title>{{ selected.full_name }}</q-toolbar-title>
          <q-btn flat icon="edit" @click="editMode = !editMode" :color="editMode ? 'accent' : 'grey-7'" />
        </q-toolbar>

        <q-card-section style="max-height: calc(100vh - 50px); overflow-y: auto">
          <!-- Профиль -->
          <div class="text-center q-mb-md">
            <q-avatar size="64px" :color="statusColor(selected.status)" text-color="white">
              <span class="text-h4">{{ selected.full_name ? selected.full_name[0] : '?' }}</span>
            </q-avatar>
            <div class="text-h6 text-weight-bold q-mt-sm">{{ selected.full_name }}</div>
            <div class="text-body2 text-grey-7">{{ selected.position }}</div>
            <q-badge :color="statusColor(selected.status)" :label="selected.status" class="q-mt-xs" />
          </div>

          <!-- Контакты -->
          <q-card flat bordered class="q-mb-md" style="border-radius: 10px">
            <q-list dense>
              <q-item v-if="selected.phone" clickable @click="call(selected.phone)">
                <q-item-section avatar><q-icon name="phone" color="positive" /></q-item-section>
                <q-item-section><q-item-label caption>Телефон</q-item-label><q-item-label>{{ selected.phone }}</q-item-label></q-item-section>
              </q-item>
              <q-item v-if="selected.email">
                <q-item-section avatar><q-icon name="email" color="info" /></q-item-section>
                <q-item-section><q-item-label caption>Email</q-item-label><q-item-label>{{ selected.email }}</q-item-label></q-item-section>
              </q-item>
              <q-item v-if="selected.department">
                <q-item-section avatar><q-icon name="business" color="grey-7" /></q-item-section>
                <q-item-section><q-item-label caption>Отдел</q-item-label><q-item-label>{{ selected.department }}</q-item-label></q-item-section>
              </q-item>
              <q-item v-if="selected.birth_date">
                <q-item-section avatar><q-icon name="cake" color="warning" /></q-item-section>
                <q-item-section><q-item-label caption>Дата рождения</q-item-label><q-item-label>{{ formatDate(selected.birth_date) }}</q-item-label></q-item-section>
              </q-item>
              <q-item v-if="selected.is_online !== undefined">
                <q-item-section avatar><q-icon :name="selected.is_online ? 'circle' : 'radio_button_unchecked'" :color="selected.is_online ? 'positive' : 'grey-5'" size="16px" /></q-item-section>
                <q-item-section><q-item-label caption>Статус</q-item-label><q-item-label>{{ selected.is_online ? 'Онлайн' : 'Не в сети' }}</q-item-label></q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Способ оплаты -->
          <q-card flat bordered class="q-mb-md" style="border-radius: 10px" v-if="selected.payment_type">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold">Способ оплаты</div></q-card-section>
            <q-list dense>
              <q-item>
                <q-item-section><q-item-label caption>Тип</q-item-label><q-item-label>{{ selected.payment_type }}</q-item-label></q-item-section>
              </q-item>
              <q-item v-if="selected.payment_phone">
                <q-item-section><q-item-label caption>Телефон</q-item-label><q-item-label>{{ selected.payment_phone }}</q-item-label></q-item-section>
              </q-item>
              <q-item v-if="selected.payment_account">
                <q-item-section><q-item-label caption>Счёт</q-item-label><q-item-label>{{ selected.payment_account }}</q-item-label></q-item-section>
              </q-item>
              <q-item v-if="selected.payment_bank_name">
                <q-item-section><q-item-label caption>Банк</q-item-label><q-item-label>{{ selected.payment_bank_name }}</q-item-label></q-item-section>
              </q-item>
            </q-list>
          </q-card>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Диалог создания -->
    <q-dialog v-model="showCreate" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card>
        <q-toolbar class="bg-white text-dark" style="border-bottom: 1px solid #E0E0E0">
          <q-btn flat round dense icon="close" @click="showCreate = false" />
          <q-toolbar-title>Новый сотрудник</q-toolbar-title>
          <q-btn flat label="Сохранить" no-caps @click="createEmployee" :loading="saving" color="positive" />
        </q-toolbar>
        <q-card-section style="max-height: calc(100vh - 50px); overflow-y: auto">
          <q-form ref="createForm" class="q-gutter-md">
            <q-input v-model="form.full_name" label="ФИО *" outlined dense :rules="[v => !!v || 'Обязательно']" />
            <q-select v-model="form.position" :options="positions" label="Должность *" outlined dense :rules="[v => !!v || 'Обязательно']" />
            <q-select v-model="form.secondary_position" :options="['', ...positions]" label="Доп. должность" outlined dense />
            <q-select v-model="form.status" :options="['активный', 'уволен', 'в резерве']" label="Статус" outlined dense />
            <q-input v-model="form.phone" label="Телефон" outlined dense type="tel" />
            <q-input v-model="form.email" label="Email *" outlined dense type="email" :rules="[v => !!v || 'Обязательно']" />
            <q-input v-model="form.birth_date" label="Дата рождения" outlined dense type="date" />
            <q-separator />
            <div class="text-subtitle2 text-weight-bold">Вход в систему</div>
            <q-input v-model="form.login" label="Логин *" outlined dense :rules="[v => v && v.length >= 3 || 'Минимум 3 символа']" />
            <q-input v-model="form.password" label="Пароль *" outlined dense type="password" :rules="[v => v && v.length >= 6 || 'Минимум 6 символов']" />
            <q-separator />
            <div class="text-subtitle2 text-weight-bold">Способ оплаты</div>
            <q-select v-model="form.payment_type" :options="['Наличными', 'Переводом на карту', 'Переводом по реквизитам']" label="Тип оплаты" outlined dense />
            <q-input v-if="form.payment_type === 'Наличными'" v-model="form.payment_phone" label="Телефон для оплаты" outlined dense />
            <q-input v-if="form.payment_type === 'Переводом на карту'" v-model="form.payment_account" label="Номер счёта" outlined dense />
            <template v-if="form.payment_type === 'Переводом по реквизитам'">
              <q-input v-model="form.payment_bank_name" label="Банк" outlined dense />
              <q-input v-model="form.payment_bik" label="БИК" outlined dense />
              <q-input v-model="form.payment_corr_account" label="Кор. счёт" outlined dense />
            </template>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { employeesApi } from 'src/services/api'

const $q = useQuasar()
const employees = ref([])
const loading = ref(false)
const saving = ref(false)
const activeDept = ref('Все отделы')
const selected = ref(null)
const showDetail = ref(false)
const showCreate = ref(false)
const editMode = ref(false)
const createForm = ref(null)

const positions = [
  'Руководитель студии', 'Старший менеджер проектов', 'СДП', 'ГАП',
  'Менеджер', 'Замерщик', 'Дизайнер', 'Чертёжник', 'ДАН'
]

const form = ref({
  full_name: '', position: '', secondary_position: '', status: 'активный',
  phone: '', email: '', birth_date: '', login: '', password: '',
  payment_type: '', payment_phone: '', payment_account: '',
  payment_bank_name: '', payment_bik: '', payment_corr_account: ''
})

const departments = computed(() => {
  const depts = new Set(employees.value.map(e => e.department).filter(Boolean))
  return ['Все отделы', ...depts]
})

const filtered = computed(() => {
  if (activeDept.value === 'Все отделы') return employees.value
  return employees.value.filter(e => e.department === activeDept.value)
})

function statusColor(status) {
  if (status === 'активный') return 'positive'
  if (status === 'уволен') return 'negative'
  return 'warning'
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('ru-RU')
}

function call(phone) { window.location.href = `tel:${phone.replace(/[^\d+]/g, '')}` }

function filterByDept(dept) { activeDept.value = dept }

function openEmployee(emp) {
  selected.value = emp
  showDetail.value = true
  editMode.value = false
}

async function loadEmployees() {
  loading.value = true
  try {
    const { data } = await employeesApi.getList()
    employees.value = data
  } catch { employees.value = [] }
  finally { loading.value = false }
}

async function createEmployee() {
  const valid = await createForm.value?.validate()
  if (!valid) return
  saving.value = true
  try {
    await employeesApi.create(form.value)
    $q.notify({ type: 'positive', message: 'Сотрудник создан' })
    showCreate.value = false
    loadEmployees()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  } finally { saving.value = false }
}

function onRefresh(done) { loadEmployees().finally(done) }

onMounted(() => loadEmployees())
</script>
