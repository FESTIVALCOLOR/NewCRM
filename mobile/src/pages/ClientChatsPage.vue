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
          <q-badge
            v-if="chat.unread_count"
            color="negative"
            :label="chat.unread_count"
            rounded
          />
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

    <!-- Диалог: ссылка-приглашение -->
    <q-dialog v-model="showLinkDialog">
      <q-card style="min-width: 340px">
        <q-card-section class="row items-center">
          <div class="text-h6">
            Ссылка для клиента
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
        <q-separator />
        <q-card-section>
          <div class="text-body2 q-mb-md">
            Отправьте клиенту эту ссылку:
          </div>
          <q-input :model-value="inviteLink" readonly outlined dense>
            <template #append>
              <q-btn flat dense icon="content_copy" @click="copyLink" />
            </template>
          </q-input>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Закрыть" />
          <q-btn
            v-if="canAddInvite"
            color="primary"
            label="Новая ссылка"
            @click="createInviteLink"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from 'src/boot/axios'
import { usePermission } from 'src/composables/usePermission'
import { useQuasar } from 'quasar'

const router = useRouter()
const { can } = usePermission()
const $q = useQuasar()

const loading = ref(false)
const chats = ref([])
const searchText = ref('')
const showLinkDialog = ref(false)
const inviteLink = ref('')
const activeChatId = ref(null)

const canAddInvite = computed(() => can('chat.client.manage'))

const filteredChats = computed(() => {
  const q = searchText.value?.toLowerCase() || ''
  if (!q) return chats.value
  return chats.value.filter(c => (c.title || '').toLowerCase().includes(q))
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

async function createInviteLink() {
  if (!activeChatId.value) return
  try {
    const { data } = await api.post(`/api/v1/chats/${activeChatId.value}/invite-links`)
    const token = data.access_token
    const base = window.location.origin
    inviteLink.value = `${base}/c/${token}`
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Ошибка создания ссылки' })
  }
}

function copyLink() {
  navigator.clipboard.writeText(inviteLink.value).then(() => {
    $q.notify({ type: 'positive', message: 'Ссылка скопирована' })
  })
}

onMounted(loadChats)
</script>
