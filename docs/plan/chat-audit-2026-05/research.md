# Аудит чатов Interior Studio CRM — Research

**Дата:** 2026-05-04
**Режим:** qa+research (аналитика без реализации)
**Охват:** Desktop (PyQt5) + Mobile (Quasar/Vue3 PWA) + Server (FastAPI)

---

## 1. ДВЕ НЕЗАВИСИМЫЕ СИСТЕМЫ ЧАТОВ

Проект содержит две архитектурно разные системы:

| Система | Backend | Desktop | Mobile |
|---------|---------|---------|--------|
| **InternalChat** | chat_router.py + client_chat_router.py | chat_room_widget.py (полный) | EmployeeChatRoomPage.vue + ClientChatRoomPage.vue |
| **MessengerChat** | messenger_router.py | messenger_admin_dialog.py (управление) | messengerApi (создание/скрипты) |

InternalChat — встроенный чат системы (внутри CRM, WebSocket, файлы).
MessengerChat — интеграция с Telegram через MTProto (внешние группы).

---

## 2. МОДЕЛИ БД

```
InternalChat
  id, chat_type (employee|client), crm_card_id, supervision_card_id,
  contract_id, title, yandex_folder_path, client_access_token,
  created_by, created_at, is_active

InternalChatMember
  id, chat_id, member_type (employee|client_guest),
  employee_id, guest_name, guest_phone, guest_access_token,
  last_read_message_id, joined_at, is_active

InternalChatMessage
  id, chat_id, sender_employee_id, sender_guest_token,
  sender_display_name, message_type (text|voice|image|file|system),
  content, file_url, file_name, file_size, yandex_path,
  reply_to_id, group_id, is_pinned, is_deleted, is_edited, created_at

MessengerChat
  id, contract_id, crm_card_id, supervision_card_id, messenger_type,
  telegram_chat_id, chat_title, invite_link, avatar_type, creation_method,
  created_by, created_at, is_active
```

---

## 3. ФУНКЦИОНАЛЬНАЯ МАТРИЦА

| Функция | Desktop (ChatRoom) | Mobile (EmployeeChatRoom) | Mobile (ClientChatRoom) | Mobile (ClientPage no-auth) |
|---------|-------------------|--------------------------|------------------------|---------------------------|
| Отправка текста | ✅ | ✅ | ✅ | ✅ |
| Отправка файлов (20 max) | ✅ | ✅ | ✅ | ✅ |
| Редактирование текста | ✅ | ✅ | ✅ | ✅ |
| Удаление сообщений | ✅ сервер | ✅ сервер | ✅ сервер | ⚠️ только UI |
| Закрепление (pin) | ✅ до 10, навигация | ✅ до 10 | ✅ до 10 | ❌ |
| Пересылка | ✅ одиночное+группа | ✅ | ✅ | ❌ |
| Цитирование (reply) | ✅ + scroll_to | ✅ + scroll_to | ✅ + scroll_to | ✅ |
| Реакции | ❌ | ❌ | ❌ | ❌ |
| Поиск в чате | ❌ | ❌ | ❌ | ❌ |
| Typing indicator | ✅ | ✅ | ✅ | ✅ |
| Маркер непрочитанных | ✅ линия | ✅ линия | ✅ линия | ⚠️ localStorage |
| WebSocket (Real-time) | ✅ exp. backoff | ✅ exp. backoff | ✅ exp. backoff | ✅ exp. backoff |
| Ping/Pong | ✅ 30s | ✅ 25s | ✅ 25s | ✅ 25s |
| Галерея (group_id) | ✅ авто-layout | ✅ авто-grid | ✅ авто-grid | ❌ |
| PDF preview | ✅ fitz (PyMuPDF) | ✅ canvas | ✅ canvas | ✅ canvas |
| Async загрузка изображений | ✅ QNetworkAccessManager | ✅ URL.createObjectURL | ✅ | ✅ |
| Копирование файла в карточку | ✅ диалог+вариации | ✅ | ✅ | ❌ |
| Управление участниками | ✅ диалог | ✅ диалог | ✅ диалог | ❌ |
| Скрипты с переменными | ⚠️ только client tab | ❌ | ✅ | ❌ |
| Invite-ссылки | ✅ | ❌ | ✅ | ❌ |
| Телефон клиента | ✅ | ❌ | ✅ (by perm) | ❌ |
| Пагинация сообщений | ⚠️ limit=50, нет scroll | ❌ (ВСЕ) | ❌ (ВСЕ) | ⚠️ limit=50 |
| Virtual scroll | ❌ | ❌ | ❌ | ❌ |
| Голосовые сообщения | 🚧 заглушка | ❌ | ❌ | ❌ |
| Поиск по названию чата | ✅ | ✅ | ✅ | N/A |
| PWA Badge (иконка) | N/A | ❌ | ✅ | ✅ |
| Offline поведение | ❌ (polling fallback) | ❌ | ❌ | ❌ |
| Лимит размера файла | ✅ 50MB сервер | ❌ | ❌ | ❌ |
| Лимит типов файлов | ✅ server whitelist | ❌ (нет клиентск.) | ❌ | ❌ |

