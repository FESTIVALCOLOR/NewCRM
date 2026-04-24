<template>
  <q-page class="column" :style="{ height: chatPageH, overflow: 'hidden' }">
    <!-- Шапка -->
    <div
      class="row items-center q-px-md q-py-sm bg-white"
      style="border-bottom: 1px solid #E0E0E0; flex-shrink: 0"
    >
      <div class="column" style="flex: 1; min-width: 0">
        <div class="text-subtitle2 text-weight-bold" style="word-break: break-word; line-height: 1.3">
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

    <!-- Баннер установки PWA (inline, чтобы не перекрывать поле ввода) -->
    <PwaInstallBanner inline />

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
        <template v-for="msg in messages" :key="msg.id">
          <!-- Разделитель «Непрочитанные сообщения» -->
          <div
            v-if="firstUnreadId && msg.id === firstUnreadId"
            data-unread-divider
            class="row items-center q-my-sm"
          >
            <div class="col" style="height: 1px; background: #E53935" />
            <span class="q-px-sm text-caption text-negative text-weight-medium">Непрочитанные сообщения</span>
            <div class="col" style="height: 1px; background: #E53935" />
          </div>
          <div
            :data-msg-id="msg.id"
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
              :class="msg.message_type === 'image'
                ? (isOwn(msg) ? 'bubble-img-own' : 'bubble-img-staff')
                : (isOwn(msg) ? 'bubble-own' : 'bubble-staff')"
              style="max-width: 80%"
            >
              <!-- Верхняя строка: имя отправителя + кнопка меню -->
              <div
                class="row no-wrap items-center justify-between q-mb-xs"
                :style="msg.message_type === 'image' ? 'min-height:16px;gap:2px;padding:6px 10px 4px' : 'min-height:16px;gap:2px'"
              >
                <div
                  class="text-caption text-weight-bold"
                  :style="{ color: isOwn(msg) ? '#1B5E20' : '#1565C0', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }"
                >
                  {{ msg.sender_display_name || (isOwn(msg) ? clientName : '') }}
                </div>
                <q-btn
                  v-if="isOwn(msg) && !msg.is_deleted"
                  flat
                  round
                  dense
                  size="xs"
                  icon="more_vert"
                  color="grey-5"
                  style="margin: -4px -6px -2px 2px; flex-shrink: 0"
                >
                  <q-menu auto-close>
                    <q-list dense style="min-width: 150px">
                      <q-item
                        v-if="msg.message_type === 'text'"
                        clickable
                        @click="startClientEdit(msg)"
                      >
                        <q-item-section avatar>
                          <q-icon name="edit" size="16px" color="grey-7" />
                        </q-item-section>
                        <q-item-section style="font-size: 13px">
                          Редактировать
                        </q-item-section>
                      </q-item>
                      <q-item clickable @click="deleteClientMsg(msg)">
                        <q-item-section avatar>
                          <q-icon name="delete_outline" size="16px" color="red-5" />
                        </q-item-section>
                        <q-item-section class="text-red-6" style="font-size: 13px">
                          Удалить
                        </q-item-section>
                      </q-item>
                    </q-list>
                  </q-menu>
                </q-btn>
              </div>

              <!-- Загрузка файла (оптимистичное сообщение) -->
              <template v-if="msg._uploading">
                <div v-if="msg._previewUrl">
                  <q-img :src="msg._previewUrl" style="width:100%;max-height:200px;display:block" fit="cover" />
                  <div class="row items-center q-gutter-xs" style="padding:3px 8px 2px;opacity:0.7">
                    <q-spinner size="10px" color="grey-5" />
                    <span class="text-caption text-grey-6">{{ msg.file_name }}</span>
                  </div>
                </div>
                <div v-else class="row items-center q-gutter-xs">
                  <q-icon :name="isPdf(msg) ? 'picture_as_pdf' : 'upload'" size="16px" :color="isPdf(msg) ? 'red-5' : 'grey-5'" />
                  <span class="text-caption text-grey-6" style="word-break:break-word">{{ msg.file_name }}…</span>
                  <q-spinner size="12px" color="grey-5" />
                </div>
              </template>
              <template v-else-if="msg.message_type === 'image'">
                <a :href="msg.file_url" target="_blank" style="display: block; text-decoration: none; color: inherit">
                  <q-img
                    v-if="imgStreamUrl(msg)"
                    :src="imgStreamUrl(msg)"
                    style="width: 100%; max-height: clamp(160px, 35vh, 480px); display: block; cursor: pointer; min-height: 80px"
                    fit="contain"
                    spinner-color="grey-4"
                    spinner-size="28px"
                  />
                  <div class="row items-center q-gutter-xs" style="padding: 4px 10px 2px">
                    <q-icon name="image" size="14px" color="grey-6" />
                    <span class="text-caption text-grey-7 ellipsis" style="max-width: 220px">
                      {{ msg.file_name || 'Изображение' }}
                    </span>
                  </div>
                </a>
              </template>
              <template v-else-if="msg.message_type === 'file'">
                <div v-if="isPdf(msg) && pdfThumbnails[msg.id]" style="display:block">
                  <q-img
                    :src="pdfThumbnails[msg.id]"
                    style="width:100%;max-height:200px;display:block"
                    fit="contain"
                    spinner-color="grey-4"
                    spinner-size="20px"
                  />
                  <div class="row items-center q-gutter-xs" style="padding:3px 8px 2px">
                    <q-icon name="picture_as_pdf" size="14px" color="red-6" />
                    <a :href="msg.file_url" target="_blank" class="text-caption ellipsis" style="max-width:200px;color:inherit">{{ msg.file_name || 'Документ' }}</a>
                  </div>
                </div>
                <div v-else class="row items-center q-gutter-xs">
                  <q-icon :name="isPdf(msg) ? 'picture_as_pdf' : 'attach_file'" :size="isPdf(msg) ? '28px' : '18px'" :color="isPdf(msg) ? 'red-6' : 'grey-7'" />
                  <a :href="msg.file_url" target="_blank" class="text-body2 ellipsis" style="max-width:200px;color:inherit">{{ msg.file_name || 'Файл' }}</a>
                </div>
              </template>

              <template v-else>
                <div class="text-body2" style="white-space: pre-wrap; word-break: break-word">
                  {{ msg.content }}
                </div>
              </template>

              <!-- Inline-редактирование -->
              <div v-if="editingClientMsgId === msg.id" class="q-mt-xs">
                <q-input
                  v-model="editClientContent"
                  dense
                  outlined
                  autofocus
                  autogrow
                  hide-bottom-space
                  style="font-size: 13px"
                  @keydown.enter.exact.prevent="saveClientEdit"
                  @keydown.escape="cancelClientEdit"
                />
                <div class="row justify-end q-gutter-xs q-mt-xs">
                  <q-btn
                    flat
                    dense
                    no-caps
                    size="sm"
                    label="Отмена"
                    color="grey-6"
                    @click="cancelClientEdit"
                  />
                  <q-btn
                    unelevated
                    dense
                    no-caps
                    size="sm"
                    label="Сохранить"
                    color="green-7"
                    :loading="savingClientEdit"
                    @click="saveClientEdit"
                  />
                </div>
              </div>

              <!-- Нижняя строка: время -->
              <div
                class="row no-wrap items-center"
                :class="isOwn(msg) ? 'justify-end' : 'justify-start'"
                :style="msg.message_type === 'image' ? 'padding:2px 10px 6px;margin-top:0' : 'margin-top:4px'"
              >
                <span v-if="msg.is_edited" class="text-caption text-grey-5 q-mr-xs" style="font-size: 9px">изм.</span>
                <div class="text-caption" style="color: #888; font-size: 10px">
                  {{ formatTime(msg.created_at) }}
                </div>
              </div>
            </div>
          </div>
        </template>
      </template>
    </div>

    <!-- Прогресс загрузки файла -->
    <q-linear-progress
      v-if="uploadProgress > 0 && uploadProgress < 100"
      :value="uploadProgress / 100"
      color="green-6"
      style="flex-shrink: 0"
    />

    <!-- Панель ввода -->
    <div class="q-pa-sm bg-white" style="border-top: 1px solid #E0E0E0; flex-shrink: 0">
      <div class="row items-center q-gutter-xs">
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
        <input
          ref="fileInput"
          type="file"
          multiple
          class="hidden"
          @change="onFileSelected"
        >
        <q-input
          v-model="inputText"
          outlined
          dense
          autogrow
          hide-bottom-space
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
import { getPdfThumbnail } from 'src/composables/usePdfThumbnail'
import axios from 'axios'
import PwaInstallBanner from 'src/components/PwaInstallBanner.vue'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()
const mainToken = route.params.token  // UUID из URL /c/{token}
// Персональный токен гостя (создаётся при регистрации, сохраняется в localStorage)
const memberToken = localStorage.getItem(`chat_member_token_${mainToken}`) || null
const activeToken = memberToken || mainToken  // токен для API/WS

