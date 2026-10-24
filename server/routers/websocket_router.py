"""
WebSocket роутер для real-time обновлений.
Клиенты подключаются через /api/v1/ws?token=JWT_TOKEN
Получают события: card_moved, card_updated, notification_new, user_online
"""
import logging
import asyncio
import json
from typing import Dict, Set, Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config import get_settings
from database import SessionLocal, Employee

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """
    Менеджер WebSocket соединений.
    Хранит активные соединения по employee_id.
    У одного сотрудника может быть несколько устройств (мобильное + десктоп).
    """

    def __init__(self):
        # employee_id -> set[WebSocket]
        self._connections: Dict[int, Set[WebSocket]] = {}
        # WebSocket -> employee_id (обратный маппинг для быстрого поиска)
        self._ws_to_user: Dict[WebSocket, int] = {}

    @property
    def online_user_ids(self) -> Set[int]:
        """Множество ID пользователей с активными соединениями"""
        return set(self._connections.keys())

    @property
    def total_connections(self) -> int:
        """Общее количество активных соединений"""
        return len(self._ws_to_user)

    async def connect(self, websocket: WebSocket, employee_id: int):
        """Принять WebSocket соединение и зарегистрировать"""
        await websocket.accept()

        if employee_id not in self._connections:
            self._connections[employee_id] = set()

        self._connections[employee_id].add(websocket)
        self._ws_to_user[websocket] = employee_id

        logger.info(
            f"WS подключён: employee_id={employee_id}, "
            f"всего соединений={self.total_connections}, "
            f"пользователей онлайн={len(self.online_user_ids)}"
        )

        # Рассылаем событие user_online всем остальным
        await self.broadcast(
            event_type="user_online",
            data={"employee_id": employee_id, "status": "online"},
            exclude_user_id=employee_id,
        )

    async def disconnect(self, websocket: WebSocket):
        """Удалить WebSocket соединение"""
        employee_id = self._ws_to_user.pop(websocket, None)
        if employee_id is None:
            return

        connections = self._connections.get(employee_id)
        if connections:
            connections.discard(websocket)
            # Если у пользователя больше нет соединений — он ушёл offline
            if not connections:
                del self._connections[employee_id]
                logger.info(
                    f"WS отключён (offline): employee_id={employee_id}, "
                    f"всего соединений={self.total_connections}"
                )
                # Рассылаем событие user_offline
                await self.broadcast(
                    event_type="user_online",
                    data={"employee_id": employee_id, "status": "offline"},
                    exclude_user_id=employee_id,
                )
            else:
                logger.info(
                    f"WS отключён (ещё есть устройства): employee_id={employee_id}, "
                    f"осталось={len(connections)}"
                )

    async def send_to_user(self, employee_id: int, message: dict):
        """Отправить сообщение конкретному пользователю (на все его устройства)"""
        connections = self._connections.get(employee_id, set())
        dead = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        # Убираем мёртвые соединения
        for ws in dead:
            await self.disconnect(ws)

    async def broadcast(
        self,
        event_type: str,
        data: dict,
        exclude_user_id: Optional[int] = None,
    ):
        """
        Рассылка события всем подключённым пользователям.
        exclude_user_id — не отправлять инициатору (чтобы не дублировать).
        """
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if exclude_user_id is not None:
            message["sender_id"] = exclude_user_id

        dead = []
        for ws, uid in list(self._ws_to_user.items()):
            if uid == exclude_user_id:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        # Убираем мёртвые соединения
        for ws in dead:
            await self.disconnect(ws)


# Глобальный экземпляр менеджера — используется из других роутеров
manager = ConnectionManager()


def _authenticate_ws_token(token: str) -> Optional[int]:
    """
    Проверить JWT токен из query-параметра WebSocket.
    Возвращает employee_id или None при ошибке.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None

    # Принимаем только access-токены
    token_type = payload.get("type")
    if token_type and token_type != "access":
        return None

    employee_id = payload.get("sub")
    if employee_id is None:
        return None

    try:
        employee_id = int(employee_id)
    except (ValueError, TypeError):
        return None

    # Проверяем что сотрудник существует и активен
    db: Session = SessionLocal()
    try:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if employee is None:
            return None
        if getattr(employee, "is_active", True) is False:
            return None
    finally:
        db.close()

    return employee_id


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint для real-time обновлений.

    Подключение: ws(s)://host/api/v1/ws?token=JWT_ACCESS_TOKEN

    Формат сообщений (JSON):
        { "type": "card_moved", "data": {...}, "sender_id": 123, "timestamp": "..." }

    Типы событий:
        - card_moved — CRM/supervision карточка перемещена в другую колонку
        - card_updated — данные карточки обновлены
        - notification_new — новое уведомление для пользователя
        - user_online — пользователь подключился/отключился

    Клиент может отправлять:
        - {"type": "ping"} — keep-alive, ответ {"type": "pong"}
    """
    # Извлекаем токен из query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Токен не указан")
        return

    # Аутентификация
    employee_id = _authenticate_ws_token(token)
    if employee_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Неверный токен")
        return

    # Подключаем
    await manager.connect(websocket, employee_id)

    try:
        while True:
            # Ожидаем сообщения от клиента (ping/pong, будущие команды)
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                # Keep-alive pong
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WS ошибка (employee_id={employee_id}): {e}")
        await manager.disconnect(websocket)


# ============================================================
# Вспомогательные функции для вызова из других роутеров
# ============================================================

async def broadcast_event(
    event_type: str,
    data: dict,
    exclude_user_id: Optional[int] = None,
):
    """
    Рассылка real-time события всем подключённым клиентам.

    Вызывается из CRM/supervision/notifications роутеров:
        from routers.websocket_router import broadcast_event
        await broadcast_event("card_moved", {"card_id": 1, "column": "..."}, exclude_user_id=current_user.id)

    Типы событий:
        - card_moved: {"card_id": int, "column_name": str, "card_type": "crm"|"supervision"}
        - card_updated: {"card_id": int, "card_type": "crm"|"supervision", "changes": {...}}
        - notification_new: {"notification_id": int, "employee_id": int, "title": str, "message": str}
        - user_online: {"employee_id": int, "status": "online"|"offline"}
    """
    try:
        await manager.broadcast(event_type, data, exclude_user_id)
    except Exception as e:
        # WebSocket рассылка не должна ломать основную бизнес-логику
        logger.error(f"broadcast_event ошибка ({event_type}): {e}")


async def send_notification_to_user(employee_id: int, notification_data: dict):
    """
    Отправить уведомление конкретному пользователю через WebSocket.
    Используется из notifications_router при создании уведомления.
    """
    try:
        message = {
            "type": "notification_new",
            "data": notification_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await manager.send_to_user(employee_id, message)
    except Exception as e:
        logger.error(f"send_notification_to_user ошибка (employee_id={employee_id}): {e}")
