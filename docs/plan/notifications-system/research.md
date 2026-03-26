# Исследование: Система уведомлений
Дата: 2026-03-05 (обновлено)

---

## 1. Текущее состояние проекта

### Что уже есть

**Серверная сторона:**
| Компонент | Файл | Состояние |
|-----------|------|-----------|
| SQLAlchemy модель `Notification` | `server/database.py:221` | ✅ Готово |
| Pydantic `NotificationResponse` | `server/schemas.py:405` | ✅ Готово |
| `GET /api/v1/notifications` | `server/main.py:466` | ✅ Готово |
| `PUT /api/v1/notifications/{id}/read` | `server/main.py:482` | ✅ Готово |
| Уведомления в Sync | `server/schemas.py:435` | ✅ Готово |
| Telegram сервис (MTProto + Bot API) | `server/telegram_service.py` | ✅ Полный |
| Email SMTP сервис | `server/email_service.py` | ✅ Готово |
| Автоуведомления в чаты | `server/services/notification_service.py` | ✅ Готово |
| Настройки мессенджера в БД | таблица `messenger_settings` | ✅ Готово |

**Клиентская сторона:**
| Компонент | Файл | Состояние |
|-----------|------|-----------|
| `get_notifications()` | `utils/api_client/misc_mixin.py` | ✅ Готово |
| `mark_notification_read()` | `utils/api_client/misc_mixin.py` | ✅ Готово |
| Admin UI (Telegram/SMTP) | `ui/messenger_admin_dialog.py` | ✅ Готово |

### Что НЕ СУЩЕСТВУЕТ (нужно создать)

| Компонент | Приоритет | Описание |
|-----------|-----------|----------|
| `NotificationSettings` модель | 🔴 Критично | Таблица настроек уведомлений на сотрудника |
| Alembic-миграция | 🔴 Критично | Добавить `notification_settings` + `employee.telegram_user_id` |
| POST/CRUD для настроек | 🔴 Критично | Endpoint-ы управления настройками |
| SMS сервис (SMS Aero / SMSC.ru) | 🟡 Важно | Отправка SMS через РФ агрегатора |
| Триггеры создания уведомлений | 🔴 Критично | В `crm_router.py`, `employees_router.py` |
| DataAccess методы | 🔴 Критично | `get_notifications()`, `mark_read()`, `get_notification_settings()` |
| SyncManager сигнал | 🟡 Важно | `notifications_updated` сигнал |
| Вкладка "Уведомления" в Admin-диалоге | 🔴 Критично | UI настройка каналов для каждого сотрудника |
| Бейдж уведомлений в main_window | 🟡 Важно | Иконка с счётчиком непрочитанных |
| `utils/notification_manager.py` | 🟡 Важно | QSystemTrayIcon + polling |

---

## 2. Каналы доставки — выбранный стек

| Канал | Решение | Обоснование |
|-------|---------|-------------|
| **Email** | `aiosmtplib` (уже установлен) | SMTP async, `EmailService` уже реализован |
| **Telegram** | `aiogram` (уже установлен) | Bot API, `TelegramService.send_message()` уже работает |
| **SMS** | `httpx` → SMS Aero REST API | Официальный РФ агрегатор, REST без лишних зависимостей |

**Ключевой вывод:** Все серверные инфраструктурные зависимости уже установлены. SMS нужен только легковесный HTTP-клиент (httpx уже есть через requests/fastapi).

---

## 3. Архитектура — что нужно сделать

### 3.1 База данных

**Новая таблица `notification_settings`** (один ряд на сотрудника):

```python
class NotificationSettings(Base):
    __tablename__ = "notification_settings"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), unique=True, nullable=False)

    # Каналы
    email_enabled = Column(Boolean, default=False)
    notify_email = Column(String(255))          # адрес (может отличаться от employee.email)

    telegram_enabled = Column(Boolean, default=False)
    telegram_chat_id = Column(String(100))      # личный chat_id пользователя в боте

    sms_enabled = Column(Boolean, default=False)
    notify_phone = Column(String(20))           # телефон (может отличаться от employee.phone)

    # Типы событий
    notify_crm_stage = Column(Boolean, default=True)   # смена стадии CRM
    notify_assigned = Column(Boolean, default=True)    # назначение исполнителем
    notify_deadline = Column(Boolean, default=True)    # предупреждение о дедлайне
    notify_payment = Column(Boolean, default=False)    # создание оплаты
    notify_supervision = Column(Boolean, default=False) # новый надзор

    employee = relationship("Employee", back_populates="notification_settings")
```

