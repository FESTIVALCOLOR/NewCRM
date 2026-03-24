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
        <template v-slot:prepend>
          <q-icon name="search" />
        </template>
        <template v-slot:append v-if="clientsStore.search">
          <q-icon name="close" class="cursor-pointer" @click="clearSearch" />
        </template>
      </q-input>

      <!-- Фильтры -->
      <div class="row q-col-gutter-xs q-mb-sm">
        <div class="col-6">
          <q-select v-model="clientType" :options="['Все', 'Физическое лицо', 'Юридическое лицо']" label="Тип" outlined dense @update:model-value="applyFilters" />
        </div>
        <div class="col-6">
          <q-select v-model="sortBy" :options="sortOpts" label="Сортировка" outlined dense emit-value map-options @update:model-value="applyFilters" />
        </div>
      </div>

      <!-- Счётчик -->
      <div class="text-caption" style="color: #888" v-if="!clientsStore.loading">
        Найдено: {{ clientsStore.filteredItems.length }}
        <span v-if="clientsStore.totalCount"> из {{ clientsStore.totalCount }}</span>
      </div>

      <!-- Загрузка -->
      <div v-if="clientsStore.loading">
        <q-card class="is-card q-mb-sm" v-for="n in 5" :key="n">
          <q-item>
            <q-item-section avatar><q-skeleton type="circle" size="40px" /></q-item-section>
            <q-item-section>
              <q-skeleton type="text" width="60%" />
              <q-skeleton type="text" width="40%" />
            </q-item-section>
          </q-item>
        </q-card>
      </div>

      <!-- Список клиентов -->
      <q-card class="is-card" v-else-if="clientsStore.filteredItems.length > 0">
        <q-list separator>
          <q-item
            v-for="client in clientsStore.filteredItems"
            :key="client.id"
            clickable
            v-ripple
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
                {{ client.full_name }}
              </q-item-label>
              <q-item-label caption v-if="client.organization_name">
                {{ client.organization_name }}
              </q-item-label>
              <q-item-label caption v-if="client.phone">
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
    <q-page-sticky v-if="canCreate" position="bottom-right" :offset="[18, 70]">
      <q-btn fab icon="add" style="background: #ffd93c; color: #333" @click="showForm = true" />
    </q-page-sticky>

    <!-- Форма создания/редактирования -->
    <client-form-dialog v-model="showForm" @saved="onSaved" />
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePermission } from 'src/composables/usePermission'
import ClientFormDialog from 'src/components/ClientFormDialog.vue'
import { useRouter } from 'vue-router'
import { useClientsStore } from 'src/stores/clients'

const router = useRouter()
const clientsStore = useClientsStore()
const { can } = usePermission()
const canCreate = computed(() => can('clients.create'))
const showForm = ref(false)
const clientType = ref('Все')
const sortBy = ref('name')

const sortOpts = [
  { label: 'По имени', value: 'name' },
  { label: 'По дате', value: 'date' }
]

function applyFilters() {
  // Фильтрация через computed в store
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
