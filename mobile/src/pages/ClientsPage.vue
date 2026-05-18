<template>
  <q-page padding>
    <q-pull-to-refresh @refresh="onRefresh">
      <!-- Поиск -->
      <q-input
        v-model="clientsStore.search"
        placeholder="Поиск клиентов..."
        outlined
        dense
        rounded
        class="q-mb-md"
        debounce="300"
        @update:model-value="onSearch"
      >
        <template #prepend>
          <q-icon name="search" />
        </template>
        <template v-if="clientsStore.search" #append>
          <q-icon name="close" class="cursor-pointer" @click="clearSearch" />
        </template>
      </q-input>

      <!-- Фильтры -->
      <div class="row q-col-gutter-xs q-mb-sm">
        <div class="col-6">
          <q-select
            v-model="clientType"
            :options="['Все', 'Физическое лицо', 'Юридическое лицо']"
            label="Тип"
            outlined
            dense
            @update:model-value="applyFilters"
          />
        </div>
        <div class="col-6">
          <q-select
            v-model="sortBy"
            :options="sortOpts"
            label="Сортировка"
            outlined
            dense
            emit-value
            map-options
            @update:model-value="applyFilters"
          />
        </div>
      </div>

      <!-- Счётчик -->
      <div v-if="!clientsStore.loading" class="text-caption" style="color: #888">
        Найдено: {{ displayedClients.length }}
        <span v-if="clientsStore.totalCount"> из {{ clientsStore.totalCount }}</span>
      </div>

      <!-- Загрузка -->
      <div v-if="clientsStore.loading">
        <q-card v-for="n in 5" :key="n" class="is-card q-mb-sm">
          <q-item>
            <q-item-section avatar>
              <q-skeleton type="circle" size="40px" />
            </q-item-section>
            <q-item-section>
              <q-skeleton type="text" width="60%" />
              <q-skeleton type="text" width="40%" />
            </q-item-section>
          </q-item>
        </q-card>
      </div>

      <!-- Портрет: компактные карточки (2 строки, без скролла) -->
      <template v-if="!clientsStore.loading && !$q.screen.landscape">
        <div
          v-for="client in displayedClients"
          :key="client.id"
          class="client-card"
          @click="openClient(client.id)"
        >
          <div class="client-row1">
            <q-icon
              :name="client.organization_name ? 'business' : 'person'"
              :color="client.organization_name ? 'blue-6' : 'green-6'"
              size="16px"
              class="q-mr-xs"
              style="flex-shrink:0"
            />
            <span class="client-name">{{ clientDisplayName(client) }}</span>
            <q-badge
              :color="client.organization_name ? 'blue-3' : 'green-3'"
              :text-color="client.organization_name ? 'blue-9' : 'green-9'"
              :label="client.organization_name ? 'Юр.' : 'Физ.'"
              dense
              style="font-size: 9px; flex-shrink: 0"
            />
          </div>
          <div class="client-row2">
            <span class="client-phone">{{ client.phone || '—' }}</span>
            <span v-if="client.email" class="client-email">{{ client.email }}</span>
          </div>
        </div>
        <div v-if="displayedClients.length === 0" class="text-center q-pa-xl text-grey-5">
          <q-icon name="people_outline" size="48px" class="q-mb-sm" />
          <div>{{ clientsStore.search ? 'Ничего не найдено' : 'Нет клиентов' }}</div>
        </div>
      </template>

      <!-- Ландшафт: таблица -->
      <q-table
        v-else-if="!clientsStore.loading && $q.screen.landscape"
        :rows="displayedClients"
        :columns="clientTableColumns"
        row-key="id"
        flat
        dense
        :rows-per-page-options="[0]"
        hide-pagination
        class="clients-table"
        :table-style="{ fontSize: '12px' }"
      >
        <template #body="props">
          <q-tr :props="props" class="cursor-pointer" @click="openClient(props.row.id)">
            <q-td key="name" :props="props">
              <div class="row items-center no-wrap">
                <q-icon :name="props.row.organization_name ? 'business' : 'person'" :color="props.row.organization_name ? 'blue-6' : 'green-6'" size="16px" class="q-mr-xs" />
                <span>{{ clientDisplayName(props.row) }}</span>
              </div>
            </q-td>
            <q-td key="phone" :props="props">
              {{ props.row.phone || '—' }}
            </q-td>
            <q-td key="email" :props="props" style="max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
              {{ props.row.email || '—' }}
            </q-td>
            <q-td key="type" :props="props">
              <q-badge
                :color="props.row.organization_name ? 'blue-3' : 'green-3'"
                :text-color="props.row.organization_name ? 'blue-9' : 'green-9'"
                :label="props.row.organization_name ? 'Юр.' : 'Физ.'"
                dense
                style="font-size: 9px"
              />
            </q-td>
          </q-tr>
        </template>
        <template #no-data>
          <div class="text-center q-pa-xl text-grey-5" style="width: 100%">
            <q-icon name="people_outline" size="48px" class="q-mb-sm" />
            <div>{{ clientsStore.search ? 'Ничего не найдено' : 'Нет клиентов' }}</div>
          </div>
        </template>
      </q-table>
    </q-pull-to-refresh>

    <!-- Круглая жёлтая кнопка добавления (если есть право) -->
    <q-page-sticky v-if="canCreate" position="bottom-right" :offset="[18, 80]">
      <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="showForm = true" />
    </q-page-sticky>

    <!-- Форма создания/редактирования -->
    <client-form-dialog v-model="showForm" @saved="onSaved" />

    <!-- Дашборд внизу -->
    <page-dashboard :items="dashItems" />
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePermission } from 'src/composables/usePermission'
import ClientFormDialog from 'src/components/ClientFormDialog.vue'
import PageDashboard from 'src/components/PageDashboard.vue'
import { useRouter } from 'vue-router'
import { useClientsStore } from 'src/stores/clients'

