import { register } from 'register-service-worker'

// Флаг: не перезагружать дважды
let _reloading = false
function softReload() {
  if (_reloading) return
  _reloading = true
  window.location.reload()
}

// Перезагрузка при смене контроллера (новый SW взял управление через clientsClaim)
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('controllerchange', softReload)
}

register(process.env.SERVICE_WORKER_FILE, {
  ready(/* registration */) {
    console.log('Service worker активен.')
  },

  registered(registration) {
    console.log('Service worker зарегистрирован.')
    // Сразу проверить обновление при загрузке страницы
    registration.update()
    // И каждые 5 минут — чтобы долго открытые вкладки не застревали на старой версии
    setInterval(() => registration.update(), 5 * 60 * 1000)
  },

  cached(/* registration */) {
    console.log('Контент закэширован для офлайн.')
  },

  updatefound(/* registration */) {
    console.log('Загрузка нового контента.')
  },

  updated(/* registration */) {
    console.log('Доступен новый контент — перезагрузка.')
    softReload()
  },

  offline() {
    console.log('Нет подключения к интернету. Работаем в офлайн режиме.')
  },

  error(err) {
    console.error('Ошибка Service Worker:', err)
  }
})