---

## 4. КЛЮЧЕВЫЕ РАСХОЖДЕНИЯ DESKTOP vs MOBILE

### Только в Desktop, нет в Mobile
1. Polling fallback при отсутствии WebSocket-клиента
2. PDF через PyMuPDF (fitz) — более качественный рендер
3. Закрепление с навигацией между N закреплёнными (1/3, 2/3...)
4. Поиск чатов в EmployeeChatsTab — fuzzy НЕТ, только substring
5. CardChatWidget с ленивой загрузкой
6. Голосовые — заглушка (только десктоп знает что это планировалось)
7. Ограничение max 20 файлов за раз — проверяется на стороне клиента

### Только в Mobile, нет в Desktop
1. PWA Badge обновление (setAppBadge)
2. Регистрация клиента при первом входе (ClientChatPage → ClientRegisterPage)
3. Двойная аутентификация токеном клиента (mainToken + memberToken)
4. Offline-индикатор "переподключение..." более явный
5. Блок установки PWA баннер
6. Показ "Вариации" при copyToCard более детален

### Паритет
- Typing indicator (оба)
- Маркер непрочитанных (оба, но клиент-мобил через localStorage)
- Управление участниками (оба)
- Галерея изображений (оба, разный layout)
- Закрепление (оба)
- Пересылка (оба)
- Цитирование (оба)
- PDF preview (разный механизм)

---

## 5. НАЙДЕННЫЕ БАГИ

### 🔴 Критичные

1. **ClientChatsPage.vue**: `activeChatId` никогда не устанавливается — нельзя создать invite-ссылку
2. **Пагинация Mobile**: EmployeeChatRoomPage и ClientChatRoomPage загружают ВСЕ сообщения (нет limit/offset) — деградирует при 1000+ сообщениях
3. **N+1 запросы в get_all_accessible_chats**: для каждого чата отдельный SELECT COUNT(*) — O(N×M)
4. **Temp files не удаляются**: client_chat_router.py `/stream` endpoint создаёт `NamedTemporaryFile(delete=False)` — утечка диска

### 🟡 Серьёзные

5. **Typing users не очищаются**: useChatWebSocket.js — если `typing_stop` не пришёл, пользователь "навсегда" печатает
6. **Удаление гостей только UI**: `ClientChatPage.vue::deleteClientMsg()` — не делает DELETE запрос, сообщение возвращается при перезагрузке
7. **Нет индекса (chat_id, created_at)**: на `internal_chat_messages` — при 100k+ сообщений full scan
8. **WebSocket без лимита соединений**: `ChatConnectionManager` не ограничивает количество соединений
9. **Mobile messengerApi.triggerScript**: вызывает `/messenger/scripts/{id}/trigger` — но endpoint `/trigger-script` принимает `{card_id, script_type}` — несоответствие URL

### 🟢 Средние

10. **CardChatWidget не обновляется**: `_data_loaded = True` навсегда, refresh не происходит
11. **group_id не валидируется**: клиент может подделать группировку чужих изображений
12. **Загрузка файлов в RAM**: весь файл читается в `file_bytes = await file.read()` (50 MB × N пользователей)
13. **CSRF не защищён для гостей**: POST /client-chat/{token}/messages без CSRF токена
14. **Максимум закреплённых**: 10 сообщений — при превышении самое старое откреп без уведомления

---

## 6. ПРОИЗВОДИТЕЛЬНОСТЬ

### Desktop (PyQt5)
- Рендеринг: полный перерисовка (`_render_all_messages`) при удалении/редактировании — O(N)
- Изображения: нет кэша, каждый открытие чата — повторная загрузка
- WebSocket: 30s ping, exp backoff 1→30s

### Mobile (Vue/Quasar)
- v-for без виртуального скролла — при 10000 сообщений DOM замораживается
- `recalcChatH()` при каждом resize — потенциально дорого
- `getPdfThumbnail()` через canvas — медленно для больших PDF
- chatUnread store: нет delta sync — каждый раз полный список

### Server (FastAPI)
- Самая критичная: N+1 в get_all_accessible_chats
- LIMIT/OFFSET pagination — деградирует при больших offset
- Файлы в RAM — 50MB × concurrent uploads = ОЗУ проблема