const router = useRouter()
const clientsStore = useClientsStore()
const { can } = usePermission()
const canCreate = computed(() => can('clients.create'))
const showForm = ref(false)

const dashItems = computed(() => [
  { label: 'Всего клиентов', value: clientsStore.items?.length || 0, color: '#333' },
  { label: 'Физ. лица', value: clientsStore.items?.filter(c => !c.organization_name).length || 0, color: '#27AE60' },
  { label: 'Юр. лица', value: clientsStore.items?.filter(c => c.organization_name).length || 0, color: '#3498DB' },
])
const clientTableColumns = [
  { name: 'name', label: 'Имя / Организация', field: row => clientDisplayName(row), sortable: true, align: 'left', style: 'min-width: 130px' },
  { name: 'phone', label: 'Телефон', field: 'phone', align: 'left', style: 'min-width: 100px' },
  { name: 'email', label: 'Email', field: 'email', align: 'left', style: 'min-width: 80px; max-width: 130px' },
  { name: 'type', label: 'Тип', field: row => row.organization_name ? 'Юр.' : 'Физ.', align: 'left', style: 'min-width: 45px; max-width: 60px' },
]

const clientType = ref('Все')
const sortBy = ref('name')

const searchQuery = ref('')

const sortOpts = [
  { label: 'По имени', value: 'name' },
  { label: 'По дате', value: 'date' },
]

const displayedClients = computed(() => {
  let items = [...(clientsStore.items || clientsStore.filteredItems || [])]

  // Фильтр по типу
  if (clientType.value && clientType.value !== 'Все') {
    if (clientType.value === 'Юридическое лицо') {
      items = items.filter(c => c.organization_name && c.organization_name.trim())
    } else {
      items = items.filter(c => !c.organization_name || !c.organization_name.trim())
    }
  }

  // Фильтр по поиску
  if (searchQuery.value && searchQuery.value.length >= 2) {
    const q = searchQuery.value.toLowerCase()
    items = items.filter(c =>
      (c.full_name || '').toLowerCase().includes(q) ||
      (c.phone || '').toLowerCase().includes(q) ||
      (c.email || '').toLowerCase().includes(q) ||
      (c.organization_name || '').toLowerCase().includes(q),
    )
  }

  // Сортировка
  if (sortBy.value === 'name') {
    items.sort((a, b) => (a.full_name || '').localeCompare(b.full_name || '', 'ru'))
  } else if (sortBy.value === 'date') {
    items.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
  }

  return items
})

function applyFilters() {
  // Фильтрация реализована через computed displayedClients
}

// Отображение имени клиента: ИП Иванов / ООО "Ромашка" / Просто ФИО
function clientDisplayName(c) {
  const orgType = c.organization_type || ''
  if (orgType === 'ИП') return `ИП ${c.full_name}`
  if (orgType && c.organization_name) return `${orgType} «${c.organization_name}»`
  if (c.organization_name) return c.organization_name
  return c.full_name
}

function openClient(clientId) {
  router.push(`/clients/${clientId}`)
}

function onSearch() {
  clientsStore.loadClients()
}

function clearSearch() {
  clientsStore.search = ''
  clientsStore.loadClients()
}

function onRefresh(done) {
  clientsStore.loadClients().finally(done)
}

function onSaved() {
  clientsStore.loadClients()
}

onMounted(() => {
  if (clientsStore.items.length === 0) {
    clientsStore.loadClients()
  }
})
</script>

<style scoped>
.clients-table {
  border: 1px solid #E0E0E0;
  border-radius: 8px;
  overflow: hidden;
}
.clients-table :deep(thead tr th) {
  font-size: 11px;
  font-weight: bold;
  color: #666;
  background: #F5F5F5;
  padding: 6px 8px;
}
.clients-table :deep(tbody tr td) {
  padding: 6px 8px;
  font-size: 12px;
}
.clients-table :deep(tbody tr:hover) {
  background: #F9F9F9 !important;
}

/* Портретные карточки клиентов */
.client-card {
  border: 1px solid #E0E0E0;
  border-radius: 8px;
  margin-bottom: 6px;
  padding: 8px 12px;
  cursor: pointer;
  background: #fff;
}
.client-card:active { background: #f5f5f5; }
.client-row1 {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 3px;
}
.client-name {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.client-row2 {
  display: flex;
  gap: 12px;
  padding-left: 22px;
}
.client-phone {
  font-size: 11px;
  color: #666;
}
.client-email {
  font-size: 11px;
  color: #888;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 160px;
}
</style>
