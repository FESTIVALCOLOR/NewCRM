<template>
  <q-page padding>
    <div v-if="crmStore.cardLoading" class="q-pa-md">
      <q-skeleton type="rect" height="150px" class="q-mb-md" /><q-skeleton type="text" width="80%" />
    </div>

    <template v-else-if="card">
      <!-- Шапка -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="row items-center justify-between q-mb-xs">
            <div class="text-subtitle1 text-weight-bold" style="color: #333">{{ card.contract_number }}</div>
            <q-badge :color="statusColor(card.column_name)" :label="card.column_name" />
          </div>
          <div class="row items-start justify-between">
            <div class="text-body2" style="color: #333; flex: 1">{{ card.address }}</div>
            <span v-if="card.agent_type" class="agent-badge q-ml-xs" :style="{ background: agentColor }">{{ card.agent_type }}</span>
          </div>
          <div class="row q-gutter-sm text-caption q-mt-xs" style="color: #888">
            <span v-if="card.area">{{ card.area }} м²</span><span v-if="card.city">{{ card.city }}</span>
          </div>
          <div v-if="card.current_substep_name" class="q-mt-xs">
            <q-chip dense size="sm" :color="substepColor(card.workflow_status)" text-color="white">
              {{ workflowLabel(card.workflow_status) }}: {{ card.current_substep_name }}
            </q-chip>
          </div>
          <q-badge v-if="card.revision_count > 0" color="negative" :label="`Правки: ${card.revision_count}`" class="q-mt-xs" />
        </q-card-section>
      </q-card>

      <!-- Вкладки как в десктопе -->
      <q-tabs v-model="activeTab" dense active-color="dark" indicator-color="accent" no-caps class="q-mb-md" style="color: #666" align="left">
        <q-tab name="executors" label="Исполнители" />
        <q-tab name="timeline" label="Таблица сроков" />
        <q-tab name="data" label="Данные проекта" />
        <q-tab name="history" label="История" />
        <q-tab name="payments" label="Оплаты" />
      </q-tabs>

      <q-tab-panels v-model="activeTab" animated class="bg-transparent">

        <!-- ВКЛАДКА 1: Исполнители и дедлайн -->
        <q-tab-panel name="executors" class="q-pa-none">
          <!-- Информация -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Информация проекта</div></q-card-section>
            <q-list dense>
              <q-item><q-item-section avatar><q-icon name="description" color="grey-7" /></q-item-section><q-item-section><q-item-label caption>Договор</q-item-label><q-item-label>{{ card.contract_number }}</q-item-label></q-item-section></q-item>
              <q-item v-if="card.deadline"><q-item-section avatar><q-icon name="event" color="grey-7" /></q-item-section><q-item-section><q-item-label caption>Дедлайн проекта</q-item-label><q-item-label :style="{ color: dlHex(card.deadline) }">{{ fmtDate(card.deadline) }} ({{ daysLeft(card.deadline) }})</q-item-label></q-item-section></q-item>
              <q-item v-if="card.tags"><q-item-section avatar><q-icon name="label" color="grey-7" /></q-item-section><q-item-section><q-item-label caption>Теги</q-item-label><q-item-label>{{ card.tags }}</q-item-label></q-item-section></q-item>
            </q-list>
          </q-card>

          <!-- Команда проекта -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Команда проекта</div></q-card-section>
            <q-list dense>
              <q-item v-for="m in teamMembers" :key="m.role" v-show="m.name">
                <q-item-section avatar><q-avatar size="28px" color="grey-3" text-color="grey-8">{{ m.name?.[0] }}</q-avatar></q-item-section>
                <q-item-section><q-item-label style="font-size: 12px">{{ m.name }}</q-item-label><q-item-label caption>{{ m.role }}</q-item-label></q-item-section>
                <q-item-section side v-if="m.deadline"><q-badge :color="dlBadgeColor(m.deadline)" :label="fmtDateShort(m.deadline)" dense /></q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Workflow действия -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Действия</div></q-card-section>
            <q-list dense>
              <q-item v-if="card.workflow_status === 'in_progress'" clickable v-ripple @click="doAction('submit')"><q-item-section avatar><q-icon name="send" color="positive" /></q-item-section><q-item-section>Сдать работу</q-item-section></q-item>
              <q-item v-if="card.workflow_status === 'pending_review'" clickable v-ripple @click="doAction('accept')"><q-item-section avatar><q-icon name="check" color="positive" /></q-item-section><q-item-section>Принять</q-item-section></q-item>
              <q-item v-if="card.workflow_status === 'pending_review'" clickable v-ripple @click="showRejectDialog = true"><q-item-section avatar><q-icon name="close" color="negative" /></q-item-section><q-item-section>На исправление</q-item-section></q-item>
              <q-item v-if="card.workflow_status === 'pending_review'" clickable v-ripple @click="doAction('client-send')"><q-item-section avatar><q-icon name="forward_to_inbox" style="color: #3498DB" /></q-item-section><q-item-section>Отправить клиенту</q-item-section></q-item>
              <q-item v-if="card.workflow_status === 'client_approval'" clickable v-ripple @click="doAction('client-approved')"><q-item-section avatar><q-icon name="thumb_up" color="positive" /></q-item-section><q-item-section>Клиент согласовал</q-item-section></q-item>
              <q-item v-if="card.workflow_status === 'act_signing'" clickable v-ripple @click="doAction('sign-act')"><q-item-section avatar><q-icon name="draw" style="color: #333" /></q-item-section><q-item-section>Акт подписан</q-item-section></q-item>
            </q-list>
          </q-card>

          <!-- Назначить исполнителя -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Назначить исполнителя</div></q-card-section>
            <q-card-section>
              <q-select v-model="assignForm.stage_name" :options="stageOptions" label="Стадия" outlined dense class="q-mb-sm" />
              <q-select v-model="assignForm.executor_id" :options="employeeOptions" option-value="id" option-label="label" label="Исполнитель" outlined dense emit-value map-options class="q-mb-sm" />
              <q-input v-model="assignForm.deadline" label="Дедлайн" outlined dense type="date" class="q-mb-sm" />
              <q-btn unelevated label="Назначить" no-caps class="full-width" style="background: #ffd93c; color: #333; border-radius: 4px" @click="assignExecutor" :loading="actionLoading" />
            </q-card-section>
          </q-card>

          <!-- Переместить -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Переместить</div></q-card-section>
            <q-list dense>
              <q-item v-for="col in crmStore.columnOrder" :key="col" clickable @click="moveToColumn(col)" :disable="col === card.column_name">
                <q-item-section><q-item-label :style="{ color: col === card.column_name ? '#ccc' : '#333', fontSize: '12px' }">{{ col }}</q-item-label></q-item-section>
                <q-item-section side v-if="col === card.column_name"><q-icon name="check" color="positive" size="16px" /></q-item-section>
              </q-item>
            </q-list>
          </q-card>
        </q-tab-panel>

        <!-- ВКЛАДКА 2: Таблица сроков -->
        <q-tab-panel name="timeline" class="q-pa-none">
          <q-card class="is-card">
            <q-list dense separator v-if="card.stage_executors?.length">
              <q-item v-for="se in card.stage_executors" :key="se.id">
                <q-item-section avatar><q-icon :name="se.completed ? 'check_circle' : 'radio_button_unchecked'" :color="se.completed ? 'positive' : 'grey-5'" size="18px" /></q-item-section>
                <q-item-section><q-item-label style="font-size: 12px; color: #333">{{ se.stage_name }}</q-item-label><q-item-label caption style="color: #888">{{ se.executor_name }} <span v-if="se.deadline">| до {{ fmtDateShort(se.deadline) }}</span></q-item-label></q-item-section>
                <q-item-section side v-if="se.completed_date"><div class="text-caption" style="color: #27AE60">{{ fmtDateShort(se.completed_date) }}</div></q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: #999">Нет стадий</q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ВКЛАДКА 3: Данные по проекту -->
        <q-tab-panel name="data" class="q-pa-none">
          <!-- ТЗ и Замер -->
          <q-card class="is-card q-mb-md">
            <q-list dense>
              <q-item v-if="card.tech_task_link" clickable @click="openLink(card.tech_task_link)"><q-item-section avatar><q-icon name="description" color="orange" /></q-item-section><q-item-section><q-item-label>Техническое задание</q-item-label><q-item-label caption v-if="card.tech_task_date">{{ fmtDateShort(card.tech_task_date) }}</q-item-label></q-item-section><q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section></q-item>
              <q-item v-if="card.measurement_image_link" clickable @click="openLink(card.measurement_image_link)"><q-item-section avatar><q-icon name="straighten" color="blue" /></q-item-section><q-item-section><q-item-label>Замер</q-item-label><q-item-label caption v-if="card.survey_date">{{ fmtDateShort(card.survey_date) }}</q-item-label></q-item-section><q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section></q-item>
              <q-item v-if="card.project_data_link" clickable @click="openLink(card.project_data_link)"><q-item-section avatar><q-icon name="folder" color="amber" /></q-item-section><q-item-section><q-item-label>Данные проекта</q-item-label></q-item-section><q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section></q-item>
            </q-list>
          </q-card>
          <!-- Загрузка файлов -->
          <q-card class="is-card q-mb-md">
            <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Загрузить файлы</div></q-card-section>
            <q-card-section>
              <div class="row q-col-gutter-xs">
                <div class="col-6"><q-btn outline color="grey-7" icon="description" label="ТЗ" no-caps class="full-width" dense @click="uploadCrmFile('tech_task')" /></div>
                <div class="col-6"><q-btn outline color="grey-7" icon="straighten" label="Замер" no-caps class="full-width" dense @click="uploadCrmFile('measurement')" /></div>
                <div class="col-6"><q-btn outline color="grey-7" icon="collections" label="Референсы" no-caps class="full-width q-mt-xs" dense @click="uploadCrmFile('references')" /></div>
                <div class="col-6"><q-btn outline color="grey-7" icon="photo_camera" label="Фотофикс." no-caps class="full-width q-mt-xs" dense @click="uploadCrmFile('photo_documentation')" /></div>
              </div>
              <input ref="crmFileInput" type="file" style="position: absolute; left: -9999px; opacity: 0" @change="handleCrmFileUpload" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" />
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ВКЛАДКА 4: История -->
        <q-tab-panel name="history" class="q-pa-none">
          <q-card class="is-card">
            <q-list dense separator v-if="cardHistory.length > 0">
              <q-item v-for="(h, idx) in cardHistory" :key="idx">
                <q-item-section avatar><q-icon name="history" color="grey-5" size="18px" /></q-item-section>
                <q-item-section><q-item-label style="font-size: 11px; color: #333">{{ h.action_type || h.message || '—' }}</q-item-label><q-item-label caption style="color: #888">{{ h.employee_name || '' }}</q-item-label></q-item-section>
                <q-item-section side><div class="text-caption" style="color: #888">{{ fmtDateShort(h.action_date || h.created_at) }}</div></q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: #999">Нет истории</q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- ВКЛАДКА 5: Оплаты исполнителям -->
        <q-tab-panel name="payments" class="q-pa-none">
          <q-card class="is-card">
            <q-list dense separator v-if="cardPayments.length > 0">
              <q-item v-for="p in cardPayments" :key="p.id">
                <q-item-section><q-item-label style="font-size: 12px; color: #333" class="text-weight-medium">{{ p.employee_name || '—' }}</q-item-label><q-item-label caption style="color: #888">{{ p.role || '' }} | {{ p.stage_name || p.payment_subtype || '' }}</q-item-label></q-item-section>
                <q-item-section side><div class="text-right"><div class="text-weight-bold" style="font-size: 13px" :style="{ color: p.is_paid ? '#27AE60' : '#333' }">{{ fmtMoney(p.final_amount || p.amount) }}</div><q-badge :color="p.is_paid ? 'positive' : 'warning'" :label="p.is_paid ? 'Оплачено' : p.report_month || 'К оплате'" dense /></div></q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: #999">Нет платежей</q-card-section>
          </q-card>
        </q-tab-panel>
      </q-tab-panels>

      <!-- Диалог ревизии -->
      <q-dialog v-model="showRejectDialog">
        <q-card style="min-width: 320px; border-radius: 10px">
          <q-toolbar style="background: #E74C3C; color: white"><q-toolbar-title class="text-weight-bold" style="font-size: 14px">На исправление</q-toolbar-title><q-btn flat round dense icon="close" color="white" @click="showRejectDialog = false" /></q-toolbar>
          <q-card-section>
            <q-input v-model="rejectReason" label="Причина *" outlined dense type="textarea" autogrow class="q-mb-sm" />
            <q-file v-model="rejectFile" label="Файл с правками" outlined dense accept=".pdf,.jpg,.png,.doc" class="q-mb-sm"><template v-slot:prepend><q-icon name="attach_file" /></template></q-file>
          </q-card-section>
          <q-card-actions align="right"><q-btn flat label="Отмена" v-close-popup no-caps /><q-btn unelevated label="Отправить" style="background: #E74C3C; color: white; border-radius: 4px" no-caps @click="submitReject" :loading="actionLoading" /></q-card-actions>
        </q-card>
      </q-dialog>

      <!-- FAB редактирования -->
      <q-page-sticky position="bottom-right" :offset="[18, 70]">
        <q-btn fab icon="edit" style="background: #ffd93c; color: #333" />
      </q-page-sticky>
    </template>

    <div v-else class="text-center q-pa-xl" style="color: #999">
      <q-icon name="search_off" size="48px" class="q-mb-sm" /><div>Карточка не найдена</div>
      <q-btn flat label="Назад" @click="$router.back()" class="q-mt-md" no-caps style="color: #333" />
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { useCrmStore } from 'src/stores/crm'
import { useReferencesStore } from 'src/stores/references'
import { crmApi, employeesApi, filesApi } from 'src/services/api'

