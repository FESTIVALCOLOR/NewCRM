<template>
  <q-page>
    <!-- Компактный тулбар: Инд/Шабл + Актив/Архив в одну строку -->
    <div style="border-bottom: 1px solid #E0E0E0; padding: 6px 8px">
      <div class="row items-center no-wrap">
        <!-- Тип проекта — pill toggle -->
        <div class="toggle-pills">
          <button :class="{ active: crmStore.projectType === 'Индивидуальный' }" @click="crmStore.setProjectType('Индивидуальный')">
            Инд. <span v-if="!crmStore.showArchive" class="pill-count">{{ crmStore.countIndividual }}</span>
          </button>
          <button :class="{ active: crmStore.projectType === 'Шаблонный' }" @click="crmStore.setProjectType('Шаблонный')">
            Шабл. <span v-if="!crmStore.showArchive" class="pill-count">{{ crmStore.countTemplate }}</span>
          </button>
        </div>
        <q-space />
        <!-- Актив/Архив — pill toggle -->
        <div class="toggle-pills">
          <button :class="{ active: !crmStore.showArchive }" @click="crmStore.showArchive && crmStore.toggleArchive()">
            Активные <span v-if="!crmStore.showArchive" class="pill-count">{{ crmStore.totalCards }}</span>
          </button>
          <button v-if="can('crm_cards.view_archive')" :class="{ active: crmStore.showArchive }" @click="!crmStore.showArchive && crmStore.toggleArchive()">
            Архив <span v-if="archiveCount > 0" class="pill-count">{{ archiveCount }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Загрузка -->
    <div v-if="crmStore.loading" class="q-pa-md">
      <q-card v-for="n in 3" :key="n" class="is-card q-mb-sm">
        <q-card-section><q-skeleton type="text" width="50%" /><q-skeleton type="text" width="70%" /></q-card-section>
      </q-card>
    </div>

    <template v-if="!crmStore.loading">
      <!-- АРХИВ — список с фильтром -->
      <div v-if="crmStore.showArchive" class="q-pa-sm">
        <q-input
          v-model="archiveSearch"
          placeholder="Поиск по адресу, номеру..."
          dense
          outlined
          clearable
          class="q-mb-sm"
          style="font-size: 12px"
        >
          <template #prepend>
            <q-icon name="search" size="18px" />
          </template>
        </q-input>
        <div v-if="archiveFiltered.length === 0" class="text-center q-py-xl" style="color: #999">
          <q-icon name="archive" size="40px" class="q-mb-sm" />
          <div class="text-caption">
            {{ archiveSearch ? 'Ничего не найдено' : 'Архив пуст' }}
          </div>
        </div>
        <div class="row q-gutter-sm">
          <div v-for="card in archiveFiltered" :key="card.id" class="col-12 col-sm-5 col-md-3 col-lg-2">
            <crm-card-item :card="card" @click="openCard(card.id)" />
          </div>
        </div>
      </div>

      <!-- АКТИВНЫЕ (ландшафт) — все колонки рядом -->
      <template v-if="!crmStore.showArchive && ($q.screen.width > $q.screen.height)">
        <div class="landscape-board">
          <div v-for="col in crmStore.columns" :key="col.name" class="landscape-column">
            <div class="column-frame" style="margin: 0; height: 100%">
              <div class="column-header">
                <span class="column-title">{{ col.name }}</span>
                <span :class="['col-count-badge', { 'has-cards': col.count > 0 }]">{{ col.count }}</span>
              </div>
              <div v-if="col.cards.length > 0" class="column-body">
                <crm-card-item
                  v-for="card in col.cards"
                  :key="card.id"
                  :card="card"
                  @click="openCard(card.id)"
                  @longpress="showMoveDialog(card)"
                  @submit-work="doCardAction(card.id, 'submit')"
                  @accept="doCardAction(card.id, 'accept')"
                  @reject="doCardAction(card.id, 'reject')"
                  @client-send="doCardAction(card.id, 'client-send')"
                  @client-approved="doCardAction(card.id, 'client-approved')"
                  @advance-round="doCardAction(card.id, 'advance-round')"
                  @close-stage="doCardAction(card.id, 'close-stage')"
                  @add-extra-round="doCardAction(card.id, 'add-extra-round')"
                  @sign-act="doCardAction(card.id, 'sign-act')"
                  @add-measurement="openMeasurementDialog(card)"
                  @add-tech-task="openTechTaskDialog(card)"
                />
              </div>
              <div v-else class="column-empty">
                <q-icon name="inbox" size="32px" color="grey-4" />
                <div>Нет карточек</div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- АКТИВНЫЕ (мобильный) — свайпабельные колонки -->
      <template v-if="!crmStore.showArchive && $q.screen.lt.md && !($q.screen.width > $q.screen.height)">
        <!-- Мини-навигация колонок: горизонтальный скролл -->
        <div class="column-nav">
          <div class="column-nav-inner">
            <button
              v-for="(col, idx) in crmStore.columns"
              :key="col.name"
              :class="{ active: currentSlide === idx }"
              @click="currentSlide = idx"
            >
              {{ col.shortName }}
              <span class="count">{{ col.count }}</span>
            </button>
          </div>
        </div>

        <!-- Карусель колонок — свайп влево/вправо -->
        <q-carousel
          v-model="currentSlide"
          swipeable
          animated
          transition-prev="slide-right"
          transition-next="slide-left"
          style="min-height: calc(100vh - 220px); background: transparent"
          control-color="grey-7"
        >
          <q-carousel-slide v-for="(col, idx) in crmStore.columns" :key="col.name" :name="idx" class="q-pa-none">
            <div class="column-frame">
              <div class="column-header">
                <span class="column-title">{{ col.name }}</span>
                <span :class="['col-count-badge', { 'has-cards': col.count > 0 }]">{{ col.count }}</span>
              </div>
              <div v-if="col.cards.length > 0" class="column-body">
                <crm-card-item
                  v-for="card in col.cards"
                  :key="card.id"
                  :card="card"
                  @click="openCard(card.id)"
                  @longpress="showMoveDialog(card)"
                  @submit-work="doCardAction(card.id, 'submit')"
                  @accept="doCardAction(card.id, 'accept')"
                  @reject="doCardAction(card.id, 'reject')"
                  @client-send="doCardAction(card.id, 'client-send')"
                  @client-approved="doCardAction(card.id, 'client-approved')"
                  @advance-round="doCardAction(card.id, 'advance-round')"
                  @close-stage="doCardAction(card.id, 'close-stage')"
                  @add-extra-round="doCardAction(card.id, 'add-extra-round')"
                  @sign-act="doCardAction(card.id, 'sign-act')"
                  @add-measurement="openMeasurementDialog(card)"
                  @add-tech-task="openTechTaskDialog(card)"
                />
              </div>
              <div v-else class="column-empty">
                <q-icon name="inbox" size="32px" color="grey-4" />
                <div>Нет карточек</div>
              </div>
            </div>
          </q-carousel-slide>
        </q-carousel>
      </template>

      <!-- Планшет — тоже свайп (карусель) -->
      <template v-if="$q.screen.gt.sm && !crmStore.showArchive && !($q.screen.width > $q.screen.height)">
        <div class="column-nav">
          <div class="column-nav-inner">
            <button v-for="(col, idx) in crmStore.columns" :key="col.name" :class="{ active: currentSlide === idx }" @click="currentSlide = idx">
              {{ col.shortName }} <span class="count">{{ col.count }}</span>
            </button>
          </div>
        </div>
        <q-carousel
          v-model="currentSlide"
          swipeable
          animated
          transition-prev="slide-right"
          transition-next="slide-left"
          style="min-height: calc(100vh - 220px); background: transparent"
        >
          <q-carousel-slide v-for="(col, idx) in crmStore.columns" :key="col.name" :name="idx" class="q-pa-none">
            <div class="column-frame">
              <div class="column-header">
                <span class="column-title">{{ col.name }}</span>
                <span :class="['col-count-badge', { 'has-cards': col.count > 0 }]">{{ col.count }}</span>
              </div>
              <div v-if="col.cards.length > 0" class="column-body">
                <crm-card-item
                  v-for="card in col.cards"
                  :key="card.id"
                  :card="card"
                  @click="openCard(card.id)"
                  @longpress="showMoveDialog(card)"
                  @submit-work="doCardAction(card.id, 'submit')"
                  @accept="doCardAction(card.id, 'accept')"
                  @reject="doCardAction(card.id, 'reject')"
                  @client-send="doCardAction(card.id, 'client-send')"
                  @client-approved="doCardAction(card.id, 'client-approved')"
                  @advance-round="doCardAction(card.id, 'advance-round')"
                  @close-stage="doCardAction(card.id, 'close-stage')"
                  @add-extra-round="doCardAction(card.id, 'add-extra-round')"
                  @sign-act="doCardAction(card.id, 'sign-act')"
                  @add-measurement="openMeasurementDialog(card)"
                  @add-tech-task="openTechTaskDialog(card)"
                />
              </div>
              <div v-else class="column-empty">
                <q-icon name="inbox" size="32px" color="grey-4" /><div>Нет карточек</div>
              </div>
            </div>
          </q-carousel-slide>
        </q-carousel>
      </template>
    </template>
    <!-- Диалог перемещения карточки (long-press) -->
    <q-dialog v-model="moveDialogVisible">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            Переместить карточку
          </q-toolbar-title>
          <q-btn
            flat
            round
            dense
            icon="close"
            @click="moveDialogVisible = false"
          />
        </q-toolbar>
        <q-card-section v-if="moveCard" class="q-pb-none">
          <div class="text-weight-bold" style="font-size: 12px">
            {{ moveCard.contract_number }} — {{ moveCard.address }}
          </div>
          <div class="text-caption q-mt-xs" style="color: #888">
            Текущая: {{ moveCard.column_name }}
          </div>
        </q-card-section>

        <!-- Шаг 1: выбор стадии -->
        <template v-if="moveStep === 1">
          <q-list separator>
            <q-item
              v-for="col in crmStore.columnOrder"
              :key="col"
              v-ripple
              clickable
              :disable="moveCard?.column_name === col"
              @click="selectMoveColumn(col)"
            >
              <q-item-section>
                <q-item-label :style="{ color: moveCard?.column_name === col ? '#ccc' : '#333', fontSize: '13px' }">
                  {{ col }}
                </q-item-label>
              </q-item-section>
              <q-item-section v-if="moveCard?.column_name === col" side>
                <q-icon name="check" color="positive" />
              </q-item-section>
              <q-item-section v-else-if="stageNeedsExecutor(col)" side>
                <q-icon name="person_add" color="grey-5" size="16px" />
              </q-item-section>
            </q-item>
          </q-list>
        </template>

        <!-- Шаг 2: назначение сотрудника (если стадия требует) -->
        <template v-if="moveStep === 2">
          <q-card-section>
            <div class="text-caption q-mb-sm" style="color: #888">
              Стадия: {{ moveTargetCol }}
            </div>
            <q-select
              v-model="moveExecutorId"
              :options="filteredMoveEmployees"
              option-value="id"
              option-label="label"
              label="Исполнитель *"
              outlined
              dense
              emit-value
              map-options
              use-input
              input-debounce="200"
              class="q-mb-sm"
              @filter="filterMoveEmps"
            />
            <q-input
              v-model="moveDeadline"
              label="Дедлайн"
              outlined
              dense
              type="date"
              class="q-mb-xs"
            />
            <div v-if="moveNormDays > 0" style="font-size: 11px; color: #2F5496; font-weight: 600; margin-bottom: 8px">
              Норма дней: {{ moveNormDays }} раб. дн.<span v-if="moveSubstepName" style="font-weight: 400; color: #666"> · {{ moveSubstepName }}</span>
            </div>
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Назад" no-caps @click="moveStep = 1" />
            <q-btn
              unelevated
              label="Переместить"
              style="background: #ffd93c; color: #333; border-radius: 4px"
              no-caps
              :loading="moveLoading"
              @click="doMoveWithAssign"
            />
          </q-card-actions>
        </template>

        <!-- Шаг 3: Завершение проекта -->
        <template v-if="moveStep === 3">
          <q-card-section>
            <div class="text-caption q-mb-sm" style="color: #888">
              Выберите статус завершения проекта
            </div>
            <q-option-group
              v-model="completionStatus"
              :options="[
                { label: 'Проект СДАН', value: 'СДАН' },
                { label: 'Авторский надзор', value: 'АВТОРСКИЙ НАДЗОР' },
                { label: 'Расторгнут', value: 'РАСТОРГНУТ' }
              ]"
              color="accent"
              class="q-mb-sm"
            />
            <q-input
              v-if="completionStatus === 'РАСТОРГНУТ'"
              v-model="terminationReason"
              label="Причина расторжения *"
              outlined
              dense
              type="textarea"
              autogrow
              class="q-mb-sm"
            />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Назад" no-caps @click="moveStep = 1" />
            <q-btn
              unelevated
              label="Завершить"
              style="background: #ffd93c; color: #333; border-radius: 4px"
              no-caps
              :loading="moveLoading"
              @click="doCompleteProject"
            />
          </q-card-actions>
        </template>
      </q-card>
    </q-dialog>
    <measurement-dialog
      v-model="showMeasDialog"
      :card-id="measCardId"
      :contract-id="measContractId"
      :contract-data="measContractData"
      :card-surveyor-id="measSurveyorId"
      @saved="onMeasurementSaved"
    />
    <tech-task-dialog
      v-model="showTTDialog"
      :card-id="ttCardId"
      :contract-id="ttContractId"
      :contract-data="ttContractData"
      @saved="onTechTaskSaved"
    />
    <page-dashboard :items="dashItems" />

    <!-- Диалог "На исправление" прямо на доске -->
    <q-dialog v-model="boardRejectVisible">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #E74C3C; color: white">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            На исправление
          </q-toolbar-title><q-btn
            flat
            round
            dense
            icon="close"
            color="white"
            @click="boardRejectVisible = false"
          />
        </q-toolbar>
        <q-card-section>
          <q-input
            v-model="boardRejectReason"
            label="Причина *"
            outlined
            dense
            type="textarea"
            autogrow
            class="q-mb-sm"
          />
          <div class="q-mb-sm">
            <q-btn
              outline
              no-caps
              icon="attach_file"
              :label="boardRejectFile ? boardRejectFile.name : 'Прикрепить файл с правками'"
              style="width: 100%; justify-content: flex-start; text-transform: none"
              @click="$refs.boardRejectFileInput.click()"
            />
            <input
              ref="boardRejectFileInput"
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
              style="display: none"
              @change="e => { boardRejectFile = e.target.files[0] || null }"
            >
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Отмена" no-caps />
          <q-btn
            unelevated
            label="Отправить"
            style="background: #E74C3C; color: white; border-radius: 4px"
            no-caps
            :loading="boardRejectLoading"
            @click="submitBoardReject"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useCrmStore } from 'src/stores/crm'
