<template>
  <q-page padding>
    <q-pull-to-refresh @refresh="onRefresh">
      <!-- Поиск -->
      <q-input
        v-model="search"
        placeholder="Поиск сотрудников..."
        outlined
        dense
        rounded
        class="q-mb-sm"
      >
        <template #prepend>
          <q-icon name="search" />
        </template>
        <template v-if="search" #append>
          <q-icon name="close" class="cursor-pointer" @click="search = ''" />
        </template>
      </q-input>
      <!-- Фильтры: отделы + роль -->
      <div class="row q-gutter-xs q-mb-xs" style="overflow-x: auto; flex-wrap: nowrap">
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
      <div class="row q-col-gutter-xs q-mb-md">
        <div class="col">
          <q-select
            v-model="roleFilter"
            :options="roleOptions"
            label="Роль"
            outlined
            dense
            clearable
            emit-value
            map-options
            style="font-size: 11px"
          />
        </div>
      </div>
      <div class="text-caption text-grey-7 q-mb-sm">
        Сотрудников: {{ filtered.length }}
      </div>

      <div v-if="loading">
        <q-card v-for="n in 5" :key="n" class="is-card q-mb-sm">
          <q-item>
            <q-item-section avatar>
              <q-skeleton type="circle" size="40px" />
            </q-item-section>
            <q-item-section><q-skeleton type="text" width="60%" /><q-skeleton type="text" width="40%" /></q-item-section>
          </q-item>
        </q-card>
      </div>

      <!-- Портрет: карточки -->
      <template v-if="!loading && !($q.screen.width > $q.screen.height)">
        <q-card v-if="filtered.length > 0" class="is-card">
          <q-list separator>
            <q-item
              v-for="emp in filtered"
              :key="emp.id"
              v-ripple
              clickable
              @click="openEmployee(emp)"
            >
              <q-item-section avatar>
                <q-avatar :color="statusColor(emp.status)" text-color="white" size="40px">
                  {{ emp.full_name ? emp.full_name[0] : '?' }}
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-medium">
                  {{ emp.full_name }}
                </q-item-label>
                <q-item-label caption>
                  {{ emp.position }}{{ emp.secondary_position ? ' / ' + emp.secondary_position : '' }}
                </q-item-label>
                <q-item-label caption>
                  {{ emp.department }}
                </q-item-label>
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
      </template>

      <!-- Ландшафт: таблица -->
      <template v-else-if="!loading && ($q.screen.width > $q.screen.height)">
        <div class="emp-landscape-header">
          <span class="emph-name">ФИО</span>
          <span class="emph-pos">Должность</span>
          <span class="emph-dept">Отдел</span>
          <span class="emph-status">Статус</span>
        </div>
        <div
          v-for="emp in filtered"
          :key="emp.id"
          class="emp-row-ls"
          @click="openEmployee(emp)"
        >
          <span class="emph-name empv-name">
            <q-avatar :color="statusColor(emp.status)" text-color="white" size="22px" style="flex-shrink:0;font-size:11px;margin-right:6px">
              {{ emp.full_name ? emp.full_name[0] : '?' }}
            </q-avatar>
            {{ emp.full_name }}
          </span>
          <span class="emph-pos empv-meta">{{ emp.position }}{{ emp.secondary_position ? ' / ' + emp.secondary_position : '' }}</span>
          <span class="emph-dept empv-meta">{{ emp.department || '—' }}</span>
          <span class="emph-status">
            <q-badge :color="statusColor(emp.status)" :label="emp.status" dense style="font-size:9px" />
          </span>
        </div>
        <div v-if="filtered.length === 0" class="text-center q-pa-xl text-grey-5">
          <q-icon name="badge" size="48px" class="q-mb-sm" />
          <div>Нет сотрудников</div>
        </div>
      </template>
    </q-pull-to-refresh>

    <q-page-sticky v-if="canCreate" position="bottom-right" :offset="[18, 80]">
      <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="showCreate = true" />
    </q-page-sticky>

    <!-- Диалог просмотра/редактирования -->
    <q-dialog v-model="showDetail" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card v-if="selected">
        <q-toolbar :style="editMode ? 'background: #ffd93c; color: #333' : 'background: white; color: #333; border-bottom: 1px solid #E0E0E0'">
          <q-btn
            flat
            round
            dense
            icon="close"
            @click="showDetail = false; editMode = false"
          />
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            {{ editMode ? 'Редактировать' : selected.full_name }}
          </q-toolbar-title>
          <q-btn
            v-if="editMode"
            label="Сохранить"
            no-caps
            :loading="saving"
            outline
            style="border: 1px solid #333; border-radius: 8px; color: #333"
            @click="saveEmployee"
          />
        </q-toolbar>

        <q-card-section style="max-height: calc(100vh - 50px); overflow-y: auto">
          <!-- Режим редактирования -->
          <template v-if="editMode">
            <q-form class="q-gutter-md">
              <q-input v-model="editForm.full_name" label="ФИО *" outlined dense />
              <q-select
                v-model="editForm.position"
                :options="positions"
                label="Должность *"
                outlined
                dense
              />
              <q-select
                v-model="editForm.secondary_position"
                :options="['', ...positions]"
                label="Доп. должность"
                outlined
                dense
              />
              <q-select
                v-model="editForm.status"
                :options="refs.employeeStatuses"
                label="Статус"
                outlined
                dense
              />
              <q-input
                v-model="editForm.phone"
                label="Телефон"
                outlined
                dense
                type="tel"
              />
              <q-input
                v-model="editForm.email"
                label="Email"
                outlined
                dense
                type="email"
              />
              <q-input v-model="editForm.address" label="Адрес проживания" outlined dense />
              <q-input
                v-model="editForm.birth_date"
                label="Дата рождения"
                outlined
                dense
                type="date"
              />
              <template v-if="isSuperuser">
                <q-separator />
                <div class="text-subtitle2 text-weight-bold">
                  Данные входа
                </div>
                <q-input v-model="editForm.login" label="Логин" outlined dense />
                <q-input
                  v-model="editForm.password"
                  label="Новый пароль (если менять)"
                  outlined
                  dense
                  type="password"
                />
              </template>
              <q-separator />
              <div class="text-subtitle2 text-weight-bold">
                Способ оплаты
              </div>
              <q-select
                v-model="editForm.payment_type"
                :options="refs.paymentTypes"
                label="Тип оплаты"
                outlined
                dense
              />
              <q-input
                v-if="editForm.payment_type === 'Наличными'"
                v-model="editForm.payment_phone"
                label="Телефон"
                outlined
                dense
              />
              <q-input
                v-if="editForm.payment_type === 'Переводом на карту'"
                v-model="editForm.payment_account"
                label="Номер счёта"
                outlined
                dense
              />
              <template v-if="editForm.payment_type === 'Переводом по реквизитам'">
                <q-input v-model="editForm.payment_bank_name" label="Банк" outlined dense />
                <q-input v-model="editForm.payment_bik" label="БИК" outlined dense />
                <q-input v-model="editForm.payment_corr_account" label="Кор. счёт" outlined dense />
              </template>
              <q-btn
                v-if="can('employees.delete') && canEditSelected"
                label="Удалить сотрудника"
                icon="delete"
                color="negative"
                flat
                no-caps
                class="full-width q-mt-md"
                @click="deleteEmployee"
              />
            </q-form>
          </template>

          <!-- Режим просмотра -->
          <template v-else>
            <!-- Профиль -->
            <div class="text-center q-mb-md">
              <div class="avatar-upload-wrap" style="display: inline-block; position: relative; cursor: pointer" @click="$refs.empPhotoInput.click()">
                <q-avatar size="64px" :color="selected.photo_url ? 'grey-2' : statusColor(selected.status)" text-color="white">
                  <img v-if="selected.photo_url" :src="selected.photo_url" style="width:100%;height:100%;object-fit:cover;border-radius:50%">
                  <span v-else class="text-h4">{{ selected.full_name ? selected.full_name[0] : '?' }}</span>
                </q-avatar>
                <div class="avatar-cam-overlay">
                  <q-spinner v-if="empPhotoUploading" size="20px" color="white" />
                  <q-icon v-else name="photo_camera" size="20px" color="white" />
                </div>
              </div>
              <input
                ref="empPhotoInput"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                style="display:none"
                @change="handleEmpPhotoUpload"
              >
              <div class="text-h6 text-weight-bold q-mt-sm" style="color: #333">
                {{ selected.full_name }}
              </div>
              <div class="text-body2" style="color: #666">
                {{ selected.position }}{{ selected.secondary_position ? ' / ' + selected.secondary_position : '' }}
              </div>
              <q-badge :color="statusColor(selected.status)" :label="selected.status" class="q-mt-xs" />
            </div>

            <!-- Контакты (ч/б иконки как у клиентов) -->
            <q-card flat bordered class="q-mb-md" style="border-radius: 8px">
              <q-list>
                <q-item>
                  <q-item-section avatar>
                    <q-btn
                      flat
                      round
                      dense
                      :icon="selected.phone ? 'phone' : 'phone_disabled'"
                      :style="{ color: selected.phone ? '#333' : '#ccc' }"
                      @click="selected.phone && call(selected.phone)"
                    />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label caption>
                      Телефон
                    </q-item-label><q-item-label :style="{ color: selected.phone ? '#333' : '#bbb' }">
                      {{ selected.phone || 'Не указан' }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section avatar>
                    <q-btn
                      flat
                      round
                      dense
                      :icon="selected.email ? 'email' : 'mail_outline'"
                      :style="{ color: selected.email ? '#333' : '#ccc' }"
                      @click="selected.email && sendEmail(selected.email)"
                    />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label caption>
                      Email
                    </q-item-label><q-item-label :style="{ color: selected.email ? '#333' : '#bbb' }">
                      {{ selected.email || 'Не указан' }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
                <q-item>
                  <q-item-section avatar>
                    <q-btn
                      flat
                      round
                      dense
                      icon="send"
                      :style="{ color: selected.telegram_user_id ? '#333' : '#ccc' }"
                    />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label caption>
                      Telegram
                    </q-item-label>
                    <q-item-label :style="{ color: selected.telegram_user_id ? '#27AE60' : '#bbb' }">
                      {{ selected.telegram_user_id ? `Подключён (ID: ${selected.telegram_user_id})` : 'Не подключён' }}
                    </q-item-label>
                  </q-item-section>
                  <q-item-section v-if="!selected.telegram_user_id" side>
                    <q-btn
                      outline
                      dense
                      size="xs"
                      label="Создать токен"
                      no-caps
                      color="grey-7"
                      style="border-radius: 4px; font-size: 10px"
                      @click="createTgToken(selected)"
                    />
                  </q-item-section>
                </q-item>
                <q-item v-if="selected.address">
                  <q-item-section avatar>
                    <q-icon name="home" style="color: #333" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label caption>
                      Адрес проживания
                    </q-item-label><q-item-label>{{ selected.address }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item v-if="selected.department">
                  <q-item-section avatar>
                    <q-icon name="business" style="color: #333" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label caption>
                      Отдел
                    </q-item-label><q-item-label>{{ selected.department }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item v-if="selected.birth_date">
                  <q-item-section avatar>
                    <q-icon name="cake" style="color: #333" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label caption>
                      Дата рождения
                    </q-item-label><q-item-label>{{ formatDate(selected.birth_date) }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-card>

            <!-- Способ оплаты -->
            <q-card
              v-if="selected.payment_type"
              flat
              bordered
              class="q-mb-md"
              style="border-radius: 8px"
            >
              <q-card-section class="q-pb-none">
                <div class="text-subtitle2 text-weight-bold">
                  Способ оплаты
                </div>
              </q-card-section>
              <q-list dense>
                <q-item>
                  <q-item-section>
                    <q-item-label caption>
                      Тип
                    </q-item-label><q-item-label>{{ selected.payment_type }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item v-if="selected.payment_phone">
                  <q-item-section>
                    <q-item-label caption>
                      Телефон
                    </q-item-label><q-item-label>{{ selected.payment_phone }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item v-if="selected.payment_account">
                  <q-item-section>
                    <q-item-label caption>
                      Счёт
                    </q-item-label><q-item-label>{{ selected.payment_account }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item v-if="selected.payment_bank_name">
                  <q-item-section>
                    <q-item-label caption>
                      Банк
                    </q-item-label><q-item-label>{{ selected.payment_bank_name }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-card>

            <!-- Действия -->
            <div class="row q-gutter-sm q-mt-md justify-center">
              <q-btn
                v-if="canEditSelected"
                unelevated
                icon="edit"
                label="Редактировать"
                no-caps
                style="background: #ffd93c; color: #333; border-radius: 8px"
                @click="startEdit"
              />
              <q-btn
                v-if="canEditSelected && selected.email"
                outline
                icon="email"
                label="Пригласить"
                no-caps
                color="grey-7"
                style="border-radius: 8px"
                @click="sendInvite(selected)"
              />
            </div>
          </template>
        </q-card-section>
      </q-card>
    </q-dialog>

    <page-dashboard :items="dashItems" />

    <!-- Диалог создания -->
    <q-dialog v-model="showCreate" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card>
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-btn
            flat
            round
            dense
            icon="close"
            @click="showCreate = false"
          />
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            Новый сотрудник
          </q-toolbar-title>
          <q-btn
            label="Сохранить"
            no-caps
            :loading="saving"
            outline
            style="border: 1px solid #333; border-radius: 8px; color: #333"
            @click="createEmployee"
          />
        </q-toolbar>
        <q-card-section style="max-height: calc(100vh - 50px); overflow-y: auto">
          <q-form ref="createForm" class="q-gutter-md">
            <q-input
              v-model="form.full_name"
              label="ФИО *"
              outlined
              dense
              :rules="[v => !!v || 'Обязательно']"
            />
            <q-select
              v-model="form.position"
              :options="positions"
              label="Должность *"
              outlined
              dense
              :rules="[v => !!v || 'Обязательно']"
            />
            <q-select
              v-model="form.secondary_position"
              :options="['', ...positions]"
              label="Доп. должность"
              outlined
              dense
            />
            <q-select
              v-model="form.status"
              :options="['активный', 'уволен', 'в резерве']"
              label="Статус"
              outlined
              dense
            />
            <q-input
              v-model="form.phone"
              label="Телефон"
              outlined
              dense
              type="tel"
            />
            <q-input
              v-model="form.email"
              label="Email *"
              outlined
              dense
              type="email"
              :rules="[v => !!v || 'Обязательно']"
            />
            <q-input v-model="form.address" label="Адрес проживания" outlined dense />
            <q-input
              v-model="form.birth_date"
              label="Дата рождения"
              outlined
              dense
              type="date"
            />
            <q-separator />
            <div class="text-subtitle2 text-weight-bold">
              Вход в систему
            </div>
            <q-input
              v-model="form.login"
              label="Логин *"
              outlined
              dense
              :rules="[v => v && v.length >= 3 || 'Минимум 3 символа']"
            />
            <q-input
              v-model="form.password"
              label="Пароль *"
              outlined
              dense
              type="password"
              :rules="[v => v && v.length >= 6 || 'Минимум 6 символов']"
            />
            <q-separator />
            <div class="text-subtitle2 text-weight-bold">
              Способ оплаты
            </div>
            <q-select
              v-model="form.payment_type"
              :options="['Наличными', 'Переводом на карту', 'Переводом по реквизитам']"
              label="Тип оплаты"
              outlined
              dense
            />
            <q-input
              v-if="form.payment_type === 'Наличными'"
              v-model="form.payment_phone"
              label="Телефон для оплаты"
              outlined
              dense
            />
            <q-input
              v-if="form.payment_type === 'Переводом на карту'"
              v-model="form.payment_account"
              label="Номер счёта"
              outlined
              dense
            />
            <template v-if="form.payment_type === 'Переводом по реквизитам'">
              <q-input v-model="form.payment_bank_name" label="Банк" outlined dense />
              <q-input v-model="form.payment_bik" label="БИК" outlined dense />
              <q-input v-model="form.payment_corr_account" label="Кор. счёт" outlined dense />
            </template>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
    <avatar-crop-dialog v-model="showEmpCrop" :src="empCropSrc" @cropped="onEmpCropped" />
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { employeesApi } from 'src/services/api'
import PageDashboard from 'src/components/PageDashboard.vue'
import AvatarCropDialog from 'src/components/AvatarCropDialog.vue'
import { useReferencesStore } from 'src/stores/references'
import { usePermission } from 'src/composables/usePermission'

const $q = useQuasar()
const refs = useReferencesStore()
const { can, isSuperuser } = usePermission()
const canCreate = computed(() => can('employees.create'))

// Админ. отдел может редактировать только Руководитель студии (как десктоп employees_tab.py:866-882)
const ADMIN_POSITIONS = ['Руководитель студии', 'Старший менеджер проектов', 'СДП', 'ГАП']
const canEditSelected = computed(() => {
  if (!can('employees.update')) return false
  if (!selected.value) return false
  // Если сотрудник из админ.отдела — нужно право access.admin
  if (ADMIN_POSITIONS.includes(selected.value.position)) {
    return isSuperuser.value // Только руководитель студии
  }
  return true
})

const dashItems = computed(() => {
  const all = employees.value
  const active = all.filter(e => e.status === 'активный').length
  return [
    { label: 'Всего', value: all.length },
    { label: 'Активных', value: active, color: '#27AE60' },
    { label: 'Отделов', value: departments.value.length - 1, color: '#3498DB' },
  ]
})
const employees = ref([])
const loading = ref(false)
const saving = ref(false)
const activeDept = ref('Все отделы')
const search = ref('')
const roleFilter = ref(null)

const roleOptions = computed(() => {
  const roles = new Set(employees.value.map(e => e.position).filter(Boolean))
  return [...roles].sort().map(r => ({ label: r, value: r }))
})
const selected = ref(null)
const showDetail = ref(false)
const empPhotoUploading = ref(false)
const showEmpCrop = ref(false)
const empCropSrc = ref(null)
const showCreate = ref(false)
const editMode = ref(false)
const createForm = ref(null)

const positions = refs.positions
const editForm = ref({})

const form = ref({
  full_name: '', position: '', secondary_position: '', status: 'активный',
  phone: '', email: '', address: '', birth_date: '', login: '', password: '',
  payment_type: '', payment_phone: '', payment_account: '',
  payment_bank_name: '', payment_bik: '', payment_corr_account: '',
})

const departments = computed(() => {
  const depts = new Set(employees.value.map(e => e.department).filter(Boolean))
  return ['Все отделы', ...depts]
})

const filtered = computed(() => {
  let result = employees.value
  if (activeDept.value !== 'Все отделы') result = result.filter(e => e.department === activeDept.value)
  if (roleFilter.value) result = result.filter(e => e.position === roleFilter.value || e.secondary_position === roleFilter.value)
  if (search.value) {
    const q = search.value.toLowerCase()
    result = result.filter(e => (e.full_name || '').toLowerCase().includes(q) || (e.position || '').toLowerCase().includes(q) || (e.phone || '').includes(q))
  }
  return result
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
function sendEmail(email) { window.location.href = `mailto:${email}` }

async function createTgToken(emp) {
  try {
    const { data } = await employeesApi.createTelegramToken(emp.id)
    $q.notify({ type: 'positive', message: data?.token ? `Токен: ${data.token}` : 'Токен создан' })
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
}

async function sendInvite(emp) {
  try {
    await employeesApi.sendInvite(emp.id)
    $q.notify({ type: 'positive', message: 'Приглашение отправлено' })
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
}

function filterByDept(dept) { activeDept.value = dept }

function openEmployee(emp) {
  selected.value = emp
  showDetail.value = true
  editMode.value = false
}

function handleEmpPhotoUpload(e) {
  const file = e.target?.files?.[0]
  if (!file || !selected.value) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    empCropSrc.value = ev.target.result
    showEmpCrop.value = true
  }
  reader.readAsDataURL(file)
  e.target.value = ''
}

async function onEmpCropped(blob) {
  if (!selected.value) return
  empPhotoUploading.value = true
  try {
    const { data } = await employeesApi.uploadPhoto(selected.value.id, blob)
    selected.value = { ...selected.value, photo_url: data.photo_url }
    $q.notify({ type: 'positive', message: 'Фото загружено' })
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки фото' })
  } finally {
    empPhotoUploading.value = false
  }
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

function startEdit() {
  editForm.value = { ...selected.value, password: '' }
  editMode.value = true
}

async function saveEmployee() {
  saving.value = true
  try {
    const data = { ...editForm.value }
    if (!data.password) delete data.password
    await employeesApi.update(selected.value.id, data)
    $q.notify({ type: 'positive', message: 'Сотрудник обновлён' })
    editMode.value = false
    showDetail.value = false
    loadEmployees()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  } finally { saving.value = false }
}

async function deleteEmployee() {
  if (!selected.value) return
  $q.dialog({
    title: 'Удалить сотрудника?',
    message: selected.value.full_name,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await employeesApi.delete(selected.value.id)
      $q.notify({ type: 'positive', message: 'Сотрудник удалён' })
      showDetail.value = false
      loadEmployees()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка удаления' })
    }
  })
}

function onRefresh(done) { loadEmployees().finally(done) }

onMounted(() => loadEmployees())
</script>

<style scoped>
.emp-landscape-header {
  display: flex;
  align-items: center;
  padding: 4px 10px;
  background: #F5F5F5;
  border: 1px solid #E0E0E0;
  border-radius: 8px 8px 0 0;
  font-size: 10px;
  font-weight: bold;
  color: #888;
  gap: 6px;
}
.emp-row-ls {
  display: flex;
  align-items: center;
  padding: 5px 10px;
  border: 1px solid #E0E0E0;
  border-top: none;
  gap: 6px;
  cursor: pointer;
  background: #fff;
  min-height: 34px;
}
.emp-row-ls:last-of-type { border-radius: 0 0 8px 8px; }
.emp-row-ls:hover { background: #F9F9F9; }
.emph-name   { flex: 1; min-width: 0; display: flex; align-items: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.emph-pos    { width: 180px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
.emph-dept   { width: 110px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
.emph-status { width: 60px; flex-shrink: 0; }
.empv-name { font-size: 12px; font-weight: 500; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empv-meta { color: #666; }
</style>
