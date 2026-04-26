import { register } from 'register-service-worker'

register(process.env.SERVICE_WORKER_FILE, {
  ready(/* registration */) {
    console.log('Service worker активен.')
  },

  registered(/* registration */) {
    console.log('Service worker зарегистрирован.')
  },

  cached(/* registration */) {
    console.log('Контент закэширован для офлайн.')
  },

  updatefound(/* registration */) {
    console.log('Загрузка нового контента.')
  },

  updated(/* registration */) {
    console.log('Доступен новый контент — обновите страницу.')
    // SW с skipWaiting() уже взял управление — перезагрузка подгрузит новые файлы
    window.location.reload()
  },

  offline() {
    console.log('Нет подключения к интернету. Работаем в офлайн режиме.')
  },

  error(err) {
    console.error('Ошибка Service Worker:', err)
  }
})
