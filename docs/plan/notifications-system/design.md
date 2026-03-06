# Дизайн: Система уведомлений
Дата: 2026-03-06 | Статус: ФИНАЛЬНЫЙ ДИЗАЙН

---

## 1. C4 Model

### 1.1 Container Diagram — Место системы уведомлений в архитектуре

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Interior Studio CRM — System Boundary                                  │
│                                                                         │
│  ┌───────────────────────┐         ┌──────────────────────────────────┐ │
│  │  PyQt5 Desktop Client │         │       FastAPI Server             │ │
│  │  (Python 3.14)        │         │       (Python 3.11 / Docker)     │ │
│  │                       │         │                                  │ │
│  │  ┌─────────────────┐  │  HTTPS  │  ┌──────────────────────────┐   │ │
│  │  │  AdminDialog    │◄─┼─────────┼─►│  notifications_router    │   │ │
│  │  │  [Вкладка       │  │  REST   │  │  GET/PUT settings        │   │ │
│  │  │  Уведомления]   │  │  JWT    │  │  POST test               │   │ │
│  │  └─────────────────┘  │         │  │  POST send-invite        │   │ │
│  │                       │         │  └──────────┬───────────────┘   │ │
│  │  ┌─────────────────┐  │         │             │                    │ │
│  │  │  EmployeesTab   │◄─┼─────────┼─►  POST     │                    │ │
│  │  │  [Кнопка        │  │         │  /send-invite                   │ │
│  │  │  Пригласить]    │  │         │             │                    │ │
│  │  └─────────────────┘  │         │             ▼                    │ │
│  │                       │         │  ┌──────────────────────────┐   │ │
│  │  ┌─────────────────┐  │         │  │  notification_dispatcher │   │ │
│  │  │  DataAccess     │  │         │  │  [Ядро диспетчера]       │   │ │
│  │  │  misc_mixin     │  │         │  └────┬──────────┬──────────┘   │ │
│  │  └─────────────────┘  │         │       │          │              │ │
│  └───────────────────────┘         │       ▼          ▼              │ │
│                                    │  EmailService  TelegramService  │ │
│  ┌───────────────────────┐         │  [aiosmtplib]  [aiogram]        │ │
│  │  SQLite (offline)     │         │       │          │              │ │
│  │  notifications table  │         │       ▼          ▼              │ │
│  └───────────────────────┘         │  ┌──────────────────────────┐   │ │
│                                    │  │  PostgreSQL               │   │ │
│                                    │  │  - employees              │   │ │
│                                    │  │    + telegram_user_id     │   │ │
│                                    │  │    + telegram_link_token  │   │ │
│                                    │  │  - notification_settings  │   │ │
│                                    │  │  - notifications          │   │ │
│                                    │  └──────────────────────────┘   │ │
│                                    └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

Внешние системы:
  SMTP-сервер (Яндекс / Mail.ru)   ← EmailService
  Telegram Bot API (api.telegram.org) ← TelegramService + aiogram polling
