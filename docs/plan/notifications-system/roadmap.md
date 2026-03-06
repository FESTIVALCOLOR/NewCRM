# Roadmap: Система уведомлений
Дата: 2026-03-06 | Ветка: feat/notifications-system

---

## Оглавление

```
⬜ Этап 1: Серверная инфраструктура
  ⬜ 1.1 database.py — 3 поля в Employee + NotificationSettings
  ⬜ 1.2 Alembic миграция
  ⬜ 1.3 schemas.py — Pydantic схемы
  ⬜ 1.4 email_service.py — send_welcome_email, send_client_chat_invite
  ⬜ 1.5 telegram_bot_handlers.py — /start handler
  ⬜ 1.6 services/notification_dispatcher.py — dispatch_notification
  ⬜ 1.7 routers/notifications_router.py — 6 endpoints
  ⬜ 1.8 main.py — подключить роутер + aiogram polling
  ⬜ 1.9 Триггеры в crm_router.py

⬜ Этап 2: Клиентская сторона
  ⬜ 2.1 utils/api_client/misc_mixin.py — 3 новых метода
  ⬜ 2.2 utils/data_access.py — методы настроек

⬜ Этап 3: UI
  ⬜ 3.1 ui/employees_tab.py — кнопка "Пригласить"
  ⬜ 3.2 ui/admin_dialog.py — вкладка "Уведомления"

⬜ Этап 4: Тесты
  ⬜ 4.1 tests/contract/ — contract-тесты новых endpoints
  ⬜ 4.2 tests/smoke/test_notifications.py — smoke-тесты
  ⬜ 4.3 tests/ui/ — UI тесты кнопки Пригласить

⬜ Этап 5: PR & Docker
  ⬜ 5.1 git commit + PR
  ⬜ 5.2 Docker rebuild на production
```

---

## Детальное описание этапов

---

### Этап 1: Серверная инфраструктура

#### 1.1 database.py — 3 поля в Employee + NotificationSettings

**Файл:** `server/database.py` (изменение)

**Что делать:**
- Добавить в модель `Employee` три новых поля:
  - `telegram_user_id = Column(BigInteger, nullable=True)` — числовой Telegram chat_id сотрудника
  - `telegram_link_token = Column(String(32), nullable=True)` — одноразовый токен для привязки
  - `telegram_link_token_expires = Column(DateTime, nullable=True)` — TTL токена (7 дней)
- Добавить в `Employee` relationship: `notification_settings = relationship("NotificationSettings", back_populates="employee", uselist=False, cascade="all, delete-orphan")`
- Создать новую модель `NotificationSettings` с полями: `id`, `employee_id` (FK unique), `telegram_enabled` (default=True), `email_enabled` (default=False), `notify_crm_stage` (default=True), `notify_assigned` (default=True), `notify_deadline` (default=True), `notify_payment` (default=False), `notify_supervision` (default=False)

**Агент:** Backend Agent

**Зависимости:** нет (первый шаг)

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 1.2 и 1.3

---

#### 1.2 Alembic миграция

**Файл:** `server/alembic/versions/e5f6g7h8i9j0_add_notifications_system.py` (новый)

**Что делать:**
- Создать файл миграции с `revision = "e5f6g7h8i9j0"`
- В `upgrade()`:
  - `op.add_column('employees', ...)` для трёх новых полей (`telegram_user_id`, `telegram_link_token`, `telegram_link_token_expires`)
  - Создать частичный индекс `ix_employees_telegram_link_token` на `telegram_link_token WHERE NOT NULL` — для быстрого поиска при `/start TOKEN`
  - `op.create_table('notification_settings', ...)` со всеми полями и `REFERENCES employees(id) ON DELETE CASCADE`
  - Создать индекс `ix_notification_settings_employee_id`
- В `downgrade()`: обратные операции в правильном порядке (сначала drop_table, потом drop_column)

**Агент:** Backend Agent

**Зависимости:** нет (миграция пишется параллельно с моделями)

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 1.1 и 1.3

**Примечание:** перед применением уточнить `Revises:` — предыдущий revision из `server/alembic/versions/`

---

#### 1.3 schemas.py — Pydantic схемы

**Файл:** `server/schemas.py` (изменение)

