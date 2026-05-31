<template>
  <q-page>
    <!-- Поиск -->
    <div class="q-px-md q-pt-md q-pb-sm">
      <q-input
        v-model="searchText"
        outlined
        dense
        placeholder="Поиск по адресу объекта…"
        clearable
      >
        <template #prepend>
          <q-icon name="search" />
        </template>
      </q-input>
    </div>

    <!-- Загрузка -->
    <div v-if="loading" class="q-pa-lg text-center">
      <q-spinner size="32px" color="primary" />
    </div>

    <!-- Список чатов -->
    <q-list v-else-if="filteredChats.length" separator>
      <q-item
        v-for="chat in filteredChats"
        :key="chat.id"
        v-ripple
        clickable
        @click="openChat(chat)"
      >
        <q-item-section avatar>
          <q-avatar color="green-2" text-color="green-9" icon="support_agent" size="42px" />
        </q-item-section>

        <q-item-section>
          <q-item-label class="text-weight-medium">
            {{ chat.title || `Чат #${chat.id}` }}
          </q-item-label>
          <q-item-label v-if="chat.last_message" caption lines="1">
            {{ chat.last_message }}
          </q-item-label>
          <q-item-label v-if="chat.member_count" caption>
            {{ chat.member_count }} уч.
            <span v-if="chat.guest_count">, {{ chat.guest_count }} клиент(ов)</span>
          </q-item-label>
        </q-item-section>

        <q-item-section side>
          <div class="row items-center no-wrap" style="gap: 4px">
            <q-btn
              v-if="canManage"
              flat
              round
              dense
              size="xs"
              icon="manage_accounts"
              color="grey-6"
              @click.stop="openAccessDialog(chat)"
            >
              <q-tooltip>Доступ клиента</q-tooltip>
            </q-btn>
            <q-badge
              v-if="chat.unread_count"
              color="negative"
              :label="chat.unread_count"
              rounded
            />
          </div>
        </q-item-section>
      </q-item>
    </q-list>

    <!-- Пусто -->
    <div v-else class="q-pa-xl text-center text-grey">
      <q-icon name="support_agent" size="48px" class="q-mb-md" />
      <div class="text-h6">
        Нет чатов с клиентами
      </div>
      <div class="text-body2 q-mt-xs">
        Чаты создаются в CRM-карточке → вкладка «Чат с клиентом»
      </div>
    </div>

    <!-- Диалог: Доступ клиента -->
    <q-dialog v-model="showAccessDialog">
      <q-card style="min-width: 340px; max-width: 460px; width: 100%">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            Доступ клиента
          </div>
          <q-space />
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
          />
        </q-card-section>

        <!-- Секция: Отправить приглашение на email -->
        <q-card-section>
          <div class="text-subtitle2 q-mb-xs">
            <q-icon name="email" size="16px" class="q-mr-xs" />
            Пригласить клиента
          </div>
          <div class="text-caption text-grey-7 q-mb-sm">
            Клиент получит письмо с инструкцией и ссылкой на чат проекта
          </div>
          <q-btn
            v-if="activeCrmCardId"
            color="primary"
            icon="send"
            label="Отправить приглашение на email"
            :loading="sendingInvite"
            unelevated
            class="full-width"
            @click="sendEmailInvite"
          />
          <div v-else class="text-caption text-orange-8 q-pa-sm bg-orange-1 rounded-borders">
            <q-icon name="warning" size="14px" class="q-mr-xs" />
            Чат не привязан к CRM-карточке — отправка невозможна
          </div>
        </q-card-section>

        <q-separator />

        <!-- Секция: Основная ссылка -->
        <q-card-section v-if="mainClientLink">
          <div class="text-subtitle2 q-mb-xs">
            <q-icon name="link" size="16px" class="q-mr-xs" />
            Основная ссылка
          </div>
          <div class="text-caption text-grey-7 q-mb-sm">
            Та же ссылка, что и в email-приглашении
          </div>
          <q-input :model-value="mainClientLink" readonly outlined dense>
            <template #append>
              <q-btn flat dense icon="content_copy" @click="copyMainLink">
                <q-tooltip>Скопировать</q-tooltip>
              </q-btn>
            </template>
          </q-input>
        </q-card-section>

        <q-separator />

        <!-- Секция: Ссылки для представителей -->
        <q-card-section>
          <div class="text-subtitle2 q-mb-xs">
            <q-icon name="group_add" size="16px" class="q-mr-xs" />
            Ссылки для представителей
          </div>
          <div class="text-caption text-grey-7 q-mb-sm">
            Для жены, прораба или других участников проекта
          </div>
          <q-input
            v-if="inviteLink"
            :model-value="inviteLink"
            readonly
            outlined
            dense
            class="q-mb-sm"
          >
            <template #append>
              <q-btn flat dense icon="content_copy" @click="copyLink">
                <q-tooltip>Скопировать</q-tooltip>
              </q-btn>
            </template>
          </q-input>
          <q-btn
            v-if="canManage"
            outline
            color="primary"
            icon="add_link"
            label="Создать новую ссылку"
            :loading="creatingLink"
            class="full-width"
            @click="createInviteLink"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Закрыть" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from 'src/boot/axios'