const { isConnected: wsConnected, connectClient, disconnect, sendMessage, sendTypingStart, sendTypingStop, sendRead, typingUsers, messages: wsMessages } = useChatWebSocket()

const chatTitle = ref('Чат с бюро')
const messages = ref([])
const inputText = ref('')
const pdfThumbnails = ref({})
const loadingMessages = ref(false)
const messagesEl = ref(null)
const fileInput = ref(null)
const clientName = localStorage.getItem('client_name') || 'Клиент'
const chatPageH = ref('100dvh')
const uploadProgress = ref(0)
const editingClientMsgId = ref(null)
const editClientContent = ref('')
const savingClientEdit = ref(false)

// Ключ хранения последнего прочитанного сообщения в localStorage
const _lastReadKey = `chat_last_read_${activeToken}`
const firstUnreadId = ref(null)

/** Бейдж иконки PWA для клиента */
function _updateClientAppBadge(msgList, lastReadId) {
  if (!('setAppBadge' in navigator)) return
  const unread = msgList.filter(m => m.id > lastReadId && !m.sender_guest_token).length
  if (unread > 0) {
    navigator.setAppBadge(unread).catch(() => {})
  } else {
    navigator.clearAppBadge().catch(() => {})
  }
}

function recalcChatH() {
  const vh = window.visualViewport?.height ?? window.innerHeight
  const header = document.querySelector('.q-header')
  const footer = document.querySelector('.q-footer')
  const headerH = header?.offsetHeight ?? 0
  const footerH = footer?.offsetHeight ?? 0
  chatPageH.value = Math.max(300, vh - headerH - footerH) + 'px'
  scrollToBottom()
}

