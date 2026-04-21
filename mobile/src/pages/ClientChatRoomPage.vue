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
        <div class="text-subtitle2 text-weight-bold" style="word-break: break-word; line-height: 1.3">
          {{ chatTitle }}
        </div>
        <div v-if="typingText" class="text-caption text-grey ellipsis">
          {{ typingText }}
        </div>
        <div v-else class="text-caption text-grey">
          <q-icon name="people" size="10px" class="q-mr-xs" />{{ membersCount }} участников
        </div>
      </div>

      <!-- Кнопка: ссылка клиенту (только при наличии прав) -->
      <q-btn
        v-if="canManage && clientToken"
        flat
        round
        dense
        icon="link"
        @click="showInviteMenu = true"
      >
        <q-tooltip>Ссылка для клиента</q-tooltip>
      </q-btn>

      <!-- Кнопка: отправить скрипт -->
      <q-btn
        v-if="canScript"
        flat
        round
        dense
        icon="text_snippet"
        @click="showScriptDialog = true"
      >
        <q-tooltip>Отправить скрипт</q-tooltip>
      </q-btn>

      <!-- Кнопка: участники -->
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
          Нет сообщений
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
            <!-- Системные -->
            <div v-if="msg.message_type === 'system'" class="text-center full-width">
              <q-chip dense size="sm" color="grey-3" text-color="grey-7">
                {{ msg.content }}
              </q-chip>
            </div>

            <div
              v-else
              :class="isOwn(msg) ? 'bubble-own' : 'bubble-other'"
              style="max-width: 75%"
            >
              <!-- Верхняя строка: имя + меню -->
              <div class="row no-wrap items-center justify-between q-mb-xs" style="min-height: 16px; gap: 2px">
                <div
                  class="text-caption text-weight-bold"
                  :style="{ color: isOwn(msg) ? '#999' : (isGuest(msg) ? '#2E7D32' : '#1565C0') }"
                  style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: default"
                >
                  {{ msg.sender_display_name }}
                  <q-chip
                    v-if="isGuest(msg)"
                    dense
                    size="xs"
                    color="green-2"
                    text-color="green-9"
                  >
                    клиент
                  </q-chip>
                  <!-- Телефон клиента (только при наличии прав) -->
                  <q-tooltip
                    v-if="isGuest(msg) && canShowPhone && guestPhone(msg)"
                    anchor="top middle"
                    self="bottom middle"
                  >
                    <q-icon name="phone" size="12px" class="q-mr-xs" />{{ guestPhone(msg) }}
                  </q-tooltip>
                </div>
                <!-- 3-точечное меню для ВСЕХ сообщений (не только своих) -->
                <q-btn
                  v-if="!msg.is_deleted && !msg._uploading"
                  flat
                  round
                  dense
                  size="xs"
                  icon="more_vert"
                  color="grey-6"
                  style="margin: -4px -6px -2px 2px; flex-shrink: 0"
                >
                  <q-menu auto-close>
                    <q-list dense style="min-width: 150px; font-size: 12px">
                      <q-item
                        v-if="isOwn(msg) && msg.message_type === 'text'"
                        clickable
                        dense
                        @click="startEdit(msg)"
                      >
                        <q-item-section avatar style="min-width: 28px">
                          <q-icon name="edit" size="14px" color="grey-8" />
                        </q-item-section>
                        <q-item-section style="font-size: 12px">
                          Редактировать
                        </q-item-section>
                      </q-item>
                      <q-item
                        v-if="isOwn(msg)"
                        clickable
                        dense
                        @click="deleteMsg(msg)"
                      >
                        <q-item-section avatar style="min-width: 28px">
                          <q-icon name="delete_outline" size="14px" color="grey-8" />
                        </q-item-section>
                        <q-item-section class="text-red-7" style="font-size: 12px">
                          Удалить
                        </q-item-section>
                      </q-item>
                      <q-item
                        clickable
                        dense
                        @click="openForwardDialog(msg)"
                      >
                        <q-item-section avatar style="min-width: 28px">
                          <q-icon name="forward" size="14px" color="grey-8" />
                        </q-item-section>
                        <q-item-section style="font-size: 12px">
                          Переслать
                        </q-item-section>
                      </q-item>
                    </q-list>
                  </q-menu>
                </q-btn>
              </div>

              <template v-if="msg.message_type === 'image'">
                <a :href="msg.file_url" target="_blank" style="display: block; text-decoration: none; color: inherit">
                  <q-img
                    v-if="imgStreamUrl(msg)"
                    :src="imgStreamUrl(msg)"
                    style="max-width: 220px; border-radius: 6px; cursor: pointer"
                    :ratio="4/3"
                    fit="contain"
                    spinner-color="grey-4"
                    spinner-size="24px"
                  />
                  <div class="row items-center q-gutter-xs q-mt-xs">
                    <q-icon name="image" size="16px" color="grey-6" />
                    <span class="text-caption text-grey-7 ellipsis" style="max-width: 200px">
                      {{ msg.file_name || 'Изображение' }}
                    </span>
                  </div>
                </a>
              </template>
              <template v-else-if="msg.message_type === 'file'">
                <div class="row items-center q-gutter-xs">
                  <q-icon name="attach_file" size="20px" />
                  <a :href="msg.file_url" target="_blank" class="text-body2 ellipsis" style="max-width: 200px; color: inherit">
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

              <div class="row no-wrap items-center q-mt-xs" :class="isOwn(msg) ? 'justify-end' : 'justify-start'" style="color: #888; font-size: 10px">
                <span v-if="msg.is_edited" class="text-caption text-grey-5 q-mr-xs" style="font-size: 9px">изм.</span>
                <span class="text-caption">{{ formatTime(msg.created_at) }}</span>
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
        <input ref="fileInput" type="file" class="hidden" @change="onFileSelected">
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
          icon="send"
          color="green"
          :disable="!inputText.trim()"
          @click="sendText"
        />
      </div>
    </div>

    <!-- Диалог: переслать сообщение -->
    <q-dialog v-model="showForwardDialog">
      <q-card style="min-width: 300px; max-width: 400px; width: 90vw">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-subtitle2">
            Переслать сообщение
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
        <q-card-section class="q-py-sm q-px-md">
          <q-input
            v-model="forwardSearchQuery"
            dense
            outlined
            placeholder="Поиск чата…"
            clearable
            clear-icon="close"
          >
            <template #prepend>
              <q-icon name="search" size="16px" />
            </template>
          </q-input>
        </q-card-section>
        <q-separator />
        <q-card-section style="max-height: 50vh; overflow-y: auto; padding: 0">
          <div v-if="loadingForwardChats" class="text-center q-pa-md">
            <q-spinner size="24px" color="grey" />
          </div>
          <q-list v-else separator>
            <q-item
              v-for="c in filteredForwardChats"
              :key="c.id"
              clickable
              :active="selectedForwardChatId === c.id"
              active-class="bg-blue-1"
              @click="selectedForwardChatId = c.id"
            >
              <q-item-section>
                <q-item-label>{{ c.title || `Чат #${c.id}` }}</q-item-label>
                <q-item-label caption>
                  {{ c.chat_type === 'client' ? 'Чат с клиентом' : 'Чат сотрудников' }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon v-if="selectedForwardChatId === c.id" name="check_circle" color="blue-6" />
              </q-item-section>
            </q-item>
            <div v-if="!loadingForwardChats && !filteredForwardChats.length" class="text-center text-grey q-pa-md">
              {{ forwardSearchQuery ? 'Ничего не найдено' : 'Нет доступных чатов' }}
            </div>
          </q-list>
        </q-card-section>
        <q-card-actions align="right" class="q-pt-sm">
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
            label="Переслать"
            color="blue-6"
            :disable="!selectedForwardChatId"
            :loading="sendingForward"
            @click="doForward"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Диалог скрипта -->
    <q-dialog v-model="showScriptDialog" @show="loadScripts">
      <q-card style="min-width: 380px; max-width: 520px">
        <q-card-section class="row items-center">
          <div class="text-h6">
            Отправить скрипт
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

        <!-- Выбор скрипта -->
        <q-card-section v-if="!selectedScript" class="q-pb-sm">
          <div v-if="loadingScripts" class="text-center q-pa-md">
            <q-spinner size="24px" color="primary" />
          </div>
          <q-list v-else separator>
            <q-item
              v-for="s in scripts"
              :key="s.id"
              v-ripple
              clickable
              @click="selectScript(s)"
            >
              <q-item-section>
                <q-item-label>{{ s.name || s.script_type }}</q-item-label>
                <q-item-label caption lines="2">
                  {{ s.message_template?.substring(0, 80) }}…
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon name="chevron_right" color="grey" />
              </q-item-section>
            </q-item>
            <q-item v-if="!scripts.length">
              <q-item-section>
                <q-item-label class="text-grey">
                  Скрипты не найдены
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <!-- Редактирование и отправка выбранного скрипта -->
        <q-card-section v-else class="q-pt-sm">
          <div class="text-caption text-grey q-mb-sm">
            {{ selectedScript.name || selectedScript.script_type }}
          </div>
          <q-input
            v-model="scriptText"
            type="textarea"
            outlined
            label="Текст (можно отредактировать)"
            rows="6"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn
            v-if="selectedScript"
            flat
            label="Назад"
            @click="selectedScript = null"
          />
          <q-btn v-close-popup flat label="Отмена" />
          <q-btn
            v-if="selectedScript"
            color="primary"
            label="Отправить"
            :disable="!scriptText.trim()"
            @click="sendScript"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Меню ссылок -->
    <q-dialog v-model="showInviteMenu">
      <q-card style="min-width: 340px">
        <q-card-section class="row items-center">
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
        <q-separator />
        <q-card-section>
          <div class="text-body2 q-mb-md">
            Основная ссылка:
          </div>
          <q-input :model-value="clientLink" readonly outlined dense>
            <template #append>
              <q-btn flat dense icon="content_copy" @click="copyText(clientLink)" />
            </template>
          </q-input>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn v-close-popup flat label="Закрыть" />
          <q-btn color="primary" label="Создать доп. ссылку" @click="createExtraLink" />
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

        <q-list dense>
          <q-item v-for="m in members" :key="m.id">
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
          <q-item v-if="!members.length">
            <q-item-section>
              <q-item-label class="text-grey">
                Нет участников
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>

        <template v-if="availableEmployees !== null">
          <q-separator class="q-mt-sm" />
          <q-card-section class="q-py-sm">
            <div class="text-body2 text-weight-medium text-blue-grey-7 q-mb-xs">
              Добавить в чат
            </div>
            <div v-if="loadingAvailableEmps" class="text-center q-py-sm">
              <q-spinner size="20px" color="grey" />
            </div>
            <div v-else-if="!availableEmployees.length" class="text-caption text-grey-5 q-py-xs" style="font-style: italic">
              Все сотрудники карточки уже в чате
            </div>
            <q-list v-else dense>
              <q-item
                v-for="emp in availableEmployees"
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
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { api } from 'src/boot/axios'
import { useChatWebSocket } from 'src/composables/useChatWebSocket'
import { usePermission } from 'src/composables/usePermission'
import { useAuthStore } from 'src/stores/auth'
import { useChatUnreadStore } from 'src/stores/chatUnread'
import { useQuasar } from 'quasar'

const route = useRoute()
const authStore = useAuthStore()
const chatUnreadStore = useChatUnreadStore()
const { can } = usePermission()
const $q = useQuasar()
const chatId = Number(route.params.chatId)

const { isConnected, connectEmployee, disconnect, sendMessage, sendTypingStart, sendTypingStop, sendRead, typingUsers } = useChatWebSocket()

const chatTitle = ref('Чат с клиентом')
const messages = ref([])
const members = ref([])
const inputText = ref('')
const loadingMessages = ref(false)
const messagesEl = ref(null)
const fileInput = ref(null)
const clientToken = ref('')
const showScriptDialog = ref(false)
const showInviteMenu = ref(false)
const showMembers = ref(false)
const scriptText = ref('')
const chatPageH = ref('100dvh')
const uploadProgress = ref(0)
const availableEmployees = ref(null)
const loadingAvailableEmps = ref(false)
const addingMemberId = ref(null)
const removingMemberId = ref(null)
const chatCrmCardId = ref(null)
const editingMsgId = ref(null)
const editContent = ref('')
const savingEdit = ref(false)
// Пересылка сообщений
const showForwardDialog = ref(false)
const forwardingMsg = ref(null)
const forwardTargetChats = ref([])
const loadingForwardChats = ref(false)
const selectedForwardChatId = ref(null)
const sendingForward = ref(false)
const forwardSearchQuery = ref('')
const filteredForwardChats = computed(() => {
  const q = forwardSearchQuery.value.trim().toLowerCase()
  if (!q) return forwardTargetChats.value
  return forwardTargetChats.value.filter(c => (c.title || `Чат #${c.id}`).toLowerCase().includes(q))
})

// Первое непрочитанное сообщение
const firstUnreadId = ref(null)

function recalcChatH() {
  const vh = window.visualViewport?.height ?? window.innerHeight
  const header = document.querySelector('.q-header')
  const footer = document.querySelector('.q-footer')
  const headerH = header?.offsetHeight ?? 0
  const footerH = footer?.offsetHeight ?? 0
  chatPageH.value = Math.max(300, vh - headerH - footerH) + 'px'
  scrollToBottom()
}

const canManage = computed(() => can('chat.client.manage'))
const canScript = computed(() => can('chat.client.send_script'))
const canShowPhone = computed(() => can('chat.client.show_phone'))

// Карта guest_name → phone из списка участников (token не передаётся в ответе API)
const guestPhoneMap = computed(() => {
  const map = {}
  for (const m of members.value) {
    if (!m.employee_id && m.guest_phone && m.guest_name) {
      map[m.guest_name] = m.guest_phone
    }
  }
  return map
})

function guestPhone(msg) {
  if (!isGuest(msg) || !msg.sender_display_name) return ''
  return guestPhoneMap.value[msg.sender_display_name] || ''
}
const membersCount = computed(() => members.value.length)

const scripts = ref([])
const loadingScripts = ref(false)
const selectedScript = ref(null)
const cardData = ref(null)

const clientLink = computed(() => {
  if (!clientToken.value) return ''
  return `${window.location.origin}/c/${clientToken.value}`
})

const typingText = computed(() => {
  if (!typingUsers.value.length) return ''
  const names = typingUsers.value.map(u => u.name)
  if (names.length === 1) return `${names[0]} печатает…`
  return `${names.join(', ')} печатают…`
})

function isOwn(msg) {
  const myId = authStore.user?.id
  if (!myId) return false
  return Number(msg.sender_employee_id) === Number(myId)
}

function startEdit(msg) {
  editingMsgId.value = msg.id
  editContent.value = msg.content
}

function cancelEdit() {
  editingMsgId.value = null
  editContent.value = ''
}

async function saveEdit() {
  if (!editContent.value.trim() || !editingMsgId.value) return
  savingEdit.value = true
  try {
    await api.patch(`/api/v1/chats/${chatId}/messages/${editingMsgId.value}`, { content: editContent.value.trim() })
    const msg = messages.value.find(m => m.id === editingMsgId.value)
    if (msg) {
      msg.content = editContent.value.trim()
      msg.is_edited = true
    }
    cancelEdit()
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка редактирования' })
  } finally {
    savingEdit.value = false
  }
}

async function openForwardDialog(msg) {
  forwardingMsg.value = msg
  selectedForwardChatId.value = null
  forwardSearchQuery.value = ''
  showForwardDialog.value = true
  loadingForwardChats.value = true
  try {
    const { data } = await api.get('/api/v1/chats/')
    forwardTargetChats.value = (Array.isArray(data) ? data : (data.items || []))
      .filter(c => c.id !== chatId)
  } catch {
    forwardTargetChats.value = []
  } finally {
    loadingForwardChats.value = false
  }
}

async function doForward() {
  if (!forwardingMsg.value || !selectedForwardChatId.value) return
  sendingForward.value = true
  try {
    await api.post(`/api/v1/chats/${chatId}/forward/${selectedForwardChatId.value}`, { msg_id: forwardingMsg.value.id })
    $q.notify({ type: 'positive', message: 'Переслано' })
    showForwardDialog.value = false
  } catch (e) {
    const raw = e.response?.data?.detail
    const message = Array.isArray(raw) ? raw.map(d => d.msg || String(d)).join('; ') : (raw || 'Ошибка пересылки')
    $q.notify({ type: 'negative', message: String(message) })
  } finally {
    sendingForward.value = false
  }
}

async function deleteMsg(msg) {
  try {
    await api.delete(`/api/v1/chats/${chatId}/messages/${msg.id}`)
    const m = messages.value.find(m => m.id === msg.id)
    if (m) {
      m.is_deleted = true
      m.content = 'Сообщение удалено'
    }
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка удаления' })
  }
}

function imgStreamUrl(msg) {
  if (!msg.yandex_path) return ''
  const path = msg.yandex_path.replace(/^disk:/, '')
  const token = localStorage.getItem('access_token') || ''
  return `/api/v1/files/stream?yandex_path=${encodeURIComponent(path)}&token=${encodeURIComponent(token)}`
}

function isGuest(msg) {
  return !!msg.sender_guest_token
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
    const { data } = await api.get(`/api/v1/chats/${chatId}`)
    chatTitle.value = data.title || `Чат #${chatId}`
    messages.value = data.messages || []
    members.value = data.members || []
    clientToken.value = data.client_access_token || ''
    firstUnreadId.value = data.first_unread_message_id || null
    scrollToFirstUnread()

    if (messages.value.length) {
      sendRead(messages.value[messages.value.length - 1].id)
    }
    chatUnreadStore.markChatRead(chatId)

    chatCrmCardId.value = data.crm_card_id || null

    // Загружаем данные карточки для подстановки переменных в скрипты
    if (data.crm_card_id) {
      loadCardData(data.crm_card_id)
    }
  } catch (e) {
    console.error('[ClientChatRoom] Ошибка:', e)
  } finally {
    loadingMessages.value = false
  }
}