import { crmApi } from 'src/services/api'
import { usePermission } from 'src/composables/usePermission'
import { useQuasar } from 'quasar'

const router = useRouter()
const { can } = usePermission()
const $q = useQuasar()

const loading = ref(false)
const chats = ref([])
const searchText = ref('')

const showAccessDialog = ref(false)
const activeChatId = ref(null)
const activeCrmCardId = ref(null)
const mainClientLink = ref('')
const inviteLink = ref('')
const sendingInvite = ref(false)
const creatingLink = ref(false)

const canManage = computed(() => can('chat.client.manage'))

function fuzzyScore(str, query) {
  if (!query) return 3
  const s = str.toLowerCase()
  const q = query.toLowerCase()
  if (s === q) return 4
  if (s.startsWith(q)) return 3
  if (s.includes(q)) return 2
  let si = 0
  for (let qi = 0; qi < q.length; qi++) {
    while (si < s.length && s[si] !== q[qi]) si++
    if (si >= s.length) return -1
    si++
  }
  return 1
}

const filteredChats = computed(() => {
  const q = searchText.value?.trim() || ''
  if (!q) return chats.value
  return chats.value
    .map(c => ({ c, score: fuzzyScore(c.title || `Чат #${c.id}`, q) }))
    .filter(({ score }) => score >= 1)
    .sort((a, b) => b.score - a.score)
    .map(({ c }) => c)
})

async function loadChats() {
  loading.value = true
  try {
    const { data } = await api.get('/api/v1/chats', {
      params: { chat_type: 'client' },
    })
    chats.value = Array.isArray(data) ? data : (data.items || [])
  } catch (e) {
    console.error('[ClientChatsPage] Ошибка:', e)
  } finally {
    loading.value = false
  }
}

function openChat(chat) {
  router.push({ name: 'client-chat-room', params: { chatId: chat.id } })
}

function openAccessDialog(chat) {
  activeChatId.value = chat.id
  activeCrmCardId.value = chat.crm_card_id || null
  inviteLink.value = ''
  mainClientLink.value = chat.client_access_token
    ? `${window.location.origin}/c/${chat.client_access_token}`
    : ''
  showAccessDialog.value = true
}

async function sendEmailInvite() {
  if (!activeCrmCardId.value) return
  sendingInvite.value = true
  try {
    const { data } = await crmApi.inviteClientToChat(activeCrmCardId.value)
    $q.notify({ type: 'positive', message: data.message || 'Приглашение отправлено' })
  } catch (e) {
    const msg = e.response?.data?.detail || 'Ошибка отправки приглашения'
    $q.notify({ type: 'negative', message: msg })
  } finally {
    sendingInvite.value = false
  }
}

async function createInviteLink() {
  if (!activeChatId.value) return
  creatingLink.value = true
  try {
    const { data } = await api.post(`/api/v1/chats/${activeChatId.value}/invite-links`)
    const token = data.access_token
    inviteLink.value = `${window.location.origin}/c/${token}`
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Ошибка создания ссылки' })
  } finally {
    creatingLink.value = false
  }
}

function copyMainLink() {
  if (!mainClientLink.value) return
  navigator.clipboard.writeText(mainClientLink.value).then(() => {
    $q.notify({ type: 'positive', message: 'Ссылка скопирована' })
  })
}

function copyLink() {
  navigator.clipboard.writeText(inviteLink.value).then(() => {
    $q.notify({ type: 'positive', message: 'Ссылка скопирована' })
  })
}

onMounted(loadChats)
</script>
