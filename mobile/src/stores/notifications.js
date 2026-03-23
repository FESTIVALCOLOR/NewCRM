import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { notificationsApi } from 'src/services/api'

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref([])
  const loading = ref(false)

  const unreadCount = computed(() =>
    items.value.filter(n => !n.is_read).length
  )

  async function load() {
    loading.value = true
    try {
      const { data } = await notificationsApi.getList()
      items.value = data
    } catch {
      // Тихо — уведомления не критичны
    } finally {
      loading.value = false
    }
  }

  async function markRead(id) {
    try {
      await notificationsApi.markRead(id)
      const item = items.value.find(n => n.id === id)
      if (item) item.is_read = true
    } catch {
      // Игнорируем
    }
  }

  return { items, loading, unreadCount, load, markRead }
})
