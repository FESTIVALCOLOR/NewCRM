<template>
  <q-page>
    <!-- Тулбар — pill toggle как в CRM -->
    <div style="border-bottom: 1px solid var(--fc-border-light); padding: 6px 8px">
      <div class="row items-center no-wrap">
        <div class="toggle-pills">
          <button :class="{ active: !showArchive }" @click="showArchive = false; loadCards()">
            Активные <span v-if="activeCount > 0" class="pill-count">{{ showArchive ? activeCount : cards.length }}</span>
          </button>
          <button v-if="can('supervision.view_archive')" :class="{ active: showArchive }" @click="showArchive = true; loadCards()">
            Архив <span v-if="archiveCount > 0" class="pill-count">{{ showArchive ? cards.length : archiveCount }}</span>
          </button>
        </div>
        <q-space />
        <div class="text-caption" style="color: var(--fc-text-light)">
          {{ cards.length }} объектов
        </div>
      </div>
    </div>

    <div v-if="loading" class="q-pa-md">
      <q-card v-for="n in 4" :key="n" class="is-card q-mb-sm">
        <q-card-section><q-skeleton type="text" width="50%" /><q-skeleton type="text" width="70%" /></q-card-section>
      </q-card>
    </div>

    <template v-else>
      <!-- Архив -->
      <div v-if="showArchive" class="q-pa-sm">
        <div v-if="cards.length === 0" class="text-center q-py-xl" style="color: var(--fc-text-muted)">
          Архив пуст
        </div>
        <div v-else class="archive-grid">
          <q-card
            v-for="card in cards"
            :key="card.id"
            flat
            bordered
            class="crm-card cursor-pointer q-mb-none"
            :style="svArchiveCardStyle(card)"
            @click="openCard(card)"
          >
            <q-card-section class="q-pa-sm">
              <!-- Номер договора + бейдж статуса -->
              <div class="row items-center justify-between q-mb-xs">
                <div style="color: var(--fc-text-light); font-size: 10px">
                  Договор: {{ card.contract_number || `#${card.id}` }}
                </div>
                <q-badge :color="sColor(card)" :label="card.contract_status || card.column_name || 'Архив'" dense style="font-size: 9px" />
              </div>
              <!-- Адрес -->
              <div class="text-weight-bold q-mb-xs" style="font-size: 14px; color: var(--fc-text); word-wrap: break-word">
                {{ card.address || 'Без адреса' }}
              </div>
              <!-- Разделитель -->
              <div style="height: 1px; background: var(--fc-border)" class="q-mb-xs" />
              <!-- Площадь + город + агент -->
              <div class="row items-center justify-between q-mb-xs">
                <div style="font-size: 11px; color: var(--fc-text-light)">
                  <span v-if="card.area">{{ card.area }} м²</span>
                  <span v-if="card.area && card.city"> | </span>
                  <span v-if="card.city">{{ card.city }}</span>
                </div>
                <span
                  v-if="card.agent_type"
                  :style="{ background: agentColorFor(card.agent_type), color: 'white', fontSize: '10px', fontWeight: 'bold', padding: '3px 8px', borderRadius: '4px', lineHeight: '16px' }"
                >{{ card.agent_type }}</span>
              </div>
              <!-- Команда (сворачиваемая) -->
              <div
                v-if="card.senior_manager_name || card.dan_name || card.studio_director_name"
                style="border: 1px solid var(--fc-border-light); border-radius: 4px; padding: 4px 6px; margin-bottom: 4px; background: var(--fc-bg-info)"
                @click.stop
              >
                <div
                  style="font-size: 10px; color: var(--fc-text-light); font-weight: bold; cursor: pointer"
                  @click="showTeamMap[card.id] = !showTeamMap[card.id]"
                >
                  Команда ({{ [card.studio_director_name, card.senior_manager_name, card.dan_name].filter(Boolean).length }})
                  {{ showTeamMap[card.id] ? '▲' : '▼' }}
                </div>
                <div v-if="showTeamMap[card.id]">
                  <div v-if="card.studio_director_name" style="font-size: 10px; color: var(--fc-text); padding: 1px 4px; border-radius: 2px; margin-top: 1px; background: #E8F4FD">
                    РС: {{ card.studio_director_name }}
                  </div>
                  <div v-if="card.senior_manager_name" style="font-size: 10px; color: var(--fc-text); padding: 1px 4px; border-radius: 2px; margin-top: 1px; background: #EAF7F0">
                    СМ: {{ card.senior_manager_name }}
                  </div>
                  <div v-if="card.dan_name" style="font-size: 10px; color: var(--fc-text); padding: 1px 4px; border-radius: 2px; margin-top: 1px; background: #FEF9E7">
                    ДАН: {{ card.dan_name }}
                  </div>
                </div>
              </div>
              <!-- Теги -->
              <div v-if="card.tags" style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 4px; justify-content: center">
                <span
                  v-for="(tag, tidx) in parseSvTags(card.tags)"
                  :key="tidx"
                  :style="{ background: tag.color, color: 'white', borderRadius: '4px', padding: '2px 8px', fontSize: '10px', fontWeight: '600' }"
                >{{ tag.text }}</span>
              </div>
              <!-- Кнопка -->
              <div style="border-top: 1px solid var(--fc-border-light); padding-top: 6px">
                <q-btn
                  flat
                  dense
                  no-caps
                  icon="open_in_new"
                  label="Данные карточки"
                  style="color: var(--fc-text); font-size: 11px; height: 28px; width: 100%; background: var(--fc-bg-alt); border-radius: 4px"
                  @click.stop="openCard(card)"
                />
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Активные — ландшафт: все колонки рядом -->
      <template v-else-if="($q.screen.width > $q.screen.height)">
        <div class="landscape-board">
          <div
            v-for="col in columns"
            :key="col.name"
            class="landscape-column"
            :class="{ 'drag-over': svDragOverCol === col.name }"
            :data-col="col.name"
          >
            <div class="column-frame" style="margin: 0; height: 100%">
              <div class="column-header">
                <span class="column-title">{{ col.name }}</span>
                <span :class="['col-count-badge', { 'has-cards': col.count > 0 }]">{{ col.count }}</span>
              </div>
              <div v-if="col.cards.length > 0" class="column-body" style="overflow-y: auto; flex: 1">
                <div
                  v-for="card in col.cards"
                  :key="card.id"
                  class="drag-card-wrapper"
                  :class="{ 'drag-source': svDragCard?.id === card.id }"
                  @pointerdown="onSvDragStart($event, card)"
                  @pointermove="onSvDragMove"
                  @pointerup="onSvDragEnd"
                  @pointercancel="onSvDragEnd"
                  @click.capture="suppressSvAfterDrag"
                >
                  <q-card class="crm-card q-mb-sm" :style="card.is_paused ? { background: 'var(--fc-state-warning-bg)', borderColor: '#F39C12' } : {}">
                    <q-card-section class="q-pa-sm">
                      <div class="row items-center justify-between q-mb-xs">
                        <div style="color: var(--fc-text-light); font-size: 10px">
                          {{ card.contract_number || `#${card.id}` }}
                        </div>
                        <div class="row items-center" style="gap: 4px">
                          <q-badge
                            v-if="!card.is_paused"
                            color="blue-grey-3"
                            text-color="blue-grey-9"
                            :label="card.column_name"
                            dense
                            style="font-size: 9px"
                          />
                          <q-badge
                            v-else
                            color="warning"
                            label="Приостановлено"
                            dense
                            style="font-size: 9px"
                          />
                          <button class="sv-mute-bell-btn" @click.stop="cardMutes.toggleMute('supervision_card', card.id)">
                            <span class="material-icons" :style="{ fontSize: '14px', color: cardMutes.isMuted('supervision_card', card.id) ? 'var(--fc-text)' : 'var(--fc-border-card)' }">
                              {{ cardMutes.isMuted('supervision_card', card.id) ? 'notifications_off' : 'notifications' }}
                            </span>
                          </button>
                        </div>
                      </div>
                      <div class="text-weight-bold q-mb-xs" style="font-size: 13px; color: var(--fc-text)">
                        {{ card.address || 'Без адреса' }}
                      </div>
                      <div class="row items-center justify-between q-mb-xs">
                        <div style="font-size: 11px; color: var(--fc-text-light)">
                          <span v-if="card.area">{{ card.area }} м²</span>
                          <span v-if="card.area && card.city"> | </span>
                          <span v-if="card.city">{{ card.city }}</span>
                        </div>
                        <span v-if="card.agent_type" :style="{ background: agentColorFor(card.agent_type), color: 'white', fontSize: '10px', fontWeight: 'bold', padding: '3px 8px', borderRadius: '4px' }">{{ card.agent_type }}</span>
                      </div>
                      <div v-if="card.tags" class="row q-gutter-xs q-mb-xs">
                        <span
                          v-for="(tag, tidx) in parseSvTags(card.tags)"
                          :key="tidx"
                          :style="{ display: 'inline-block', background: tag.color, color: 'white', borderRadius: '4px', padding: '2px 8px', fontSize: '10px', fontWeight: '600' }"
                        >{{ tag.text }}</span>
                      </div>
                      <div style="border-top: 1px solid var(--fc-border-light); padding-top: 6px">
                        <q-btn
                          flat
                          dense
                          no-caps
                          icon="open_in_new"
                          label="Данные карточки"
                          style="color: var(--fc-text); font-size: 11px; height: 28px; width: 100%; background: var(--fc-bg-alt); border-radius: 4px"
                          @click="openCard(card)"
                        />
                      </div>
                    </q-card-section>
                  </q-card>
                </div><!-- /drag-card-wrapper -->
              </div>
              <div v-else class="column-empty">
                <q-icon name="inbox" size="32px" color="grey-4" /><div>Нет карточек</div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Активные — QCarousel свайп как CRM -->
      <template v-else>
        <div class="column-nav">
          <button v-for="(col, idx) in columns" :key="col.name" :class="{ active: currentSlide === idx }" @click="currentSlide = idx">
            {{ col.shortName }} <span class="count">{{ col.count }}</span>
          </button>
        </div>
        <q-carousel
          v-model="currentSlide"
          swipeable
          animated
          transition-prev="slide-right"
          transition-next="slide-left"
          style="min-height: calc(100vh - 220px); background: transparent"
        >
          <q-carousel-slide v-for="(col, idx) in columns" :key="col.name" :name="idx" class="q-pa-none">
            <div class="column-frame">
              <div class="column-header">
                <span class="column-title">{{ col.name }}</span>
                <span :class="['col-count-badge', { 'has-cards': col.count > 0 }]">{{ col.count }}</span>
              </div>
              <div v-if="col.cards.length > 0" class="column-body">
                <q-card v-for="card in col.cards" :key="card.id" class="crm-card q-mb-sm" :style="card.is_paused ? { background: 'var(--fc-state-warning-bg)', borderColor: '#F39C12' } : {}">
                  <q-card-section class="q-pa-sm">
                    <!-- 1. Номер договора (слева) + Стадия + Тишина (справа) -->
                    <div class="row items-center justify-between q-mb-xs">
                      <div style="color: var(--fc-text-light); font-size: 10px">
                        {{ card.contract_number || `#${card.id}` }}
                      </div>
                      <div class="row items-center" style="gap: 4px">
                        <q-badge
                          v-if="!card.is_paused"
                          color="blue-grey-3"
                          text-color="blue-grey-9"
                          :label="card.column_name"
                          dense
                          style="font-size: 9px"
                        />
                        <q-badge
                          v-else
                          color="warning"
                          label="Приостановлено"
                          dense
                          style="font-size: 9px"
                        />
                        <button class="sv-mute-bell-btn" @click.stop="cardMutes.toggleMute('supervision_card', card.id)">
                          <span class="material-icons" :style="{ fontSize: '14px', color: cardMutes.isMuted('supervision_card', card.id) ? 'var(--fc-text)' : 'var(--fc-border-card)' }">
                            {{ cardMutes.isMuted('supervision_card', card.id) ? 'notifications_off' : 'notifications' }}
                          </span>
                        </button>
                      </div>
                    </div>
                    <!-- Причина паузы -->
                    <div v-if="card.is_paused && card.pause_reason" class="q-mb-xs">
                      <q-badge
                        color="orange-2"
                        text-color="orange-9"
                        :label="card.pause_reason"
                        dense
                        style="font-size: 9px; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"
                      />
                    </div>
                    <!-- 2. Адрес -->
                    <div class="text-weight-bold q-mb-xs" style="font-size: 13px; color: var(--fc-text)">
                      {{ card.address || 'Без адреса' }}
                    </div>
                    <!-- 3. Площадь/город (слева) + Тип агента badge (справа) -->
                    <div class="row items-center justify-between q-mb-xs">
                      <div style="font-size: 11px; color: var(--fc-text-light)">
                        <span v-if="card.area">{{ card.area }} м²</span>
                        <span v-if="card.area && card.city"> | </span>
                        <span v-if="card.city">{{ card.city }}</span>
                        <span v-if="card.dan_name"> | ДАН: {{ card.dan_name }}</span>
                      </div>
                      <span v-if="card.agent_type" :style="{ background: agentColorFor(card.agent_type), color: 'white', fontSize: '10px', fontWeight: 'bold', padding: '3px 8px', borderRadius: '4px' }">{{ card.agent_type }}</span>
                    </div>
                    <div v-if="card.tags" class="row q-gutter-xs q-mb-xs">
                      <span
                        v-for="(tag, tidx) in parseSvTags(card.tags)"
                        :key="tidx"
                        :style="{ display: 'inline-block', background: tag.color, color: 'white', borderRadius: '4px', padding: '2px 8px', fontSize: '10px', fontWeight: '600' }"
                      >{{ tag.text }}</span>
                    </div>
                    <!-- 4. Дедлайн -->
                    <div v-if="card.deadline" class="q-mb-xs row items-center" style="background: #FFF3CD; border-radius: 4px; padding: 3px 8px; width: 100%">
                      <q-icon name="schedule" size="12px" style="color: #856404" class="q-mr-xs" />
                      <span style="font-size: 10px; color: #856404; font-weight: bold">{{ new Date(card.deadline).toLocaleDateString('ru-RU') }}</span>
                    </div>
                    <!-- 5. Пауза/Возобновить -->
                    <div class="row q-gutter-xs q-mb-xs">
                      <q-btn
                        v-if="!card.is_paused"
                        flat
                        dense
                        no-caps
                        icon="pause"
                        label="Пауза"
                        style="color: #F39C12; font-size: 10px; height: 24px; flex: 1; border: 1px solid #F39C12; border-radius: 4px"
                        @click.stop="quickPause(card)"
                      />
                      <q-btn
                        v-else
                        flat
                        dense
                        no-caps
                        icon="play_arrow"
                        label="Возобновить"
                        style="color: #27AE60; font-size: 10px; height: 24px; flex: 1; border: 1px solid #27AE60; border-radius: 4px"
                        @click.stop="quickResume(card)"
                      />
                    </div>
                    <!-- 6. Кнопки -->
                    <div style="border-top: 1px solid var(--fc-border-light); padding-top: 6px">
                      <q-btn
                        flat
                        dense
                        no-caps
                        icon="open_in_new"
                        label="Данные карточки"
                        style="color: var(--fc-text); font-size: 11px; height: 28px; width: 100%; background: var(--fc-bg-alt); border-radius: 4px"
                        class="q-mb-xs"
                        @click="openCard(card)"
                      />
                      <q-btn
                        flat
                        dense
                        no-caps
                        icon="swap_horiz"
                        label="Переместить"
                        style="color: var(--fc-text-light); font-size: 10px; height: 24px; width: 100%"
                        @click.stop="showMoveDialog(card)"
                      />
                    </div>
                  </q-card-section>
                </q-card>
              </div>
              <div v-else class="column-empty">
                <q-icon name="inbox" size="32px" color="grey-4" /><div>Нет карточек</div>
              </div>
            </div>
          </q-carousel-slide>
        </q-carousel>
      </template>
    </template>
    <!-- Диалог перемещения надзорной карточки -->
    <q-dialog v-model="moveDialogVisible">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: var(--fc-accent); color: var(--fc-text)">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
            Переместить
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
          <div class="text-caption q-mt-xs" style="color: var(--fc-text-light)">
            Текущая: {{ moveCard.column_name }}
          </div>
        </q-card-section>
        <q-list separator>
          <q-item
            v-for="col in SUPERVISION_COLUMNS"
            :key="col"
            v-ripple
            clickable
            :disable="moveCard?.column_name === col"
            @click="doMove(col)"
          >
            <q-item-section>
              <q-item-label :style="{ color: moveCard?.column_name === col ? 'var(--fc-border-card)' : 'var(--fc-text)', fontSize: '13px' }">
                {{ col }}
              </q-item-label>
            </q-item-section>
            <q-item-section v-if="moveCard?.column_name === col" side>
              <q-icon name="check" color="positive" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </q-dialog>

    <page-dashboard :items="dashItems" />
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { supervisionApi } from 'src/services/api'
import { usePermission } from 'src/composables/usePermission'
import { useReferencesStore } from 'src/stores/references'
import { useAuthStore } from 'src/stores/auth'
import { useCardMutesStore } from 'src/stores/cardMutes'
import PageDashboard from 'src/components/PageDashboard.vue'

