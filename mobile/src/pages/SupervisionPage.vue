<template>
  <q-page>
    <!-- Тулбар — pill toggle как в CRM -->
    <div style="border-bottom: 1px solid #E0E0E0; padding: 6px 8px">
      <div class="row items-center no-wrap">
        <div class="toggle-pills">
          <button :class="{ active: !showArchive }" @click="showArchive = false; loadCards()">Активные</button>
          <button :class="{ active: showArchive }" @click="showArchive = true; loadCards()">Архив</button>
        </div>
        <q-space />
        <div class="text-caption" style="color: #888">{{ cards.length }} объектов</div>
      </div>
    </div>

    <div v-if="loading" class="q-pa-md">
      <q-card class="is-card q-mb-sm" v-for="n in 4" :key="n"><q-card-section><q-skeleton type="text" width="50%" /><q-skeleton type="text" width="70%" /></q-card-section></q-card>
    </div>

    <template v-else>
      <!-- Архив -->
      <div v-if="showArchive" class="q-pa-sm">
        <q-card v-for="card in cards" :key="card.id" class="is-card q-mb-sm cursor-pointer" @click="openCard(card)">
          <q-card-section class="q-pa-md">
            <div class="row items-center justify-between q-mb-xs">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">{{ card.contract_number || `#${card.id}` }}</div>
              <q-badge :color="sColor(card)" :label="card.column_name || 'Архив'" dense />
            </div>
            <div class="text-body2" style="color: #333">{{ card.address || 'Без адреса' }}</div>
            <div class="row q-gutter-sm text-caption" style="color: #888">
              <span v-if="card.area">{{ card.area }} м²</span><span v-if="card.city">{{ card.city }}</span>
            </div>
          </q-card-section>
        </q-card>
        <div v-if="cards.length === 0" class="text-center q-py-xl" style="color: #999">Архив пуст</div>
      </div>

      <!-- Активные — QCarousel свайп как CRM -->
      <template v-else>
        <div class="column-nav">
          <button v-for="(col, idx) in columns" :key="col.name" :class="{ active: currentSlide === idx }" @click="currentSlide = idx">
            {{ col.shortName }} <span class="count">{{ col.count }}</span>
          </button>
        </div>
        <q-carousel v-model="currentSlide" swipeable animated transition-prev="slide-right" transition-next="slide-left" style="min-height: calc(100vh - 220px); background: transparent">
          <q-carousel-slide v-for="(col, idx) in columns" :key="col.name" :name="idx" class="q-pa-none">
            <div class="column-frame">
              <div class="column-header">
                <span class="column-title">{{ col.name }}</span>
                <span style="color: #888; font-size: 11px">Карточек: {{ col.count }}</span>
              </div>
              <div class="column-body" v-if="col.cards.length > 0">
                <q-card v-for="card in col.cards" :key="card.id" class="crm-card q-mb-sm" :style="card.is_paused ? { background: '#FFF8E1', borderColor: '#F39C12' } : {}">
                  <q-card-section class="q-pa-sm">
                    <!-- 1. Номер договора (слева) + Стадия (справа) -->
                    <div class="row items-center justify-between q-mb-xs">
                      <div style="color: #888; font-size: 10px">{{ card.contract_number || `#${card.id}` }}</div>
                      <q-badge v-if="!card.is_paused" color="blue-grey-3" text-color="blue-grey-9" :label="card.column_name" dense style="font-size: 9px" />
                      <q-badge v-else color="warning" label="Приостановлено" dense style="font-size: 9px" />
                    </div>
                    <!-- Причина паузы -->
                    <div v-if="card.is_paused && card.pause_reason" class="q-mb-xs">
                      <q-badge color="orange-2" text-color="orange-9" :label="card.pause_reason" dense style="font-size: 9px; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap" />
                    </div>
                    <!-- 2. Адрес -->
                    <div class="text-weight-bold q-mb-xs" style="font-size: 13px; color: #222">{{ card.address || 'Без адреса' }}</div>
                    <!-- 3. Площадь/город (слева) + Тип агента badge (справа) -->
                    <div class="row items-center justify-between q-mb-xs">
                      <div style="font-size: 11px; color: #888">
                        <span v-if="card.area">{{ card.area }} м²</span>
                        <span v-if="card.area && card.city"> | </span>
                        <span v-if="card.city">{{ card.city }}</span>
                        <span v-if="card.dan_name"> | ДАН: {{ card.dan_name }}</span>
                      </div>
                      <span v-if="card.agent_type" :style="{ background: agentColorFor(card.agent_type), color: 'white', fontSize: '10px', fontWeight: 'bold', padding: '3px 8px', borderRadius: '4px' }">{{ card.agent_type }}</span>
                    </div>
                    <!-- 4. Дедлайн -->
                    <div v-if="card.deadline" class="q-mb-xs row items-center" style="background: #FFF3CD; border-radius: 4px; padding: 3px 8px; width: 100%">
                      <q-icon name="schedule" size="12px" style="color: #856404" class="q-mr-xs" />
                      <span style="font-size: 10px; color: #856404; font-weight: bold">{{ new Date(card.deadline).toLocaleDateString('ru-RU') }}</span>
                    </div>
                    <!-- 5. Пауза/Возобновить -->
                    <div class="row q-gutter-xs q-mb-xs">
                      <q-btn v-if="!card.is_paused" flat dense no-caps icon="pause" label="Пауза" style="color: #F39C12; font-size: 10px; height: 24px; flex: 1; border: 1px solid #F39C12; border-radius: 4px" @click.stop="quickPause(card)" />
                      <q-btn v-else flat dense no-caps icon="play_arrow" label="Возобновить" style="color: #27AE60; font-size: 10px; height: 24px; flex: 1; border: 1px solid #27AE60; border-radius: 4px" @click.stop="quickResume(card)" />
                    </div>
                    <!-- 6. Кнопки -->
                    <div style="border-top: 1px solid #E0E0E0; padding-top: 6px">
                      <q-btn flat dense no-caps icon="open_in_new" label="Данные карточки" style="color: #333; font-size: 11px; height: 28px; width: 100%; background: #F5F5F5; border-radius: 4px" class="q-mb-xs" @click="openCard(card)" />
                      <q-btn flat dense no-caps icon="swap_horiz" label="Переместить" style="color: #888; font-size: 10px; height: 24px; width: 100%" @click.stop="showMoveDialog(card)" />
                    </div>
                  </q-card-section>
                </q-card>
              </div>
              <div v-else class="column-empty"><q-icon name="inbox" size="32px" color="grey-4" /><div>Нет карточек</div></div>
            </div>
          </q-carousel-slide>
        </q-carousel>
      </template>
    </template>
    <!-- Диалог перемещения надзорной карточки -->
    <q-dialog v-model="moveDialogVisible">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">Переместить</q-toolbar-title>
          <q-btn flat round dense icon="close" @click="moveDialogVisible = false" />
        </q-toolbar>
        <q-card-section v-if="moveCard" class="q-pb-none">
          <div class="text-weight-bold" style="font-size: 12px">{{ moveCard.contract_number }} — {{ moveCard.address }}</div>
          <div class="text-caption q-mt-xs" style="color: #888">Текущая: {{ moveCard.column_name }}</div>
        </q-card-section>
        <q-list separator>
          <q-item v-for="col in SUPERVISION_COLUMNS" :key="col" clickable v-ripple @click="doMove(col)" :disable="moveCard?.column_name === col">
            <q-item-section>
              <q-item-label :style="{ color: moveCard?.column_name === col ? '#ccc' : '#333', fontSize: '13px' }">{{ col }}</q-item-label>
            </q-item-section>
            <q-item-section side v-if="moveCard?.column_name === col"><q-icon name="check" color="positive" /></q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </q-dialog>

    <page-dashboard :items="dashItems" />
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { supervisionApi } from 'src/services/api'
import { usePermission } from 'src/composables/usePermission'
import { useReferencesStore } from 'src/stores/references'
import PageDashboard from 'src/components/PageDashboard.vue'

