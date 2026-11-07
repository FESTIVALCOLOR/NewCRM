# План реализации: Внутренний чат Interior Studio CRM

> **Дата:** 2026-04-11  
> **Ветка:** `feat/internal-chat`  
> **Статус:** На утверждении  
> **Оценка трудоёмкости:** ~25–35 рабочих дней  

---

## Оглавление

1. [Анализ существующего кода](#1-анализ-существующего-кода)
2. [Референсный код с GitHub](#2-референсный-код-с-github)
3. [Архитектура решения](#3-архитектура-решения)
4. [Фаза 0 — DB + Permissions](#фаза-0--db--permissions)
5. [Фаза 1 — Backend WebSocket API](#фаза-1--backend-websocket-api)
6. [Фаза 2 — Desktop: Чат сотрудников](#фаза-2--desktop-чат-сотрудников)
7. [Фаза 3 — Desktop: Чат с клиентами](#фаза-3--desktop-чат-с-клиентами)
8. [Фаза 4 — Mobile: Чат сотрудников](#фаза-4--mobile-чат-сотрудников)
9. [Фаза 5 — Mobile: Чат с клиентами](#фаза-5--mobile-чат-с-клиентами)
10. [Фаза 6 — Client PWA (ссылочный доступ)](#фаза-6--client-pwa-ссылочный-доступ)
11. [Фаза 7 — Права, уведомления, скрипты](#фаза-7--права-уведомления-скрипты)
12. [Фаза 8 — Бекапы и очистка](#фаза-8--бекапы-и-очистка)
13. [Граф зависимостей](#граф-зависимостей)
14. [Риски и решения](#риски-и-решения)

---

## 1. Анализ существующего кода

### Текущее состояние (что есть)

| Компонент | Файл | Описание |
|-----------|------|----------|
| Desktop вкладки | `ui/main_window.py:1265` | Таб-бар: Клиенты, Договора, СРМ, СРМ надзора, Отчеты, Сотрудники, Зарплаты |
| Карточка CRM | `ui/crm_card_edit_dialog.py:1123` | Вкладки: Исполнители и дедлайн, Таблица сроков, Данные по проекту, История, Оплаты |
| Голосовые заметки (mobile) | `mobile/src/components/VoiceRecorder.vue` | MediaRecorder API, загрузка на ЯД |
| Заметки в карточке (mobile) | `mobile/src/pages/CrmCardPage.vue:98` | Вкладка "Заметки" — текст + голос |
| Telegram чат (mobile) | `mobile/src/pages/CrmCardPage.vue:97` | Вкладка "Чат" — управление Telegram-группой |
| Telegram DB модели | `server/database.py:910` | `MessengerChat`, `MessengerChatMember`, `MessengerScript` |
| Права мессенджера | `server/permissions.py:97` | `messenger.create_chat`, `messenger.delete_chat`, `messenger.view_chat`, `messenger.manage_scripts` |
| Роли по умолчанию | `server/permissions.py:154` | Руководитель/Ст.менеджер — полный доступ; СДП/ГАП/ДАН — только просмотр |

### Ключевые зависимости

- **VoiceRecorder.vue** → переиспользуем в чате как есть
- **ЯД интеграция** → файлы чата → папка `/disk:/CRM/Чаты/{card_id}/`
- **DataAccess** → все CRUD через DataAccess, не напрямую
- **PyQt Signal Safety** → emit через `QTimer.singleShot(0, ...)`
- **MessengerScript** → переиспользуем для скриптов клиентского чата
- **permissions.py** → расширяем новыми правами `chat.*`

---

## 2. Референсный код с GitHub

### Сервер (FastAPI + WebSocket)
**Репозиторий:** [notarious2/fastapi-chat](https://github.com/notarious2/fastapi-chat)  
**Стек:** FastAPI, WebSockets, SQLAlchemy 2, Redis PubSub, PostgreSQL  
**Использовать:**
- Паттерн `ConnectionManager` для хранения активных WebSocket-соединений по `chat_id`
- Схема подтверждения доставки: `sending → sent → read`
- Схема `last_read_message_id` (одно поле на участника) вместо флага на каждое сообщение
- Индикатор "печатает..." через WebSocket events
- Отслеживание online/offline статуса

**Адаптация под наш стек:**
- Убрать Redis (наш масштаб не требует горизонтального масштабирования)
- JWT auth из нашего `auth.py` вместо HTTP-only cookies
- SQLAlchemy sync (наш проект синхронный) вместо async
- Интеграция в существующий `docker-compose.yml`

### Frontend (Vue 3)
**Quasar встроенный компонент:** `q-chat-message`  
Поддерживает: `name`, `text`, `stamp` (время), `sent` (bool — правая сторона), `avatar`, `bg-color`  
→ Использовать как основу для обоих чатов в mobile

### Desktop (PyQt5)
Нет готовых библиотек. Реализовать паттерн из проекта:
- `QScrollArea` + `QWidget` + `QVBoxLayout` для списка сообщений
- Кастомный `MessageBubble(QFrame)` — с выравниванием влево/вправо
- Цвета: чужие `#F5F5F5` слева, свои `#FFF3CD` (жёлтые, под фирстиль) справа

---

## 3. Архитектура решения

### Новые DB-таблицы

```
internal_chats
├── id, chat_type (employee|client), crm_card_id, supervision_card_id
├── title (адрес объекта)
│   yandex_folder_path — подпапка ВНУТРИ папки карточки:
│     чат сотрудников → {contract.yandex_folder_path}/Чат сотрудников
│     чат с клиентом  → {contract.yandex_folder_path}/Чат с клиентом
├── client_access_token (UUID, только для client-чата)
├── created_by, created_at, is_active

internal_chat_members
├── id, chat_id → internal_chats.id
├── member_type (employee|client_guest)
├── employee_id → employees.id (nullable)
├── guest_name, guest_phone, guest_access_token (UUID)
├── last_read_message_id, joined_at

internal_chat_messages
├── id, chat_id → internal_chats.id
├── sender_employee_id (nullable), sender_guest_token (nullable)
├── sender_display_name
├── message_type (text|voice|image|file|system)
├── content (текст или null)
├── file_url (ЯД ссылка), file_name, file_size
├── yandex_path (disk:/CRM/Чаты/...)
├── is_deleted, created_at

internal_chat_message_reactions (опционально, фаза 2)
```

### Новые права (permissions.py)

```python
# Чат сотрудников
"chat.employee.view"          — просмотр чатов сотрудников (по заказу)
"chat.employee.send"          — отправка сообщений в чат сотрудников
"chat.employee.manage"        — добавление участников, управление чатом
"chat.employee.upload_to_data" — загрузка файлов из чата в "Данные проекта"

# Чат с клиентами
"chat.client.view"            — просмотр клиентских чатов
"chat.client.send"            — отправка сообщений клиенту
"chat.client.manage"          — создание/удаление чата, добавление участников
"chat.client.send_script"     — отправка скриптов клиенту

# Уведомления чата
"chat.notifications"          — настройка уведомлений чата
```

### Матрица доступа по умолчанию

| Роль | employee.view | employee.send | employee.manage | employee.upload_to_data | client.view | client.send | client.manage | client.send_script |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Руководитель | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ст. менеджер | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| СДП | ✅ | ✅ | ➖ | ✅ | ✅ | ✅ | ➖ | ✅ |
| ГАП | ✅ | ✅ | ➖ | ✅ | ✅ | ✅ | ➖ | ✅ |
| Менеджер | ✅ | ✅ | ➖ | ➖ | ✅ | ✅ | ✅ | ✅ |
| ДАН | ✅ | ✅ | ➖ | ➖ | ➖ | ➖ | ➖ | ➖ |
| Дизайнер | ✅ | ✅ | ➖ | ✅* | ➖ | ➖ | ➖ | ➖ |
| Чертёжник | ✅ | ✅ | ➖ | ✅* | ➖ | ➖ | ➖ | ➖ |

*только для стадий, доступных по роли

### WebSocket события

```json
// Клиент → сервер
{ "type": "message", "content": "текст", "message_type": "text" }
{ "type": "typing_start" }
{ "type": "typing_stop" }
{ "type": "read", "last_read_id": 42 }

// Сервер → клиент
{ "type": "new_message", "message": {...} }
{ "type": "typing", "sender_id": 5, "sender_name": "Иван" }
{ "type": "read_receipt", "reader_id": 5, "last_read_id": 42 }
{ "type": "member_joined", "member": {...} }
{ "type": "system", "content": "Алина Иванова добавлена в чат" }
```

---

## Фаза 0 — DB + Permissions

**Трудоёмкость:** 1–2 дня  
**Ветка:** `feat/internal-chat`  
**Файлы:** `server/database.py`, `server/permissions.py`, `server/schemas.py`

### 0.1 database.py — новые модели

```python
class InternalChat(Base):
    __tablename__ = "internal_chats"
    id, chat_type, crm_card_id, supervision_card_id,
    title, yandex_folder_path,
    client_access_token (UUID),
    created_by, created_at, is_active

class InternalChatMember(Base):
    __tablename__ = "internal_chat_members"
    id, chat_id (FK cascade), member_type,
    employee_id, guest_name, guest_phone, guest_access_token,
    last_read_message_id, joined_at

class InternalChatMessage(Base):
    __tablename__ = "internal_chat_messages"
    id, chat_id (FK cascade), sender_employee_id, sender_guest_token,
    sender_display_name, message_type, content,
    file_url, file_name, file_size, yandex_path,
    is_deleted, created_at
```

### 0.2 permissions.py — 8 новых прав

Добавить в `ALL_PERMISSIONS` и `DEFAULT_ROLE_PERMISSIONS` согласно матрице выше.

### 0.3 schemas.py — Pydantic схемы

```
InternalChatCreate, InternalChatResponse
InternalMessageCreate, InternalMessageResponse
ChatMemberCreate, ChatMemberResponse
GuestRegistration (имя + телефон)
FileUploadToChatRequest
FileUploadToDataRequest (stage, variation_type)
```

### 0.4 Миграция DB

```sql
CREATE TABLE internal_chats (...);
CREATE TABLE internal_chat_members (...);
CREATE TABLE internal_chat_messages (...);
```

Добавить в `server/database.py` и Docker rebuild.

---

## Фаза 1 — Backend WebSocket API

**Трудоёмкость:** 3–4 дня  
**Файлы:** `server/routers/chat_router.py` (новый), `server/services/chat_service.py` (новый)

### 1.1 REST endpoints

```
POST   /api/internal-chats/                      — создать чат
GET    /api/internal-chats/                      — список чатов сотрудника (по card_id или глобально)
GET    /api/internal-chats/{chat_id}             — детали чата
DELETE /api/internal-chats/{chat_id}             — удалить чат (cascade: члены + сообщения + ЯД папка)

GET    /api/internal-chats/{chat_id}/messages    — история сообщений (пагинация, limit/offset)
POST   /api/internal-chats/{chat_id}/messages    — отправить сообщение (текст)
DELETE /api/internal-chats/{chat_id}/messages/{msg_id} — удалить своё сообщение

POST   /api/internal-chats/{chat_id}/members    — добавить участника
DELETE /api/internal-chats/{chat_id}/members/{member_id} — удалить участника

POST   /api/internal-chats/{chat_id}/files      — загрузить файл/голос → ЯД → сообщение
POST   /api/internal-chats/{chat_id}/upload-to-data — загрузить файл из чата в данные проекта

# Клиентский доступ (без JWT, по токену)
GET    /api/client-chat/{token}                 — получить чат по ссылке
POST   /api/client-chat/{token}/register        — первый вход: имя + телефон
GET    /api/client-chat/{token}/messages        — история
POST   /api/client-chat/{token}/messages        — отправить сообщение
POST   /api/client-chat/{token}/files           — загрузить файл

# Ссылки для клиентов
POST   /api/internal-chats/{chat_id}/invite-links  — создать новую ссылку (UUID токен)
GET    /api/internal-chats/{chat_id}/invite-links  — список ссылок
DELETE /api/internal-chats/{chat_id}/invite-links/{token} — отозвать ссылку

# Скрипты в клиентский чат
GET    /api/internal-chats/{chat_id}/scripts    — доступные скрипты
POST   /api/internal-chats/{chat_id}/scripts/{script_id}/send  — отправить скрипт
```

### 1.2 WebSocket endpoints

```
WS /ws/chat/{chat_id}?token=JWT          — сотрудник
WS /ws/client-chat/{access_token}        — клиент (без JWT)
```

**ConnectionManager** (аналог notarious2/fastapi-chat):
```python
class ChatConnectionManager:
    # {chat_id: {employee_id: WebSocket}}
    active_connections: dict

    async def connect(chat_id, employee_id, ws)
    async def disconnect(chat_id, employee_id)
    async def broadcast(chat_id, message_dict, exclude=None)
    async def send_personal(chat_id, employee_id, message_dict)
```

### 1.3 chat_service.py

- `create_employee_chat(card_id, created_by_id)` — создаёт чат + автоматически добавляет всех назначенных сотрудников
- `create_client_chat(card_id, created_by_id)` — создаёт чат + генерирует UUID токен + создаёт ЯД папку
- `add_message(chat_id, sender, content, msg_type)` — сохраняет + broadcast WebSocket
- `upload_file_to_chat(chat_id, file_bytes, filename)` — загружает на ЯД → создаёт сообщение с ссылкой
- `upload_to_project_data(chat_id, msg_id, stage, variation)` — копирует файл из папки чата в папку данных проекта
- `forward_to_employee_chat(from_chat_id, msg_id, to_chat_id)` — пересылка

### 1.4 Уведомления о новых сообщениях

- Если получатель не подключён к WebSocket → отправить push через `notifications_router` (internal notification)
- Бейдж с числом непрочитанных на иконке чата в sidebar (мобиль) / счётчик в таб-баре (desktop)

---

## Фаза 2 — Desktop: Чат сотрудников

**Трудоёмкость:** 4–5 дней  
**Файлы новые:** `ui/employee_chats_tab.py`, `ui/chat_room_widget.py`, `ui/chat_message_bubble.py`  
**Файлы изменяемые:** `ui/main_window.py`, `ui/crm_card_edit_dialog.py`

### 2.1 Новая главная вкладка "Чаты сотрудников"

**`ui/employee_chats_tab.py`** — аналог `crm_tab.py`

Структура:
```
EmployeeChatsTab (QWidget)
├── QSplitter (горизонтальный)
│   ├── LEFT: ChatListWidget
│   │   ├── QLineEdit (поиск по адресу)
│   │   ├── QListWidget (список чатов)
│   │   │   └── ChatListItem: заголовок, последнее сообщение, время, бейдж непрочитанных
│   └── RIGHT: ChatRoomWidget (или заглушка "Выберите чат")
```

Поведение:
- Список фильтруется: **только чаты, где текущий сотрудник является участником** (backend фильтрует по employee_id)
- Клик → открывает ChatRoomWidget в правой панели
- Бейдж обновляется через WebSocket

**Добавить в `main_window.py:1265`:**
```python
if can('chat.employee.view'):
    tab_configs.append(('  Чаты сотрудников  ', 'employee_chats_tab',
        lambda: EmployeeChatsTab(self._employee, self._api_client), ...))
```

### 2.2 ChatRoomWidget (основной виджет чата)

**`ui/chat_room_widget.py`**

```
ChatRoomWidget (QWidget)
├── Header: название чата + кнопка "Участники" + кнопка "Загрузить в данные" (если право)
├── QScrollArea → MessagesContainer
│   └── MessageBubble × N
├── InputPanel
│   ├── QTextEdit (многострочный, Enter = отправить, Shift+Enter = перенос)
│   ├── QPushButton (скрепка) → выбор файла/изображения
│   ├── VoiceButton → запись голосового (QAudioRecorder или Python sounddevice)
│   └── QPushButton "Отправить"
└── TypingIndicator ("Иван печатает...")
```

**WebSocket клиент на desktop:**  
Использовать `websocket-client` в threading.Thread. Emit сигналов через `QTimer.singleShot(0, ...)` для thread safety.

```python
class ChatWebSocketWorker(QThread):
    message_received = pyqtSignal(dict)
    typing_event = pyqtSignal(str)
    
    def run(self):
        ws = websocket.WebSocketApp(url, ...)
        ws.run_forever()
```

### 2.3 MessageBubble (пузырь сообщения)

**`ui/chat_message_bubble.py`**

```python
class MessageBubble(QFrame):
    """
    Слева: чужие сообщения (bg #F5F5F5, align LEFT)
    Справа: свои (bg #FFF8DC, align RIGHT)
    """
    def __init__(self, message: dict, is_own: bool):
        # sender_name (QLabel, bold)
        # content_widget:
        #   text → QLabel (word wrap)
        #   voice → QMediaPlayer controls
        #   image → QLabel + pixmap (thumbnail 200px)
        #   file → QLabel + ссылка/кнопка скачать
        # timestamp (QLabel, grey, 10px)
        # read_status (галочки ✓✓ для отправленных)
```

**Стиль:**
```css
/* Чужое сообщение */
QFrame[bubbleType="other"] {
    background: #F5F5F5;
    border-radius: 12px;
    margin-right: 60px;
}
/* Своё сообщение */
QFrame[bubbleType="own"] {
    background: #FFF8DC;
    border-radius: 12px;
    margin-left: 60px;
}
```

### 2.4 Диалог участников чата

**Внутри `chat_room_widget.py`** — кнопка "Участники" открывает `ChatMembersDialog`:
- Список текущих участников с ролью в проекте
- Кнопка "Добавить" → список назначенных на заказ сотрудников (которых ещё нет в чате)
- Кнопка "Удалить" (если `chat.employee.manage`)

### 2.5 Загрузка файлов в "Данные проекта"

**Кнопка в заголовке чата** (только при `chat.employee.upload_to_data`):
→ Диалог `UploadToProjectDataDialog`:
```
UploadToProjectDataDialog
├── ComboBox "Выберите стадию" (из timeline этапов карточки)
├── ComboBox "Тип" (основной проект / вариация)
├── QListWidget — выбор файлов из сообщений чата
├── CheckBox "Это правки" → создать папку "Исправления"
└── Кнопка "Загрузить"
```
Доступность стадий — строго по матрице прав (как в текущем tab "Данные по проекту").

### 2.6 Редизайн вкладки "История" в карточке CRM → "Заметки/Чат"

В `crm_card_edit_dialog.py` — вкладка "История по проекту" остаётся, но **добавляется новая вкладка "Чат сотрудников"**:
- Открывает `ChatRoomWidget` для чата, связанного с данной карточкой
- Если чат не создан — кнопка "Создать чат" (при наличии права `chat.employee.manage`)
- Чат создаётся автоматически при первом открытии для Ст.менеджера/Руководителя

---

## Фаза 3 — Desktop: Чат с клиентами

**Трудоёмкость:** 3–4 дня  
**Файлы новые:** `ui/client_chats_tab.py`  
**Файлы изменяемые:** `ui/crm_card_edit_dialog.py`, `ui/crm_dialogs.py`

### 3.1 Новая главная вкладка "Чаты с клиентами"

**`ui/client_chats_tab.py`** — аналог EmployeeChatsTab

Отличия:
- Список: только чаты типа `client`, где текущий сотрудник — участник
- Правая панель: `ChatRoomWidget` с дополнительной кнопкой "Отправить скрипт"
- Баннер с ссылками для клиентов (кнопка "Поделиться ссылкой")

**Добавить в `main_window.py`:**
```python
if can('chat.client.view'):
    tab_configs.append(('  Чаты с клиентами  ', 'client_chats_tab', ...))
```

### 3.2 Редизайн вкладки "Чат" в карточке → "Чат с клиентом"

**Текущий код** (`crm_card_edit_dialog.py:6910`) — управление Telegram-чатом.  
**Новое:** вкладка "Чат с клиентом" с `ChatRoomWidget(chat_type='client')`.

- Кнопка "Создать чат для клиента" → `chat_service.create_client_chat()`
- Кнопки управления ссылками: "Создать ссылку", "Скопировать", "Отправить на email"
- Диалог добавления представителя заказчика (`AddClientRepresentativeDialog`)
- Старые кнопки Telegram (`create_chat_btn`, `delete_chat_btn`, `open_chat_btn`) — удалить

### 3.3 Кнопка "Отправить скрипт"

Переиспользует `MessengerScriptPreviewDialog` из `crm_dialogs.py:4955` — но вместо отправки в Telegram → отправка в `InternalChat` через API.

### 3.4 Пересылка сообщений

**Контекстное меню** на MessageBubble (ПКМ):
- "Переслать в чат сотрудников" → выбор чата из списка → `forward_to_employee_chat()`

---

## Фаза 4 — Mobile: Чат сотрудников

**Трудоёмкость:** 3 дня  
**Файлы новые:** `mobile/src/pages/EmployeeChatsPage.vue`, `mobile/src/pages/EmployeeChatRoomPage.vue`  
**Файлы изменяемые:** `mobile/src/layouts/MainLayout.vue`, `mobile/src/pages/CrmCardPage.vue`

### 4.1 Новые страницы

**EmployeeChatsPage.vue:**
```vue
<q-list>
  <q-item v-for="chat in chats" clickable @click="openRoom(chat.id)">
    <q-item-section avatar>
      <q-icon name="group" />
    </q-item-section>
    <q-item-section>
      <q-item-label>{{ chat.title }}</q-item-label>
      <q-item-label caption>{{ chat.last_message }}</q-item-label>
    </q-item-section>
    <q-badge v-if="chat.unread > 0" color="red" floating>{{ chat.unread }}</q-badge>
  </q-item>
</q-list>
```

**EmployeeChatRoomPage.vue:**
```vue
<!-- Список сообщений через Quasar q-chat-message -->
<q-chat-message
  v-for="msg in messages" :key="msg.id"
  :name="msg.sender_display_name"
  :text="[msg.content]"
  :stamp="formatTime(msg.created_at)"
  :sent="msg.sender_employee_id === currentUser.id"
  :bg-color="msg.sender_employee_id === currentUser.id ? 'amber-1' : 'grey-2'"
/>
<!-- Голосовые: audio player вместо text -->
<!-- Изображения: q-img thumbnail -->
<!-- Файлы: q-item с иконкой и ссылкой -->

<!-- Input bar -->
<q-footer>
  <q-toolbar>
    <q-btn round flat icon="attach_file" @click="attachFile" />
    <VoiceRecorder @uploaded="onVoiceUploaded" />
    <q-input v-model="text" filled autogrow placeholder="Сообщение..." />
    <q-btn round flat icon="send" @click="sendMessage" />
  </q-toolbar>
</q-footer>
```

**WebSocket (mobile):** нативный браузерный `WebSocket` → обновление списка сообщений через `ref`.

### 4.2 Редизайн вкладки "Заметки" → "Чат сотрудников" в CrmCardPage.vue

Вкладка `notes` переименовывается в `employee_chat`.  
Старый UI (textarea + список заметок) → `EmployeeChatRoomPage.vue` встроенный.

### 4.3 Роутер

```javascript
// mobile/src/router/routes.js
{ path: '/employee-chats', component: EmployeeChatsPage, meta: { perm: 'chat.employee.view' } },
{ path: '/employee-chats/:id', component: EmployeeChatRoomPage },
```

### 4.4 Навигация в MainLayout.vue

Добавить пункт меню "Чаты сотрудников" (иконка `group`) с баджем непрочитанных.

---

## Фаза 5 — Mobile: Чат с клиентами

**Трудоёмкость:** 3 дня  
**Файлы новые:** `mobile/src/pages/ClientChatsPage.vue`, `mobile/src/pages/ClientChatRoomPage.vue`  
**Файлы изменяемые:** `mobile/src/pages/CrmCardPage.vue`

### 5.1 Новые страницы

Аналогично Фазе 4, но:
- Дополнительная панель **"Скрипты"** (выпадающий список → отправить скрипт)
- Кнопка **"Добавить представителя"** → диалог с ссылкой
- Кнопка **"Переслать"** на каждом сообщении
- Отображение имени и телефона при нажатии на имя участника (q-popup-proxy)

### 5.2 Редизайн вкладки "Чат" в CrmCardPage.vue

Вкладка `chat` (текущий Telegram-чат) → `ClientChatRoomPage.vue` встроенный.  
Убрать всю Telegram-логику (`tgDeepLink`, `chatData.invite_link`, кнопки "Создать чат в Telegram").

---

## Фаза 6 — Client PWA (ссылочный доступ)

**Трудоёмкость:** 4–5 дней  
**Файлы новые:**  
`mobile/src/pages/ClientChatPage.vue` — страница клиентского чата  
`mobile/src/pages/ClientRegisterPage.vue` — регистрация при первом входе  
`mobile/src/layouts/ClientLayout.vue` — минималистичный layout (без auth)  

### 6.1 Маршрутизация без авторизации

```javascript
// routes.js — публичные маршруты (без guard)
{ 
  path: '/c/:token', 
  component: ClientRegisterPage,  // если guest_name не заполнен
  meta: { public: true }
},
{ 
  path: '/c/:token/chat', 
  component: ClientChatPage,
  meta: { public: true }
}
```

**Navigation guard:** если токен существует в DB и `guest_name` заполнен → сразу в `/c/:token/chat`.

### 6.2 ClientRegisterPage.vue

```
При первом входе по ссылке:
┌────────────────────────────────┐
│  Добро пожаловать!             │
│  Введите ваши данные для чата  │
│                                │
│  [Имя] ___________________     │
│  [Телефон] +7 (___) ___-__-__ │
│                                │
│  [Войти в чат]                 │
└────────────────────────────────┘
```

- Валидация телефона: маска `+7 (XXX) XXX-XX-XX`
- POST `/api/client-chat/{token}/register` → сохраняет `guest_name`, `guest_phone`
- Перенаправление в `/c/{token}/chat`

### 6.3 ClientChatPage.vue

Полностью синхронизирован с `InternalChat` через WebSocket `/ws/client-chat/{token}`:

```
ClientLayout (без header авторизации)
├── Заголовок: название объекта + "Чат с бюро"
├── Список сообщений (q-chat-message)
│   ├── Сотрудники — слева (bg grey-2)
│   └── Свои — справа (bg amber-1)
├── Клик на имя → q-popup-proxy с номером телефона
└── Input: текст + файл/фото + голос
```

**Особенности:**
- WebSocket держит соединение, получает новые сообщения в реальном времени
- При потере соединения — polling каждые 5 сек (fallback)
- Голосовые — через `VoiceRecorder.vue` (тот же компонент)

### 6.4 Ссылка в пригласительном письме

**Текущее письмо** использует Telegram ссылку.  
**Новое:** заменить на `https://crm.yourdomain.ru/c/{access_token}`

Изменения в `server/services/notification_service.py`:
```python
# Старое: telegram_invite_link
# Новое:
client_chat_url = f"https://your-domain.ru/c/{chat.client_access_token}"
```

### 6.5 Диалог "Добавить в чат" (для сотрудников)

В `ClientChatRoomPage.vue` — кнопка "Добавить представителя":
```
AddRepresentativeDialog
├── Информация: "Будет создана отдельная ссылка для нового участника"
├── Кнопка "Создать ссылку" → POST /api/internal-chats/{id}/invite-links
├── Результат:
│   ├── [Скопировать ссылку] (clipboard)
│   └── Отправить на email:
│       ├── Input: email адрес
│       └── Кнопка "Отправить"
```

---

## Фаза 7 — Права, уведомления, скрипты

**Трудоёмкость:** 2–3 дня  
**Файлы:** `server/permissions.py`, `ui/permissions_matrix_widget.py`, `ui/notification_settings_widget.py`, `mobile/src/pages/AdminPage.vue`, `mobile/src/pages/NotificationSettingsPage.vue`

### 7.1 Матрица прав (admin UI)

**`ui/permissions_matrix_widget.py`** и **`mobile/src/pages/AdminPage.vue`**:

Добавить секцию "Чат сотрудников" и "Чат с клиентами":
```python
# permissions_matrix_widget.py — добавить группу
PERM_GROUPS = {
    ...
    "Чат сотрудников": [
        "chat.employee.view", "chat.employee.send",
        "chat.employee.manage", "chat.employee.upload_to_data"
    ],
    "Чат с клиентами": [
        "chat.client.view", "chat.client.send",
        "chat.client.manage", "chat.client.send_script"
    ],
}
```

### 7.2 Уведомления чата (internal, не Telegram)

**Замена Telegram → внутренние push-уведомления:**

Таблица `notifications` уже существует. При новом сообщении в чате:
- Если получатель не онлайн в WebSocket → создать запись `Notification(employee_id, type='chat_message', chat_id, preview)`
- `notifications_list_widget.py` — добавить тип `chat_message` с кликом → открыть чат

**`ui/notification_settings_widget.py`** — добавить настройки:
- "Уведомлять о новых сообщениях в чате сотрудников"
- "Уведомлять о новых сообщениях от клиентов"

**`mobile/src/pages/NotificationSettingsPage.vue`** — аналогично.

### 7.3 Пригласительное письмо (переработка)

**Текущее:** содержит инструкцию по добавлению в Telegram-бот + ссылку.  
**Новое:** заменить на ссылку внутреннего чата.

`server/services/notification_service.py` — функция `send_invitation_email()`:
```python
# Убрать: telegram_bot_link, telegram_instructions
# Добавить: client_chat_url = f"https://domain.ru/c/{token}"
```

### 7.4 Скрипты клиентского чата

Существующая таблица `MessengerScript` — оставить как есть.  
Новый endpoint `POST /api/internal-chats/{chat_id}/scripts/{script_id}/send`:
- Рендерит шаблон скрипта через `notification_service.build_script_context()`
- Отправляет как сообщение в `InternalChat` (не в Telegram)

**Автоматические скрипты** — `trigger_messenger_notification()` теперь создаёт сообщение в чате, а не в Telegram:
```python
# Старое: send_to_telegram_chat(chat_id, message)
# Новое: create_internal_chat_message(card_id, message, sender='system')
```

---

## Фаза 8 — Бекапы и очистка

**Трудоёмкость:** 1–2 дня  
**Файлы:** `server/services/maintenance_service.py` (новый), `docker-compose.yml`, `nginx/`

### 8.1 Ежедневные бекапы чатов

**Cron задача (docker-compose service `backup`):**
```bash
# Ежедневно в 03:00
pg_dump -t internal_chats -t internal_chat_members -t internal_chat_messages \
    interior_studio | gzip > /backups/chat_$(date +%Y%m%d).sql.gz
```

**Удаление бекапов старше 30 дней:**
```bash
find /backups -name "chat_*.sql.gz" -mtime +30 -delete
```

**Добавить в `docker-compose.yml`:**
```yaml
backup:
  image: postgres:15
  volumes:
    - ./backups:/backups
  command: >
    sh -c "while true; do
      sleep 86400;
      pg_dump ... | gzip > /backups/chat_$$(date +%Y%m%d).sql.gz;
      find /backups -name 'chat_*.sql.gz' -mtime +30 -delete;
    done"
```

### 8.2 Очистка файлов на Яндекс Диске

**При удалении чата** (`DELETE /api/internal-chats/{chat_id}`):
```python
async def delete_chat(chat_id):
    chat = db.query(InternalChat).get(chat_id)
    # Удалить папку ЯД
    yandex_disk.delete(chat.yandex_folder_path)
    # Cascade удаляет сообщения и членов
    db.delete(chat)
```

**Очистка файлов старше 6 месяцев** (scheduler через APScheduler или cron):
```python
# server/services/maintenance_service.py
def cleanup_old_chat_files():
    cutoff = datetime.utcnow() - timedelta(days=180)
    old_files = db.query(InternalChatMessage).filter(
        InternalChatMessage.file_url.isnot(None),
        InternalChatMessage.created_at < cutoff,
        InternalChatMessage.yandex_path.isnot(None)
    ).all()
    for msg in old_files:
        yandex_disk.delete(msg.yandex_path)
        msg.file_url = None
        msg.yandex_path = None
        msg.content = "[Файл удалён по истечении срока хранения]"
```

**Расписание:** APScheduler (уже в requirements?) или отдельный cron-контейнер.

---

## Граф зависимостей

```
Фаза 0 (DB + Perms)
    └── Фаза 1 (Backend API)
            ├── Фаза 2 (Desktop: чат сотрудников)
            ├── Фаза 3 (Desktop: чат с клиентами) ← зависит от Фазы 2 (переиспользует ChatRoomWidget)
            ├── Фаза 4 (Mobile: чат сотрудников)
            ├── Фаза 5 (Mobile: чат с клиентами) ← зависит от Фазы 4
            └── Фаза 6 (Client PWA)
                    └── Фаза 7 (Права + Уведомления)
                                └── Фаза 8 (Бекапы)
```

**Параллелизм:**
- Фазы 2, 4, 6 можно начать параллельно после завершения Фазы 1
- Фаза 3 стартует после Фазы 2 (переиспользует ChatRoomWidget)
- Фаза 5 стартует после Фазы 4
- Фаза 7 — в конце, после всех UI

---

## Риски и решения

| Риск | Вероятность | Решение |
|------|:-----------:|---------|
| WebSocket нестабилен на десктопе (PyQt5 threading) | Средняя | QThread + `QTimer.singleShot(0, ...)` per CLAUDE.md; fallback polling каждые 30 сек |
| Большое количество сообщений → OOM при загрузке | Средняя | Пагинация: загрузка по 50 сообщений, виртуальный скролл (QListView с моделью) |
| ЯД API rate limiting при массовой загрузке | Низкая | Очередь загрузок (threading.Queue), max 3 параллельных запроса |
| Клиентская PWA — поддержка WebSocket на старых iOS | Средняя | Fallback: long polling каждые 3 сек через обычный HTTP |
| Пересечение с текущим Telegram-функционалом | Высокая | Оставить таблицы `messenger_chats` нетронутыми; новый код — отдельные таблицы; постепенный переход |
| Производительность PostgreSQL при > 10K сообщений | Низкая | Индексы: `(chat_id, created_at)`, `(sender_employee_id)` |
| UUID токены для клиентов — безопасность | Средняя | UUID v4 (128 бит), HTTPS only, токен одного представителя = его личная ссылка |

---

## Новые файлы (итого)

### Server
- `server/routers/chat_router.py` — REST + WebSocket endpoints
- `server/services/chat_service.py` — бизнес-логика чата
- `server/services/maintenance_service.py` — бекапы и очистка

### Desktop (ui/)
- `ui/employee_chats_tab.py` — главная вкладка чатов сотрудников
- `ui/client_chats_tab.py` — главная вкладка клиентских чатов
- `ui/chat_room_widget.py` — универсальный виджет чат-комнаты
- `ui/chat_message_bubble.py` — пузырь сообщения (WhatsApp стиль)

### Mobile
- `mobile/src/pages/EmployeeChatsPage.vue`
- `mobile/src/pages/EmployeeChatRoomPage.vue`
- `mobile/src/pages/ClientChatsPage.vue`
- `mobile/src/pages/ClientChatRoomPage.vue`
- `mobile/src/pages/ClientChatPage.vue` (клиентская PWA)
- `mobile/src/pages/ClientRegisterPage.vue`
- `mobile/src/layouts/ClientLayout.vue`

### Изменяемые файлы
- `server/database.py` — 3 новые таблицы
- `server/permissions.py` — 8 новых прав
- `server/schemas.py` — новые схемы
- `server/services/notification_service.py` — переход с Telegram на internal
- `ui/main_window.py` — 2 новых таба
- `ui/crm_card_edit_dialog.py` — новая вкладка чата в карточке
- `ui/crm_dialogs.py` — скрипты → internal chat
- `ui/permissions_matrix_widget.py` — новые группы прав
- `ui/notification_settings_widget.py` — настройки чата
- `mobile/src/pages/CrmCardPage.vue` — редизайн вкладок
- `mobile/src/layouts/MainLayout.vue` — новые пункты меню
- `mobile/src/pages/AdminPage.vue` — матрица прав
- `docker-compose.yml` — backup service