const router = useRouter()
const $q = useQuasar()
const { can } = usePermission()
const refsStore = useReferencesStore()
const cardMutes = useCardMutesStore()

function agentColorFor(agentType) {
  const agent = refsStore.agentByName?.(agentType)
  return agent?.color || '#95A5A6'
}
const cards = ref([])
const loading = ref(false)
const showArchive = ref(false)
const archiveCount = ref(0)
const activeCount = ref(0)
const showTeamMap = reactive({})

async function loadArchiveCount() {
  try {
    const { data } = await supervisionApi.getCards({ status: 'archived' })
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
    archiveCount.value = data.filter(c => c.dan_id === empId || c.senior_manager_id === empId || c.studio_director_id === empId).length
  } catch { archiveCount.value = 0 }
}
const currentSlide = ref(parseInt(sessionStorage.getItem('sv_slide') || '0'))
const moveDialogVisible = ref(false)
const moveCard = ref(null)

const SUPERVISION_COLUMNS = [
  'Новый заказ', 'В ожидании',
  'Стадия 1: Демонтаж/Монтаж/Штукатурные работы',
  'Стадия 2: Электрика/Сантехника/Звукоизоляция',
  'Стадия 3: Монтаж Пола/Потолков/Шпатлевание стен',
  'Стадия 4: Плиточные работы',
  'Стадия 5: Финишные отделочные работы',
  'Стадия 6: Чистовая электрика/сантехника',
  'Стадия 7: Монтаж Заказной мебели',
  'Стадия 8: Монтаж фабричной мебели/зеркал и стекл',
  'Стадия 9: Финишные доп. работы/декорирование',
  'Выполненный проект',
]

