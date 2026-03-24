<template>
  <q-page>
    <!-- Тулбар -->
    <div class="q-pa-sm" style="border-bottom: 1px solid #E0E0E0">
      <div class="row items-center q-gutter-xs">
        <!-- Активные / Архив -->
        <q-btn
          :style="!showArchive ? 'background: white; border-bottom: 2px solid #ffd93c; font-weight: bold' : 'background: #E8E8E8'"
          label="Активные" dense no-caps size="sm"
          style="border: 1px solid #d9d9d9; border-radius: 4px; color: #333; font-size: 11px; padding: 4px 10px"
          @click="showArchive = false; loadCards()"
        />
        <q-btn
          :style="showArchive ? 'background: white; border-bottom: 2px solid #ffd93c; font-weight: bold' : 'background: #E8E8E8'"
          label="Архив" dense no-caps size="sm"
          style="border: 1px solid #d9d9d9; border-radius: 4px; color: #333; font-size: 11px; padding: 4px 10px"
          @click="showArchive = true; loadCards()"
        />
        <q-space />
        <div class="text-caption" style="color: #888">{{ cards.length }} объектов</div>
      </div>
    </div>

    <div v-if="loading" class="q-pa-md">
      <q-card class="is-card q-mb-sm" v-for="n in 4" :key="n">
        <q-card-section><q-skeleton type="text" width="50%" /><q-skeleton type="text" width="70%" /></q-card-section>
      </q-card>
    </div>

    <template v-else>
      <!-- Архив — просто список -->
      <div v-if="showArchive" class="q-pa-sm">
        <q-card v-for="card in cards" :key="card.id" class="is-card q-mb-sm cursor-pointer" @click="openCard(card)">
          <q-card-section class="q-pa-md">
            <div class="row items-center justify-between q-mb-xs">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">{{ card.contract_number || `#${card.id}` }}</div>
              <q-badge :color="sColor(card)" :label="card.column_name || card.status || 'Архив'" dense />
            </div>
            <div class="text-body2" style="color: #333">{{ card.address || 'Без адреса' }}</div>
            <div class="row q-gutter-sm text-caption" style="color: #888">
              <span v-if="card.area">{{ card.area }} м²</span>
              <span v-if="card.city">{{ card.city }}</span>
            </div>
          </q-card-section>
        </q-card>
        <div v-if="cards.length === 0" class="text-center q-py-xl" style="color: #999">Архив пуст</div>
      </div>

      <!-- Активные — kanban (как CRM) -->
      <template v-else>
        <!-- Столбцы стадий -->
        <div class="q-pa-xs" style="overflow-x: auto; white-space: nowrap; border: 1px solid #d9d9d9; border-radius: 4px; margin: 4px">
          <q-btn
            v-for="col in columns" :key="col.name"
            dense no-caps size="sm"
            :label="`${col.shortName} (${col.count})`"
            :style="activeCol === col.name
              ? 'background: white; border-bottom: 2px solid #ffd93c; font-weight: bold; color: #333'
              : 'background: #E8E8E8; color: #666'"
            style="border: 1px solid #d9d9d9; border-radius: 4px 4px 0 0; font-size: 10px; padding: 4px 8px; margin-right: 2px"
            @click="activeCol = col.name"
          />
        </div>
        <div style="border: 1px solid #d9d9d9; border-top: none; border-radius: 0 0 4px 4px; margin: 0 4px; min-height: 200px">
          <div v-for="col in columns" :key="col.name" v-show="activeCol === col.name" class="q-pa-sm">
            <div v-if="col.cards.length === 0" class="text-center q-py-xl" style="color: #999">
              <q-icon name="inbox" size="40px" class="q-mb-sm" />
              <div class="text-caption">Нет карточек</div>
            </div>
            <q-card v-for="card in col.cards" :key="card.id" class="is-card q-mb-sm cursor-pointer" @click="openCard(card)">
              <q-card-section class="q-pa-sm">
                <div class="row items-center justify-between q-mb-xs">
                  <div class="text-caption" style="color: #888; font-size: 10px">{{ card.contract_number || `#${card.id}` }}</div>
                  <q-badge v-if="card.is_paused" color="warning" label="Приостановлено" dense />
                </div>
                <div class="text-weight-bold" style="font-size: 13px; color: #222">{{ card.address || 'Без адреса' }}</div>
                <div class="row q-gutter-xs text-caption" style="color: #888">
                  <span v-if="card.area">{{ card.area }} м²</span>
                  <span v-if="card.city">{{ card.city }}</span>
                  <span v-if="card.dan_name">ДАН: {{ card.dan_name }}</span>
                </div>
                <div v-if="card.deadline" class="text-caption q-mt-xs" :style="{ color: dlColor(card.deadline) }">
                  Дедлайн: {{ new Date(card.deadline).toLocaleDateString('ru-RU') }}
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </template>
    </template>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { supervisionApi } from 'src/services/api'

const router = useRouter()
const cards = ref([])
const loading = ref(false)
const showArchive = ref(false)
const activeCol = ref('Новый заказ')

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
  for (const card of cards.value) {
    const col = card.column_name || 'Новый заказ'
    if (!grouped[col]) grouped[col] = []
    grouped[col].push(card)
  }
  return SUPERVISION_COLUMNS.filter(c => grouped[c]).map(c => ({
    name: c,
    shortName: c.replace(/^Стадия \d+: /, '').substring(0, 15),
    cards: grouped[c],
    count: grouped[c].length
  }))
})

function sColor(card) {
  const s = card.column_name || card.status || ''
  if (s.includes('работе') || s.includes('Стадия')) return 'orange'
  if (s.includes('Сдан') || s.includes('Выполненный')) return 'positive'
  if (s.includes('Приостановлено')) return 'warning'
  return 'blue'
}

function dlColor(d) {
  const days = Math.ceil((new Date(d) - new Date()) / 86400000)
  if (days < 0) return '#8B0000'
  if (days <= 2) return '#F39C12'
  return '#888'
}

function openCard(card) { router.push(`/supervision/${card.id}`) }

async function loadCards() {
  loading.value = true
  try {
    const { data } = await supervisionApi.getCards({ status: showArchive.value ? 'archived' : 'active' })
    cards.value = data
  } catch { cards.value = [] }
  finally { loading.value = false }
}

onMounted(() => loadCards())
</script>
