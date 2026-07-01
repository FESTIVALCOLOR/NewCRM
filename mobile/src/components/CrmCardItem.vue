<template>
  <q-card flat bordered class="crm-card q-mb-sm" :style="archiveCardStyle">
    <q-card-section class="q-pa-sm">
      <!-- 1. Верхняя строка: номер + статус работы + колокольчик тишины -->
      <div class="row items-center justify-between q-mb-xs">
        <div style="color: #888; font-size: 10px">
          Договор: {{ card.contract_number || `#${card.id}` }}
        </div>
        <div class="row items-center" style="gap: 4px">
          <div v-if="workStatusText" :style="{ fontSize: '8px', fontWeight: 'bold', color: workStatusColor, border: `1px solid ${workStatusColor}`, borderRadius: '3px', padding: '1px 6px' }">
            {{ workStatusText }}
          </div>
          <button v-if="!isArchived" class="mute-bell-btn" @click.stop="emit('toggle-mute')">
            <span class="material-icons" :style="{ fontSize: '14px', color: isMuted ? '#333' : '#CCC' }">
              {{ isMuted ? 'notifications_off' : 'notifications' }}
            </span>
          </button>
        </div>
      </div>

      <!-- 2. Адрес -->
      <div class="text-weight-bold q-mb-xs" style="font-size: 14px; color: #222; word-wrap: break-word">
        {{ card.address || 'Без адреса' }}
      </div>

      <!-- 3. Разделитель -->
      <div style="height: 1px; background: #DDD" class="q-mb-xs" />

      <!-- 4. Подэтап (ВСЕГДА если есть) -->
      <div v-if="card.current_substep_name" class="q-mb-xs" :style="{ color: substepColor, fontSize: '9px', fontWeight: 'bold', wordWrap: 'break-word' }">
        {{ substepPrefix }}{{ card.current_substep_name }}
      </div>

      <!-- 5. Счётчик правок -->
      <div v-if="card.revision_count > 0" style="font-size: 9px; color: #E74C3C; font-weight: bold" class="q-mb-xs">
        Правки: {{ card.revision_count }}
      </div>

      <!-- 6. Площадь + Город | Агент -->
      <div class="row items-center justify-between q-mb-xs">
        <div style="font-size: 11px; color: #888">
          <span v-if="card.area">{{ card.area }} м²</span>
          <span v-if="card.area && card.city"> | </span>
          <span v-if="card.city">{{ card.city }}</span>
        </div>
        <span v-if="card.agent_type" :style="{ background: agentColor, color: 'white', fontSize: '10px', fontWeight: 'bold', padding: '3px 8px', borderRadius: '4px', lineHeight: '16px' }">
          {{ card.agent_type }}
        </span>
      </div>

      <!-- 7. Команда (сворачиваемая) -->
      <div v-if="teamMembers.length > 0" style="border: 1px solid #E0E0E0; border-radius: 4px; padding: 4px 6px; margin-bottom: 4px; background: #F8F9FA" @click.stop>
        <div style="font-size: 10px; color: #888; font-weight: bold; cursor: pointer" @click="showTeam = !showTeam">
          Команда ({{ teamMembers.length }}) {{ showTeam ? '▲' : '▼' }}
        </div>
        <div v-if="showTeam">
          <div v-for="m in teamMembers" :key="m.text" style="font-size: 10px; padding: 1px 4px; border-radius: 2px; margin-top: 1px" :style="{ background: m.bg, color: '#333' }">
            {{ m.text }}
          </div>
        </div>
      </div>

      <!-- 8. Теги -->
      <div v-if="card.tags" class="row q-gutter-xs q-mb-xs">
        <span
          v-for="(tag, tidx) in parseCrmTags(card.tags)"
          :key="tidx"
          :style="{ display: 'inline-block', background: tag.color, color: 'white', borderRadius: '4px', padding: '2px 8px', fontSize: '10px', fontWeight: '600' }"
        >{{ tag.text }}</span>
      </div>

      <!-- 9. Дедлайны (скрыты в архиве) -->
      <div v-if="!isArchived && (generalDeadlineText || substepDeadlineText)" class="q-mb-xs row no-wrap" style="gap: 4px">
        <!-- Общий дедлайн заказа (всегда слева) -->
        <div v-if="generalDeadlineText" :style="{ flex: 1, background: generalDeadlineBg, borderRadius: '4px', padding: '3px 6px', minWidth: 0 }">
          <div style="font-size: 8px; color: #888; font-weight: bold; line-height: 1.3">
            Общий
          </div>
          <div :style="{ fontSize: '10px', color: generalDeadlineColor, fontWeight: 'bold', lineHeight: '1.3', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }">
            {{ generalDeadlineText }}
          </div>
        </div>
        <!-- Дедлайн текущего подэтапа (справа, если есть) -->
        <div v-if="substepDeadlineText" :style="{ flex: 1, background: substepDeadlineBg, borderRadius: '4px', padding: '3px 6px', minWidth: 0 }">
          <div style="font-size: 8px; color: #888; font-weight: bold; line-height: 1.3">
            Подэтап
          </div>
          <div :style="{ fontSize: '10px', color: substepDeadlineColor, fontWeight: 'bold', lineHeight: '1.3', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }">
            {{ substepDeadlineText }}
          </div>
        </div>
      </div>

      <!-- 10. Индикатор "Работа сдана" (скрыт в архиве) -->
      <div v-if="workSubmittedText && !isArchived" class="q-mb-xs" style="background: #27AE60; color: white; font-size: 10px; padding: 4px 8px; border-radius: 4px">
        {{ workSubmittedText }}
      </div>

      <!-- Кнопки действий (скрыты в архиве) -->
      <div v-if="!isArchived" class="q-mt-xs" style="border-top: 1px solid #E0E0E0; padding-top: 6px">
        <!-- Строка 1: Workflow кнопки -->
        <div v-if="canSubmitWork" class="q-mb-xs">
          <q-btn
            unelevated
            dense
            no-caps
            label="Сдать работу"
            icon="check"
            style="background: #58D68D; color: white; font-size: 11px; font-weight: bold; padding: 4px 12px; height: 32px; border-radius: 4px; width: 100%"
            @click.stop="emit('submit-work')"
          />
        </div>
        <div v-if="showWaitReview" class="q-mb-xs" style="background: #FFF3E0; color: #E67E22; font-size: 11px; font-weight: bold; padding: 6px 12px; border-radius: 4px; text-align: center; border: 1px solid #F39C12">
          Ожидайте проверку
        </div>
        <div v-if="canApprove" class="row q-gutter-xs q-mb-xs">
          <q-btn
            unelevated
            dense
            no-caps
            label="Клиенту"
            style="background: #58D68D; color: white; font-size: 11px; font-weight: bold; height: 32px; border-radius: 4px; flex: 1"
            @click.stop="emit('client-send')"
          />
          <q-btn
            unelevated
            dense
            no-caps
            label="Исправление"
            style="background: #F1948A; color: white; font-size: 11px; font-weight: bold; height: 32px; border-radius: 4px; flex: 1"
            @click.stop="emit('reject')"
          />
        </div>
        <div v-if="canClientApproved" class="q-mb-xs">
          <q-btn
            unelevated
            dense
            no-caps
            label="Получен ответ от клиента"
            style="background: #27AE60; color: white; font-size: 11px; font-weight: bold; height: 32px; border-radius: 4px; width: 100%"
            @click.stop="emit('client-approved')"
          />
        </div>
        <!-- Решение после согласования клиента (pending_decision) -->
        <div v-if="canPendingDecision" class="q-mb-xs">
          <div style="font-size: 9px; color: #888; text-align: center; margin-bottom: 3px">
            Клиент согласовал. Выберите действие:
          </div>
          <div class="row q-gutter-xs q-mb-xs">
            <q-btn
              unelevated
              dense
              no-caps
              icon="skip_next"
              label="Следующий подэтап"
              style="background: #5DADE2; color: white; font-size: 10px; font-weight: bold; height: 30px; border-radius: 4px; flex: 1"
              @click.stop="emit('advance-round')"
            />
            <q-btn
              unelevated
              dense
              no-caps
              icon="done_all"
              label="Закрыть этап"
              style="background: #27AE60; color: white; font-size: 10px; font-weight: bold; height: 30px; border-radius: 4px; flex: 1"
              @click.stop="emit('close-stage')"
            />
          </div>
          <q-btn
            unelevated
            dense
            no-caps
            icon="add_circle_outline"
            label="Доп. круг"
            style="background: #D5D8DC; color: #333; font-size: 10px; font-weight: bold; height: 28px; border-radius: 4px; width: 100%"
            @click.stop="emit('add-extra-round')"
          />
        </div>
        <div v-if="canSignAct" class="row q-gutter-xs q-mb-xs">
          <q-btn
            unelevated
            dense
            no-caps
            label="Отправить акт"
            style="background: #58D68D; color: white; font-size: 11px; font-weight: bold; height: 32px; border-radius: 4px; flex: 1"
            @click.stop="emit('send-act')"
          />
          <q-btn
            unelevated
            dense
            no-caps
            label="Акт подписан"
            style="background: #85C1E9; color: white; font-size: 11px; font-weight: bold; height: 32px; border-radius: 4px; flex: 1"
            @click.stop="emit('sign-act')"
          />
        </div>

        <!-- Строка 2: Добавить замер / ТЗ -->
        <div v-if="showAddMeasurement || showAddTechTask" style="display: flex; gap: 4px; margin-bottom: 4px">
          <button v-if="showAddMeasurement" class="crm-add-btn crm-add-measurement" @click.stop="emit('add-measurement')">
            <span class="material-icons" style="font-size: 14px; flex-shrink: 0; line-height: 1">photo_camera</span>
            Добавить замер
          </button>
          <button v-if="showAddTechTask" class="crm-add-btn crm-add-techtask" @click.stop="emit('add-tech-task')">
            <span class="material-icons" style="font-size: 14px; flex-shrink: 0; line-height: 1">description</span>
            Добавить ТЗ
          </button>
        </div>

        <!-- Строка 3: Данные карточки -->
        <div class="q-mb-xs">
          <q-btn
            flat
            dense
            no-caps
            icon="open_in_new"
            label="Данные карточки"
            style="color: #333; font-size: 11px; height: 28px; width: 100%; background: #F5F5F5; border-radius: 4px"
            @click="emit('click')"
          />
        </div>

        <!-- Строка 4: Переместить -->
        <div>
          <q-btn
            flat
            dense
            no-caps
            icon="swap_horiz"
            label="Переместить"
            style="color: #888; font-size: 10px; height: 24px; width: 100%"
            @click="emit('longpress')"
          />
        </div>
      </div>

      <!-- Архив: только кнопка открытия -->
      <div v-else class="q-mt-xs" style="border-top: 1px solid #E0E0E0; padding-top: 6px">
        <q-btn
          flat
          dense
          no-caps
          icon="open_in_new"
          label="Данные карточки"
          style="color: #333; font-size: 11px; height: 28px; width: 100%; background: #F5F5F5; border-radius: 4px"
          @click="emit('click')"
        />
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useReferencesStore } from 'src/stores/references'
import { useAuthStore } from 'src/stores/auth'
import { usePermission } from 'src/composables/usePermission'
import { addWorkingDays, countWorkingDaysUntil } from 'src/composables/useDeadline'