**Что делать:**
- Добавить класс `NotificationSettingsResponse(BaseModel)` с полями: `employee_id`, `telegram_enabled`, `email_enabled`, `notify_crm_stage`, `notify_assigned`, `notify_deadline`, `notify_payment`, `notify_supervision`, `telegram_connected` (вычисляемое bool). `Config: from_attributes = True`
- Добавить класс `NotificationSettingsUpdate(BaseModel)` с теми же полями кроме `telegram_connected` (оно вычисляемое, не принимается от клиента). Все поля с дефолтными значениями
- Добавить вспомогательную схему `SendInviteResponse(BaseModel)` с полями `ok: bool`, `message: str`
- Добавить `TestNotificationRequest(BaseModel)` с полями `employee_id: int`, `message: str`

**Агент:** Backend Agent

**Зависимости:** нет

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 1.1 и 1.2

---

#### 1.4 email_service.py — send_welcome_email, send_client_chat_invite

**Файл:** `server/email_service.py` (изменение)

**Что делать:**
- Добавить метод `async def send_welcome_email(self, to_email, employee_name, login, password, download_link, telegram_token, bot_username="festival_color_crm_bot") -> bool`
  - HTML-шаблон из `docs/plan/notifications-system/welcome_email_preview.html` — встроить как строку
  - Логотип и footer.jpg — кодировать в base64 и вшивать в письмо как inline attachments
  - Deep-link формат: `https://t.me/{bot_username}?start={telegram_token}`
- Добавить метод `async def send_client_chat_invite(self, to_email, client_name, project_address, project_type, manager_name, invite_link) -> bool`
  - HTML-шаблон из `docs/plan/notifications-system/client_invite_email_preview.html`

**Агент:** Backend Agent

**Зависимости:** 1.1, 1.2, 1.3 должны быть готовы

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 1.5 и 1.6

---

#### 1.5 telegram_bot_handlers.py — /start handler

**Файл:** `server/telegram_bot_handlers.py` (новый)

**Что делать:**
- Создать `router = Router()` из aiogram
- Реализовать `@router.message(CommandStart()) async def handle_start(message: Message)`
  - Извлечь токен из `message.text.split(maxsplit=1)[1]` если есть
  - Открыть сессию БД через `SessionLocal()`
  - Найти `Employee` по `telegram_link_token == token AND telegram_link_token_expires > datetime.utcnow()`
  - Если не найден — ответить "Ссылка недействительна или устарела"
  - Если найден: `employee.telegram_user_id = message.from_user.id`, `telegram_link_token = None`, `telegram_link_token_expires = None`, `db.commit()`
  - Ответить приветственным сообщением с именем сотрудника и перечислением типов уведомлений
  - Обработать случай без токена (просто `/start`) — инструкция как получить ссылку

**Агент:** Backend Agent

**Зависимости:** 1.1, 1.2, 1.3 должны быть готовы

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 1.4 и 1.6

---

#### 1.6 services/notification_dispatcher.py — dispatch_notification

**Файл:** `server/services/notification_dispatcher.py` (новый)

**Что делать:**
- Создать директорию `server/services/` если не существует, добавить `__init__.py`
- Реализовать `async def dispatch_notification(db, employee_id, event_type, title, message, related_entity_type=None, related_entity_id=None)`
  - Шаг 1: создать запись `Notification` в БД (INSERT)
  - Шаг 2: загрузить `NotificationSettings` для сотрудника. Если нет записи — вернуть (не отправлять)
  - Шаг 3: проверить флаг типа события через маппинг `{'assigned': settings.notify_assigned, 'crm_stage_change': settings.notify_crm_stage, 'deadline': settings.notify_deadline, 'payment': settings.notify_payment, 'supervision': settings.notify_supervision}`. Если False — вернуть
  - Шаг 4: если `settings.telegram_enabled` и `employee.telegram_user_id` не None — вызвать `TelegramService.send_message(telegram_user_id, f"<b>{title}</b>\n{message}")`
  - Для `event_type='test'` — пропустить проверку флага события, всегда отправить

**Агент:** Backend Agent

**Зависимости:** 1.1, 1.2, 1.3 должны быть готовы

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 1.4 и 1.5