```

### 1.2 Component Diagram — Новые компоненты

```
┌──────────────────────────────────────────────────────────────────────┐
│  FastAPI Server — Компоненты системы уведомлений                     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  notifications_router  (server/routers/notifications_router.py)│  │
│  │                                                              │   │
│  │  GET  /notifications                  ← список уведомлений   │   │
│  │  PUT  /notifications/{id}/read        ← отметить прочитанным │   │
│  │  GET  /notifications/settings/{id}   ← получить настройки   │   │
│  │  PUT  /notifications/settings/{id}   ← обновить настройки   │   │
│  │  POST /notifications/test             ← тестовое уведомление │   │
│  │  POST /employees/{id}/send-invite     ← отправить приглашение│   │
│  └────────────────────┬─────────────────────────────────────────┘   │
│                       │ вызывает                                     │
│                       ▼                                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  notification_dispatcher                                      │   │
│  │  (server/services/notification_dispatcher.py) — НОВЫЙ        │   │
│  │                                                              │   │
│  │  dispatch_notification(db, employee_id, event_type,          │   │
│  │                        title, message, entity_type, entity_id)│  │
│  │                                                              │   │
│  │  1. Создать Notification запись в БД                         │   │
│  │  2. Загрузить NotificationSettings                           │   │
│  │  3. Проверить флаг события                                   │   │
│  │  4. Telegram → TelegramService.send_message()                │   │
│  │  5. Email → EmailService.send_notification()                 │   │
│  └────────────┬──────────────────┬───────────────────────────────┘  │
│               │                  │                                   │
│               ▼                  ▼                                   │
│  ┌────────────────┐  ┌────────────────────────────────────────────┐ │
│  │ TelegramService│  │ EmailService                               │ │
│  │ (уже есть)     │  │ (уже есть + новые методы)                  │ │
│  │                │  │ + send_welcome_email()                     │ │
│  │ send_message() │  │ + send_client_chat_invite()                │ │
│  └────────────────┘  └────────────────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  telegram_bot_handlers  (server/telegram_bot_handlers.py)    │   │
│  │  — НОВЫЙ                                                     │   │
│  │                                                              │   │
│  │  @router.message(CommandStart())                             │   │
│  │  handle_start(message):                                      │   │
│  │    token = args[1] → найти Employee по токену                │   │
│  │    employee.telegram_user_id = message.from_user.id          │   │
│  │    employee.telegram_link_token = None                       │   │
│  │    ответить подтверждением                                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  NotificationSettings  (server/database.py) — НОВАЯ МОДЕЛЬ   │   │
│  │                                                              │   │
│  │  id, employee_id (FK, UNIQUE)                                │   │
│  │  telegram_enabled, email_enabled                             │   │
│  │  notify_crm_stage, notify_assigned, notify_deadline          │   │
│  │  notify_payment, notify_supervision                          │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  PyQt5 Client — Новые компоненты                                     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  AdminDialog → вкладка "Уведомления"                         │   │
│  │  (ui/admin_dialog.py) — ИЗМЕНЕНИЕ                           │   │
│  │                                                              │   │
│  │  - Выпадающий список сотрудников                             │   │
│  │  - Секция Telegram: [✓ включить] + статус подключения        │   │
│  │  - Флажки типов событий                                      │   │
│  │  - Кнопки [Сохранить] [Тест]                                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  EmployeesTab → кнопка "Пригласить"                          │   │
│  │  (ui/employees_tab.py) — ИЗМЕНЕНИЕ                          │   │
│  │                                                              │   │
│  │  - Иконка mail.svg в строке действий                         │   │
│  │  - Зелёная иконка если telegram_user_id заполнен             │   │
│  │  - POST /employees/{id}/send-invite при нажатии              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  DataAccess + misc_mixin — новые методы                      │   │
│  │                                                              │   │
│  │  get_notification_settings(employee_id) → dict               │   │
│  │  update_notification_settings(employee_id, data) → bool      │   │
│  │  send_employee_invite(employee_id) → bool                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. DFD — Потоки данных

### 2.1 Поток "Привязка Telegram"

