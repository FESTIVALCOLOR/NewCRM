<template>
  <q-page>
    <!-- Компактный тулбар: Инд/Шабл + Актив/Архив в одну строку -->
    <div style="border-bottom: 1px solid #E0E0E0; padding: 6px 8px">
      <div class="row items-center no-wrap">
        <!-- Тип проекта — pill toggle -->
        <div class="toggle-pills">
          <button :class="{ active: crmStore.projectType === 'Индивидуальный' }" @click="crmStore.setProjectType('Индивидуальный')">Инд.</button>
          <button :class="{ active: crmStore.projectType === 'Шаблонный' }" @click="crmStore.setProjectType('Шаблонный')">Шабл.</button>
        </div>
        <q-space />
        <!-- Актив/Архив — pill toggle -->
        <div class="toggle-pills">
          <button :class="{ active: !crmStore.showArchive }" @click="crmStore.showArchive && crmStore.toggleArchive()">Активные</button>
          <button :class="{ active: crmStore.showArchive }" @click="!crmStore.showArchive && crmStore.toggleArchive()">Архив</button>
        </div>
      </div>
    </div>

    <!-- Загрузка -->
    <div v-if="crmStore.loading" class="q-pa-md">
      <q-card class="is-card q-mb-sm" v-for="n in 3" :key="n">
        <q-card-section><q-skeleton type="text" width="50%" /><q-skeleton type="text" width="70%" /></q-card-section>
      </q-card>
    </div>

    <template v-if="!crmStore.loading">

      <!-- АРХИВ — список с фильтром -->
      <div v-if="crmStore.showArchive" class="q-pa-sm">
        <q-input v-model="archiveSearch" placeholder="Поиск по адресу, номеру..." dense outlined clearable class="q-mb-sm" style="font-size: 12px">
          <template v-slot:prepend><q-icon name="search" size="18px" /></template>
        </q-input>
        <div v-if="archiveFiltered.length === 0" class="text-center q-py-xl" style="color: #999">
          <q-icon name="archive" size="40px" class="q-mb-sm" />
          <div class="text-caption">{{ archiveSearch ? 'Ничего не найдено' : 'Архив пуст' }}</div>
        </div>
        <crm-card-item v-for="card in archiveFiltered" :key="card.id" :card="card" @click="openCard(card.id)" @longpress="showMoveDialog(card)" />
      </div>

      <!-- АКТИВНЫЕ (мобильный) — свайпабельные колонки -->
      <template v-if="!crmStore.showArchive && $q.screen.lt.md">
        <!-- Мини-навигация колонок: горизонтальный скролл -->
        <div class="column-nav">
          <button
            v-for="(col, idx) in crmStore.columns" :key="col.name"
            :class="{ active: currentSlide === idx }"
            @click="currentSlide = idx"
          >
            {{ col.shortName }}
            <span class="count">{{ col.count }}</span>
          </button>
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
                <span style="color: #888; font-size: 11px">Карточек в столбце: {{ col.count }}</span>
              </div>
              <div class="column-body" v-if="col.cards.length > 0">
                <crm-card-item v-for="card in col.cards" :key="card.id" :card="card" @click="openCard(card.id)" @longpress="showMoveDialog(card)" />
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
      <template v-if="$q.screen.gt.sm && !crmStore.showArchive">
        <div class="column-nav">
          <button v-for="(col, idx) in crmStore.columns" :key="col.name" :class="{ active: currentSlide === idx }" @click="currentSlide = idx">
            {{ col.shortName }} <span class="count">{{ col.count }}</span>
          </button>
        </div>
        <q-carousel v-model="currentSlide" swipeable animated transition-prev="slide-right" transition-next="slide-left" style="min-height: calc(100vh - 220px); background: transparent">
          <q-carousel-slide v-for="(col, idx) in crmStore.columns" :key="col.name" :name="idx" class="q-pa-none">
            <div class="column-frame">
              <div class="column-header">
                <span class="column-title">{{ col.name }}</span>
                <span style="color: #888; font-size: 11px">Карточек в столбце: {{ col.count }}</span>
              </div>
              <div class="column-body" v-if="col.cards.length > 0">
                <crm-card-item v-for="card in col.cards" :key="card.id" :card="card" @click="openCard(card.id)" @longpress="showMoveDialog(card)" />
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
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">Переместить карточку</q-toolbar-title>
          <q-btn flat round dense icon="close" @click="moveDialogVisible = false" />
        </q-toolbar>
        <q-card-section v-if="moveCard" class="q-pb-none">
          <div class="text-weight-bold" style="font-size: 12px">{{ moveCard.contract_number }} — {{ moveCard.address }}</div>
          <div class="text-caption q-mt-xs" style="color: #888">Текущая: {{ moveCard.column_name }}</div>
        </q-card-section>

        <!-- Шаг 1: выбор стадии -->
        <template v-if="moveStep === 1">
          <q-list separator>
            <q-item v-for="col in crmStore.columnOrder" :key="col" clickable v-ripple @click="selectMoveColumn(col)" :disable="moveCard?.column_name === col">
              <q-item-section>
                <q-item-label :style="{ color: moveCard?.column_name === col ? '#ccc' : '#333', fontSize: '13px' }">{{ col }}</q-item-label>
              </q-item-section>
              <q-item-section side v-if="moveCard?.column_name === col"><q-icon name="check" color="positive" /></q-item-section>
              <q-item-section side v-else-if="stageNeedsExecutor(col)"><q-icon name="person_add" color="grey-5" size="16px" /></q-item-section>
            </q-item>
          </q-list>
        </template>

        <!-- Шаг 2: назначение сотрудника (если стадия требует) -->
        <template v-if="moveStep === 2">
          <q-card-section>
            <div class="text-caption q-mb-sm" style="color: #888">Стадия: {{ moveTargetCol }}</div>
            <q-select v-model="moveExecutorId" :options="filteredMoveEmployees" option-value="id" option-label="label" label="Исполнитель *" outlined dense emit-value map-options use-input input-debounce="200" @filter="filterMoveEmps" class="q-mb-sm" />
            <q-input v-model="moveDeadline" label="Дедлайн" outlined dense type="date" class="q-mb-sm" />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Назад" no-caps @click="moveStep = 1" />
            <q-btn unelevated label="Переместить" style="background: #ffd93c; color: #333; border-radius: 4px" no-caps @click="doMoveWithAssign" :loading="moveLoading" />
          </q-card-actions>
        </template>

        <!-- Шаг 3: Завершение проекта -->
        <template v-if="moveStep === 3">
          <q-card-section>
            <div class="text-caption q-mb-sm" style="color: #888">Выберите статус завершения проекта</div>
            <q-option-group v-model="completionStatus" :options="[
              { label: 'Проект СДАН', value: 'СДАН' },
              { label: 'Авторский надзор', value: 'АВТОРСКИЙ НАДЗОР' },
              { label: 'Расторгнут', value: 'РАСТОРГНУТ' }
            ]" color="accent" class="q-mb-sm" />
            <q-input v-if="completionStatus === 'РАСТОРГНУТ'" v-model="terminationReason" label="Причина расторжения *" outlined dense type="textarea" autogrow class="q-mb-sm" />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Назад" no-caps @click="moveStep = 1" />
            <q-btn unelevated label="Завершить" style="background: #ffd93c; color: #333; border-radius: 4px" no-caps @click="doCompleteProject" :loading="moveLoading" />
          </q-card-actions>
        </template>
      </q-card>
    </q-dialog>
    <page-dashboard :items="dashItems" />
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useCrmStore } from 'src/stores/crm'
import { crmApi, employeesApi, contractsApi } from 'src/services/api'
import { usePermission } from 'src/composables/usePermission'
import { calcDeadlineFromTimeline } from 'src/composables/useDeadline'
import CrmCardItem from 'src/components/CrmCardItem.vue'
import PageDashboard from 'src/components/PageDashboard.vue'

