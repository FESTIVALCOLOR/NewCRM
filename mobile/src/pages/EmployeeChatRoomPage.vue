<template>
  <q-page class="column" :style="{ height: chatPageH, overflow: 'hidden' }">
    <!-- Шапка -->
    <div class="row items-center q-px-md q-py-sm bg-white" style="border-bottom: 1px solid #E0E0E0; flex-shrink: 0">
      <q-btn
        flat
        round
        dense
        icon="arrow_back"
        @click="$router.back()"
      />
      <div class="q-ml-sm column" style="flex: 1; min-width: 0">
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
          <q-icon name="wifi_off" size="10px" color="negative" class="q-mr-xs" />оффлайн
        </div>
      </div>
      <q-btn
        flat
        round
        dense
        icon="people"
        @click="showMembers = true"
      >
        <q-tooltip>Участники</q-tooltip>
      </q-btn>
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
        <div class="q-mt-sm">
          Начните диалог
        </div>
      </div>

      <template v-else>
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="q-mb-sm"
          :class="isOwn(msg) ? 'row justify-end' : 'row justify-start'"
        >
          <!-- Системные сообщения — по центру -->
          <div v-if="msg.message_type === 'system'" class="text-center full-width">
            <q-chip dense size="sm" color="grey-3" text-color="grey-7">
              {{ msg.content }}
            </q-chip>
          </div>

          <!-- Обычные сообщения -->
          <div
            v-else
            :class="isOwn(msg) ? 'bubble-own' : 'bubble-other'"
            style="max-width: 75%; position: relative"
          >
            <!-- Имя отправителя (чужие) -->
            <div
              v-if="!isOwn(msg)"
              class="text-caption text-weight-bold q-mb-xs"
              style="color: #1565C0"
            >
              {{ msg.sender_display_name }}
            </div>

            <!-- Файл -->
            <template v-if="msg.message_type === 'image'">
              <a :href="msg.file_url" target="_blank">
                <img
                  :src="msg.file_url"
                  style="max-width: 100%; max-height: 200px; border-radius: 6px; display: block; cursor: pointer"
                  @error="$event.target.style.display='none'"
                >
              </a>
              <div v-if="msg.file_name" class="text-caption q-mt-xs" style="color: #888">
                {{ msg.file_name }}
              </div>
            </template>
            <template v-else-if="msg.message_type === 'file'">
              <div class="row items-center q-gutter-xs">
                <q-icon name="attach_file" size="20px" />
                <a :href="msg.file_url" target="_blank" class="text-body2 ellipsis" style="max-width: 180px; color: inherit">
                  {{ msg.file_name || 'Файл' }}
                </a>
              </div>
            </template>

            <!-- Голосовое -->
            <template v-else-if="msg.message_type === 'voice'">
              <div class="row items-center q-gutter-xs">
                <q-btn
                  flat
                  round
                  dense
                  icon="play_arrow"
                  size="sm"
                  @click="playVoice(msg.file_url)"
                />
                <span class="text-body2">Голосовое сообщение</span>
              </div>
            </template>

            <!-- Текст -->
            <template v-else>
              <div class="text-body2" style="white-space: pre-wrap; word-break: break-word">
                {{ msg.content }}
              </div>
            </template>

            <!-- Время + кнопка переслать клиенту -->
            <div class="row items-center q-mt-xs" :class="isOwn(msg) ? 'justify-end' : 'justify-between'">
              <q-btn
                v-if="clientChatId && !isOwn(msg)"
                flat
                dense
                size="xs"
                icon="forward"
                color="blue-5"
                class="q-mr-xs"
                :loading="forwardingMsgId === msg.id"
                @click="forwardToClient(msg)"
              >
                <q-tooltip>Переслать клиенту</q-tooltip>
              </q-btn>
              <q-btn
                v-if="clientChatId && isOwn(msg)"
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

    <!-- Прогресс загрузки файла -->
    <q-linear-progress
      v-if="uploadProgress > 0 && uploadProgress < 100"
      :value="uploadProgress / 100"
      color="primary"
      style="flex-shrink: 0"
    />

    <!-- Панель ввода -->
    <div class="q-pa-sm bg-white" style="border-top: 1px solid #E0E0E0; flex-shrink: 0">
      <div class="row items-center q-gutter-xs">
        <!-- Прикрепить файл -->
        <q-btn
          flat
          round
          dense
          icon="attach_file"
          :loading="uploadProgress > 0 && uploadProgress < 100"
          @click="pickFile"
        >
          <q-tooltip>Прикрепить файл</q-tooltip>
        </q-btn>
        <input ref="fileInput" type="file" class="hidden" @change="onFileSelected">

        <!-- Поле ввода -->
        <q-input
          v-model="inputText"
          outlined
          dense
          autogrow
          hide-bottom-space
          placeholder="Сообщение…"
          style="flex: 1"
          @keydown.enter.exact.prevent="sendText"
          @input="onTyping"
        />

        <!-- Отправить -->
        <q-btn
          round
          dense
          icon="send"
          color="primary"
          :disable="!inputText.trim()"
          @click="sendText"
        />
      </div>
    </div>

    <!-- Участники -->
    <q-dialog v-model="showMembers">
      <q-card style="min-width: 300px">
        <q-card-section class="row items-center">
          <div class="text-h6">
            Участники чата
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
        <q-list>
          <q-item v-for="m in members" :key="m.id">
            <q-item-section avatar>
              <q-avatar
                :color="m.member_type === 'employee' ? 'blue-2' : 'green-2'"
                :text-color="m.member_type === 'employee' ? 'blue-9' : 'green-9'"
                icon="person"
                size="32px"
              />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ m.display_name || m.guest_name || `#${m.id}` }}</q-item-label>
              <q-item-label caption>
                {{ m.role_in_project || (m.member_type === 'employee' ? 'Сотрудник' : 'Клиент') }}
              </q-item-label>
            </q-item-section>
          </q-item>
          <q-item v-if="!members.length">
            <q-item-section>
              <q-item-label class="text-grey">
                Нет участников
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { api } from 'src/boot/axios'
import { useChatWebSocket } from 'src/composables/useChatWebSocket'
import { useAuthStore } from 'src/stores/auth'
import { useQuasar } from 'quasar'

