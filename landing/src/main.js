import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router.js'
import './assets/main.css'
import './assets/decor.css'

createApp(App).use(router).mount('#app')