```
Сотрудник                  CRM (Email)              FastAPI             Telegram Bot
    │                          │                        │                     │
    │  Нажимает кнопку         │                        │                     │
    │  "Пригласить"            │                        │                     │
    │──────────────────────────┼───────────────────────►│                     │
    │                          │  POST /employees/{id}  │                     │
    │                          │  /send-invite          │                     │
    │                          │                        │ Генерирует токен    │
    │                          │                        │ (uuid4, 32 символа) │
    │                          │                        │ Сохраняет в         │
    │                          │                        │ employee:           │
    │                          │                        │ telegram_link_token │
    │                          │                        │ expires = +7 дней   │
    │                          │                        │                     │
    │                          │◄───────────────────────│                     │
    │                          │  send_welcome_email()  │                     │
    │                          │  (HTML письмо с deep   │                     │
    │                          │   link на бота)        │                     │
    │◄─────────────────────────│                        │                     │
    │  Получает письмо         │                        │                     │
    │  Нажимает ссылку:        │                        │                     │
    │  t.me/festival_color_bot │                        │                     │
    │  ?start=TOKEN            │                        │                     │
    │──────────────────────────────────────────────────────────────────────►│
    │                          │                        │  /start TOKEN       │
    │                          │                        │◄────────────────────│
    │                          │                        │ CommandStart handler│
    │                          │                        │ Ищет Employee по    │
    │                          │                        │ telegram_link_token │
    │                          │                        │ Проверяет expires   │
    │                          │                        │                     │
    │                          │                        │ employee.           │
    │                          │                        │ telegram_user_id =  │
    │                          │                        │ message.from_user.id│
    │                          │                        │ token = None        │
    │                          │                        │ expires = None      │
    │                          │                        │ db.commit()         │
    │                          │                        │                     │
    │◄─────────────────────────────────────────────────────────────────────│
    │  "Ваш аккаунт привязан   │                        │  ответ боту         │
    │  к CRM Festival Color"   │                        │                     │
    │                          │                        │                     │

Результат: employee.telegram_user_id сохранён в PostgreSQL
```

### 2.2 Поток "Отправка уведомления"

```
CRM Событие             crm_router.py          notification_dispatcher    Telegram
(смена стадии /              │                          │                     │
 назначение)                 │                          │                     │
    │                        │                          │                     │
    │ PUT /crm-cards/{id}    │                          │                     │
    │ /move или              │                          │                     │
    │ /stage-executor        │                          │                     │
    │───────────────────────►│                          │                     │
    │                        │ await dispatch_          │                     │
    │                        │ notification(            │                     │
    │                        │   db,                    │                     │
    │                        │   employee_id,           │                     │
    │                        │   'crm_stage_change'     │                     │
    │                        │   или 'assigned',        │                     │
    │                        │   title, message         │                     │
    │                        │ )                        │                     │
    │                        │─────────────────────────►│                     │
    │                        │                          │ 1. INSERT INTO      │
    │                        │                          │    notifications    │
    │                        │                          │                     │
    │                        │                          │ 2. SELECT           │
    │                        │                          │    notification_    │
    │                        │                          │    settings         │
    │                        │                          │    WHERE            │
    │                        │                          │    employee_id=...  │
    │                        │                          │                     │
    │                        │                          │ 3. Проверить флаг:  │
    │                        │                          │    notify_crm_stage │
    │                        │                          │    или              │
    │                        │                          │    notify_assigned  │
    │                        │                          │                     │
    │                        │                          │ 4. Если             │
    │                        │                          │    telegram_enabled │
    │                        │                          │    и telegram_      │
    │                        │                          │    user_id не None  │
    │                        │                          │──────────────────►│ │
    │                        │                          │ TelegramService.    │
    │                        │                          │ send_message(       │
    │                        │                          │   telegram_user_id, │
    │                        │                          │   formatted_text    │
    │                        │                          │ )                   │
    │                        │                          │                     │ POST
    │                        │                          │                     │ api.telegram.org
    │                        │                          │                     │ /sendMessage
    │◄───────────────────────│                          │                     │
    │  200 OK (ответ роутера)│                          │                     │

Telegram-уведомление доставляется асинхронно (BackgroundTask или await)
```

### 2.3 Поток "Email приглашение сотруднику"