const columns = computed(() => {
  const grouped = {}
  for (const col of SUPERVISION_COLUMNS) grouped[col] = []
  for (const card of cards.value) { const col = card.column_name || 'Новый заказ'; if (!grouped[col]) grouped[col] = []; grouped[col].push(card) }
  return SUPERVISION_COLUMNS.filter(c => grouped[c]).map(c => ({ name: c, shortName: c.replace(/^Стадия \d+: /, '').substring(0, 18), cards: grouped[c], count: grouped[c].length }))
})

watch(columns, (cols) => { if (cols.length > 0 && currentSlide.value >= cols.length) currentSlide.value = 0 })
watch(currentSlide, (v) => { sessionStorage.setItem('sv_slide', String(v)) })

function sColor(card) {
  const cs = card.contract_status || ''
  if (cs === 'РАСТОРГНУТ') return 'negative'
  if (cs === 'СДАН') return 'positive'
  const s = card.column_name || ''
  if (s.includes('Стадия')) return 'orange'
  if (s.includes('Выполненный')) return 'positive'
  return 'blue'
}
function svArchiveCardStyle(card) {
  const cs = card.contract_status || ''
  if (cs === 'РАСТОРГНУТ') return { background: '#FADBD8', borderColor: '#E74C3C' }
  return { background: '#E8F8F5', borderColor: '#27AE60' }
}
function dlColor(d) { const days = Math.ceil((new Date(d) - new Date()) / 86400000); if (days < 0) return '#8B0000'; if (days <= 2) return '#F39C12'; return 'var(--fc-text-light)' }
function openCard(card) { router.push(`/supervision/${card.id}`) }
function parseSvTags(tagsStr) {
  if (!tagsStr) return []
  try {
    const parsed = JSON.parse(tagsStr)
    if (Array.isArray(parsed)) return parsed.map(t => ({ text: String(t.text || ''), color: String(t.color || '#FF6B6B') }))
    return [{ text: String(tagsStr), color: '#FF6B6B' }]
  } catch { return [{ text: String(tagsStr), color: '#FF6B6B' }] }
}

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
  { label: 'В работе', value: cards.value.filter(c => (c.column_name || '').includes('Стадия') && !c.is_paused).length, color: '#F39C12' },
  { label: 'Приостановлено', value: cards.value.filter(c => c.is_paused).length, color: '#E74C3C' },
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

