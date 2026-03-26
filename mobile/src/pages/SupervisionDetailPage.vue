<template>
  <q-page padding>
    <div v-if="loading" class="q-pa-md">
      <q-skeleton type="rect" height="150px" class="q-mb-md" />
      <q-skeleton type="text" width="70%" />
      <q-skeleton type="text" width="50%" />
    </div>

    <template v-else-if="card">
      <!-- Шапка -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="row items-center justify-between q-mb-sm">
            <div class="text-h6 text-weight-bold">{{ card.contract_number }}</div>
            <q-badge
              :color="card.is_paused ? 'warning' : 'positive'"
              :label="card.is_paused ? 'Приостановлено' : card.column_name"
            />
          </div>
          <div class="text-body1 q-mb-xs">{{ card.address }}</div>
          <div class="row q-gutter-md text-caption text-grey-7">
            <span v-if="card.area"><q-icon name="square_foot" size="14px" /> {{ card.area }} м²</span>
            <span v-if="card.city"><q-icon name="location_on" size="14px" /> {{ card.city }}</span>
          </div>
        </q-card-section>
      </q-card>

      <!-- Команда -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Команда</div>
        </q-card-section>
        <q-list dense>
          <q-item v-if="card.dan_name">
            <q-item-section avatar>
              <q-avatar size="32px" color="orange-2" text-color="orange-8">{{ card.dan_name[0] }}</q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ card.dan_name }}</q-item-label>
              <q-item-label caption>ДАН</q-item-label>
            </q-item-section>
            <q-item-section side v-if="card.dan_completed">
              <q-icon name="check_circle" color="positive" />
            </q-item-section>
          </q-item>
          <q-item v-if="card.senior_manager_name">
            <q-item-section avatar>
              <q-avatar size="32px" color="blue-2" text-color="blue-8">{{ card.senior_manager_name[0] }}</q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ card.senior_manager_name }}</q-item-label>
              <q-item-label caption>Ст. менеджер</q-item-label>
            </q-item-section>
          </q-item>
          <q-item v-if="card.studio_director_name">
            <q-item-section avatar>
              <q-avatar size="32px" color="purple-2" text-color="purple-8">{{ card.studio_director_name[0] }}</q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ card.studio_director_name }}</q-item-label>
              <q-item-label caption>Руководитель студии</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Таблица сроков (стадии) -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="row items-center justify-between">
            <div class="text-subtitle2 text-weight-bold">Стадии закупок</div>
            <div class="row q-gutter-xs">
              <q-btn flat dense size="xs" icon="picture_as_pdf" color="grey-7" @click="exportTimelinePDF">
                <q-tooltip>Экспорт PDF</q-tooltip>
              </q-btn>
              <q-btn flat dense size="xs" icon="table_chart" color="grey-7" @click="exportTimelineExcel">
                <q-tooltip>Экспорт Excel</q-tooltip>
              </q-btn>
              <div class="text-caption text-grey-7" v-if="summary">{{ summary.total_site_visits }} выездов</div>
            </div>
          </div>
        </q-card-section>

        <q-list v-if="timeline.length > 0" dense separator>
          <q-item v-for="entry in timeline" :key="entry.id" clickable v-ripple @click="editTimelineEntry(entry)">
            <q-item-section avatar>
              <q-icon :name="stageIcon(entry.status)" :color="stageColor(entry.status)" size="20px" />
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-medium">
                {{ entry.stage_name.replace(/^Стадия \d+: /, '') }}
              </q-item-label>
              <q-item-label caption>
                <span v-if="entry.plan_date">План: {{ formatDate(entry.plan_date) }}</span>
                <span v-if="entry.actual_date"> | Факт: {{ formatDate(entry.actual_date) }}</span>
              </q-item-label>
              <q-item-label caption v-if="entry.supplier" style="color: #888">{{ entry.supplier }}</q-item-label>
              <q-item-label caption v-if="entry.budget_planned > 0" style="color: #888">
                Бюджет: {{ formatMoney(entry.budget_actual || 0) }} / {{ formatMoney(entry.budget_planned) }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge :color="stageColor(entry.status)" :label="entry.status" dense />
            </q-item-section>
          </q-item>
        </q-list>

        <q-card-section v-else class="text-center text-grey-5">
          Стадии не инициализированы
        </q-card-section>
      </q-card>

      <!-- Бюджет -->
      <q-card class="is-card q-mb-md" v-if="summary && summary.total_budget_planned > 0">
        <q-card-section>
          <div class="text-subtitle2 text-weight-bold q-mb-sm">Бюджет</div>
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <div class="text-caption text-grey-7">Запланировано</div>
              <div class="text-weight-bold">{{ formatMoney(summary.total_budget_planned) }}</div>
            </div>
            <div class="col-6">
              <div class="text-caption text-grey-7">Фактически</div>
              <div class="text-weight-bold">{{ formatMoney(summary.total_budget_actual) }}</div>
            </div>
            <div class="col-6">
              <div class="text-caption text-grey-7">Экономия</div>
              <div class="text-weight-bold text-positive">{{ formatMoney(summary.total_savings) }}</div>
            </div>
            <div class="col-6">
              <div class="text-caption text-grey-7">Дефекты</div>
              <div class="text-weight-bold">
                {{ summary.total_defects_resolved }}/{{ summary.total_defects_found }}
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Выезды -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Выезды на объект</div>
        </q-card-section>

        <q-list v-if="visits.length > 0" dense separator>
          <q-item v-for="visit in visits" :key="visit.id">
            <q-item-section avatar>
              <q-icon name="place" color="blue" size="20px" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ formatDate(visit.visit_date) }}</q-item-label>
              <q-item-label caption>
                {{ visit.stage_name?.replace(/^Стадия \d+: /, '') }}
              </q-item-label>
              <q-item-label caption v-if="visit.notes" class="text-grey-7">
                {{ visit.notes }}
              </q-item-label>
            </q-item-section>
            <q-item-section side class="text-caption text-grey-7">
              {{ visit.executor_name }}
            </q-item-section>
          </q-item>
        </q-list>

        <q-card-section v-else class="text-center text-grey-5 q-py-md">
          Нет выездов
        </q-card-section>
        <q-card-actions>
          <q-btn flat color="positive" icon="add" label="Добавить выезд" no-caps @click="showAddVisit = true" />
        </q-card-actions>
      </q-card>

      <!-- Фото с камеры -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Фотофиксация</div>
        </q-card-section>
        <q-card-section>
          <q-btn v-if="can('supervision.files_upload')" icon="photo_camera" label="Сделать фото" color="accent" text-color="dark" no-caps unelevated @click="takePhoto" class="q-mr-sm" />
          <q-btn v-if="can('supervision.files_upload')" icon="upload_file" label="Загрузить" flat no-caps @click="uploadPhoto" />
          <input ref="cameraInput" type="file" accept="image/*" capture="environment" style="display:none" @change="handlePhotoCapture" />
          <input ref="fileInput" type="file" accept="image/*,.pdf" style="display:none" @change="handleFileUpload" />
        </q-card-section>
      </q-card>

      <!-- Диалог добавления выезда -->
      <q-dialog v-model="showAddVisit">
        <q-card style="min-width: 320px">
          <q-card-section><div class="text-subtitle1 text-weight-bold">Новый выезд</div></q-card-section>
          <q-card-section>
            <q-input v-model="visitForm.visit_date" label="Дата выезда" outlined dense type="date" class="q-mb-sm" />
            <q-select v-model="visitForm.stage_code" :options="stageCodesForVisit" label="Стадия" outlined dense emit-value map-options class="q-mb-sm" />
            <q-input v-model="visitForm.notes" label="Заметки" outlined dense type="textarea" autogrow />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Отмена" v-close-popup no-caps />
            <q-btn unelevated color="positive" label="Сохранить" no-caps @click="saveVisit" />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Диалог редактирования стадии -->
      <q-dialog v-model="showEditEntry">
        <q-card style="min-width: 320px">
          <q-card-section><div class="text-subtitle1 text-weight-bold">{{ editEntry?.stage_name }}</div></q-card-section>
          <q-card-section class="q-pt-none" v-if="editEntry">
            <q-input v-model="editEntry.plan_date" label="Плановая дата" outlined dense type="date" class="q-mb-sm" />
            <q-input v-model="editEntry.actual_date" label="Фактическая дата" outlined dense type="date" class="q-mb-sm" />
            <q-input v-model.number="editEntry.budget_planned" label="Бюджет план" outlined dense type="number" prefix="₽" class="q-mb-sm" />
            <q-input v-model.number="editEntry.budget_actual" label="Бюджет факт" outlined dense type="number" prefix="₽" class="q-mb-sm" />
            <q-input v-model="editEntry.supplier" label="Поставщик" outlined dense class="q-mb-sm" />
            <q-select v-model="editEntry.status" :options="['Не начато','В работе','Закуплено','Доставлено','Просрочено']" label="Статус" outlined dense class="q-mb-sm" />
            <q-input v-model="editEntry.notes" label="Заметки" outlined dense type="textarea" autogrow class="q-mb-sm" />
            <q-input v-model="editEntry.executor" label="Исполнитель" outlined dense class="q-mb-sm" />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Отмена" v-close-popup no-caps />
            <q-btn unelevated color="accent" text-color="dark" label="Сохранить" no-caps @click="saveTimelineEntry" />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <!-- Действия -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Действия</div>
        </q-card-section>
        <q-list>
          <q-item v-if="can('supervision.pause_resume') && !card.is_paused" clickable v-ripple @click="handlePause">
            <q-item-section avatar><q-icon name="pause_circle" color="warning" /></q-item-section>
            <q-item-section>Приостановить</q-item-section>
          </q-item>
          <q-item v-else-if="can('supervision.pause_resume') && card.is_paused" clickable v-ripple @click="handleResume">
            <q-item-section avatar><q-icon name="play_circle" color="positive" /></q-item-section>
            <q-item-section>Возобновить</q-item-section>
          </q-item>
          <q-item v-if="can('supervision.complete_stage')" clickable v-ripple @click="handleCompleteStage">
            <q-item-section avatar><q-icon name="check_circle" color="primary" /></q-item-section>
            <q-item-section>Завершить текущую стадию</q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </template>

    <div v-else class="text-center q-pa-xl text-grey-5">
      <q-icon name="search_off" size="48px" class="q-mb-sm" />
      <div>Карточка не найдена</div>
      <q-btn flat color="primary" label="Назад" @click="$router.back()" class="q-mt-md" no-caps />
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { supervisionApi, filesApi } from 'src/services/api'
import { usePermission } from 'src/composables/usePermission'