```
Директор (UI)          EmployeesTab          FastAPI                  SMTP
    │                       │                   │                        │
    │  Нажимает иконку      │                   │                        │
    │  "Пригласить"         │                   │                        │
    │──────────────────────►│                   │                        │
    │                       │ DataAccess.        │                        │
    │                       │ send_employee_     │                        │
    │                       │ invite(id)         │                        │
    │                       │──────────────────►│                        │
    │                       │  POST /api/v1/     │                        │
    │                       │  employees/{id}/   │                        │
    │                       │  send-invite       │                        │
    │                       │                   │ Проверить employee.email│
    │                       │                   │ Если не заполнен →      │
    │                       │                   │ 400 "Email не заполнен" │
    │                       │                   │                        │
    │                       │                   │ Сгенерировать токен     │
    │                       │                   │ Сохранить в employee    │
    │                       │                   │                        │
    │                       │                   │ EmailService.           │
    │                       │                   │ send_welcome_email(     │
    │                       │                   │   to=employee.email,    │
    │                       │                   │   name, login,          │
    │                       │                   │   telegram_token,       │
    │                       │                   │   deep_link             │
    │                       │                   │ )                       │
    │                       │                   │───────────────────────►│
    │                       │                   │  SMTP SEND              │
    │                       │                   │  (HTML письмо)          │
    │                       │                   │◄───────────────────────│
    │                       │◄──────────────────│                        │
    │                       │  {"ok": true,      │                        │
    │◄──────────────────────│   "message":       │                        │
    │  CustomMessageBox:     │   "Приглашение     │                        │
    │  "Приглашение          │    отправлено"}    │                        │
    │   отправлено"          │                   │                        │
```

### 2.4 Поток "Email приглашение клиенту"

```
Менеджер (UI)     CrmCardEditDialog       FastAPI               SMTP
    │                     │                  │                     │
    │  Нажимает кнопку    │                  │                     │
    │  "Пригласить        │                  │                     │
    │   клиента"          │                  │                     │
    │────────────────────►│                  │                     │
    │                     │ POST /api/v1/     │                     │
    │                     │ messenger/chats/  │                     │
    │                     │ {chat_id}/        │                     │
    │                     │ invite-client     │                     │
    │                     │─────────────────►│                     │
    │                     │                  │ Найти чат → контракт│
    │                     │                  │ → клиент            │
    │                     │                  │ client.email        │
    │                     │                  │ Если нет email →    │
    │                     │                  │ 400 "Email клиента  │
    │                     │                  │  не заполнен"       │
    │                     │                  │                     │
    │                     │                  │ EmailService.       │
    │                     │                  │ send_client_chat_   │
    │                     │                  │ invite(             │
    │                     │                  │   to=client.email,  │
    │                     │                  │   client_name,      │
    │                     │                  │   project_address,  │
    │                     │                  │   project_type,     │
    │                     │                  │   manager_name,     │
    │                     │                  │   invite_link       │
    │                     │                  │ )                   │
    │                     │                  │────────────────────►│
    │                     │                  │  SMTP SEND          │
    │                     │                  │◄────────────────────│
    │                     │◄─────────────────│                     │
    │◄────────────────────│  {"ok": true}    │                     │
    │  "Клиент приглашён" │                  │                     │
```

---

## 3. API Контракты

### GET /api/v1/notifications/settings/{employee_id}

**Требования:** JWT-токен, авторизован как Директор или как сам сотрудник с данным ID.

**Response 200:**
```json
{
  "employee_id": 1,
  "telegram_enabled": true,
  "email_enabled": false,
  "notify_crm_stage": true,
  "notify_assigned": true,
  "notify_deadline": true,
  "notify_payment": false,
  "notify_supervision": false,
  "telegram_connected": true
}
```

Поле `telegram_connected` — вычисляемое: `employee.telegram_user_id is not None`.
Если запись `notification_settings` для сотрудника ещё не создана → возвращать дефолтные значения (не 404).

**Response 403:** если запрашивает не Директор и не сам сотрудник.

---

### PUT /api/v1/notifications/settings/{employee_id}

**Request Body** (без поля `telegram_connected` — оно вычисляемое):
```json
{
  "telegram_enabled": true,
  "email_enabled": false,
  "notify_crm_stage": true,
  "notify_assigned": true,
  "notify_deadline": true,
  "notify_payment": false,
  "notify_supervision": false
}
```

