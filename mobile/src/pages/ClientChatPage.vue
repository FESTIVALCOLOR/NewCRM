<template>
  <q-page class="column" style="height: 100vh; overflow: hidden">
    <!-- Шапка -->
    <div
      class="row items-center q-px-md q-py-sm bg-white"
      style="border-bottom: 1px solid #E0E0E0; flex-shrink: 0"
    >
      <div class="column" style="flex: 1; min-width: 0">
        <div class="text-subtitle2 text-weight-bold ellipsis">
          {{ chatTitle }}
        </div>
        <div v-if="typingText" class="text-caption text-grey ellipsis">
          {{ typingText }}
        </div>
        <div v-else-if="wsConnected" class="text-caption text-grey">
          <q-icon name="wifi" size="10px" color="positive" class="q-mr-xs" />онлайн
        </div>
        <div v-else class="text-caption text-grey">
          <q-icon name="wifi_off" size="10px" color="negative" class="q-mr-xs" />переподключение…
        </div>
      </div>
    </div>

    <!-- Список сообщений -->
    <div
      ref="messagesEl"
      class="col q-pa-md"
      style="overflow-y: auto; background: #F5F5F5"
    >
      <div v-if="loadingMessages" class="text-center q-mt-lg">
        <q-spinner size="24px" color="grey" />
      </div>

      <div v-else-if="!messages.length" class="text-center text-grey q-mt-xl">
        <q-icon name="chat_bubble_outline" size="40px" />
        <div class="q-mt-sm text-body2">
          Напишите нам — мы ответим!
        </div>
      </div>

      <template v-else>
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="q-mb-sm"
          :class="isOwn(msg) ? 'row justify-end' : 'row justify-start'"
        >
          <!-- Системные сообщения -->
          <div v-if="msg.message_type === 'system'" class="text-center full-width">
            <q-chip dense size="sm" color="green-1" text-color="green-9">
              {{ msg.content }}
            </q-chip>
          </div>

          <!-- Обычные -->
          <div
            v-else
            :class="isOwn(msg) ? 'bubble-own' : 'bubble-staff'"
            style="max-width: 80%"
          >
            <div
              v-if="!isOwn(msg)"
              class="text-caption text-weight-bold q-mb-xs"
              style="color: #1565C0"
            >
              {{ msg.sender_display_name }}
            </div>

            <template v-if="msg.message_type === 'file' || msg.message_type === 'image'">
              <div class="row items-center q-gutter-xs">
                <q-icon :name="msg.message_type === 'image' ? 'image' : 'attach_file'" size="20px" />
                <a :href="msg.file_url" target="_blank" class="text-body2 ellipsis" style="max-width: 200px; color: inherit">
                  {{ msg.file_name || 'Файл' }}
                </a>
              </div>
            </template>

            <template v-else>
              <div class="text-body2" style="white-space: pre-wrap; word-break: break-word">
                {{ msg.content }}
              </div>
            </template>

            <div
              class="text-caption q-mt-xs"
              :class="isOwn(msg) ? 'text-right' : 'text-left'"
              style="color: #888; font-size: 10px"
            >
              {{ formatTime(msg.created_at) }}
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
          icon="attach_file"
          @click="pickFile"
        >
          <q-tooltip>Прикрепить файл</q-tooltip>
        </q-btn>
        <input ref="fileInput" type="file" class="hidden" @change="onFileSelected">
        <q-input
          v-model="inputText"
          outlined
          dense
          autogrow
          placeholder="Ваше сообщение…"
          style="flex: 1"
          @keydown.enter.exact.prevent="sendText"
          @input="onTyping"
        />
        <q-btn
          round
          dense
          icon="send"
          color="green-7"
          :disable="!inputText.trim()"
          @click="sendText"
        />
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatWebSocket } from 'src/composables/useChatWebSocket'
import { useQuasar } from 'quasar'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const accessToken = route.params.token  // UUID из URL /c/{token}

const { isConnected: wsConnected, connectClient, disconnect, sendMessage, sendTypingStart, sendTypingStop, sendRead, typingUsers, messages: wsMessages } = useChatWebSocket()

const chatTitle = ref('Чат с бюро')
const messages = ref([])
const inputText = ref('')
const loadingMessages = ref(false)
const messagesEl = ref(null)
const fileInput = ref(null)
const clientName = sessionStorage.getItem('client_name') || 'Клиент'

const typingText = computed(() => {
  if (!typingUsers.value.length) return ''
  const names = typingUsers.value.map(u => u.name)
  if (names.length === 1) return `${names[0]} печатает…`
  return `${names.join(', ')} печатают…`
})

function isOwn(msg) {
  // Сообщение принадлежит этому клиенту — по guestToken совпадению
  return msg.sender_guest_token === accessToken
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

async function loadMessages() {
  loadingMessages.value = true
  try {
    const baseURL = window.location.origin
    const { data } = await axios.get(`${baseURL}/api/v1/client-chat/${accessToken}`)
    if (data.requires_registration) {
      // Клиент не зарегистрирован → на страницу регистрации
      router.replace({ name: 'client-register', params: { token: accessToken } })
      return
    }
    chatTitle.value = data.title || 'Чат с бюро'
    messages.value = data.messages || []
    scrollToBottom()

    if (messages.value.length) {
      sendRead(messages.value[messages.value.length - 1].id)
    }
  } catch (e) {
    if (e.response?.status === 404) {
      $q.notify({ type: 'negative', message: 'Ссылка недействительна' })
    } else {
      console.error('[ClientChatPage]', e)
    }
  } finally {
    loadingMessages.value = false
  }
}

function sendText() {
  const text = inputText.value.trim()
  if (!text) return
  sendMessage(text)
  // Оптимистично добавляем в список
  messages.value.push({
    id: Date.now(),
    message_type: 'text',
    content: text,
    sender_guest_token: accessToken,
    sender_display_name: clientName,
    created_at: new Date().toISOString(),
  })
  inputText.value = ''
  scrollToBottom()
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
  if (!file) return
  try {
    const baseURL = window.location.origin
    const formData = new FormData()
    formData.append('file', file)
    await axios.post(`${baseURL}/api/v1/client-chat/${accessToken}/files`, formData)
    $q.notify({ type: 'positive', message: 'Файл отправлен' })
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки файла' })
  } finally {
    event.target.value = ''
  }
}

onMounted(async () => {
  await loadMessages()
  // Подключаем WS как клиент (без JWT)
  connectClient(accessToken, {
    onMessage: (msg) => {
      // Не дублируем оптимистичные сообщения
      const exists = messages.value.some(m => m.id === msg.id)
      if (!exists) {
        messages.value.push(msg)
        scrollToBottom()
      }
    },
  })
})

onUnmounted(() => {
  disconnect()
  if (typingTimer) clearTimeout(typingTimer)
})
</script>

<style scoped>
.bubble-own {
  background: #E8F5E9;
  border-radius: 12px 12px 2px 12px;
  padding: 8px 12px;
}
.bubble-staff {
  background: #fff;
  border-radius: 12px 12px 12px 2px;
  padding: 8px 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
.hidden {
  display: none;
}
</style>