import { useAuthStore } from 'src/stores/auth'
import { crmApi, employeesApi, contractsApi, paymentsApi, filesApi } from 'src/services/api'
import { usePermission } from 'src/composables/usePermission'
import { useOptimistic } from 'src/composables/useOptimistic'
import { calcDeadlineFromTimeline } from 'src/composables/useDeadline'
import CrmCardItem from 'src/components/CrmCardItem.vue'
import PageDashboard from 'src/components/PageDashboard.vue'
import MeasurementDialog from 'src/components/MeasurementDialog.vue'
import TechTaskDialog from 'src/components/TechTaskDialog.vue'

const { can } = usePermission()
const { optimistic } = useOptimistic()

const $q = useQuasar()
const router = useRouter()
const crmStore = useCrmStore()
const currentSlide = ref(parseInt(sessionStorage.getItem('crm_slide') || '0'))
const moveDialogVisible = ref(false)
const moveCard = ref(null)
const moveStep = ref(1)
const moveTargetCol = ref('')
const moveExecutorId = ref(null)
const moveDeadline = ref('')
const moveNormDays = ref(0)
const moveSubstepName = ref('')
const moveLoading = ref(false)
const employeeOpts = ref([])
const completionStatus = ref('СДАН')
const showMeasDialog = ref(false)
const measCardId = ref(null)
const measContractId = ref(null)
const measContractData = ref(null)
const measSurveyorId = ref(null)
const terminationReason = ref('')
const archiveSearch = ref('')
const archiveCount = ref(0)

