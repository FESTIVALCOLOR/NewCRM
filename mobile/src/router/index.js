import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from 'src/stores/auth'
import routes from './routes'

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ left: 0, top: 0 })
})

let sessionRestored = false

// Auth guard
router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  // Восстановить сессию один раз при загрузке
  if (!sessionRestored) {
    sessionRestored = true
    await authStore.restoreSession()
  }

  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !authStore.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.path === '/login' && authStore.isAuthenticated) {
    return { path: '/' }
  }
})

export default router
