<template>
  <router-view />
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, provide } from 'vue'
import { useMeta, useQuasar } from 'quasar'

const $q = useQuasar()

useMeta({
  title: 'Interior Studio CRM',
  meta: {
    description: { name: 'description', content: 'CRM для интерьерного бюро Festival Color' }
  }
})

// Реактивный статус сети — provide для дочерних компонентов
const isOnline = ref(true)
provide('isOnline', isOnline)

function updateOnlineStatus() {
  const online = navigator.onLine
  if (isOnline.value && !online) {
    isOnline.value = false
    $q.notify({ type: 'warning', message: 'Нет подключения к интернету', icon: 'wifi_off', timeout: 0, position: 'top', actions: [{ icon: 'close', color: 'white', round: true }] })
  } else if (!isOnline.value && online) {
    isOnline.value = true
    $q.notify({ type: 'positive', message: 'Подключение восстановлено', icon: 'wifi', timeout: 3000, position: 'top' })
    // Синхронизация offline-очереди
    syncOfflineQueue()
  }
}

async function syncOfflineQueue() {
  try {
    const { pendingCount, syncAll } = await import('src/services/offlineQueue')
    const count = await pendingCount()
    if (count === 0) return
    $q.notify({ type: 'info', message: `Синхронизация ${count} операций...`, timeout: 2000, icon: 'sync' })
    const result = await syncAll()
    if (result.sent > 0) {
      $q.notify({ type: 'positive', message: `Синхронизировано: ${result.sent}`, icon: 'cloud_done' })
    }
  } catch (err) {
    console.warn('[OfflineSync]', err)
  }
}

onMounted(() => {
  window.addEventListener('online', updateOnlineStatus)
  window.addEventListener('offline', updateOnlineStatus)
})

onUnmounted(() => {
  window.removeEventListener('online', updateOnlineStatus)
  window.removeEventListener('offline', updateOnlineStatus)
})
</script>