const route = useRoute()
const authStore = useAuthStore()
const $q = useQuasar()
const chatId = Number(route.params.chatId)

const { isConnected: wsConnected, connectEmployee, disconnect, sendMessage, sendTypingStart, sendTypingStop, sendRead, typingUsers } = useChatWebSocket()

const chatTitle = ref('Чат сотрудников')
const messages = ref([])
const members = ref([])
const inputText = ref('')
const loadingMessages = ref(false)
const showMembers = ref(false)
const messagesEl = ref(null)
const fileInput = ref(null)
const clientChatId = ref(null)
const forwardingMsgId = ref(null)
const chatPageH = ref(window.innerHeight + 'px')
const uploadProgress = ref(0)

let typingTimer = null

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
  const d = new Date(dt)
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

async function loadMessages() {
  loadingMessages.value = true
  try {
    const { data } = await api.get(`/api/v1/chats/${chatId}`)
    chatTitle.value = data.title || `Чат #${chatId}`
    messages.value = data.messages || []
    members.value = data.members || []
    scrollToBottom()

    // Отметить прочитанными
    if (messages.value.length) {
      const lastId = messages.value[messages.value.length - 1].id
      sendRead(lastId)
    }

    // Загрузить клиентский чат для той же карточки (для пересылки)
    if (data.crm_card_id) {
      loadClientChat(data.crm_card_id)
    }
  } catch (e) {
    console.error('[ChatRoom] Ошибка загрузки:', e)
  } finally {
    loadingMessages.value = false
  }
}

async function loadClientChat(cardId) {
  try {
    const { data } = await api.get('/api/v1/chats/', {
      params: { chat_type: 'client', crm_card_id: cardId },
    })
    const list = Array.isArray(data) ? data : (data.items || [])
    if (list.length > 0) {
      clientChatId.value = list[0].id
    }
  } catch {
    // Клиентский чат не найден — кнопка не показывается
  }
}

async function forwardToClient(msg) {
  if (!clientChatId.value || forwardingMsgId.value) return
  forwardingMsgId.value = msg.id
  try {
    await api.post(`/api/v1/chats/${chatId}/forward/${clientChatId.value}`, { msg_id: msg.id })
    $q.notify({ type: 'positive', message: 'Переслано в чат клиента' })
  } catch (e) {
    const raw = e.response?.data?.detail
    const message = Array.isArray(raw) ? raw.map(d => d.msg || String(d)).join('; ') : (raw || 'Ошибка пересылки')
    $q.notify({ type: 'negative', message: String(message) })
  } finally {
    forwardingMsgId.value = null
  }
}

function sendText() {
  const text = inputText.value.trim()
  if (!text) return
  sendMessage(text)
  inputText.value = ''
}

function onTyping() {
  sendTypingStart()
  if (typingTimer) clearTimeout(typingTimer)
  typingTimer = setTimeout(() => {
    sendTypingStop()
  }, 2000)
}

function pickFile() {
  fileInput.value?.click()
}

async function onFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return
  try {
    const ext = file.name.split('.').pop()?.toLowerCase() || ''
    const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif']
    const msgType = imageExts.includes(ext) ? 'image' : 'file'

    const formData = new FormData()
    formData.append('file', file)
    formData.append('message_type', msgType)

    uploadProgress.value = 1
    await api.post(`/api/v1/chats/${chatId}/files`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        uploadProgress.value = e.total ? Math.round((e.loaded / e.total) * 100) : 50
      },
    })
    // Сообщение придёт через WS
  } catch (e) {
    console.error('[ChatRoom] Ошибка загрузки файла:', e)
    $q.notify({ type: 'negative', message: 'Ошибка загрузки файла' })
  } finally {
    uploadProgress.value = 0
    event.target.value = ''
  }
}

function playVoice(url) {
  if (url) window.open(url, '_blank')
}

onMounted(() => {
  const header = document.querySelector('.q-header')
  chatPageH.value = (window.innerHeight - (header?.offsetHeight ?? 44)) + 'px'
  loadMessages()
  const token = localStorage.getItem('access_token')
  if (token) {
    connectEmployee(chatId, token, {
      onMessage: (msg) => {
        const exists = messages.value.some(m => m.id === msg.id)
        if (!exists) {
          messages.value.push(msg)
          scrollToBottom()
          sendRead(msg.id)
        }
      },
    })
  }
})

onUnmounted(() => {
  disconnect()
  if (typingTimer) clearTimeout(typingTimer)
})
</script>

<style scoped>
.bubble-own {
  background: #FFF8DC;
  border-radius: 12px 12px 2px 12px;
  padding: 8px 12px;
}
.bubble-other {
  background: #fff;
  border-radius: 12px 12px 12px 2px;
  padding: 8px 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
.hidden {
  display: none;
}
</style>