const props = defineProps({
  card: { type: Object, required: true },
  isMuted: { type: Boolean, default: false },
})
const emit = defineEmits(['click', 'longpress', 'submit-work', 'reject', 'client-send', 'client-approved', 'sign-act', 'send-act', 'add-measurement', 'add-tech-task', 'advance-round', 'close-stage', 'add-extra-round', 'toggle-mute'])

function parseCrmTags(tagsStr) {
  if (!tagsStr) return []
  try {
    const parsed = JSON.parse(tagsStr)
    if (Array.isArray(parsed)) return parsed.map(t => ({ text: String(t.text || ''), color: String(t.color || '#FF6B6B') }))
    return [{ text: String(tagsStr), color: '#FF6B6B' }]
  } catch { return [{ text: String(tagsStr), color: '#FF6B6B' }] }
}

const showTeam = ref(false)
const refs = useReferencesStore()
const auth = useAuthStore()
const { can } = usePermission()

const agentColor = computed(() => refs.agentByName(props.card.agent_type)?.color || '#95A5A6')

// Архивный режим
const ARCHIVE_COLUMNS = ['Выполненный проект', 'СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР']
const isArchived = computed(() => ARCHIVE_COLUMNS.includes(props.card.column_name))
const archiveCardStyle = computed(() => {
  const col = props.card.column_name || ''
  const cs = props.card.contract_status || ''
  if (col === 'РАСТОРГНУТ') return { background: '#FADBD8', borderColor: '#E74C3C' }
  if (col.includes('НАДЗОР') || cs === 'АВТОРСКИЙ НАДЗОР') return { background: '#E3F2FD', borderColor: '#2196F3' }
  if (col === 'Выполненный проект' || col === 'СДАН') return { background: '#E8F8F5', borderColor: '#27AE60' }
  return {}
})

