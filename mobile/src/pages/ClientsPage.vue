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

      <!-- Список клиентов -->
      <q-card v-else-if="displayedClients.length > 0" class="is-card">
        <q-list separator>
          <q-item
            v-for="client in displayedClients"
            :key="client.id"
            v-ripple
            clickable
            @click="openClient(client.id)"
          >
            <q-item-section avatar>
              <q-avatar
                :color="client.client_type === 'ООО' || client.organization_name ? 'blue-2' : 'green-2'"
                :text-color="client.client_type === 'ООО' || client.organization_name ? 'blue-8' : 'green-8'"
                size="40px"
              >
                <q-icon :name="client.organization_name ? 'business' : 'person'" />
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-medium">
                {{ clientDisplayName(client) }}
              </q-item-label>
              <q-item-label v-if="client.organization_name && client.organization_type !== 'ИП'" caption>
                {{ client.full_name }}
              </q-item-label>
              <q-item-label v-if="client.phone" caption>
                {{ client.phone }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-icon name="chevron_right" color="grey-5" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Пустой список -->
      <div v-else class="text-center q-pa-xl text-grey-5">
        <q-icon name="people_outline" size="48px" class="q-mb-sm" />
        <div>{{ clientsStore.search ? 'Ничего не найдено' : 'Нет клиентов' }}</div>
      </div>
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