async function loadArchiveCount() {
  try {
    const { data } = await crmApi.getCards(crmStore.projectType, true)
    const auth = useAuthStore()
    const user = auth.user
    if (!user || !Array.isArray(data)) { archiveCount.value = 0; return }
    const pos = user.position || ''
    const role = user.role || ''
    if (['Руководитель студии', 'Старший менеджер проектов'].includes(pos) || ['admin', 'director'].includes(role)) {
      archiveCount.value = data.length
      return
    }
    const empId = user.id
    const empName = user.full_name || ''
    archiveCount.value = data.filter(card => {
      if (pos === 'Менеджер' && card.manager_id === empId) return true
      if (pos === 'ГАП' && card.gap_id === empId) return true
      if (pos === 'СДП' && card.sdp_id === empId) return true
      if (pos === 'Дизайнер' && card.designer_name === empName) return true
      if (pos === 'Чертёжник' && card.draftsman_name === empName) return true
      if (pos === 'Замерщик' && card.surveyor_id === empId) return true
      return false
    }).length
  } catch { archiveCount.value = 0 }
}

const archiveFiltered = computed(() => {
  const list = crmStore.filteredCards
  if (!archiveSearch.value) return list
  const q = archiveSearch.value.toLowerCase()
  return list.filter(c =>
    (c.address || '').toLowerCase().includes(q) ||
    (c.contract_number || '').toLowerCase().includes(q) ||
    (c.city || '').toLowerCase().includes(q) ||
    (c.agent_type || '').toLowerCase().includes(q),
  )
})

