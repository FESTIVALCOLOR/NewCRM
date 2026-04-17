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
    <!-- Шапка чата: ссылка и участники -->
    <div
      class="q-px-md q-py-xs bg-white"
      style="border-bottom: 1px solid #E0E0E0; flex-shrink: 0; min-height: 36px; display: flex; flex-wrap: nowrap; align-items: center; overflow: hidden"
    >
      <!-- Блок ссылки: flex: 1 1 0% + overflow:hidden гарантирует обрезку -->
      <div
        v-if="chatType === 'client' && clientLink"
        style="flex: 1 1 0%; min-width: 0; display: flex; flex-wrap: nowrap; align-items: center; overflow: hidden"
      >
        <q-icon
          name="link"
          size="14px"
          color="green-7"
          class="q-mr-xs"
          style="flex: 0 0 auto"
        />
        <span
          class="text-caption text-green-8"
          style="flex: 1 1 0%; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap"
        >
          {{ clientLink }}
        </span>
        <q-btn
          flat
          dense
          size="xs"
          icon="content_copy"
          color="green-7"
          style="flex: 0 0 auto; margin-left: 4px"
          @click="copyClientLink"
        >
          <q-tooltip>Копировать ссылку</q-tooltip>
        </q-btn>
      </div>
      <span v-else class="text-caption text-grey-6" style="flex: 1 1 0%; min-width: 0">
        {{ chatType === 'client' ? 'Чат с клиентом' : 'Чат сотрудников' }}
      </span>
      <!-- Кнопка участников: всегда справа, никогда не сжимается -->
      <q-btn
        flat
        dense
        size="xs"
        icon="people"
        color="grey-7"
        style="flex: 0 0 auto; margin-left: 4px"
        @click="showMembers = true"
      >
        <q-tooltip>Участники</q-tooltip>
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

    <!-- Прогресс загрузки файла -->
    <q-linear-progress
      v-if="uploadProgress > 0 && uploadProgress < 100"
      :value="uploadProgress / 100"
      color="blue-5"
      style="flex-shrink: 0"
    />

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

            <!-- Загрузка файла (оптимистичное сообщение) -->
            <template v-if="msg._uploading">
              <div class="row items-center q-gutter-xs">
                <q-spinner size="14px" color="grey-5" />
                <span class="text-caption text-grey-6" style="word-break: break-word">{{ msg.file_name }}…</span>
              </div>
            </template>
            <template v-else-if="msg.message_type === 'image'">
              <a :href="msg.file_url" target="_blank" style="display: block; text-decoration: none; color: inherit">
                <img
                  v-if="imgStreamUrl(msg)"
                  :src="imgStreamUrl(msg)"
                  style="max-width: 100%; max-height: 180px; border-radius: 6px; display: block; cursor: pointer"
                  @error="$event.target.style.display='none'"
                >
                <div class="row items-center q-gutter-xs q-mt-xs">
                  <q-icon name="image" size="14px" color="grey-6" />
                  <span class="text-caption text-grey-7 ellipsis" style="max-width: 180px; font-size: 11px">
                    {{ msg.file_name || 'Изображение' }}
                  </span>
                </div>
              </a>
            </template>
            <template v-else-if="msg.message_type === 'file'">
              <div class="row items-center q-gutter-xs">
                <q-icon name="attach_file" size="18px" />
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

            <!-- Редактирование сообщения -->
            <div v-if="editingMsgId === msg.id" class="q-mt-xs">
              <q-input
                v-model="editContent"
                dense
                outlined
                autofocus
                autogrow
                hide-bottom-space
                style="font-size: 13px"
                @keydown.enter.exact.prevent="saveEdit"
                @keydown.escape="cancelEdit"
              />
              <div class="row justify-end q-gutter-xs q-mt-xs">
                <q-btn
                  flat
                  dense
                  no-caps
                  size="sm"
                  label="Отмена"
                  color="grey-6"
                  @click="cancelEdit"
                />
                <q-btn
                  unelevated
                  dense
                  no-caps
                  size="sm"
                  label="Сохранить"
                  color="blue-6"
                  :loading="savingEdit"
                  @click="saveEdit"
                />
              </div>
            </div>

            <!-- Нижняя строка: время + меню -->
            <div class="row no-wrap items-center q-mt-xs" :class="isOwn(msg) ? 'justify-end' : 'justify-start'">
              <span v-if="msg.is_edited" class="text-caption text-grey-5 q-mr-xs" style="font-size: 9px">изм.</span>
              <div class="text-caption q-mr-xs" style="color: #888; font-size: 10px">
                {{ formatTime(msg.created_at) }}
              </div>
              <q-btn
                v-if="!msg.is_deleted"
                flat
                round
                dense
                size="xs"
                icon="more_vert"
                color="grey-5"
                style="margin: -2px -4px"
              >
                <q-menu auto-close>
                  <q-list dense style="min-width: 180px">
                    <q-item
                      v-if="isOwn(msg) && msg.message_type === 'text'"
                      clickable
                      @click="startEdit(msg)"
                    >
                      <q-item-section avatar>
                        <q-icon name="edit" size="16px" color="blue-6" />
                      </q-item-section>
                      <q-item-section>Редактировать</q-item-section>
                    </q-item>
                    <q-item
                      v-if="isOwn(msg)"
                      clickable
                      @click="deleteMsg(msg)"
                    >
                      <q-item-section avatar>
                        <q-icon name="delete_outline" size="16px" color="red-5" />
                      </q-item-section>
                      <q-item-section class="text-red-6">
                        Удалить
                      </q-item-section>
                    </q-item>
                    <q-item
                      v-if="chatType === 'employee' && clientChatId"
                      clickable
                      :disable="!!forwardingMsgId"
                      @click="forwardToClient(msg)"
                    >
                      <q-item-section avatar>
                        <q-icon name="forward" size="16px" color="blue-5" />
                      </q-item-section>
                      <q-item-section>Переслать клиенту</q-item-section>
                    </q-item>
                    <q-item
                      v-if="msg.yandex_path && chat && chat.crm_card_id"
                      clickable
                      @click="openCopyToCard(msg)"
                    >
                      <q-item-section avatar>
                        <q-icon name="drive_file_move" size="16px" color="green-6" />
                      </q-item-section>
                      <q-item-section>Скопировать в карточку</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-btn>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Панель ввода -->
    <div class="q-pa-sm bg-white" style="border-top: 1px solid #E0E0E0; flex-shrink: 0">
      <div class="row items-center q-gutter-xs">
        <q-btn
          flat
          round
          dense
          size="sm"
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
          style="display: none"
          @change="onFileSelected"
        >
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

    <!-- Диалог: скопировать файл в карточку -->
    <q-dialog v-model="showCopyToCard" persistent>
      <q-card style="min-width: 300px; max-width: 420px; width: 92vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-subtitle2">
            Скопировать в карточку
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
        <q-card-section class="q-pt-sm">
          <div class="text-caption text-grey-6 q-mb-sm">
            Файл будет скопирован в папку карточки на Яндекс.Диске и сохранён в выбранном поле.
          </div>
          <q-list dense>
            <template v-for="group in COPY_DESTINATIONS" :key="group.group">
              <q-item-label header class="text-caption text-weight-bold text-grey-7 q-px-none q-pt-sm q-pb-xs">
                {{ group.group }}
              </q-item-label>
              <q-item
                v-for="dest in group.items"
                :key="dest.value"
                clickable
                :active="selectedDestination === dest.value"
                active-class="bg-green-1 text-green-9"
                class="rounded-borders"
                style="min-height: 36px"
                @click="selectedDestination = dest.value"
              >
                <q-item-section avatar style="min-width: 28px">
                  <q-icon
                    :name="selectedDestination === dest.value ? 'radio_button_checked' : 'radio_button_unchecked'"
                    size="18px"
                    :color="selectedDestination === dest.value ? 'green-7' : 'grey-5'"
                  />
                </q-item-section>
                <q-item-section>{{ dest.label }}</q-item-section>
              </q-item>
            </template>
          </q-list>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn
            v-close-popup
            flat
            no-caps
            label="Отмена"
            color="grey-7"
          />
          <q-btn
            unelevated
            no-caps
            label="Скопировать"
            color="green-7"
            :disable="!selectedDestination"
            :loading="copyingToCard"
            @click="confirmCopyToCard"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог участников -->
    <q-dialog v-model="showMembers" @show="onMembersDialogOpen">
      <q-card style="min-width: 300px; max-width: 400px; width: 90vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            Участники
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

        <!-- Текущие участники -->
        <q-list dense>
          <q-item v-for="m in chatMembers" :key="m.id">
            <q-item-section avatar>
              <q-avatar
                :color="m.member_type === 'employee' ? 'blue-2' : 'green-2'"
                :text-color="m.member_type === 'employee' ? 'blue-9' : 'green-9'"
                icon="person"
                size="28px"
              />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ m.display_name || m.guest_name || `#${m.id}` }}</q-item-label>
              <q-item-label caption>
                {{ m.role_in_project || (m.member_type === 'employee' ? 'Сотрудник' : 'Клиент') }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn
                flat
                round
                dense
                size="xs"
                icon="close"
                color="red-4"
                :loading="removingMemberId === m.id"
                @click.stop="removeMember(m)"
              >
                <q-tooltip>Удалить из чата</q-tooltip>
              </q-btn>
            </q-item-section>
          </q-item>
          <q-item v-if="!chatMembers.length">
            <q-item-section>
              <q-item-label class="text-grey">
                Нет участников
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <!-- Секция добавления сотрудников карточки -->
        <template v-if="cardEmployees !== null">
          <q-separator class="q-mt-sm" />
          <q-card-section class="q-py-sm">
            <div class="text-body2 text-weight-medium text-blue-grey-7 q-mb-xs">
              Добавить в чат
            </div>
            <div v-if="loadingCardEmployees" class="text-center q-py-sm">
              <q-spinner size="20px" color="grey" />
            </div>
            <div v-else-if="!cardEmployees.length" class="text-caption text-grey-5 q-py-xs" style="font-style: italic">
              Все сотрудники карточки уже в чате
            </div>
            <q-list v-else dense>
              <q-item
                v-for="emp in cardEmployees"
                :key="emp.id"
                clickable
                class="rounded-borders"
                @click="addMemberToChat(emp)"
              >
                <q-item-section avatar>
                  <q-avatar color="grey-3" text-color="grey-8" icon="person_add" size="28px" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ emp.name }}</q-item-label>
                  <q-item-label caption>
                    {{ emp.role }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-spinner v-if="addingMemberId === emp.id" size="18px" color="blue-6" />
                  <q-icon v-else name="add_circle_outline" color="blue-6" size="20px" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </template>

        <q-card-actions align="right" class="q-pt-none">
          <q-btn
            v-close-popup
            flat
            no-caps
            label="Закрыть"
            color="grey-7"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
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
const uploadProgress = ref(0)
const showMembers = ref(false)
const chatMembers = ref([])
// null = секция не показывалась; [] = загружено, но все уже в чате
const cardEmployees = ref(null)
const loadingCardEmployees = ref(false)
const addingMemberId = ref(null)
const removingMemberId = ref(null)

// Редактирование сообщений
const editingMsgId = ref(null)
const editContent = ref('')
const savingEdit = ref(false)

// Удаление
const deletingMsgId = ref(null)

// Копирование в карточку
const showCopyToCard = ref(false)
const copyToCardMsg = ref(null)
const selectedDestination = ref(null)
const copyingToCard = ref(false)

const COPY_DESTINATIONS = [
  { group: 'Документы', items: [
    { label: 'Замер', value: 'measurement_yandex_path' },
    { label: 'ТЗ', value: 'tech_task_yandex_path' },
    { label: 'Фото-документация', value: 'photo_documentation_yandex_path' },
    { label: 'Референсы', value: 'references_yandex_path' },
  ] },
  { group: 'Акты', items: [
    { label: 'Акт планировочного', value: 'act_planning_yandex_path' },
    { label: 'Акт концептуального', value: 'act_concept_yandex_path' },
    { label: 'Акт финального', value: 'act_final_yandex_path' },
    { label: 'Информационное письмо', value: 'info_letter_yandex_path' },
  ] },
  { group: 'Договор', items: [
    { label: 'Договор', value: 'contract_file_yandex_path' },
    { label: 'Доп. соглашение', value: 'additional_agreement_yandex_path' },
  ] },
  { group: 'Оплаты', items: [
    { label: 'Чек аванса', value: 'advance_receipt_yandex_path' },
    { label: 'Чек доплаты', value: 'additional_receipt_yandex_path' },
    { label: 'Чек (3-й платёж)', value: 'third_receipt_yandex_path' },
  ] },
]

function recalcHeight() {
  // Двойной requestAnimationFrame — ждём стабилизации layout
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (!chatContainerEl.value) return
      const rect = chatContainerEl.value.getBoundingClientRect()
      const topOffset = Math.max(0, rect.top)
      // Учитываем нижнюю панель навигации
      const footer = document.querySelector('.q-footer')
      const footerH = footer ? footer.offsetHeight : 0
      const vh = window.visualViewport?.height ?? window.innerHeight
      const h = Math.max(320, vh - topOffset - footerH - 4)
      containerHeight.value = h + 'px'
    })
  })
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

