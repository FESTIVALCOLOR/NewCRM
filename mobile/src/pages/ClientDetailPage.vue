<template>
  <q-page padding>
    <template v-if="client">
      <!-- Шапка -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="text-center">
          <q-avatar
            size="64px"
            :color="client.organization_name ? 'blue-2' : 'green-2'"
            :text-color="client.organization_name ? 'blue-8' : 'green-8'"
            class="q-mb-sm"
          >
            <q-icon :name="client.organization_name ? 'business' : 'person'" size="32px" />
          </q-avatar>
          <div class="text-h6 text-weight-bold">{{ client.full_name }}</div>
          <div class="text-body2 text-grey-7" v-if="client.organization_name">
            {{ client.organization_name }}
          </div>
        </q-card-section>
      </q-card>

      <!-- Контакты -->
      <q-card class="is-card q-mb-md">
        <q-list>
          <q-item v-if="client.phone" clickable @click="callPhone(client.phone)">
            <q-item-section avatar><q-icon name="phone" color="positive" /></q-item-section>
            <q-item-section>
              <q-item-label caption>Телефон</q-item-label>
              <q-item-label>{{ client.phone }}</q-item-label>
            </q-item-section>
            <q-item-section side><q-icon name="call" color="positive" /></q-item-section>
          </q-item>

          <q-item v-if="client.email" clickable @click="sendEmail(client.email)">
            <q-item-section avatar><q-icon name="email" color="blue" /></q-item-section>
            <q-item-section>
              <q-item-label caption>Email</q-item-label>
              <q-item-label>{{ client.email }}</q-item-label>
            </q-item-section>
            <q-item-section side><q-icon name="send" color="blue" /></q-item-section>
          </q-item>

          <q-item v-if="client.registration_address">
            <q-item-section avatar><q-icon name="location_on" color="grey-7" /></q-item-section>
            <q-item-section>
              <q-item-label caption>Адрес</q-item-label>
              <q-item-label>{{ client.registration_address }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Реквизиты (юр. лицо) -->
      <q-card class="is-card q-mb-md" v-if="client.inn || client.ogrn">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">Реквизиты</div>
        </q-card-section>
        <q-list dense>
          <q-item v-if="client.inn">
            <q-item-section>
              <q-item-label caption>ИНН</q-item-label>
              <q-item-label>{{ client.inn }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item v-if="client.ogrn">
            <q-item-section>
              <q-item-label caption>ОГРН</q-item-label>
              <q-item-label>{{ client.ogrn }}</q-item-label>
            </q-item-section>
          </q-item>
          <q-item v-if="client.account_details">
            <q-item-section>
              <q-item-label caption>Банковские реквизиты</q-item-label>
              <q-item-label>{{ client.account_details }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Договоры клиента -->
      <q-card class="is-card">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold">
            Договоры
            <q-badge v-if="clientsStore.clientContracts.length" :label="clientsStore.clientContracts.length" class="q-ml-xs" />
          </div>
        </q-card-section>

        <q-list v-if="clientsStore.clientContracts.length > 0" separator>
          <q-item
            v-for="contract in clientsStore.clientContracts"
            :key="contract.id"
            clickable
            v-ripple
          >
            <q-item-section>
              <q-item-label class="text-weight-medium">{{ contract.contract_number }}</q-item-label>
              <q-item-label caption>{{ contract.address }}</q-item-label>
              <q-item-label caption>
                {{ contract.project_type }} — {{ contract.area }} м²
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-badge :color="contractStatusColor(contract.status)" :label="contract.status" dense />
            </q-item-section>
          </q-item>
        </q-list>

        <q-card-section v-else class="text-center text-grey-5">
          Нет договоров
        </q-card-section>
      </q-card>
    </template>

    <!-- Не найден -->
    <div v-else class="text-center q-pa-xl text-grey-5">
      <q-spinner v-if="!loaded" size="40px" color="primary" />
      <template v-else>
        <q-icon name="person_off" size="48px" class="q-mb-sm" />
        <div>Клиент не найден</div>
      </template>
    </div>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useClientsStore } from 'src/stores/clients'

const route = useRoute()
const clientsStore = useClientsStore()
const loaded = ref(false)

const client = computed(() => clientsStore.selectedClient)

function callPhone(phone) {
  window.location.href = `tel:${phone.replace(/[^\d+]/g, '')}`
}

function sendEmail(email) {
  window.location.href = `mailto:${email}`
}

function contractStatusColor(status) {
  if (!status) return 'grey'
  if (status === 'В работе') return 'orange'
  if (status.includes('СДАН') || status.includes('Сдан')) return 'positive'
  if (status.includes('РАСТОРГНУТ')) return 'negative'
  return 'blue'
}

onMounted(async () => {
  const clientId = route.params.id
  if (clientId) {
    await Promise.all([
      clientsStore.loadClient(clientId),
      clientsStore.loadClientContracts(clientId)
    ])
  }
  loaded.value = true
})
</script>
