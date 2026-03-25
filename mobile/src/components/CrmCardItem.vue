<template>
  <q-card flat bordered class="crm-card q-mb-sm">
    <q-card-section class="q-pa-sm">
      <!-- Верхняя строка: номер + workflow status -->
      <div class="row items-center justify-between q-mb-xs">
        <div class="text-caption" style="color: #888; font-size: 10px">
          Договор: {{ card.contract_number || `#${card.id}` }}
        </div>
        <q-chip v-if="card.workflow_status && card.workflow_status !== 'active'" dense size="xs"
          :color="substepColor" text-color="white" style="font-size: 9px">
          {{ workflowLabel }}
        </q-chip>
      </div>

      <!-- Адрес + Агент (агент справа, крупный) -->
      <div class="row items-start justify-between q-mb-xs">
        <div class="text-weight-bold ellipsis-2-lines" style="font-size: 14px; color: #222; flex: 1">
          {{ card.address || 'Без адреса' }}
        </div>
        <span v-if="card.agent_type" class="agent-badge q-ml-xs" :style="{ background: agentBadgeColor, padding: '4px 10px', fontSize: '11px', lineHeight: '16px' }" style="white-space: nowrap; flex-shrink: 0">
          {{ card.agent_type }}
        </span>
      </div>

      <!-- Разделитель -->
      <div style="height: 1px; background: #DDDDDD" class="q-mb-xs" />

      <!-- Подэтап -->
      <div v-if="card.current_substep_name" class="q-mb-xs" :style="{ color: substepTextColor, fontSize: '9px', fontWeight: 'bold' }">
        {{ card.current_substep_name }}
      </div>

      <!-- Правки -->
      <div v-if="card.revision_count > 0" style="font-size: 9px; color: #E74C3C; font-weight: bold" class="q-mb-xs">
        Правки: {{ card.revision_count }}
      </div>

      <!-- Площадь, Город -->
      <div class="row items-center q-gutter-xs q-mb-xs" style="font-size: 11px; color: #888">
        <span v-if="card.area">{{ card.area }} м²</span>
        <span v-if="card.city">{{ card.city }}</span>
      </div>

      <!-- Команда (в рамке, не проваливается — stopPropagation) -->
      <div v-if="teamNames.length > 0" style="border: 1px solid #E0E0E0; border-radius: 4px; padding: 4px 6px; margin-bottom: 4px" @click.stop>
        <div style="font-size: 10px; color: #888; font-weight: bold; margin-bottom: 2px; cursor: pointer" @click="showTeam = !showTeam">
          Команда {{ showTeam ? '▲' : '▼' }}
        </div>
        <div v-if="showTeam">
          <div v-for="m in teamNames" :key="m" style="font-size: 10px; color: #666">{{ m }}</div>
        </div>
      </div>

      <!-- Теги (крупные, как блок Команда) -->
      <div v-if="card.tags" class="q-mt-xs" style="border: 1px solid #FFCDD2; border-radius: 4px; padding: 4px 6px; background: #FFF5F5">
        <q-badge v-for="tag in card.tags.split(',')" :key="tag" color="red-2" text-color="red-8" :label="tag.trim()" class="q-mr-xs" style="font-size: 11px; padding: 3px 8px" />
      </div>

      <!-- Дедлайн -->
      <div v-if="card.deadline" class="q-mt-xs row items-center q-gutter-xs">
        <q-icon name="schedule" size="12px" :color="deadlineColor" />
        <span :style="{ fontSize: '10px', color: deadlineHexColor, fontWeight: 'bold' }">
          {{ formatDate(card.deadline) }} ({{ daysLeftText }})
        </span>
      </div>

      <!-- Кнопки действий -->
      <div class="q-mt-sm row q-gutter-xs" style="border-top: 1px solid #E0E0E0; padding-top: 6px">
        <q-btn flat dense no-caps size="sm" icon="open_in_new" label="Данные проекта" style="color: #333; font-size: 10px; flex: 1" @click="emit('click')" />
        <q-btn flat dense no-caps size="sm" icon="swap_horiz" label="Переместить" style="color: #888; font-size: 10px" @click="emit('longpress')" />
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useReferencesStore } from 'src/stores/references'

const props = defineProps({ card: { type: Object, required: true } })
const emit = defineEmits(['click', 'longpress'])

const showTeam = ref(false)

const refs = useReferencesStore()

const agentBadgeColor = computed(() => {
  const agent = refs.agentByName(props.card.agent_type)
  return agent?.color || '#95A5A6'
})

const teamNames = computed(() => {
  const c = props.card
  return [
    c.senior_manager_name && `СМ: ${c.senior_manager_name}`,
    c.sdp_name && `СДП: ${c.sdp_name}`,
    c.gap_name && `ГАП: ${c.gap_name}`,
    c.manager_name && `Менеджер: ${c.manager_name}`,
    c.designer_name && `Дизайнер: ${c.designer_name}`,
    c.draftsman_name && `Чертёжник: ${c.draftsman_name}`
  ].filter(Boolean)
})

const substepColor = computed(() => {
  const m = { pending_review: 'purple', revision: 'negative', client_approval: 'info', act_signing: 'purple', stage_completed: 'positive' }
  return m[props.card.workflow_status] || 'orange'
})

const substepTextColor = computed(() => {
  const m = { pending_review: '#8E44AD', revision: '#E74C3C', client_approval: '#3498DB', act_signing: '#9B59B6', stage_completed: '#27AE60' }
  return m[props.card.workflow_status] || '#E67E22'
})

const workflowLabel = computed(() => {
  const m = { pending_review: 'Проверка', revision: 'Исправление', client_approval: 'У клиента', act_signing: 'Акт', stage_completed: 'Завершено' }
  return m[props.card.workflow_status] || ''
})

const deadlineColor = computed(() => {
  if (!props.card.deadline) return 'grey'
  const days = Math.ceil((new Date(props.card.deadline) - new Date()) / 86400000)
  if (days < 0) return 'negative'
  if (days <= 2) return 'warning'
  return 'grey-5'
})

const deadlineHexColor = computed(() => {
  if (!props.card.deadline) return '#E0E0E0'
  const days = Math.ceil((new Date(props.card.deadline) - new Date()) / 86400000)
  if (days < 0) return '#8B0000'
  if (days === 0) return '#DC143C'
  if (days <= 1) return '#E74C3C'
  if (days <= 2) return '#F39C12'
  return '#E0E0E0'
})

const daysLeftText = computed(() => {
  if (!props.card.deadline) return ''
  const days = Math.ceil((new Date(props.card.deadline) - new Date()) / 86400000)
  if (days < 0) return `${Math.abs(days)} дн. просрочено`
  if (days === 0) return 'сегодня'
  return `${days} дн.`
})

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}
</script>

<style scoped>
.crm-card {
  border: 2px solid #CCCCCC;
  border-radius: 8px;
  background: white;
}
.crm-card:active {
  border-color: #909090;
  background: #f5f5f5;
}
</style>
