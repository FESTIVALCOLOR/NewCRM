<template>
  <!-- Загрузка -->
  <div v-if="loading" class="flex flex-center q-pa-xl">
    <q-spinner size="32px" color="grey" />
  </div>

  <!-- Чат не создан -->
  <div v-else-if="!chat" class="flex flex-center q-pa-xl column items-center">
    <q-icon
      :name="chatType === 'client' ? 'support_agent' : 'chat_bubble_outline'"
      size="48px"
      color="grey-4"
      class="q-mb-md"
    />
    <div class="text-grey-6 q-mb-md text-body2">
      {{ chatType === 'client' ? 'Чат с клиентом не создан' : 'Чат сотрудников не создан' }}
    </div>
    <q-btn
      unelevated
      no-caps
      :color="chatType === 'client' ? 'green-7' : 'blue-7'"
      :label="chatType === 'client' ? 'Создать чат с клиентом' : 'Создать чат сотрудников'"
      :loading="creating"
      @click="createChat"
    />
  </div>

  <!-- Чат существует -->
  <div v-else ref="chatContainerEl" class="column" :style="{ height: containerHeight, minHeight: '320px' }">
    <!-- Панель: ссылка для клиента -->
    <div
      v-if="chatType === 'client' && clientLink"
      class="row items-center q-px-md q-py-xs"
      style="background: #E8F5E9; border-bottom: 1px solid #C8E6C9; flex-shrink: 0"
    >
      <q-icon name="link" size="14px" color="green-7" class="q-mr-xs" />
      <span class="text-caption text-green-8" style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
        {{ clientLink }}
      </span>
      <q-btn
        flat
        dense
        size="xs"
        icon="content_copy"
        color="green-7"
        @click="copyClientLink"
      >
        <q-tooltip>Копировать ссылку</q-tooltip>
      </q-btn>
    </div>

    <!-- Индикатор печати -->
    <div
      v-if="typingText"
      class="q-px-md q-py-xs text-caption text-grey"
      style="flex-shrink: 0; background: #FAFAFA"
    >
      {{ typingText }}
    </div>

    <!-- Список сообщений -->
    <div
      ref="messagesEl"
      class="col q-px-md q-py-sm"
      style="overflow-y: auto; background: #F5F5F5"
    >
      <div v-if="!messages.length" class="text-center text-grey q-mt-lg">
        <q-icon name="chat_bubble_outline" size="32px" />
        <div class="q-mt-xs text-body2">
          Нет сообщений
        </div>
      </div>

      <template v-else>
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="q-mb-sm"
          :class="isOwn(msg) ? 'row justify-end' : 'row justify-start'"
        >
          <!-- Системные -->
          <div v-if="msg.message_type === 'system'" class="text-center full-width">
            <q-chip dense size="sm" color="grey-3" text-color="grey-7">
              {{ msg.content }}
            </q-chip>
          </div>

          <!-- Обычные -->
          <div
            v-else
            :class="isOwn(msg) ? 'bubble-own' : 'bubble-other'"
            style="max-width: 80%"
          >
            <div
              v-if="!isOwn(msg)"
              class="text-caption text-weight-bold q-mb-xs"
              :style="{ color: msg.sender_guest_token ? '#2E7D32' : '#1565C0' }"
            >
              {{ msg.sender_display_name }}
              <q-chip
                v-if="msg.sender_guest_token"
                dense
                size="xs"
                color="green-2"
                text-color="green-9"
              >
                клиент
              </q-chip>
            </div>

            <template v-if="msg.message_type === 'file' || msg.message_type === 'image'">
              <div class="row items-center q-gutter-xs">
                <q-icon :name="msg.message_type === 'image' ? 'image' : 'attach_file'" size="18px" />
                <a
                  :href="msg.file_url"
                  target="_blank"
                  class="text-body2 ellipsis"
                  style="max-width: 180px; color: inherit; font-size: 12px"
                >
                  {{ msg.file_name || 'Файл' }}
                </a>
              </div>
            </template>

            <template v-else>
              <div class="text-body2" style="white-space: pre-wrap; word-break: break-word; font-size: 13px">
                {{ msg.content }}
              </div>
            </template>

            <!-- Время + кнопка переслать клиенту (только в чате сотрудников) -->
            <div class="row items-center q-mt-xs" :class="isOwn(msg) ? 'justify-end' : 'justify-between'">
              <q-btn
                v-if="chatType === 'employee' && clientChatId && !isOwn(msg)"
                flat
                dense
                size="xs"
                icon="forward"
                color="blue-5"
                :loading="forwardingMsgId === msg.id"
                @click="forwardToClient(msg)"
              >
                <q-tooltip>Переслать клиенту</q-tooltip>
              </q-btn>
              <q-btn
                v-if="chatType === 'employee' && clientChatId && isOwn(msg)"
                flat
                dense
                size="xs"
                icon="forward"
                color="blue-5"
                :loading="forwardingMsgId === msg.id"
                @click="forwardToClient(msg)"
              >
                <q-tooltip>Переслать клиенту</q-tooltip>
              </q-btn>
              <div class="text-caption" style="color: #888; font-size: 10px">
                {{ formatTime(msg.created_at) }}
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Панель ввода -->
    <div class="q-pa-sm bg-white" style="border-top: 1px solid #E0E0E0; flex-shrink: 0">
      <div class="row items-end q-gutter-xs">
        <q-btn
          flat
          round
          dense
          size="sm"
          icon="attach_file"
          @click="pickFile"
        >
          <q-tooltip>Прикрепить файл</q-tooltip>
        </q-btn>
        <input ref="fileInput" type="file" style="display: none" @change="onFileSelected">
        <q-input
          v-model="inputText"
          outlined
          dense
          autogrow
          placeholder="Сообщение…"
          style="flex: 1"
          @keydown.enter.exact.prevent="sendText"
          @input="onTyping"
        />
        <q-btn
          round
          dense
          size="sm"
          icon="send"
          :color="chatType === 'client' ? 'green-7' : 'blue-7'"
          :disable="!inputText.trim()"
          @click="sendText"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { api } from 'src/boot/axios'
