import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from 'src/stores/auth'
import { usePermissionsStore } from 'src/stores/permissions'
import routes from './routes'

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ left: 0, top: 0 }),
})

let sessionRestored = false

// Auth + Permission guard
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

  // Проверка прав доступа к странице
  const requiredPerm = to.meta.requiresPermission
  if (requiredPerm && authStore.isAuthenticated) {
    const permsStore = usePermissionsStore()
    // Дождаться загрузки прав если ещё не загружены
    if (!permsStore.loaded && !permsStore.isSuperuser) {
      await permsStore.load()
    }
    if (!permsStore.has(requiredPerm)) {
      return { path: '/' }
    }
  }
})

export default router
