/**
 * WebSocket composable для real-time обновлений.
 * Подключается к ws(s)://crm.festivalcolor.ru/api/v1/ws?token=JWT
 * Auto-reconnect с экспоненциальной задержкой (1s, 2s, 4s, ..., max 30s)
 * Ping/pong каждые 30 секунд для keep-alive
 *
 * Вызывает callbacks при получении событий:
 *   - card_moved / card_updated → обновление CRM store
 *   - notification_new → обновление notifications store + toast
 */
import { ref, readonly } from 'vue'

// Состояние соединения (реактивное, глобальное — singleton)
const isConnected = ref(false)
const lastError = ref(null)

// Внутренние переменные (не реактивные — не нужны в UI)
let ws = null
let pingInterval = null
let reconnectTimeout = null
let reconnectDelay = 1000 // начальная задержка 1с
const MAX_RECONNECT_DELAY = 30000 // максимум 30с
const PING_INTERVAL = 30000 // пинг каждые 30с
let manualClose = false // флаг для отличия ручного disconnect от разрыва
let _didOpen = false   // true если onopen сработал (соединение было установлено)

/**
 * Определить WebSocket URL по текущему адресу страницы.
 * http:// → ws://, https:// → wss://
 */
function buildWsUrl(token) {
  const loc = window.location
  const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${loc.host}/api/v1/ws?token=${encodeURIComponent(token)}`
}

/**
 * Основной composable.
 * Возвращает методы connect/disconnect и реактивное состояние.
 */
export function useWebSocket() {
  /**
   * Подключиться к WebSocket серверу.
   * @param {string} token — JWT access token
   * @param {object} handlers — колбэки для событий:
   *   { onCardMoved, onCardUpdated, onNotificationNew, onUserOnline, onAny }
   */
  function connect(token, handlers = {}) {
    if (!token) return
    // Если уже подключены — сначала отключаем
    if (ws) {
      disconnect()
    }

    manualClose = false
    _doConnect(token, handlers)
  }

  /**
   * Отключиться (без reconnect).
   */
  function disconnect() {
    manualClose = true
    _cleanup()
    if (ws) {
      try {
        ws.close(1000, 'Клиент отключился')
      } catch {
        // Игнорируем — соединение может быть уже закрыто
      }
      ws = null
    }
    isConnected.value = false
  }

  return {
    isConnected: readonly(isConnected),
    lastError: readonly(lastError),
    connect,
    disconnect,
  }
}

// ========== Внутренние функции ==========

function _doConnect(token, handlers) {
  const url = buildWsUrl(token)
  _didOpen = false

  try {
    ws = new WebSocket(url)
  } catch (err) {
    lastError.value = `Не удалось создать WebSocket: ${err.message}`
    _scheduleReconnect(token, handlers)
    return
  }

  ws.onopen = () => {
    _didOpen = true
    isConnected.value = true
    lastError.value = null
    reconnectDelay = 1000 // сбрасываем задержку при успешном подключении
    _startPing()

    console.log('[WS] Подключён')
  }

  ws.onmessage = (event) => {
    let msg
    try {
      msg = JSON.parse(event.data)
    } catch {
      return
    }

    const type = msg.type
    const data = msg.data || {}

    // Pong от сервера — игнорируем
    if (type === 'pong') return

    // Вызываем соответствующий handler
    switch (type) {
      case 'card_moved':
        if (handlers.onCardMoved) handlers.onCardMoved(data, msg)
        break
      case 'card_updated':
        if (handlers.onCardUpdated) handlers.onCardUpdated(data, msg)
        break
      case 'notification_new':
        if (handlers.onNotificationNew) handlers.onNotificationNew(data, msg)
        break
      case 'user_online':
        if (handlers.onUserOnline) handlers.onUserOnline(data, msg)
        break
      default:
        break
    }

    // Общий handler для всех событий
    if (handlers.onAny) handlers.onAny(msg)
  }

  ws.onclose = (event) => {
    isConnected.value = false
    _stopPing()

    if (manualClose) {
      console.log('[WS] Отключён вручную')
      return
    }

    // Если onopen не срабатывал — сервер отклонил соединение на HTTP-уровне (401/403, истёкший токен).
    // Пробуем обновить токен через callback, а не уходим в бесконечный цикл reconnect.
    if (!_didOpen && handlers.onAuthFailed) {
      console.log(`[WS] Соединение отклонено (code=${event.code}) — возможно токен истёк, вызываем onAuthFailed`)
      handlers.onAuthFailed()
      return
    }

    console.log(`[WS] Соединение закрыто (code=${event.code}), переподключение через ${reconnectDelay}мс...`)
    _scheduleReconnect(token, handlers)
  }

  ws.onerror = (event) => {
    lastError.value = 'Ошибка WebSocket соединения'
    // onclose будет вызван автоматически после onerror
  }
}

/**
 * Запланировать переподключение с экспоненциальной задержкой.
 */
function _scheduleReconnect(token, handlers) {
  if (manualClose) return
  if (reconnectTimeout) clearTimeout(reconnectTimeout)

  reconnectTimeout = setTimeout(() => {
    reconnectTimeout = null
     
    console.log('[WS] Попытка переподключения...')
    _doConnect(token, handlers)
  }, reconnectDelay)

  // Увеличиваем задержку (экспоненциальный backoff)
  reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY)
}

/**
 * Начать отправку ping для keep-alive.
 */
function _startPing() {
  _stopPing()
  pingInterval = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ type: 'ping' }))
      } catch {
        // Ошибка отправки — соединение скоро закроется
      }
    }
  }, PING_INTERVAL)
}

/**
 * Остановить ping.
 */
function _stopPing() {
  if (pingInterval) {
    clearInterval(pingInterval)
    pingInterval = null
  }
}

/**
 * Очистить таймеры.
 */
function _cleanup() {
  _stopPing()
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout)
    reconnectTimeout = null
  }
}
