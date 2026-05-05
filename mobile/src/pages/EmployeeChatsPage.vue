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

    <!-- Список чатов -->
    <q-list v-else-if="filteredChats.length" separator>
      <q-item
        v-for="chat in filteredChats"
        :key="chat.id"
        v-ripple
        clickable
        @click="openChat(chat)"
      >
        <q-item-section avatar>
          <q-avatar color="amber-2" text-color="amber-9" icon="chat" size="42px" />
        </q-item-section>

        <q-item-section>
          <q-item-label class="text-weight-medium">
            {{ chat.title || `Чат #${chat.id}` }}
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
import { api } from 'src/boot/axios'

const router = useRouter()
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
  // Fuzzy: все символы query встречаются в str по порядку
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

async function loadChats() {
  loading.value = true
  try {
    const { data } = await api.get('/api/v1/chats', {
      params: { chat_type: 'employee' },
    })
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

onMounted(loadChats)
</script>