import { useChatWebSocket } from 'src/composables/useChatWebSocket'
import { useAuthStore } from 'src/stores/auth'
import { useQuasar } from 'quasar'

const props = defineProps({
  chatType: {
    type: String,
    required: true, // 'employee' | 'client'
  },
  cardId: {
    type: Number,
    default: null,
  },
})

const authStore = useAuthStore()
const $q = useQuasar()
const { connectEmployee, disconnect, sendMessage, sendTypingStart, sendTypingStop, sendRead, typingUsers } = useChatWebSocket()

const loading = ref(false)
const creating = ref(false)
const chat = ref(null)
const messages = ref([])
const inputText = ref('')
const messagesEl = ref(null)
const fileInput = ref(null)
const chatContainerEl = ref(null)
const containerHeight = ref('calc(100vh - 270px)')
const clientChatId = ref(null)
const forwardingMsgId = ref(null)

function recalcHeight() {
  if (!chatContainerEl.value) return
  const rect = chatContainerEl.value.getBoundingClientRect()
  const h = Math.max(320, window.innerHeight - rect.top - 8)
  containerHeight.value = h + 'px'
}

const clientLink = computed(() => {
  if (props.chatType !== 'client' || !chat.value?.client_access_token) return ''
  return `${window.location.origin}/c/${chat.value.client_access_token}`
})

const typingText = computed(() => {
  if (!typingUsers.value.length) return ''
  const names = typingUsers.value.map(u => u.name)
  if (names.length === 1) return `${names[0]} печатает…`
  return `${names.join(', ')} печатают…`
})

function isOwn(msg) {
  return msg.sender_employee_id === authStore.employee?.id
}

