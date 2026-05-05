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
              v-if="canAddInvite"
              flat
              round
              dense
              size="xs"
              icon="link"
              color="grey-6"
              @click.stop="openLinkDialog(chat)"
            >
              <q-tooltip>Ссылка для клиента</q-tooltip>
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
  activeChatId.value = chat.id
  router.push({ name: 'client-chat-room', params: { chatId: chat.id } })
}

function openLinkDialog(chat) {
  activeChatId.value = chat.id
  inviteLink.value = ''
  showLinkDialog.value = true
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