async function loadCardData(cardId) {
  try {
    const { data } = await api.get(`/api/v1/crm/cards/${cardId}`)
    cardData.value = data
  } catch {
    // Не критично — переменные останутся незаполненными
  }
}

function fillScriptVars(template) {
  if (!template) return ''
  const d = cardData.value || {}
  const clientFullName = d.client_name || ''
  const clientFirstName = clientFullName.split(' ').filter(Boolean)[1] || clientFullName.split(' ')[0] || ''
  const vars = {
    client_name: clientFullName,
    client_first_name: clientFirstName,
    address: d.address || '',
    area: d.area ? `${d.area} м²` : '',
    contract_number: d.contract_number || '',
    deadline: d.deadline || '',
    deadline_date: d.deadline || '',
    senior_manager: d.senior_manager_name || '',
    senior_manager_username: d.senior_manager_name || '',
    manager_name: d.manager_name || '',
    manager_username: d.manager_name || '',
    sdp: d.sdp_name || '',
    sdp_username: d.sdp_name || '',
    sender_name: authStore.employee?.full_name || '',
    role_name: authStore.employee?.position || '',
  }
  // Обрабатываем построчно: строки с незаполненными переменными убираем
  return template.split('\n').map(line => {
    const varMatches = [...line.matchAll(/\{(\w+)\}/g)]
    if (!varMatches.length) return line
    let hasEmptyVar = false
    const substituted = line.replace(/\{(\w+)\}/g, (match, key) => {
      if (key in vars) {
        if (!vars[key]) hasEmptyVar = true
        return vars[key]
      }
      return match // Неизвестная переменная — оставляем
    })
    return hasEmptyVar ? null : substituted
  }).filter(line => line !== null).join('\n').trim()
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
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки файла' })
  } finally {
    uploadProgress.value = 0
    event.target.value = ''
  }
}

