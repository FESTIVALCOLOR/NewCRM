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

    <template v-else-if="hasAnyChats">
      <!-- Закреплённые чаты -->
      <template v-if="pinnedChats.length">
        <div class="section-header q-px-md q-py-xs text-caption text-grey-6">
          Закреплённые
        </div>
        <q-list separator>
          <q-slide-item
            v-for="chat in pinnedChats"
            :key="chat.id"
            right-color="warning"
            @right="(evt) => swipeUnpin(chat, evt)"
          >
            <template #right>
              <q-icon name="push_pin" />
              <span class="q-ml-xs text-caption">Открепить</span>
            </template>

            <q-item
              v-ripple
              clickable
              class="pinned-chat-item"
              @click="openChat(chat)"
            >
              <q-item-section avatar>
                <q-avatar color="light-green-2" text-color="light-green-9" size="42px">
                  <q-icon name="support_agent" />
                </q-avatar>
              </q-item-section>

              <q-item-section>
                <q-item-label class="text-weight-medium">
                  <q-icon name="push_pin" size="12px" color="amber-8" class="q-mr-xs" />
                  {{ chat.title || `Чат #${chat.id}` }}
                </q-item-label>
                <q-item-label caption>
                  <q-badge :color="chatTypeLabel(chat).color" outline style="font-size: 10px; padding: 1px 5px">
                    {{ chatTypeLabel(chat).label }}
                  </q-badge>
                </q-item-label>
                <q-item-label v-if="chat.last_message" caption lines="1">
                  {{ chat.last_message }}
                </q-item-label>
                <q-item-label v-if="chat.member_count" caption>
                  {{ chat.member_count }} уч.<span v-if="chat.guest_count">, {{ chat.guest_count }} клиент(ов)</span>
                </q-item-label>
              </q-item-section>

              <q-item-section side class="items-center row no-wrap q-gutter-xs">
                <q-badge
                  v-if="chat.unread_count"
                  color="negative"
                  :label="chat.unread_count"
                  rounded
                />
                <q-btn
                  flat
                  dense
                  round
                  icon="push_pin"
                  color="amber-8"
                  size="sm"
                  :loading="pinLoading[chat.id]"
                  @click.stop="unpinChat(chat)"
                >
                  <q-tooltip>Открепить</q-tooltip>
                </q-btn>
              </q-item-section>
            </q-item>
          </q-slide-item>
        </q-list>
      </template>

      <!-- Остальные чаты -->
      <template v-if="regularChats.length">
        <div v-if="pinnedChats.length" class="section-header q-px-md q-py-xs text-caption text-grey-6">
          Все чаты
        </div>
        <q-list separator>
          <q-slide-item
            v-for="chat in regularChats"
            :key="chat.id"
            right-color="primary"
            @right="(evt) => swipePin(chat, evt)"
          >
            <template #right>
              <q-icon name="push_pin" />
              <span class="q-ml-xs text-caption">Закрепить</span>
            </template>

            <q-item
              v-ripple
              clickable
              @click="openChat(chat)"
            >
              <q-item-section avatar>
                <q-avatar color="green-2" text-color="green-9" size="42px">
                  <q-icon name="support_agent" />
                </q-avatar>
              </q-item-section>

              <q-item-section>
                <q-item-label class="text-weight-medium">
                  {{ chat.title || `Чат #${chat.id}` }}
                </q-item-label>
                <q-item-label caption>
                  <q-badge :color="chatTypeLabel(chat).color" outline style="font-size: 10px; padding: 1px 5px">
                    {{ chatTypeLabel(chat).label }}
                  </q-badge>
                </q-item-label>
                <q-item-label v-if="chat.last_message" caption lines="1">
                  {{ chat.last_message }}
                </q-item-label>
                <q-item-label v-if="chat.member_count" caption>
                  {{ chat.member_count }} уч.<span v-if="chat.guest_count">, {{ chat.guest_count }} клиент(ов)</span>
                </q-item-label>
              </q-item-section>

              <q-item-section side class="items-center row no-wrap q-gutter-xs">
                <q-badge
                  v-if="chat.unread_count"
                  color="negative"
                  :label="chat.unread_count"
                  rounded
                />
                <q-btn
                  flat
                  dense
                  round
                  icon="push_pin"
                  color="grey-5"
                  size="sm"
                  :loading="pinLoading[chat.id]"
                  @click.stop="pinChat(chat)"
                >
                  <q-tooltip>Закрепить</q-tooltip>
                </q-btn>
              </q-item-section>
            </q-item>
          </q-slide-item>
        </q-list>
      </template>

      <!-- Чаты надзора (с доступом для клиента) -->
      <template v-if="filteredSupervisionChats.length">
        <div class="section-header q-px-md q-py-xs text-caption text-grey-6">
          Надзор
        </div>
        <q-list separator>
          <q-slide-item
            v-for="chat in filteredSupervisionChats"
            :key="chat.id"
            :right-color="chat.is_pinned_by_user ? 'warning' : 'primary'"
            @right="(evt) => chat.is_pinned_by_user ? swipeSvUnpin(chat, evt) : swipeSvPin(chat, evt)"
          >
            <template #right>
              <q-icon :name="chat.is_pinned_by_user ? 'push_pin' : 'push_pin'" />
              <span class="q-ml-xs text-caption">{{ chat.is_pinned_by_user ? 'Открепить' : 'Закрепить' }}</span>
            </template>

            <q-item
              v-ripple
              clickable
              :class="chat.is_pinned_by_user ? 'pinned-sv-chat-item' : ''"
              @click="openSupervisionChat(chat)"
            >
              <q-item-section avatar>
                <q-avatar color="blue-2" text-color="blue-9" size="42px">
                  <q-icon name="engineering" />
                </q-avatar>
              </q-item-section>

              <q-item-section>
                <q-item-label class="text-weight-medium">
                  <q-icon
                    v-if="chat.is_pinned_by_user"
                    name="push_pin"
                    size="12px"
                    color="amber-8"
                    class="q-mr-xs"
                  />
                  {{ chat.title || `Чат надзора #${chat.id}` }}
                </q-item-label>
                <q-item-label caption>
                  <q-badge color="blue" outline style="font-size: 10px; padding: 1px 5px">
                    Авторский надзор
                  </q-badge>
                </q-item-label>
                <q-item-label v-if="chat.last_message" caption lines="1">
                  {{ chat.last_message }}
                </q-item-label>
                <q-item-label v-if="chat.member_count" caption>
                  {{ chat.member_count }} уч.<span v-if="chat.guest_count">, {{ chat.guest_count }} клиент(ов)</span>
                </q-item-label>
              </q-item-section>

              <q-item-section side class="items-center row no-wrap q-gutter-xs">
                <q-badge
                  v-if="chat.unread_count"
                  color="negative"
                  :label="chat.unread_count"
                  rounded
                />
                <q-btn
                  flat
                  dense
                  round
                  :icon="chat.is_pinned_by_user ? 'push_pin' : 'push_pin'"
                  :color="chat.is_pinned_by_user ? 'amber-8' : 'grey-5'"
                  size="sm"
                  :loading="pinLoading[chat.id]"
                  @click.stop="chat.is_pinned_by_user ? svUnpinChat(chat) : svPinChat(chat)"
                >
                  <q-tooltip>{{ chat.is_pinned_by_user ? 'Открепить' : 'Закрепить' }}</q-tooltip>
                </q-btn>
              </q-item-section>
            </q-item>
          </q-slide-item>
        </q-list>
      </template>
    </template>

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
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

