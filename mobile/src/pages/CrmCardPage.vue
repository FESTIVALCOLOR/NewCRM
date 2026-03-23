<template>
  <q-page padding>
    <!-- Загрузка -->
    <div v-if="crmStore.cardLoading" class="q-pa-md">
      <q-skeleton type="rect" height="200px" class="q-mb-md" />
      <q-skeleton type="text" width="80%" class="q-mb-sm" />
      <q-skeleton type="text" width="60%" />
    </div>

    <template v-else-if="card">
      <!-- Шапка карточки -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="row items-center justify-between q-mb-sm">
            <div class="text-h6 text-weight-bold">{{ card.contract_number }}</div>
            <q-badge
              :color="statusColor(card.column_name)"
              :label="card.column_name"
            />
          </div>
          <div class="text-body1 q-mb-xs">{{ card.address }}</div>
          <div class="row q-gutter-md text-caption text-grey-7">
            <span v-if="card.area"><q-icon name="square_foot" size="14px" /> {{ card.area }} м²</span>
            <span v-if="card.city"><q-icon name="location_on" size="14px" /> {{ card.city }}</span>
            <span v-if="card.floors"><q-icon name="layers" size="14px" /> {{ card.floors }} эт.</span>
          </div>
        </q-card-section>
      </q-card>

      <!-- Клиент -->
      <q-card class="is-card q-mb-md" v-if="card.client_name">
        <q-card-section>
          <div class="text-caption text-grey-7 q-mb-xs">Клиент</div>
          <div class="text-subtitle2 text-weight-bold">{{ card.client_name }}</div>
          <div class="text-caption text-grey-7" v-if="card.agent_type">{{ card.agent_type }}</div>
        </q-card-section>
      </q-card>

      <!-- Команда проекта -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Команда</div>
        </q-card-section>
        <q-list dense>
          <q-item v-for="member in teamMembers" :key="member.role" v-show="member.name">
            <q-item-section avatar>
              <q-avatar size="32px" color="grey-3" text-color="grey-8">
                {{ member.name ? member.name[0] : '?' }}
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ member.name }}</q-item-label>
              <q-item-label caption>{{ member.role }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Дедлайны -->
      <q-card class="is-card q-mb-md" v-if="card.deadline || card.designer_deadline || card.draftsman_deadline">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Сроки</div>
        </q-card-section>
        <q-list dense>
          <q-item v-if="card.deadline">
            <q-item-section avatar><q-icon name="event" color="grey-7" /></q-item-section>
            <q-item-section>
              <q-item-label>Общий дедлайн</q-item-label>
              <q-item-label caption>{{ formatDate(card.deadline) }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item v-if="card.designer_deadline">
            <q-item-section avatar><q-icon name="palette" color="grey-7" /></q-item-section>
            <q-item-section>
              <q-item-label>Дизайнер: {{ card.designer_name || '—' }}</q-item-label>
              <q-item-label caption>
                {{ formatDate(card.designer_deadline) }}
                <q-badge v-if="card.designer_completed" color="positive" label="Выполнено" dense class="q-ml-xs" />
              </q-item-label>
            </q-item-section>
          </q-item>
          <q-item v-if="card.draftsman_deadline">
            <q-item-section avatar><q-icon name="draw" color="grey-7" /></q-item-section>
            <q-item-section>
              <q-item-label>Чертёжник: {{ card.draftsman_name || '—' }}</q-item-label>
              <q-item-label caption>
                {{ formatDate(card.draftsman_deadline) }}
                <q-badge v-if="card.draftsman_completed" color="positive" label="Выполнено" dense class="q-ml-xs" />
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Стадии исполнителей -->
      <q-card class="is-card q-mb-md" v-if="card.stage_executors?.length">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Стадии</div>
        </q-card-section>
        <q-list dense separator>
          <q-item v-for="stage in card.stage_executors" :key="stage.id">
            <q-item-section avatar>
              <q-icon
                :name="stage.completed ? 'check_circle' : 'radio_button_unchecked'"
                :color="stage.completed ? 'positive' : 'grey-5'"
              />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ stage.stage_name }}</q-item-label>
              <q-item-label caption>
                {{ stage.executor_name }}
                <span v-if="stage.deadline"> — до {{ formatDate(stage.deadline) }}</span>
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Файлы -->
      <q-card class="is-card q-mb-md" v-if="hasFiles">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Файлы</div>
        </q-card-section>
        <q-list dense>
          <q-item v-if="card.tech_task_link" clickable @click="openLink(card.tech_task_link)">
            <q-item-section avatar><q-icon name="description" color="blue" /></q-item-section>
            <q-item-section>
              <q-item-label>{{ card.tech_task_file || 'Техническое задание' }}</q-item-label>
            </q-item-section>
            <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
          </q-item>
          <q-item v-if="card.measurement_image_link" clickable @click="openLink(card.measurement_image_link)">
            <q-item-section avatar><q-icon name="straighten" color="orange" /></q-item-section>
            <q-item-section>
              <q-item-label>{{ card.measurement_file_name || 'Замер' }}</q-item-label>
            </q-item-section>
            <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
          </q-item>
          <q-item v-if="card.project_data_link" clickable @click="openLink(card.project_data_link)">
            <q-item-section avatar><q-icon name="folder" color="amber" /></q-item-section>
            <q-item-section>
              <q-item-label>Данные проекта</q-item-label>
            </q-item-section>
            <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- FAB действий -->
      <q-page-sticky position="bottom-right" :offset="[18, 18]">
        <q-btn fab icon="more_vert" color="primary" @click="showActions = true" />
      </q-page-sticky>

      <crm-actions-sheet v-model="showActions" :card="card" @updated="reloadCard" />
    </template>

    <!-- Не найдено -->
    <div v-else class="text-center q-pa-xl text-grey-5">
      <q-icon name="search_off" size="48px" class="q-mb-sm" />
      <div>Карточка не найдена</div>
      <q-btn flat color="primary" label="Назад" @click="$router.back()" class="q-mt-md" no-caps />
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useCrmStore } from 'src/stores/crm'
import CrmActionsSheet from 'src/components/CrmActionsSheet.vue'