**Response 200:**
```json
{
  "employee_id": 1,
  "telegram_enabled": true,
  "email_enabled": false,
  "notify_crm_stage": true,
  "notify_assigned": true,
  "notify_deadline": true,
  "notify_payment": false,
  "notify_supervision": false,
  "telegram_connected": true
}
```

Семантика: upsert (INSERT ... ON CONFLICT DO UPDATE). Запись создаётся автоматически при первом PUT.

---

### POST /api/v1/employees/{employee_id}/send-invite

**Требования:** JWT-токен, роль Директор.

**Request Body:** пустой (все данные берутся из employee в БД).

**Response 200:**
```json
{
  "ok": true,
  "message": "Приглашение отправлено на email@example.com"
}
```

**Response 400:**
```json
{
  "detail": "Email сотрудника не заполнен"
}
```

**Response 409** (если telegram уже подключён):
```json
{
  "detail": "Telegram уже подключён к этому аккаунту"
}
```

Действия сервера:
1. Загрузить `Employee` по ID.
2. Проверить наличие email.
3. Сгенерировать `telegram_link_token = uuid4().hex[:32]`.
4. Установить `telegram_link_token_expires = datetime.utcnow() + timedelta(days=7)`.
5. Сохранить в БД.
6. Вызвать `EmailService.send_welcome_email(...)`.

---

### POST /api/v1/notifications/test

**Требования:** JWT-токен, роль Директор.

**Request Body:**
```json
{
  "employee_id": 1,
  "message": "Тест уведомления"
}
```

**Response 200:**
```json
{
  "ok": true
}
```

**Response 400** (нет настроек или Telegram не подключён):
```json
{
  "detail": "Telegram не подключён для этого сотрудника"
}
```

Действие сервера: вызвать `dispatch_notification(...)` с `event_type='test'` — отправить Telegram без проверки флагов событий.

---

### POST /api/v1/messenger/chats/{chat_id}/invite-client

**Требования:** JWT-токен, роль Директор или Менеджер.

**Request Body:** пустой.

**Response 200:**
```json
{
  "ok": true,
  "message": "Клиент приглашён"
}
```

**Response 400:**
```json
{
  "detail": "Email клиента не заполнен"
}
```

---

## 4. Стратегия тестирования

### 4.1 Unit-тесты (CI, без сервера)

**Файл:** `tests/client/test_notifications_unit.py`

```python
# Тест 1: dispatch_notification вызывает TelegramService при telegram_enabled=True
# Мокировать: db.query, TelegramService.send_message
# Проверить: send_message вызван с правильным chat_id и текстом

# Тест 2: dispatch_notification НЕ вызывает TelegramService если флаг события False
# notify_crm_stage=False → event_type='crm_stage_change' → send_message НЕ вызван

# Тест 3: dispatch_notification НЕ вызывает TelegramService если telegram_user_id=None
# (Telegram не привязан) → send_message НЕ вызван

# Тест 4: handle_start с валидным токеном → employee.telegram_user_id сохранён
# handle_start с истёкшим токеном → ответ "ссылка недействительна"
# handle_start с несуществующим токеном → ответ "ссылка недействительна"
```

Мок-классы:
```python
class MockTelegramService:
    async def send_message(self, chat_id, text): return True

class MockEmailService:
    async def send_welcome_email(self, *args, **kwargs): return True
    async def send_client_chat_invite(self, *args, **kwargs): return True
```

### 4.2 Contract-тесты

**Файл:** `tests/contract/conftest.py` — добавить:

```python
NOTIFICATION_SETTINGS_KEYS = {
    "employee_id", "telegram_enabled", "email_enabled",
    "notify_crm_stage", "notify_assigned", "notify_deadline",
    "notify_payment", "notify_supervision", "telegram_connected"
}

SEND_INVITE_RESPONSE_KEYS = {"ok", "message"}

TEST_NOTIFICATION_RESPONSE_KEYS = {"ok"}
```

