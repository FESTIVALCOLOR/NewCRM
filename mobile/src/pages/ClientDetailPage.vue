<template>
  <q-page padding>
    <template v-if="client">
      <!-- Шапка -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="text-center">
          <q-avatar size="56px" :color="client.organization_name ? 'blue-2' : 'green-2'" :text-color="client.organization_name ? 'blue-8' : 'green-8'" class="q-mb-sm">
            <q-icon :name="client.organization_name ? 'business' : 'person'" size="28px" />
          </q-avatar>
          <div class="text-h6 text-weight-bold" style="color: #333">{{ client.full_name }}</div>
          <div class="text-body2" style="color: #888" v-if="client.organization_name">{{ client.organization_name }}</div>
        </q-card-section>
      </q-card>

      <!-- Контакты: кнопки СЛЕВА вертикально, данные справа -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">Контакты</div>
        </q-card-section>
        <q-list>
          <!-- Телефон -->
          <q-item>
            <q-item-section avatar>
              <q-btn flat round dense :icon="client.phone ? 'phone' : 'phone_disabled'" :style="{ color: client.phone ? '#333' : '#ccc' }" @click="client.phone && callPhone(client.phone)" />
            </q-item-section>
            <q-item-section>
              <q-item-label caption>Телефон</q-item-label>
              <q-item-label :style="{ color: client.phone ? '#333' : '#bbb' }">{{ client.phone || 'Не указан' }}</q-item-label>
            </q-item-section>
          </q-item>
          <!-- Email -->
          <q-item>
            <q-item-section avatar>
              <q-btn flat round dense :icon="client.email ? 'email' : 'mail_outline'" :style="{ color: client.email ? '#333' : '#ccc' }" @click="client.email && sendEmail(client.email)" />
            </q-item-section>
            <q-item-section>
              <q-item-label caption>Email</q-item-label>
              <q-item-label :style="{ color: client.email ? '#333' : '#bbb' }">{{ client.email || 'Не указан' }}</q-item-label>
            </q-item-section>
          </q-item>
          <!-- Telegram -->
          <q-item>
            <q-item-section avatar>
              <q-btn flat round dense icon="send" :style="{ color: telegramLink ? '#333' : '#ccc' }" @click="telegramLink && openLink(telegramLink)" />
            </q-item-section>
            <q-item-section>
              <q-item-label caption>Telegram</q-item-label>
              <q-item-label :style="{ color: client.telegram_account ? '#333' : '#bbb' }">{{ client.telegram_account || 'Не указан' }}</q-item-label>
            </q-item-section>
          </q-item>
          <!-- Адрес / Геоточка -->
          <q-item>
            <q-item-section avatar>
              <q-btn flat round dense :icon="client.registration_address ? 'location_on' : 'location_off'" :style="{ color: client.registration_address ? '#333' : '#ccc' }" @click="client.registration_address && openMap(client.registration_address)" />
            </q-item-section>
            <q-item-section>
              <q-item-label caption>Адрес</q-item-label>
              <q-item-label :style="{ color: client.registration_address ? '#333' : '#bbb' }">{{ client.registration_address || 'Не указан' }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Реквизиты (юр. лицо) -->
      <q-card class="is-card q-mb-md" v-if="client.inn || client.ogrn">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">Реквизиты</div>
        </q-card-section>
        <q-list dense>
          <q-item v-if="client.inn"><q-item-section><q-item-label caption>ИНН</q-item-label><q-item-label>{{ client.inn }}</q-item-label></q-item-section></q-item>
          <q-item v-if="client.ogrn"><q-item-section><q-item-label caption>ОГРН</q-item-label><q-item-label>{{ client.ogrn }}</q-item-label></q-item-section></q-item>
          <q-item v-if="client.account_details"><q-item-section><q-item-label caption>Банковские реквизиты</q-item-label><q-item-label>{{ client.account_details }}</q-item-label></q-item-section></q-item>
        </q-list>
      </q-card>

      <!-- Договоры клиента -->
      <q-card class="is-card">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">
            Договоры <q-badge v-if="clientsStore.clientContracts.length" :label="clientsStore.clientContracts.length" class="q-ml-xs" />
          </div>
        </q-card-section>
        <q-list v-if="clientsStore.clientContracts.length > 0" separator>
          <q-item v-for="c in clientsStore.clientContracts" :key="c.id" clickable v-ripple @click="$router.push(`/contracts/${c.id}`)">
            <q-item-section>
              <q-item-label class="text-weight-medium">{{ c.contract_number }}</q-item-label>
              <q-item-label caption>{{ c.address }}</q-item-label>
              <q-item-label caption>{{ c.project_type }} — {{ c.area }} м²</q-item-label>
            </q-item-section>
            <q-item-section side style="min-width: 100px">
              <div class="column items-end q-gutter-xs">
                <q-badge :color="contractStatusColor(c.status)" :label="c.status" style="min-width: 90px; justify-content: center; padding: 4px 8px; font-size: 11px" />
                <q-badge v-if="c.agent_type" text-color="white" :style="{ background: agentColor(c.agent_type), minWidth: '90px', justifyContent: 'center', padding: '4px 8px', fontSize: '11px' }" :label="c.agent_type" />
              </div>
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section v-else class="text-center" style="color: #999">Нет договоров</q-card-section>
      </q-card>

      <!-- FAB редактирования -->
      <q-page-sticky position="bottom-right" :offset="[18, 18]">
        <q-btn fab icon="edit" style="background: #ffd93c; color: #333" @click="showEdit = true" />
      </q-page-sticky>

      <client-form-dialog v-model="showEdit" :client="client" @saved="reloadClient" />
    </template>

    <div v-else class="text-center q-pa-xl" style="color: #999">
      <q-spinner v-if="!loaded" size="40px" color="accent" />
      <template v-else>
        <q-icon name="person_off" size="48px" class="q-mb-sm" /><div>Клиент не найден</div>
      </template>
    </div>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useClientsStore } from 'src/stores/clients'