const { can } = usePermission()

const $q = useQuasar()
const router = useRouter()
const crmStore = useCrmStore()
const currentSlide = ref(0)
const moveDialogVisible = ref(false)
const moveCard = ref(null)
const moveStep = ref(1)
const moveTargetCol = ref('')
const moveExecutorId = ref(null)
const moveDeadline = ref('')
const moveLoading = ref(false)
const employeeOpts = ref([])
const completionStatus = ref('СДАН')
const terminationReason = ref('')
const archiveSearch = ref('')

const archiveFiltered = computed(() => {
  const list = crmStore.filteredCards
  if (!archiveSearch.value) return list
  const q = archiveSearch.value.toLowerCase()
  return list.filter(c =>
    (c.address || '').toLowerCase().includes(q) ||
    (c.contract_number || '').toLowerCase().includes(q) ||
    (c.city || '').toLowerCase().includes(q) ||
    (c.agent_type || '').toLowerCase().includes(q)
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
    { label: 'Столбцов', value: cols.length, color: '#3498DB' }
  ]
})

// При смене данных сбрасываем слайд на первый непустой столбец
watch(() => crmStore.columns, (cols) => {
  if (cols.length > 0) {
    const firstNonEmpty = cols.findIndex(c => c.count > 0)
    currentSlide.value = firstNonEmpty >= 0 ? firstNonEmpty : 0
  }
})