---

#### 1.7 routers/notifications_router.py — 6 endpoints

**Файл:** `server/routers/notifications_router.py` (новый)

**Что делать:**
- Перенести из `server/main.py` существующие endpoints:
  - `GET /api/v1/notifications` — список уведомлений текущего пользователя
  - `PUT /api/v1/notifications/{id}/read` — отметить прочитанным
- Добавить новые endpoints:
  - `GET /api/v1/notifications/settings/{employee_id}` — получить настройки. Если запись не существует — вернуть дефолтные значения (не 404). Проверить права: Директор или сам сотрудник, иначе 403
  - `PUT /api/v1/notifications/settings/{employee_id}` — upsert настроек. `INSERT ... ON CONFLICT DO UPDATE`
  - `POST /api/v1/employees/{employee_id}/send-invite` — только Директор. Генерировать токен, сохранять, вызывать `send_welcome_email()`. 400 если email пустой, 409 если Telegram уже подключён
  - `POST /api/v1/notifications/test` — только Директор. Вызвать `dispatch_notification` с `event_type='test'`. 400 если Telegram не подключён

**ВАЖНО:** статические пути (`/settings/{id}`, `/test`) объявлять ПЕРЕД динамическими (`/{id}/read`) во избежание конфликтов маршрутизации FastAPI.

**Агент:** Backend Agent

**Зависимости:** 1.4, 1.5, 1.6 должны быть готовы

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 1.8 и 1.9 только если 1.4-1.6 завершены

---

#### 1.8 main.py — подключить роутер + aiogram polling

**Файл:** `server/main.py` (изменение)

**Что делать:**
- Подключить `notifications_router` через `app.include_router(notifications_router, prefix="/api/v1")`
- Удалить из `main.py` старые inline-handlers для `/notifications` и `/notifications/{id}/read` (они перенесены в роутер)
- В функции `lifespan` добавить запуск aiogram polling:
  ```python
  from telegram_bot_handlers import router as bot_router
  from aiogram import Dispatcher as BotDispatcher
  bot = get_telegram_service()._bot
  if bot:
      dp = BotDispatcher()
      dp.include_router(bot_router)
      asyncio.create_task(dp.start_polling(bot, handle_signals=False))
  ```
- Polling запускается как фоновая задача asyncio, не блокирует FastAPI

**Агент:** Backend Agent

**Зависимости:** 1.7 должен быть готов (роутер создан), 1.5 (bot_handlers созданы)

**Параллелизм:** выполнять ПОСЛЕ 1.7

---

#### 1.9 Триггеры в crm_router.py (и employees_router.py)

**Файлы:**
- `server/routers/crm_router.py` (изменение)
- `server/routers/employees_router.py` (изменение)

**Что делать в crm_router.py:**
- При смене стадии CRM карточки (endpoint `PUT /crm-cards/{id}/move` или аналогичный) — добавить вызов:
  `await dispatch_notification(db, manager_id, 'crm_stage_change', title="Стадия изменена", message=f"Проект {address}: стадия изменена на {new_stage}")`
- При назначении исполнителя на стадию — добавить вызов:
  `await dispatch_notification(db, executor_id, 'assigned', title="Назначение", message=f"Вы назначены на стадию {stage_name} проекта {address}")`

**Что делать в employees_router.py:**
- При добавлении сотрудника в мессенджер-чат — auto-populate `MessengerChatMember.telegram_user_id` из `Employee.telegram_user_id` (если заполнен)

**Агент:** Backend Agent

**Зависимости:** 1.6 (dispatcher), 1.7 (роутер настроек) должны быть готовы

**Параллелизм:** выполнять ПОСЛЕ 1.6, можно ОДНОВРЕМЕННО с 1.8

---

### Этап 2: Клиентская сторона

#### 2.1 utils/api_client/misc_mixin.py — 3 новых метода

**Файл:** `utils/api_client/misc_mixin.py` (изменение)

**Что делать:**
- Добавить метод `get_notification_settings(self, employee_id: int) -> dict | None`
  - `GET /api/v1/notifications/settings/{employee_id}`
  - Возвращать dict с ключами из `NOTIFICATION_SETTINGS_KEYS` или None при ошибке