import { useReferencesStore } from 'src/stores/references'
import ClientFormDialog from 'src/components/ClientFormDialog.vue'

const route = useRoute()
const clientsStore = useClientsStore()
const refs = useReferencesStore()
const loaded = ref(false)
const showEdit = ref(false)

const client = computed(() => clientsStore.selectedClient)

const telegramLink = computed(() => {
  const tg = client.value?.telegram_account
  if (!tg) return null
  const clean = tg.replace('@', '').trim()
  if (!clean) return null
  if (/^\+?\d+$/.test(clean)) return `https://t.me/+${clean.replace('+', '')}`
  return `https://t.me/${clean}`
})

function callPhone(phone) { window.location.href = `tel:${phone.replace(/[^\d+]/g, '')}` }
function sendEmail(email) { window.location.href = `mailto:${email}` }
function openLink(url) { if (url) window.open(url, '_blank') }
function openMap(address) { window.open(`https://yandex.ru/maps/?text=${encodeURIComponent(address)}`, '_blank') }
function agentColor(name) { return refs.agentByName(name)?.color || '#95A5A6' }
function contractStatusColor(status) {
  if (!status) return 'grey'
  if (status === 'В работе') return 'orange'
  if (status.includes('СДАН') || status.includes('Сдан')) return 'positive'
  if (status.includes('РАСТОРГНУТ')) return 'negative'
  if (status.includes('НАДЗОР')) return 'purple'
  return 'blue'
}

async function reloadClient() {
  const clientId = route.params.id
  if (clientId) {
    await clientsStore.loadClient(clientId)
    await clientsStore.loadClientContracts(clientId)
  }
}

onMounted(async () => {
  const clientId = route.params.id
  if (clientId) {
    await Promise.all([clientsStore.loadClient(clientId), clientsStore.loadClientContracts(clientId)])
  }
  loaded.value = true
})
</script>
