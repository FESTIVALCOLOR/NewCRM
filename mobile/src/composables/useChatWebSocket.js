/**
 * useChatWebSocket — WebSocket для чата (employee или client).
 *
 * Для сотрудников: ws(s)://host/api/v1/ws/chat/{chatId}?token=JWT
 * Для клиентов:   ws(s)://host/api/v1/ws/client-chat/{accessToken}
 *
 * Отличие от useWebSocket: каждый чат — отдельный экземпляр соединения.
 * Поддерживает: message, typing, read события.
 */
import { ref } from 'vue'

const MAX_RECONNECT_DELAY = 30000
const PING_INTERVAL = 25000

export function useChatWebSocket() {
  const isConnected = ref(false)
  const messages = ref([])
  const typingUsers = ref([]) // [{name, expires}]

  let ws = null
  let pingInterval = null
  let reconnectTimeout = null
  let reconnectDelay = 1000
  let manualClose = false
  let _url = null
  let _handlers = {}

  function _buildUrl(chatId, tokenOrAccessToken, isClient = false) {
    const loc = window.location
    const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = loc.host
    if (isClient) {
      return `${protocol}//${host}/api/v1/ws/client-chat/${tokenOrAccessToken}`
    }
    return `${protocol}//${host}/api/v1/ws/chat/${chatId}?token=${encodeURIComponent(tokenOrAccessToken)}`
  }

  /**
   * Подключиться как сотрудник.
   * @param {number} chatId
   * @param {string} jwtToken
   * @param {object} handlers — { onMessage, onTyping, onRead, onConnect, onDisconnect }
   */
  function connectEmployee(chatId, jwtToken, handlers = {}) {
    _url = _buildUrl(chatId, jwtToken, false)
    _handlers = handlers
    manualClose = false
    _doConnect()
  }

  /**
   * Подключиться как клиент (PWA без JWT).
   * @param {string} accessToken — UUID токен из URL /c/{token}
   * @param {object} handlers
   */
  function connectClient(accessToken, handlers = {}) {
    _url = _buildUrl(null, accessToken, true)
    _handlers = handlers
    manualClose = false
    _doConnect()
  }

  function disconnect() {
    manualClose = true
    _stopPing()
    _clearReconnect()
    if (ws) {
      try { ws.close(1000, 'Клиент отключился') } catch { }
      ws = null
    }
    isConnected.value = false
  }

  /**
   * Отправить текстовое сообщение.
   */
  function sendMessage(content, messageType = 'text') {
    _send({ type: 'message', content, message_type: messageType })
  }

  /**
   * Отправить событие "печатает".
   */
  function sendTypingStart() {
    _send({ type: 'typing_start' })
  }

  function sendTypingStop() {
    _send({ type: 'typing_stop' })
  }

  /**
   * Отметить сообщения как прочитанные.
   */
  function sendRead(lastMessageId) {
    _send({ type: 'read', last_message_id: lastMessageId })
  }

  // ========== внутренние ==========

  function _send(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try { ws.send(JSON.stringify(data)) } catch { }
    }
  }

  function _doConnect() {
    if (!_url) return
    try {
      ws = new WebSocket(_url)
    } catch (err) {
      console.warn('[ChatWS] Ошибка создания:', err)
      _scheduleReconnect()
      return
    }

    ws.onopen = () => {
      isConnected.value = true
      reconnectDelay = 1000
      _startPing()
      if (_handlers.onConnect) _handlers.onConnect()
    }

    ws.onmessage = (event) => {
      let msg
      try { msg = JSON.parse(event.data) } catch { return }
      if (msg.type === 'pong') return
      _handleEvent(msg)
    }

    ws.onclose = () => {
      isConnected.value = false
      _stopPing()
      if (!manualClose) {
        if (_handlers.onDisconnect) _handlers.onDisconnect()
        _scheduleReconnect()
      }
    }

    ws.onerror = () => {
      // onclose будет вызван автоматически
    }
  }

  function _handleEvent(msg) {
    const { type } = msg

    // Сервер отправляет type: "new_message", data в поле msg.message
    if (type === 'new_message') {
      const messageData = msg.message
      if (messageData) {
        messages.value.push(messageData)
        if (_handlers.onMessage) _handlers.onMessage(messageData)
      }
    } else if (type === 'typing_start') {
      const sn = msg.sender_name
      if (sn && !typingUsers.value.find(u => u.name === sn)) typingUsers.value.push({ name: sn })
      if (_handlers.onTyping) _handlers.onTyping(msg, true)
    } else if (type === 'typing_stop') {
      const sn = msg.sender_name
      if (sn) typingUsers.value = typingUsers.value.filter(u => u.name !== sn)
      if (_handlers.onTyping) _handlers.onTyping(msg, false)
    } else if (type === 'read') {
      if (_handlers.onRead) _handlers.onRead(msg)
    } else if (type === 'message_updated') {
      if (msg.message && _handlers.onMessageUpdated) _handlers.onMessageUpdated(msg.message)
    } else if (type === 'message_deleted') {
      if (msg.message_id && _handlers.onMessageDeleted) _handlers.onMessageDeleted(msg.message_id)
    } else if (type === 'member_added') {
      if (_handlers.onMemberAdded) _handlers.onMemberAdded(msg)
    } else if (type === 'member_removed') {
      if (_handlers.onMemberRemoved) _handlers.onMemberRemoved(msg)
    }
  }

  function _scheduleReconnect() {
    if (manualClose) return
    _clearReconnect()
    reconnectTimeout = setTimeout(() => {
      reconnectTimeout = null
      _doConnect()
    }, reconnectDelay)
    reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY)
  }

  function _startPing() {
    _stopPing()
    pingInterval = setInterval(() => {
      _send({ type: 'ping' })
    }, PING_INTERVAL)
  }

  function _stopPing() {
    if (pingInterval) { clearInterval(pingInterval); pingInterval = null }
  }

  function _clearReconnect() {
    if (reconnectTimeout) { clearTimeout(reconnectTimeout); reconnectTimeout = null }
  }

  return {
    isConnected,
    messages,
    typingUsers,
    connectEmployee,
    connectClient,
    disconnect,
    sendMessage,
    sendTypingStart,
    sendTypingStop,
    sendRead,
  }
}
