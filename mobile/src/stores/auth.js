import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from 'src/boot/axios'

export const useAuthStore = defineStore('auth', () => {
  // Состояние
  const user = ref(null)
  const accessToken = ref(localStorage.getItem('access_token') || null)
  const refreshToken = ref(localStorage.getItem('refresh_token') || null)
  const loading = ref(false)
  const error = ref(null)

  // Вычисляемые
  const isAuthenticated = computed(() => !!accessToken.value)
  const fullName = computed(() => user.value?.full_name || '')
  const userRole = computed(() => user.value?.role || '')
  const userPosition = computed(() => user.value?.position || '')
  const initials = computed(() => {
    if (!user.value?.full_name) return '?'
    const parts = user.value.full_name.split(' ')
    return parts.map(p => p[0]).join('').substring(0, 2).toUpperCase()
  })

  // Вход
  async function login(username, password) {
    loading.value = true
    error.value = null

    try {
      // OAuth2 form — отправляется как x-www-form-urlencoded
      const formData = new URLSearchParams()
      formData.append('username', username)
      formData.append('password', password)

      const { data } = await api.post('/api/v1/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })

      accessToken.value = data.access_token
      refreshToken.value = data.refresh_token

      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)

      // Сохраняем базовые данные пользователя из ответа login
      user.value = {
        id: data.employee_id,
        full_name: data.full_name,
        role: data.role,
        position: data.position,
        secondary_position: data.secondary_position,
        department: data.department,
      }

      // Загружаем полный профиль
      await fetchProfile()

      return true
    } catch (err) {
      const status = err.response?.status
      if (status === 401) {
        error.value = 'Неверный логин или пароль'
      } else if (status === 403) {
        error.value = 'Учётная запись неактивна'
      } else if (status === 429) {
        error.value = 'Слишком много попыток. Попробуйте позже'
      } else {
        error.value = 'Ошибка подключения к серверу'
      }
      return false
    } finally {
      loading.value = false
    }
  }

  // Получить профиль
  async function fetchProfile() {
    try {
      const { data } = await api.get('/api/v1/auth/me')
      user.value = data
    } catch {
      // Если профиль не загрузился — используем данные из login
    }
  }

  // Выход
  async function logout() {
    try {
      if (accessToken.value) {
        await api.post('/api/v1/auth/logout')
      }
    } catch {
      // Игнорируем ошибки при logout
    } finally {
      accessToken.value = null
      refreshToken.value = null
      user.value = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
    }
  }

  // Восстановить сессию при загрузке
  async function restoreSession() {
    if (!accessToken.value) return false

    try {
      await fetchProfile()
      return true
    } catch {
      // Токен невалидный — пытаемся refresh
      try {
        if (refreshToken.value) {
          const { data } = await api.post('/api/v1/auth/refresh', {
            refresh_token: refreshToken.value,
          })
          accessToken.value = data.access_token
          localStorage.setItem('access_token', data.access_token)
          await fetchProfile()
          return true
        }
      } catch {
        // Refresh тоже не удался
      }
      // Очищаем всё
      accessToken.value = null
      refreshToken.value = null
      user.value = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      return false
    }
  }

  return {
    // Состояние
    user,
    accessToken,
    refreshToken,
    loading,
    error,
    // Вычисляемые
    isAuthenticated,
    fullName,
    userRole,
    userPosition,
    initials,
    // Действия
    login,
    logout,
    fetchProfile,
    restoreSession,
  }
})