// --- Drag-and-drop (ландшафт) ---
const svDragCard = ref(null)     // reactive: управляет .drag-source opacity — ставится ТОЛЬКО при реальном drag
const svDragOverCol = ref(null)
let _svPendingDragCard = null    // нереактивно: хранит карточку во время ожидания (без визуальных изменений)
let _svDragGhost = null
let _svDragMoved = false
let _svDragReady = false         // true после 150ms удержания
let _svDragTimer = null
let _svDragStartX = 0
let _svDragStartY = 0
let _svDragOffsetX = 0
let _svDragOffsetY = 0
let _svDragEl = null
let _svDragPointerId = null
let _svDragPointerType = ''

function onSvDragStart(e, card) {
  if (e.pointerType === 'mouse' && e.button !== 0) return
  _svPendingDragCard = card   // НЕ svDragCard.value — никаких визуальных изменений пока
  _svDragMoved = false
  _svDragReady = false
  _svDragStartX = e.clientX
  _svDragStartY = e.clientY
  _svDragEl = e.currentTarget
  _svDragPointerId = e.pointerId
  _svDragPointerType = e.pointerType
  const rect = e.currentTarget.getBoundingClientRect()
  _svDragOffsetX = e.clientX - rect.left
  _svDragOffsetY = e.clientY - rect.top
  _svDragTimer = setTimeout(() => {
    if (_svPendingDragCard) _svDragReady = true
  }, 150)
}

