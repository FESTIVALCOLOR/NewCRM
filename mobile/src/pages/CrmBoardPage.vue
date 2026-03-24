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
        <crm-card-item v-for="card in crmStore.cards" :key="card.id" :card="card" @click="openCard(card.id)" />
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
                <q-badge color="grey-7" :label="col.count" />
              </div>
              <div class="column-body" v-if="col.cards.length > 0">
                <crm-card-item v-for="card in col.cards" :key="card.id" :card="card" @click="openCard(card.id)" />
              </div>
              <div v-else class="column-empty">
                <q-icon name="inbox" size="32px" color="grey-4" />
                <div>Нет карточек</div>
              </div>
            </div>
          </q-carousel-slide>
        </q-carousel>
      </template>

      <!-- Планшет — колонки рядом -->
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
              <div v-if="col.cards.length === 0" class="text-center q-py-md" style="color: #bbb; font-size: 11px">Нет карточек</div>
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
const currentSlide = ref(0)

// При смене данных сбрасываем слайд на первый непустой столбец
watch(() => crmStore.columns, (cols) => {
  if (cols.length > 0) {
    const firstNonEmpty = cols.findIndex(c => c.count > 0)
    currentSlide.value = firstNonEmpty >= 0 ? firstNonEmpty : 0
  }
})

function openCard(cardId) { router.push(`/crm/${cardId}`) }

onMounted(() => { crmStore.loadCards() })
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
