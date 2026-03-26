# Руководство по реализации встроенного чата Interior Studio CRM

**Дата создания:** 2026-03-23
**Статус:** План реализации (на основании исследования `research-report.md`)
**Целевой стек:** FastAPI WebSocket + PostgreSQL + Quasar PWA + PyQt5 Desktop

---

## Оглавление

1. [Схема базы данных (PostgreSQL + Alembic)](#1-схема-базы-данных)
2. [SQLAlchemy модели](#2-sqlalchemy-модели)
3. [Alembic миграция](#3-alembic-миграция)
4. [WebSocket — ConnectionManager](#4-websocket--connectionmanager)
5. [WebSocket endpoint (FastAPI)](#5-websocket-endpoint-fastapi)
6. [REST API endpoints](#6-rest-api-endpoints)
7. [Pydantic-схемы (chat_schemas.py)](#7-pydantic-схемы)
8. [Обработка файлов в чате](#8-обработка-файлов-в-чате)
9. [Push-уведомления](#9-push-уведомления)
10. [PyQt5 Desktop клиент (QWebSocket)](#10-pyqt5-desktop-клиент)
11. [Quasar PWA — компоненты чата](#11-quasar-pwa--компоненты-чата)
12. [Конфигурация nginx для WebSocket](#12-конфигурация-nginx)
13. [Docker — изменения](#13-docker--изменения)
14. [Серверные требования и масштабирование](#14-серверные-требования)
15. [Centrifugo (масштабирование 500+ пользователей)](#15-centrifugo)
16. [Референсный проект](#16-референсный-проект)
17. [Чеклист реализации](#17-чеклист-реализации)

---

## 1. Схема базы данных

### Таблицы (5 штук)

Все таблицы добавляются к существующей PostgreSQL БД `interior_studio_crm` через Alembic миграцию.

```sql
-- =============================================================
-- ТАБЛИЦА 1: ЧАТЫ
-- =============================================================
-- Типы чатов:
--   'direct'  — личная переписка 1:1
--   'group'   — групповой чат (произвольный)
--   'project' — привязан к договору (contract_id)
-- =============================================================
CREATE TABLE chat (
    id SERIAL PRIMARY KEY,
    guid UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    chat_type VARCHAR(10) NOT NULL,        -- 'direct', 'group', 'project'
    name VARCHAR(255),                      -- Название чата (NULL для direct)
    contract_id INTEGER REFERENCES contracts(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE chat IS 'Чаты системы — личные, групповые, проектные';
COMMENT ON COLUMN chat.guid IS 'UUID для использования в URL (вместо id)';
COMMENT ON COLUMN chat.chat_type IS 'direct — 1:1, group — групповой, project — привязан к договору';
COMMENT ON COLUMN chat.contract_id IS 'Связь с договором (только для project-чатов)';

-- =============================================================
-- ТАБЛИЦА 2: УЧАСТНИКИ ЧАТА
-- =============================================================
-- Составной PK (user_id, chat_id) — один пользователь в одном чате один раз.
-- role: 'admin' — может добавлять/удалять участников, 'member' — обычный, 'client' — клиент.
-- =============================================================
CREATE TABLE chat_participant (
    user_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    chat_id INTEGER NOT NULL REFERENCES chat(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member' NOT NULL,   -- 'admin', 'member', 'client'
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (user_id, chat_id)
);

COMMENT ON TABLE chat_participant IS 'Участники чатов (M:N связь employees <-> chat)';
COMMENT ON COLUMN chat_participant.is_active IS 'FALSE = пользователь покинул чат (мягкое удаление)';

-- =============================================================
-- ТАБЛИЦА 3: СООБЩЕНИЯ
-- =============================================================
-- message_type:
--   'text'   — обычное текстовое сообщение
--   'file'   — файловое сообщение (вложения в message_attachment)
--   'system' — системное ("Пользователь добавлен", "Чат создан")
-- =============================================================
CREATE TABLE message (
    id SERIAL PRIMARY KEY,
    guid UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
    chat_id INTEGER NOT NULL REFERENCES chat(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    message_type VARCHAR(10) DEFAULT 'text' NOT NULL,  -- 'text', 'file', 'system'
    reply_to_id INTEGER REFERENCES message(id) ON DELETE SET NULL,
    is_edited BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE message IS 'Сообщения в чатах';
COMMENT ON COLUMN message.guid IS 'UUID для идемпотентности при отправке с клиента';
COMMENT ON COLUMN message.reply_to_id IS 'Ответ на сообщение (цитирование)';
COMMENT ON COLUMN message.is_deleted IS 'Мягкое удаление — контент заменяется на "Сообщение удалено"';

-- =============================================================
-- ТАБЛИЦА 4: СТАТУС ПРОЧТЕНИЯ
-- =============================================================
-- ОДНА строка на пользователя/чат (как в WhatsApp).
-- last_read_message_id — ID последнего прочитанного сообщения.
-- Непрочитанные = все message.id > last_read_message_id в данном чате.
-- Это значительно эффективнее, чем хранить статус на каждое сообщение.
-- =============================================================
CREATE TABLE read_status (
    user_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    chat_id INTEGER NOT NULL REFERENCES chat(id) ON DELETE CASCADE,
    last_read_message_id INTEGER REFERENCES message(id) ON DELETE SET NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, chat_id)
);

COMMENT ON TABLE read_status IS 'Прогресс чтения — одна строка на пользователя/чат';

-- =============================================================
-- ТАБЛИЦА 5: ВЛОЖЕНИЯ К СООБЩЕНИЯМ
-- =============================================================
-- Файлы хранятся на Яндекс.Диске (интеграция уже есть).
-- file_path — путь на Яндекс.Диске (disk:/CRM/Chat/...).
-- thumbnail_path — путь к миниатюре (для изображений).
-- =============================================================
CREATE TABLE message_attachment (
    id SERIAL PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES message(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,       -- Путь на Яндекс.Диске
    file_type VARCHAR(50),                   -- MIME type (image/jpeg, application/pdf...)
    file_size INTEGER,                       -- Размер в байтах
    thumbnail_path VARCHAR(1000),            -- Путь к миниатюре (Яндекс.Диск)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE message_attachment IS 'Вложения к сообщениям (файлы на Яндекс.Диске)';

-- =============================================================
-- ИНДЕКСЫ
-- =============================================================

-- Быстрая выборка сообщений чата (последние первыми) — основной запрос
CREATE INDEX idx_message_chat_created ON message(chat_id, created_at DESC);

-- Поиск всех чатов пользователя
CREATE INDEX idx_chat_participant_user ON chat_participant(user_id) WHERE is_active = TRUE;

-- Быстрое получение статуса прочтения
CREATE INDEX idx_read_status_user_chat ON read_status(user_id, chat_id);

-- Вложения к сообщению
CREATE INDEX idx_attachment_message ON message_attachment(message_id);

-- Поиск project-чатов по договору
CREATE INDEX idx_chat_contract ON chat(contract_id) WHERE contract_id IS NOT NULL;

-- Поиск непрочитанных сообщений (для badge count)
CREATE INDEX idx_message_chat_id ON message(chat_id, id);
```

### ER-диаграмма (текстовая)

```
employees ──┐
             ├──< chat_participant >──┐
             │                        │
             ├──< message             ├── chat ──── contracts
             │       │                │
             ├──< read_status >───────┘
             │
             └──< message_attachment ──── message
```

---

## 2. SQLAlchemy модели

Файл: `server/database.py` — добавить в конец, после существующих моделей.

```python
# =========================
# ЧАТЫ (встроенный мессенджер)
# =========================

import uuid
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class Chat(Base):
    """Чат — личный, групповой или проектный"""
    __tablename__ = "chat"

    id = Column(Integer, primary_key=True, index=True)
    guid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    chat_type = Column(String(10), nullable=False)  # 'direct', 'group', 'project'
    name = Column(String(255), nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    # Связи
    participants = relationship("ChatParticipant", back_populates="chat", lazy="selectin")
    messages = relationship("Message", back_populates="chat", lazy="dynamic")
    contract = relationship("Contract", backref="chats")


class ChatParticipant(Base):
    """Участник чата"""
    __tablename__ = "chat_participant"

    user_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True)
    chat_id = Column(Integer, ForeignKey("chat.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(20), default="member", nullable=False)  # 'admin', 'member', 'client'
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Связи
    chat = relationship("Chat", back_populates="participants")
    user = relationship("Employee", backref="chat_participations")


class Message(Base):
    """Сообщение в чате"""
    __tablename__ = "message"

    id = Column(Integer, primary_key=True, index=True)
    guid = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    chat_id = Column(Integer, ForeignKey("chat.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(10), default="text", nullable=False)
    reply_to_id = Column(Integer, ForeignKey("message.id", ondelete="SET NULL"), nullable=True)
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("Employee", backref="messages")
    attachments = relationship("MessageAttachment", back_populates="message", lazy="selectin")
    reply_to = relationship("Message", remote_side=[id], backref="replies")


class ReadStatus(Base):
    """Статус прочтения — одна строка на пользователя/чат"""
    __tablename__ = "read_status"

    user_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True)
    chat_id = Column(Integer, ForeignKey("chat.id", ondelete="CASCADE"), primary_key=True)
    last_read_message_id = Column(Integer, ForeignKey("message.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    user = relationship("Employee", backref="read_statuses")
    chat = relationship("Chat", backref="read_statuses")
    last_read_message = relationship("Message")


class MessageAttachment(Base):
    """Вложение к сообщению"""
    __tablename__ = "message_attachment"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("message.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(1000), nullable=False)  # Путь на Яндекс.Диске
    file_type = Column(String(50), nullable=True)       # MIME type
    file_size = Column(Integer, nullable=True)           # Байты
    thumbnail_path = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    message = relationship("Message", back_populates="attachments")
```

**Важно:** Не забыть добавить импорт новых моделей в `database.py`:
```python
from database import (
    get_db, init_db, SessionLocal,
    Employee, Client, Contract, Notification,
    Chat, ChatParticipant, Message, ReadStatus, MessageAttachment,  # <-- добавить
)
```

---

## 3. Alembic миграция

Файл: `server/alembic/versions/l2m3n4o5p6q7_add_chat_tables.py`

Именование следует существующему паттерну (буквенно-цифровой prefix + описательное имя).

```python
"""Добавление таблиц встроенного чата (chat, chat_participant, message, read_status, message_attachment)

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6  # <-- актуальный предыдущий revision, проверить через `alembic heads`
Create Date: 2026-XX-XX
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = 'l2m3n4o5p6q7'
down_revision = 'k1l2m3n4o5p6'  # <-- ПРОВЕРИТЬ через `alembic heads`!
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === chat ===
    op.create_table(
        'chat',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('guid', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'),
                  unique=True, nullable=False),
        sa.Column('chat_type', sa.String(10), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('contract_id', sa.Integer(),
                  sa.ForeignKey('contracts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('FALSE')),
    )

    # === chat_participant ===
    op.create_table(
        'chat_participant',
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('employees.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('chat_id', sa.Integer(),
                  sa.ForeignKey('chat.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role', sa.String(20), nullable=False, server_default='member'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('TRUE')),
    )

    # === message ===
    op.create_table(
        'message',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('guid', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'),
                  unique=True, nullable=False),
        sa.Column('chat_id', sa.Integer(),
                  sa.ForeignKey('chat.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(10), nullable=False, server_default='text'),
        sa.Column('reply_to_id', sa.Integer(),
                  sa.ForeignKey('message.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_edited', sa.Boolean(), server_default=sa.text('FALSE')),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('FALSE')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    # === read_status ===
    op.create_table(
        'read_status',
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('employees.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('chat_id', sa.Integer(),
                  sa.ForeignKey('chat.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('last_read_message_id', sa.Integer(),
                  sa.ForeignKey('message.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    # === message_attachment ===
    op.create_table(
        'message_attachment',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('message_id', sa.Integer(),
                  sa.ForeignKey('message.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('thumbnail_path', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    # === Индексы ===
    op.create_index('idx_message_chat_created', 'message', ['chat_id', sa.text('created_at DESC')])
    op.create_index('idx_chat_participant_user', 'chat_participant', ['user_id'])
    op.create_index('idx_read_status_user_chat', 'read_status', ['user_id', 'chat_id'])
    op.create_index('idx_attachment_message', 'message_attachment', ['message_id'])
    op.create_index('idx_chat_contract', 'chat', ['contract_id'])
    op.create_index('idx_message_chat_id', 'message', ['chat_id', 'id'])


def downgrade() -> None:
    # Удаление в обратном порядке (из-за FK)
    op.drop_table('message_attachment')
    op.drop_table('read_status')
    op.drop_table('message')
    op.drop_table('chat_participant')
    op.drop_table('chat')
```

### Применение миграции

```bash
# Локально (для проверки)
cd server
alembic upgrade head

# Production (Docker)
ssh timeweb "cd /opt/interior_studio && docker exec crm_api alembic upgrade head"
```

---

## 4. WebSocket -- ConnectionManager

Файл: `server/services/chat_connection_manager.py`

```python
"""
ConnectionManager для WebSocket чатов.
Управляет подключениями, комнатами (чатами) и рассылкой сообщений.

Архитектура:
- Один инстанс на uvicorn worker (in-memory)
- При масштабировании до нескольких workers — перейти на Redis PubSub или Centrifugo
- Текущая конфигурация: 1 worker → in-memory достаточно

Паттерн использования:
    manager = ConnectionManager()
    await manager.connect(websocket, user_id)
    await manager.add_to_chat(websocket, user_id, chat_guid)
    await manager.broadcast_to_chat(chat_guid, message_data, exclude_user_id=sender_id)
    await manager.disconnect(websocket, user_id)
"""

import asyncio
import logging
from collections import defaultdict
from typing import Optional, Any
from datetime import datetime

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Менеджер WebSocket соединений.

    Структуры данных:
    - chats: dict[str, set[WebSocket]] — WebSocket'ы в каждом чате (по guid)
    - user_connections: dict[int, set[WebSocket]] — все соединения пользователя
      (один пользователь может быть подключён с нескольких устройств)
    - connection_user: dict[WebSocket, int] — обратный маппинг (ws → user_id)
    """

    def __init__(self):
        # guid чата → множество WebSocket'ов
        self.chats: dict[str, set[WebSocket]] = defaultdict(set)
        # user_id → множество WebSocket'ов (мульти-девайс)
        self.user_connections: dict[int, set[WebSocket]] = defaultdict(set)
        # WebSocket → user_id (обратный маппинг для disconnect)
        self.connection_user: dict[WebSocket, int] = {}
        # user_id → последнее время активности
        self.last_activity: dict[int, datetime] = {}

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        """
        Принять WebSocket соединение и зарегистрировать пользователя.

        Args:
            websocket: WebSocket объект FastAPI
            user_id: ID сотрудника из JWT
        """
        await websocket.accept()
        self.user_connections[user_id].add(websocket)
        self.connection_user[websocket] = user_id
        self.last_activity[user_id] = datetime.utcnow()

        logger.info(
            f"WS подключение: user_id={user_id}, "
            f"всего соединений пользователя: {len(self.user_connections[user_id])}, "
            f"всего пользователей онлайн: {len(self.user_connections)}"
        )

    async def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """
        Отключить WebSocket и удалить из всех чатов.

        Args:
            websocket: WebSocket объект
            user_id: ID пользователя
        """
        # Удалить из всех чатов
        for chat_guid in list(self.chats.keys()):
            self.chats[chat_guid].discard(websocket)
            # Удалить пустые комнаты
            if not self.chats[chat_guid]:
                del self.chats[chat_guid]

        # Удалить соединение пользователя
        self.user_connections[user_id].discard(websocket)
        if not self.user_connections[user_id]:
            del self.user_connections[user_id]
            self.last_activity.pop(user_id, None)

        # Удалить обратный маппинг
        self.connection_user.pop(websocket, None)

        logger.info(
            f"WS отключение: user_id={user_id}, "
            f"всего пользователей онлайн: {len(self.user_connections)}"
        )

    async def add_to_chat(self, websocket: WebSocket, user_id: int, chat_guid: str) -> None:
        """
        Добавить WebSocket в комнату чата.
        Вызывается при подключении — пользователь автоматически
        добавляется во все свои чаты.

        Args:
            websocket: WebSocket объект
            user_id: ID пользователя (для логирования)
            chat_guid: UUID чата
        """
        self.chats[chat_guid].add(websocket)
        logger.debug(f"user_id={user_id} → чат {chat_guid} (участников: {len(self.chats[chat_guid])})")

    async def remove_from_chat(self, websocket: WebSocket, chat_guid: str) -> None:
        """Удалить WebSocket из комнаты чата."""
        self.chats[chat_guid].discard(websocket)
        if not self.chats[chat_guid]:
            del self.chats[chat_guid]

    async def broadcast_to_chat(
        self,
        chat_guid: str,
        data: dict[str, Any],
        exclude_user_id: Optional[int] = None
    ) -> None:
        """
        Отправить сообщение всем участникам чата.

        Args:
            chat_guid: UUID чата
            data: JSON-совместимый словарь для отправки
            exclude_user_id: Не отправлять этому пользователю
                             (обычно — отправитель сообщения)
        """
        if chat_guid not in self.chats:
            return

        disconnected: list[WebSocket] = []

        for ws in self.chats[chat_guid]:
            # Пропустить отправителя, если задан exclude
            if exclude_user_id is not None:
                ws_user = self.connection_user.get(ws)
                if ws_user == exclude_user_id:
                    continue

            try:
                await ws.send_json(data)
            except Exception as e:
                logger.warning(f"Ошибка отправки в WS: {e}")
                disconnected.append(ws)

        # Очистить разорванные соединения
        for ws in disconnected:
            user_id = self.connection_user.get(ws)
            if user_id is not None:
                await self.disconnect(ws, user_id)

    async def send_to_user(self, user_id: int, data: dict[str, Any]) -> None:
        """
        Отправить сообщение конкретному пользователю (все его устройства).
        Используется для персональных уведомлений.

        Args:
            user_id: ID пользователя
            data: JSON-совместимый словарь
        """
        if user_id not in self.user_connections:
            return

        disconnected: list[WebSocket] = []

        for ws in self.user_connections[user_id]:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            await self.disconnect(ws, user_id)

    def is_user_online(self, user_id: int) -> bool:
        """Проверить, подключён ли пользователь."""
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0

    def get_online_users(self) -> list[int]:
        """Список ID пользователей, которые сейчас онлайн."""
        return list(self.user_connections.keys())

    def get_chat_online_count(self, chat_guid: str) -> int:
        """Количество онлайн-участников в чате."""
        return len(self.chats.get(chat_guid, set()))

    def get_stats(self) -> dict:
        """Статистика для мониторинга (endpoint /health или /debug)."""
        return {
            "online_users": len(self.user_connections),
            "total_connections": sum(len(conns) for conns in self.user_connections.values()),
            "active_chats": len(self.chats),
        }


# Глобальный инстанс (один на worker)
chat_manager = ConnectionManager()
```

### Heartbeat (keep-alive)

WebSocket соединения могут быть закрыты прокси/файрволом при отсутствии активности. Для поддержания соединения нужен heartbeat.

```python
# Константы heartbeat
HEARTBEAT_INTERVAL = 30  # секунд
HEARTBEAT_TIMEOUT = 10   # секунд ожидания pong

# В WebSocket endpoint (см. раздел 5) — heartbeat task:
async def heartbeat_task(websocket: WebSocket):
    """Периодическая отправка ping для поддержания соединения."""
    while True:
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await websocket.send_json({"type": "ping", "ts": datetime.utcnow().isoformat()})
        except Exception:
            break
```

---

## 5. WebSocket endpoint (FastAPI)

Файл: `server/routers/chat_ws_router.py`

```python
"""
WebSocket endpoint для встроенного чата.

Протокол обмена сообщениями (JSON):

Клиент → Сервер:
  {"type": "new_message",  "chat_guid": "...", "content": "текст", "client_guid": "uuid"}
  {"type": "typing",       "chat_guid": "..."}
  {"type": "read",         "chat_guid": "...", "message_id": 123}
  {"type": "join_chat",    "chat_guid": "..."}
  {"type": "leave_chat",   "chat_guid": "..."}
  {"type": "pong"}

Сервер → Клиент:
  {"type": "new_message",  "chat_guid": "...", "message": {...}}
  {"type": "typing",       "chat_guid": "...", "user_id": 1, "user_name": "Иван"}
  {"type": "read",         "chat_guid": "...", "user_id": 1, "message_id": 123}
  {"type": "user_online",  "user_id": 1}
  {"type": "user_offline", "user_id": 1}
  {"type": "ping",         "ts": "..."}
  {"type": "error",        "message": "..."}

Аутентификация:
  WebSocket подключение через query parameter:
  wss://crm.festivalcolor.ru/ws/chat?token=eyJhbGci...

  Браузеры НЕ поддерживают кастомные заголовки при WebSocket handshake,
  поэтому JWT передаётся через query string.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database import (
    get_db, Chat, ChatParticipant, Message, ReadStatus, MessageAttachment, Employee
)
from auth import verify_access_token  # нужна функция, принимающая строку токена
from services.chat_connection_manager import chat_manager

logger = logging.getLogger(__name__)

router = APIRouter()

HEARTBEAT_INTERVAL = 30  # секунд


def get_user_from_token(token: str, db: Session) -> Optional[Employee]:
    """
    Валидация JWT из query parameter.

    В отличие от REST (где используется OAuth2PasswordBearer),
    WebSocket получает токен из query string.
    """
    try:
        from jose import jwt, JWTError
        from config import get_settings
        settings = get_settings()

        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if user_id is None or token_type != "access":
            return None

        user = db.query(Employee).filter(Employee.id == int(user_id)).first()
        return user
    except (JWTError, ValueError, Exception) as e:
        logger.warning(f"WS JWT ошибка: {e}")
        return None


async def heartbeat_task(websocket: WebSocket):
    """Периодическая отправка ping для поддержания соединения."""
    while True:
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await websocket.send_json({"type": "ping", "ts": datetime.utcnow().isoformat()})
        except Exception:
            break


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    Главный WebSocket endpoint для чата.

    Подключение:
        ws = new WebSocket("wss://crm.festivalcolor.ru/ws/chat?token=JWT_TOKEN")

    Жизненный цикл:
        1. Клиент подключается с JWT в query string
        2. Сервер валидирует JWT, accept соединение
        3. Сервер подписывает пользователя на все его чаты
        4. Клиент и сервер обмениваются JSON-сообщениями
        5. Heartbeat каждые 30 секунд
        6. При disconnect — очистка из всех комнат
    """
    # --- 1. Аутентификация ---
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Токен не передан")
        return

    # Получаем DB сессию вручную (WebSocket не поддерживает Depends для DB)
    from database import SessionLocal
    db = SessionLocal()

    try:
        user = get_user_from_token(token, db)
        if not user:
            await websocket.close(code=4001, reason="Неверный или истёкший токен")
            return

        user_id = user.id
        user_name = user.full_name

        # --- 2. Подключение ---
        await chat_manager.connect(websocket, user_id)

        # --- 3. Подписка на все чаты пользователя ---
        user_chats = (
            db.query(ChatParticipant)
            .join(Chat)
            .filter(
                ChatParticipant.user_id == user_id,
                ChatParticipant.is_active == True,
                Chat.is_deleted == False,
            )
            .all()
        )

        for cp in user_chats:
            chat = db.query(Chat).filter(Chat.id == cp.chat_id).first()
            if chat:
                await chat_manager.add_to_chat(websocket, user_id, str(chat.guid))

        # Уведомить всех о появлении пользователя онлайн
        for cp in user_chats:
            chat = db.query(Chat).filter(Chat.id == cp.chat_id).first()
            if chat:
                await chat_manager.broadcast_to_chat(
                    str(chat.guid),
                    {"type": "user_online", "user_id": user_id, "user_name": user_name},
                    exclude_user_id=user_id,
                )

        # --- 4. Запуск heartbeat ---
        heartbeat = asyncio.create_task(heartbeat_task(websocket))

        # --- 5. Основной цикл приёма сообщений ---
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")

                if msg_type == "pong":
                    # Ответ на heartbeat — обновляем время активности
                    chat_manager.last_activity[user_id] = datetime.utcnow()

                elif msg_type == "new_message":
                    await handle_new_message(data, user_id, user_name, db)

                elif msg_type == "typing":
                    await handle_typing(data, user_id, user_name)

                elif msg_type == "read":
                    await handle_read(data, user_id, db)

                elif msg_type == "join_chat":
                    chat_guid = data.get("chat_guid")
                    if chat_guid:
                        await chat_manager.add_to_chat(websocket, user_id, chat_guid)

                elif msg_type == "leave_chat":
                    chat_guid = data.get("chat_guid")
                    if chat_guid:
                        await chat_manager.remove_from_chat(websocket, chat_guid)

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Неизвестный тип сообщения: {msg_type}"
                    })

        except WebSocketDisconnect:
            logger.info(f"WS disconnect: user_id={user_id}")

        except Exception as e:
            logger.error(f"WS ошибка: user_id={user_id}, error={e}")

        finally:
            # --- 6. Очистка ---
            heartbeat.cancel()

            # Уведомить об уходе оффлайн
            for cp in user_chats:
                chat = db.query(Chat).filter(Chat.id == cp.chat_id).first()
                if chat:
                    await chat_manager.broadcast_to_chat(
                        str(chat.guid),
                        {"type": "user_offline", "user_id": user_id, "user_name": user_name},
                        exclude_user_id=user_id,
                    )

            await chat_manager.disconnect(websocket, user_id)

    finally:
        db.close()


# =============================================================
# ОБРАБОТЧИКИ ТИПОВ СООБЩЕНИЙ
# =============================================================

async def handle_new_message(data: dict, user_id: int, user_name: str, db: Session):
    """
    Обработка нового сообщения.

    Клиент отправляет:
        {
            "type": "new_message",
            "chat_guid": "uuid-чата",
            "content": "Текст сообщения",
            "client_guid": "uuid-для-идемпотентности",
            "reply_to_guid": "uuid-сообщения-на-которое-отвечаем"  // необязательно
        }

    Сервер:
        1. Проверяет, что пользователь — участник чата
        2. Создаёт запись Message в БД
        3. Рассылает всем участникам чата через WebSocket
    """
    chat_guid = data.get("chat_guid")
    content = data.get("content", "").strip()
    client_guid = data.get("client_guid")  # UUID от клиента для идемпотентности
    reply_to_guid = data.get("reply_to_guid")

    if not chat_guid or not content:
        return

    # Найти чат
    chat = db.query(Chat).filter(Chat.guid == chat_guid, Chat.is_deleted == False).first()
    if not chat:
        return

    # Проверить участие
    participant = (
        db.query(ChatParticipant)
        .filter(
            ChatParticipant.user_id == user_id,
            ChatParticipant.chat_id == chat.id,
            ChatParticipant.is_active == True,
        )
        .first()
    )
    if not participant:
        return

    # Идемпотентность: если сообщение с таким client_guid уже есть — не создавать
    if client_guid:
        existing = db.query(Message).filter(Message.guid == client_guid).first()
        if existing:
            return  # Дубликат — игнорируем

    # Найти reply_to (если есть)
    reply_to_id = None
    if reply_to_guid:
        reply_msg = db.query(Message).filter(Message.guid == reply_to_guid).first()
        if reply_msg:
            reply_to_id = reply_msg.id

    # Создать сообщение
    message = Message(
        guid=client_guid or uuid4(),
        chat_id=chat.id,
        user_id=user_id,
        content=content,
        message_type="text",
        reply_to_id=reply_to_id,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    # Автоматически обновить read_status отправителя
    read_status = (
        db.query(ReadStatus)
        .filter(ReadStatus.user_id == user_id, ReadStatus.chat_id == chat.id)
        .first()
    )
    if read_status:
        read_status.last_read_message_id = message.id
        read_status.updated_at = datetime.utcnow()
    else:
        db.add(ReadStatus(user_id=user_id, chat_id=chat.id, last_read_message_id=message.id))
    db.commit()

    # Формируем ответ
    response = {
        "type": "new_message",
        "chat_guid": str(chat.guid),
        "message": {
            "id": message.id,
            "guid": str(message.guid),
            "user_id": user_id,
            "user_name": user_name,
            "content": message.content,
            "message_type": message.message_type,
            "reply_to_id": reply_to_id,
            "created_at": message.created_at.isoformat(),
            "is_edited": False,
            "attachments": [],
        },
    }

    # Рассылка всем участникам чата (включая отправителя — для подтверждения)
    await chat_manager.broadcast_to_chat(str(chat.guid), response)

    # Отправить push-уведомление оффлайн-пользователям
    await send_offline_push_notifications(chat, message, user_id, user_name, db)


async def handle_typing(data: dict, user_id: int, user_name: str):
    """
    Обработка индикатора набора текста.

    Клиент отправляет: {"type": "typing", "chat_guid": "..."}
    Сервер рассылает:  {"type": "typing", "chat_guid": "...", "user_id": 1, "user_name": "Иван"}

    Троттлинг на клиенте: отправлять не чаще 1 раза в 3 секунды.
    """
    chat_guid = data.get("chat_guid")
    if not chat_guid:
        return

    await chat_manager.broadcast_to_chat(
        chat_guid,
        {
            "type": "typing",
            "chat_guid": chat_guid,
            "user_id": user_id,
            "user_name": user_name,
        },
        exclude_user_id=user_id,
    )


async def handle_read(data: dict, user_id: int, db: Session):
    """
    Обработка отметки прочтения.

    Клиент отправляет: {"type": "read", "chat_guid": "...", "message_id": 123}
    Сервер:
        1. Обновляет read_status в БД
        2. Рассылает уведомление другим участникам чата
    """
    chat_guid = data.get("chat_guid")
    message_id = data.get("message_id")

    if not chat_guid or not message_id:
        return

    chat = db.query(Chat).filter(Chat.guid == chat_guid).first()
    if not chat:
        return

    # Upsert read_status
    read_status = (
        db.query(ReadStatus)
        .filter(ReadStatus.user_id == user_id, ReadStatus.chat_id == chat.id)
        .first()
    )

    if read_status:
        # Обновляем только если новый message_id больше текущего
        if read_status.last_read_message_id is None or message_id > read_status.last_read_message_id:
            read_status.last_read_message_id = message_id
            read_status.updated_at = datetime.utcnow()
    else:
        db.add(ReadStatus(user_id=user_id, chat_id=chat.id, last_read_message_id=message_id))

    db.commit()

    # Уведомить других (для галочек прочтения)
    await chat_manager.broadcast_to_chat(
        chat_guid,
        {
            "type": "read",
            "chat_guid": chat_guid,
            "user_id": user_id,
            "message_id": message_id,
        },
        exclude_user_id=user_id,
    )


async def send_offline_push_notifications(
    chat: Chat, message: Message, sender_id: int, sender_name: str, db: Session
):
    """
    Отправить push-уведомления пользователям, которые НЕ онлайн.

    Для каждого оффлайн-участника:
    - Если у него есть telegram_user_id → отправить через Telegram Bot
    - Иначе → Web Push (если подписан на PWA push)
    """
    participants = (
        db.query(ChatParticipant)
        .filter(
            ChatParticipant.chat_id == chat.id,
            ChatParticipant.is_active == True,
            ChatParticipant.user_id != sender_id,
        )
        .all()
    )

    for p in participants:
        if not chat_manager.is_user_online(p.user_id):
            # TODO: реализовать push через Telegram Bot / Web Push VAPID
            # Шаблон уведомления:
            # f"{sender_name}: {message.content[:100]}"
            logger.debug(f"Push для user_id={p.user_id}: {sender_name}: {message.content[:50]}...")
```

### Регистрация роутера в main.py

```python
# В server/main.py, после остальных include_router:
from routers.chat_ws_router import router as chat_ws_router
app.include_router(chat_ws_router, tags=["chat-websocket"])
```

---

## 6. REST API endpoints

Файл: `server/routers/chat_rest_router.py`

WebSocket используется для реального времени, а REST — для:
- Создание/настройка чатов
- Загрузка истории сообщений (с пагинацией)
- Загрузка файлов
- Управление участниками
- Отметка прочтения (альтернатива WS для оффлайн-сценариев)

### Полный список endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/v1/chat` | Создать чат |
| `GET` | `/api/v1/chat` | Список чатов пользователя |
| `GET` | `/api/v1/chat/{guid}` | Детали чата |
| `GET` | `/api/v1/chat/{guid}/messages` | История сообщений (cursor-based) |
| `POST` | `/api/v1/chat/{guid}/upload` | Загрузить файл в чат |
| `PUT` | `/api/v1/chat/{guid}/read` | Отметить прочтение |
| `GET` | `/api/v1/chat/{guid}/participants` | Участники чата |
| `POST` | `/api/v1/chat/{guid}/participants` | Добавить участника |
| `DELETE` | `/api/v1/chat/{guid}/participants/{user_id}` | Удалить участника |
| `PUT` | `/api/v1/chat/{guid}/messages/{msg_guid}` | Редактировать сообщение |
| `DELETE` | `/api/v1/chat/{guid}/messages/{msg_guid}` | Удалить сообщение |

### Код роутера

```python
"""
REST API endpoints для чата.

Используются для:
- CRUD операций (создание/удаление чатов, управление участниками)
- Загрузки истории сообщений (cursor-based pagination)
- Загрузки файлов (REST upload → WS notification)
"""

import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from database import (
    get_db, Chat, ChatParticipant, Message, ReadStatus, MessageAttachment, Employee
)
from auth import get_current_user
from chat_schemas import (
    ChatCreate, ChatResponse, ChatListResponse,
    MessageResponse, MessageListResponse,
    ParticipantResponse, ParticipantCreate,
    ReadMarkRequest,
)
from services.chat_connection_manager import chat_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# =============================================================
# ЧАТЫ
# =============================================================

@router.post("", response_model=ChatResponse, status_code=201)
async def create_chat(
    data: ChatCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Создать новый чат.

    Тело запроса:
        {
            "chat_type": "direct" | "group" | "project",
            "name": "Название чата",          // обязательно для group/project
            "contract_id": 123,               // обязательно для project
            "participant_ids": [1, 2, 3]      // ID сотрудников
        }

    Для direct-чата: ровно 2 участника (текущий + один другой).
    Проверяется уникальность direct-чата (нельзя создать два 1:1 с тем же человеком).
    """
    # Валидация типа чата
    if data.chat_type == "direct":
        if len(data.participant_ids) != 1:
            raise HTTPException(400, "Для direct-чата нужен ровно 1 собеседник")

        other_id = data.participant_ids[0]

        # Проверить, нет ли уже direct-чата с этим пользователем
        existing = (
            db.query(Chat)
            .join(ChatParticipant)
            .filter(
                Chat.chat_type == "direct",
                Chat.is_deleted == False,
                ChatParticipant.user_id.in_([current_user.id, other_id]),
            )
            .group_by(Chat.id)
            .having(func.count(ChatParticipant.user_id) == 2)
            .first()
        )
        if existing:
            raise HTTPException(409, f"Direct-чат уже существует: {existing.guid}")

    elif data.chat_type == "project":
        if not data.contract_id:
            raise HTTPException(400, "Для project-чата нужен contract_id")

    # Создать чат
    chat = Chat(
        guid=uuid4(),
        chat_type=data.chat_type,
        name=data.name,
        contract_id=data.contract_id,
    )
    db.add(chat)
    db.flush()

    # Добавить создателя как admin
    db.add(ChatParticipant(user_id=current_user.id, chat_id=chat.id, role="admin"))

    # Добавить остальных участников
    for uid in data.participant_ids:
        if uid != current_user.id:
            # Проверить, что сотрудник существует
            emp = db.query(Employee).filter(Employee.id == uid).first()
            if not emp:
                raise HTTPException(404, f"Сотрудник {uid} не найден")
            db.add(ChatParticipant(user_id=uid, chat_id=chat.id, role="member"))

    # Инициализировать read_status для всех
    all_participant_ids = [current_user.id] + [uid for uid in data.participant_ids if uid != current_user.id]
    for uid in all_participant_ids:
        db.add(ReadStatus(user_id=uid, chat_id=chat.id, last_read_message_id=None))

    # Системное сообщение
    system_msg = Message(
        guid=uuid4(),
        chat_id=chat.id,
        user_id=current_user.id,
        content="Чат создан",
        message_type="system",
    )
    db.add(system_msg)

    db.commit()
    db.refresh(chat)

    return _chat_to_response(chat, current_user.id, db)


@router.get("", response_model=List[ChatListResponse])
async def list_chats(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Список чатов текущего пользователя.

    Возвращает чаты с:
    - Последним сообщением (для превью)
    - Количеством непрочитанных
    - Списком участников

    Сортировка: по дате последнего сообщения (новые сверху).
    """
    # Все чаты пользователя
    user_chats = (
        db.query(Chat)
        .join(ChatParticipant)
        .filter(
            ChatParticipant.user_id == current_user.id,
            ChatParticipant.is_active == True,
            Chat.is_deleted == False,
        )
        .all()
    )

    result = []
    for chat in user_chats:
        result.append(_chat_to_response(chat, current_user.id, db))

    # Сортировка по дате последнего сообщения
    result.sort(key=lambda c: c.last_message_at or datetime.min, reverse=True)

    return result


@router.get("/{guid}", response_model=ChatResponse)
async def get_chat(
    guid: UUID,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Детали конкретного чата."""
    chat = db.query(Chat).filter(Chat.guid == guid, Chat.is_deleted == False).first()
    if not chat:
        raise HTTPException(404, "Чат не найден")

    # Проверить участие
    _check_participant(current_user.id, chat.id, db)

    return _chat_to_response(chat, current_user.id, db)


# =============================================================
# СООБЩЕНИЯ (cursor-based pagination)
# =============================================================

@router.get("/{guid}/messages", response_model=MessageListResponse)
async def get_messages(
    guid: UUID,
    before_id: Optional[int] = Query(None, description="ID сообщения, ДО которого загружать (для подгрузки)"),
    limit: int = Query(50, ge=1, le=100, description="Количество сообщений"),
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    История сообщений чата с cursor-based пагинацией.

    Пагинация:
    - Первый запрос: GET /api/v1/chat/{guid}/messages?limit=50
      → Возвращает 50 последних сообщений
    - Подгрузка: GET /api/v1/chat/{guid}/messages?before_id=100&limit=50
      → Возвращает 50 сообщений ДО message.id=100

    Cursor-based пагинация (а не offset-based), потому что:
    - Не ломается при добавлении новых сообщений
    - Работает стабильно при любом количестве сообщений
    - Использует индекс idx_message_chat_created
    """
    chat = db.query(Chat).filter(Chat.guid == guid, Chat.is_deleted == False).first()
    if not chat:
        raise HTTPException(404, "Чат не найден")

    _check_participant(current_user.id, chat.id, db)

    # Построение запроса
    query = (
        db.query(Message)
        .filter(
            Message.chat_id == chat.id,
            Message.is_deleted == False,
        )
    )

    if before_id:
        query = query.filter(Message.id < before_id)

    messages = (
        query
        .order_by(desc(Message.created_at))
        .limit(limit + 1)  # +1 для определения has_more
        .all()
    )

    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    # Формируем ответ (в хронологическом порядке)
    messages.reverse()

    return MessageListResponse(
        messages=[_message_to_response(m, db) for m in messages],
        has_more=has_more,
    )


@router.put("/{guid}/messages/{msg_guid}")
async def edit_message(
    guid: UUID,
    msg_guid: UUID,
    content: str,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Редактирование своего сообщения."""
    chat = db.query(Chat).filter(Chat.guid == guid).first()
    if not chat:
        raise HTTPException(404, "Чат не найден")

    message = db.query(Message).filter(
        Message.guid == msg_guid,
        Message.chat_id == chat.id,
    ).first()
    if not message:
        raise HTTPException(404, "Сообщение не найдено")

    if message.user_id != current_user.id:
        raise HTTPException(403, "Можно редактировать только свои сообщения")

    message.content = content.strip()
    message.is_edited = True
    db.commit()

    # Уведомить участников чата через WebSocket
    await chat_manager.broadcast_to_chat(
        str(chat.guid),
        {
            "type": "message_edited",
            "chat_guid": str(chat.guid),
            "message": _message_to_response(message, db).__dict__,
        },
    )

    return {"ok": True}


@router.delete("/{guid}/messages/{msg_guid}")
async def delete_message(
    guid: UUID,
    msg_guid: UUID,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Мягкое удаление сообщения (контент заменяется)."""
    chat = db.query(Chat).filter(Chat.guid == guid).first()
    if not chat:
        raise HTTPException(404, "Чат не найден")

    message = db.query(Message).filter(
        Message.guid == msg_guid,
        Message.chat_id == chat.id,
    ).first()
    if not message:
        raise HTTPException(404, "Сообщение не найдено")

    if message.user_id != current_user.id:
        raise HTTPException(403, "Можно удалять только свои сообщения")

    message.is_deleted = True
    message.content = "Сообщение удалено"
    db.commit()

    await chat_manager.broadcast_to_chat(
        str(chat.guid),
        {
            "type": "message_deleted",
            "chat_guid": str(chat.guid),
            "message_guid": str(msg_guid),
        },
    )

    return {"ok": True}


# =============================================================
# ОТМЕТКА ПРОЧТЕНИЯ (REST-альтернатива WS)
# =============================================================

@router.put("/{guid}/read")
async def mark_as_read(
    guid: UUID,
    data: ReadMarkRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Отметить сообщения как прочитанные (REST-альтернатива WebSocket "read").
    Используется, когда WebSocket недоступен (оффлайн-режим).
    """
    chat = db.query(Chat).filter(Chat.guid == guid).first()
    if not chat:
        raise HTTPException(404, "Чат не найден")

    _check_participant(current_user.id, chat.id, db)

    read_status = (
        db.query(ReadStatus)
        .filter(ReadStatus.user_id == current_user.id, ReadStatus.chat_id == chat.id)
        .first()
    )

    if read_status:
        if read_status.last_read_message_id is None or data.message_id > read_status.last_read_message_id:
            read_status.last_read_message_id = data.message_id
            read_status.updated_at = datetime.utcnow()
    else:
        db.add(ReadStatus(
            user_id=current_user.id,
            chat_id=chat.id,
            last_read_message_id=data.message_id,
        ))

    db.commit()
    return {"ok": True}


# =============================================================
# УЧАСТНИКИ
# =============================================================

@router.get("/{guid}/participants", response_model=List[ParticipantResponse])
async def list_participants(
    guid: UUID,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Список участников чата."""
    chat = db.query(Chat).filter(Chat.guid == guid).first()
    if not chat:
        raise HTTPException(404, "Чат не найден")

    _check_participant(current_user.id, chat.id, db)

    participants = (
        db.query(ChatParticipant)
        .filter(ChatParticipant.chat_id == chat.id, ChatParticipant.is_active == True)
        .all()
    )

    result = []
    for p in participants:
        emp = db.query(Employee).filter(Employee.id == p.user_id).first()
        result.append(ParticipantResponse(
            user_id=p.user_id,
            full_name=emp.full_name if emp else "Неизвестный",
            role=p.role,
            is_online=chat_manager.is_user_online(p.user_id),
            joined_at=p.joined_at,
        ))

    return result


@router.post("/{guid}/participants", status_code=201)
async def add_participant(
    guid: UUID,
    data: ParticipantCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Добавить участника в чат.
    Только admin чата может добавлять.
    """
    chat = db.query(Chat).filter(Chat.guid == guid).first()
    if not chat:
        raise HTTPException(404, "Чат не найден")

    # Проверить, что текущий пользователь — admin
    admin = (
        db.query(ChatParticipant)
        .filter(
            ChatParticipant.user_id == current_user.id,
            ChatParticipant.chat_id == chat.id,
            ChatParticipant.role == "admin",
            ChatParticipant.is_active == True,
        )
        .first()
    )
    if not admin:
        raise HTTPException(403, "Только администратор чата может добавлять участников")

    # Проверить, что сотрудник существует
    emp = db.query(Employee).filter(Employee.id == data.user_id).first()
    if not emp:
        raise HTTPException(404, f"Сотрудник {data.user_id} не найден")

    # Проверить, не в чате ли уже
    existing = (
        db.query(ChatParticipant)
        .filter(ChatParticipant.user_id == data.user_id, ChatParticipant.chat_id == chat.id)
        .first()
    )
    if existing:
        if existing.is_active:
            raise HTTPException(409, "Пользователь уже в чате")
        # Реактивировать
        existing.is_active = True
        existing.role = data.role or "member"
    else:
        db.add(ChatParticipant(
            user_id=data.user_id,
            chat_id=chat.id,
            role=data.role or "member",
        ))
        db.add(ReadStatus(user_id=data.user_id, chat_id=chat.id))

    # Системное сообщение
    db.add(Message(
        guid=uuid4(),
        chat_id=chat.id,
        user_id=current_user.id,
        content=f"{emp.full_name} добавлен(а) в чат",
        message_type="system",
    ))

    db.commit()

    # Уведомить через WS
    await chat_manager.broadcast_to_chat(
        str(chat.guid),
        {
            "type": "participant_added",
            "chat_guid": str(chat.guid),
            "user_id": data.user_id,
            "user_name": emp.full_name,
        },
    )

    return {"ok": True}


@router.delete("/{guid}/participants/{user_id}")
async def remove_participant(
    guid: UUID,
    user_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Удалить участника из чата (мягкое удаление)."""
    chat = db.query(Chat).filter(Chat.guid == guid).first()
    if not chat:
        raise HTTPException(404, "Чат не найден")

    # Может удалять: admin или сам пользователь (покинуть чат)
    if user_id != current_user.id:
        admin = (
            db.query(ChatParticipant)
            .filter(
                ChatParticipant.user_id == current_user.id,
                ChatParticipant.chat_id == chat.id,
                ChatParticipant.role == "admin",
            )
            .first()
        )
        if not admin:
            raise HTTPException(403, "Только admin может удалять других участников")

    participant = (
        db.query(ChatParticipant)
        .filter(
            ChatParticipant.user_id == user_id,
            ChatParticipant.chat_id == chat.id,
            ChatParticipant.is_active == True,
        )
        .first()
    )
    if not participant:
        raise HTTPException(404, "Участник не найден")

    participant.is_active = False
    db.commit()

    return {"ok": True}


# =============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================

def _check_participant(user_id: int, chat_id: int, db: Session):
    """Проверить, что пользователь — активный участник чата."""
    p = (
        db.query(ChatParticipant)
        .filter(
            ChatParticipant.user_id == user_id,
            ChatParticipant.chat_id == chat_id,
            ChatParticipant.is_active == True,
        )
        .first()
    )
    if not p:
        raise HTTPException(403, "Вы не участник этого чата")


def _chat_to_response(chat: Chat, current_user_id: int, db: Session) -> ChatListResponse:
    """Конвертировать Chat ORM → ChatListResponse."""
    # Последнее сообщение
    last_msg = (
        db.query(Message)
        .filter(Message.chat_id == chat.id, Message.is_deleted == False)
        .order_by(desc(Message.created_at))
        .first()
    )

    # Непрочитанные
    read_status = (
        db.query(ReadStatus)
        .filter(ReadStatus.user_id == current_user_id, ReadStatus.chat_id == chat.id)
        .first()
    )

    last_read_id = read_status.last_read_message_id if read_status else 0
    unread_count = (
        db.query(func.count(Message.id))
        .filter(
            Message.chat_id == chat.id,
            Message.id > (last_read_id or 0),
            Message.is_deleted == False,
            Message.user_id != current_user_id,  # Не считать свои сообщения
        )
        .scalar()
    ) or 0

    # Участники (для отображения имени в direct-чате)
    participants = (
        db.query(ChatParticipant)
        .filter(ChatParticipant.chat_id == chat.id, ChatParticipant.is_active == True)
        .all()
    )

    participant_names = []
    for p in participants:
        emp = db.query(Employee).filter(Employee.id == p.user_id).first()
        if emp:
            participant_names.append({"user_id": emp.id, "full_name": emp.full_name})

    # Имя чата для direct — имя собеседника
    display_name = chat.name
    if chat.chat_type == "direct" and not display_name:
        other = [p for p in participant_names if p["user_id"] != current_user_id]
        display_name = other[0]["full_name"] if other else "Личный чат"

    return ChatListResponse(
        guid=str(chat.guid),
        chat_type=chat.chat_type,
        name=display_name,
        contract_id=chat.contract_id,
        unread_count=unread_count,
        last_message=last_msg.content[:100] if last_msg else None,
        last_message_at=last_msg.created_at if last_msg else None,
        last_message_user=last_msg.user_id if last_msg else None,
        participants=participant_names,
        created_at=chat.created_at,
    )


def _message_to_response(msg: Message, db: Session) -> MessageResponse:
    """Конвертировать Message ORM → MessageResponse."""
    sender = db.query(Employee).filter(Employee.id == msg.user_id).first()
    attachments = (
        db.query(MessageAttachment)
        .filter(MessageAttachment.message_id == msg.id)
        .all()
    )

    return MessageResponse(
        id=msg.id,
        guid=str(msg.guid),
        user_id=msg.user_id,
        user_name=sender.full_name if sender else "Неизвестный",
        content=msg.content,
        message_type=msg.message_type,
        reply_to_id=msg.reply_to_id,
        is_edited=msg.is_edited,
        created_at=msg.created_at,
        attachments=[
            {
                "id": a.id,
                "file_name": a.file_name,
                "file_path": a.file_path,
                "file_type": a.file_type,
                "file_size": a.file_size,
                "thumbnail_path": a.thumbnail_path,
            }
            for a in attachments
        ],
    )
```

### Регистрация REST роутера в main.py

```python
# В server/main.py:
from routers.chat_rest_router import router as chat_rest_router
app.include_router(chat_rest_router)
```

---

## 7. Pydantic-схемы

Файл: `server/chat_schemas.py`

```python
"""
Pydantic-схемы для чата.
Аналог messenger_schemas.py, но для встроенного чата.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# =========================
# СОЗДАНИЕ ЧАТА
# =========================

class ChatCreate(BaseModel):
    """Создание чата."""
    chat_type: str = Field(..., pattern="^(direct|group|project)$")
    name: Optional[str] = None
    contract_id: Optional[int] = None
    participant_ids: List[int] = Field(default_factory=list, description="ID сотрудников")


# =========================
# ОТВЕТЫ
# =========================

class ChatResponse(BaseModel):
    """Базовый ответ чата."""
    guid: str
    chat_type: str
    name: Optional[str] = None
    contract_id: Optional[int] = None
    created_at: datetime
    participants: List[dict] = []

    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    """Чат в списке (с превью и непрочитанными)."""
    guid: str
    chat_type: str
    name: Optional[str] = None
    contract_id: Optional[int] = None
    unread_count: int = 0
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_message_user: Optional[int] = None
    participants: List[dict] = []
    created_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Сообщение."""
    id: int
    guid: str
    user_id: int
    user_name: str
    content: str
    message_type: str = "text"
    reply_to_id: Optional[int] = None
    is_edited: bool = False
    created_at: datetime
    attachments: List[dict] = []

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Список сообщений с пагинацией."""
    messages: List[MessageResponse]
    has_more: bool = False


class ParticipantResponse(BaseModel):
    """Участник чата."""
    user_id: int
    full_name: str
    role: str = "member"
    is_online: bool = False
    joined_at: datetime

    class Config:
        from_attributes = True


class ParticipantCreate(BaseModel):
    """Добавление участника."""
    user_id: int
    role: Optional[str] = "member"


class ReadMarkRequest(BaseModel):
    """Отметка прочтения."""
    message_id: int


# =========================
# WEBSOCKET ТИПЫ СООБЩЕНИЙ (для документации)
# =========================

class WsNewMessage(BaseModel):
    """Клиент → Сервер: новое сообщение."""
    type: str = "new_message"
    chat_guid: str
    content: str
    client_guid: Optional[str] = None  # UUID для идемпотентности
    reply_to_guid: Optional[str] = None

class WsTyping(BaseModel):
    """Клиент → Сервер: набирает текст."""
    type: str = "typing"
    chat_guid: str

class WsRead(BaseModel):
    """Клиент → Сервер: прочитано."""
    type: str = "read"
    chat_guid: str
    message_id: int

class WsPong(BaseModel):
    """Клиент → Сервер: ответ на heartbeat."""
    type: str = "pong"
```

---

## 8. Обработка файлов в чате

### Паттерн: REST upload + WebSocket notification

Файлы загружаются через HTTP POST (не через WebSocket), потому что:
1. WebSocket не поддерживает multipart/form-data
2. HTTP лучше подходит для больших файлов (progress bar, retry)
3. Яндекс.Диск интеграция уже работает через HTTP

### Endpoint загрузки файлов

Добавить в `server/routers/chat_rest_router.py`:

```python
import io
from PIL import Image  # Pillow — уже в requirements (для thumbnails)


@router.post("/{guid}/upload", status_code=201)
async def upload_file_to_chat(
    guid: UUID,
    file: UploadFile = File(...),
    content: Optional[str] = "",
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Загрузить файл в чат.

    Поток:
    1. Файл загружается через HTTP POST (multipart/form-data)
    2. Сохраняется на Яндекс.Диск в disk:/CRM/Chat/{chat_guid}/{filename}
    3. Для изображений генерируется thumbnail (200x200)
    4. Создаётся Message (type='file') + MessageAttachment
    5. Все участники получают WebSocket уведомление

    Поддерживаемые типы:
    - Изображения: jpg, jpeg, png, gif, webp
    - Документы: pdf, doc, docx, xls, xlsx
    - Архивы: zip, rar
    - Максимальный размер: 50 MB (из config.py)
    """
    chat = db.query(Chat).filter(Chat.guid == guid, Chat.is_deleted == False).first()
    if not chat:
        raise HTTPException(404, "Чат не найден")

    _check_participant(current_user.id, chat.id, db)

    # Проверить размер файла
    from config import get_settings
    settings = get_settings()
    file_bytes = await file.read()
    if len(file_bytes) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(413, f"Файл слишком большой. Максимум: {settings.max_file_size_mb} MB")

    # Определить MIME type
    file_type = file.content_type or "application/octet-stream"
    file_name = file.filename or "file"
    file_size = len(file_bytes)

    # Загрузить на Яндекс.Диск
    from yandex_disk_service import get_yandex_service
    yd = get_yandex_service()

    yandex_path = f"disk:/CRM/Chat/{guid}/{file_name}"
    try:
        # Создать папку (если не существует)
        yd.create_folder(f"disk:/CRM/Chat/{guid}")
    except Exception:
        pass  # Папка уже существует

    upload_result = yd.upload_file(file_bytes, yandex_path)
    if not upload_result:
        raise HTTPException(500, "Ошибка загрузки на Яндекс.Диск")

    # Thumbnail для изображений
    thumbnail_path = None
    if file_type.startswith("image/"):
        try:
            img = Image.open(io.BytesIO(file_bytes))
            img.thumbnail((200, 200))
            thumb_bytes = io.BytesIO()
            img.save(thumb_bytes, format="JPEG", quality=80)
            thumb_bytes.seek(0)

            thumb_name = f"thumb_{file_name.rsplit('.', 1)[0]}.jpg"
            thumb_yandex_path = f"disk:/CRM/Chat/{guid}/thumbs/{thumb_name}"

            try:
                yd.create_folder(f"disk:/CRM/Chat/{guid}/thumbs")
            except Exception:
                pass

            yd.upload_file(thumb_bytes.read(), thumb_yandex_path)
            thumbnail_path = thumb_yandex_path
        except Exception as e:
            logger.warning(f"Ошибка создания thumbnail: {e}")

    # Создать сообщение
    message = Message(
        guid=uuid4(),
        chat_id=chat.id,
        user_id=current_user.id,
        content=content or file_name,
        message_type="file",
    )
    db.add(message)
    db.flush()

    # Создать вложение
    attachment = MessageAttachment(
        message_id=message.id,
        file_name=file_name,
        file_path=yandex_path,
        file_type=file_type,
        file_size=file_size,
        thumbnail_path=thumbnail_path,
    )
    db.add(attachment)
    db.commit()
    db.refresh(message)

    # WebSocket уведомление
    sender = db.query(Employee).filter(Employee.id == current_user.id).first()
    await chat_manager.broadcast_to_chat(
        str(chat.guid),
        {
            "type": "new_message",
            "chat_guid": str(chat.guid),
            "message": {
                "id": message.id,
                "guid": str(message.guid),
                "user_id": current_user.id,
                "user_name": sender.full_name if sender else "Неизвестный",
                "content": message.content,
                "message_type": "file",
                "created_at": message.created_at.isoformat(),
                "attachments": [{
                    "id": attachment.id,
                    "file_name": file_name,
                    "file_path": yandex_path,
                    "file_type": file_type,
                    "file_size": file_size,
                    "thumbnail_path": thumbnail_path,
                }],
            },
        },
    )

    return {
        "ok": True,
        "message_id": message.id,
        "attachment_id": attachment.id,
    }
```

### Скачивание файлов

Для скачивания используется существующий endpoint Яндекс.Диска. Клиент получает `file_path` из сообщения и запрашивает ссылку:

```
GET /api/v1/files/public-link?path=disk:/CRM/Chat/{guid}/photo.jpg
```

---

## 9. Push-уведомления

### Три канала уведомлений

| Канал | Когда | Для кого |
|-------|-------|----------|
| **WebSocket** | Пользователь онлайн | Мгновенно, все устройства |
| **Web Push VAPID** | PWA установлен, пользователь оффлайн | Смартфоны/планшеты |
| **Telegram Bot** | Desktop клиент, пользователь оффлайн | Уже интегрирован |

### Web Push VAPID (для PWA)

Зависимость: `pywebpush` (добавить в requirements.txt).

```bash
pip install pywebpush
```

#### Генерация VAPID ключей (один раз)

```python
from pywebpush import webpush
from py_vapid import Vapid

vapid = Vapid()
vapid.generate_keys()
vapid.save_key("vapid_private.pem")
vapid.save_public_key("vapid_public.pem")

# Получить applicationServerKey для фронтенда
print(vapid.public_key)
```

#### Серверный код отправки

```python
# server/services/push_service.py
"""
Web Push уведомления для PWA.
"""

from pywebpush import webpush, WebPushException
from config import get_settings
import json
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

# VAPID ключи (из переменных окружения)
VAPID_PRIVATE_KEY = settings.vapid_private_key  # добавить в config.py
VAPID_CLAIMS = {
    "sub": "mailto:admin@festivalcolor.ru"
}


def send_web_push(subscription_info: dict, title: str, body: str, url: str = "/chat"):
    """
    Отправить Web Push уведомление.

    Args:
        subscription_info: JSON подписки браузера
            {"endpoint": "https://...", "keys": {"p256dh": "...", "auth": "..."}}
        title: Заголовок уведомления
        body: Текст уведомления
        url: URL для перехода при клике
    """
    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
        "icon": "/icons/icon-192.png",
        "badge": "/icons/badge-72.png",
    })

    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS,
        )
        logger.info(f"Web Push отправлен: {title}")
    except WebPushException as e:
        logger.error(f"Web Push ошибка: {e}")
        if e.response and e.response.status_code == 410:
            # Подписка недействительна — удалить из БД
            logger.info("Подписка 410 Gone — нужно удалить из БД")
            return "expired"
    except Exception as e:
        logger.error(f"Web Push неожиданная ошибка: {e}")

    return "sent"
```

#### PWA Service Worker (получение push)

```javascript
// mobile/src-pwa/custom-service-worker.js

self.addEventListener('push', function (event) {
  const data = event.data ? event.data.json() : {}

  const options = {
    body: data.body || 'Новое сообщение',
    icon: data.icon || '/icons/icon-192.png',
    badge: data.badge || '/icons/badge-72.png',
    data: { url: data.url || '/chat' },
    vibrate: [200, 100, 200],
    tag: 'chat-notification',     // Группировка (одно уведомление на чат)
    renotify: true,                // Повторная вибрация при обновлении
  }

  event.waitUntil(
    self.registration.showNotification(data.title || 'Interior Studio', options)
  )
})

// Обработка клика по уведомлению
self.addEventListener('notificationclick', function (event) {
  event.notification.close()

  const url = event.notification.data?.url || '/chat'

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (clientList) {
      // Если приложение уже открыто — переключиться на него
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(url)
          return client.focus()
        }
      }
      // Иначе — открыть новое окно
      return clients.openWindow(url)
    })
  )
})
```

### ntfy.sh (лёгкая альтернатива)

Если Web Push VAPID слишком сложен для первой версии, можно использовать ntfy.sh:

```python
# Отправка через HTTP POST (0 зависимостей)
import requests

def send_ntfy(topic: str, title: str, message: str):
    """Отправить push через ntfy.sh (бесплатно, без регистрации)."""
    requests.post(
        f"https://ntfy.sh/{topic}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": "default",
            "Tags": "speech_balloon",
        },
    )

# Каждый пользователь подписывается на свой topic:
# ntfy.sh/interior-studio-user-{user_id}
```

---

## 10. PyQt5 Desktop клиент

### QWebSocket класс

Файл: `utils/chat_websocket.py`

```python
"""
WebSocket клиент для чата в PyQt5 Desktop приложении.

Особенности:
- Автоматическое переподключение с exponential backoff
- Heartbeat/pong ответы
- Потокобезопасная работа через Qt Signals
- Интеграция с DataAccess для JWT токена
"""

import json
import logging
from typing import Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QUrl
from PyQt5.QtWebSockets import QWebSocket

logger = logging.getLogger(__name__)


class ChatWebSocket(QObject):
    """
    WebSocket клиент для чата.

    Сигналы:
        message_received(dict) — новое сообщение
        typing_received(dict) — индикатор набора
        read_received(dict) — отметка прочтения
        user_online(dict) — пользователь подключился
        user_offline(dict) — пользователь отключился
        connected() — соединение установлено
        disconnected() — соединение потеряно
        error_occurred(str) — ошибка
    """

    # Сигналы (потокобезопасные, можно connect из UI-потока)
    message_received = pyqtSignal(dict)
    typing_received = pyqtSignal(dict)
    read_received = pyqtSignal(dict)
    user_online = pyqtSignal(dict)
    user_offline = pyqtSignal(dict)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error_occurred = pyqtSignal(str)

    # Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (max)
    RECONNECT_BASE = 1000       # мс
    RECONNECT_MAX = 30000       # мс
    TYPING_THROTTLE = 3000      # мс (не чаще 1 раза в 3 секунды)

    def __init__(self, base_url: str, token: str, parent=None):
        """
        Args:
            base_url: Базовый URL API (напр. "https://crm.festivalcolor.ru")
            token: JWT access token
            parent: QObject-родитель
        """
        super().__init__(parent)

        self._base_url = base_url
        self._token = token
        self._socket = QWebSocket()
        self._reconnect_delay = self.RECONNECT_BASE
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._do_connect)
        self._is_intentional_close = False

        # Троттлинг typing
        self._typing_timer = QTimer(self)
        self._typing_timer.setSingleShot(True)
        self._can_send_typing = True

        # Подключение сигналов QWebSocket
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.textMessageReceived.connect(self._on_message)
        self._socket.error.connect(self._on_error)

    def connect_to_server(self):
        """Начать подключение к WebSocket серверу."""
        self._is_intentional_close = False
        self._do_connect()

    def _do_connect(self):
        """Выполнить подключение."""
        ws_url = self._base_url.replace("https://", "wss://").replace("http://", "ws://")
        url = f"{ws_url}/ws/chat?token={self._token}"
        logger.info(f"WS подключение к {ws_url}/ws/chat")
        self._socket.open(QUrl(url))

    def disconnect_from_server(self):
        """Закрыть соединение (без автопереподключения)."""
        self._is_intentional_close = True
        self._reconnect_timer.stop()
        self._socket.close()

    def send_message(self, chat_guid: str, content: str, client_guid: str = None,
                     reply_to_guid: str = None):
        """Отправить текстовое сообщение."""
        data = {
            "type": "new_message",
            "chat_guid": chat_guid,
            "content": content,
        }
        if client_guid:
            data["client_guid"] = client_guid
        if reply_to_guid:
            data["reply_to_guid"] = reply_to_guid

        self._send_json(data)

    def send_typing(self, chat_guid: str):
        """Отправить индикатор набора (с троттлингом)."""
        if not self._can_send_typing:
            return
        self._can_send_typing = False
        self._typing_timer.start(self.TYPING_THROTTLE)
        self._typing_timer.timeout.connect(lambda: setattr(self, '_can_send_typing', True))

        self._send_json({"type": "typing", "chat_guid": chat_guid})

    def send_read(self, chat_guid: str, message_id: int):
        """Отправить отметку прочтения."""
        self._send_json({
            "type": "read",
            "chat_guid": chat_guid,
            "message_id": message_id,
        })

    def update_token(self, new_token: str):
        """Обновить JWT токен (после refresh)."""
        self._token = new_token
        # Переподключиться с новым токеном
        if self._socket.isValid():
            self._socket.close()
            # _on_disconnected вызовет переподключение

    def _send_json(self, data: dict):
        """Отправить JSON через WebSocket."""
        if self._socket.isValid():
            self._socket.sendTextMessage(json.dumps(data, ensure_ascii=False))
        else:
            logger.warning(f"WS не подключён, сообщение не отправлено: {data.get('type')}")

    # =============================================================
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # =============================================================

    def _on_connected(self):
        """WebSocket соединение установлено."""
        self._reconnect_delay = self.RECONNECT_BASE  # Сбросить backoff
        logger.info("WS соединение установлено")
        self.connected.emit()

    def _on_disconnected(self):
        """WebSocket соединение потеряно."""
        logger.warning("WS соединение потеряно")
        self.disconnected.emit()

        if not self._is_intentional_close:
            # Exponential backoff
            logger.info(f"WS переподключение через {self._reconnect_delay}мс")
            self._reconnect_timer.start(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 2, self.RECONNECT_MAX)

    def _on_message(self, raw_text: str):
        """Получено текстовое сообщение от сервера."""
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error(f"WS невалидный JSON: {raw_text[:100]}")
            return

        msg_type = data.get("type")

        if msg_type == "ping":
            # Ответить на heartbeat
            self._send_json({"type": "pong"})

        elif msg_type == "new_message":
            self.message_received.emit(data)

        elif msg_type == "typing":
            self.typing_received.emit(data)

        elif msg_type == "read":
            self.read_received.emit(data)

        elif msg_type == "user_online":
            self.user_online.emit(data)

        elif msg_type == "user_offline":
            self.user_offline.emit(data)

        elif msg_type == "message_edited":
            self.message_received.emit(data)  # Обработать как обновление

        elif msg_type == "message_deleted":
            self.message_received.emit(data)

        elif msg_type == "participant_added":
            self.message_received.emit(data)

        elif msg_type == "error":
            self.error_occurred.emit(data.get("message", "Неизвестная ошибка WS"))

        else:
            logger.debug(f"WS неизвестный тип: {msg_type}")

    def _on_error(self, error):
        """Ошибка WebSocket."""
        error_msg = self._socket.errorString()
        logger.error(f"WS ошибка: {error_msg}")
        self.error_occurred.emit(error_msg)
```

### Пример использования в UI

```python
# В main.py или в главном окне:
from utils.chat_websocket import ChatWebSocket

# Инициализация
chat_ws = ChatWebSocket(
    base_url="https://crm.festivalcolor.ru",
    token=data_access.get_access_token(),
)

# Подключение сигналов
chat_ws.message_received.connect(on_new_message)
chat_ws.typing_received.connect(on_typing_indicator)
chat_ws.connected.connect(lambda: print("Чат подключён"))
chat_ws.disconnected.connect(lambda: print("Чат отключён"))

# Старт
chat_ws.connect_to_server()

# Отправка
chat_ws.send_message(chat_guid="...", content="Привет!")
chat_ws.send_typing(chat_guid="...")
chat_ws.send_read(chat_guid="...", message_id=123)

# Закрытие (при выходе из приложения)
chat_ws.disconnect_from_server()
```

**Важно (PyQt Signal Safety):** Все сигналы ChatWebSocket эмитятся в потоке QWebSocket, что безопасно, так как QWebSocket работает в event loop Qt. Если бы использовался `threading.Thread`, потребовался бы `QTimer.singleShot(0, ...)` (правило 11 из CLAUDE.md).

---

## 11. Quasar PWA -- компоненты чата

### Chat Store (Pinia)

Файл: `mobile/src/stores/chat.js`

```javascript
// Состояние чата (Pinia)

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from 'src/boot/axios'
import { useWebSocket } from '@vueuse/core'

export const useChatStore = defineStore('chat', () => {
  // ==================
  // STATE
  // ==================
  const chats = ref([])                // Список чатов
  const currentChat = ref(null)        // Текущий открытый чат
  const messages = ref([])             // Сообщения текущего чата
  const hasMore = ref(false)           // Есть ли ещё сообщения для подгрузки
  const loading = ref(false)           // Загрузка
  const typingUsers = ref({})          // { chat_guid: [{ user_id, user_name, timeout_id }] }
  const onlineUsers = ref(new Set())   // Set<user_id> пользователей онлайн

  // ==================
  // WEBSOCKET
  // ==================
  let ws = null

  function connectWebSocket(token) {
    const wsUrl = `${import.meta.env.VITE_WS_URL || 'wss://crm.festivalcolor.ru'}/ws/chat?token=${token}`

    ws = useWebSocket(wsUrl, {
      autoReconnect: {
        retries: Infinity,
        delay: 1000,
        maxDelay: 30000,
        onFailed() {
          console.error('WS: все попытки переподключения исчерпаны')
        },
      },
      heartbeat: {
        message: JSON.stringify({ type: 'pong' }),
        interval: 30000,
        pongTimeout: 10000,
      },
      onMessage(ws, event) {
        const data = JSON.parse(event.data)
        handleWsMessage(data)
      },
      onConnected() {
        console.log('WS подключён')
      },
      onDisconnected() {
        console.log('WS отключён')
      },
    })

    return ws
  }

  function handleWsMessage(data) {
    switch (data.type) {
      case 'new_message':
        _onNewMessage(data)
        break
      case 'typing':
        _onTyping(data)
        break
      case 'read':
        _onRead(data)
        break
      case 'user_online':
        onlineUsers.value.add(data.user_id)
        break
      case 'user_offline':
        onlineUsers.value.delete(data.user_id)
        break
      case 'ping':
        ws?.send(JSON.stringify({ type: 'pong' }))
        break
      case 'message_edited':
        _onMessageEdited(data)
        break
      case 'message_deleted':
        _onMessageDeleted(data)
        break
    }
  }

  function _onNewMessage(data) {
    const msg = data.message

    // Добавить в текущий чат (если открыт)
    if (currentChat.value?.guid === data.chat_guid) {
      messages.value.push(msg)
    }

    // Обновить превью в списке чатов
    const chat = chats.value.find(c => c.guid === data.chat_guid)
    if (chat) {
      chat.last_message = msg.content?.substring(0, 100)
      chat.last_message_at = msg.created_at
      chat.last_message_user = msg.user_id
      // Увеличить счётчик непрочитанных (если чат не открыт)
      if (currentChat.value?.guid !== data.chat_guid) {
        chat.unread_count = (chat.unread_count || 0) + 1
      }
    }
  }

  function _onTyping(data) {
    const key = data.chat_guid
    if (!typingUsers.value[key]) {
      typingUsers.value[key] = []
    }

    // Удалить предыдущий таймер для этого пользователя
    const existing = typingUsers.value[key].find(u => u.user_id === data.user_id)
    if (existing) {
      clearTimeout(existing.timeout_id)
      typingUsers.value[key] = typingUsers.value[key].filter(u => u.user_id !== data.user_id)
    }

    // Добавить с таймером на 4 секунды
    const timeout_id = setTimeout(() => {
      typingUsers.value[key] = (typingUsers.value[key] || []).filter(u => u.user_id !== data.user_id)
    }, 4000)

    typingUsers.value[key].push({
      user_id: data.user_id,
      user_name: data.user_name,
      timeout_id,
    })
  }

  function _onRead(data) {
    // Обновить статус прочтения в UI (галочки)
    // Можно хранить в отдельном reactive объекте
  }

  function _onMessageEdited(data) {
    const msg = data.message
    const idx = messages.value.findIndex(m => m.guid === msg.guid)
    if (idx !== -1) {
      messages.value[idx] = { ...messages.value[idx], ...msg }
    }
  }

  function _onMessageDeleted(data) {
    const idx = messages.value.findIndex(m => m.guid === data.message_guid)
    if (idx !== -1) {
      messages.value.splice(idx, 1)
    }
  }

  // ==================
  // REST API
  // ==================

  async function loadChats() {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/chat')
      chats.value = data
    } finally {
      loading.value = false
    }
  }

  async function loadMessages(chatGuid, beforeId = null) {
    loading.value = true
    try {
      const params = { limit: 50 }
      if (beforeId) params.before_id = beforeId

      const { data } = await api.get(`/api/v1/chat/${chatGuid}/messages`, { params })
      if (beforeId) {
        // Подгрузка старых — добавить в начало
        messages.value = [...data.messages, ...messages.value]
      } else {
        // Первая загрузка
        messages.value = data.messages
      }
      hasMore.value = data.has_more
    } finally {
      loading.value = false
    }
  }

  async function createChat(chatType, name, participantIds, contractId = null) {
    const { data } = await api.post('/api/v1/chat', {
      chat_type: chatType,
      name,
      participant_ids: participantIds,
      contract_id: contractId,
    })
    await loadChats()  // Обновить список
    return data
  }

  async function markAsRead(chatGuid, messageId) {
    // Через WebSocket (быстрее)
    if (ws?.status === 'OPEN') {
      ws.send(JSON.stringify({
        type: 'read',
        chat_guid: chatGuid,
        message_id: messageId,
      }))
    } else {
      // Fallback на REST
      await api.put(`/api/v1/chat/${chatGuid}/read`, { message_id: messageId })
    }

    // Обновить локальный счётчик
    const chat = chats.value.find(c => c.guid === chatGuid)
    if (chat) chat.unread_count = 0
  }

  // ==================
  // SEND
  // ==================

  function sendMessage(chatGuid, content, clientGuid = null, replyToGuid = null) {
    if (!ws) return

    ws.send(JSON.stringify({
      type: 'new_message',
      chat_guid: chatGuid,
      content,
      client_guid: clientGuid || crypto.randomUUID(),
      reply_to_guid: replyToGuid,
    }))
  }

  let typingThrottle = null
  function sendTyping(chatGuid) {
    if (typingThrottle) return
    typingThrottle = setTimeout(() => { typingThrottle = null }, 3000)

    if (ws) {
      ws.send(JSON.stringify({ type: 'typing', chat_guid: chatGuid }))
    }
  }

  // ==================
  // COMPUTED
  // ==================

  const totalUnread = computed(() =>
    chats.value.reduce((sum, c) => sum + (c.unread_count || 0), 0)
  )

  const currentTyping = computed(() => {
    if (!currentChat.value) return []
    return typingUsers.value[currentChat.value.guid] || []
  })

  return {
    // State
    chats, currentChat, messages, hasMore, loading, onlineUsers,
    // Computed
    totalUnread, currentTyping,
    // Actions
    connectWebSocket, loadChats, loadMessages, createChat,
    sendMessage, sendTyping, markAsRead,
  }
})
```

### ChatPage.vue (окно чата)

```vue
<!-- mobile/src/pages/ChatPage.vue -->
<template>
  <q-page class="chat-page">
    <!-- Заголовок чата -->
    <q-header class="chat-header">
      <q-toolbar>
        <q-btn flat round icon="arrow_back" @click="$router.back()" />
        <q-toolbar-title>
          {{ chatName }}
          <div v-if="currentTyping.length" class="typing-indicator text-caption">
            {{ typingText }}
          </div>
        </q-toolbar-title>
        <q-btn flat round icon="more_vert">
          <q-menu>
            <q-list>
              <q-item clickable @click="showParticipants = true">
                <q-item-section>Участники</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
      </q-toolbar>
    </q-header>

    <!-- Область сообщений -->
    <q-scroll-area
      ref="scrollArea"
      class="messages-area"
      @scroll="onScroll"
    >
      <!-- Подгрузка истории -->
      <q-infinite-scroll
        reverse
        @load="loadOlderMessages"
        :offset="250"
      >
        <template v-slot:loading>
          <div class="text-center q-my-md">
            <q-spinner-dots color="primary" size="40px" />
          </div>
        </template>

        <!-- Список сообщений -->
        <div class="q-pa-md">
          <div v-for="msg in messages" :key="msg.guid" class="q-mb-sm">
            <!-- Системное сообщение -->
            <div v-if="msg.message_type === 'system'" class="system-message text-center text-caption text-grey">
              {{ msg.content }}
            </div>

            <!-- Обычное сообщение -->
            <q-chat-message
              v-else
              :name="msg.user_name"
              :text="[msg.content]"
              :sent="msg.user_id === currentUserId"
              :stamp="formatTime(msg.created_at)"
              :bg-color="msg.user_id === currentUserId ? 'light-green-2' : 'white'"
            >
              <!-- Вложения -->
              <template v-if="msg.attachments?.length">
                <div v-for="att in msg.attachments" :key="att.id" class="attachment q-mt-xs">
                  <!-- Изображение -->
                  <q-img
                    v-if="att.file_type?.startsWith('image/')"
                    :src="getThumbnailUrl(att)"
                    style="max-width: 250px; border-radius: 8px; cursor: pointer"
                    @click="openFullImage(att)"
                  />
                  <!-- Документ -->
                  <q-btn
                    v-else
                    flat
                    no-caps
                    :icon="getFileIcon(att.file_type)"
                    :label="att.file_name"
                    @click="downloadFile(att)"
                  />
                </div>
              </template>

              <!-- Пометка "изменено" -->
              <template v-if="msg.is_edited">
                <span class="text-caption text-grey-6"> (изм.)</span>
              </template>
            </q-chat-message>
          </div>
        </div>
      </q-infinite-scroll>
    </q-scroll-area>

    <!-- Поле ввода -->
    <q-footer class="chat-footer">
      <!-- Индикатор ответа -->
      <div v-if="replyTo" class="reply-bar q-px-md q-py-xs bg-grey-2">
        <span class="text-caption">Ответ для {{ replyTo.user_name }}: {{ replyTo.content.substring(0, 50) }}</span>
        <q-btn flat round dense icon="close" size="xs" @click="replyTo = null" />
      </div>

      <q-toolbar class="q-pa-sm">
        <!-- Загрузка файлов -->
        <q-btn flat round icon="attach_file" @click="$refs.fileInput.click()">
          <input
            ref="fileInput"
            type="file"
            hidden
            multiple
            accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.zip"
            @change="onFileSelected"
          />
        </q-btn>

        <!-- Текстовое поле -->
        <q-input
          v-model="newMessage"
          dense
          rounded
          outlined
          placeholder="Сообщение..."
          class="col"
          @keyup.enter="send"
          @update:model-value="onTyping"
        >
          <template v-slot:append>
            <q-btn
              flat
              round
              dense
              icon="send"
              color="primary"
              :disable="!newMessage.trim()"
              @click="send"
            />
          </template>
        </q-input>
      </q-toolbar>
    </q-footer>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useChatStore } from 'src/stores/chat'
import { useAuthStore } from 'src/stores/auth'
import { date } from 'quasar'

const route = useRoute()
const chatStore = useChatStore()
const authStore = useAuthStore()

const chatGuid = route.params.guid
const newMessage = ref('')
const replyTo = ref(null)
const scrollArea = ref(null)

const currentUserId = computed(() => authStore.user?.id)
const messages = computed(() => chatStore.messages)
const currentTyping = computed(() => chatStore.currentTyping)

const chatName = computed(() => {
  const chat = chatStore.chats.find(c => c.guid === chatGuid)
  return chat?.name || 'Чат'
})

const typingText = computed(() => {
  const names = currentTyping.value.map(u => u.user_name)
  if (names.length === 1) return `${names[0]} печатает...`
  if (names.length > 1) return `${names.join(', ')} печатают...`
  return ''
})

onMounted(async () => {
  chatStore.currentChat = chatStore.chats.find(c => c.guid === chatGuid) || { guid: chatGuid }
  await chatStore.loadMessages(chatGuid)
  scrollToBottom()
  // Отметить прочтение
  if (messages.value.length) {
    chatStore.markAsRead(chatGuid, messages.value[messages.value.length - 1].id)
  }
})

onUnmounted(() => {
  chatStore.currentChat = null
})

// Автоскролл при новом сообщении
watch(
  () => messages.value.length,
  () => nextTick(() => scrollToBottom())
)

function scrollToBottom() {
  if (scrollArea.value) {
    const el = scrollArea.value.$el.querySelector('.q-scrollarea__container')
    if (el) el.scrollTop = el.scrollHeight
  }
}

async function loadOlderMessages(index, done) {
  if (!chatStore.hasMore || !messages.value.length) {
    done(true)
    return
  }
  const oldestId = messages.value[0]?.id
  await chatStore.loadMessages(chatGuid, oldestId)
  done(!chatStore.hasMore)
}

function send() {
  const text = newMessage.value.trim()
  if (!text) return

  chatStore.sendMessage(
    chatGuid,
    text,
    null,  // client_guid (авто)
    replyTo.value?.guid || null,
  )

  newMessage.value = ''
  replyTo.value = null
}

function onTyping() {
  chatStore.sendTyping(chatGuid)
}

function formatTime(isoString) {
  return date.formatDate(new Date(isoString), 'HH:mm')
}

async function onFileSelected(event) {
  const files = event.target.files
  for (const file of files) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('content', file.name)

    try {
      const { data } = await api.post(`/api/v1/chat/${chatGuid}/upload`, formData)
      // WebSocket уведомление придёт автоматически
    } catch (err) {
      console.error('Ошибка загрузки файла:', err)
    }
  }
  event.target.value = ''  // Сбросить input
}

function getThumbnailUrl(attachment) {
  // Получить URL миниатюры через API
  if (attachment.thumbnail_path) {
    return `/api/v1/files/public-link?path=${encodeURIComponent(attachment.thumbnail_path)}`
  }
  return `/api/v1/files/public-link?path=${encodeURIComponent(attachment.file_path)}`
}

function getFileIcon(mimeType) {
  if (!mimeType) return 'insert_drive_file'
  if (mimeType.includes('pdf')) return 'picture_as_pdf'
  if (mimeType.includes('word') || mimeType.includes('doc')) return 'description'
  if (mimeType.includes('sheet') || mimeType.includes('xls')) return 'table_chart'
  if (mimeType.includes('zip') || mimeType.includes('rar')) return 'folder_zip'
  return 'insert_drive_file'
}

function downloadFile(attachment) {
  window.open(`/api/v1/files/download?path=${encodeURIComponent(attachment.file_path)}`)
}

function openFullImage(attachment) {
  window.open(`/api/v1/files/public-link?path=${encodeURIComponent(attachment.file_path)}`)
}
</script>

<style scoped lang="scss">
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.chat-header {
  background: #f5f5f5;
  color: #333;
}

.messages-area {
  flex: 1;
  background: #e8e8e8;
}

.chat-footer {
  background: #fff;
  border-top: 1px solid #e0e0e0;
}

.typing-indicator {
  font-size: 11px;
  color: #888;
  font-style: italic;
}

.system-message {
  padding: 4px 12px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 12px;
  display: inline-block;
  margin: 4px auto;
}

.reply-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-left: 3px solid #1976d2;
}
</style>
```

### ChatListPage.vue (список чатов)

```vue
<!-- mobile/src/pages/ChatListPage.vue -->
<template>
  <q-page>
    <q-pull-to-refresh @refresh="onRefresh">
      <q-list separator>
        <q-item
          v-for="chat in sortedChats"
          :key="chat.guid"
          clickable
          @click="openChat(chat)"
        >
          <!-- Аватар -->
          <q-item-section avatar>
            <q-avatar :color="chat.chat_type === 'direct' ? 'primary' : 'teal'" text-color="white">
              {{ getInitials(chat.name) }}
            </q-avatar>
          </q-item-section>

          <!-- Контент -->
          <q-item-section>
            <q-item-label>{{ chat.name }}</q-item-label>
            <q-item-label caption lines="1">
              {{ chat.last_message || 'Нет сообщений' }}
            </q-item-label>
          </q-item-section>

          <!-- Время + badge -->
          <q-item-section side top>
            <q-item-label caption>{{ formatDate(chat.last_message_at) }}</q-item-label>
            <q-badge
              v-if="chat.unread_count > 0"
              rounded
              color="red"
              :label="chat.unread_count"
              class="q-mt-xs"
            />
          </q-item-section>
        </q-item>
      </q-list>

      <!-- Пустой список -->
      <div v-if="!chats.length && !loading" class="text-center q-pa-xl text-grey">
        Нет чатов. Создайте первый!
      </div>
    </q-pull-to-refresh>

    <!-- FAB — создать чат -->
    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-fab icon="add" direction="up" color="primary">
        <q-fab-action color="secondary" icon="person" label="Личный" @click="createDirectChat" />
        <q-fab-action color="accent" icon="group" label="Группа" @click="createGroupChat" />
      </q-fab>
    </q-page-sticky>
  </q-page>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from 'src/stores/chat'
import { date } from 'quasar'

const router = useRouter()
const chatStore = useChatStore()

const chats = computed(() => chatStore.chats)
const loading = computed(() => chatStore.loading)

const sortedChats = computed(() =>
  [...chats.value].sort((a, b) => {
    const dateA = a.last_message_at ? new Date(a.last_message_at) : new Date(a.created_at)
    const dateB = b.last_message_at ? new Date(b.last_message_at) : new Date(b.created_at)
    return dateB - dateA
  })
)

onMounted(() => chatStore.loadChats())

async function onRefresh(done) {
  await chatStore.loadChats()
  done()
}

function openChat(chat) {
  router.push(`/chat/${chat.guid}`)
}

function formatDate(isoString) {
  if (!isoString) return ''
  const d = new Date(isoString)
  const today = new Date()
  if (date.isSameDate(d, today, 'day')) return date.formatDate(d, 'HH:mm')
  if (date.isSameDate(d, today, 'year')) return date.formatDate(d, 'D MMM')
  return date.formatDate(d, 'DD.MM.YYYY')
}

function getInitials(name) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase()
}

function createDirectChat() {
  // Открыть диалог выбора сотрудника
  router.push('/chat/new?type=direct')
}

function createGroupChat() {
  router.push('/chat/new?type=group')
}
</script>
```

---

## 12. Конфигурация nginx

### Текущий nginx.conf

В текущей конфигурации (`nginx/nginx.conf`) WebSocket уже частично поддерживается в блоке `location /` (заголовки Upgrade/Connection). Однако для чата рекомендуется выделить отдельный `location /ws/` с увеличенным таймаутом.

### Изменения в nginx.conf

```nginx
# В блоке server (HTTPS, port 443) — ДОБАВИТЬ перед location / :

# =============================================================
# WebSocket для чата — отдельный location с большим таймаутом
# =============================================================
location /ws/ {
    proxy_pass http://api;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # КРИТИЧНО: WebSocket соединения длительные
    # 3600s = 1 час (heartbeat каждые 30 секунд поддерживает соединение)
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;

    # Отключить буферизацию для WebSocket
    proxy_buffering off;
    proxy_cache off;
}
```

**Важно:** Текущий `proxy_read_timeout 60s` в `location /` слишком мал для WebSocket. Без отдельного `location /ws/` соединение будет разрываться через 60 секунд неактивности (между heartbeat'ами — 30 секунд, поэтому формально должно работать, но лучше не рисковать).

### CSP заголовок

Также нужно обновить `Content-Security-Policy` для поддержки WebSocket:

```nginx
# Было:
add_header Content-Security-Policy "default-src 'self'; ... connect-src 'self' https://crm.festivalcolor.ru" always;

# Стало (добавить wss://):
add_header Content-Security-Policy "default-src 'self'; ... connect-src 'self' https://crm.festivalcolor.ru wss://crm.festivalcolor.ru" always;
```

---

## 13. Docker -- изменения

### docker-compose.yml

Изменений в `docker-compose.yml` **не требуется** — WebSocket обрабатывается тем же uvicorn на порту 8000.

### Dockerfile

Если используется Pillow для thumbnails, добавить в `server/Dockerfile`:

```dockerfile
# Установка зависимостей системы + шрифты + Pillow зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    fonts-dejavu-core \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
```

### requirements.txt

Добавить:

```
# Чат — push-уведомления
pywebpush==2.0.0
# Чат — thumbnails (уже может быть через reportlab, но нужен явно)
Pillow==10.4.0
```

### Количество workers

**Важно:** Текущий `Dockerfile` запускает uvicorn с `--workers 2`. Для WebSocket чата с in-memory ConnectionManager это проблема: два worker'а имеют **разные** инстансы ConnectionManager, и пользователь, подключённый к worker 1, не получит сообщение от пользователя на worker 2.

**Решения (в порядке простоты):**

1. **Один worker (рекомендуется для начала):**
   ```dockerfile
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--limit-concurrency", "100", "--backlog", "2048"]
   ```
   Один async worker справится с 10,000+ WebSocket соединений. Для 50-100 пользователей CRM — более чем достаточно.

2. **Redis PubSub (для 2+ workers):**
   Добавить Redis в docker-compose и `broadcaster` библиотеку. ConnectionManager подписывается на Redis channel и ретранслирует сообщения.

3. **Centrifugo (для 500+ пользователей):**
   См. раздел 15.

---

## 14. Серверные требования

### Текущий сервер (Timeweb)

| Ресурс | Без чата | С чатом | Примечание |
|--------|----------|---------|------------|
| RAM | ~1 GB | ~1.5 GB | +WebSocket ~5 MB (100 пользователей) |
| CPU | Минимальная | Минимальная | WebSocket в idle = 0 CPU |
| Диск | API + БД | +5 MB (PWA) | PWA статика мизерная |
| Сеть | REST API | +WebSocket | Минимальный трафик (JSON) |

### Потребление памяти WebSocket

| Компонент | Потребление |
|-----------|-------------|
| 1 WebSocket соединение | ~20-50 KB RAM |
| 50 пользователей (1 устройство) | ~2.5 MB |
| 50 пользователей (2 устройства) | ~5 MB |
| ConnectionManager (структуры) | ~1 MB |
| **Итого** | **~6-8 MB** |

### Минимальные требования

- **CPU:** 2 ядра
- **RAM:** 4 GB (2 GB для PostgreSQL + 1 GB для FastAPI + 1 GB запас)
- **Redis:** Не нужен при 1 worker (текущая конфигурация)
- **Диск:** +100 MB (чат файлы хранятся на Яндекс.Диске)

### Мониторинг

Добавить в health endpoint статистику WebSocket:

```python
# В server/main.py, в endpoint /health:
from services.chat_connection_manager import chat_manager

@app.get("/health")
async def health():
    ws_stats = chat_manager.get_stats()
    return {
        "status": "healthy",
        "websocket": ws_stats,
        # ... остальное
    }
```

---

## 15. Centrifugo

### Когда переходить

| Показатель | Без Centrifugo | С Centrifugo |
|-----------|---------------|-------------|
| Пользователей | до 200-300 | 500+ |
| Workers uvicorn | 1 | Любое количество |
| Гарантия доставки | Нет (если disconnect) | Да (history + recover) |
| Presence (кто онлайн) | Ручной tracking | Встроенный |
| Масштабирование | Вертикальное | Горизонтальное (Redis/Nats) |

**Рекомендация:** Начинать с нативного FastAPI WebSocket. Переходить на Centrifugo только при достижении 200+ одновременных подключений или при необходимости горизонтального масштабирования.

### Docker setup

```yaml
# Добавить в docker-compose.yml:
centrifugo:
  image: centrifugo/centrifugo:v5
  container_name: crm_centrifugo
  restart: always
  volumes:
    - ./centrifugo/config.json:/centrifugo/config.json:ro
  ports:
    - "127.0.0.1:8001:8000"  # Centrifugo API
  command: centrifugo -c config.json
  depends_on:
    - postgres
```

### config.json

```json
{
  "token_hmac_secret_key": "SAME_AS_JWT_SECRET_KEY",
  "admin": true,
  "admin_password": "ADMIN_PASSWORD",
  "admin_secret": "ADMIN_SECRET",
  "api_key": "API_KEY_FOR_SERVER",
  "allowed_origins": [
    "https://crm.festivalcolor.ru"
  ],
  "namespaces": [
    {
      "name": "chat",
      "presence": true,
      "join_leave": true,
      "history_size": 100,
      "history_ttl": "720h",
      "recover": true
    }
  ]
}
```

### Python SDK (серверная часть)

```bash
pip install pycent
```

```python
# server/services/centrifugo_service.py
from cent import Client, PublishRequest

centrifugo = Client("http://centrifugo:8000/api", api_key="API_KEY_FOR_SERVER")

async def publish_to_chat(chat_guid: str, data: dict):
    """Отправить сообщение через Centrifugo."""
    request = PublishRequest(channel=f"chat:{chat_guid}", data=data)
    centrifugo.publish(request)
```

### Клиентская часть (JavaScript)

```javascript
// Centrifugo JS SDK
import { Centrifuge } from 'centrifuge'

const centrifuge = new Centrifuge('wss://crm.festivalcolor.ru/connection/websocket', {
  token: jwtToken,  // Тот же JWT, если secret совпадает
})

const sub = centrifuge.newSubscription(`chat:${chatGuid}`)

sub.on('publication', (ctx) => {
  // Новое сообщение
  handleNewMessage(ctx.data)
})

sub.on('join', (ctx) => {
  // Пользователь подключился
})

sub.on('leave', (ctx) => {
  // Пользователь отключился
})

sub.subscribe()
centrifuge.connect()
```

### nginx для Centrifugo

```nginx
# Добавить в nginx.conf:
location /connection/ {
    proxy_pass http://centrifugo:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;
}
```

---

## 16. Референсный проект

### notarious2/fastapi-chat

**GitHub:** https://github.com/notarious2/fastapi-chat

Почему релевантен:
- **Тот же стек:** FastAPI + SQLAlchemy 2.0 + PostgreSQL + Alembic
- **WebSocket:** Нативный FastAPI WebSocket (без Socket.IO)
- **Архитектура:** ConnectionManager + room support
- **Пагинация:** Cursor-based для истории
- **Файлы:** Upload через REST

Что можно взять оттуда:
- Структуру ConnectionManager (адаптирована в разделе 4)
- Паттерн cursor-based пагинации сообщений
- Обработку WebSocket disconnect/reconnect

---

## 17. Чеклист реализации

### Этап 1: Бэкенд чата (1-2 недели)

- [ ] Alembic миграция — 5 таблиц (раздел 3)
- [ ] SQLAlchemy модели в `database.py` (раздел 2)
- [ ] `ConnectionManager` в `services/chat_connection_manager.py` (раздел 4)
- [ ] WebSocket endpoint в `routers/chat_ws_router.py` (раздел 5)
- [ ] REST endpoints в `routers/chat_rest_router.py` (раздел 6)
- [ ] Pydantic-схемы в `chat_schemas.py` (раздел 7)
- [ ] Загрузка файлов + thumbnails (раздел 8)
- [ ] Обновить `main.py` — зарегистрировать роутеры
- [ ] Обновить `nginx.conf` — location /ws/ + CSP (раздел 12)
- [ ] Обновить `requirements.txt` (pywebpush, Pillow)
- [ ] Тесты: WebSocket endpoint (pytest + httpx + websocket)
- [ ] Docker rebuild + проверка /health

### Этап 2: PyQt5 Desktop интеграция (1 неделя)

- [ ] `ChatWebSocket` в `utils/chat_websocket.py` (раздел 10)
- [ ] Виджет списка чатов (QListWidget + badge непрочитанных)
- [ ] Виджет окна чата (QTextBrowser + QLineEdit)
- [ ] Интеграция с DataAccess (JWT, загрузка чатов)
- [ ] Кнопка чата в панели навигации

### Этап 3: PWA каркас + авторизация (1 неделя)

- [ ] `quasar create mobile` + добавить PWA mode
- [ ] Авторизация (Pinia + axios interceptor + JWT refresh)
- [ ] QLayout + навигация (bottom tabs: Чаты, Проекты, Профиль)
- [ ] manifest.json + иконки + splash screens
- [ ] nginx раздача PWA статики (`location /` → `dist/pwa/`)

### Этап 4: PWA чат (2 недели)

- [ ] Chat store (Pinia) с WebSocket (раздел 11)
- [ ] ChatListPage.vue — список чатов
- [ ] ChatPage.vue — окно чата (QChatMessage + QInfiniteScroll)
- [ ] Создание чатов (direct / group / project)
- [ ] Загрузка файлов (камера / галерея / документы)
- [ ] Typing indicator + read status

### Этап 5: Push-уведомления + полировка (1 неделя)

- [ ] Web Push VAPID (pywebpush) (раздел 9)
- [ ] Service Worker — обработка push + offline cache
- [ ] Telegram Bot — push для Desktop (уже интегрирован)
- [ ] Install banner (Android auto + iOS инструкция)
- [ ] Safe areas (notch, Dynamic Island)
- [ ] Тестирование на реальных устройствах

**Итого: 6-8 недель**

---

## Приложение А: Полная структура файлов (что создать/изменить)

```
server/
├── database.py                              # ИЗМЕНИТЬ — добавить Chat, Message и т.д.
├── chat_schemas.py                          # СОЗДАТЬ
├── requirements.txt                         # ИЗМЕНИТЬ — pywebpush, Pillow
├── main.py                                  # ИЗМЕНИТЬ — include_router
├── Dockerfile                               # ИЗМЕНИТЬ — workers=1, libjpeg
├── services/
│   ├── chat_connection_manager.py           # СОЗДАТЬ
│   └── push_service.py                      # СОЗДАТЬ
├── routers/
│   ├── chat_ws_router.py                    # СОЗДАТЬ
│   └── chat_rest_router.py                  # СОЗДАТЬ
└── alembic/versions/
    └── l2m3n4o5p6q7_add_chat_tables.py      # СОЗДАТЬ

nginx/
└── nginx.conf                               # ИЗМЕНИТЬ — location /ws/ + CSP

utils/
└── chat_websocket.py                        # СОЗДАТЬ (PyQt5 клиент)

mobile/                                       # СОЗДАТЬ (Quasar PWA)
├── src/stores/chat.js
├── src/pages/ChatListPage.vue
├── src/pages/ChatPage.vue
├── src-pwa/custom-service-worker.js
└── ...
```

---

## Приложение Б: Команды для быстрого старта

```bash
# 1. Применить миграцию
ssh timeweb "cd /opt/interior_studio && docker exec crm_api alembic upgrade head"

# 2. Docker rebuild (после изменений в server/)
ssh timeweb "cd /opt/interior_studio && git pull origin feat/chat && docker-compose down && docker-compose build --no-cache api && docker-compose up -d"

# 3. Проверить health
ssh timeweb 'curl -s http://localhost:8000/health | python3 -m json.tool'

# 4. Тест WebSocket (из консоли)
python3 -c "
import asyncio, websockets, json
async def test():
    uri = 'wss://crm.festivalcolor.ru/ws/chat?token=JWT_TOKEN'
    async with websockets.connect(uri) as ws:
        print('Connected!')
        msg = await ws.recv()
        print(f'Received: {msg}')
asyncio.run(test())
"

# 5. Создать Quasar PWA проект
npm init quasar mobile
cd mobile
quasar mode add pwa
quasar dev -m pwa
```
