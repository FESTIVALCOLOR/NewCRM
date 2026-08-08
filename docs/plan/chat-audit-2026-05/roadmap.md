# Дорожная карта улучшений чатов — Interior Studio CRM

**Дата:** 2026-05-04
**Статус:** Рекомендации (не реализовано)

## Оглавление

### Фаза 1: Критические баги (1-2 дня)
- ✅ 1.1 Исправить activeChatId в ClientChatsPage.vue
- ✅ 1.2 Исправить удаление сообщений гостя (ClientChatPage)
- ✅ 1.3 Исправить temp file leak в stream endpoint
- ✅ 1.4 Добавить auto-cleanup для typingUsers

### Фаза 2: Производительность (3-5 дней)
- ✅ 2.1 Cursor-based pagination для всех чат-комнат (Intersection Observer)
- ✅ 2.2 Добавить индексы (chat_id, id DESC; chat_id + employee_id)
- ✅ 2.3 Batch load unread counts (убрать N+1)
- ✅ 2.4 Виртуальный скролл в Mobile чатах (Intersection Observer)

### Фаза 3: Паритет Desktop ↔ Mobile (5-7 дней)
- ✅ 3.1 Скрипты с переменными в EmployeeChatRoomPage.vue
- ✅ 3.2 PWA Notifications + Badge в Desktop (N/A, пропущено)
- ✅ 3.3 Поиск по сообщениям (Desktop + Mobile)
- ✅ 3.4 Галерея на Mobile для client-page (no-auth)

### Фаза 4: Улучшения UX (опционально)
- ✅ 4.1 Emoji-реакции (реализовано 2026-05-05)
- ✅ 4.2 Голосовые сообщения (реализовано 2026-05-05)
- ✅ 4.3 Fuzzy-поиск по названию чата
- ✅ 4.4 Кэш изображений в Desktop (LRU 60 записей)

---

## Детали фаз

### Фаза 1: Критические баги

**1.1 ClientChatsPage.vue — activeChatId**
```javascript
// Текущий код (БАГ):
const openChat = (chat) => {
  router.push(`/client-chats/${chat.id}`)
  // activeChatId никогда не устанавливается!
}

// Исправление:
const openChat = (chat) => {
  activeChatId.value = chat.id
  showLinkDialog.value = false
  router.push(`/client-chats/${chat.id}`)
}
```

**1.2 ClientChatPage.vue — удаление гостя**
```javascript
// Текущий код (БАГ): только скрывает в UI
const deleteClientMsg = (msg) => {
  messages.value = messages.value.filter(m => m.id !== msg.id)
}

// Исправление: делать реальный DELETE
const deleteClientMsg = async (msg) => {
  await axios.delete(`/api/v1/client-chat/${route.params.token}/messages/${msg.id}`)
  messages.value = messages.value.filter(m => m.id !== msg.id)
}
// + добавить endpoint DELETE /client-chat/{token}/messages/{msg_id} в server
```

**1.3 Stream endpoint temp file leak**
```python
# Текущий код (БАГ):
tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
...
return FileResponse(tmp.name, ...)

# Исправление: cleanup после отправки
import asyncio, os
async def cleanup_tmp(path: str):
    await asyncio.sleep(1)  # дать время FileResponse завершить отдачу
    try: os.unlink(path)
    except OSError: pass

tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
background_tasks.add_task(cleanup_tmp, tmp.name)
return FileResponse(tmp.name, background=background_tasks)
```

**1.4 Typing users auto-cleanup**
```javascript
// В useChatWebSocket.js:
const TYPING_TIMEOUT = 5000  // 5 сек

const _handleEvent = (msg) => {
  if (msg.type === 'typing_start') {
    // Убрать дубли + добавить expires
    typingUsers.value = typingUsers.value.filter(u => u.name !== msg.sender_name)
    typingUsers.value.push({ name: msg.sender_name, expires: Date.now() + TYPING_TIMEOUT })
    // Авто-очистка
    setTimeout(() => {
      typingUsers.value = typingUsers.value.filter(u => u.expires > Date.now())
    }, TYPING_TIMEOUT + 100)
  }
}
```

---

### Фаза 2: Производительность

**2.1 Cursor-based pagination (Mobile)**
```javascript
// EmployeeChatRoomPage.vue:
const lastCursor = ref(null)
const hasMore = ref(true)

const loadMessages = async (cursor = null) => {
  const params = { limit: 50 }
  if (cursor) params.before_id = cursor
  const res = await api.get(`/api/v1/chats/${chatId}/messages`, { params })
  const newMsgs = res.data
  if (newMsgs.length < 50) hasMore.value = false
  if (newMsgs.length > 0) lastCursor.value = newMsgs[0].id
  messages.value = [...newMsgs, ...messages.value]
}
```

**Серверный endpoint (изменить параметры):**
```python
@router.get("/{chat_id}/messages")
async def get_messages(
    chat_id: int,
    limit: int = Query(50, ge=1, le=200),  # уменьшить max с 10000 до 200
    before_id: Optional[int] = None,  # cursor вместо offset
    ...
):
    q = session.query(InternalChatMessage).filter(
        InternalChatMessage.chat_id == chat_id,
        InternalChatMessage.is_deleted == False
    )
    if before_id:
        q = q.filter(InternalChatMessage.id < before_id)
    messages = q.order_by(InternalChatMessage.id.desc()).limit(limit).all()
    return list(reversed(messages))
```