function formatTime(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

async function loadChat() {
  if (!props.cardId) return
  loading.value = true
  try {
    const { data } = await api.get('/api/v1/chats/', {
      params: { chat_type: props.chatType, crm_card_id: props.cardId },
    })
    const list = Array.isArray(data) ? data : (data.items || [])
    if (list.length > 0) {
      await openChat(list[0].id)
    }
  } catch (e) {
    console.error('[InlineChatRoom] loadChat:', e)
  } finally {
    loading.value = false
  }
}

async function openChat(chatId) {
  try {
    const { data } = await api.get(`/api/v1/chats/${chatId}`)
    chat.value = data
    messages.value = data.messages || []
    scrollToBottom()

    // Для чата сотрудников загрузить клиентский чат (для пересылки)
    if (props.chatType === 'employee' && data.crm_card_id) {
      loadClientChat(data.crm_card_id)
    }

    const token = localStorage.getItem('access_token')
    if (token) {
      connectEmployee(chatId, token, {
        onMessage: (msg) => {
          const exists = messages.value.some(m => m.id === msg.id)
          if (!exists) {
            messages.value.push(msg)
            scrollToBottom()
          }
        },
      })
    }

    if (messages.value.length) {
      sendRead(messages.value[messages.value.length - 1].id)
    }
  } catch (e) {
    console.error('[InlineChatRoom] openChat:', e)
  }
}

async function loadClientChat(cardId) {
  try {
    const { data } = await api.get('/api/v1/chats/', {
      params: { chat_type: 'client', crm_card_id: cardId },
    })
    const list = Array.isArray(data) ? data : (data.items || [])
    if (list.length > 0) clientChatId.value = list[0].id
  } catch {
    // Нет клиентского чата
  }
}

async function forwardToClient(msg) {
  if (!clientChatId.value || forwardingMsgId.value) return
  forwardingMsgId.value = msg.id
  try {
    const formData = new FormData()
    formData.append('msg_id', msg.id)
    await api.post(`/api/v1/chats/${chat.value.id}/forward/${clientChatId.value}`, formData)
    $q.notify({ type: 'positive', message: 'Переслано в чат клиента' })
  } catch (e) {
    const detail = e.response?.data?.detail || 'Ошибка пересылки'
    $q.notify({ type: 'negative', message: detail })
  } finally {
    forwardingMsgId.value = null
  }
}

async function createChat() {
  if (!props.cardId) return
  creating.value = true
  try {
    const { data } = await api.post('/api/v1/chats/', {
      chat_type: props.chatType,
      crm_card_id: props.cardId,
    })
    await openChat(data.id)
    $q.notify({ type: 'positive', message: 'Чат создан' })
  } catch (e) {
    const msg = e.response?.data?.detail || 'Ошибка создания чата'
    $q.notify({ type: 'negative', message: msg })
  } finally {
    creating.value = false
  }
}

function sendText() {
  const text = inputText.value.trim()
  if (!text) return
  sendMessage(text)
  inputText.value = ''
}

let typingTimer = null
function onTyping() {
  sendTypingStart()
  if (typingTimer) clearTimeout(typingTimer)
  typingTimer = setTimeout(() => sendTypingStop(), 2000)
}

function pickFile() {
  fileInput.value?.click()
}

async function onFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file || !chat.value) return
  try {
    const formData = new FormData()
    formData.append('file', file)
    await api.post(`/api/v1/chats/${chat.value.id}/files`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки файла' })
  } finally {
    event.target.value = ''
  }
}

function copyClientLink() {
  if (!clientLink.value) return
  navigator.clipboard.writeText(clientLink.value).then(() => {
    $q.notify({ type: 'positive', message: 'Ссылка скопирована' })
  }).catch(() => {})
}

onMounted(() => {
  loadChat()
  nextTick(() => {
    recalcHeight()
    window.addEventListener('resize', recalcHeight)
  })
})

// Пересчитываем высоту когда чат загружается (переход из skeleton → контент)
watch(chat, () => nextTick(recalcHeight))

onUnmounted(() => {
  disconnect()
  window.removeEventListener('resize', recalcHeight)
  if (typingTimer) clearTimeout(typingTimer)
})
</script>

<style scoped>
.bubble-own {
  background: #E8F5E9;
  border-radius: 12px 12px 2px 12px;
  padding: 6px 10px;
}
.bubble-other {
  background: #fff;
  border-radius: 12px 12px 12px 2px;
  padding: 6px 10px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
</style>