function onSvDragMove(e) {
  if (!_svPendingDragCard || e.pointerId !== _svDragPointerId) return
  if (!_svDragReady) return
  const dx = e.clientX - _svDragStartX
  const dy = e.clientY - _svDragStartY
  const threshold = _svDragPointerType === 'touch' ? 15 : 8
  if (!_svDragMoved && Math.hypot(dx, dy) < threshold) return
  if (!_svDragMoved) {
    _svDragMoved = true
    svDragCard.value = _svPendingDragCard  // только теперь — opacity 0.35 на источнике
    try { _svDragEl?.setPointerCapture(_svDragPointerId) } catch {}
    const src = _svDragEl
    _svDragGhost = src.cloneNode(true)
    _svDragGhost.style.cssText = `position:fixed;pointer-events:none;opacity:0.75;z-index:9999;width:${src.offsetWidth}px;box-shadow:0 6px 24px rgba(0,0,0,0.25);transform:rotate(2deg) scale(1.03);border-radius:8px;background:var(--fc-bg);`
    document.body.appendChild(_svDragGhost)
  }
  if (_svDragGhost) {
    _svDragGhost.style.left = (e.clientX - _svDragOffsetX) + 'px'
    _svDragGhost.style.top = (e.clientY - _svDragOffsetY) + 'px'
    _svDragGhost.style.visibility = 'hidden'
  }
  const el = document.elementFromPoint(e.clientX, e.clientY)
  if (_svDragGhost) _svDragGhost.style.visibility = ''
  svDragOverCol.value = el?.closest('[data-col]')?.dataset.col || null
}