const { can } = usePermission()

const route = useRoute()
const $q = useQuasar()
const loading = ref(true)
const card = ref(null)
const timeline = ref([])
const summary = ref(null)
const visits = ref([])
const showAddVisit = ref(false)
const showEditEntry = ref(false)
const editEntry = ref(null)
const cameraInput = ref(null)
const fileInput = ref(null)
const visitForm = ref({ visit_date: new Date().toISOString().split('T')[0], stage_code: '', notes: '' })

const stageCodesForVisit = [
  { label: 'Ст. 1: Закупка керамогранита', value: 'STAGE_1_CERAMIC' },
  { label: 'Ст. 2: Закупка сантехники', value: 'STAGE_2_PLUMBING' },
  { label: 'Ст. 3: Закупка оборудования', value: 'STAGE_3_EQUIPMENT' },
  { label: 'Ст. 4: Двери и окна', value: 'STAGE_4_DOORS' },
  { label: 'Ст. 5: Настенные материалы', value: 'STAGE_5_WALLS' },
  { label: 'Ст. 6: Напольные материалы', value: 'STAGE_6_FLOORS' },
  { label: 'Ст. 7: Лепной декор', value: 'STAGE_7_STUCCO' },
  { label: 'Ст. 8: Освещение', value: 'STAGE_8_LIGHTING' },
  { label: 'Ст. 9: Бытовая техника', value: 'STAGE_9_APPLIANCES' },
  { label: 'Ст. 10: Заказная мебель', value: 'STAGE_10_CUSTOM_FURNITURE' },
  { label: 'Ст. 11: Фабричная мебель', value: 'STAGE_11_FACTORY_FURNITURE' },
  { label: 'Ст. 12: Декор', value: 'STAGE_12_DECOR' }
]