// Стадии, требующие назначения исполнителя
const STAGES_WITH_EXECUTOR = ['Стадия 1:', 'Стадия 2:', 'Стадия 3:']
function stageNeedsExecutor(colName) { return STAGES_WITH_EXECUTOR.some(s => colName.includes(s)) }

const filteredMoveEmployees = ref([])

// Фильтр исполнителей по роли стадии
function getStageRole(colName) {
  const col = colName.toLowerCase()
  if (col.includes('планировочн') || col.includes('чертеж') || col.includes('чертёж')) return 'Чертёжник'
  if (col.includes('концепция') || col.includes('дизайн') || col.includes('визуализац')) return 'Дизайнер'
  return null
}

function filterMoveEmps(val, update) {
  const role = getStageRole(moveTargetCol.value)
  let list = employeeOpts.value
  if (role) {
    list = employeeOpts.value.filter(e => e.label.includes(role) || e.label.includes(role.toLowerCase()))
    if (list.length === 0) list = employeeOpts.value // fallback на всех
  }
  if (val) { const q = val.toLowerCase(); list = list.filter(e => e.label.toLowerCase().includes(q)) }
  update(() => { filteredMoveEmployees.value = list })
}

const dashItems = computed(() => {
  const total = crmStore.filteredCards.length
  const cols = crmStore.columns
  const inWork = cols.filter(c => c.name.includes('Стадия')).reduce((s, c) => s + c.count, 0)
  return [
    { label: 'Всего карточек', value: total },
    { label: 'В работе', value: inWork, color: '#F39C12' },
    { label: 'В архиве', value: archiveCount.value, color: '#3498DB' },
  ]
})

// При смене данных — сохраняем позицию (не сбрасываем если уже была)
watch(() => crmStore.columns, (cols) => {
  if (cols.length > 0 && currentSlide.value >= cols.length) {
    currentSlide.value = 0
  }
})
// Сохраняем позицию слайда в session
watch(currentSlide, (v) => { sessionStorage.setItem('crm_slide', String(v)) })

