<template>
  <q-page padding>
    <q-pull-to-refresh @refresh="onRefresh">
      <!-- Поиск -->
      <q-input
        v-model="search"
        placeholder="Поиск договоров..."
        outlined
        dense
        rounded
        class="q-mb-md"
      >
        <template v-slot:prepend><q-icon name="search" /></template>
        <template v-slot:append v-if="search">
          <q-icon name="close" class="cursor-pointer" @click="search = ''" />
        </template>
      </q-input>

      <div class="text-caption text-grey-7 q-mb-sm" v-if="!loading">
        Договоров: {{ filtered.length }}
      </div>

      <!-- Загрузка -->
      <div v-if="loading">
        <q-card class="is-card q-mb-sm" v-for="n in 5" :key="n">
          <q-card-section>
            <q-skeleton type="text" width="50%" class="q-mb-xs" />
            <q-skeleton type="text" width="70%" />
          </q-card-section>
        </q-card>
      </div>

      <!-- Список -->
      <template v-else>
        <q-card
          v-for="contract in filtered"
          :key="contract.id"
          class="is-card q-mb-sm cursor-pointer"
          @click="$router.push(`/contracts/${contract.id}`)"
        >
          <q-card-section class="q-pa-md">
            <div class="row items-center justify-between q-mb-xs">
              <div class="text-subtitle2 text-weight-bold text-primary">
                {{ contract.contract_number }}
              </div>
              <q-badge :color="statusColor(contract.status)" :label="contract.status" dense />
            </div>
            <div class="text-body2 q-mb-xs">{{ contract.address || 'Без адреса' }}</div>
            <div class="row q-gutter-md text-caption text-grey-7">
              <span>{{ contract.project_type }}</span>
              <span v-if="contract.area">{{ contract.area }} м²</span>
              <span v-if="contract.city">{{ contract.city }}</span>
            </div>
          </q-card-section>
        </q-card>

        <div v-if="filtered.length === 0" class="text-center q-pa-xl text-grey-5">
          <q-icon name="description" size="48px" class="q-mb-sm" />
          <div>{{ search ? 'Ничего не найдено' : 'Нет договоров' }}</div>
        </div>
      </template>
    </q-pull-to-refresh>
    <!-- FAB создания -->
    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-btn fab icon="add" color="primary" @click="showForm = true" />
    </q-page-sticky>

    <contract-form-dialog v-model="showForm" @saved="loadContracts" />
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { contractsApi } from 'src/services/api'
import ContractFormDialog from 'src/components/ContractFormDialog.vue'

const contracts = ref([])
const loading = ref(false)
const search = ref('')
const showForm = ref(false)

const filtered = computed(() => {
  if (!search.value) return contracts.value
  const q = search.value.toLowerCase()
  return contracts.value.filter(c =>
    (c.contract_number || '').toLowerCase().includes(q) ||
    (c.address || '').toLowerCase().includes(q) ||
    (c.city || '').toLowerCase().includes(q)
  )
})

function statusColor(status) {
  if (!status) return 'grey'
  if (status === 'В работе') return 'orange'
  if (status.includes('СДАН') || status.includes('Сдан')) return 'positive'
  if (status.includes('РАСТОРГНУТ')) return 'negative'
  if (status.includes('НАДЗОР') || status.includes('надзор')) return 'purple'
  return 'blue'
}

async function loadContracts() {
  loading.value = true
  try {
    const { data } = await contractsApi.getList({ limit: 200 })
    contracts.value = data
  } catch {
    contracts.value = []
  } finally {
    loading.value = false
  }
}

function onRefresh(done) {
  loadContracts().finally(done)
}

onMounted(() => loadContracts())
</script>