function stageIcon(status) {
  const icons = {
    'Не начато': 'radio_button_unchecked',
    'В работе': 'pending',
    'Закуплено': 'shopping_cart',
    'Доставлено': 'check_circle',
    'Просрочено': 'error'
  }
  return icons[status] || 'radio_button_unchecked'
}

function stageColor(status) {
  const colors = {
    'Не начато': 'grey-5',
    'В работе': 'orange',
    'Закуплено': 'blue',
    'Доставлено': 'positive',
    'Просрочено': 'negative'
  }
  return colors[status] || 'grey'
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'short'
  })
}

function formatMoney(amount) {
  if (!amount) return '0 ₽'
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency', currency: 'RUB', maximumFractionDigits: 0
  }).format(amount)
}

async function reloadData() {
  const cardId = route.params.id
  if (!cardId) return
  const [cardRes, timelineRes, summaryRes, visitsRes] = await Promise.allSettled([
    supervisionApi.getCard(cardId),
    supervisionApi.getTimeline(cardId),
    supervisionApi.getTimelineSummary(cardId),
    supervisionApi.getVisits(cardId)
  ])
  if (cardRes.status === 'fulfilled') card.value = cardRes.value.data
  if (timelineRes.status === 'fulfilled') timeline.value = timelineRes.value.data?.entries || timelineRes.value.data || []
  if (summaryRes.status === 'fulfilled') summary.value = summaryRes.value.data
  if (visitsRes.status === 'fulfilled') visits.value = visitsRes.value.data || []
}

