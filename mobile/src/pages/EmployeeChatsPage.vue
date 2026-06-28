<template>
  <q-page>
    <!-- Поиск -->
    <div class="q-px-md q-pt-md q-pb-sm">
      <q-input
        v-model="searchText"
        outlined
        dense
        placeholder="Поиск по названию чата…"
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

    <template v-else-if="filteredChats.length">
      <!-- Административные чаты (всегда сверху) -->
      <template v-if="adminChats.length">
        <div class="section-header q-px-md q-py-xs text-caption text-grey-6">
          Административные
        </div>
        <q-list separator>
          <q-item
            v-for="chat in adminChats"
            :key="chat.id"
            v-ripple
            clickable
            class="admin-chat-item"
            @click="openChat(chat)"
          >
            <q-item-section avatar>
              <q-avatar color="blue-2" text-color="blue-9" size="42px">
                <q-icon name="admin_panel_settings" />
              </q-avatar>
            </q-item-section>

            <q-item-section>
              <q-item-label class="text-weight-bold text-blue-9">
                {{ chat.title || `Чат #${chat.id}` }}
              </q-item-label>
              <q-item-label v-if="chatTypeInfo(chat)" caption>
                <q-badge :color="chatTypeInfo(chat).color" outline style="font-size: 10px; padding: 1px 5px">
                  {{ chatTypeInfo(chat).label }}
                </q-badge>
              </q-item-label>
              <q-item-label v-if="chat.last_message" caption lines="1">
                {{ chat.last_message }}
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
      </template>

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
                <q-avatar color="amber-2" text-color="amber-9" size="42px">
                  <q-icon name="chat" />
                </q-avatar>
              </q-item-section>

              <q-item-section>
                <q-item-label class="text-weight-medium">
                  <q-icon name="push_pin" size="12px" color="amber-8" class="q-mr-xs" />
                  {{ chat.title || `Чат #${chat.id}` }}
                </q-item-label>
                <q-item-label v-if="chatTypeInfo(chat)" caption>
                  <q-badge :color="chatTypeInfo(chat).color" outline style="font-size: 10px; padding: 1px 5px">
                    {{ chatTypeInfo(chat).label }}
                  </q-badge>
                </q-item-label>
                <q-item-label v-if="chat.last_message" caption lines="1">
                  {{ chat.last_message }}
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
        <div
          v-if="adminChats.length || pinnedChats.length"
          class="section-header q-px-md q-py-xs text-caption text-grey-6"
        >
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
                <q-avatar color="amber-2" text-color="amber-9" size="42px">
                  <q-icon name="chat" />
                </q-avatar>
              </q-item-section>

              <q-item-section>
                <q-item-label class="text-weight-medium">
                  {{ chat.title || `Чат #${chat.id}` }}
                </q-item-label>
                <q-item-label v-if="chatTypeInfo(chat)" caption>
                  <q-badge :color="chatTypeInfo(chat).color" outline style="font-size: 10px; padding: 1px 5px">
                    {{ chatTypeInfo(chat).label }}
                  </q-badge>
                </q-item-label>
                <q-item-label v-if="chat.last_message" caption lines="1">
                  {{ chat.last_message }}
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
    </template>

    <!-- Пусто -->
    <div v-else class="q-pa-xl text-center text-grey">
      <q-icon name="chat_bubble_outline" size="48px" class="q-mb-md" />
      <div class="text-h6">
        Нет чатов
      </div>
      <div class="text-body2 q-mt-xs">
        Чаты создаются автоматически при открытии CRM-карточки
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'

const router = useRouter()
const $q = useQuasar()
const loading = ref(false)
const chats = ref([])
const searchText = ref('')
const pinLoading = ref({})

function chatTypeInfo(chat) {
  if (chat.is_admin_chat) {
    const map = {
      ip: { label: 'Индивидуальный проект', color: 'green' },
      shp: { label: 'Шаблонный проект', color: 'orange' },
      an: { label: 'Авторский надзор', color: 'blue' },
    }
    return map[chat.admin_chat_type] || null
  }
  if (chat.project_type === 'Авторский надзор') return { label: 'Авторский надзор', color: 'blue' }
  if (chat.project_type === 'Индивидуальный') return { label: 'Индивидуальный проект', color: 'green' }
  if (chat.project_type === 'Шаблонный') return { label: 'Шаблонный проект', color: 'orange' }
  return null
}

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

const adminChats = computed(() => filteredChats.value.filter(c => c.is_admin_chat))
const pinnedChats = computed(() => filteredChats.value.filter(c => !c.is_admin_chat && c.is_pinned_by_user))
const regularChats = computed(() => filteredChats.value.filter(c => !c.is_admin_chat && !c.is_pinned_by_user))

async function loadChats() {
  loading.value = true
  try {
    const { data } = await api.get('/api/v1/chats', { params: { chat_type: 'employee' } })
    chats.value = Array.isArray(data) ? data : (data.items || [])
  } catch (e) {
    console.error('[EmployeeChatsPage] Ошибка загрузки:', e)
  } finally {
    loading.value = false
  }
}

function openChat(chat) {
  router.push({ name: 'employee-chat-room', params: { chatId: chat.id } })
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

.admin-chat-item {
  background: #e8f4fd;
  border-left: 3px solid #1565c0;
}

.pinned-chat-item {
  background: #fffde7;
}
</style>
