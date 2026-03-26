# GitHub Search: Система уведомлений

> Исследование выполнено: 2026-03-05
> Проект: Interior Studio CRM (FastAPI + PyQt5 + PostgreSQL)

---

## Библиотеки по каналам

### Email

| Библиотека | Лицензия | Python 3.11+ | Звёзды | Сложность | Примечание |
|-----------|----------|:------------:|--------|:---------:|------------|
| **fastapi-mail** | MIT | Да | ~980 | Низкая | FastAPI native, async SMTP, Jinja2 шаблоны, Background Tasks, активно поддерживается (v1.6.2, фев 2026) |
| **smtplib** (stdlib) | PSF | Да | — | Низкая | Встроен в Python, синхронный, требует обёртки для async |
| **aiosmtplib** | MIT | Да | ~800 | Низкая | Async SMTP без лишних зависимостей, используется внутри fastapi-mail |
| **yagmail** | MIT | Да | ~2.5k | Низкая | Упрощённая отправка через Gmail OAuth/пароль, плохо подходит для production SMTP |
| **sendgrid-python** | MIT | Да | ~1.5k | Средняя | Облачный провайдер, требует платного аккаунта SendGrid |
| **fastapi-mailman** | BSD | Да | ~100 | Низкая | Порт Django email на FastAPI, поддерживает несколько бэкендов |

**Рекомендация для проекта:** `fastapi-mail` — нативная интеграция с FastAPI, BackgroundTasks, async, Jinja2 шаблоны. Для базового SMTP достаточно `aiosmtplib` напрямую.

---

### Telegram

| Библиотека | Лицензия | Python 3.11+ | Звёзды | Сложность | Примечание |
|-----------|----------|:------------:|--------|:---------:|------------|
| **python-telegram-bot** | LGPL-3.0 | Да (3.10+) | ~28.9k | Низкая | Самая популярная, полная поддержка Bot API 9.3, async с v20+, большое сообщество |
| **aiogram** | MIT | Да (3.10+) | ~5.6k | Средняя | Полностью async с asyncio, производительнее под нагрузкой, FSM, middleware |
| **pyTelegramBotAPI (telebot)** | GPL-2.0 | Да | ~8k | Низкая | Простейший синхронный/async API, минимальный boilerplate |
| **telethon** | MIT | Да | ~10k | Высокая | Клиент (не бот) — работа от имени пользователя через MTProto |

**Рекомендация для проекта:** `python-telegram-bot` — для отправки уведомлений через бота (простой паттерн bot.send_message). Если нужна только отправка уведомлений без диалогов — можно использовать `requests` напрямую к Bot API (без библиотек).

---

### SMS (РФ рынок)

| Провайдер/API | PyPI пакет | Цена (РФ) | Примечание |
|--------------|-----------|:---------|------------|
| **SMS Aero** (smsaero.ru) | `smsaero-api` | ~1-4 руб/смс | Официальный Python клиент, REST API, поддержка async, популярен в РФ |
| **SMSC.ru** | `smsru-api` | ~1-3 руб/смс | Один из старейших РФ агрегаторов, простое HTTP API |
| **SMS.ru** | `smsru-api` | ~1-4 руб/смс | Популярен в РФ, пакет на PyPI |
| **Twilio** | `twilio` | ~$0.07-0.70/смс | Глобальный провайдер, дорогой для РФ, могут быть ограничения доставки |
| **Vonage (Nexmo)** | `vonage` | ~$0.05-0.50/смс | Альтернатива Twilio, аналогичные ограничения |

**Рекомендация для проекта:** `smsaero-api` (SMS Aero) или SMSC.ru — наиболее дешёвые и надёжные для РФ рынка с минимальными зависимостями. SMS Aero имеет официальный Python клиент на PyPI.

---

### Многоканальные решения