function imgStreamUrl(msg) {
  if (!msg.yandex_path) return ''
  const path = msg.yandex_path.replace(/^disk:/, '')
  const token = localStorage.getItem('access_token') || ''
  return `/api/v1/files/stream?yandex_path=${encodeURIComponent(path)}&token=${encodeURIComponent(token)}`
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
    chatMembers.value = data.members || []
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
        onMessageUpdated: (msg) => {
          const idx = messages.value.findIndex(m => m.id === msg.id)
          if (idx !== -1) messages.value.splice(idx, 1, msg)
        },
        onMessageDeleted: (msgId) => {
          const idx = messages.value.findIndex(m => m.id === msgId)
          if (idx !== -1) {
            messages.value[idx] = { ...messages.value[idx], is_deleted: true, content: '[Сообщение удалено]' }
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

// Открытие диалога участников — сразу грузим сотрудников карточки
async function onMembersDialogOpen() {
  if (!props.cardId || !chat.value) return
  cardEmployees.value = null
  loadingCardEmployees.value = true
  try {
    const { data } = await api.get(`/api/v1/crm/cards/${props.cardId}`)
    const emps = new Map()
    // Менеджеры и другие роли из полей карточки
    const roles = [
      { id: data.senior_manager_id, name: data.senior_manager_name, role: 'Старший менеджер' },
      { id: data.sdp_id, name: data.sdp_name, role: 'СДП' },
      { id: data.gap_id, name: data.gap_name, role: 'ГАП' },
      { id: data.manager_id, name: data.manager_name, role: 'Менеджер' },
      { id: data.surveyor_id, name: data.surveyor_name, role: 'Замерщик' },
    ]
    for (const r of roles) {
      if (r.id && r.name) emps.set(r.id, { name: r.name, role: r.role })
    }
    // Исполнители этапов
    for (const se of (data.stage_executors || [])) {
      if (se.executor_id && se.executor_name) {
        emps.set(se.executor_id, { name: se.executor_name, role: se.stage_name || 'Исполнитель' })
      }
    }
    // Исключаем тех, кто уже в чате
    const memberIds = new Set(chatMembers.value.filter(m => m.employee_id).map(m => m.employee_id))
    cardEmployees.value = [...emps.entries()]
      .filter(([id]) => !memberIds.has(id))
      .map(([id, info]) => ({ id, name: info.name, role: info.role }))
  } catch {
    cardEmployees.value = []
  } finally {
    loadingCardEmployees.value = false
  }
}

async function addMemberToChat(emp) {
  if (addingMemberId.value || !chat.value) return
  addingMemberId.value = emp.id
  try {
    await api.post(`/api/v1/chats/${chat.value.id}/members`, { employee_id: emp.id })
    // Обновляем список участников чата
    const { data } = await api.get(`/api/v1/chats/${chat.value.id}`)
    chatMembers.value = data.members || []
    // Убираем из списка доступных
    cardEmployees.value = cardEmployees.value.filter(e => e.id !== emp.id)
    $q.notify({ type: 'positive', message: `${emp.name} добавлен в чат` })
  } catch (e) {
    const msg = e.response?.data?.detail || 'Ошибка добавления'
    $q.notify({ type: 'negative', message: String(msg) })
  } finally {
    addingMemberId.value = null
  }
}

async function removeMember(m) {
  if (removingMemberId.value || !chat.value) return
  removingMemberId.value = m.id
  try {
    await api.delete(`/api/v1/chats/${chat.value.id}/members/${m.id}`)
    chatMembers.value = chatMembers.value.filter(mb => mb.id !== m.id)
    $q.notify({ type: 'positive', message: `${m.display_name || 'Участник'} удалён из чата` })
  } catch (e) {
    const msg = e.response?.data?.detail || 'Ошибка удаления'
    $q.notify({ type: 'negative', message: String(msg) })
  } finally {
    removingMemberId.value = null
  }
}

async function forwardToClient(msg) {
  if (!clientChatId.value || forwardingMsgId.value) return
  forwardingMsgId.value = msg.id
  try {
    await api.post(`/api/v1/chats/${chat.value.id}/forward/${clientChatId.value}`, { msg_id: msg.id })
    $q.notify({ type: 'positive', message: 'Переслано в чат клиента' })
  } catch (e) {
    const raw = e.response?.data?.detail
    const message = Array.isArray(raw) ? raw.map(d => d.msg || String(d)).join('; ') : (raw || 'Ошибка пересылки')
    $q.notify({ type: 'negative', message: String(message) })
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

// ── Edit ──────────────────────────────────────────────────────────────────
function startEdit(msg) {
  editingMsgId.value = msg.id
  editContent.value = msg.content || ''
}

function cancelEdit() {
  editingMsgId.value = null
  editContent.value = ''
}

async function saveEdit() {
  if (!editContent.value.trim() || !chat.value) return
  savingEdit.value = true
  try {
    const { data: updated } = await api.patch(
      `/api/v1/chats/${chat.value.id}/messages/${editingMsgId.value}`,
      { content: editContent.value.trim() },
    )
    const idx = messages.value.findIndex(m => m.id === editingMsgId.value)
    if (idx !== -1) messages.value.splice(idx, 1, updated)
    cancelEdit()
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка редактирования' })
  } finally {
    savingEdit.value = false
  }
}

// ── Delete ────────────────────────────────────────────────────────────────
async function deleteMsg(msg) {
  if (deletingMsgId.value || !chat.value) return
  deletingMsgId.value = msg.id
  try {
    await api.delete(`/api/v1/chats/${chat.value.id}/messages/${msg.id}`)
    const idx = messages.value.findIndex(m => m.id === msg.id)
    if (idx !== -1) {
      messages.value[idx] = { ...messages.value[idx], is_deleted: true, content: '[Сообщение удалено]' }
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка удаления' })
  } finally {
    deletingMsgId.value = null
  }
}

// ── Copy to card ──────────────────────────────────────────────────────────
function openCopyToCard(msg) {
  copyToCardMsg.value = msg
  selectedDestination.value = null
  showCopyToCard.value = true
}

async function confirmCopyToCard() {
  if (!selectedDestination.value || !copyToCardMsg.value || !chat.value?.crm_card_id) return
  copyingToCard.value = true
  try {
    await api.post(
      `/api/v1/chats/${chat.value.id}/messages/${copyToCardMsg.value.id}/copy-to-card`,
      { crm_card_id: chat.value.crm_card_id, destination: selectedDestination.value },
    )
    $q.notify({ type: 'positive', message: 'Файл скопирован в карточку' })
    showCopyToCard.value = false
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка копирования' })
  } finally {
    copyingToCard.value = false
  }
}

// ── File upload ───────────────────────────────────────────────────────────
function pickFile() {
  fileInput.value?.click()
}

async function _uploadSingleFile(file) {
  if (!chat.value) return
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif']
  const msgType = imageExts.includes(ext) ? 'image' : 'file'

  const tempId = `temp_${Date.now()}_${Math.random()}`
  messages.value.push({
    id: tempId,
    sender_employee_id: authStore.employee?.id,
    sender_display_name: authStore.employee?.name || 'Вы',
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
  })
  scrollToBottom()

  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('message_type', msgType)
    const { data: savedMsg } = await api.post(`/api/v1/chats/${chat.value.id}/files`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
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
  }
}

async function onFileSelected(event) {
  const files = [...(event.target.files || [])]
  if (!files.length || !chat.value) return
  uploadProgress.value = 1
  const errors = []
  for (const file of files) {
    try {
      await _uploadSingleFile(file)
    } catch {
      errors.push(file.name)
    }
  }
  uploadProgress.value = 0
  event.target.value = ''
  if (errors.length) {
    $q.notify({ type: 'negative', message: `Ошибка загрузки: ${errors.join(', ')}` })
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
    window.visualViewport?.addEventListener('resize', recalcHeight)
    document.addEventListener('scroll', recalcHeight, true)
  })
})

// Пересчитываем высоту когда чат загружается
watch(chat, (newVal) => {
  if (!newVal) return
  nextTick(recalcHeight)
  setTimeout(recalcHeight, 150)
  setTimeout(recalcHeight, 500)
})

onUnmounted(() => {
  disconnect()
  window.removeEventListener('resize', recalcHeight)
  window.visualViewport?.removeEventListener('resize', recalcHeight)
  document.removeEventListener('scroll', recalcHeight, true)
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
