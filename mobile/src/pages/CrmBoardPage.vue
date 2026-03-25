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

      <!-- АРХИВ — список без столбцов -->
      <div v-if="crmStore.showArchive" class="q-pa-sm">
        <div v-if="crmStore.cards.length === 0" class="text-center q-py-xl" style="color: #999">
          <q-icon name="archive" size="40px" class="q-mb-sm" />
          <div class="text-caption">Архив пуст</div>
        </div>
        <crm-card-item v-for="card in crmStore.cards" :key="card.id" :card="card" @click="openCard(card.id)" @longpress="showMoveDialog(card)" />
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
            <q-select v-model="moveExecutorId" :options="employeeOpts" option-value="id" option-label="label" label="Исполнитель *" outlined dense emit-value map-options class="q-mb-sm" />
            <q-input v-model="moveDeadline" label="Дедлайн" outlined dense type="date" class="q-mb-sm" />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn flat label="Назад" no-caps @click="moveStep = 1" />
            <q-btn unelevated label="Переместить" style="background: #ffd93c; color: #333; border-radius: 4px" no-caps @click="doMoveWithAssign" :loading="moveLoading" />
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
import { crmApi, employeesApi } from 'src/services/api'
import CrmCardItem from 'src/components/CrmCardItem.vue'
import PageDashboard from 'src/components/PageDashboard.vue'

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

// Стадии, требующие назначения исполнителя
const STAGES_WITH_EXECUTOR = ['Стадия 1:', 'Стадия 2:', 'Стадия 3:']
function stageNeedsExecutor(colName) { return STAGES_WITH_EXECUTOR.some(s => colName.includes(s)) }

const dashItems = computed(() => {
  const total = crmStore.cards.length
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
  moveCard.value = card
  moveStep.value = 1
  moveExecutorId.value = null
  moveDeadline.value = ''
  moveDialogVisible.value = true
}

function selectMoveColumn(colName) {
  if (!moveCard.value || moveCard.value.column_name === colName) return
  moveTargetCol.value = colName
  if (stageNeedsExecutor(colName)) {
    moveStep.value = 2
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
