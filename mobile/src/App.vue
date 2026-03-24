<template>
  <router-view v-if="isOnline" />
  <offline-page v-else />
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useMeta } from 'quasar'
import OfflinePage from 'src/pages/OfflinePage.vue'

useMeta({
  title: 'Interior Studio CRM',
  meta: {
    description: { name: 'description', content: 'CRM для интерьерного бюро Festival Color' }
  }
})

const isOnline = ref(navigator.onLine)

function updateOnlineStatus() {
  isOnline.value = navigator.onLine
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
