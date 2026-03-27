/**
 * Offline-очередь — сохраняет операции при отсутствии сети
 * и автоматически отправляет при восстановлении
 *
 * Использует IndexedDB через нативный API (без библиотек)
 */

const DB_NAME = 'crm_offline_queue'
const STORE_NAME = 'operations'
const DB_VERSION = 1

/** Открыть IndexedDB */
function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = (e) => {
      const db = e.target.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true })
        // Индекс по времени создания для сортировки
        store.createIndex('created_at', 'created_at', { unique: false })
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

/**
 * Добавить операцию в очередь
 * @param {Object} operation - { method, url, data, description }
 *   method: 'POST' | 'PUT' | 'PATCH' | 'DELETE'
 *   url: '/api/v1/...'
 *   data: тело запроса (опционально)
 *   description: человекочитаемое описание
 * @returns {Promise<number>} id записи в очереди
 */
export async function enqueue(operation) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const record = {
      ...operation,
      created_at: new Date().toISOString(),
      retries: 0
    }
    const req = store.add(record)
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
    tx.oncomplete = () => db.close()
  })
}

/**
 * Получить все ожидающие операции (в порядке добавления)
 * @returns {Promise<Array>}
 */
export async function getPending() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const index = store.index('created_at')
    const req = index.getAll()
    req.onsuccess = () => resolve(req.result || [])
    req.onerror = () => reject(req.error)
    tx.oncomplete = () => db.close()
  })
}

/**
 * Удалить операцию из очереди по id
 * @param {number} id
 */
async function removeById(id) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const req = store.delete(id)
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
    tx.oncomplete = () => db.close()
  })
}

/**
 * Обновить количество попыток для операции
 * @param {number} id
 * @param {number} retries
 */
async function updateRetries(id, retries) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const getReq = store.get(id)
    getReq.onsuccess = () => {
      const record = getReq.result
      if (record) {
        record.retries = retries
        store.put(record)
      }
      resolve()
    }
    getReq.onerror = () => reject(getReq.error)
    tx.oncomplete = () => db.close()
  })
}

/**
 * Отправить все ожидающие операции
 * Порядок: FIFO (первая добавленная — первая отправляется)
 *
 * При ошибке 4xx (клиентская) — удаляем из очереди (retry бесполезен)
 * При ошибке 5xx или сетевой — оставляем для следующей попытки
 *
 * @param {Function} onProgress - колбэк прогресса (current, total, description)
 * @returns {Promise<{sent: number, failed: number, remaining: number}>}
 */
export async function syncAll(onProgress = null) {
  // Импортируем axios динамически, чтобы использовать interceptors (JWT)
  const { api } = await import('src/boot/axios')
  const pending = await getPending()
  const total = pending.length
  let sent = 0
  let failed = 0

  for (let i = 0; i < pending.length; i++) {
    const op = pending[i]
    if (onProgress) onProgress(i + 1, total, op.description || op.url)

    try {
      const config = {
        method: op.method.toLowerCase(),
        url: op.url,
        timeout: 15000
      }
      if (op.data && ['post', 'put', 'patch'].includes(config.method)) {
        config.data = op.data
      }
      await api(config)
      await removeById(op.id)
      sent++
    } catch (err) {
      const status = err.response?.status
      if (status && status >= 400 && status < 500) {
        // Клиентская ошибка (400, 401, 403, 404, 409, 422) — retry бесполезен
        console.warn(`[OfflineQueue] Операция #${op.id} удалена (${status}): ${op.description}`)
        await removeById(op.id)
        failed++
      } else {
        // Сетевая ошибка или 5xx — оставляем для следующей попытки
        await updateRetries(op.id, (op.retries || 0) + 1)
        failed++
      }
    }
  }

  const remaining = (await getPending()).length
  return { sent, failed, remaining }
}

/**
 * Количество ожидающих операций
 * @returns {Promise<number>}
 */
export async function pendingCount() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const req = store.count()
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
    tx.oncomplete = () => db.close()
  })
}

/**
 * Очистить всю очередь
 * @returns {Promise<void>}
 */
export async function clearAll() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const req = store.clear()
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
    tx.oncomplete = () => db.close()
  })
}

/**
 * Проверка: является ли ошибка сетевой (не бизнес-ошибкой)
 * Сетевые: нет response, timeout, network error
 * НЕ сетевые: 400, 401, 403, 404, 409, 422 — бизнес-ошибки
 */
export function isNetworkError(error) {
  // Нет ответа вообще — сетевая ошибка
  if (!error.response) return true
  // 5xx — серверная ошибка, можно retry
  if (error.response.status >= 500) return true
  // Всё остальное (4xx) — бизнес-ошибки, retry бесполезен
  return false
}
