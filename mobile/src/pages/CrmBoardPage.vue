<template>
  <q-page>
    <!-- Фильтры -->
    <div class="q-pa-sm q-pb-none">
      <div class="row items-center q-gutter-xs">
        <q-btn-toggle
          v-model="crmStore.projectType"
          no-caps
          dense
          unelevated
          toggle-color="primary"
          :options="[
            { label: 'Индивидуальные', value: 'Индивидуальный' },
            { label: 'Шаблонные', value: 'Шаблонный' }
          ]"
          class="q-mr-sm"
          @update:model-value="crmStore.loadCards()"
        />
        <q-space />
        <q-btn
          flat
          dense
          :icon="crmStore.showArchive ? 'unarchive' : 'archive'"
          :color="crmStore.showArchive ? 'primary' : 'grey-7'"
          @click="crmStore.toggleArchive()"
        >
          <q-tooltip>{{ crmStore.showArchive ? 'Активные' : 'Архив' }}</q-tooltip>
        </q-btn>
        <q-badge color="grey-7" :label="`${crmStore.totalCards} карточек`" class="q-ml-xs" />
      </div>
    </div>

    <!-- Загрузка -->
    <div v-if="crmStore.loading" class="q-pa-md">
      <q-card class="is-card q-mb-sm" v-for="n in 3" :key="n">
        <q-card-section>
          <q-skeleton type="text" width="50%" class="q-mb-sm" />
          <q-skeleton type="text" width="70%" />
          <q-skeleton type="text" width="40%" />
        </q-card-section>
      </q-card>
    </div>

    <!-- Свайпабельные колонки (на телефоне) -->
    <q-tabs
      v-if="!crmStore.loading && $q.screen.lt.md"
      v-model="activeColumn"
      dense
      active-color="primary"
      indicator-color="primary"
      class="text-grey-7 q-mt-xs"
      narrow-indicator
      no-caps
      align="left"
      inline-label
      outside-arrows
      mobile-arrows
    >
      <q-tab
        v-for="col in crmStore.columns"
        :key="col.name"
        :name="col.name"
        :label="`${col.shortName} (${col.count})`"
        no-caps
      />
    </q-tabs>

    <q-tab-panels
      v-if="!crmStore.loading && $q.screen.lt.md"
      v-model="activeColumn"
      animated
      swipeable
      class="bg-transparent"
    >
      <q-tab-panel
        v-for="col in crmStore.columns"
        :key="col.name"
        :name="col.name"
        class="q-pa-sm"
      >
        <div v-if="col.cards.length === 0" class="text-center text-grey-5 q-py-xl">
          <q-icon name="inbox" size="48px" class="q-mb-sm" />
          <div>Нет карточек</div>
        </div>

        <crm-card-item
          v-for="card in col.cards"
          :key="card.id"
          :card="card"
          @click="openCard(card.id)"
        />
      </q-tab-panel>
    </q-tab-panels>

    <!-- Все колонки рядом (планшет/десктоп) -->
    <div v-if="!crmStore.loading && $q.screen.gt.sm" class="row q-pa-sm q-col-gutter-sm" style="overflow-x: auto">
      <div
        v-for="col in crmStore.columns"
        :key="col.name"
        class="col-3"
        style="min-width: 280px"
      >
        <q-card class="is-card">
          <q-card-section class="q-pb-xs">
            <div class="row items-center justify-between">
              <div class="text-subtitle2 text-weight-bold">{{ col.shortName }}</div>
              <q-badge color="primary" :label="col.count" />
            </div>
          </q-card-section>
          <q-card-section class="q-pt-xs">
            <crm-card-item
              v-for="card in col.cards"
              :key="card.id"
              :card="card"
              @click="openCard(card.id)"
            />
          </q-card-section>
        </q-card>
      </div>
    </div>
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

// Установить первую колонку при загрузке
watch(() => crmStore.columns, (cols) => {
  if (cols.length > 0 && !cols.find(c => c.name === activeColumn.value)) {
    activeColumn.value = cols[0].name
  }
})

function openCard(cardId) {
  router.push(`/crm/${cardId}`)
}

onMounted(() => {
  crmStore.loadCards()
})
</script>