**Добавить в `Employee`:**
```python
notification_settings = relationship("NotificationSettings", back_populates="employee",
                                      uselist=False, cascade="all, delete-orphan")
```

### 3.2 SMS сервис (server/sms_service.py — НОВЫЙ ФАЙЛ)

```python
# SMS через SMS Aero REST API (httpx, без внешних зависимостей кроме уже установленных)
class SmsService:
    def configure(self, settings: Dict[str, str]):
        self._login = settings.get("sms_login", "")
        self._api_key = settings.get("sms_api_key", "")
        self._sender = settings.get("sms_sender", "FESTIVAL")
        self._configured = bool(self._login and self._api_key)

    async def send_sms(self, phone: str, text: str) -> bool:
        # POST https://gate.smsaero.ru/v2/sms/send
        ...
```

**Настройки SMS в `messenger_settings`** (дополнительные ключи):
- `sms_login`
- `sms_api_key`
- `sms_sender` (sender name, до 11 символов)

### 3.3 Notification Dispatcher (server/services/notification_dispatcher.py — НОВЫЙ ФАЙЛ)

Центральный диспетчер, вызываемый из роутеров:

```python
async def dispatch_notification(
    db: Session,
    employee_id: int,
    event_type: str,         # 'crm_stage_change' | 'assigned' | 'deadline' | 'payment'
    title: str,
    message: str,
    related_entity_type: str = None,
    related_entity_id: int = None,
):
    # 1. Создать запись Notification в БД
    # 2. Загрузить NotificationSettings для сотрудника
    # 3. Если email_enabled → EmailService.send_notification(...)
    # 4. Если telegram_enabled → TelegramService.send_message(chat_id, text)
    # 5. Если sms_enabled → SmsService.send_sms(phone, text)
```

### 3.4 Роутер уведомлений (server/routers/notifications_router.py — НОВЫЙ ФАЙЛ)

```
GET  /api/v1/notifications                           → список уведомлений текущего пользователя
PUT  /api/v1/notifications/{id}/read                 → отметить прочитанным
GET  /api/v1/notifications/settings/{employee_id}    → получить настройки канала
PUT  /api/v1/notifications/settings/{employee_id}    → обновить настройки канала
POST /api/v1/notifications/test                      → тестовое уведомление (Директор)
```

*(Существующие GET/PUT перенести из `server/main.py` в роутер)*

### 3.5 UI — вкладка Уведомления в Admin-диалоге

**Где:** `ui/admin_dialog.py` → добавить вкладку "Уведомления" (рядом с вкладкой "Мессенджер")

**Структура вкладки:**
```
Вкладка "Уведомления"
├── Раздел: SMS-настройки (глобальные, только Директор)
│   ├── Поле: API логин SMS Aero
│   ├── Поле: API ключ SMS Aero
│   └── Поле: SMS отправитель (до 11 символов)
│
└── Раздел: Настройки уведомлений сотрудника
    ├── Выпадающий список: Выбрать сотрудника (Директор видит всех, остальные — только себя)
    ├── Email: [✓ Включить] [поле: адрес email]
    ├── Telegram: [✓ Включить] [поле: chat_id пользователя] [кнопка: как получить?]
    ├── SMS: [✓ Включить] [поле: номер телефона]
    ├── Разделитель: Типы событий
    │   ├── [✓] Смена стадии CRM
    │   ├── [✓] Назначение исполнителем
    │   ├── [✓] Предупреждение о дедлайне
    │   ├── [ ] Создание оплаты
    │   └── [ ] Новый надзор
    └── [Сохранить] [Тест]
```

---

## 4. Триггеры уведомлений в роутерах

| Событие | Роутер | Кому | Тип |
|---------|--------|------|-----|
| Назначен исполнитель CRM стадии | `crm_router.py` | Исполнитель | `assigned` |
| Смена стадии CRM | `crm_router.py` | Менеджер карточки | `crm_stage_change` |
| Создана оплата | `payments_router.py` | Менеджер | `payment` |
| Дедлайн через N дней | Scheduler/cron | Исполнитель | `deadline` |
| Новая карточка надзора | `supervision_router.py` | Менеджер | `supervision` |