const typingText = computed(() => {
  if (!typingUsers.value.length) return ''
  const names = typingUsers.value.map(u => u.name)
  if (names.length === 1) return `${names[0]} печатает…`
  return `${names.join(', ')} печатают…`
})

function isOwn(msg) {
  // Сравниваем по персональному токену (после регистрации) или основной ссылке
  if (memberToken) return msg.sender_guest_token === memberToken
  return msg.sender_guest_token === mainToken
}

function imgStreamUrl(msg) {
  if (msg._previewUrl) return msg._previewUrl
  if (!msg.yandex_path) return ''
  const path = msg.yandex_path.replace(/^disk:/, '')
  return `/api/v1/client-chat/${activeToken}/stream?yandex_path=${encodeURIComponent(path)}`
}

function isPdf(msg) {
  return msg.file_name?.toLowerCase().endsWith('.pdf')
}

async function loadPdfThumbnail(msg) {
  if (pdfThumbnails.value[msg.id]) return
  if (!isPdf(msg) || !msg.yandex_path) return
  const path = msg.yandex_path.replace(/^disk:/, '')
  const url = `/api/v1/client-chat/${activeToken}/stream?yandex_path=${encodeURIComponent(path)}`
  const thumb = await getPdfThumbnail(url, String(msg.id))
  if (thumb) pdfThumbnails.value[msg.id] = thumb
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

function scrollToFirstUnread() {
  nextTick(() => {
    const container = messagesEl.value
    if (!container) return
    if (firstUnreadId.value) {
      const divider = container.querySelector('[data-unread-divider]')
      const target = divider || container.querySelector(`[data-msg-id="${firstUnreadId.value}"]`)
      if (target) {
        const containerRect = container.getBoundingClientRect()
        const targetRect = target.getBoundingClientRect()
        container.scrollTop = container.scrollTop + (targetRect.top - containerRect.top) - 8
        return
      }
    }
    container.scrollTop = container.scrollHeight
  })
}

async function loadMessages() {
  loadingMessages.value = true
  try {
    const baseURL = window.location.origin
    const { data } = await axios.get(`${baseURL}/api/v1/client-chat/${activeToken}`)
    if (data.requires_registration && !memberToken) {
      // Не зарегистрирован и нет сохранённого токена → на страницу регистрации
      router.replace({ name: 'client-register', params: { token: mainToken } })
      return
    }
    chatTitle.value = data.title || 'Чат с бюро'
    messages.value = data.messages || []

    // Находим первое непрочитанное (localStorage-based, т.к. гость не имеет серверного трекинга)
    const lastRead = parseInt(localStorage.getItem(_lastReadKey) || '0', 10)
    const firstUnread = messages.value.find(m => m.id > lastRead && !m.sender_guest_token)
    firstUnreadId.value = firstUnread?.id || null
    // Показать бейдж иконки ДО сохранения прочитанного (чтоб увидеть счётчик)
    _updateClientAppBadge(messages.value, lastRead)
    scrollToFirstUnread()

    if (messages.value.length) {
      const lastId = messages.value[messages.value.length - 1].id
      sendRead(lastId)
      // Сохраняем последний id прочитанного для следующего визита → очищаем бейдж
      localStorage.setItem(_lastReadKey, String(lastId))
      if ('clearAppBadge' in navigator) navigator.clearAppBadge().catch(() => {})
    }
    messages.value
      .filter(m => isPdf(m) && m.yandex_path && !m._uploading)
      .forEach(m => loadPdfThumbnail(m))
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
  inputText.value = ''
  // Сообщение придёт обратно через WS broadcast (сервер отправляет всем, включая отправителя)
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

function startClientEdit(msg) {
  editingClientMsgId.value = msg.id
  editClientContent.value = msg.content || ''
}

function cancelClientEdit() {
  editingClientMsgId.value = null
  editClientContent.value = ''
}

async function saveClientEdit() {
  const text = editClientContent.value.trim()
  if (!text || !editingClientMsgId.value) return
  savingClientEdit.value = true
  try {
    const baseURL = window.location.origin
    const { data } = await axios.patch(
      `${baseURL}/api/v1/client-chat/${activeToken}/messages/${editingClientMsgId.value}`,
      { content: text, message_type: 'text' },
    )
    const idx = messages.value.findIndex(m => m.id === editingClientMsgId.value)
    if (idx !== -1) messages.value.splice(idx, 1, data)
    cancelClientEdit()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Ошибка редактирования' })
  } finally {
    savingClientEdit.value = false
  }
}

async function deleteClientMsg(msg) {
  // Клиент не имеет JWT — только локально скрываем (сервер не поддерживает delete без JWT)
  const idx = messages.value.findIndex(m => m.id === msg.id)
  if (idx !== -1) {
    messages.value[idx] = { ...messages.value[idx], is_deleted: true, content: '[Сообщение удалено]' }
  }
}

async function _uploadClientFile(file) {
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif']
  const msgType = imageExts.includes(ext) ? 'image' : 'file'
  const isPdfUpload = ext === 'pdf'
  const tempId = `temp_${Date.now()}_${Math.random()}`
  const previewUrl = msgType === 'image' ? URL.createObjectURL(file) : null
  messages.value.push({
    id: tempId,
    sender_guest_token: activeToken,
    sender_display_name: clientName || 'Вы',
    message_type: msgType,
    content: null,
    file_url: '',
    file_name: file.name,
    file_size: file.size,
    yandex_path: null,
    is_deleted: false,
    is_edited: false,
    created_at: new Date().toISOString(),
    _uploading: true,
    _previewUrl: previewUrl,
  })
  scrollToBottom()
  if (isPdfUpload) {
    getPdfThumbnail(file).then(thumb => {
      if (thumb) {
        const m = messages.value.find(m2 => m2.id === tempId)
        if (m) m._previewUrl = thumb
      }
    })
  }
  try {
    const baseURL = window.location.origin
    const formData = new FormData()
    formData.append('file', file)
    formData.append('message_type', msgType)
    const { data: savedMsg } = await axios.post(`${baseURL}/api/v1/client-chat/${activeToken}/files`, formData, {
      onUploadProgress: (e) => {
        uploadProgress.value = e.total ? Math.round((e.loaded / e.total) * 100) : 50
      },
    })
    const idx = messages.value.findIndex(m => m.id === tempId)
    if (idx !== -1) {
      const alreadyAdded = messages.value.some(m => m.id === savedMsg.id)
      alreadyAdded ? messages.value.splice(idx, 1) : messages.value.splice(idx, 1, savedMsg)
    }
  } catch {
    messages.value = messages.value.filter(m => m.id !== tempId)
    throw new Error(file.name)
  } finally {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
  }
}

async function onFileSelected(event) {
  const files = [...(event.target.files || [])]
  if (!files.length) return
  uploadProgress.value = 1
  const errors = []
  for (const file of files) {
    try { await _uploadClientFile(file) } catch { errors.push(file.name) }
  }
  uploadProgress.value = 0
  event.target.value = ''
  if (errors.length) $q.notify({ type: 'negative', message: `Ошибка загрузки: ${errors.join(', ')}` })
}

onMounted(async () => {
  recalcChatH()
  window.addEventListener('resize', recalcChatH)
  window.visualViewport?.addEventListener('resize', recalcChatH)
  await loadMessages()
  connectClient(activeToken, {
    onMessage: (msg) => {
      const exists = messages.value.some(m => m.id === msg.id)
      if (!exists) {
        messages.value.push(msg)
        scrollToBottom()
        if (isPdf(msg)) loadPdfThumbnail(msg)
        // Если новое сообщение от сотрудника — обновить бейдж иконки
        if (!msg.sender_guest_token && 'setAppBadge' in navigator) {
          const lastRead = parseInt(localStorage.getItem(_lastReadKey) || '0', 10)
          _updateClientAppBadge(messages.value, lastRead)
        }
      }
    },
  })
})

onUnmounted(() => {
  disconnect()
  window.removeEventListener('resize', recalcChatH)
  window.visualViewport?.removeEventListener('resize', recalcChatH)
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
.bubble-img-own {
  background: #E8F5E9;
  border-radius: 12px 12px 2px 12px;
  overflow: hidden;
  min-width: 160px;
  max-width: 280px;
}
.bubble-img-staff {
  background: #fff;
  border-radius: 12px 12px 12px 2px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
  min-width: 160px;
  max-width: 280px;
}
.hidden {
  display: none;
}
</style>