const router = useRouter()
const $q = useQuasar()
const { can } = usePermission()
const refsStore = useReferencesStore()

function agentColorFor(agentType) {
  const agent = refsStore.agentByName?.(agentType)
  return agent?.color || '#95A5A6'
}
const cards = ref([])
const loading = ref(false)
const showArchive = ref(false)
const currentSlide = ref(parseInt(sessionStorage.getItem('sv_slide') || '0'))
const moveDialogVisible = ref(false)
const moveCard = ref(null)

const SUPERVISION_COLUMNS = [
  'Новый заказ', 'В ожидании',
  'Стадия 1: Закупка керамогранита', 'Стадия 2: Закупка сантехники',
  'Стадия 3: Закупка оборудования', 'Стадия 4: Закупка дверей и окон',
  'Стадия 5: Закупка настенных материалов', 'Стадия 6: Закупка напольных материалов',
  'Стадия 7: Лепной декор', 'Стадия 8: Освещение',
  'Стадия 9: Бытовая техника', 'Стадия 10: Закупка заказной мебели',
  'Стадия 11: Закупка фабричной мебели', 'Стадия 12: Закупка декора',
  'Выполненный проект'
]

const columns = computed(() => {
  const grouped = {}
  for (const col of SUPERVISION_COLUMNS) grouped[col] = []
  for (const card of cards.value) { const col = card.column_name || 'Новый заказ'; if (!grouped[col]) grouped[col] = []; grouped[col].push(card) }
  return SUPERVISION_COLUMNS.filter(c => grouped[c]).map(c => ({ name: c, shortName: c.replace(/^Стадия \d+: (Закупка )?/, '').substring(0, 15), cards: grouped[c], count: grouped[c].length }))
})

