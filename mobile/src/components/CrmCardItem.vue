<template>
  <q-card flat bordered class="crm-card q-mb-sm" :style="archiveCardStyle">
    <q-card-section class="q-pa-sm">
      <!-- 1. Верхняя строка: номер + статус работы -->
      <div class="row items-center justify-between q-mb-xs">
        <div style="color: #888; font-size: 10px">Договор: {{ card.contract_number || `#${card.id}` }}</div>
        <div v-if="workStatusText" :style="{ fontSize: '8px', fontWeight: 'bold', color: workStatusColor, border: `1px solid ${workStatusColor}`, borderRadius: '3px', padding: '1px 6px' }">
          {{ workStatusText }}
        </div>
      </div>

      <!-- 2. Адрес -->
      <div class="text-weight-bold q-mb-xs" style="font-size: 14px; color: #222; word-wrap: break-word; max-height: 50px; overflow: hidden">
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
      <div v-if="card.tags" class="q-mb-xs" style="background: #FF6B6B; border-radius: 4px; padding: 3px 8px">
        <span style="color: white; font-size: 10px">{{ card.tags }}</span>
      </div>

      <!-- 9. Дедлайн (скрыт в архиве) -->
      <div v-if="deadlineText && !isArchived" class="q-mb-xs row items-center q-gutter-xs" :style="{ background: deadlineBg, borderRadius: '4px', padding: '3px 8px', height: '28px', width: '100%' }">
        <q-icon name="schedule" size="10px" :style="{ color: deadlineTextColor }" />
        <span :style="{ fontSize: '10px', color: deadlineTextColor, fontWeight: 'bold' }">{{ deadlineText }}</span>
      </div>

      <!-- 10. Индикатор "Работа сдана" (скрыт в архиве) -->
      <div v-if="workSubmittedText && !isArchived" class="q-mb-xs" style="background: #27AE60; color: white; font-size: 10px; padding: 4px 8px; border-radius: 4px">
        {{ workSubmittedText }}
      </div>

      <!-- Кнопки действий (скрыты в архиве) -->
      <div v-if="!isArchived" class="q-mt-xs" style="border-top: 1px solid #E0E0E0; padding-top: 6px">
        <!-- Строка 1: Workflow кнопки -->
        <div v-if="canSubmitWork" class="q-mb-xs">
          <q-btn unelevated dense no-caps label="Сдать работу" icon="check" style="background: #58D68D; color: white; font-size: 11px; font-weight: bold; padding: 4px 12px; height: 32px; border-radius: 4px; width: 100%" @click.stop="emit('submit-work')" />
        </div>
        <div v-if="showWaitReview" class="q-mb-xs" style="background: #FFF3E0; color: #E67E22; font-size: 11px; font-weight: bold; padding: 6px 12px; border-radius: 4px; text-align: center; border: 1px solid #F39C12">
          Ожидайте проверку
        </div>
        <div v-if="canApprove" class="row q-gutter-xs q-mb-xs">
          <q-btn unelevated dense no-caps label="Клиенту" style="background: #58D68D; color: white; font-size: 11px; font-weight: bold; height: 32px; border-radius: 4px; flex: 1" @click.stop="emit('client-send')" />
          <q-btn unelevated dense no-caps label="Исправление" style="background: #F1948A; color: white; font-size: 11px; font-weight: bold; height: 32px; border-radius: 4px; flex: 1" @click.stop="emit('reject')" />
        </div>
        <div v-if="canClientApproved" class="q-mb-xs">
          <q-btn unelevated dense no-caps label="Клиент согласовал" style="background: #27AE60; color: white; font-size: 11px; font-weight: bold; height: 32px; border-radius: 4px; width: 100%" @click.stop="emit('client-approved')" />
        </div>
        <div v-if="canSignAct" class="row q-gutter-xs q-mb-xs">
          <q-btn unelevated dense no-caps label="Отправить акт" style="background: #58D68D; color: white; font-size: 11px; font-weight: bold; height: 32px; border-radius: 4px; flex: 1" @click.stop="emit('client-send')" />
          <q-btn unelevated dense no-caps label="Акт подписан" style="background: #85C1E9; color: white; font-size: 11px; font-weight: bold; height: 32px; border-radius: 4px; flex: 1" @click.stop="emit('sign-act')" />
        </div>

        <!-- Строка 2: Добавить замер / ТЗ -->
        <div v-if="showAddMeasurement || showAddTechTask" class="row q-gutter-xs q-mb-xs">
          <q-btn v-if="showAddMeasurement" unelevated dense no-caps icon="photo_camera" label="Добавить замер" style="background: #F39C12; color: white; font-size: 10px; font-weight: bold; height: 28px; border-radius: 4px; flex: 1" @click.stop="emit('add-measurement')" />
          <q-btn v-if="showAddTechTask" unelevated dense no-caps icon="description" label="Добавить ТЗ" style="background: #9B59B6; color: white; font-size: 10px; font-weight: bold; height: 28px; border-radius: 4px; flex: 1" @click.stop="emit('add-tech-task')" />
        </div>

        <!-- Строка 3: Данные карточки -->
        <div class="q-mb-xs">
          <q-btn flat dense no-caps icon="open_in_new" label="Данные карточки" style="color: #333; font-size: 11px; height: 28px; width: 100%; background: #F5F5F5; border-radius: 4px" @click="emit('click')" />
        </div>

        <!-- Строка 4: Переместить -->
        <div>
          <q-btn flat dense no-caps icon="swap_horiz" label="Переместить" style="color: #888; font-size: 10px; height: 24px; width: 100%" @click="emit('longpress')" />
        </div>
      </div>

      <!-- Архив: только кнопка открытия -->
      <div v-else class="q-mt-xs" style="border-top: 1px solid #E0E0E0; padding-top: 6px">
        <q-btn flat dense no-caps icon="open_in_new" label="Данные карточки" style="color: #333; font-size: 11px; height: 28px; width: 100%; background: #F5F5F5; border-radius: 4px" @click="emit('click')" />
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useReferencesStore } from 'src/stores/references'
import { useAuthStore } from 'src/stores/auth'
import { usePermission } from 'src/composables/usePermission'
import { countWorkingDaysUntil } from 'src/composables/useDeadline'