async function onSvDragEnd() {
  clearTimeout(_svDragTimer)
  _svDragTimer = null
  _svDragReady = false
  const card = _svPendingDragCard
  _svPendingDragCard = null
  if (!card) return
  const targetCol = svDragOverCol.value
  if (_svDragGhost) { _svDragGhost.remove(); _svDragGhost = null }
  svDragOverCol.value = null
  svDragCard.value = null
  if (!(_svDragMoved && targetCol && targetCol !== card.column_name)) {
    _svDragMoved = false
    return
  }
  if (!can('supervision.move')) { _svDragMoved = false; return }
  moveCard.value = card
  await doMove(targetCol)
}

function suppressSvAfterDrag(e) {
  if (_svDragMoved) {
    e.stopPropagation()
    e.preventDefault()
    _svDragMoved = false
  }
}

async function loadCards() {
  loading.value = true
  try {
    const { data } = await supervisionApi.getCards({ status: showArchive.value ? 'archived' : 'active' })
    cards.value = data
    if (!showArchive.value) activeCount.value = data.length
  } catch { cards.value = [] } finally { loading.value = false }
}

watch(showArchive, (isArchive) => { if (!isArchive && can('supervision.view_archive')) loadArchiveCount() })

onMounted(() => { loadCards(); cardMutes.load(); if (can('supervision.view_archive')) loadArchiveCount() })
</script>

