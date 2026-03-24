<template>
  <q-page padding>
    <div v-if="crmStore.cardLoading" class="q-pa-md">
      <q-skeleton type="rect" height="150px" class="q-mb-md" />
      <q-skeleton type="text" width="80%" />
    </div>

    <template v-else-if="card">
      <!-- Шапка -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="row items-center justify-between q-mb-xs">
            <div class="text-subtitle1 text-weight-bold">{{ card.contract_number }}</div>
            <q-badge :color="statusColor(card.column_name)" :label="card.column_name" />
          </div>
          <div class="text-body1 q-mb-xs">{{ card.address }}</div>
          <div class="row q-gutter-sm text-caption text-grey-7">
            <span v-if="card.area">{{ card.area }} м²</span>
            <span v-if="card.city">{{ card.city }}</span>
            <span v-if="card.floors">{{ card.floors }} эт.</span>
          </div>
          <!-- Подэтап и workflow статус -->
          <div v-if="card.current_substep_name" class="q-mt-sm">
            <q-chip dense size="sm" :color="substepColor(card.workflow_status)" text-color="white">
              {{ workflowLabel(card.workflow_status) }}: {{ card.current_substep_name }}
            </q-chip>
          </div>
          <div v-if="card.revision_count > 0" class="q-mt-xs">
            <q-badge color="negative" :label="`Правки: ${card.revision_count}`" />
          </div>
          <!-- Агент (цвет из справочника) -->
          <div v-if="card.agent_type" class="q-mt-xs">
            <span class="agent-badge" :style="{ background: agentColor }">{{ card.agent_type }}</span>
          </div>
        </q-card-section>
      </q-card>

      <!-- Вкладки карточки -->
      <q-tabs v-model="activeTab" dense active-color="dark" indicator-color="accent" no-caps class="q-mb-md text-grey-7">
        <q-tab name="team" label="Команда" />
        <q-tab name="timeline" label="Сроки" />
        <q-tab name="files" label="Файлы" />
        <q-tab name="payments" label="Оплаты" />
        <q-tab name="history" label="История" />
      </q-tabs>

      <!-- Команда -->
      <q-tab-panels v-model="activeTab" animated class="bg-transparent">
        <q-tab-panel name="team" class="q-pa-none">
          <q-card class="is-card q-mb-md" v-if="card.client_name">
            <q-card-section>
              <div class="text-caption text-grey-7">Клиент</div>
              <div class="text-subtitle2 text-weight-bold">{{ card.client_name }}</div>
            </q-card-section>
          </q-card>
          <q-card class="is-card">
            <q-list dense>
              <q-item v-for="m in teamMembers" :key="m.role" v-show="m.name">
                <q-item-section avatar>
                  <q-avatar size="32px" color="grey-3" text-color="grey-8">{{ m.name ? m.name[0] : '?' }}</q-avatar>
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ m.name }}</q-item-label>
                  <q-item-label caption>{{ m.role }}</q-item-label>
                </q-item-section>
                <q-item-section side v-if="m.deadline">
                  <q-badge :color="deadlineColor(m.deadline)" :label="formatDate(m.deadline)" dense />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Дедлайн проекта -->
          <q-card class="is-card q-mt-md" v-if="card.deadline">
            <q-card-section>
              <div class="row items-center justify-between">
                <div>
                  <div class="text-caption text-grey-7">Дедлайн проекта</div>
                  <div class="text-weight-bold">{{ formatDate(card.deadline) }}</div>
                </div>
                <q-badge :color="deadlineColor(card.deadline)" :label="daysLeft(card.deadline)" />
              </div>
            </q-card-section>
          </q-card>

          <!-- Workflow действия -->
          <q-card class="is-card q-mt-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">Действия</div>
            </q-card-section>
            <q-list dense>
              <q-item v-if="card.workflow_status === 'in_progress'" clickable v-ripple @click="doAction('submit')">
                <q-item-section avatar><q-icon name="send" color="positive" /></q-item-section>
                <q-item-section>Сдать работу</q-item-section>
              </q-item>
              <q-item v-if="card.workflow_status === 'pending_review'" clickable v-ripple @click="doAction('accept')">
                <q-item-section avatar><q-icon name="check" color="positive" /></q-item-section>
                <q-item-section>Принять работу</q-item-section>
              </q-item>
              <q-item v-if="card.workflow_status === 'pending_review'" clickable v-ripple @click="doAction('reject')">
                <q-item-section avatar><q-icon name="close" color="negative" /></q-item-section>
                <q-item-section>На исправление</q-item-section>
              </q-item>
              <q-item v-if="card.workflow_status === 'pending_review'" clickable v-ripple @click="doAction('client-send')">
                <q-item-section avatar><q-icon name="forward_to_inbox" style="color: #3498DB" /></q-item-section>
                <q-item-section>Отправить клиенту</q-item-section>
              </q-item>
              <q-item v-if="card.workflow_status === 'client_approval'" clickable v-ripple @click="doAction('client-approved')">
                <q-item-section avatar><q-icon name="thumb_up" color="positive" /></q-item-section>
                <q-item-section>Клиент согласовал</q-item-section>
              </q-item>
              <q-item v-if="card.workflow_status === 'act_signing'" clickable v-ripple @click="doAction('sign-act')">
                <q-item-section avatar><q-icon name="draw" style="color: #333" /></q-item-section>
                <q-item-section>Акт подписан</q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Назначить исполнителя -->
          <q-card class="is-card q-mt-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">Назначить исполнителя</div>
            </q-card-section>
            <q-card-section>
              <q-select v-model="assignForm.stage_name" :options="stageOptions" label="Стадия" outlined dense class="q-mb-sm" />
              <q-select v-model="assignForm.executor_id" :options="employeeOptions" option-value="id" option-label="label" label="Исполнитель" outlined dense emit-value map-options class="q-mb-sm" />
              <q-input v-model="assignForm.deadline" label="Дедлайн" outlined dense type="date" class="q-mb-sm" />
              <q-btn color="accent" text-color="dark" label="Назначить" no-caps unelevated class="full-width" @click="assignExecutor" :loading="actionLoading" style="border-radius: 4px" />
            </q-card-section>
          </q-card>

          <!-- Перемещение -->
          <q-card class="is-card q-mt-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">Переместить</div>
            </q-card-section>
            <q-list dense>
              <q-item v-for="col in crmStore.columnOrder" :key="col" clickable @click="moveToColumn(col)" :disable="col === card.column_name">
                <q-item-section>
                  <q-item-label :style="{ color: col === card.column_name ? '#ccc' : '#333' }">{{ col }}</q-item-label>
                </q-item-section>
                <q-item-section side v-if="col === card.column_name"><q-icon name="check" color="positive" /></q-item-section>
              </q-item>
            </q-list>
          </q-card>
        </q-tab-panel>

        <!-- Таблица сроков (подэтапы) -->
        <q-tab-panel name="timeline" class="q-pa-none">
          <q-card class="is-card">
            <q-list dense separator v-if="card.stage_executors?.length">
              <q-item v-for="se in card.stage_executors" :key="se.id">
                <q-item-section avatar>
                  <q-icon :name="se.completed ? 'check_circle' : 'radio_button_unchecked'" :color="se.completed ? 'positive' : 'grey-5'" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ se.stage_name }}</q-item-label>
                  <q-item-label caption>{{ se.executor_name }}</q-item-label>
                </q-item-section>
                <q-item-section side v-if="se.deadline">
                  <div class="text-caption">{{ formatDate(se.deadline) }}</div>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center text-grey-5">Нет стадий</q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- Файлы -->
        <q-tab-panel name="files" class="q-pa-none">
          <q-card class="is-card">
            <q-list dense v-if="hasFiles">
              <q-item v-if="card.tech_task_link" clickable @click="openLink(card.tech_task_link)">
                <q-item-section avatar><q-icon name="description" color="red" /></q-item-section>
                <q-item-section><q-item-label>{{ card.tech_task_file || 'Техническое задание' }}</q-item-label></q-item-section>
                <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
              </q-item>
              <q-item v-if="card.measurement_image_link" clickable @click="openLink(card.measurement_image_link)">
                <q-item-section avatar><q-icon name="straighten" color="orange" /></q-item-section>
                <q-item-section><q-item-label>{{ card.measurement_file_name || 'Замер' }}</q-item-label></q-item-section>
                <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
              </q-item>
              <q-item v-if="card.project_data_link" clickable @click="openLink(card.project_data_link)">
                <q-item-section avatar><q-icon name="folder" color="amber" /></q-item-section>
                <q-item-section><q-item-label>Данные проекта</q-item-label></q-item-section>
                <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center text-grey-5">Нет файлов</q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- Оплаты -->
        <q-tab-panel name="payments" class="q-pa-none">
          <q-card class="is-card">
            <q-list dense separator v-if="cardPayments.length > 0">
              <q-item v-for="p in cardPayments" :key="p.id">
                <q-item-section>
                  <q-item-label class="text-weight-medium">{{ p.employee_name || 'Без исполнителя' }}</q-item-label>
                  <q-item-label caption>{{ p.stage_name || p.payment_subtype || '—' }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="text-right">
                    <div class="text-weight-bold" :class="p.is_paid ? 'text-positive' : 'text-warning'">
                      {{ formatMoney(p.final_amount || p.amount) }}
                    </div>
                    <q-badge :color="p.is_paid ? 'positive' : 'warning'" :label="p.is_paid ? 'Оплачено' : 'Ожидает'" dense />
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center text-grey-5">Нет платежей</q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- История -->
        <q-tab-panel name="history" class="q-pa-none">
          <q-card class="is-card">
            <q-list dense separator v-if="cardHistory.length > 0">
              <q-item v-for="h in cardHistory" :key="h.id || h.action_date">
                <q-item-section avatar>
                  <q-icon name="history" color="grey-5" size="20px" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ h.action_type || h.message || '—' }}</q-item-label>
                  <q-item-label caption>{{ h.employee_name || '' }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="text-caption text-grey-5">{{ formatDate(h.action_date || h.created_at) }}</div>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center text-grey-5">Нет истории</q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- Действия -->
        <!-- Вкладка "Действия" убрана — действия теперь в каждой вкладке -->
      </q-tab-panels>
    </template>

    <div v-else class="text-center q-pa-xl text-grey-5">
      <q-icon name="search_off" size="48px" class="q-mb-sm" />
      <div>Карточка не найдена</div>
      <q-btn flat color="accent" text-color="dark" label="Назад" @click="$router.back()" class="q-mt-md" no-caps />
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { useCrmStore } from 'src/stores/crm'
import { useReferencesStore } from 'src/stores/references'
import { crmApi, employeesApi } from 'src/services/api'

const route = useRoute()
const $q = useQuasar()
const crmStore = useCrmStore()
const refs = useReferencesStore()
const card = computed(() => crmStore.selectedCard)

const agentColor = computed(() => {
  const agent = refs.agentByName(card.value?.agent_type)
  return agent?.color || '#95A5A6'
})
const activeTab = ref('team')
const actionLoading = ref(false)
const employeeOptions = ref([])
const assignForm = ref({ stage_name: '', executor_id: null, deadline: '' })
const cardPayments = ref([])
const cardHistory = ref([])

const stageOptions = [
  'Стадия 1: планировочные решения',
  'Стадия 2: концепция дизайна',
  'Стадия 3: рабочие чертежи'
]

const teamMembers = computed(() => {
  if (!card.value) return []
  return [
    { role: 'Ст. менеджер', name: card.value.senior_manager_name },
    { role: 'СДП', name: card.value.sdp_name },
    { role: 'ГАП', name: card.value.gap_name },
    { role: 'Менеджер', name: card.value.manager_name },
    { role: 'Замерщик', name: card.value.surveyor_name },
    { role: 'Дизайнер', name: card.value.designer_name, deadline: card.value.designer_deadline },
    { role: 'Чертёжник', name: card.value.draftsman_name, deadline: card.value.draftsman_deadline }
  ].filter(m => m.name)
})

const hasFiles = computed(() => card.value && (card.value.tech_task_link || card.value.measurement_image_link || card.value.project_data_link))

function statusColor(col) {
  if (!col) return 'grey'
  if (col.includes('Новый')) return 'info'
  if (col.includes('ожидании')) return 'warning'
  if (col.includes('Стадия')) return 'accent'
  if (col.includes('Выполненный')) return 'positive'
  return 'grey'
}

function substepColor(status) {
  const m = { in_progress: 'orange', pending_review: 'purple', revision: 'negative', client_approval: 'info', act_signing: 'purple', stage_completed: 'positive' }
  return m[status] || 'grey'
}

function workflowLabel(status) {
  const m = { in_progress: 'В работе', pending_review: 'На проверке', revision: 'Исправление', client_approval: 'У клиента', pending_decision: 'Решение', act_signing: 'Подписание акта', stage_completed: 'Завершено' }
  return m[status] || status || ''
}

function deadlineColor(d) {
  if (!d) return 'grey'
  const days = Math.ceil((new Date(d) - new Date()) / 86400000)
  if (days < 0) return 'negative'
  if (days <= 2) return 'warning'
  return 'positive'
}

function daysLeft(d) {
  if (!d) return ''
  const days = Math.ceil((new Date(d) - new Date()) / 86400000)
  if (days < 0) return `${Math.abs(days)} дн. просрочено`
  if (days === 0) return 'Сегодня'
  return `${days} дн.`
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

function formatMoney(v) {
  if (!v) return '0 ₽'
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(v)
}

function openLink(url) { if (url) window.open(url, '_blank') }

async function doAction(action) {
  actionLoading.value = true
  try {
    const id = card.value.id
    const actions = {
      submit: () => crmApi.submitWork(id),
      accept: () => crmApi.acceptWork(id),
      reject: () => crmApi.rejectWork(id, {}),
      'client-send': () => crmApi.sendToClient(id),
      'client-approved': () => crmApi.clientApproved(id),
      'sign-act': () => crmApi.signAct(id)
    }
    await actions[action]()
    $q.notify({ type: 'positive', message: 'Действие выполнено' })
    crmStore.loadCard(id)
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  } finally { actionLoading.value = false }
}

async function moveToColumn(col) {
  actionLoading.value = true
  try {
    await crmApi.moveCard(card.value.id, col)
    $q.notify({ type: 'positive', message: `Перемещено: ${col}` })
    crmStore.loadCard(card.value.id)
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  } finally { actionLoading.value = false }
}

async function assignExecutor() {
  if (!assignForm.value.stage_name || !assignForm.value.executor_id) return
  actionLoading.value = true
  try {
    await crmApi.assignExecutor(card.value.id, assignForm.value)
    $q.notify({ type: 'positive', message: 'Исполнитель назначен' })
    crmStore.loadCard(card.value.id)
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  } finally { actionLoading.value = false }
}

onMounted(async () => {
  const cardId = route.params.id
  crmStore.loadCard(cardId)

  // Параллельная загрузка всех данных
  const [empRes, payRes, histRes] = await Promise.allSettled([
    employeesApi.getList(),
    crmApi.getPayments(cardId),
    crmApi.getHistory(cardId)
  ])

  if (empRes.status === 'fulfilled') {
    employeeOptions.value = empRes.value.data.filter(e => e.status === 'активный').map(e => ({ id: e.id, label: `${e.full_name} (${e.position})` }))
  }
  if (payRes.status === 'fulfilled') cardPayments.value = payRes.value.data || []
  if (histRes.status === 'fulfilled') cardHistory.value = histRes.value.data || []
})
</script>
