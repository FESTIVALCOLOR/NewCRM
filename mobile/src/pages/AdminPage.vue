<template>
  <q-page padding>
    <q-tabs
      v-model="tab"
      dense
      active-color="dark"
      indicator-color="accent"
      no-caps
      class="q-mb-md"
      style="color: #666"
      align="left"
    >
      <q-tab name="rates" label="Тарифы" />
      <q-tab name="agents" label="Агенты" />
      <q-tab name="cities" label="Города" />
      <q-tab name="roles" label="Роли" />
      <q-tab name="normdays" label="Нормодни" />
      <q-tab name="telegram" label="Telegram/Email" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated class="bg-transparent">
      <!-- ТАРИФЫ -->
      <q-tab-panel name="rates" class="q-pa-none">
        <q-tabs
          v-model="rateTab"
          dense
          active-color="dark"
          indicator-color="accent"
          no-caps
          class="q-mb-sm"
          style="color: #888"
          align="left"
        >
          <q-tab name="individual" label="Индивид." />
          <q-tab name="template" label="Шаблон." />
          <q-tab name="supervision" label="Надзор" />
          <q-tab name="surveyor" label="Замерщик" />
        </q-tabs>

        <q-card v-for="rate in filteredRates" :key="rate.id" class="is-card q-mb-xs">
          <q-card-section class="q-pa-sm">
            <div class="row items-center justify-between">
              <div style="flex: 1">
                <div class="text-weight-bold" style="font-size: 12px; color: #333">
                  {{ rate.role }}
                </div>
                <div class="text-caption" style="color: #888">
                  <span v-if="rate.stage_name">{{ rate.stage_name }}</span>
                  <span v-if="rate.city"> | {{ rate.city }}</span>
                  <span v-if="rate.area_from"> | {{ rate.area_from }}-{{ rate.area_to }} м²</span>
                </div>
              </div>
              <div class="text-weight-bold q-mr-sm" style="color: #333">
                <span v-if="rate.rate_per_m2">{{ rate.rate_per_m2 }} ₽/м²</span>
                <span v-else-if="rate.fixed_price">{{ rate.fixed_price }} ₽</span>
                <span v-else-if="rate.surveyor_price">{{ rate.surveyor_price }} ₽</span>
              </div>
              <div>
                <q-btn
                  flat
                  dense
                  size="xs"
                  icon="edit"
                  color="grey-7"
                  @click="editRate(rate)"
                />
                <q-btn
                  flat
                  dense
                  size="xs"
                  icon="delete"
                  color="negative"
                  @click="deleteRate(rate)"
                />
              </div>
            </div>
          </q-card-section>
        </q-card>
        <div v-if="filteredRates.length === 0" class="text-center q-pa-md" style="color: #999">
          Нет тарифов
        </div>
        <q-page-sticky position="bottom-right" :offset="[18, 18]">
          <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="addRate" />
        </q-page-sticky>
      </q-tab-panel>

      <!-- АГЕНТЫ -->
      <q-tab-panel name="agents" class="q-pa-none">
        <q-card class="is-card">
          <q-list separator>
            <q-item v-for="agent in refs.agents" :key="agent.id">
              <q-item-section avatar>
                <q-avatar size="32px" :style="{ background: agent.color || '#95A5A6' }" text-color="white">
                  {{ agent.name?.[0] }}
                </q-avatar>
              </q-item-section>
              <q-item-section style="color: #333">
                {{ agent.name }}
              </q-item-section>
              <q-item-section side>
                <div class="row items-center q-gutter-xs">
                  <input type="color" :value="agent.color || '#95A5A6'" style="width: 28px; height: 28px; border: none; cursor: pointer; border-radius: 4px" @change="updateAgentColor(agent, $event.target.value)">
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="delete"
                    color="negative"
                    @click="deleteAgent(agent)"
                  />
                </div>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
        <q-page-sticky position="bottom-right" :offset="[18, 18]">
          <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="addAgent" />
        </q-page-sticky>
      </q-tab-panel>

      <!-- ГОРОДА -->
      <q-tab-panel name="cities" class="q-pa-none">
        <q-card class="is-card">
          <q-list separator>
            <q-item v-for="city in citiesFull" :key="city.id">
              <q-item-section avatar>
                <q-icon name="location_on" color="grey-7" />
              </q-item-section>
              <q-item-section style="color: #333">
                {{ city.name }}
              </q-item-section>
              <q-item-section side>
                <div class="row items-center q-gutter-xs">
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="edit"
                    color="grey-7"
                    @click="editCity(city)"
                  />
                  <q-btn
                    flat
                    dense
                    size="xs"
                    icon="delete"
                    color="negative"
                    @click="deleteCity(city)"
                  />
                </div>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
        <q-page-sticky position="bottom-right" :offset="[18, 18]">
          <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="addCity" />
        </q-page-sticky>
      </q-tab-panel>

      <!-- РОЛИ — права по блокам -->
      <q-tab-panel name="roles" class="q-pa-none">
        <q-card class="is-card q-mb-md">
          <q-card-section class="q-pb-none">
            <div class="text-subtitle2 text-weight-bold" style="color: #333">
              Матрица ролей
            </div>
          </q-card-section>
          <q-list separator>
            <q-item
              v-for="role in rolesList"
              :key="role"
              v-ripple
              clickable
              @click="viewRolePermissions(role)"
            >
              <q-item-section avatar>
                <q-icon name="security" color="grey-7" />
              </q-item-section>
              <q-item-section style="color: #333">
                {{ role }}
              </q-item-section>
              <q-item-section side>
                <q-icon name="chevron_right" color="grey-5" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>
      </q-tab-panel>

      <!-- НОРМОДНИ -->
      <q-tab-panel name="normdays" class="q-pa-none">
        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col-6">
            <q-select
              v-model="ndProjectType"
              :options="['Индивидуальный', 'Шаблонный']"
              label="Тип"
              outlined
              dense
              @update:model-value="loadNormDays"
            />
          </div>
          <div class="col-6">
            <q-select
              v-model="ndSubtype"
              :options="refs.projectSubtypes"
              label="Подтип"
              outlined
              dense
              @update:model-value="loadNormDays"
            />
          </div>
        </div>
        <q-card class="is-card">
          <q-list v-if="normDays.length > 0" dense separator>
            <q-item v-for="nd in normDays" :key="nd.sort_order" :class="{ 'bg-grey-2': !nd.stage_code?.includes('.') }">
              <q-item-section>
                <q-item-label style="font-size: 11px; color: #333" :class="{ 'text-weight-bold': !nd.stage_code?.includes('.') }">
                  {{ nd.stage_name }}
                </q-item-label>
                <q-item-label caption style="color: #888">
                  {{ nd.executor_role }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <div class="text-weight-bold" style="color: #333; font-size: 12px">
                  {{ nd.base_norm_days || nd.norm_days || '—' }} дн.
                </div>
              </q-item-section>
            </q-item>
          </q-list>
          <q-card-section v-else class="text-center" style="color: #999">
            <q-spinner v-if="ndLoading" size="30px" color="accent" />
            <div v-else>
              Выберите тип и подтип проекта
            </div>
          </q-card-section>
        </q-card>
      </q-tab-panel>

      <!-- TELEGRAM / EMAIL -->
      <q-tab-panel name="telegram" class="q-pa-none">
        <q-card class="is-card q-mb-md">
          <q-card-section>
            <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">
              Telegram
            </div>
            <div class="text-caption q-mb-md" style="color: #888">
              Управление подключением Telegram бота для уведомлений сотрудников
            </div>
            <q-btn
              unelevated
              label="Отправить тестовое уведомление"
              icon="send"
              no-caps
              style="background: #ffd93c; color: #333; border-radius: 4px"
              class="full-width q-mb-sm"
              @click="sendTestNotification"
            />
          </q-card-section>
        </q-card>

        <q-card class="is-card q-mb-md">
          <q-card-section>
            <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">
              Приглашения сотрудникам
            </div>
            <div class="text-caption q-mb-md" style="color: #888">
              Отправить welcome-email с ссылкой на Telegram бот и временным паролем
            </div>
            <q-select
              v-model="inviteEmployeeId"
              :options="inviteEmployeeOpts"
              label="Сотрудник"
              outlined
              dense
              emit-value
              map-options
              class="q-mb-sm"
            />
            <q-btn
              unelevated
              label="Отправить приглашение"
              icon="mail"
              no-caps
              style="background: #27AE60; color: white; border-radius: 4px"
              class="full-width"
              :disable="!inviteEmployeeId"
              @click="sendInvite"
            />
          </q-card-section>
        </q-card>

        <!-- Токены сотрудников для ручного подключения -->
        <q-card class="is-card q-mb-md">
          <q-card-section>
            <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">
              Telegram-токены сотрудников
            </div>
            <div class="text-caption q-mb-md" style="color: #888">
              Если сотрудник не может открыть ссылку — отправьте ему инструкцию вручную
            </div>
            <q-select
              v-model="tgInfoEmployeeId"
              :options="inviteEmployeeOpts"
              label="Выберите сотрудника"
              outlined
              dense
              emit-value
              map-options
              class="q-mb-sm"
              @update:model-value="loadTgInfo"
            />
            <template v-if="tgInfo">
              <q-card flat bordered class="q-pa-sm q-mb-sm" style="border-radius: 8px">
                <div class="row items-center q-mb-xs">
                  <q-icon :name="tgInfo.telegram_connected ? 'check_circle' : 'radio_button_unchecked'" :color="tgInfo.telegram_connected ? 'positive' : 'warning'" size="20px" class="q-mr-xs" />
                  <span style="font-size: 12px; color: #333">{{ tgInfo.telegram_connected ? 'Telegram подключён' : 'Не подключён' }}</span>
                </div>
                <template v-if="tgInfo.token_command">
                  <div class="text-caption q-mb-xs" style="color: #888">
                    Инструкция для сотрудника:
                  </div>
                  <div style="background: #F5F5F5; border-radius: 6px; padding: 8px; font-family: monospace; font-size: 11px; color: #333; word-break: break-all">
                    Откройте Telegram → найдите бота @festival_color_crm_bot → отправьте:<br>
                    <strong>{{ tgInfo.token_command }}</strong>
                  </div>
                  <div class="row q-gutter-xs q-mt-sm">
                    <q-btn
                      flat
                      dense
                      size="sm"
                      icon="content_copy"
                      label="Копировать команду"
                      no-caps
                      color="grey-7"
                      @click="copyToClipboard(tgInfo.token_command)"
                    />
                    <q-btn
                      flat
                      dense
                      size="sm"
                      icon="link"
                      label="Копировать tg://"
                      no-caps
                      color="grey-7"
                      @click="copyToClipboard(tgInfo.tg_link)"
                    />
                  </div>
                </template>
                <div v-else class="text-caption" style="color: #999">
                  {{ tgInfo.telegram_connected ? 'Уже подключён, токен не нужен' : 'Токен не создан — отправьте приглашение' }}
                </div>
              </q-card>
            </template>
          </q-card-section>
        </q-card>

        <q-card class="is-card">
          <q-card-section>
            <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">
              Email сервис
            </div>
            <div class="text-caption" style="color: #888">
              SMTP настроен на сервере.
            </div>
          </q-card-section>
        </q-card>
      </q-tab-panel>
    </q-tab-panels>

    <!-- Диалог прав роли — ПО БЛОКАМ -->
    <q-dialog v-model="showRoleDialog" maximized transition-show="slide-up" transition-hide="slide-down">
      <q-card>
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-btn
            flat
            round
            dense
            icon="close"
            @click="showRoleDialog = false"
          />
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            {{ selectedRole }}
          </q-toolbar-title>
          <q-btn
            label="Сохранить"
            no-caps
            outline
            style="border: 1px solid #333; border-radius: 8px; color: #333"
            @click="saveRolePermissions"
          />
        </q-toolbar>
        <q-card-section style="max-height: calc(100vh - 50px); overflow-y: auto">
          <div v-for="(perms, group) in permissionsByGroup" :key="group" class="q-mb-md">
            <div class="text-subtitle2 text-weight-bold q-mb-xs" style="color: #333; border-bottom: 1px solid #E0E0E0; padding-bottom: 4px">
              {{ group }}
            </div>
            <q-list dense>
              <q-item v-for="perm in perms" :key="perm.name" tag="label" dense>
                <q-item-section>
                  <q-item-label style="font-size: 11px; color: #333">
                    {{ perm.description || perm.name }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-toggle v-model="perm.granted" color="accent" dense />
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Диалог редактирования тарифа -->
    <q-dialog v-model="showRateDialog">
      <q-card style="min-width: 320px">
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            {{ editingRate?.id ? 'Редактировать' : 'Новый' }} тариф
          </q-toolbar-title>
        </q-toolbar>
        <q-card-section v-if="editingRate">
          <!-- Тариф замерщика: только цена и город -->
          <template v-if="rateTab === 'surveyor' || editingRate.surveyor_price">
            <q-input
              v-model.number="editingRate.surveyor_price"
              label="Цена замера (₽)"
              outlined
              dense
              type="number"
              class="q-mb-sm"
            />
            <q-select
              v-model="editingRate.city"
              :options="refs.cities"
              label="Город"
              outlined
              dense
              clearable
              class="q-mb-sm"
            />
          </template>
          <!-- Остальные тарифы -->
          <template v-else>
            <q-select
              v-model="editingRate.role"
              :options="refs.positions"
              label="Роль"
              outlined
              dense
              class="q-mb-sm"
            />
            <q-input
              v-model.number="editingRate.rate_per_m2"
              label="₽/м²"
              outlined
              dense
              type="number"
              class="q-mb-sm"
            />
            <q-input
              v-model.number="editingRate.fixed_price"
              label="Фикс. цена"
              outlined
              dense
              type="number"
              class="q-mb-sm"
            />
            <q-input
              v-model="editingRate.stage_name"
              label="Стадия"
              outlined
              dense
              class="q-mb-sm"
            />
            <q-select
              v-model="editingRate.city"
              :options="refs.cities"
              label="Город"
              outlined
              dense
              clearable
              class="q-mb-sm"
            />
          </template>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps />
          <q-btn
            unelevated
            label="Сохранить"
            style="background: #ffd93c; color: #333; border-radius: 8px"
            no-caps
            @click="saveRate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'
import { useReferencesStore } from 'src/stores/references'

const $q = useQuasar()
const refs = useReferencesStore()
const tab = ref('rates')
const rateTab = ref('individual')
const rates = ref([])
const normDays = ref([])
const ndLoading = ref(false)
const ndProjectType = ref('Индивидуальный')
const ndSubtype = ref('Полный (с 3д визуализацией)')
const showRoleDialog = ref(false)
const selectedRole = ref('')
const rolePermissions = ref([])
const showRateDialog = ref(false)
const editingRate = ref(null)

const citiesFull = ref([])
const rolesList = refs.positions
const inviteEmployeeId = ref(null)
const inviteEmployeeOpts = ref([])
const tgInfoEmployeeId = ref(null)
const tgInfo = ref(null)

// Блоки прав как в десктопе
const PERMISSION_GROUPS = {
  'Доступ к страницам': ['access.clients', 'access.contracts', 'access.crm', 'access.supervision', 'access.reports', 'access.employees', 'access.salaries', 'access.employee_reports', 'access.admin', 'access.dashboards'],
  'Сотрудники': ['employees.create', 'employees.update', 'employees.delete'],
  'Клиенты': ['clients.create', 'clients.view', 'clients.update', 'clients.delete'],
  'Договоры': ['contracts.create', 'contracts.view', 'contracts.update', 'contracts.delete'],
  'CRM': ['crm_cards.update', 'crm_cards.move', 'crm_cards.delete', 'crm_cards.assign_executor', 'crm_cards.delete_executor', 'crm_cards.reset_stages', 'crm_cards.reset_approval', 'crm_cards.complete_approval', 'crm_cards.reset_designer', 'crm_cards.reset_draftsman', 'crm_cards.files_upload', 'crm_cards.files_delete', 'crm_cards.deadlines', 'crm_cards.payments'],
  'Надзор': ['supervision.update', 'supervision.move', 'supervision.pause_resume', 'supervision.complete_stage', 'supervision.delete_order', 'supervision.assign_executor', 'supervision.files_upload', 'supervision.files_delete', 'supervision.deadlines', 'supervision.payments'],
  'Платежи': ['payments.create', 'payments.update', 'payments.delete'],
  'Зарплаты': ['salaries.create', 'salaries.update', 'salaries.delete', 'salaries.mark_to_pay', 'salaries.mark_paid'],
  'Тарифы': ['rates.create', 'rates.delete'],
  'Мессенджер': ['messenger.create_chat', 'messenger.delete_chat', 'messenger.view_chat', 'messenger.manage_scripts'],
  'Уведомления': ['notifications.settings_projects', 'notifications.settings_duplication', 'notifications.settings_supervision', 'notifications.settings_payment'],
}

const rateTypeMap = { individual: 'Индивидуальный', template: 'Шаблонный', supervision: 'Авторский надзор', surveyor: 'Замерщик' }

const filteredRates = computed(() => {
  if (rateTab.value === 'surveyor') return rates.value.filter(r => r.role === 'Замерщик')
  return rates.value.filter(r => r.project_type === rateTypeMap[rateTab.value])
})

const permissionsByGroup = computed(() => {
  const result = {}
  for (const [group, permNames] of Object.entries(PERMISSION_GROUPS)) {
    const perms = permNames.map(name => {
      const existing = rolePermissions.value.find(p => p.name === name)
      return existing || { name, description: name, granted: false }
    })
    result[group] = perms
  }
  return result
})

async function loadRates() {
  try { const { data } = await api.get('/api/v1/rates'); rates.value = data } catch { rates.value = [] }
}

async function loadNormDays() {
  if (!ndProjectType.value || !ndSubtype.value) return
  ndLoading.value = true
  try {
    const { data } = await api.get('/api/v1/norm-days/templates', { params: { project_type: ndProjectType.value, project_subtype: ndSubtype.value } })
    normDays.value = data.entries || data || []
  } catch { normDays.value = [] }
  finally { ndLoading.value = false }
}

function editRate(rate) {
  editingRate.value = { ...rate }
  showRateDialog.value = true
}

function addRate() {
  if (rateTab.value === 'surveyor') {
    editingRate.value = { role: 'Замерщик', surveyor_price: null, city: null }
  } else {
    editingRate.value = { role: null, rate_per_m2: null, fixed_price: null, stage_name: '', city: null }
  }
  showRateDialog.value = true
}

async function saveRate() {
  if (!editingRate.value) return
  try {
    const isSurveyor = rateTab.value === 'surveyor' || !!editingRate.value.surveyor_price
    if (isSurveyor) {
      // Замерщик: upsert по городу через специальный endpoint
      await api.post('/api/v1/rates/surveyor', { city: editingRate.value.city, price: editingRate.value.surveyor_price })
    } else if (editingRate.value.id) {
      await api.put(`/api/v1/rates/${editingRate.value.id}`, editingRate.value)
    } else {
      await api.post('/api/v1/rates', editingRate.value)
    }
    $q.notify({ type: 'positive', message: 'Тариф сохранён' })
    showRateDialog.value = false
    loadRates()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
}

async function deleteRate(rate) {
  $q.dialog({ title: 'Удалить тариф?', message: `${rate.role} — ${rate.rate_per_m2 || rate.fixed_price || rate.surveyor_price} ₽`, cancel: true }).onOk(async () => {
    try {
      await api.delete(`/api/v1/rates/${rate.id}`)
      $q.notify({ type: 'positive', message: 'Удалено' })
      loadRates()
    } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

async function viewRolePermissions(role) {
  selectedRole.value = role
  try {
    const [defsRes, matrixRes] = await Promise.allSettled([
      api.get('/api/v1/permissions/definitions'),
      api.get('/api/v1/permissions/role-matrix'),
    ])
    const defs = defsRes.status === 'fulfilled' ? defsRes.value.data : []
    const matrix = matrixRes.status === 'fulfilled' ? matrixRes.value.data?.roles || {} : {}
    const rolePerms = matrix[role] || []
    rolePermissions.value = defs.map(d => ({ name: d.name, description: d.description, granted: rolePerms.includes(d.name) }))
    showRoleDialog.value = true
  } catch {}
}

async function saveRolePermissions() {
  const granted = rolePermissions.value.filter(p => p.granted).map(p => p.name)
  try {
    // Загружаем полную текущую матрицу, чтобы не затереть другие роли
    const { data: currentData } = await api.get('/api/v1/permissions/role-matrix')
    const fullMatrix = currentData.roles || {}
    fullMatrix[selectedRole.value] = granted
    await api.put('/api/v1/permissions/role-matrix', {
      roles: fullMatrix,
      apply_to_employees: true,
    })
    $q.notify({ type: 'positive', message: 'Права сохранены и применены к сотрудникам' })
    showRoleDialog.value = false
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
}

function addAgent() {
  $q.dialog({ title: 'Новый агент', prompt: { model: '', type: 'text', label: 'Название' }, cancel: true }).onOk(async (name) => {
    try { await api.post('/api/v1/agents', { name, color: '#95A5A6' }); $q.notify({ type: 'positive', message: 'Добавлен' }); refs.loaded = false; refs.loadAll() }
    catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

function deleteAgent(agent) {
  $q.dialog({ title: 'Удалить агента?', message: agent.name, cancel: true }).onOk(async () => {
    try { await api.delete(`/api/v1/agents/${agent.id}`); $q.notify({ type: 'positive', message: 'Удалён' }); refs.loaded = false; refs.loadAll() }
    catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

async function updateAgentColor(agent, color) {
  try { await api.patch(`/api/v1/agents/${encodeURIComponent(agent.name)}/color`, { color }); refs.loaded = false; refs.loadAll() }
  catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
}

async function loadCitiesFull() {
  try { const { data } = await api.get('/api/v1/cities'); citiesFull.value = data.filter(c => c.status === 'активный') } catch { citiesFull.value = [] }
}

function addCity() {
  $q.dialog({ title: 'Новый город', prompt: { model: '', type: 'text', label: 'Название' }, cancel: true }).onOk(async (name) => {
    try { await api.post('/api/v1/cities', { name }); $q.notify({ type: 'positive', message: 'Добавлен' }); refs.loaded = false; await Promise.all([refs.loadAll(), loadCitiesFull()]) }
    catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

function deleteCity(city) {
  $q.dialog({ title: 'Удалить город?', message: city.name, cancel: true }).onOk(async () => {
    try { await api.delete(`/api/v1/cities/${city.id}`); $q.notify({ type: 'positive', message: 'Удалён' }); refs.loaded = false; await Promise.all([refs.loadAll(), loadCitiesFull()]) }
    catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  })
}

function editCity(city) {
  $q.dialog({ title: 'Переименовать город', prompt: { model: city.name, type: 'text', label: 'Название' }, cancel: true })
    .onOk(async (name) => {
      if (!name || name.trim() === city.name) return
      try {
        await api.patch(`/api/v1/cities/${city.id}`, { name: name.trim() })
        $q.notify({ type: 'positive', message: 'Город переименован' })
        refs.loaded = false
        await Promise.all([refs.loadAll(), loadCitiesFull()])
      } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
    })
}

async function loadTgInfo() {
  if (!tgInfoEmployeeId.value) { tgInfo.value = null; return }
  try {
    const { data } = await api.get(`/api/v1/employees/${tgInfoEmployeeId.value}/telegram-info`)
    tgInfo.value = data
  } catch { tgInfo.value = null }
}

function copyToClipboard(text) {
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    $q.notify({ type: 'positive', message: 'Скопировано' })
  })
}

async function sendTestNotification() {
  try {
    await api.post('/api/v1/notifications/test')
    $q.notify({ type: 'positive', message: 'Тестовое уведомление отправлено' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function sendInvite() {
  if (!inviteEmployeeId.value) return
  try {
    await api.post(`/api/v1/employees/${inviteEmployeeId.value}/send-invite`)
    $q.notify({ type: 'positive', message: 'Приглашение отправлено' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

onMounted(async () => {
  loadRates()
  loadCitiesFull()
  try {
    const { data } = await api.get('/api/v1/employees')
    inviteEmployeeOpts.value = data.filter(e => e.status === 'активный').map(e => ({ label: `${e.full_name} (${e.email || 'нет email'})`, value: e.id }))
  } catch {}
})
</script>
