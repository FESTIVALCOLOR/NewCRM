# План реализации: Система уведомлений
Дата: 2026-03-06 | Статус: ГОТОВ К РЕАЛИЗАЦИИ

---

## Скоуп (согласован)

**Реализуем:**
- Telegram личные уведомления сотрудникам (через бота)
- Email-приглашение сотруднику при создании (онбординг)
- Email-приглашение клиенту в проектный чат
- Кнопка "Пригласить" в странице сотрудников
- Кнопка "Пригласить клиента" в карточке CRM (чат)
- Admin UI: настройки уведомлений для каждого сотрудника

**НЕ реализуем сейчас:**
- SMS
- In-app бейдж уведомлений (отдельная фаза)
- APScheduler для дедлайн-уведомлений (отдельная фаза)

---

## HTML-шаблоны писем (согласованы)

- `docs/plan/notifications-system/welcome_email_preview.html` — письмо сотруднику
- `docs/plan/notifications-system/client_invite_email_preview.html` — письмо клиенту
- Генератор: `docs/plan/notifications-system/gen_emails.py`

---

## Фаза 1: Серверная инфраструктура

### 1.1 БД — новая таблица + поля в Employee

**Файл:** `server/database.py`

Добавить в `Employee`:
```python
telegram_user_id = Column(BigInteger, nullable=True)           # личный Telegram ID
telegram_link_token = Column(String(32), nullable=True)        # одноразовый токен
telegram_link_token_expires = Column(DateTime, nullable=True)  # срок 7 дней
```

Новая таблица `notification_settings`:
```python
class NotificationSettings(Base):
    __tablename__ = "notification_settings"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), unique=True, nullable=False)
    # каналы
    telegram_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=False)
    # типы событий
    notify_crm_stage = Column(Boolean, default=True)
    notify_assigned = Column(Boolean, default=True)
    notify_deadline = Column(Boolean, default=True)
    notify_payment = Column(Boolean, default=False)
    notify_supervision = Column(Boolean, default=False)
    employee = relationship("Employee", back_populates="notification_settings")
```

Добавить в `Employee`:
```python
notification_settings = relationship("NotificationSettings",
    back_populates="employee", uselist=False, cascade="all, delete-orphan")
```

### 1.2 Alembic-миграция

**Файл:** `server/alembic/versions/e5f6g7h8i9j0_add_notifications_system.py`

Добавить колонки в `employees` + создать таблицу `notification_settings`.

### 1.3 Pydantic схемы

**Файл:** `server/schemas.py`

```python
class NotificationSettingsResponse(BaseModel):
    employee_id: int
    telegram_enabled: bool
    email_enabled: bool
    notify_crm_stage: bool
    notify_assigned: bool
    notify_deadline: bool
    notify_payment: bool
    notify_supervision: bool
    telegram_connected: bool  # вычисляемое: telegram_user_id is not None
    class Config: from_attributes = True

class NotificationSettingsUpdate(BaseModel):
    telegram_enabled: bool = True
    email_enabled: bool = False
    notify_crm_stage: bool = True
    notify_assigned: bool = True
    notify_deadline: bool = True
    notify_payment: bool = False
    notify_supervision: bool = False
```

### 1.4 Email-сервис — новый метод

**Файл:** `server/email_service.py`

Добавить методы:
```python
async def send_welcome_email(self, to_email, employee_name, login,
                              password, download_link, telegram_token,
                              bot_username="festival_color_crm_bot") -> bool

async def send_client_chat_invite(self, to_email, client_name,
                                   project_address, project_type,
                                   manager_name, invite_link) -> bool
```

HTML шаблоны — из согласованных preview-файлов (встроить как строки в сервис).
Логотип и footer.jpg — кодировать в base64 и вшивать в письмо при отправке.

### 1.5 Telegram bot handlers — обработчик /start

**Файл:** `server/telegram_bot_handlers.py` (НОВЫЙ)