| Библиотека | Каналы | Лицензия | Звёзды | Примечание |
|-----------|--------|----------|--------|------------|
| **apprise** | 100+ (Email, Telegram, SMS, Slack, Discord, ...) | BSD-2 | ~16k | Самое полное решение, единый интерфейс для всех каналов, CLI + library |
| **notifiers** | 18+ (Email/SMTP, Telegram, Twilio, Slack, ...) | MIT | ~2.7k | Простой unified API, минимум зависимостей (requests, jsonschema, click) |
| **async-notify** | Email, Telegram, Twilio, Slack, o365, ... | MIT | ~50 | Async-first на asyncio, поддерживает несколько провайдеров |
| **pyndm** | Email, Telegram, SMS | MIT | ~10 | Лёгкая библиотека, мало звёзд — риск заброшенности |

**Рекомендация:** `apprise` — если нужна гибкость и много каналов в одной библиотеке. `notifiers` — если нужен простой синхронный API с минимумом зависимостей.

---

### PyQt5 — внутриприложенческие уведомления

| Библиотека | Лицензия | PyQt5 | Звёзды | Примечание |
|-----------|----------|:-----:|--------|------------|
| **pyqttoast** (pyqt-toast-notification) | MIT | Да | ~146 | Toast уведомления внутри приложения, 7 позиций, очередь, пресеты (success/error/warning) |
| **QSystemTrayIcon** (PyQt5 built-in) | — | Да | — | Системные уведомления ОС через трей, встроен в PyQt5 |

**Рекомендация для CRM:** `pyqttoast` для inline-уведомлений внутри приложения + `QSystemTrayIcon.showMessage()` для системных уведомлений (когда приложение свёрнуто).

---

## Паттерны реализации

### Паттерн 1: FastAPI BackgroundTasks (рекомендован для проекта)

Наиболее простой и встроенный способ — подходит для уведомлений с низкой нагрузкой (десятки/сотни в минуту).

```python
# server/routers/notifications_router.py
from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import httpx

router = APIRouter(prefix="/notifications", tags=["notifications"])

# --- Email через fastapi-mail ---
mail_config = ConnectionConfig(
    MAIL_USERNAME="noreply@example.com",
    MAIL_PASSWORD="...",
    MAIL_FROM="noreply@example.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.example.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
)
fastmail = FastMail(mail_config)

async def send_email_notification(to: str, subject: str, body: str):
    message = MessageSchema(
        subject=subject,
        recipients=[to],
        body=body,
        subtype="html"
    )
    await fastmail.send_message(message)

# --- Telegram через Bot API (без библиотек) ---
async def send_telegram_notification(chat_id: str, text: str, bot_token: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": text})

# --- Endpoint с BackgroundTasks ---
@router.post("/send")
async def trigger_notification(
    background_tasks: BackgroundTasks,
    employee_id: int,
):
    settings = await get_employee_notification_settings(employee_id)
    if settings.email_enabled and settings.email:
        background_tasks.add_task(
            send_email_notification,
            settings.email,
            "Уведомление от CRM",
            "<p>Тестовое уведомление</p>"
        )
    if settings.telegram_enabled and settings.telegram_chat_id:
        background_tasks.add_task(
            send_telegram_notification,
            settings.telegram_chat_id,
            "Уведомление от CRM",
            settings.telegram_bot_token
        )
    return {"status": "queued"}
```