// === Workflow status → текст + цвет ===
const ws = computed(() => props.card.workflow_status)
const workStatusText = computed(() => {
  const m = { pending_review: 'Ожидает проверки', revision: 'На исправлении', client_approval: 'Клиент согласовывает', act_signing: 'Подписание акта', stage_completed: 'Стадия завершена', in_progress: 'В работе' }
  return m[ws.value] || null
})
const workStatusColor = computed(() => {
  const m = { pending_review: '#8E44AD', revision: '#E74C3C', client_approval: '#3498DB', act_signing: '#9B59B6', stage_completed: '#27AE60', in_progress: '#F39C12' }
  return m[ws.value] || '#888'
})

// === Подэтап: ВСЕГДА показывается если есть ===
const substepPrefix = computed(() => {
  const m = { pending_review: 'Проверка: ', revision: 'Исправление: ', client_approval: 'Согласование: ', act_signing: 'Акт: ', stage_completed: 'Завершено: ' }
  return m[ws.value] || ''
})
const substepColor = computed(() => {
  const m = { pending_review: '#8E44AD', revision: '#E74C3C', client_approval: '#3498DB', act_signing: '#9B59B6', stage_completed: '#27AE60' }
  return m[ws.value] || '#E67E22'
})

// === Команда с подсветкой ===
const teamMembers = computed(() => {
  const c = props.card
  const col = (c.column_name || '').toLowerCase()
  const wf = c.workflow_status
  const pt = c.project_type || ''
  const items = []

  // Управленческие роли: жёлтый по статусу workflow
  const mgmtIsActive = (roleKey) => {
    if (wf === 'pending_review') return pt === 'Шаблонный' ? roleKey === 'gap' : roleKey === 'sdp'
    if (wf === 'pending_decision') return roleKey === 'gap'
    return false
  }
  const addMgmt = (label, name, roleKey) => {
    if (!name) return
    const bg = mgmtIsActive(roleKey) ? '#FFE082' : 'transparent'
    items.push({ text: `${label}: ${name}`, bg })
  }

  // Исполнители стадий: жёлтый если текущая колонка совпадает и стадия не завершена
  const addStage = (label, name, completed, colSubstr) => {
    if (!name) return
    const isCurrent = !completed && col.includes(colSubstr)
    const bg = completed ? '#C8E6C9' : isCurrent ? '#FFE082' : 'transparent'
    items.push({ text: `${label}: ${name}${completed ? ' ✓' : ''}`, bg })
  }

  addMgmt('СМ', c.senior_manager_name, 'senior_manager')
  if (c.sdp_name) addMgmt('СДП', c.sdp_name, 'sdp')
  addMgmt('ГАП', c.gap_name, 'gap')
  addMgmt('Менеджер', c.manager_name, 'manager')
  addMgmt('Замерщик', c.surveyor_name, 'surveyor')

  addStage('Стадия 1', c.stage_plan_name, c.stage_plan_completed, 'планировочн')
  if (pt === 'Шаблонный') {
    addStage('Стадия 2', c.draftsman_name, c.draftsman_completed, 'чертеж')
    addStage('Стадия 3', c.designer_name, c.designer_completed, 'визуализац')
  } else {
    addStage('Стадия 2', c.designer_name, c.designer_completed, 'концепция')
    addStage('Стадия 3', c.draftsman_name, c.draftsman_completed, 'чертеж')
  }

  return items
})