**2.2 Индексы (критично)**
```sql
CREATE INDEX CONCURRENTLY idx_messages_chat_id_asc 
  ON internal_chat_messages(chat_id, id DESC)
  WHERE is_deleted = FALSE;

CREATE INDEX CONCURRENTLY idx_chat_member_chat_employee 
  ON internal_chat_members(chat_id, employee_id)
  WHERE is_active = TRUE;
```

**2.3 Batch unread counts (убрать N+1)**
```python
# chat_service.py
def get_all_accessible_chats_with_unread(db, employee_id, chat_type=None):
    chats = get_all_accessible_chats(db, employee_id, chat_type)
    chat_ids = [c.id for c in chats]
    
    # Одним запросом все unread
    member_rows = db.query(
        InternalChatMember.chat_id,
        InternalChatMember.last_read_message_id
    ).filter(
        InternalChatMember.chat_id.in_(chat_ids),
        InternalChatMember.employee_id == employee_id
    ).all()
    
    last_read_map = {r.chat_id: r.last_read_message_id for r in member_rows}
    
    # Подсчёт за один запрос (GROUP BY)
    from sqlalchemy import func, case
    unread_rows = db.query(
        InternalChatMessage.chat_id,
        func.count(InternalChatMessage.id).label('cnt')
    ).filter(
        InternalChatMessage.chat_id.in_(chat_ids),
        InternalChatMessage.is_deleted == False,
        InternalChatMessage.message_type != 'system',
        InternalChatMessage.sender_employee_id != employee_id
    ).filter(
        # id > last_read for each chat — через subquery per chat_id
        ...  # сложнее, но возможно через CASE или lateral join
    ).group_by(InternalChatMessage.chat_id).all()
    
    unread_map = {r.chat_id: r.cnt for r in unread_rows}
    return chats, unread_map
```

**2.4 Virtual scroll (Mobile)**
```vue
<!-- EmployeeChatRoomPage.vue: использовать q-virtual-scroll -->
<q-virtual-scroll
  ref="virtualScroll"
  :items="messages"
  :virtual-scroll-item-size="60"
  :virtual-scroll-sticky-size-start="36"
  v-slot="{ item: msg, index }"
>
  <chat-message-bubble :message="msg" :key="msg.id" />
</q-virtual-scroll>
```

Или Intersection Observer для infinite scroll:
```javascript
const observer = new IntersectionObserver(([entry]) => {
  if (entry.isIntersecting && hasMore.value) loadOlderMessages()
}, { threshold: 0.1 })
// observe topSentinel element
```

---

### Фаза 3: Паритет

**3.1 Скрипты в EmployeeChatRoomPage**
Добавить drawer/панель со скриптами (аналог ClientChatRoomPage):
```javascript
// Скопировать из ClientChatRoomPage:
const scripts = ref([])
const loadScripts = async () => {
  const r = await api.get('/api/v1/messenger/scripts', { params: { project_type: 'all' } })
  scripts.value = r.data
}
const selectScript = (s) => {
  inputText.value = fillScriptVars(s.message_template)
  scriptsDialog.value = false
}
```

**3.2 Поиск по сообщениям**

**Серверный endpoint:**
```python
@router.get("/{chat_id}/messages/search")
async def search_messages(
    chat_id: int,
    q: str = Query(..., min_length=2),
    limit: int = 20,
    ...
):
    # Full-text search через PostgreSQL tsvector
    from sqlalchemy import func, text
    results = session.query(InternalChatMessage).filter(
        InternalChatMessage.chat_id == chat_id,
        InternalChatMessage.is_deleted == False,
        func.to_tsvector('russian', InternalChatMessage.content)
            .op('@@')(func.plainto_tsquery('russian', q))
    ).order_by(InternalChatMessage.created_at.desc()).limit(limit).all()
    return results
```

**Desktop (chat_room_widget.py):**
```python
# Добавить поле поиска в шапку
self._search_input = QLineEdit()
self._search_input.setPlaceholderText("Поиск в чате...")
self._search_input.returnPressed.connect(self._search_messages)

def _search_messages(self):
    query = self._search_input.text().strip()
    if not query: return
    results = self._api_client.search_chat_messages(self._chat_id, query)
    # Показать результаты + scroll_to первому
```

---

## Приоритетная матрица

| Задача | Усилие | Влияние | Приоритет |
|--------|--------|---------|-----------|
| 1.1 activeChatId bug | 30 мин | Критично | 🔴 P0 |
| 1.3 Temp file leak | 30 мин | High | 🔴 P0 |
| 1.4 Typing timeout | 1 час | Medium | 🟡 P1 |
| 2.2 Индексы БД | 1 час | High | 🔴 P0 |
| 2.3 Batch unread | 2 часа | High | 🟡 P1 |
| 2.1 Pagination mobile | 4 часа | Critical (>1000 msg) | 🟡 P1 |
| 1.2 Guest delete | 2 часа | Medium | 🟡 P1 |
| 2.4 Virtual scroll | 6 часов | Medium | 🟢 P2 |
| 3.1 Скрипты в Employee | 3 часа | Medium | 🟢 P2 |
| 3.2 Поиск сообщений | 1 день | Medium | 🟢 P2 |
| 4.1 Реакции | 3 дня | Low | ✅ Готово |
| 4.2 Голосовые | 5 дней | Low | ✅ Готово |
