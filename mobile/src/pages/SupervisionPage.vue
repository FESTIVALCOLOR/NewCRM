<template>
  <q-page padding>
    <q-pull-to-refresh @refresh="onRefresh">
      <!-- Список карточек надзора -->
      <div v-if="loading">
        <q-card class="is-card q-mb-sm" v-for="n in 4" :key="n">
          <q-card-section>
            <q-skeleton type="text" width="50%" class="q-mb-xs" />
            <q-skeleton type="text" width="70%" />
            <q-skeleton type="text" width="30%" class="q-mt-xs" />
          </q-card-section>
        </q-card>
      </div>

      <template v-else>
        <div class="text-caption text-grey-7 q-mb-sm">
          Объектов: {{ cards.length }}
        </div>

        <q-card
          v-for="card in cards"
          :key="card.id"
          class="is-card q-mb-sm cursor-pointer"
          @click="openCard(card)"
        >
          <q-card-section class="q-pa-md">
            <div class="row items-center justify-between q-mb-xs">
              <div class="text-subtitle2 text-weight-bold">{{ card.contract_number || `#${card.id}` }}</div>
              <q-badge :color="statusColor(card.status)" :label="card.status || 'Активный'" dense />
            </div>
            <div class="text-body2 q-mb-xs">{{ card.address || 'Без адреса' }}</div>
            <div class="row q-gutter-md text-caption text-grey-7">
              <span v-if="card.area">{{ card.area }} м²</span>
              <span v-if="card.city">{{ card.city }}</span>
              <span v-if="card.executor_name">{{ card.executor_name }}</span>
            </div>
          </q-card-section>
        </q-card>

        <div v-if="cards.length === 0" class="text-center q-pa-xl text-grey-5">
          <q-icon name="engineering" size="48px" class="q-mb-sm" />
          <div>Нет объектов надзора</div>
        </div>
      </template>
    </q-pull-to-refresh>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { supervisionApi } from 'src/services/api'

const router = useRouter()
const cards = ref([])
const loading = ref(false)

function statusColor(status) {
  if (!status) return 'grey'
  if (status.includes('работе') || status === 'Авторский надзор') return 'orange'
  if (status.includes('сдан') || status.includes('Сдан')) return 'positive'
  if (status.includes('Приостановлено')) return 'warning'
  return 'blue'
}

function openCard(card) {
  router.push(`/supervision/${card.id}`)
}

async function loadCards() {
  loading.value = true
  try {
    const { data } = await supervisionApi.getCards()
    cards.value = data
  } catch {
    cards.value = []
  } finally {
    loading.value = false
  }
}

function onRefresh(done) {
  loadCards().finally(done)
}

onMounted(() => {
  loadCards()
})
</script>