---

## 5. Как пользователь получает Telegram chat_id

Проблема: пользователь не знает свой Telegram chat_id для личных уведомлений (не групповой чат).

**Решение:** Команда `/start` в Telegram-боте CRM:
- Бот отвечает: "Ваш chat_id: 123456789"
- Пользователь копирует и вставляет в поле в CRM

**Альтернатива (упрощённая):** Кнопка "Получить chat_id" в UI открывает инструкцию с ссылкой на бот.

---

## 6. Новые зависимости

| Компонент | Зависимость | Установка |
|-----------|-------------|-----------|
| SMS Aero | `httpx` (уже есть) | Только REST API, без pip install |
| In-app toast | `pyqt-toast-notification` | `pip install pyqt-toast-notification` (опционально) |
| Scheduler | `apscheduler` | `pip install apscheduler` (для дедлайн-уведомлений, опционально фаза 2) |

**Минимальные новые зависимости для Phase 1:** **нет** (использовать httpx для SMS, уже есть aiogram и aiosmtplib).

---

## 7. План разработки — фазы

### Фаза 1: Инфраструктура (сервер)
- `server/database.py` → добавить `NotificationSettings`, связь в `Employee`
- `server/schemas.py` → добавить `NotificationSettingsCreate`, `NotificationSettingsResponse`
- `server/alembic/versions/` → миграция `add_notification_settings`
- `server/sms_service.py` → создать `SmsService` (httpx + SMS Aero)
- `server/routers/messenger_router.py` → добавить ключи `sms_*` в `load_messenger_settings()`
- `server/services/notification_dispatcher.py` → создать диспетчер
- `server/routers/notifications_router.py` → создать роутер (перенос из main.py + новые)
- `server/main.py` → подключить новый роутер, убрать дублирующие endpoint-ы

### Фаза 2: Триггеры событий (сервер)
- `server/routers/crm_router.py` → добавить вызов `dispatch_notification` при смене стадии
- `server/routers/employees_router.py` → триггер при назначении исполнителя
- `server/routers/payments_router.py` → триггер при создании оплаты

### Фаза 3: Клиент — DataAccess и SyncManager
- `utils/data_access.py` → `get_notifications()`, `mark_notification_read()`, `get_notification_settings()`, `update_notification_settings()`
- `utils/sync_manager.py` → сигнал `notifications_updated`, обработка в `sync()`
- `database/db_manager.py` → таблица `notifications` offline, CRUD методы

### Фаза 4: UI — Admin и главное окно
- `ui/admin_dialog.py` → вкладка "Уведомления"
- Новый виджет `NotificationSettingsWidget` (по образцу `MessengerSettingsWidget`)
- `ui/main_window.py` → бейдж/кнопка уведомлений

---

## 8. Чеклист верификации

- [ ] Alembic-миграция применена без ошибок
- [ ] `GET /api/v1/notifications` возвращает данные с JWT
- [ ] `GET/PUT /api/v1/notifications/settings/{id}` работают
- [ ] Email отправляется (SMTP тест)
- [ ] Telegram бот отправляет личное сообщение по chat_id
- [ ] SMS через SMS Aero (тест с реальным номером)
- [ ] Admin UI: настройки сохраняются в БД
- [ ] Триггер: смена стадии CRM → уведомление менеджеру
- [ ] Contract-тест для новых API ответов
- [ ] Docker rebuild после серверных изменений

---

## Источники из github-search.md

- [apprise (16k ⭐)](https://github.com/caronc/apprise) — мультиканальный, MIT
- [fastapi-mail (980 ⭐)](https://github.com/sabuhish/fastapi-mail) — nativeFastAPI email
- [python-telegram-bot (28.9k ⭐)](https://github.com/python-telegram-bot/python-telegram-bot) — Telegram Bot
- [aiogram (5.6k ⭐)](https://github.com/aiogram/aiogram) — уже в проекте
- [pyqttoast (146 ⭐)](https://github.com/niklashenning/pyqttoast) — toast в PyQt5
- [SMS Aero API](https://smsaero.ru/integration/class/python/) — РФ SMS агрегатор