// === Дедлайн: два блока — общий + подэтап ===

// Вспомогательные функции форматирования
function _deadlineDaysColor(days) {
  if (days === null) return '#888'
  if (days < 0) return '#8B0000'
  if (days === 0) return '#DC143C'
  if (days <= 1) return '#E74C3C'
  if (days <= 2) return '#F39C12'
  return '#888'
}
function _deadlineDaysBg(days) {
  if (days === null) return '#F5F5F5'
  if (days < 0) return '#FFEBEE'
  if (days <= 2) return '#FFF8E1'
  return '#F5F5F5'
}

// Левый блок: Общий дедлайн заказа — из card.deadline или вычисленный из contract_period
const effectiveDeadline = computed(() => {
  if (props.card.deadline) return props.card.deadline
  const period = props.card.contract_period
  if (!period || period <= 0) return null
  const dates = []
  if (props.card.contract_date) dates.push(props.card.contract_date)
  if (props.card.survey_date) dates.push(props.card.survey_date)
  if (props.card.tech_task_date) dates.push(props.card.tech_task_date)
  if (!dates.length) return null
  const latest = [...dates].sort().at(-1)
  return addWorkingDays(latest, period)
})
const generalDeadlineDays = computed(() => {
  if (!effectiveDeadline.value) return null
  return countWorkingDaysUntil(effectiveDeadline.value)
})
const generalDeadlineText = computed(() => {
  if (generalDeadlineDays.value === null) return null
  const d = new Date(effectiveDeadline.value).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: '2-digit' })
  const days = generalDeadlineDays.value
  if (days < 0) return `${d} (−${Math.abs(days)}р.д.)`
  if (days === 0) return `${d} Сегодня!`
  return `${d} (${days}р.д.)`
})
const generalDeadlineColor = computed(() => _deadlineDaysColor(generalDeadlineDays.value))
const generalDeadlineBg = computed(() => _deadlineDaysBg(generalDeadlineDays.value))

