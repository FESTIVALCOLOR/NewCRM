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

      <!-- Таблица договоров -->
      <template v-else>
        <q-table
          :rows="filtered"
          :columns="tableColumns"
          row-key="id"
          flat
          dense
          :rows-per-page-options="[0]"
          hide-pagination
          class="contracts-table"
          :table-style="{ fontSize: '12px' }"
          @row-click="(_, row) => $router.push(`/contracts/${row.id}`)"
        >
          <template #body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="statusColor(props.value)" :label="props.value" style="font-size: 10px; padding: 3px 6px" />
            </q-td>
          </template>
          <template #body-cell-agent_type="props">
            <q-td :props="props">
              <span v-if="props.value" :style="{ background: agentColor(props.value), color: 'white', fontSize: '10px', padding: '2px 6px', borderRadius: '4px', whiteSpace: 'nowrap' }">{{ props.value }}</span>
            </q-td>
          </template>
          <template #body="props">
            <q-tr :props="props" :style="cardBgStyle(props.row)" class="cursor-pointer" @click="$router.push(`/contracts/${props.row.id}`)">
              <q-td v-for="col in props.cols" :key="col.name" :props="props">
                <template v-if="col.name === 'status'">
                  <q-badge :color="statusColor(props.row.status)" :label="props.row.status || '—'" style="font-size: 10px; padding: 3px 6px" />
                </template>
                <template v-else-if="col.name === 'agent_type'">
                  <span v-if="props.row.agent_type" :style="{ background: agentColor(props.row.agent_type), color: 'white', fontSize: '10px', padding: '2px 6px', borderRadius: '4px', whiteSpace: 'nowrap' }">{{ props.row.agent_type }}</span>
                </template>
                <template v-else>
                  {{ col.value }}
                </template>
              </q-td>
            </q-tr>
          </template>
          <template #no-data>
            <div class="text-center q-pa-xl text-grey-5" style="width: 100%">
              <q-icon name="description" size="48px" class="q-mb-sm" />
              <div>{{ search ? 'Ничего не найдено' : 'Нет договоров' }}</div>
            </div>
          </template>
        </q-table>
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
const tableColumns = [
  { name: 'contract_number', label: '№', field: 'contract_number', sortable: true, align: 'left', style: 'min-width: 60px; max-width: 80px' },
  { name: 'address', label: 'Адрес', field: 'address', sortable: true, align: 'left', style: 'min-width: 120px' },
  { name: 'project_type', label: 'Тип', field: row => row.project_type ? (row.project_type === 'Индивидуальный' ? 'Инд.' : row.project_type === 'Шаблонный' ? 'Шабл.' : row.project_type) : '—', sortable: true, align: 'left', style: 'min-width: 50px; max-width: 70px' },
  { name: 'status', label: 'Статус', field: 'status', sortable: true, align: 'left', style: 'min-width: 90px' },
  { name: 'agent_type', label: 'Агент', field: 'agent_type', sortable: true, align: 'left', style: 'min-width: 70px' },
]

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
.contracts-table {
  border: 1px solid #E0E0E0;
  border-radius: 8px;
  overflow: hidden;
}
.contracts-table :deep(thead tr th) {
  font-size: 11px;
  font-weight: bold;
  color: #666;
  background: #F5F5F5;
  padding: 6px 8px;
}
.contracts-table :deep(tbody tr td) {
  padding: 6px 8px;
  font-size: 12px;
}
.contracts-table :deep(tbody tr:hover) {
  background: #F9F9F9 !important;
}
</style>