**Файл:** `tests/contract/test_notifications_contracts.py`

```python
def test_notification_settings_get_keys(api_client, employee_id):
    resp = api_client.get(f"/api/v1/notifications/settings/{employee_id}")
    assert resp.status_code == 200
    assert NOTIFICATION_SETTINGS_KEYS == set(resp.json().keys())

def test_notification_settings_put_returns_same_keys(api_client, employee_id):
    body = {"telegram_enabled": True, "email_enabled": False,
            "notify_crm_stage": True, "notify_assigned": True,
            "notify_deadline": True, "notify_payment": False,
            "notify_supervision": False}
    resp = api_client.put(f"/api/v1/notifications/settings/{employee_id}", json=body)
    assert resp.status_code == 200
    assert NOTIFICATION_SETTINGS_KEYS == set(resp.json().keys())
```

### 4.3 Smoke-тесты (реальный сервер)

**Файл:** `tests/smoke/test_notifications.py` (уже существует — расширить)

```python
# test_get_notification_settings — GET settings возвращает все ключи
# test_put_notification_settings — PUT settings сохраняет значения
# test_send_invite_no_email — 400 если email пустой
# test_test_notification_no_telegram — 400 если Telegram не привязан
# test_full_telegram_link_flow — (интеграционный, требует бота)
```

### 4.4 Acceptance Criteria

| Критерий | Как проверять |
|----------|--------------|
| `/start TOKEN` → `telegram_user_id` сохранён | Smoke-тест: POST `/start` боту через Telegram API, затем GET employee проверить `telegram_connected: true` |
| Смена стадии CRM → Telegram-сообщение доставлено | Интеграционный тест: PUT `/crm-cards/{id}/move`, затем проверить `getUpdates` тестового бота |
| POST `send-invite` → email отправлен | Smoke-тест: POST → 200 OK + проверить SMTP-лог или тестовый ящик |
| `PUT settings` → значения сохранены | Contract-тест: PUT → GET → сравнить значения |
| `telegram_connected: false` если токен не привязан | Contract-тест: новый сотрудник → GET settings → `telegram_connected: false` |

---

## 5. Схема БД (Alembic-миграция)

### 5.1 Изменения в таблице `employees`

```sql
ALTER TABLE employees
    ADD COLUMN telegram_user_id BIGINT NULL,
    ADD COLUMN telegram_link_token VARCHAR(32) NULL,
    ADD COLUMN telegram_link_token_expires TIMESTAMP WITHOUT TIME ZONE NULL;

CREATE INDEX ix_employees_telegram_link_token
    ON employees (telegram_link_token)
    WHERE telegram_link_token IS NOT NULL;
```

Индекс по `telegram_link_token` — для быстрого поиска при `/start TOKEN` без full-scan.

### 5.2 Новая таблица `notification_settings`

```sql
CREATE TABLE notification_settings (
    id                  SERIAL PRIMARY KEY,
    employee_id         INTEGER NOT NULL UNIQUE
                        REFERENCES employees(id) ON DELETE CASCADE,

    -- каналы доставки
    telegram_enabled    BOOLEAN NOT NULL DEFAULT TRUE,
    email_enabled       BOOLEAN NOT NULL DEFAULT FALSE,

    -- типы событий
    notify_crm_stage    BOOLEAN NOT NULL DEFAULT TRUE,
    notify_assigned     BOOLEAN NOT NULL DEFAULT TRUE,
    notify_deadline     BOOLEAN NOT NULL DEFAULT TRUE,
    notify_payment      BOOLEAN NOT NULL DEFAULT FALSE,
    notify_supervision  BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX ix_notification_settings_employee_id
    ON notification_settings (employee_id);
```

### 5.3 Alembic-миграция

**Файл:** `server/alembic/versions/e5f6g7h8i9j0_add_notifications_system.py`