- Добавить метод `update_notification_settings(self, employee_id: int, data: dict) -> dict | None`
  - `PUT /api/v1/notifications/settings/{employee_id}`
  - Возвращать обновлённые настройки или None
- Добавить метод `send_employee_invite(self, employee_id: int) -> dict | None`
  - `POST /api/v1/employees/{employee_id}/send-invite`
  - Возвращать `{"ok": True, "message": "..."}` или None

**Агент:** API Client Agent

**Зависимости:** 1.7 (endpoints на сервере готовы)

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 2.2

---

#### 2.2 utils/data_access.py — методы настроек

**Файл:** `utils/data_access.py` (изменение)

**Что делать:**
- Добавить метод `get_notification_settings(self, employee_id: int) -> dict | None`
  - Делегировать в `self.api.get_notification_settings(employee_id)`
  - Нет offline-fallback (настройки уведомлений не кешируются локально)
- Добавить метод `update_notification_settings(self, employee_id: int, data: dict) -> dict | None`
  - Делегировать в `self.api.update_notification_settings(employee_id, data)`
- Добавить метод `send_employee_invite(self, employee_id: int) -> dict | None`
  - Делегировать в `self.api.send_employee_invite(employee_id)`
  - Не добавлять в offline-очередь (приглашение — живая операция)

**Агент:** API Client Agent

**Зависимости:** 2.1 (misc_mixin методы готовы)

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 2.1 (2.2 зависит от 2.1 только логически, код можно писать параллельно)

---

### Этап 3: UI

#### 3.1 ui/employees_tab.py — кнопка "Пригласить"

**Файл:** `ui/employees_tab.py` (изменение)

**Что делать:**
- В строку действий сотрудника (где кнопки редактировать/удалить) добавить кнопку-иконку без текста
- SVG иконка: `mail.svg` из `resources/icons/` — загружать через `IconLoader`
- Если `employee.telegram_user_id` заполнен → отображать зелёную иконку `check.svg` (или аналог), кнопка неактивна (disabled), tooltip "Telegram подключён"
- Если `telegram_user_id` не заполнен → кнопка активна, tooltip "Отправить приглашение"
- При нажатии:
  - Вызвать `self.data.send_employee_invite(employee_id)` через `QTimer.singleShot(0, ...)` если вызов из потока
  - Если email не заполнен (сервер вернул 400) — показать `CustomMessageBox` "Email сотрудника не заполнен"
  - Если успех — показать `CustomMessageBox` "Приглашение отправлено на {email}"
  - Если ошибка (None) — показать `CustomMessageBox` "Ошибка отправки приглашения"

**Агент:** Frontend Agent

**Зависимости:** 2.1, 2.2 должны быть готовы

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 3.2

---

#### 3.2 ui/admin_dialog.py — вкладка "Уведомления"

**Файл:** `ui/admin_dialog.py` (изменение)

**Что делать:**
- Добавить новую вкладку "Уведомления" в существующий `QTabWidget` рядом с "Мессенджером"
- Содержимое вкладки:
  - Выпадающий список `QComboBox` для выбора сотрудника. Директор видит всех сотрудников, остальные — только себя (определять по текущей роли)
  - Секция "Telegram": `QCheckBox` "Включить Telegram-уведомления" + `QLabel` статус "Подключён" (зелёный) / "Не подключён" (серый)
  - Секция "Типы событий": `QCheckBox` для каждого из 5 флагов: "Смена стадии CRM", "Назначение исполнителем", "Приближение дедлайна", "Обновление оплаты", "События надзора"
  - Кнопка `QPushButton("Сохранить")` → `PUT /api/v1/notifications/settings/{id}` через `self.data.update_notification_settings()`
  - Кнопка `QPushButton("Тест")` → `POST /api/v1/notifications/test` через API
- При смене сотрудника в ComboBox — загружать его настройки через `self.data.get_notification_settings(id)` и обновлять состояние чекбоксов
- Все вызовы DataAccess оборачивать в try/except с показом `CustomMessageBox` при ошибке

**Агент:** Frontend Agent

**Зависимости:** 2.1, 2.2 должны быть готовы

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 3.1

---

### Этап 4: Тесты

#### 4.1 tests/contract/ — contract-тесты новых endpoints