const route = useRoute()
const $q = useQuasar()
const crmStore = useCrmStore()
const refs = useReferencesStore()
const card = computed(() => crmStore.selectedCard)
const activeTab = ref('executors')
const actionLoading = ref(false)
const employeeOptions = ref([])
const assignForm = ref({ stage_name: '', executor_id: null, deadline: '' })
const cardPayments = ref([])
const cardHistory = ref([])
const showRejectDialog = ref(false)
const rejectReason = ref('')
const rejectFile = ref(null)
const crmFileInput = ref(null)
const crmUploadStage = ref('')

const agentColor = computed(() => refs.agentByName(card.value?.agent_type)?.color || '#95A5A6')

const stageOptions = ['Стадия 1: планировочные решения', 'Стадия 2: концепция дизайна', 'Стадия 3: рабочие чертежи']

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

function statusColor(col) { if (!col) return 'grey'; if (col.includes('Новый')) return 'info'; if (col.includes('ожидании')) return 'warning'; if (col.includes('Стадия')) return 'accent'; if (col.includes('Выполненный')) return 'positive'; return 'grey' }
function substepColor(s) { return { pending_review: 'purple', revision: 'negative', client_approval: 'info', act_signing: 'purple', stage_completed: 'positive' }[s] || 'orange' }
function workflowLabel(s) { return { in_progress: 'В работе', pending_review: 'На проверке', revision: 'Исправление', client_approval: 'У клиента', pending_decision: 'Решение', act_signing: 'Подписание акта', stage_completed: 'Завершено' }[s] || '' }
function dlHex(d) { if (!d) return '#888'; const days = Math.ceil((new Date(d) - new Date()) / 86400000); if (days < 0) return '#E74C3C'; if (days <= 2) return '#F39C12'; return '#888' }
function dlBadgeColor(d) { if (!d) return 'grey'; const days = Math.ceil((new Date(d) - new Date()) / 86400000); if (days < 0) return 'negative'; if (days <= 2) return 'warning'; return 'positive' }
function daysLeft(d) { if (!d) return ''; const days = Math.ceil((new Date(d) - new Date()) / 86400000); if (days < 0) return `${Math.abs(days)} дн. просрочено`; if (days === 0) return 'сегодня'; return `${days} дн.` }
function fmtDate(d) { if (!d) return '—'; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' }) }
function fmtDateShort(d) { if (!d) return ''; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) }
function fmtMoney(v) { if (!v) return '0 ₽'; return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(v) }
function openLink(url) { if (url) window.open(url, '_blank') }

