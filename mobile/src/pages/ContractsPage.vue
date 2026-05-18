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
        <template #prepend>
          <q-icon name="search" />
        </template>
        <template v-if="search" #append>
          <q-icon name="close" class="cursor-pointer" @click="search = ''" />
        </template>
      </q-input>

      <!-- Фильтры -->
      <div class="row q-col-gutter-xs q-mb-sm">
        <div class="col-3">
          <q-select
            v-model="statusFilter"
            :options="statusOpts"
            label="Статус"
            outlined
            dense
            emit-value
            map-options
            clearable
          />
        </div>
        <div class="col-3">
          <q-select
            v-model="typeFilter"
            :options="typeOpts"
            label="Тип"
            outlined
            dense
            emit-value
            map-options
            clearable
          />
        </div>
        <div class="col-3">
          <q-select
            v-model="agentFilter"
            :options="agentOpts"
            label="Агент"
            outlined
            dense
            clearable
          />
        </div>
        <div class="col-3">
          <q-select
            v-model="sortBy"
            :options="sortOptions"
            label="Сортировка"
            outlined
            dense
            emit-value
            map-options
            clearable
          />
        </div>
      </div>

      <div v-if="!loading" class="text-caption" style="color: #888">
        Договоров: {{ filtered.length }}
      </div>

      <!-- Загрузка -->
      <div v-if="loading">
        <q-card v-for="n in 5" :key="n" class="is-card q-mb-sm">
          <q-card-section>
            <q-skeleton type="text" width="50%" class="q-mb-xs" />
            <q-skeleton type="text" width="70%" />
          </q-card-section>
        </q-card>
      </div>

      <!-- Портрет: компактные карточки (2 строки, без скролла) -->
      <template v-else-if="!$q.screen.landscape">
        <div
          v-for="contract in filtered"
          :key="contract.id"
          class="contract-card"
          :style="cardBgStyle(contract)"
          @click="$router.push(`/contracts/${contract.id}`)"
        >
          <div class="contract-row1">
            <span class="contract-num">{{ contract.contract_number }}</span>
            <q-badge :color="statusColor(contract.status)" :label="contract.status" style="font-size: 10px; padding: 2px 6px" />
          </div>
          <div class="contract-row2">
            <span class="contract-addr">{{ contract.address || 'Без адреса' }}</span>
            <span v-if="contract.agent_type" class="contract-agent" :style="{ background: agentColor(contract.agent_type) }">{{ contract.agent_type }}</span>
          </div>
        </div>
        <div v-if="filtered.length === 0" class="text-center q-pa-xl text-grey-5">
          <q-icon name="description" size="48px" class="q-mb-sm" />
          <div>{{ search ? 'Ничего не найдено' : 'Нет договоров' }}</div>
        </div>
      </template>

      <!-- Ландшафт: 1 строка на договор -->
      <template v-else>
        <div class="landscape-header">
          <span class="lh-num">№</span>
          <span class="lh-addr">Адрес</span>
          <span class="lh-type">Тип</span>
          <span class="lh-status">Статус</span>
          <span class="lh-agent">Агент</span>
        </div>
        <div
          v-for="contract in filtered"
          :key="contract.id"
          class="contract-row-ls"
          :style="cardBgStyle(contract)"
          @click="$router.push(`/contracts/${contract.id}`)"
        >
          <span class="lh-num ls-num">{{ contract.contract_number }}</span>
          <span class="lh-addr ls-addr">{{ contract.address || '—' }}</span>
          <span class="lh-type ls-meta">{{ contract.project_type === 'Индивидуальный' ? 'Инд.' : contract.project_type === 'Шаблонный' ? 'Шабл.' : (contract.project_type || '—') }}</span>
          <span class="lh-status">
            <q-badge :color="statusColor(contract.status)" :label="contract.status || '—'" style="font-size: 10px; padding: 2px 5px" />
          </span>
          <span class="lh-agent">
            <span v-if="contract.agent_type" class="contract-agent" :style="{ background: agentColor(contract.agent_type) }">{{ contract.agent_type }}</span>
          </span>
        </div>
        <div v-if="filtered.length === 0" class="text-center q-pa-xl text-grey-5">
          <q-icon name="description" size="48px" class="q-mb-sm" />
          <div>{{ search ? 'Ничего не найдено' : 'Нет договоров' }}</div>
        </div>
      </template>
    </q-pull-to-refresh>
    <!-- FAB создания (если есть право) -->
    <q-page-sticky v-if="canCreate" position="bottom-right" :offset="[18, 80]">
      <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="showForm = true" />
    </q-page-sticky>

    <contract-form-dialog v-model="showForm" @saved="loadContracts" />

    <!-- Дашборд внизу -->
    <page-dashboard :items="dashItems" />
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { contractsApi } from 'src/services/api'
import { useReferencesStore } from 'src/stores/references'
import { usePermission } from 'src/composables/usePermission'
import ContractFormDialog from 'src/components/ContractFormDialog.vue'
import PageDashboard from 'src/components/PageDashboard.vue'

const refs = useReferencesStore()
const { can } = usePermission()
const canCreate = computed(() => can('contracts.create'))