// Правый блок: Дедлайн подэтапа — предпочитаем дедлайн исполнителя (current_stage_deadline),
// иначе плановый из тайм-лайна (current_substep_deadline)
const substepDeadlineDays = computed(() => {
  const deadline = props.card.current_stage_deadline || props.card.current_substep_deadline
  if (!deadline) return null
  return countWorkingDaysUntil(deadline)
})
const substepDeadlineText = computed(() => {
  const deadline = props.card.current_stage_deadline || props.card.current_substep_deadline
  if (!deadline || substepDeadlineDays.value === null) return null
  const d = new Date(deadline).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: '2-digit' })
  const days = substepDeadlineDays.value
  if (days < 0) return `${d} (−${Math.abs(days)}р.д.)`
  if (days === 0) return `${d} Сегодня!`
  return `${d} (${days}р.д.)`
})
const substepDeadlineColor = computed(() => _deadlineDaysColor(substepDeadlineDays.value))
const substepDeadlineBg = computed(() => _deadlineDaysBg(substepDeadlineDays.value))

// === Индикатор "Работа сдана" (для проверяющих) ===
const workSubmittedText = computed(() => {
  if (!can('crm_cards.complete_approval')) return null
  if (ws.value === 'act_signing' || ws.value === 'stage_completed') return null
  const c = props.card
  const col = (c.column_name || '').toLowerCase()
  const parts = []
  if (col.includes('планировочн')) {
    if (c.stage_plan_completed) parts.push(`Стадия 1: ${c.stage_plan_name}`)
  } else if (col.includes('концепция') || col.includes('визуализац')) {
    if (c.designer_completed) parts.push(`Стадия 2: ${c.designer_name}`)
  } else if (col.includes('чертеж') || col.includes('чертёж')) {
    if (c.draftsman_completed) parts.push(`Стадия 3: ${c.draftsman_name}`)
  }
  return parts.length > 0 ? `Работа сдана: ${parts.join(', ')}` : null
})