function chatTypeLabel(chat) {
  if (chat.project_type === 'Авторский надзор') return { label: 'Авторский надзор', color: 'blue' }
  if (chat.project_type === 'Индивидуальный') return { label: 'Индивидуальный проект', color: 'green' }
  if (chat.project_type === 'Шаблонный') return { label: 'Шаблонный проект', color: 'orange' }
  return { label: 'Чат с клиентом', color: 'green' }
}
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'

const router = useRouter()
const $q = useQuasar()
const loading = ref(false)
const chats = ref([])
const supervisionChats = ref([])
const searchText = ref('')
const pinLoading = ref({})

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

const filteredSupervisionChats = computed(() => {
  const q = searchText.value?.trim() || ''
  if (!q) return supervisionChats.value
  return supervisionChats.value
    .map(c => ({ c, score: fuzzyScore(c.title || `Чат #${c.id}`, q) }))
    .filter(({ score }) => score >= 1)
    .sort((a, b) => b.score - a.score)
    .map(({ c }) => c)
})

const hasAnyChats = computed(() => filteredChats.value.length > 0 || filteredSupervisionChats.value.length > 0)

const pinnedChats = computed(() => filteredChats.value.filter(c => c.is_pinned_by_user))
const regularChats = computed(() => filteredChats.value.filter(c => !c.is_pinned_by_user))