<style scoped>
.archive-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 8px;
}

.toggle-pills { display: inline-flex; border: 1px solid var(--fc-border); border-radius: 6px; overflow: hidden }
.toggle-pills button { border: none; background: var(--fc-tab-hover); color: var(--fc-text-secondary); font-size: 11px; padding: 5px 12px; cursor: pointer; transition: all 0.2s; font-family: inherit }
.toggle-pills button.active { background: var(--fc-bg); color: var(--fc-text); font-weight: bold; box-shadow: 0 1px 3px var(--fc-shadow-sm) }
.toggle-pills button + button { border-left: 1px solid var(--fc-border) }
.pill-count { display: inline-block; background: var(--fc-shadow-sm); border-radius: 8px; padding: 0 5px; margin-left: 3px; font-size: 10px; min-width: 16px; text-align: center; }
.toggle-pills button.active .pill-count { background: var(--fc-accent); color: var(--fc-text); }
.column-nav { display: flex; overflow-x: auto; padding: 6px 8px; gap: 4px; border-bottom: 1px solid var(--fc-border-light); -webkit-overflow-scrolling: touch; scrollbar-width: none }
.column-nav::-webkit-scrollbar { display: none }
.column-nav button { border: 1px solid var(--fc-border); border-radius: 16px; background: var(--fc-bg-alt); color: var(--fc-text-light); font-size: 10px; padding: 3px 10px; white-space: nowrap; cursor: pointer; font-family: inherit; transition: all 0.2s; flex-shrink: 0 }
.column-nav button.active { background: var(--fc-text); color: white; border-color: var(--fc-text); font-weight: bold }
.column-nav button .count { display: inline-block; background: rgba(255,255,255,0.2); border-radius: 8px; padding: 0 4px; margin-left: 3px; font-size: 9px }
.column-nav button.active .count { background: rgba(255,255,255,0.3) }
.column-frame { border: 1px solid var(--fc-border); border-radius: 8px; margin: 8px; background: var(--fc-bg-hover); min-height: calc(100vh - 260px); display: flex; flex-direction: column }
.column-header { display: flex; align-items: flex-start; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid var(--fc-border-light); background: var(--fc-bg); border-radius: 8px 8px 0 0; min-height: 52px; box-sizing: border-box; }
.column-title { font-size: 13px; font-weight: bold; color: var(--fc-text); flex: 1; white-space: normal; line-height: 1.35; }
.column-body { padding: 8px; flex: 1; overflow-y: auto }
.column-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--fc-text-disabled); font-size: 12px; padding: 40px 0 }
.landscape-board { position: fixed; left: var(--drawer-offset, 0px); right: 0; top: calc(var(--q-header-height, 48px) + 41px); bottom: var(--q-footer-height, 56px); display: flex; flex-direction: row; overflow-x: auto; overflow-y: hidden; gap: 8px; padding: 8px; background: var(--fc-bg); z-index: 1; -webkit-overflow-scrolling: touch; transition: left 0.3s ease; }
.landscape-column { flex: 1 1 280px; min-width: 280px; display: flex; flex-direction: column; height: 100%; }
.col-count-badge { border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; flex-shrink: 0; background: var(--fc-border-light); color: var(--fc-text-light); }
.col-count-badge.has-cards { background: var(--fc-accent); color: var(--fc-text); }
.landscape-column .column-frame { flex: 1; margin: 0; display: flex; flex-direction: column; overflow: hidden; height: 100%; }
.landscape-column .column-body { overflow-y: auto; flex: 1; }

/* Drag-and-drop (ландшафт) */
.drag-card-wrapper {
  touch-action: none;
  cursor: grab;
}
.drag-card-wrapper button,
.drag-card-wrapper a,
.drag-card-wrapper .q-btn {
  cursor: pointer;
}
.drag-source > * {
  opacity: 0.35;
  pointer-events: none;
}
.landscape-column.drag-over > .column-frame {
  border-color: var(--fc-accent);
  box-shadow: 0 0 0 2px var(--fc-accent);
  background: var(--fc-highlight-yellow);
}
.sv-mute-bell-btn {
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
