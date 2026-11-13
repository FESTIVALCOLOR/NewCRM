import { createApp } from 'vue'
import App from './App.vue'
import { router, reloadForNewVersion, reloadTarget } from './router.js'
import './assets/main.css'
import './assets/decor.css'

// Не удалось подгрузить стили или скрипт страницы — значит, сайт обновился, пока вкладка была открыта
window.addEventListener('vite:preloadError', (event) => {
  // Если сбой случился при переходе на другую страницу, открываем сразу её, а не текущую
  if (reloadForNewVersion(reloadTarget())) event.preventDefault()
})

createApp(App).use(router).mount('#app')
