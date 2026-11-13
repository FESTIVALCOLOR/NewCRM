import { register } from 'register-service-worker'

// sessionStorage переживает reload (в отличие от JS-переменной)
// Защищает от цикла: updated() → reload → updated() → ...
function softReload() {
  if (sessionStorage.getItem('sw_reloading')) return
  sessionStorage.setItem('sw_reloading', '1')
  window.location.reload()
}

// Сбрасываем флаг через 3 сек после загрузки — чтобы следующее реальное обновление SW
// снова могло перезагрузить страницу
window.addEventListener('load', () => {
  setTimeout(() => sessionStorage.removeItem('sw_reloading'), 3000)
})

// НЕ подписываемся на controllerchange — это создаёт бесконечный цикл:
// skipWaiting() → clientsClaim() → controllerchange → reload → снова сначала

register(process.env.SERVICE_WORKER_FILE, {
  ready(/* registration */) {
    console.log('Service worker активен.')
  },

  registered(registration) {
    console.log('Service worker зарегистрирован.')
    // Не проверять обновление сразу если мы только что перезагрузились из-за SW
    if (!sessionStorage.getItem('sw_reloading')) {
      registration.update()
    }
    // Проверять обновление каждые 5 минут
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
  },
})
