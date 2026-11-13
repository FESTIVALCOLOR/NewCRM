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