const dashItems = computed(() => {
  const all = contracts.value
  const active = all.filter(c => c.status === 'В работе').length
  const done = all.filter(c => c.status?.includes('СДАН')).length
  return [
    { label: 'Всего', value: all.length },
    { label: 'В работе', value: active, color: '#F39C12' },
    { label: 'Сдано', value: done, color: '#27AE60' },
  ]
})
const contracts = ref([])
const loading = ref(false)
const search = ref('')
const showForm = ref(false)
const statusFilter = ref(null)
const typeFilter = ref(null)
const agentFilter = ref(null)
const sortBy = ref(null)
const sortOptions = [
  { label: 'По дате', value: 'date' },
  { label: 'По типу агента', value: 'agent' },
  { label: 'По типу проекта', value: 'project_type' },
  { label: 'По городу', value: 'city' },
  { label: 'По площади', value: 'area' },
]

const statusOpts = [
  { label: 'В работе', value: 'В работе' },
  { label: 'Новый заказ', value: 'Новый заказ' },
  { label: 'СДАН', value: 'СДАН' },
  { label: 'РАСТОРГНУТ', value: 'РАСТОРГНУТ' },
  { label: 'АВТ. НАДЗОР', value: 'АВТОРСКИЙ НАДЗОР' },
]

const typeOpts = [
  { label: 'Индивидуальный', value: 'Индивидуальный' },
  { label: 'Шаблонный', value: 'Шаблонный' },
]

const agentOpts = computed(() => refs.agentNames())

function agentColor(agentName) {
  const agent = refs.agentByName(agentName)
  return agent?.color || '#95A5A6'
}

function cardBgStyle(contract) {
  const s = contract.status || ''
  if (s.includes('СДАН') || s.includes('Сдан')) return { background: '#E8F5E9' }
  if (s.includes('НАДЗОР') || s.includes('надзор')) return { background: '#E3F2FD' }
  if (s.includes('РАСТОРГНУТ') || s.includes('Расторгнут')) return { background: '#FFEBEE' }
  if (s === 'В работе') return { background: '#F5F5F5' }
  if (s === 'Новый заказ' || s === 'Новый') return { background: '#FFFFFF' }
  return {}
}

const filtered = computed(() => {
  let result = contracts.value
  if (search.value) {
    const q = search.value.toLowerCase()
    result = result.filter(c =>
      (c.contract_number || '').toLowerCase().includes(q) ||
      (c.address || '').toLowerCase().includes(q) ||
      (c.city || '').toLowerCase().includes(q),
    )
  }
  if (statusFilter.value) result = result.filter(c => c.status === statusFilter.value)
  if (typeFilter.value) result = result.filter(c => c.project_type === typeFilter.value)
  if (agentFilter.value) result = result.filter(c => c.agent_type === agentFilter.value)
  // Сортировка
  const items = [...result]
  if (sortBy.value === 'date') items.sort((a, b) => new Date(b.contract_date || 0) - new Date(a.contract_date || 0))
  else if (sortBy.value === 'agent') items.sort((a, b) => (a.agent_type || '').localeCompare(b.agent_type || '', 'ru'))
  else if (sortBy.value === 'project_type') items.sort((a, b) => (a.project_type || '').localeCompare(b.project_type || '', 'ru'))
  else if (sortBy.value === 'city') items.sort((a, b) => (a.city || '').localeCompare(b.city || '', 'ru'))
  else if (sortBy.value === 'area') items.sort((a, b) => (b.area || 0) - (a.area || 0))
  return items
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

<style scoped>
/* Ландшафт — шапка + 1-строчные строки */
.landscape-header {
  display: flex;
  align-items: center;
  padding: 4px 10px;
  background: #F5F5F5;
  border: 1px solid #E0E0E0;
  border-radius: 8px 8px 0 0;
  font-size: 10px;
  font-weight: bold;
  color: #888;
  gap: 6px;
}
.contract-row-ls {
  display: flex;
  align-items: center;
  padding: 5px 10px;
  border: 1px solid #E0E0E0;
  border-top: none;
  gap: 6px;
  cursor: pointer;
  background: #fff;
  min-height: 32px;
}
.contract-row-ls:last-of-type { border-radius: 0 0 8px 8px; }
.contract-row-ls:hover { background: #F9F9F9; }
/* колонки ландшафта */
.lh-num   { width: 72px; flex-shrink: 0; font-size: 11px; }
.lh-addr  { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
.lh-type  { width: 44px; flex-shrink: 0; font-size: 11px; }
.lh-status { width: 100px; flex-shrink: 0; }
.lh-agent { width: 80px; flex-shrink: 0; }
/* значения в строках */
.ls-num   { font-weight: bold; color: #333; }
.ls-addr  { color: #444; }
.ls-meta  { color: #888; }

/* Портретные карточки договоров */
.contract-card {
  border: 1px solid #E0E0E0;
  border-radius: 8px;
  margin-bottom: 6px;
  padding: 8px 12px;
  cursor: pointer;
  background: #fff;
}
.contract-card:active { background: #f5f5f5; }
.contract-row1 {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.contract-num {
  font-size: 12px;
  font-weight: bold;
  color: #333;
}
.contract-row2 {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.contract-addr {
  font-size: 12px;
  color: #555;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.contract-agent {
  color: #fff;
  font-size: 10px;
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
}
</style>
