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

          <div
            v-else
            :class="isOwn(msg) ? 'bubble-own' : 'bubble-other'"
            style="max-width: 75%"
          >
            <div
              v-if="!isOwn(msg)"
              class="text-caption text-weight-bold q-mb-xs"
              :style="{ color: isGuest(msg) ? '#2E7D32' : '#1565C0' }"
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
            </div>

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

            <div class="text-caption q-mt-xs" :class="isOwn(msg) ? 'text-right' : 'text-left'" style="color: #888; font-size: 10px">
              {{ formatTime(msg.created_at) }}
            </div>
          </div>
        </div>
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
            <div class="text-caption text-grey-6 q-mb-xs">
              Сотрудники карточки — не в чате
            </div>
            <div v-if="loadingAvailableEmps" class="text-center q-py-sm">
              <q-spinner size="20px" color="grey" />
            </div>
            <div v-else-if="!availableEmployees.length" class="text-caption text-grey q-py-xs">
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
import { useQuasar } from 'quasar'

const route = useRoute()
const authStore = useAuthStore()
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
const chatCrmCardId = ref(null)

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
  return msg.sender_employee_id === authStore.employee?.id
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

async function loadMessages() {
  loadingMessages.value = true
  try {
    const { data } = await api.get(`/api/v1/chats/${chatId}`)
    chatTitle.value = data.title || `Чат #${chatId}`
    messages.value = data.messages || []
    members.value = data.members || []
    clientToken.value = data.client_access_token || ''
    scrollToBottom()

    if (messages.value.length) {
      sendRead(messages.value[messages.value.length - 1].id)
    }

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
    const formData = new FormData()
    formData.append('employee_id', emp.id)
    await api.post(`/api/v1/chats/${chatId}/members`, formData)
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