**Файлы:**
- `tests/contract/conftest.py` (изменение) — добавить наборы ключей
- `tests/contract/test_notifications_contracts.py` (новый) — тесты

**Что делать в conftest.py:**
```python
NOTIFICATION_SETTINGS_KEYS = {
    "employee_id", "telegram_enabled", "email_enabled",
    "notify_crm_stage", "notify_assigned", "notify_deadline",
    "notify_payment", "notify_supervision", "telegram_connected"
}
SEND_INVITE_RESPONSE_KEYS = {"ok", "message"}
TEST_NOTIFICATION_RESPONSE_KEYS = {"ok"}
```

**Что делать в test_notifications_contracts.py:**
- `test_notification_settings_get_keys` — GET settings → 200, проверить все 9 ключей
- `test_notification_settings_put_returns_same_keys` — PUT settings → 200, те же 9 ключей
- `test_send_invite_missing_email_returns_400` — POST send-invite для сотрудника без email → 400
- `test_test_notification_no_telegram_returns_400` — POST /test для сотрудника без telegram_user_id → 400

**Агент:** Backend Agent (contract-тесты касаются API-контракта)

**Зависимости:** 3.1, 3.2 должны быть готовы (весь стек задеплоен)

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 4.2 и 4.3

---

#### 4.2 tests/smoke/test_notifications.py — smoke-тесты

**Файл:** `tests/smoke/test_notifications.py` (изменение — расширить существующий)

**Что делать:**
- Добавить тесты (с `@pytest.mark.skipif` при недоступности сервера):
  - `test_get_notification_settings_default` — GET для нового сотрудника → дефолтные значения (не 404)
  - `test_put_notification_settings_persists` — PUT → GET → значения совпадают
  - `test_send_invite_no_email_returns_400` — сотрудник без email → 400 с правильным detail
  - `test_test_notification_no_telegram_returns_400` — сотрудник без привязки → 400
  - `test_telegram_connected_false_for_new_employee` — `telegram_connected: false` для нового сотрудника

**Агент:** Backend Agent

**Зависимости:** 3.1, 3.2 готовы (сервер задеплоен с новыми endpoints)

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 4.1 и 4.3

---

#### 4.3 tests/ui/ — UI тесты кнопки Пригласить

**Файл:** `tests/ui/test_employees_deep.py` (изменение) или новый `tests/ui/test_notifications_ui.py`

**Что делать:**
- `test_invite_button_shows_for_employee_without_telegram` — кнопка активна если `telegram_user_id` не заполнен
- `test_invite_button_disabled_for_employee_with_telegram` — кнопка disabled/зелёная если Telegram подключён
- `test_invite_button_shows_error_if_data_returns_none` — DataAccess возвращает None → `CustomMessageBox` показана
- `test_notification_settings_tab_exists_in_admin_dialog` — вкладка "Уведомления" есть в AdminDialog
- `test_notification_settings_save_calls_data_access` — нажатие "Сохранить" вызывает `update_notification_settings`

Все тесты мокируют DataAccess через `patch`.

**Агент:** Frontend Agent

**Зависимости:** 3.1, 3.2 готовы

**Параллелизм:** выполнять ОДНОВРЕМЕННО с 4.1 и 4.2

---

### Этап 5: PR & Docker

#### 5.1 git commit + PR

**Действия:**
- Закоммитить все изменения в ветку `feat/notifications-system`
- Открыть PR в `main` с описанием изменений
- Убедиться что CI green (все 5 jobs)

**Зависимости:** 4.1, 4.2, 4.3 готовы

---

#### 5.2 Docker rebuild на production

**Действия:**
```bash
ssh timeweb "cd /opt/interior_studio && git pull origin feat/notifications-system && docker-compose down && docker-compose build --no-cache api && docker-compose up -d"
```
После rebuild проверить health:
```bash
ssh timeweb 'curl -s http://localhost:8000/health'
```
Применить Alembic-миграцию:
```bash
ssh timeweb 'docker-compose exec api alembic upgrade head'
```
Проверить новые endpoints через curl с JWT-токеном.

**Зависимости:** PR смержен или ветка доступна на remote

---

## Граф зависимостей и параллелизм

