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

    <template v-else-if="filteredChats.length">
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
            @right="(evt) => onUnpin(chat, evt)"
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
                <q-item-label v-if="chat.last_message" caption lines="1">
                  {{ chat.last_message }}
                </q-item-label>
                <q-item-label v-if="chat.member_count" caption>
                  {{ chat.member_count }} уч.<span v-if="chat.guest_count">, {{ chat.guest_count }} клиент(ов)</span>
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
            @right="(evt) => onPin(chat, evt)"
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
                <q-item-label v-if="chat.last_message" caption lines="1">
                  {{ chat.last_message }}
                </q-item-label>
                <q-item-label v-if="chat.member_count" caption>
                  {{ chat.member_count }} уч.<span v-if="chat.guest_count">, {{ chat.guest_count }} клиент(ов)</span>
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
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'

const router = useRouter()
const $q = useQuasar()
const loading = ref(false)
const chats = ref([])
const searchText = ref('')

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

const pinnedChats = computed(() => filteredChats.value.filter(c => c.is_pinned_by_user))
const regularChats = computed(() => filteredChats.value.filter(c => !c.is_pinned_by_user))

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
  router.push({ name: 'client-chat-room', params: { chatId: chat.id } })
}

async function onPin(chat, { reset }) {
  try {
    await api.post(`/api/v1/chats/${chat.id}/pin`)
    chat.is_pinned_by_user = true
    $q.notify({ type: 'positive', message: 'Чат закреплён', timeout: 1500 })
  } catch {
    $q.notify({ type: 'negative', message: 'Не удалось закрепить чат' })
    reset()
  }
}

async function onUnpin(chat, { reset }) {
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
</style>
