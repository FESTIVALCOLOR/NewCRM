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

      <!-- Фильтры -->
      <div class="row q-col-gutter-xs q-mb-sm">
        <div class="col-4">
          <q-select v-model="statusFilter" :options="statusOpts" label="Статус" outlined dense emit-value map-options clearable />
        </div>
        <div class="col-4">
          <q-select v-model="typeFilter" :options="typeOpts" label="Тип" outlined dense emit-value map-options clearable />
        </div>
        <div class="col-4">
          <q-select v-model="agentFilter" :options="agentOpts" label="Агент" outlined dense clearable />
        </div>
      </div>

      <div class="text-caption" style="color: #888" v-if="!loading">
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
          :style="cardBgStyle(contract)"
          @click="$router.push(`/contracts/${contract.id}`)"
        >
          <q-card-section class="q-pa-md">
            <div class="row items-center justify-between q-mb-xs">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                {{ contract.contract_number }}
              </div>
              <div class="row q-gutter-xs">
                <q-badge v-if="contract.agent_type" :style="{ background: agentColor(contract.agent_type) }" :label="contract.agent_type" dense text-color="white" />
                <q-badge :color="statusColor(contract.status)" :label="contract.status" dense />
              </div>
            </div>
            <div class="text-body2 q-mb-xs" style="color: #333">{{ contract.address || 'Без адреса' }}</div>
            <div class="row q-gutter-md text-caption" style="color: #888">
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
      <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="showForm = true" />
    </q-page-sticky>

    <contract-form-dialog v-model="showForm" @saved="loadContracts" />
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { contractsApi } from 'src/services/api'
import { useReferencesStore } from 'src/stores/references'
import ContractFormDialog from 'src/components/ContractFormDialog.vue'

const refs = useReferencesStore()
const contracts = ref([])
const loading = ref(false)
const search = ref('')
const showForm = ref(false)
const statusFilter = ref(null)
const typeFilter = ref(null)
const agentFilter = ref(null)

const statusOpts = [
  { label: 'В работе', value: 'В работе' },
  { label: 'Новый заказ', value: 'Новый заказ' },
  { label: 'СДАН', value: 'СДАН' },
  { label: 'РАСТОРГНУТ', value: 'РАСТОРГНУТ' },
  { label: 'АВТ. НАДЗОР', value: 'АВТОРСКИЙ НАДЗОР' }
]

const typeOpts = [
  { label: 'Индивидуальный', value: 'Индивидуальный' },
  { label: 'Шаблонный', value: 'Шаблонный' }
]

const agentOpts = computed(() => refs.agentNames())

function agentColor(agentName) {
  const agent = refs.agentByName(agentName)
  return agent?.color || '#95A5A6'
}

// Фон карточки: зелёный если оплачен, оранжевый если нет
function cardBgStyle(contract) {
  if (contract.status?.includes('СДАН')) return { background: '#E8F5E9' }
  if (contract.status === 'В работе') return { background: '#FFF8E1' }
  return {}
}

const filtered = computed(() => {
  let result = contracts.value
  if (search.value) {
    const q = search.value.toLowerCase()
    result = result.filter(c =>
      (c.contract_number || '').toLowerCase().includes(q) ||
      (c.address || '').toLowerCase().includes(q) ||
      (c.city || '').toLowerCase().includes(q)
    )
  }
  if (statusFilter.value) result = result.filter(c => c.status === statusFilter.value)
  if (typeFilter.value) result = result.filter(c => c.project_type === typeFilter.value)
  if (agentFilter.value) result = result.filter(c => c.agent_type === agentFilter.value)
  return result
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
