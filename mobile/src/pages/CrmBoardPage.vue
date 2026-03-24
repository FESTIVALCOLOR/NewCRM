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

    <!-- Колонки — табы сверху (мобиль) -->
    <template v-if="!crmStore.loading">
      <q-tabs
        v-if="$q.screen.lt.md"
        v-model="activeColumn"
        dense
        active-color="dark"
        indicator-color="accent"
        no-caps
        align="left"
        outside-arrows
        mobile-arrows
        class="q-mt-xs"
        style="border-bottom: 1px solid #E0E0E0"
      >
        <q-tab
          v-for="col in crmStore.columns"
          :key="col.name"
          :name="col.name"
          no-caps
          style="font-size: 11px; padding: 4px 8px"
        >
          <div>{{ col.shortName }}</div>
          <q-badge color="grey-7" :label="col.count" class="q-ml-xs" style="font-size: 9px" />
        </q-tab>
      </q-tabs>

      <q-tab-panels v-if="$q.screen.lt.md" v-model="activeColumn" animated swipeable class="bg-transparent">
        <q-tab-panel v-for="col in crmStore.columns" :key="col.name" :name="col.name" class="q-pa-sm">
          <div v-if="col.cards.length === 0" class="text-center q-py-xl" style="color: #999">
            <q-icon name="inbox" size="40px" class="q-mb-sm" />
            <div class="text-caption">Нет карточек</div>
          </div>
          <crm-card-item v-for="card in col.cards" :key="card.id" :card="card" @click="openCard(card.id)" />
        </q-tab-panel>
      </q-tab-panels>

      <!-- Планшет — колонки рядом -->
      <div v-if="$q.screen.gt.sm" class="row q-pa-sm q-col-gutter-sm" style="overflow-x: auto">
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