```python
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()

@router.message(CommandStart())
async def handle_start(message: Message):
    args = message.text.split(maxsplit=1)
    token = args[1] if len(args) > 1 else None
    if not token:
        await message.answer("Для подключения используйте ссылку из приветственного письма.")
        return
    db = SessionLocal()
    try:
        employee = db.query(Employee).filter(
            Employee.telegram_link_token == token,
            Employee.telegram_link_token_expires > datetime.utcnow()
        ).first()
        if not employee:
            await message.answer("Ссылка недействительна или устарела. Попросите администратора выслать приглашение повторно.")
            return
        employee.telegram_user_id = message.from_user.id
        employee.telegram_link_token = None
        employee.telegram_link_token_expires = None
        db.commit()
        first_name = employee.full_name.split()[1] if len(employee.full_name.split()) > 1 else employee.full_name
        await message.answer(
            f"✅ Отлично, {first_name}!\n\n"
            f"Ваш аккаунт привязан к CRM Festival Color.\n"
            f"Теперь вы будете получать уведомления:\n\n"
            f"• Назначение на стадии\n"
            f"• Напоминания о дедлайнах\n"
            f"• Изменения по проектам"
        )
    finally:
        db.close()
```

### 1.6 Notification Dispatcher

**Файл:** `server/services/notification_dispatcher.py` (НОВЫЙ)

```python
async def dispatch_notification(
    db: Session,
    employee_id: int,
    event_type: str,  # 'assigned' | 'crm_stage_change' | 'deadline' | 'payment' | 'supervision'
    title: str,
    message: str,
    related_entity_type: str = None,
    related_entity_id: int = None,
):
    # 1. Создать запись Notification в БД
    notification = Notification(employee_id=employee_id, ...)
    db.add(notification)
    db.flush()

    # 2. Загрузить NotificationSettings
    settings = db.query(NotificationSettings).filter_by(employee_id=employee_id).first()
    if not settings:
        return  # нет настроек — не отправляем

    # 3. Проверить флаг типа события
    event_flag_map = {
        'assigned': settings.notify_assigned,
        'crm_stage_change': settings.notify_crm_stage,
        'deadline': settings.notify_deadline,
        'payment': settings.notify_payment,
        'supervision': settings.notify_supervision,
    }
    if not event_flag_map.get(event_type, False):
        return

    # 4. Отправить через Telegram если включён
    employee = db.query(Employee).filter_by(id=employee_id).first()
    if settings.telegram_enabled and employee and employee.telegram_user_id:
        tg = get_telegram_service()
        await tg.send_message(employee.telegram_user_id, f"<b>{title}</b>\n{message}")
```

### 1.7 Роутер уведомлений

**Файл:** `server/routers/notifications_router.py` (НОВЫЙ)

Endpoints:
```
GET  /api/v1/notifications                              → список (перенести из main.py)
PUT  /api/v1/notifications/{id}/read                    → отметить прочитанным (перенести)
GET  /api/v1/notifications/settings/{employee_id}       → настройки канала
PUT  /api/v1/notifications/settings/{employee_id}       → обновить настройки
POST /api/v1/employees/{employee_id}/send-invite        → отправить приглашение
POST /api/v1/notifications/test                         → тест уведомления (Директор)
```

### 1.8 Запуск aiogram polling при старте FastAPI

**Файл:** `server/main.py`

В `lifespan`:
```python
from telegram_bot_handlers import router as bot_router
from aiogram import Dispatcher as BotDispatcher

@asynccontextmanager
async def lifespan(app):
    # ... существующий код ...
    dp = BotDispatcher()
    dp.include_router(bot_router)
    bot = get_telegram_service()._bot
    if bot:
        asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    yield
    # ... shutdown ...
```

### 1.9 Триггеры событий в роутерах

**Файл:** `server/routers/crm_router.py`
- При смене стадии → `dispatch_notification(manager_id, 'crm_stage_change', ...)`
- При назначении исполнителя → `dispatch_notification(executor_id, 'assigned', ...)`

**Файл:** `server/routers/employees_router.py`
- При добавлении сотрудника в чат → auto-populate `MessengerChatMember.telegram_user_id` из `Employee.telegram_user_id`

---

## Фаза 2: Кнопка "Пригласить" в странице сотрудников

