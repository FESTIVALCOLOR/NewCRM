<template>
  <!-- Баннер установки PWA (Android) -->
  <q-banner
    v-if="showInstallBanner"
    class="bg-primary text-white q-mb-md"
    rounded
    dense
  >
    <template #avatar>
      <q-icon name="install_mobile" />
    </template>
    Установите приложение для быстрого доступа
    <template #action>
      <q-btn flat label="Установить" no-caps @click="installApp" />
      <q-btn
        flat
        icon="close"
        round
        dense
        @click="dismissBanner"
      />
    </template>
  </q-banner>

  <!-- Инструкция для iOS -->
  <q-dialog v-model="showIosGuide">
    <q-card style="max-width: 340px">
      <q-card-section class="text-center">
        <q-icon name="ios_share" size="48px" color="primary" class="q-mb-md" />
        <div class="text-h6 q-mb-sm">
          Установка на iPhone
        </div>
        <div class="text-body2 text-grey-7">
          1. Нажмите кнопку <q-icon name="ios_share" size="18px" /> внизу экрана<br>
          2. Выберите «На экран Домой»<br>
          3. Нажмите «Добавить»
        </div>
      </q-card-section>
      <q-card-actions align="center">
        <q-btn
          v-close-popup
          flat
          label="Понятно"
          color="primary"
          no-caps
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'

const $q = useQuasar()
const showInstallBanner = ref(false)
const showIosGuide = ref(false)

let deferredPrompt = null

onMounted(() => {
  // Не показывать если уже установлено
  if (window.matchMedia('(display-mode: standalone)').matches) return
  if (window.navigator.standalone === true) return

  // Проверяем, не закрыл ли пользователь баннер ранее
  const dismissed = $q.localStorage.getItem('install_dismissed')
  if (dismissed) return

  // Android: перехватываем beforeinstallprompt
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    deferredPrompt = e
    showInstallBanner.value = true
  })

  // iOS: показываем инструкцию через 30 секунд
  const isIos = /iphone|ipad|ipod/.test(navigator.userAgent.toLowerCase())
  if (isIos) {
    setTimeout(() => {
      showIosGuide.value = true
    }, 30000)
  }
})

async function installApp() {
  if (!deferredPrompt) return

  deferredPrompt.prompt()
  const { outcome } = await deferredPrompt.userChoice

  if (outcome === 'accepted') {
    showInstallBanner.value = false
  }
  deferredPrompt = null
}

function dismissBanner() {
  showInstallBanner.value = false
  $q.localStorage.set('install_dismissed', true)
}
</script>