async function loadScripts() {
  if (scripts.value.length) return
  loadingScripts.value = true
  try {
    const { data } = await api.get('/api/v1/messenger/scripts')
    scripts.value = Array.isArray(data) ? data : (data.items || [])
  } catch (e) {
    console.error('[ClientChatRoom] Ошибка загрузки скриптов:', e)
  } finally {
    loadingScripts.value = false
  }
}

function selectScript(s) {
  selectedScript.value = s
  scriptText.value = fillScriptVars(s.message_template || '')
}

async function sendScript() {
  const text = scriptText.value.trim()
  if (!text) return
  try {
    const { data } = await api.post(`/api/v1/chats/${chatId}/messages`, {
      content: text,
      message_type: 'text',
    })
    // Добавляем сообщение сразу из ответа REST (не ждём WS)
    if (data && data.id) {
      const exists = messages.value.some(m => m.id === data.id)
      if (!exists) {
        messages.value.push(data)
        scrollToBottom()
      }
    }
    scriptText.value = ''
    selectedScript.value = null
    showScriptDialog.value = false
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Ошибка отправки скрипта' })
  }
}

async function createExtraLink() {
  try {
    const { data } = await api.post(`/api/v1/chats/${chatId}/invite-links`)
    const token = data.access_token
    const link = `${window.location.origin}/c/${token}`
    copyText(link)
    $q.notify({ type: 'positive', message: 'Новая ссылка скопирована' })
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Ошибка создания ссылки' })
  }
}