```python
"""add notifications system

Revision ID: e5f6g7h8i9j0
Revises: <предыдущий revision>
Create Date: 2026-03-06

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Добавить поля в employees
    op.add_column('employees', sa.Column('telegram_user_id',
        sa.BigInteger(), nullable=True))
    op.add_column('employees', sa.Column('telegram_link_token',
        sa.String(32), nullable=True))
    op.add_column('employees', sa.Column('telegram_link_token_expires',
        sa.DateTime(), nullable=True))

    op.create_index('ix_employees_telegram_link_token', 'employees',
        ['telegram_link_token'], unique=False,
        postgresql_where=sa.text('telegram_link_token IS NOT NULL'))

    # Создать таблицу notification_settings
    op.create_table('notification_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('employee_id', sa.Integer(),
            sa.ForeignKey('employees.id', ondelete='CASCADE'),
            nullable=False, unique=True),
        sa.Column('telegram_enabled', sa.Boolean(),
            nullable=False, server_default='true'),
        sa.Column('email_enabled', sa.Boolean(),
            nullable=False, server_default='false'),
        sa.Column('notify_crm_stage', sa.Boolean(),
            nullable=False, server_default='true'),
        sa.Column('notify_assigned', sa.Boolean(),
            nullable=False, server_default='true'),
        sa.Column('notify_deadline', sa.Boolean(),
            nullable=False, server_default='true'),
        sa.Column('notify_payment', sa.Boolean(),
            nullable=False, server_default='false'),
        sa.Column('notify_supervision', sa.Boolean(),
            nullable=False, server_default='false'),
    )

    op.create_index('ix_notification_settings_employee_id',
        'notification_settings', ['employee_id'])


def downgrade():
    op.drop_table('notification_settings')
    op.drop_index('ix_employees_telegram_link_token', 'employees')
    op.drop_column('employees', 'telegram_link_token_expires')
    op.drop_column('employees', 'telegram_link_token')
    op.drop_column('employees', 'telegram_user_id')
```

---

## 6. ADR (Architecture Decision Records)

### ADR-001: Привязка Telegram через одноразовый токен (не username / ручной ввод chat_id)

**Статус:** Принято

**Контекст:**
Для отправки личных Telegram-уведомлений сотруднику сервер должен знать его `chat_id` (числовой идентификатор). Существуют три подхода:
1. Ручной ввод `chat_id` пользователем в форме CRM.
2. Привязка через Telegram username (`@username` → Bot API getChat).
3. Привязка через одноразовый deep-link токен (`t.me/bot?start=TOKEN`).

**Решение:** Подход 3 — одноразовый токен.

Механизм:
- Сервер генерирует `uuid4().hex[:32]`, сохраняет в `employee.telegram_link_token` со сроком жизни 7 дней.
- Токен включается в welcome email как deep-link: `t.me/festival_color_crm_bot?start=TOKEN`.
- Сотрудник нажимает ссылку → Telegram открывает бота → бот получает `/start TOKEN`.
- Обработчик `/start` находит сотрудника по токену, сохраняет `telegram_user_id`, очищает токен.

**Обоснование принятия:**
- Безопасность: токен одноразовый, имеет TTL, не требует знания внутренних ID.
- UX: пользователь не должен ничего копировать вручную — просто нажимает ссылку.
- Не требует верификации Telegram-аккаунта через стороннее API (getChat требует публичный username).

**Отклонённые альтернативы:**
- Ручной ввод `chat_id`: неудобно, пользователь должен найти chat_id самостоятельно (через @userinfobot или `/start` у другого бота). Высокий процент ошибок.
- Привязка через username: Telegram Bot API `getChat(@username)` работает только для публичных каналов/групп, а не для личных чатов пользователей.

**Последствия:**
- Если welcome email не дошёл или ссылка устарела — Директор повторно нажимает "Пригласить" → генерируется новый токен.
- Endpoint `POST /employees/{id}/send-invite` отвечает 409 если `telegram_user_id` уже заполнен (защита от случайного повторного вызова).

