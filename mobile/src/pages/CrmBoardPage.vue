<template>
  <q-page>
    <!-- Тулбар: индивидуальные/шаблонные + обновить + архив -->
    <div class="q-pa-sm" style="border-bottom: 1px solid #E0E0E0">
      <div class="row items-center q-gutter-xs">
        <!-- Индивидуальные / Шаблонные (как десктоп — серые кнопки, жёлтый border selected) -->
        <q-btn
          :outline="crmStore.projectType !== 'Индивидуальный'"
          :unelevated="crmStore.projectType === 'Индивидуальный'"
          :style="crmStore.projectType === 'Индивидуальный' ? 'background: white; border-bottom: 2px solid #ffd93c; font-weight: bold' : 'background: #E8E8E8'"
          label="Индивидуальные"
          dense no-caps size="sm"
          style="border: 1px solid #d9d9d9; border-radius: 4px; color: #333; font-size: 11px; padding: 4px 12px"
          @click="crmStore.setProjectType('Индивидуальный')"
        />
        <q-btn
          :outline="crmStore.projectType !== 'Шаблонный'"
          :unelevated="crmStore.projectType === 'Шаблонный'"
          :style="crmStore.projectType === 'Шаблонный' ? 'background: white; border-bottom: 2px solid #ffd93c; font-weight: bold' : 'background: #E8E8E8'"
          label="Шаблонные"
          dense no-caps size="sm"
          style="border: 1px solid #d9d9d9; border-radius: 4px; color: #333; font-size: 11px; padding: 4px 12px"
          @click="crmStore.setProjectType('Шаблонный')"
        />
        <q-space />
        <!-- Активные / Архив — toggle как индивидуальные/шаблонные -->
        <q-btn
          :style="!crmStore.showArchive ? 'background: white; border-bottom: 2px solid #ffd93c; font-weight: bold' : 'background: #E8E8E8'"
          label="Активные" dense no-caps size="sm"
          style="border: 1px solid #d9d9d9; border-radius: 4px; color: #333; font-size: 11px; padding: 4px 10px"
          @click="crmStore.showArchive && crmStore.toggleArchive()"
        />
        <q-btn
          :style="crmStore.showArchive ? 'background: white; border-bottom: 2px solid #ffd93c; font-weight: bold' : 'background: #E8E8E8'"
          label="Архив" dense no-caps size="sm"
          style="border: 1px solid #d9d9d9; border-radius: 4px; color: #333; font-size: 11px; padding: 4px 10px"
          @click="!crmStore.showArchive && crmStore.toggleArchive()"
        />
      </div>
    </div>

    <!-- Загрузка -->
    <div v-if="crmStore.loading" class="q-pa-md">
      <q-card class="is-card q-mb-sm" v-for="n in 3" :key="n">
        <q-card-section><q-skeleton type="text" width="50%" /><q-skeleton type="text" width="70%" /></q-card-section>
      </q-card>
    </div>

    <!-- Колонки -->
    <template v-if="!crmStore.loading">

      <!-- АРХИВ — просто список без столбцов -->
      <div v-if="crmStore.showArchive" class="q-pa-sm">
        <div v-if="crmStore.cards.length === 0" class="text-center q-py-xl" style="color: #999">
          <q-icon name="archive" size="40px" class="q-mb-sm" />
          <div class="text-caption">Архив пуст</div>
        </div>
        <crm-card-item v-for="card in crmStore.cards" :key="card.id" :card="card" @click="openCard(card.id)" />
      </div>

      <!-- АКТИВНЫЕ — столбцы-кнопки -->
      <div v-if="!crmStore.showArchive && $q.screen.lt.md" class="q-pa-xs" style="overflow-x: auto; white-space: nowrap; border: 1px solid #d9d9d9; border-radius: 4px; margin: 4px">
        <q-btn
          v-for="col in crmStore.columns"
          :key="col.name"
          dense no-caps size="sm"
          :label="`${col.shortName} (${col.count})`"
          :style="activeColumn === col.name
            ? 'background: white; border-bottom: 2px solid #ffd93c; font-weight: bold; color: #333'
            : 'background: #E8E8E8; color: #666'"
          style="border: 1px solid #d9d9d9; border-radius: 4px 4px 0 0; font-size: 10px; padding: 4px 8px; margin-right: 2px"
          @click="activeColumn = col.name"
        />
      </div>

      <!-- Контент колонки (в рамке) — только для активных -->
      <div v-if="!crmStore.showArchive && $q.screen.lt.md" style="border: 1px solid #d9d9d9; border-top: none; border-radius: 0 0 4px 4px; margin: 0 4px; min-height: 200px">
        <div v-for="col in crmStore.columns" :key="col.name" v-show="activeColumn === col.name" class="q-pa-sm">
          <div v-if="col.cards.length === 0" class="text-center q-py-xl" style="color: #999">
            <q-icon name="inbox" size="40px" class="q-mb-sm" />
            <div class="text-caption">Нет карточек</div>
          </div>
          <crm-card-item v-for="card in col.cards" :key="card.id" :card="card" @click="openCard(card.id)" />
        </div>
      </div>

      <!-- Планшет — колонки рядом (только для активных) -->
      <div v-if="$q.screen.gt.sm && !crmStore.showArchive" class="row q-pa-sm q-col-gutter-sm" style="overflow-x: auto">
        <div v-for="col in crmStore.columns" :key="col.name" class="col-3" style="min-width: 280px">
          <q-card class="is-card">
            <q-card-section class="q-pb-xs">
              <div class="row items-center justify-between">
                <div class="text-weight-bold" style="font-size: 12px; color: #333">{{ col.shortName }}</div>
                <q-badge color="grey-7" :label="col.count" />
              </div>
            </q-card-section>
            <q-card-section class="q-pt-xs">
              <crm-card-item v-for="card in col.cards" :key="card.id" :card="card" @click="openCard(card.id)" />
            </q-card-section>
          </q-card>
        </div>
      </div>
    </template>
  </q-page>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useCrmStore } from 'src/stores/crm'
import CrmCardItem from 'src/components/CrmCardItem.vue'

const $q = useQuasar()
const router = useRouter()
const crmStore = useCrmStore()
const activeColumn = ref('Новый заказ')

watch(() => crmStore.columns, (cols) => {
  if (cols.length > 0 && !cols.find(c => c.name === activeColumn.value)) {
    activeColumn.value = cols[0].name
  }
})

function openCard(cardId) { router.push(`/crm/${cardId}`) }

onMounted(() => { crmStore.loadCards() })
</script>