const route = useRoute()
const crmStore = useCrmStore()
const card = computed(() => crmStore.selectedCard)
const showActions = ref(false)

function reloadCard() {
  const cardId = route.params.id
  if (cardId) crmStore.loadCard(cardId)
}

const teamMembers = computed(() => {
  if (!card.value) return []
  return [
    { role: 'Ст. менеджер', name: card.value.senior_manager_name },
    { role: 'СДП', name: card.value.sdp_name },
    { role: 'ГАП', name: card.value.gap_name },
    { role: 'Менеджер', name: card.value.manager_name },
    { role: 'Замерщик', name: card.value.surveyor_name },
    { role: 'Дизайнер', name: card.value.designer_name },
    { role: 'Чертёжник', name: card.value.draftsman_name }
  ].filter(m => m.name)
})

const hasFiles = computed(() =>
  card.value && (card.value.tech_task_link || card.value.measurement_image_link || card.value.project_data_link)
)

function statusColor(columnName) {
  if (!columnName) return 'grey'
  if (columnName.includes('Новый')) return 'blue'
  if (columnName.includes('согласовани')) return 'purple'
  if (columnName.includes('работе') || columnName.includes('Стадия')) return 'orange'
  if (columnName.includes('Согласовано') || columnName.includes('Сдан')) return 'positive'
  return 'grey'
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'short', year: 'numeric'
  })
}

function openLink(url) {
  if (url) window.open(url, '_blank')
}

onMounted(() => {
  const cardId = route.params.id
  if (cardId) {
    crmStore.loadCard(cardId)
  }
})
</script>