async function loadChats() {
  loading.value = true
  try {
    const [clientRes, svRes] = await Promise.all([
      api.get('/api/v1/chats', { params: { chat_type: 'client' } }),
      api.get('/api/v1/chats', { params: { chat_type: 'employee' } }),
    ])
    chats.value = Array.isArray(clientRes.data) ? clientRes.data : (clientRes.data.items || [])
    const allEmployee = Array.isArray(svRes.data) ? svRes.data : (svRes.data.items || [])
    supervisionChats.value = allEmployee.filter(c => c.supervision_card_id != null)
  } catch (e) {
    console.error('[ClientChatsPage] Ошибка:', e)
  } finally {
    loading.value = false
  }
}

function openChat(chat) {
  router.push({ name: 'client-chat-room', params: { chatId: chat.id } })
}

function openSupervisionChat(chat) {
  router.push({ name: 'employee-chat-room', params: { chatId: chat.id } })
}

async function svPinChat(chat) {
  pinLoading.value[chat.id] = true
  try {
    await api.post(`/api/v1/chats/${chat.id}/pin`)
    chat.is_pinned_by_user = true
    $q.notify({ type: 'positive', message: 'Чат закреплён', timeout: 1500 })
  } catch {
    $q.notify({ type: 'negative', message: 'Не удалось закрепить чат' })
  } finally {
    pinLoading.value[chat.id] = false
  }
}

async function svUnpinChat(chat) {
  pinLoading.value[chat.id] = true
  try {
    await api.delete(`/api/v1/chats/${chat.id}/pin`)
    chat.is_pinned_by_user = false
    $q.notify({ type: 'info', message: 'Чат откреплён', timeout: 1500 })
  } catch {
    $q.notify({ type: 'negative', message: 'Не удалось открепить чат' })
  } finally {
    pinLoading.value[chat.id] = false
  }
}

async function swipeSvPin(chat, { reset }) {
  try {
    await api.post(`/api/v1/chats/${chat.id}/pin`)
    chat.is_pinned_by_user = true
    $q.notify({ type: 'positive', message: 'Чат закреплён', timeout: 1500 })
  } catch {
    $q.notify({ type: 'negative', message: 'Не удалось закрепить чат' })
    reset()
  }
}

async function swipeSvUnpin(chat, { reset }) {
  try {
    await api.delete(`/api/v1/chats/${chat.id}/pin`)
    chat.is_pinned_by_user = false
    $q.notify({ type: 'info', message: 'Чат откреплён', timeout: 1500 })
  } catch {
    $q.notify({ type: 'negative', message: 'Не удалось открепить чат' })
    reset()
  }
}

async function pinChat(chat) {
  pinLoading.value[chat.id] = true
  try {
    await api.post(`/api/v1/chats/${chat.id}/pin`)
    chat.is_pinned_by_user = true
    $q.notify({ type: 'positive', message: 'Чат закреплён', timeout: 1500 })
  } catch {
    $q.notify({ type: 'negative', message: 'Не удалось закрепить чат' })
  } finally {
    pinLoading.value[chat.id] = false
  }
}

async function unpinChat(chat) {
  pinLoading.value[chat.id] = true
  try {
    await api.delete(`/api/v1/chats/${chat.id}/pin`)
    chat.is_pinned_by_user = false
    $q.notify({ type: 'info', message: 'Чат откреплён', timeout: 1500 })
  } catch {
    $q.notify({ type: 'negative', message: 'Не удалось открепить чат' })
  } finally {
    pinLoading.value[chat.id] = false
  }
}

async function swipePin(chat, { reset }) {
  try {
    await api.post(`/api/v1/chats/${chat.id}/pin`)
    chat.is_pinned_by_user = true
    $q.notify({ type: 'positive', message: 'Чат закреплён', timeout: 1500 })
  } catch {
    $q.notify({ type: 'negative', message: 'Не удалось закрепить чат' })
    reset()
  }
}

async function swipeUnpin(chat, { reset }) {
  try {
    await api.delete(`/api/v1/chats/${chat.id}/pin`)
    chat.is_pinned_by_user = false
    $q.notify({ type: 'info', message: 'Чат откреплён', timeout: 1500 })
  } catch {
    $q.notify({ type: 'negative', message: 'Не удалось открепить чат' })
    reset()
  }
}

onMounted(loadChats)
</script>

<style scoped>
.section-header {
  background: #f5f5f5;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.pinned-chat-item {
  background: #f1f8e9;
}

.pinned-sv-chat-item {
  background: #e3f2fd;
}
</style>