---

### ADR-002: aiogram polling в `asyncio.create_task` (не webhook)

**Статус:** Принято

**Контекст:**
Для обработки входящих сообщений Telegram-бота (команда `/start TOKEN`) требуется выбор между двумя моделями получения сообщений:
1. **Webhook:** Telegram отправляет POST-запросы на публичный HTTPS URL сервера.
2. **Long polling:** Сервер периодически запрашивает новые сообщения через `getUpdates`.

**Решение:** Long polling через `asyncio.create_task(dp.start_polling(bot, handle_signals=False))` в `lifespan` FastAPI.

Запуск в `server/main.py`:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... инициализация сервисов ...
    bot = get_telegram_service()._bot
    if bot:
        dp = BotDispatcher()
        dp.include_router(bot_router)
        asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    yield
    # ... shutdown ...
```

**Обоснование принятия:**
- Production-сервер на Timeweb работает за nginx с HTTPS, но настройка webhook требует дополнительной конфигурации nginx (отдельный location для webhook URL) и публичного endpoint-а.
- Polling не требует публичного URL — подходит для любой конфигурации, включая development и staging окружения.
- Простота maintenance: нет необходимости регистрировать/обновлять webhook при смене IP или домена.
- Объём входящих сообщений минимален (команда `/start` — только при первичной настройке сотрудника), поэтому задержка polling (до 1 секунды) несущественна.

**Отклонённые альтернативы:**
- Webhook: требует настройки nginx location, SSL-сертификата на конкретном endpoint-е, регистрации через `setWebhook`. При смене конфигурации сервера — ручное обновление.
- Отдельный процесс для бота: усложняет Docker-конфигурацию (отдельный контейнер/сервис), требует shared-доступа к БД.

**Ограничения:**
- Одно Telegram-соединение на экземпляр сервера — не масштабируется горизонтально. При развёртывании нескольких инстансов FastAPI только один будет получать сообщения (гонка за `getUpdates`). Для текущего single-instance deployment на Timeweb это некритично.
- При падении FastAPI процесса бот останавливается вместе с ним — но сервис и так падает, оба восстанавливаются при перезапуске контейнера.

---

## 7. Сводная таблица файлов изменений

| Файл | Тип | Описание изменений |
|------|-----|--------------------|
| `server/database.py` | Изменение | +3 поля в Employee, +класс NotificationSettings, связь |
| `server/schemas.py` | Изменение | +NotificationSettingsResponse, +NotificationSettingsUpdate |
| `server/alembic/versions/e5f6g7h8i9j0_...py` | Новый | Миграция: employees + notification_settings |
| `server/email_service.py` | Изменение | +send_welcome_email(), +send_client_chat_invite() |
| `server/telegram_bot_handlers.py` | Новый | Обработчик /start TOKEN |
| `server/services/notification_dispatcher.py` | Новый | Центральный диспетчер уведомлений |
| `server/routers/notifications_router.py` | Новый | CRUD settings + send-invite + test |
| `server/routers/crm_router.py` | Изменение | Триггеры dispatch_notification |
| `server/main.py` | Изменение | Подключить роутер + aiogram polling в lifespan |
| `utils/api_client/misc_mixin.py` | Изменение | +get/update_notification_settings, +send_employee_invite |
| `utils/data_access.py` | Изменение | +get/update_notification_settings, +send_employee_invite |
| `ui/employees_tab.py` | Изменение | Кнопка "Пригласить" в строке действий |
| `ui/admin_dialog.py` | Изменение | Вкладка "Уведомления" |
| `tests/contract/conftest.py` | Изменение | +NOTIFICATION_SETTINGS_KEYS и связанные |
| `tests/contract/test_notifications_contracts.py` | Новый | Contract-тесты новых endpoints |
| `tests/smoke/test_notifications.py` | Изменение | +новые smoke-тесты |