async function doAction(action) {
  actionLoading.value = true
  try {
    const id = card.value.id
    const actions = { submit: () => crmApi.submitWork(id), accept: () => crmApi.acceptWork(id), 'client-send': () => crmApi.sendToClient(id), 'client-approved': () => crmApi.clientApproved(id), 'sign-act': () => crmApi.signAct(id) }
    await actions[action]()
    $q.notify({ type: 'positive', message: 'Выполнено' })
    crmStore.loadCard(id)
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

async function submitReject() {
  if (!rejectReason.value) { $q.notify({ type: 'warning', message: 'Укажите причину' }); return }
  actionLoading.value = true
  try {
    let filePath = null
    if (rejectFile.value) {
      const yp = `/CRM/Правки/${card.value.contract_number || card.value.id}/${rejectFile.value.name}`
      await filesApi.upload(rejectFile.value, yp)
      filePath = yp
    }
    await crmApi.rejectWork(card.value.id, { reason: rejectReason.value, revision_file_path: filePath })
    $q.notify({ type: 'positive', message: 'Отправлено на исправление' })
    showRejectDialog.value = false; rejectReason.value = ''; rejectFile.value = null
    crmStore.loadCard(card.value.id)
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

async function moveToColumn(col) {
  actionLoading.value = true
  try { await crmApi.moveCard(card.value.id, col); $q.notify({ type: 'positive', message: `Перемещено: ${col}` }); crmStore.loadCard(card.value.id) }
  catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

async function assignExecutor() {
  if (!assignForm.value.stage_name || !assignForm.value.executor_id) return
  actionLoading.value = true
  try { await crmApi.assignExecutor(card.value.id, assignForm.value); $q.notify({ type: 'positive', message: 'Назначен' }); crmStore.loadCard(card.value.id) }
  catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { actionLoading.value = false }
}

function uploadCrmFile(stage) { crmUploadStage.value = stage; crmFileInput.value?.click() }

async function handleCrmFileUpload(event) {
  const file = event.target.files?.[0]
  if (!file || !card.value) return
  try {
    $q.loading.show({ message: 'Загрузка...' })
    const yp = `/CRM/Проекты/${card.value.contract_number}/${crmUploadStage.value}/${file.name}`
    await filesApi.upload(file, yp)
    $q.notify({ type: 'positive', message: 'Файл загружен' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка загрузки' }) }
  finally { $q.loading.hide(); event.target.value = '' }
}

onMounted(async () => {
  const cardId = route.params.id
  crmStore.loadCard(cardId)
  const [empRes, payRes, histRes] = await Promise.allSettled([
    employeesApi.getList(),
    crmApi.getPayments(cardId),
    crmApi.getHistory(cardId)
  ])
  if (empRes.status === 'fulfilled') employeeOptions.value = empRes.value.data.filter(e => e.status === 'активный').map(e => ({ id: e.id, label: `${e.full_name} (${e.position})` }))
  if (payRes.status === 'fulfilled') cardPayments.value = payRes.value.data || []
  if (histRes.status === 'fulfilled') cardHistory.value = histRes.value.data || []
})
</script>