const props = defineProps({ card: { type: Object, required: true } })
const emit = defineEmits(['click', 'longpress', 'submit-work', 'reject', 'client-send', 'client-approved', 'sign-act', 'add-measurement', 'add-tech-task'])

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
  if (col === 'Выполненный проект' || col === 'СДАН') return { background: '#E8F8F5', borderColor: '#27AE60' }
  if (col === 'РАСТОРГНУТ') return { background: '#FADBD8', borderColor: '#E74C3C' }
  if (col.includes('НАДЗОР')) return { background: '#E3F2FD', borderColor: '#2196F3' }
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
  const empName = auth.user?.full_name || ''
  const items = []
  const add = (role, name, completed) => {
    if (!name) return
    const isCurrent = name === empName
    const bg = completed ? '#C8E6C9' : isCurrent ? '#FFE082' : 'transparent'
    items.push({ text: `${role}: ${name}${completed ? ' ✓' : ''}`, bg })
  }
  add('СМ', c.senior_manager_name)
  if (c.sdp_name) add('СДП', c.sdp_name)
  add('ГАП', c.gap_name)
  add('Менеджер', c.manager_name)
  add('Замерщик', c.surveyor_name)
  add('Дизайнер', c.designer_name, c.designer_completed)
  add('Чертёжник', c.draftsman_name, c.draftsman_completed)
  return items
})

// === Дедлайн: исполнителя стадии (как десктоп crm_tab.py:2306-2314) ===
const stageDeadline = computed(() => {
  const c = props.card
  const col = (c.column_name || '').toLowerCase()
  // Дизайнер — стадия 2 (концепция/визуализация)
  if ((col.includes('концепция') || col.includes('визуализац')) && c.designer_deadline)
    return c.designer_deadline
  // Чертёжник — стадия 1 (планировочные) или 3 (чертежи)
  if ((col.includes('планировочн') || col.includes('чертеж') || col.includes('чертёж')) && c.draftsman_deadline)
    return c.draftsman_deadline
  return c.deadline
})

// Рабочие дни (как десктоп — без выходных и праздников РФ)
const deadlineDays = computed(() => {
  if (!stageDeadline.value) return null
  return countWorkingDaysUntil(stageDeadline.value)
})
const deadlineText = computed(() => {
  if (deadlineDays.value === null) return null
  const d = new Date(stageDeadline.value).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
  const days = deadlineDays.value
  if (days < 0) return `${d} ПРОСРОЧЕН (${Math.abs(days)} раб.дн.)`
  if (days === 0) return `${d} СЕГОДНЯ!`
  return `${d} (${days} раб.дн.)`
})
const deadlineBg = computed(() => {
  const days = deadlineDays.value
  if (days === null) return 'transparent'
  if (days < 0) return '#FFEBEE'
  if (days <= 2) return '#FFF8E1'
  return '#F5F5F5'
})
const deadlineTextColor = computed(() => {
  const days = deadlineDays.value
  if (days === null) return '#888'
  if (days < 0) return '#8B0000'
  if (days === 0) return '#DC143C'
  if (days <= 1) return '#E74C3C'
  if (days <= 2) return '#F39C12'
  return '#888'
})

// === Индикатор "Работа сдана" (для проверяющих) ===
const workSubmittedText = computed(() => {
  if (!can('crm_cards.complete_approval')) return null
  if (ws.value === 'act_signing' || ws.value === 'stage_completed') return null
  const c = props.card
  const col = (c.column_name || '').toLowerCase()
  const parts = []
  if (col.includes('концепция') || col.includes('визуализац')) {
    if (c.designer_completed) parts.push(`Дизайнер ${c.designer_name}`)
  }
  if (col.includes('планировочн') || col.includes('чертеж') || col.includes('чертёж')) {
    if (c.draftsman_completed) parts.push(`Чертёжник ${c.draftsman_name}`)
  }
  return parts.length > 0 ? `Работа сдана: ${parts.join(', ')}` : null
})

// === Кнопки по ролям ===
const empName = computed(() => auth.user?.full_name || '')
const empPos = computed(() => auth.user?.position || '')

const canSubmitWork = computed(() => {
  if (ws.value && ws.value !== 'in_progress' && ws.value !== 'active' && ws.value !== 'revision') return false
  const c = props.card
  if (empPos.value === 'Дизайнер' && c.designer_name === empName.value && !c.designer_completed) return true
  if ((empPos.value === 'Чертёжник' || auth.user?.secondary_position === 'Чертёжник') && c.draftsman_name === empName.value && !c.draftsman_completed) return true
  return false
})
const showWaitReview = computed(() => {
  if (ws.value !== 'pending_review') return false
  const c = props.card
  if (empPos.value === 'Дизайнер' && c.designer_name === empName.value) return true
  if (empPos.value === 'Чертёжник' && c.draftsman_name === empName.value) return true
  return false
})
const canApprove = computed(() => ws.value === 'pending_review' && can('crm_cards.complete_approval'))
const canClientApproved = computed(() => ws.value === 'client_approval' && can('crm_cards.complete_approval'))
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
</style>