```
Старт
  │
  ├── 1.1 ──┐
  ├── 1.2 ──┼── (параллельно) ──► готово ──┬── 1.4 ──┐
  └── 1.3 ──┘                               ├── 1.5 ──┼── (параллельно) ──► готово ──► 1.7 ──► 1.8
                                            └── 1.6 ──┘                                         │
                                                                                       1.9 ─────┘
                                                                                        (после 1.6)
  После 1.7:
  ┌── 2.1 ──┐
  └── 2.2 ──┘ (параллельно) ──► готово
                                  │
                         ┌── 3.1 ──┐
                         └── 3.2 ──┘ (параллельно) ──► готово
                                                          │
                                             ┌── 4.1 ──┐
                                             ├── 4.2 ──┼── (параллельно) ──► готово ──► 5.1 ──► 5.2
                                             └── 4.3 ──┘
```

---

## Сводная таблица

| Пункт | Файл | Тип | Агент | Зависит от | Параллельно с |
|-------|------|-----|-------|------------|---------------|
| 1.1 | `server/database.py` | изменение | Backend | — | 1.2, 1.3 |
| 1.2 | `server/alembic/versions/e5f6g7h8i9j0_...py` | новый | Backend | — | 1.1, 1.3 |
| 1.3 | `server/schemas.py` | изменение | Backend | — | 1.1, 1.2 |
| 1.4 | `server/email_service.py` | изменение | Backend | 1.1, 1.2, 1.3 | 1.5, 1.6 |
| 1.5 | `server/telegram_bot_handlers.py` | новый | Backend | 1.1, 1.2, 1.3 | 1.4, 1.6 |
| 1.6 | `server/services/notification_dispatcher.py` | новый | Backend | 1.1, 1.2, 1.3 | 1.4, 1.5 |
| 1.7 | `server/routers/notifications_router.py` | новый | Backend | 1.4, 1.5, 1.6 | 1.9 |
| 1.8 | `server/main.py` | изменение | Backend | 1.7 | 1.9 |
| 1.9 | `server/routers/crm_router.py`, `employees_router.py` | изменение | Backend | 1.6 | 1.8 |
| 2.1 | `utils/api_client/misc_mixin.py` | изменение | API Client | 1.7 | 2.2 |
| 2.2 | `utils/data_access.py` | изменение | API Client | 2.1 | 2.1 |
| 3.1 | `ui/employees_tab.py` | изменение | Frontend | 2.1, 2.2 | 3.2 |
| 3.2 | `ui/admin_dialog.py` | изменение | Frontend | 2.1, 2.2 | 3.1 |
| 4.1 | `tests/contract/` | новый/изменение | Backend | 3.x готово | 4.2, 4.3 |
| 4.2 | `tests/smoke/test_notifications.py` | изменение | Backend | 3.x готово | 4.1, 4.3 |
| 4.3 | `tests/ui/test_notifications_ui.py` | новый | Frontend | 3.x готово | 4.1, 4.2 |
| 5.1 | git + PR | — | — | 4.1, 4.2, 4.3 | — |
| 5.2 | Docker rebuild | — | — | 5.1 | — |

---

## Чеклист верификации (после завершения)

- [ ] Alembic-миграция применена без ошибок (`alembic upgrade head`)
- [ ] `/start TOKEN` в боте → `employee.telegram_user_id` сохранён в PostgreSQL
- [ ] Кнопка "Пригласить" → письмо приходит на email сотрудника
- [ ] Кнопка "Пригласить клиента" → письмо приходит клиенту
- [ ] Смена стадии CRM → уведомление менеджеру в Telegram
- [ ] Назначение исполнителя → уведомление исполнителю в Telegram
- [ ] Admin UI вкладка "Уведомления": настройки сохраняются и применяются корректно
- [ ] Contract-тесты: все 4 новых теста зелёные
- [ ] Smoke-тесты: все 5 новых тестов зелёные
- [ ] UI тесты: все 5 новых тестов зелёные
- [ ] CI: все 5 jobs зелёные
- [ ] Docker rebuild после серверных изменений: `health` возвращает `{"status":"healthy"}`
- [ ] Curl-проверка всех 6 новых endpoints с реальным JWT-токеном