**Источник:** [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) | [FastAPI-Mail GitHub](https://github.com/sabuhish/fastapi-mail)

**Когда использовать:** простые уведомления (email, telegram, SMS) без гарантий доставки, без retry, без мониторинга очереди.

---

### Паттерн 2: Celery + Redis (async очередь)

Подходит при высокой нагрузке, необходимости retry, мониторинга задач, распределённой обработки.

```python
# celery_app.py
from celery import Celery

celery_app = Celery("notifications", broker="redis://localhost:6379/0")

@celery_app.task(bind=True, max_retries=3)
def send_notification_task(self, channel: str, recipient: str, message: str):
    try:
        if channel == "email":
            # send email
            pass
        elif channel == "telegram":
            # send telegram
            pass
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

# FastAPI endpoint вызывает Celery задачу:
@router.post("/send")
async def send_notification(data: NotificationRequest):
    send_notification_task.delay("email", data.email, data.message)
    return {"status": "queued"}
```

**Источник:** [Asynchronous Tasks with FastAPI and Celery](https://testdriven.io/blog/fastapi-and-celery/)

**Применимость:** для проекта Interior Studio CRM на текущем этапе Celery **избыточен** — BackgroundTasks достаточно. Celery оправдан при >1000 уведомлений/час или необходимости retry с persistence.

---

### Паттерн 3: Admin настройки уведомлений (DB модель)

Хранение настроек уведомлений пользователя в БД.

```python
# server/models.py (SQLAlchemy)
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class NotificationSettings(Base):
    """Настройки уведомлений для сотрудника"""
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), unique=True, nullable=False)

    # Email канал
    email_enabled = Column(Boolean, default=False)
    email = Column(String(255), nullable=True)

    # Telegram канал
    telegram_enabled = Column(Boolean, default=False)
    telegram_chat_id = Column(String(100), nullable=True)
    telegram_bot_token = Column(String(100), nullable=True)

    # SMS канал
    sms_enabled = Column(Boolean, default=False)
    phone = Column(String(20), nullable=True)

    # Типы событий
    notify_on_crm_stage_change = Column(Boolean, default=True)
    notify_on_payment = Column(Boolean, default=True)
    notify_on_deadline = Column(Boolean, default=True)
    notify_on_new_supervision = Column(Boolean, default=False)

    employee = relationship("Employee", back_populates="notification_settings")
```

```python
# server/schemas.py (Pydantic)
from pydantic import BaseModel, EmailStr
from typing import Optional

class NotificationSettingsUpdate(BaseModel):
    email_enabled: bool = False
    email: Optional[EmailStr] = None
    telegram_enabled: bool = False
    telegram_chat_id: Optional[str] = None
    sms_enabled: bool = False
    phone: Optional[str] = None
    notify_on_crm_stage_change: bool = True
    notify_on_payment: bool = True
    notify_on_deadline: bool = True
    notify_on_new_supervision: bool = False
```

```python
# server/routers/admin_router.py — CRUD для настроек
@router.get("/employees/{employee_id}/notification-settings")
async def get_notification_settings(employee_id: int, db: AsyncSession = Depends(get_db)):
    settings = await db.get(NotificationSettings, employee_id)
    return settings

@router.put("/employees/{employee_id}/notification-settings")
async def update_notification_settings(
    employee_id: int,
    data: NotificationSettingsUpdate,
    db: AsyncSession = Depends(get_db)
):
    settings = await db.get(NotificationSettings, employee_id)
    if not settings:
        settings = NotificationSettings(employee_id=employee_id)
        db.add(settings)
    for key, value in data.dict().items():
        setattr(settings, key, value)
    await db.commit()
    return settings
```

**Источник:** [Building a Modern Permission System with FastAPI, SQLAlchemy](https://dev.to/mochafreddo/building-a-modern-user-permission-management-system-with-fastapi-sqlalchemy-and-mariadb-5fp1) | [FastAPI SQL Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/)

---

### Паттерн 4: Apprise — универсальный мультиканальный отправщик

```python
import apprise

async def send_notification_apprise(
    email: str | None,
    telegram_chat_id: str | None,
    telegram_bot_token: str | None,
    message: str,
    title: str = "Interior Studio CRM"
):
    apobj = apprise.Apprise()

    if email:
        apobj.add(f"mailtos://smtp_user:smtp_pass@smtp.example.com/{email}")
    if telegram_chat_id and telegram_bot_token:
        apobj.add(f"tgram://{telegram_bot_token}/{telegram_chat_id}/")

    await apobj.async_notify(title=title, body=message)
```

**Достоинства:** единый API для всех каналов, 100+ провайдеров, MIT лицензия, 16k звёзд.
**Недостатки:** крупная зависимость, URL-формат строк конфигурации непривычен.

**Источник:** [Apprise GitHub](https://github.com/caronc/apprise) | [Apprise PyPI](https://pypi.org/project/apprise/)

---

### Паттерн 5: PyQt5 — внутриприложенческие уведомления

```python
# ui/notifications.py
from PyQt5.QtWidgets import QSystemTrayIcon, QApplication
from PyQt5.QtGui import QIcon

# Toast через pyqttoast
from pyqttoast import Toast, ToastPreset

def show_toast(parent_widget, title: str, text: str, preset=ToastPreset.SUCCESS):
    toast = Toast(parent_widget)
    toast.setDuration(4000)
    toast.setTitle(title)
    toast.setText(text)
    toast.applyPreset(preset)
    toast.show()

# Системное уведомление ОС (через трей)
def show_system_notification(tray_icon: QSystemTrayIcon, title: str, message: str):
    tray_icon.showMessage(
        title,
        message,
        QSystemTrayIcon.Information,
        3000  # миллисекунды
    )
```

**Источник:** [pyqttoast GitHub](https://github.com/niklashenning/pyqttoast) | [PyPI pyqt-toast-notification](https://pypi.org/project/pyqt-toast-notification/)

---

## Рекомендованный стек

### Итоговые рекомендации по каналам

| Канал | Рекомендация | Пакет | Обоснование |
|-------|-------------|-------|-------------|
| **Email** | `fastapi-mail` | `fastapi-mail` | Нативная интеграция с FastAPI, async, Jinja2, 980 звёзд, активно поддерживается |
| **Telegram Bot** | Прямой Bot API | `httpx` (уже в проекте) | Для отправки уведомлений не нужна отдельная библиотека — достаточно POST к `api.telegram.org`. Если нужен полноценный бот — `python-telegram-bot` (28.9k звёзд, LGPL) |
| **SMS (РФ)** | SMS Aero | `smsaero-api` | Официальный Python клиент, популярен в РФ, дешевле Twilio |
| **Мультиканал** | `apprise` (опционально) | `apprise` | Если нужен единый интерфейс для 3+ каналов |
| **In-app PyQt5** | `pyqttoast` + `QSystemTrayIcon` | `pyqt-toast-notification` | Toast внутри приложения + системные уведомления ОС |
| **Очередь задач** | FastAPI BackgroundTasks | встроен | Достаточно для проекта; Celery — только при >1k уведом/час |

### Критерии выбора для Interior Studio CRM

1. **Минимум новых зависимостей** — использовать `httpx` (уже есть) для Telegram Bot API
2. **Async-first** — `fastapi-mail` + `aiosmtplib` для email
3. **РФ рынок** — SMS Aero или SMSC.ru вместо Twilio
4. **Хранение настроек** — отдельная таблица `notification_settings` в PostgreSQL (SQLAlchemy модель)
5. **UI настроек** — диалог в PyQt5 с полями: email, telegram_chat_id, phone, флаги включения
6. **Delivery паттерн** — FastAPI BackgroundTasks (не Celery, нет необходимости)

### Миграционный путь

```
Phase 1: Email (fastapi-mail + SMTP) → самое простое, нет внешних платных сервисов
Phase 2: Telegram (httpx + Bot API) → бесплатно, популярно в РФ
Phase 3: SMS (smsaero-api) → платный, добавить по требованию
```

---

## Источники

- [apprise — GitHub (16k звёзд)](https://github.com/caronc/apprise)
- [fastapi-mail — GitHub (980 звёзд)](https://github.com/sabuhish/fastapi-mail)
- [python-telegram-bot — GitHub (28.9k звёзд)](https://github.com/python-telegram-bot/python-telegram-bot)
- [aiogram — GitHub (5.6k звёзд)](https://github.com/aiogram/aiogram)
- [notifiers — GitHub (2.7k звёзд)](https://github.com/liiight/notifiers)
- [pyqttoast — GitHub (146 звёзд)](https://github.com/niklashenning/pyqttoast)
- [smsaero-api — PyPI](https://pypi.org/project/smsaero-api/)
- [SMS Aero Python integration](https://smsaero.ru/integration/class/python/)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Asynchronous Tasks with FastAPI and Celery](https://testdriven.io/blog/fastapi-and-celery/)
- [notifiers — PyPI](https://pypi.org/project/notifiers/)
- [apprise — PyPI](https://pypi.org/project/apprise/)
- [async-notify — PyPI](https://pypi.org/project/async-notify/1.3.0/)
