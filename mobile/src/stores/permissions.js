import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from 'src/boot/axios'
import { useAuthStore } from './auth'

export const usePermissionsStore = defineStore('permissions', () => {
  const permissions = ref([])
  const loaded = ref(false)

  const SUPERUSER_POSITIONS = ['Руководитель студии']
  const SUPERUSER_ROLES = ['admin', 'director']

  const isSuperuser = computed(() => {
    const auth = useAuthStore()
    const user = auth.user
    if (!user) return false
    return SUPERUSER_ROLES.includes(user.role) || SUPERUSER_POSITIONS.includes(user.position) || SUPERUSER_POSITIONS.includes(user.secondary_position)
  })

  function has(permName) {
    if (isSuperuser.value) return true
    return permissions.value.includes(permName)
  }

  // Какие страницы видны пользователю
  const visiblePages = computed(() => {
    if (isSuperuser.value) return 'all'
    const pages = ['/'] // Дашборд всегда виден
    if (has('access.clients')) pages.push('/clients')
    if (has('access.contracts')) pages.push('/contracts')
    if (has('access.crm')) pages.push('/crm')
    if (has('access.supervision')) pages.push('/supervision')
    if (has('access.reports')) pages.push('/reports')
    if (has('access.employees')) pages.push('/employees')
    if (has('access.salaries')) pages.push('/salaries')
    if (has('access.employee_reports') || has('access.employee_analytics')) pages.push('/employee-reports')
    if (has('chat.employee.view')) pages.push('/employee-chats')
    if (has('chat.client.view')) pages.push('/client-chats')
    pages.push('/notifications', '/profile')
    if (isSuperuser.value) pages.push('/admin', '/files')
    return pages
  })

  async function load() {
    const auth = useAuthStore()
    if (!auth.user?.id || loaded.value) return
    try {
      const { data } = await api.get(`/api/v1/permissions/${auth.user.id}`)
      permissions.value = data.permissions || []
      loaded.value = true
    } catch {
      // Если не загрузились — считаем что прав нет (кроме суперюзера)
    }
  }

  return { permissions, loaded, isSuperuser, has, visiblePages, load }
})
