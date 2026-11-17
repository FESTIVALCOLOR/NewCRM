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

  function connectEmployee(chatId, jwtToken, handlers = {}) {
    _url = _buildUrl(chatId, jwtToken, false)
    _handlers = handlers
    manualClose = false
    _doConnect()
  }

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
    typingUsers.value.forEach(u => { if (u._timer) clearTimeout(u._timer) })
    typingUsers.value = []
  }

  function sendMessage(content, replyToId = null, messageType = 'text') {
    const payload = { type: 'message', content, message_type: messageType }
    if (replyToId) payload.reply_to_id = replyToId
    _send(payload)
  }

  function sendTypingStart() {
    _send({ type: 'typing_start' })
  }
  function sendTypingStop() {
    _send({ type: 'typing_stop' })
  }

  function sendRead(lastMessageId) {
    _send({ type: 'read', last_message_id: lastMessageId })
  }

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

    ws.onerror = () => {}
  }

  function _onNewMessage(msg) {
    const messageData = msg.message
    if (!messageData) return
    messages.value.push(messageData)
    if (_handlers.onMessage) _handlers.onMessage(messageData)
  }

  function _onNewMessageGroup(msg) {
    const batchMsgs = msg.messages
    if (!Array.isArray(batchMsgs) || !batchMsgs.length) return
    if (_handlers.onMessageGroup) { _handlers.onMessageGroup(batchMsgs); return }
    batchMsgs.forEach(m => { messages.value.push(m); if (_handlers.onMessage) _handlers.onMessage(m) })
  }

  function _onTypingStart(msg) {
    const sn = msg.sender_name
    if (sn) {
      typingUsers.value = typingUsers.value.filter(u => u.name !== sn)
      const timer = setTimeout(() => { typingUsers.value = typingUsers.value.filter(u => u.name !== sn) }, 6000)
      typingUsers.value.push({ name: sn, _timer: timer })
    }
    if (_handlers.onTyping) _handlers.onTyping(msg, true)
  }

  function _onTypingStop(msg) {
    const sn = msg.sender_name
    if (sn) {
      const user = typingUsers.value.find(u => u.name === sn)
      if (user?._timer) clearTimeout(user._timer)
      typingUsers.value = typingUsers.value.filter(u => u.name !== sn)
    }
    if (_handlers.onTyping) _handlers.onTyping(msg, false)
  }

  const _EVENT_MAP = {
    new_message: _onNewMessage,
    new_message_group: _onNewMessageGroup,
    typing_start: _onTypingStart,
    typing_stop: _onTypingStop,
    read: msg => { if (_handlers.onRead) _handlers.onRead(msg) },
    message_updated: msg => { if (msg.message && _handlers.onMessageUpdated) _handlers.onMessageUpdated(msg.message) },
    message_deleted: msg => { if (msg.message_id && _handlers.onMessageDeleted) _handlers.onMessageDeleted(msg.message_id) },
    member_added: msg => { if (_handlers.onMemberAdded) _handlers.onMemberAdded(msg) },
    member_removed: msg => { if (_handlers.onMemberRemoved) _handlers.onMemberRemoved(msg) },
    message_pinned: msg => { if (_handlers.onPinned) _handlers.onPinned(msg) },
    reaction_updated: msg => { if (_handlers.onReactionUpdated) _handlers.onReactionUpdated(msg) },
  }

  function _handleEvent(msg) {
    const handler = _EVENT_MAP[msg.type]
    if (handler) handler(msg)
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