function openCard(cardId) { router.push(`/crm/${cardId}`) }

async function openMeasurementDialog(card) {
  measCardId.value = card.id
  measContractId.value = card.contract_id
  measSurveyorId.value = card.surveyor_id || null
  try {
    const { data } = await contractsApi.getById(card.contract_id)
    measContractData.value = data
  } catch { measContractData.value = null }
  showMeasDialog.value = true
}
function onMeasurementSaved() { crmStore.loadCards() }

// === TechTask Dialog ===
const showTTDialog = ref(false)
const ttCardId = ref(null)
const ttContractId = ref(null)
const ttContractData = ref(null)

async function openTechTaskDialog(card) {
  ttCardId.value = card.id
  ttContractId.value = card.contract_id
  try {
    const { data } = await contractsApi.getById(card.contract_id)
    ttContractData.value = data
  } catch { ttContractData.value = null }
  showTTDialog.value = true
}
function onTechTaskSaved() { crmStore.loadCards() }

// === Reject диалог на доске ===
const boardRejectVisible = ref(false)
const boardRejectReason = ref('')
const boardRejectFile = ref(null)
const boardRejectLoading = ref(false)
const boardRejectCardId = ref(null)

function openBoardReject(cardId) {
  boardRejectCardId.value = cardId
  boardRejectReason.value = ''
  boardRejectFile.value = null
  boardRejectVisible.value = true
}

