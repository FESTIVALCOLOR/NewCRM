import { boot } from 'quasar/wrappers'
import axios from 'axios'
import { isNetworkError, enqueue } from 'src/services/offlineQueue'

const api = axios.create({
  baseURL: 'https://crm.festivalcolor.ru',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor — добавляет JWT токен
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Response interceptor — обработка 401 и refresh
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/refresh')
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (!refreshToken) {
          throw new Error('Нет refresh token')
        }

        const { data } = await axios.post(
          `${api.defaults.baseURL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken },
        )

        const newToken = data.access_token
        localStorage.setItem('access_token', newToken)

        originalRequest.headers.Authorization = `Bearer ${newToken}`
        processQueue(null, newToken)
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        // Refresh не удался — очищаем токены и редиректим
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

// Interceptor для offline-очереди:
// При сетевой ошибке на записывающих операциях (POST/PUT/PATCH/DELETE) —
// предлагаем сохранить в очередь. НЕ сохраняем бизнес-ошибки (400, 409 и т.д.)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config
    // Только записывающие операции
    const writeMethods = ['post', 'put', 'patch', 'delete']
    const method = (config?.method || '').toLowerCase()
    if (!writeMethods.includes(method)) return Promise.reject(error)
    // Только сетевые ошибки (не бизнес-ошибки)
    if (!isNetworkError(error)) return Promise.reject(error)
    // Не сохраняем auth-запросы в очередь
    if (config?.url?.includes('/auth/')) return Promise.reject(error)
    // Не сохраняем heartbeat
    if (config?.url?.includes('/heartbeat')) return Promise.reject(error)
    // Файловые операции на Яндекс.Диске — не сохраняем (ошибка YD, не сетевая)
    if (config?.url?.includes('/files/folder') || config?.url?.includes('/files/move-folder')) return Promise.reject(error)
    // Не дублируем уже сохранённые
    if (config?._offlineQueued) return Promise.reject(error)

    try {
      await enqueue({
        method: method.toUpperCase(),
        url: config.url,
        data: config.data ? JSON.parse(typeof config.data === 'string' ? config.data : JSON.stringify(config.data)) : null,
        description: `${method.toUpperCase()} ${config.url}`,
      })
      console.info(`[OfflineQueue] Операция сохранена: ${method.toUpperCase()} ${config.url}`)
    } catch (queueErr) {
      console.warn('[OfflineQueue] Не удалось сохранить в очередь:', queueErr)
    }
    return Promise.reject(error)
  },
)

export default boot(({ app }) => {
  app.config.globalProperties.$api = api
})

export { api }