async function handlePause() {
  $q.dialog({
    title: 'Приостановить',
    message: 'Укажите причину приостановки',
    prompt: { model: '', type: 'text' },
    cancel: true
  }).onOk(async (reason) => {
    try {
      await supervisionApi.pause(card.value.id, reason || 'Без причины')
      $q.notify({ type: 'positive', message: 'Карточка приостановлена' })
      await reloadData()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

async function handleResume() {
  try {
    await supervisionApi.resume(card.value.id)
    $q.notify({ type: 'positive', message: 'Карточка возобновлена' })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

function exportTimelinePDF() {
  if (!card.value) return
  const url = `https://crm.festivalcolor.ru/api/v1/supervision-timeline/${card.value.id}/export/pdf`
  window.open(url, '_blank')
}

function exportTimelineExcel() {
  if (!card.value) return
  const url = `https://crm.festivalcolor.ru/api/v1/supervision-timeline/${card.value.id}/export/excel`
  window.open(url, '_blank')
}

function editTimelineEntry(entry) {
  editEntry.value = { ...entry }
  showEditEntry.value = true
}

async function saveTimelineEntry() {
  if (!editEntry.value || !card.value) return
  try {
    await supervisionApi.updateTimelineEntry(card.value.id, editEntry.value.stage_code, {
      plan_date: editEntry.value.plan_date,
      actual_date: editEntry.value.actual_date,
      budget_planned: editEntry.value.budget_planned,
      budget_actual: editEntry.value.budget_actual,
      supplier: editEntry.value.supplier,
      status: editEntry.value.status,
      notes: editEntry.value.notes,
      executor: editEntry.value.executor
    })
    $q.notify({ type: 'positive', message: 'Стадия обновлена' })
    showEditEntry.value = false
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function saveVisit() {
  if (!visitForm.value.visit_date || !visitForm.value.stage_code) {
    $q.notify({ type: 'warning', message: 'Заполните дату и стадию' })
    return
  }
  try {
    const stageLabel = stageCodesForVisit.find(s => s.value === visitForm.value.stage_code)?.label || ''
    await supervisionApi.createVisit(card.value.id, {
      stage_code: visitForm.value.stage_code,
      stage_name: stageLabel,
      visit_date: visitForm.value.visit_date,
      executor_name: '',
      notes: visitForm.value.notes
    })
    $q.notify({ type: 'positive', message: 'Выезд добавлен' })
    showAddVisit.value = false
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

function takePhoto() { cameraInput.value?.click() }
function uploadPhoto() { fileInput.value?.click() }

async function handlePhotoCapture(event) {
  await uploadFile(event.target.files?.[0])
  event.target.value = ''
}

async function handleFileUpload(event) {
  await uploadFile(event.target.files?.[0])
  event.target.value = ''
}

async function uploadFile(file) {
  if (!file) return
  try {
    $q.loading.show({ message: 'Загрузка...' })
    const yandexPath = `/CRM/Надзор/${card.value.contract_number || card.value.id}/${file.name}`
    const uploadRes = await filesApi.upload(file, yandexPath)
    const publicLink = uploadRes.data?.public_link || ''
    // Создаём запись в БД (привязка к contract_id)
    if (card.value.contract_id) {
      const { api: ax } = await import('src/boot/axios')
      await ax.post('/api/v1/files/', {
        contract_id: card.value.contract_id,
        stage: 'supervision',
        file_type: file.type?.includes('image') ? 'image' : 'pdf',
        public_link: publicLink,
        yandex_path: yandexPath,
        file_name: file.name,
        file_order: 0, variation: 1
      })
    }
    $q.notify({ type: 'positive', message: 'Файл загружен' })
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки' })
  } finally {
    $q.loading.hide()
  }
}

async function handleCompleteStage() {
  try {
    await supervisionApi.completeStage(card.value.id)
    $q.notify({ type: 'positive', message: 'Стадия завершена' })
    await reloadData()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

onMounted(async () => {
  const cardId = route.params.id
  if (!cardId) return

  try {
    const [cardRes, timelineRes, summaryRes, visitsRes] = await Promise.allSettled([
      supervisionApi.getCard(cardId),
      supervisionApi.getTimeline(cardId),
      supervisionApi.getTimelineSummary(cardId),
      supervisionApi.getVisits(cardId)
    ])

    if (cardRes.status === 'fulfilled') card.value = cardRes.value.data
    if (timelineRes.status === 'fulfilled') {
      timeline.value = timelineRes.value.data?.entries || timelineRes.value.data || []
    }
    if (summaryRes.status === 'fulfilled') summary.value = summaryRes.value.data
    if (visitsRes.status === 'fulfilled') visits.value = visitsRes.value.data || []
  } finally {
    loading.value = false
  }
})
</script>
