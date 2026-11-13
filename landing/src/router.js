import { createRouter, createWebHistory } from 'vue-router'
import HomePage from './pages/HomePage.vue'

const SITE_NAME = 'FESTIVAL COLOR'
// Высота закреплённой шапки: якорь не должен прятаться под ней
export const HEADER_HEIGHT = 68

const routes = [
  { path: '/', name: 'home', component: HomePage },
  { path: '/individual', name: 'individual', component: () => import('./pages/IndividualPage.vue'), meta: { title: 'Индивидуальный дизайн интерьера' } },
  { path: '/ready', name: 'ready', component: () => import('./pages/ReadyCatalogPage.vue'), meta: { title: 'Готовый дизайн интерьера' } },
  { path: '/ready/:id(\\d+)', name: 'ready-design', component: () => import('./pages/ReadyDesignPage.vue'), meta: { title: 'Готовый дизайн интерьера' } },
  { path: '/:rest(.*)*', redirect: '/' },
]

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) {
      // При переходе с другой страницы блоку нужно время появиться
      const delay = from.name && from.path !== to.path ? 350 : 0
      return new Promise(resolve => setTimeout(() => {
        resolve(document.querySelector(to.hash) ? { el: to.hash, top: HEADER_HEIGHT - 1, behavior: 'smooth' } : { top: 0 })
      }, delay))
    }
    return { top: 0 }
  },
})

// Заголовок вкладки: у главной — из настроек SEO, у внутренних страниц — свой
let homeTitle = document.title
export function rememberHomeTitle() { homeTitle = document.title }
export function setPageTitle(title) {
  document.title = title ? `${title} — ${SITE_NAME}` : homeTitle
}
router.afterEach((to) => setPageTitle(to.meta.title))

// После выкладки новой версии у вкладки, открытой раньше, может не оказаться файла нужной страницы.
// Вместо молчаливого «не открывается» перезагружаем страницу сразу на нужном адресе — один раз, без зацикливания
const RELOAD_KEY = 'chunk_reload_at'
export function reloadForNewVersion(path) {
  try {
    const last = Number(sessionStorage.getItem(RELOAD_KEY) || 0)
    if (Date.now() - last < 10000) return false
    sessionStorage.setItem(RELOAD_KEY, String(Date.now()))
  } catch { /* хранилище недоступно — перезагрузка всё равно поможет */ }
  window.location.assign(path)
  return true
}
// Куда идёт переход прямо сейчас: файл страницы подгружается уже после начала перехода
let pendingHref = null
router.beforeEach((to) => { pendingHref = router.resolve(to).href })
router.afterEach(() => { pendingHref = null })
export function reloadTarget() {
  return pendingHref || window.location.href
}

router.onError((error, to) => {
  const message = String(error?.message || error || '')
  if (/dynamically imported module|Importing a module script failed|Failed to fetch|Unable to preload/i.test(message)) {
    reloadForNewVersion(router.resolve(to).href)
  }
})