// === Кнопки по ролям ===
const empName = computed(() => auth.user?.full_name || '')
const empPos = computed(() => auth.user?.position || '')

const canSubmitWork = computed(() => {
  if (ws.value && ws.value !== 'in_progress' && ws.value !== 'active' && ws.value !== 'revision') return false
  const c = props.card
  if (empPos.value === 'Дизайнер' && c.stage_plan_name === empName.value && !c.stage_plan_completed) return true
  if (empPos.value === 'Дизайнер' && c.designer_name === empName.value && !c.designer_completed) return true
  if ((empPos.value === 'Чертёжник' || auth.user?.secondary_position === 'Чертёжник') && c.draftsman_name === empName.value && !c.draftsman_completed) return true
  return false
})
const showWaitReview = computed(() => {
  if (ws.value !== 'pending_review') return false
  const c = props.card
  if (empPos.value === 'Дизайнер' && (c.stage_plan_name === empName.value || c.designer_name === empName.value)) return true
  if (empPos.value === 'Чертёжник' && c.draftsman_name === empName.value) return true
  return false
})
const canApprove = computed(() => ws.value === 'pending_review' && can('crm_cards.complete_approval'))
const canClientApproved = computed(() => ws.value === 'client_approval' && can('crm_cards.complete_approval'))
const canPendingDecision = computed(() => ws.value === 'pending_decision' && can('crm_cards.complete_approval'))
const canSignAct = computed(() => ws.value === 'act_signing' && can('crm_cards.complete_approval'))

// Добавить замер: нет measurement_image_link И нет survey_date + (crm_cards.update ИЛИ замерщик)
const isSurveyor = computed(() => empPos.value === 'Замерщик')
const showAddMeasurement = computed(() => {
  const c = props.card
  const hasMeas = c.measurement_image_link || c.survey_date
  return !hasMeas && (can('crm_cards.update') || isSurveyor.value)
})
// Добавить ТЗ: нет tech_task_link И нет tech_task_file + crm_cards.update + не замерщик
const showAddTechTask = computed(() => {
  const c = props.card
  const hasTT = c.tech_task_link || c.tech_task_file
  return !hasTT && can('crm_cards.update') && !isSurveyor.value
})
</script>

<style scoped>
.crm-card { border: 2px solid #CCCCCC; border-radius: 8px; background: white; }
.crm-card:active { border-color: #909090; background: #f5f5f5; }

.crm-add-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  flex: 1;
  min-height: 28px;
  padding: 4px 6px;
  border: none;
  border-radius: 4px;
  color: white;
  font-size: 10px;
  font-weight: bold;
  cursor: pointer;
  font-family: inherit;
  white-space: normal;
  word-break: break-word;
  line-height: 1.3;
  text-align: center;
}
.crm-add-measurement { background: #F39C12; }
.crm-add-techtask { background: #9B59B6; }

.mute-bell-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  padding: 2px;
  cursor: pointer;
  line-height: 1;
}
</style>