async function submitBoardReject() {
  if (!boardRejectReason.value) { $q.notify({ type: 'warning', message: 'Укажите причину' }); return }
  boardRejectLoading.value = true
  try {
    // Загрузка файла если есть
    let filePath = null
    if (boardRejectFile.value) {
      try {
        const card = crmStore.cards.find(c => c.id === boardRejectCardId.value)
        const contractId = card?.contract_id
        let folder = '/CRM/Правки'
        if (contractId) {
          const { data: ct } = await contractsApi.getById(contractId)
          if (ct?.yandex_folder_path) {
            const STAGE_YD = { 'Стадия 1: планировочные решения': '1 стадия - Планировочное решение', 'Стадия 2: концепция дизайна': '2 стадия - Концепция дизайна', 'Стадия 3: рабочие чертежи': '3 стадия - Чертежный проект', 'Стадия 2: рабочие чертежи': '2 стадия - Чертежный проект', 'Стадия 3: 3д визуализация (Дополнительная)': '3D визуализация' }
            const stageName = STAGE_YD[card.column_name] || (card.column_name || 'Стадия').replace(/:/g, ' -')
            folder = ct.yandex_folder_path.replace(/^disk:/, '') + '/' + stageName + '/правки'
          }
        }
        await filesApi.upload(boardRejectFile.value, `${folder}/${boardRejectFile.value.name}`)
        filePath = folder
      } catch (e) { console.warn('Ошибка загрузки файла правок:', e) }
    }
    await crmApi.rejectWork(boardRejectCardId.value, { reason: boardRejectReason.value, revision_file_path: filePath })
    $q.notify({ type: 'positive', message: 'Отправлено на исправление' })
    boardRejectVisible.value = false
    crmStore.loadCards()
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
  finally { boardRejectLoading.value = false }
}

async function doCardAction(cardId, action) {
  try {
    const actions = {
      submit: () => crmApi.submitWork(cardId),
      accept: () => crmApi.acceptWork(cardId),
      reject: () => { openBoardReject(cardId); return null },
      'client-send': () => crmApi.sendToClient(cardId),
      'client-approved': () => crmApi.clientApproved(cardId),
      'advance-round': () => crmApi.advanceRound(cardId),
      'close-stage': () => crmApi.closeStage(cardId),
      'add-extra-round': () => crmApi.addExtraRound(cardId),
      'sign-act': () => crmApi.signAct(cardId),
      'send-act': () => { $q.notify({ type: 'info', message: 'Акт отправлен клиенту' }); return { ok: true } },
    }
    if (actions[action]) {
      const result = await actions[action]()
      if (result === null) return // reject открывает диалог, не показывать toast
      $q.notify({ type: 'positive', message: 'Действие выполнено' })
      crmStore.loadCards()
    }
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function showMoveDialog(card) {
  if (!can('crm_cards.move')) return
  moveCard.value = card
  moveStep.value = 1
  moveExecutorId.value = null
  moveDeadline.value = ''
  filteredMoveEmployees.value = employeeOpts.value // предзаполняем на случай открытия step 2
  moveDialogVisible.value = true
  // Перезагружаем список сотрудников если пуст (например после ошибки onMounted)
  if (employeeOpts.value.length === 0) {
    try {
      const { data } = await employeesApi.getList()
      employeeOpts.value = data.filter(e => e.status === 'активный').map(e => ({ id: e.id, label: `${e.full_name} (${e.position})` }))
      filteredMoveEmployees.value = employeeOpts.value
    } catch {}
  }
}

async function selectMoveColumn(colName) {
  if (!moveCard.value || moveCard.value.column_name === colName) return
  const fromCol = moveCard.value.column_name

  // === Правило: нельзя вернуть в «Новый заказ» ===
  if (colName === 'Новый заказ' && fromCol !== 'Новый заказ') {
    $q.notify({ type: 'warning', message: 'Нельзя вернуть карточку в "Новый заказ". Используйте "В ожидании".' })
    return
  }

  // === Правило: из «В ожидании» — только в previous_column или «Выполненный проект» ===
  if (fromCol === 'В ожидании' && colName !== 'В ожидании' && colName !== 'Выполненный проект') {
    const prev = moveCard.value.previous_column
    if (prev && prev !== 'Новый заказ' && colName !== prev) {
      $q.notify({ type: 'warning', message: `Из "В ожидании" можно вернуть только в "${prev}" или "Выполненный проект".` })
      return
    }
  }

  // === Правило: запрет перемещения назад (кроме тех, у кого complete_approval) ===
  if (fromCol !== 'Новый заказ' && fromCol !== 'В ожидании' && colName !== 'В ожидании' && colName !== 'Выполненный проект') {
    if (!can('crm_cards.complete_approval')) {
      const order = crmStore.columnOrder
      const fromIdx = order.indexOf(fromCol)
      const toIdx = order.indexOf(colName)
      if (fromIdx >= 0 && toIdx >= 0 && toIdx < fromIdx) {
        $q.notify({ type: 'warning', message: 'Нельзя переместить карточку назад. Используйте "В ожидании".' })
        return
      }
    }
  }

  // === Правило: Планировочный подтип — только Стадия 1 ===
  if (moveCard.value.project_subtype && moveCard.value.project_subtype.includes('Планировочный')) {
    if (colName.includes('Стадия 2') || colName.includes('Стадия 3')) {
      $q.notify({ type: 'warning', message: 'Планировочный проект не может перейти в эту стадию' })
      return
    }
  }

  // === Правило: проверка оплаты аванса для индивидуальных (как в десктопе crm_tab.py:659-670) ===
  if (moveCard.value.project_type === 'Индивидуальный' && colName.startsWith('Стадия')) {
    const cid = moveCard.value.contract_id
    if (cid) {
      try {
        const { data: contract } = await contractsApi.getById(cid)
        if (!contract.advance_payment_paid_date) {
          $q.notify({ type: 'warning', message: 'Перемещение невозможно: аванс (1-й платёж) не оплачен. Откройте договор и подтвердите оплату.' })
          return
        }
      } catch { /* если не удалось загрузить — пропускаем проверку */ }
    }
  }

  moveTargetCol.value = colName
  if (stageNeedsExecutor(colName)) {
    moveStep.value = 2
    moveExecutorId.value = null
    moveDeadline.value = ''
    // Предзаполняем список исполнителей по роли стадии немедленно
    const stageRole = getStageRole(colName)
    let empList = employeeOpts.value
    if (stageRole) {
      const filtered = empList.filter(e => e.label.includes(stageRole))
      empList = filtered.length > 0 ? filtered : empList
    }
    filteredMoveEmployees.value = empList

    // Подстановка уже назначенного исполнителя из stage_executors
    // (если назначили заранее через команду проекта)
    let _cardDetail = null
    try {
      const { data } = await crmApi.getCard(moveCard.value.id)
      _cardDetail = data
      const seList = _cardDetail?.stage_executors || []
      const existing = seList.filter(s => s.stage_name === colName).sort((a, b) => b.id - a.id)[0]
      if (existing?.executor_id) {
        moveExecutorId.value = existing.executor_id
        if (existing.deadline) moveDeadline.value = existing.deadline
      }
    } catch {}

    // Автоподстановка дедлайна + norm_days из timeline (только если дедлайн ещё не подставлен)
    moveNormDays.value = 0
    moveSubstepName.value = ''
    const cid = moveCard.value.contract_id
    if (cid) {
      try {
        const { api: ax } = await import('src/boot/axios')
        const { getStageDeadlineInfo } = await import('src/composables/useDeadline')
        const resp = await ax.get(`/api/v1/timeline/${cid}`)
        const entries = Array.isArray(resp.data) ? resp.data : []
        const info = getStageDeadlineInfo(entries, colName)
        // НЕ перезаписываем дедлайн если уже загружен из stage_executors
        if (info.deadline && !moveDeadline.value) moveDeadline.value = info.deadline
        moveNormDays.value = info.normDays || 0
        moveSubstepName.value = info.substepName || ''
      } catch { /* fallback ниже */ }

      // Fallback: таймлайн не инициализирован (Новый заказ) — берём норм-дни из шаблона по площади
      if (moveNormDays.value === 0 && _cardDetail) {
        try {
          const { api: ax } = await import('src/boot/axios')
          const { getStageDeadlineInfo } = await import('src/composables/useDeadline')
          const area = _cardDetail.area || 0
          const projectType = _cardDetail.project_type || 'Индивидуальный'
          const projectSubtype = _cardDetail.project_subtype ||
            (projectType === 'Шаблонный' ? 'Стандарт' : 'Полный (с 3д визуализацией)')
          const agentType = _cardDetail.agent_type || 'Все агенты'
          if (area > 0) {
            const previewResp = await ax.post('/api/norm-days/preview', {
              project_type: projectType,
              project_subtype: projectSubtype,
              agent_type: agentType,
              area,
              floors: 1,
            })
            const previewEntries = previewResp.data?.entries || []
            const previewInfo = getStageDeadlineInfo(previewEntries, colName)
            if (previewInfo.normDays > 0) {
              moveNormDays.value = previewInfo.normDays
              moveSubstepName.value = previewInfo.substepName
              if (!moveDeadline.value) moveDeadline.value = previewInfo.deadline || ''
            }
          }
        } catch {}
      }
    }
    if (!moveDeadline.value) {
      const d = new Date(); d.setDate(d.getDate() + 7)
      moveDeadline.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    }
  } else if (colName === 'Выполненный проект') {
    // Показываем диалог завершения
    completionStatus.value = 'СДАН'
    terminationReason.value = ''
    moveStep.value = 3
  } else {
    doMoveCard(colName)
  }
}

async function doMoveCard(colName) {
  const cardId = moveCard.value.id
  moveDialogVisible.value = false

  // Оптимистичное перемещение — UI обновляется мгновенно
  await optimistic(
    () => {
      const { oldColumn } = crmStore.moveCardOptimistic(cardId, colName)
      return oldColumn
    },
    () => crmApi.moveCard(cardId, colName),
    (oldColumn) => crmStore.rollbackMoveCard(cardId, oldColumn),
    `Перемещено: ${colName}`,
  )
  // Перезагружаем для полной синхронизации (обновление счётчиков и т.д.)
  crmStore.loadCards()
}

async function doMoveWithAssign() {
  if (!moveExecutorId.value) { $q.notify({ type: 'warning', message: 'Выберите исполнителя' }); return }
  moveLoading.value = true
  try {
    // 1. Перемещаем карточку
    await crmApi.moveCard(moveCard.value.id, moveTargetCol.value)

    // 2. Назначаем исполнителя (upsert — сервер обновит если уже есть)
    await crmApi.assignExecutor(moveCard.value.id, {
      stage_name: moveTargetCol.value,
      executor_id: moveExecutorId.value,
      deadline: moveDeadline.value || null,
    })

    // 3. Создаём оплату при перемещении (как десктоп ExecutorSelectionDialog)
    try {
      const roleName = getStageRole(moveTargetCol.value) || 'Чертёжник'
      const stageName = moveTargetCol.value
      const isTemplate = moveCard.value.project_type === 'Шаблонный'
      const isStage1 = stageName.includes('Стадия 1')

      // Проверяем нет ли уже оплаты для этого исполнителя на этой роли+стадии
      const { data: existingPayments } = await crmApi.getPayments(moveCard.value.contract_id)
      const alreadyPaid = (existingPayments || []).some(p =>
        p.employee_id === moveExecutorId.value && p.role === roleName &&
        (p.stage_name === stageName || !p.stage_name) && !p.reassigned,
      )

      if (!alreadyPaid) {
        const calcRes = await paymentsApi.calculate({
          contract_id: moveCard.value.contract_id,
          employee_id: moveExecutorId.value,
          role: roleName,
          stage_name: stageName,
          project_subtype: moveCard.value.project_subtype || undefined,
        })
        const fullAmount = calcRes.data?.amount || calcRes.data?.full_amount || 0

        if (isTemplate) {
          // Шаблонный: Полная оплата (Стадия 1 = 0)
          const amount = isStage1 ? 0 : fullAmount
          await paymentsApi.create({ contract_id: moveCard.value.contract_id, employee_id: moveExecutorId.value, role: roleName, stage_name: stageName, payment_type: 'Полная оплата', crm_card_id: moveCard.value.id, calculated_amount: amount, final_amount: amount, report_month: '' })
        } else {
          // Индивидуальный: Аванс 50% + Доплата 50%
          if (fullAmount > 0) {
            const advance = Math.round(fullAmount / 2)
            const balance = fullAmount - advance
            const month = new Date().toISOString().slice(0, 7)
            await paymentsApi.create({ contract_id: moveCard.value.contract_id, employee_id: moveExecutorId.value, role: roleName, stage_name: stageName, payment_type: 'Аванс', crm_card_id: moveCard.value.id, calculated_amount: advance, final_amount: advance, report_month: month })
            await paymentsApi.create({ contract_id: moveCard.value.contract_id, employee_id: moveExecutorId.value, role: roleName, stage_name: stageName, payment_type: 'Доплата', crm_card_id: moveCard.value.id, calculated_amount: balance, final_amount: balance, report_month: null })
          }
        }
      }
    } catch { /* оплата опциональна */ }
    $q.notify({ type: 'positive', message: 'Перемещено + исполнитель назначен' })
    moveDialogVisible.value = false
    crmStore.loadCards()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  } finally { moveLoading.value = false }
}

async function doCompleteProject() {
  if (completionStatus.value === 'РАСТОРГНУТ' && !terminationReason.value.trim()) {
    $q.notify({ type: 'warning', message: 'Укажите причину расторжения' })
    return
  }
  moveLoading.value = true
  try {
    // 1. Перемещаем карточку в «Выполненный проект»
    await crmApi.moveCard(moveCard.value.id, 'Выполненный проект')

    // 2. Обновляем статус договора
    const cid = moveCard.value.contract_id
    if (cid) {
      const update = { status: completionStatus.value }
      if (completionStatus.value === 'РАСТОРГНУТ') {
        update.termination_reason = terminationReason.value.trim()
      }
      await contractsApi.update(cid, update)
    }

    $q.notify({ type: 'positive', message: `Проект завершён: ${completionStatus.value}` })
    moveDialogVisible.value = false
    crmStore.loadCards()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка завершения' })
  } finally { moveLoading.value = false }
}

watch(() => crmStore.projectType, () => { if (can('crm_cards.view_archive')) loadArchiveCount() })

onMounted(async () => {
  crmStore.loadCards()
  if (can('crm_cards.view_archive')) loadArchiveCount()
  try {
    const { data } = await employeesApi.getList()
    employeeOpts.value = data.filter(e => e.status === 'активный').map(e => ({ id: e.id, label: `${e.full_name} (${e.position})` }))
  } catch {}
})
</script>

<style scoped>
/* Toggle pill buttons */
.toggle-pills {
  display: inline-flex;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  overflow: hidden;
}
.toggle-pills button {
  border: none;
  background: #F0F0F0;
  color: #666;
  font-size: 11px;
  padding: 5px 12px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}
.toggle-pills button.active {
  background: white;
  color: #333;
  font-weight: bold;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.toggle-pills button + button {
  border-left: 1px solid #d9d9d9;
}
.pill-count {
  display: inline-block;
  background: rgba(0,0,0,0.12);
  border-radius: 8px;
  font-size: 10px;
  font-weight: bold;
  padding: 0 5px;
  margin-left: 3px;
  min-width: 16px;
  text-align: center;
}
.toggle-pills button.active .pill-count {
  background: #ffd93c;
  color: #333;
}

/* Column navigation mini-bar */
.column-nav {
  overflow-x: auto;
  border-bottom: 1px solid #E0E0E0;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.column-nav::-webkit-scrollbar { display: none }
.column-nav-inner {
  display: inline-flex;
  min-width: 100%;
  justify-content: center;
  padding: 6px 8px;
  gap: 4px;
  box-sizing: border-box;
}
.column-nav button {
  border: 1px solid #d9d9d9;
  border-radius: 16px;
  background: #F5F5F5;
  color: #888;
  font-size: 10px;
  padding: 3px 10px;
  white-space: nowrap;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s;
  flex-shrink: 0;
}
.column-nav button.active {
  background: #333;
  color: white;
  border-color: #333;
  font-weight: bold;
}
.column-nav button .count {
  display: inline-block;
  background: rgba(255,255,255,0.2);
  border-radius: 8px;
  padding: 0 4px;
  margin-left: 3px;
  font-size: 9px;
}
.column-nav button.active .count {
  background: rgba(255,255,255,0.3);
}

/* Column frame inside carousel */
.column-frame {
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  margin: 8px;
  background: #FAFAFA;
  min-height: calc(100vh - 260px);
  display: flex;
  flex-direction: column;
}
.column-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid #E0E0E0;
  background: white;
  border-radius: 8px 8px 0 0;
  min-height: 52px;
  box-sizing: border-box;
}
.column-title {
  font-size: 13px;
  font-weight: bold;
  color: #333;
  flex: 1;
  white-space: normal;
  line-height: 1.35;
}
.column-body {
  padding: 8px;
  flex: 1;
  overflow-y: auto;
}
.column-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #bbb;
  font-size: 12px;
  padding: 40px 0;
}

/* Ландшафтная доска — position:fixed обходит overflow:hidden q-layout */
.landscape-board {
  position: fixed;
  left: var(--drawer-offset, 0px);
  right: 0;
  transition: left 0.3s ease;
  top: calc(var(--q-header-height, 48px) + 41px);
  bottom: var(--q-footer-height, 56px);
  display: flex;
  flex-direction: row;
  overflow-x: auto;
  overflow-y: hidden;
  gap: 8px;
  padding: 8px;
  background: #fff;
  z-index: 1;
  -webkit-overflow-scrolling: touch;
}
.landscape-column {
  flex: 1 1 280px;
  min-width: 280px;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.col-count-badge {
  border-radius: 50%;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: bold;
  flex-shrink: 0;
  background: #E0E0E0;
  color: #888;
}
.col-count-badge.has-cards {
  background: #ffd93c;
  color: #333;
}
.landscape-column .column-frame {
  flex: 1;
  margin: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
}
.landscape-column .column-body {
  overflow-y: auto;
  flex: 1;
}
</style>