**Файл:** `ui/employees_tab.py`

- Добавить кнопку-иконку в строку действий сотрудника (без текста, tooltip "Отправить приглашение")
- SVG иконка: `mail.svg` или `send.svg` из `resources/icons/`
- При нажатии: API call `POST /api/v1/employees/{id}/send-invite`
- Если `telegram_user_id` уже заполнен → иконка "✓ Telegram подключён" (зелёная), кнопка недоступна
- Если email не заполнен → показать CustomMessageBox "Email сотрудника не заполнен"

---

## Фаза 3: Кнопка "Пригласить клиента" в карточке CRM (чат)

**Файл:** `ui/crm_card_edit_dialog.py` или `ui/messenger_admin_dialog.py`

- В секции управления чатом добавить кнопку "Пригласить клиента"
- При нажатии: API call `POST /api/v1/messenger/chats/{chat_id}/invite-client`
- Сервер берёт email клиента из `Contract.client.email`, отправляет `send_client_chat_invite()`

---

## Фаза 4: Admin UI — вкладка "Уведомления"

**Файл:** `ui/admin_dialog.py`

Новая вкладка "Уведомления" (рядом с "Мессенджером"):
- Выпадающий список сотрудников (Директор видит всех, остальные — только себя)
- Секция "Telegram": [✓ включить] + статус "Подключён / Не подключён"
- Секция "Типы событий": флажки (смена стадии, назначение, дедлайн, оплата, надзор)
- Кнопка [Сохранить] → PUT /api/v1/notifications/settings/{id}
- Кнопка [Тест] → POST /api/v1/notifications/test

---

## Фаза 5: Клиентская сторона

**Файл:** `utils/data_access.py`
- `get_notification_settings(employee_id)` → DataAccess метод
- `update_notification_settings(employee_id, data)` → DataAccess метод

**Файл:** `utils/api_client/misc_mixin.py`
- `get_notification_settings(employee_id)` → GET запрос
- `update_notification_settings(employee_id, data)` → PUT запрос
- `send_employee_invite(employee_id)` → POST запрос

---

## Ключевые файлы изменений

| Файл | Действие |
|------|----------|
| `server/database.py` | +3 поля в Employee, +класс NotificationSettings |
| `server/alembic/versions/` | новая миграция |
| `server/schemas.py` | +NotificationSettingsResponse/Update |
| `server/email_service.py` | +send_welcome_email, +send_client_chat_invite |
| `server/telegram_bot_handlers.py` | НОВЫЙ: /start handler |
| `server/services/notification_dispatcher.py` | НОВЫЙ: dispatch_notification |
| `server/routers/notifications_router.py` | НОВЫЙ: CRUD + invite endpoints |
| `server/routers/crm_router.py` | триггеры событий |
| `server/routers/employees_router.py` | auto-populate telegram_user_id в чат |
| `server/main.py` | подключить роутер + aiogram polling |
| `utils/api_client/misc_mixin.py` | +методы для настроек и invite |
| `utils/data_access.py` | +методы для настроек |
| `ui/employees_tab.py` | кнопка "Пригласить" |
| `ui/admin_dialog.py` | вкладка "Уведомления" |

---

## Зависимости — новых нет

Все библиотеки уже установлены:
- `aiogram==3.25.0` — Telegram Bot API
- `aiosmtplib==3.0.2` — SMTP
- `pyrogram==2.0.106` — MTProto

---

## Чеклист верификации

- [ ] Alembic-миграция применена без ошибок
- [ ] `/start TOKEN` в боте → `employee.telegram_user_id` сохранён
- [ ] Кнопка "Пригласить" → письмо приходит на email сотрудника
- [ ] Кнопка "Пригласить клиента" → письмо приходит клиенту
- [ ] Смена стадии CRM → уведомление менеджеру в Telegram
- [ ] Назначение исполнителя → уведомление исполнителю в Telegram
- [ ] Admin UI: настройки сохраняются и применяются
- [ ] Contract-тест для новых API endpoints
- [ ] Docker rebuild после серверных изменений