watch(columns, (cols) => { if (cols.length > 0 && currentSlide.value >= cols.length) currentSlide.value = 0 })
watch(currentSlide, (v) => { sessionStorage.setItem('sv_slide', String(v)) })

function sColor(card) { const s = card.column_name || ''; if (s.includes('Стадия')) return 'orange'; if (s.includes('Выполненный')) return 'positive'; return 'blue' }
function dlColor(d) { const days = Math.ceil((new Date(d) - new Date()) / 86400000); if (days < 0) return '#8B0000'; if (days <= 2) return '#F39C12'; return '#888' }
function openCard(card) { router.push(`/supervision/${card.id}`) }

async function quickPause(card) {
  $q.dialog({ title: 'Приостановить', message: 'Причина приостановки', prompt: { model: '', type: 'text' }, cancel: true }).onOk(async (reason) => {
    try { await supervisionApi.pause(card.id, reason || 'Без причины'); $q.notify({ type: 'positive', message: 'Приостановлено' }); loadCards() } catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка' }) }
  })
}
async function quickResume(card) {
  try { await supervisionApi.resume(card.id); $q.notify({ type: 'positive', message: 'Возобновлено' }); loadCards() } catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка' }) }
}

const dashItems = computed(() => [
  { label: 'Всего', value: cards.value.length },
  { label: 'В работе', value: cards.value.filter(c => (c.column_name || '').includes('Стадия')).length, color: '#F39C12' },
  { label: 'Приостановлено', value: cards.value.filter(c => c.is_paused).length, color: '#E74C3C' }
])

function showMoveDialog(card) {
  if (!can('supervision.move')) return
  moveCard.value = card
  moveDialogVisible.value = true
}

async function doMove(colName) {
  if (!moveCard.value || moveCard.value.column_name === colName) return
  try {
    await supervisionApi.moveCard(moveCard.value.id, colName)
    $q.notify({ type: 'positive', message: `Перемещено: ${colName}` })
    moveDialogVisible.value = false
    loadCards()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка перемещения' })
  }
}

async function loadCards() {
  loading.value = true
  try { const { data } = await supervisionApi.getCards({ status: showArchive.value ? 'archived' : 'active' }); cards.value = data }
  catch { cards.value = [] } finally { loading.value = false }
}

onMounted(() => loadCards())
</script>

<style scoped>
.toggle-pills { display: inline-flex; border: 1px solid #d9d9d9; border-radius: 6px; overflow: hidden }
.toggle-pills button { border: none; background: #F0F0F0; color: #666; font-size: 11px; padding: 5px 12px; cursor: pointer; transition: all 0.2s; font-family: inherit }
.toggle-pills button.active { background: white; color: #333; font-weight: bold; box-shadow: 0 1px 3px rgba(0,0,0,0.08) }
.toggle-pills button + button { border-left: 1px solid #d9d9d9 }
.column-nav { display: flex; overflow-x: auto; padding: 6px 8px; gap: 4px; border-bottom: 1px solid #E0E0E0; -webkit-overflow-scrolling: touch; scrollbar-width: none }
.column-nav::-webkit-scrollbar { display: none }
.column-nav button { border: 1px solid #d9d9d9; border-radius: 16px; background: #F5F5F5; color: #888; font-size: 10px; padding: 3px 10px; white-space: nowrap; cursor: pointer; font-family: inherit; transition: all 0.2s; flex-shrink: 0 }
.column-nav button.active { background: #333; color: white; border-color: #333; font-weight: bold }
.column-nav button .count { display: inline-block; background: rgba(255,255,255,0.2); border-radius: 8px; padding: 0 4px; margin-left: 3px; font-size: 9px }
.column-nav button.active .count { background: rgba(255,255,255,0.3) }
.column-frame { border: 1px solid #d9d9d9; border-radius: 8px; margin: 8px; background: #FAFAFA; min-height: calc(100vh - 260px); display: flex; flex-direction: column }
.column-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-bottom: 1px solid #E0E0E0; background: white; border-radius: 8px 8px 0 0 }
.column-title { font-size: 13px; font-weight: bold; color: #333 }
.column-body { padding: 8px; flex: 1; overflow-y: auto }
.column-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #bbb; font-size: 12px; padding: 40px 0 }
</style>