function copyText(text) {
  navigator.clipboard.writeText(text).catch(() => { })
}

async function onMembersDialogOpen() {
  if (!chatCrmCardId.value) return
  availableEmployees.value = null
  loadingAvailableEmps.value = true
  try {
    const { data } = await api.get(`/api/v1/crm/cards/${chatCrmCardId.value}`)
    const emps = new Map()
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
    for (const se of (data.stage_executors || [])) {
      if (se.executor_id && se.executor_name) {
        emps.set(se.executor_id, { name: se.executor_name, role: se.stage_name || 'Исполнитель' })
      }
    }
    const memberIds = new Set(members.value.filter(m => m.employee_id).map(m => m.employee_id))
    availableEmployees.value = [...emps.entries()]
      .filter(([id]) => !memberIds.has(id))
      .map(([id, info]) => ({ id, name: info.name, role: info.role }))
  } catch {
    availableEmployees.value = []
  } finally {
    loadingAvailableEmps.value = false
  }
}

async function addMemberToChat(emp) {
  if (addingMemberId.value) return
  addingMemberId.value = emp.id
  try {
    await api.post(`/api/v1/chats/${chatId}/members`, { employee_id: emp.id })
    const { data } = await api.get(`/api/v1/chats/${chatId}`)
    members.value = data.members || []
    availableEmployees.value = availableEmployees.value.filter(e => e.id !== emp.id)
    $q.notify({ type: 'positive', message: `${emp.name} добавлен в чат` })
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка добавления' })
  } finally {
    addingMemberId.value = null
  }
}

async function removeMember(m) {
  if (removingMemberId.value) return
  removingMemberId.value = m.id
  try {
    await api.delete(`/api/v1/chats/${chatId}/members/${m.id}`)
    members.value = members.value.filter(mb => mb.id !== m.id)
    $q.notify({ type: 'positive', message: `${m.display_name || 'Участник'} удалён из чата` })
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Ошибка удаления' })
  } finally {
    removingMemberId.value = null
  }
}

onMounted(() => {
  recalcChatH()
  window.addEventListener('resize', recalcChatH)
  window.visualViewport?.addEventListener('resize', recalcChatH)
  loadMessages()
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
