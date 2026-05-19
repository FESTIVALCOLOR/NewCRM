<template>
  <q-page padding>
    <q-pull-to-refresh @refresh="onRefresh">
      <!-- Поиск -->
      <q-input
        v-model="clientsStore.search"
        placeholder="Поиск клиентов..."
        outlined
        dense
        class="q-mb-md crm-search-input"
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
            class="crm-filter-select"
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
            class="crm-filter-select"
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
      <template v-if="!clientsStore.loading && !($q.screen.width > $q.screen.height)">
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

      <!-- Ландшафт: 1 строка на клиента -->
      <template v-else-if="!clientsStore.loading && ($q.screen.width > $q.screen.height)">
        <div class="landscape-header">
          <span class="clh-name">Имя / Организация</span>
          <span class="clh-phone">Телефон</span>
          <span class="clh-email">Email</span>
          <span class="clh-type">Тип</span>
        </div>
        <div
          v-for="client in displayedClients"
          :key="client.id"
          class="client-row-ls"
          @click="openClient(client.id)"
        >
          <span class="clh-name cls-name">
            <q-icon :name="client.organization_name ? 'business' : 'person'" :color="client.organization_name ? 'blue-6' : 'green-6'" size="14px" style="margin-right:4px;flex-shrink:0" />
            {{ clientDisplayName(client) }}
          </span>
          <span class="clh-phone cls-meta">{{ client.phone || '—' }}</span>
          <span class="clh-email cls-meta">{{ client.email || '—' }}</span>
          <span class="clh-type">
            <q-badge
              :color="client.organization_name ? 'blue-3' : 'green-3'"
              :text-color="client.organization_name ? 'blue-9' : 'green-9'"
              :label="client.organization_name ? 'Юр.' : 'Физ.'"
              dense
              style="font-size: 9px"
            />
          </span>
        </div>
        <div v-if="displayedClients.length === 0" class="text-center q-pa-xl text-grey-5">
          <q-icon name="people_outline" size="48px" class="q-mb-sm" />
          <div>{{ clientsStore.search ? 'Ничего не найдено' : 'Нет клиентов' }}</div>
        </div>
      </template>
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
.client-row-ls {
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
.client-row-ls:last-of-type { border-radius: 0 0 8px 8px; }
.client-row-ls:hover { background: #F9F9F9; }
/* колонки ландшафта клиентов */
.clh-name  { flex: 1; min-width: 0; display: flex; align-items: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.clh-phone { width: 110px; flex-shrink: 0; font-size: 11px; }
.clh-email { width: 160px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
.clh-type  { width: 46px; flex-shrink: 0; }
/* значения */
.cls-name  { font-size: 12px; font-weight: 500; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cls-meta  { color: #666; }

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
/* Радиус поиска и фильтров = радиус таблицы (8px) */
.crm-search-input :deep(.q-field__control) { border-radius: 8px; }
.crm-filter-select :deep(.q-field__control) { border-radius: 8px !important; height: 32px !important; min-height: 32px !important; }
.crm-filter-select :deep(.q-field--dense .q-field__control) { height: 32px !important; min-height: 32px !important; }
.crm-filter-select :deep(.q-field__control-container) { min-width: 0; overflow: hidden; }
.crm-filter-select :deep(.q-field__native) { padding-top: 0 !important; padding-bottom: 0 !important; min-height: 30px !important; min-width: 0; overflow: hidden; }
.crm-filter-select :deep(.q-field__native span) { overflow: hidden !important; text-overflow: ellipsis !important; white-space: nowrap !important; display: block !important; }
.crm-filter-select :deep(.q-field__label) { top: 7px !important; font-size: 11px; }
</style>
