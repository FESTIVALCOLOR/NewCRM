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

      <!-- Счётчик -->
      <div class="text-caption text-grey-7 q-mb-sm" v-if="!clientsStore.loading">
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

    <!-- FAB создания клиента -->
    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-btn fab icon="person_add" color="primary" @click="showForm = true" />
    </q-page-sticky>

    <!-- Форма создания/редактирования -->
    <client-form-dialog v-model="showForm" @saved="onSaved" />
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import ClientFormDialog from 'src/components/ClientFormDialog.vue'
import { useRouter } from 'vue-router'
import { useClientsStore } from 'src/stores/clients'

const router = useRouter()
const clientsStore = useClientsStore()
const showForm = ref(false)

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