function openCard(cardId) { router.push(`/crm/${cardId}`) }

function showMoveDialog(card) {
  if (!can('crm_cards.move')) return
  moveCard.value = card
  moveStep.value = 1
  moveExecutorId.value = null
  moveDeadline.value = ''
  moveDialogVisible.value = true
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
    moveDeadline.value = ''
    // Автоподстановка дедлайна из timeline
    const cid = moveCard.value.contract_id
    if (cid) {
      try {
        const { api: ax } = await import('src/boot/axios')
        const resp = await ax.get(`/api/v1/timeline/${cid}`)
        const entries = Array.isArray(resp.data) ? resp.data : []
        const auto = calcDeadlineFromTimeline(entries, colName)
        if (auto) moveDeadline.value = auto
      } catch { /* fallback ниже */ }
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
  moveLoading.value = true
  try {
    await crmApi.moveCard(moveCard.value.id, colName)
    $q.notify({ type: 'positive', message: `Перемещено: ${colName}` })
    moveDialogVisible.value = false
    crmStore.loadCards()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка перемещения' })
  } finally { moveLoading.value = false }
}

async function doMoveWithAssign() {
  if (!moveExecutorId.value) { $q.notify({ type: 'warning', message: 'Выберите исполнителя' }); return }
  moveLoading.value = true
  try {
    // Сначала перемещаем
    await crmApi.moveCard(moveCard.value.id, moveTargetCol.value)
    // Потом назначаем исполнителя на стадию
    await crmApi.assignExecutor(moveCard.value.id, {
      stage_name: moveTargetCol.value,
      executor_id: moveExecutorId.value,
      deadline: moveDeadline.value || null
    })
    $q.notify({ type: 'positive', message: `Перемещено + исполнитель назначен` })
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

onMounted(async () => {
  crmStore.loadCards()
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

/* Column navigation mini-bar */
.column-nav {
  display: flex;
  overflow-x: auto;
  padding: 6px 8px;
  gap: 4px;
  border-bottom: 1px solid #E0E0E0;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.column-nav::-webkit-scrollbar { display: none }
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
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #E0E0E0;
  background: white;
  border-radius: 8px 8px 0 0;
}
.column-title {
  font-size: 13px;
  font-weight: bold;
  color: #333;
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
</style>
