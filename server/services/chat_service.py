"""
Сервис внутреннего чата Interior Studio CRM.

Бизнес-логика:
- Создание чатов (сотрудники / клиенты)
- Управление участниками
- Сохранение сообщений
- Загрузка файлов в ЯД (папка внутри карточки)
- WebSocket ConnectionManager
- Пересылка сообщений
"""

from datetime import datetime
import logging
from typing import Dict, Optional, Set
import uuid

from fastapi import WebSocket
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import (
    Contract,
    CRMCard,
    Employee,
    InternalChat,
    InternalChatMember,
    InternalChatMessage,
    StageExecutor,
    SupervisionCard,
)

logger = logging.getLogger(__name__)


# =========================
# WebSocket ConnectionManager
# =========================


class ChatConnectionManager:
    """Управление активными WebSocket-соединениями чатов.

    Структура: {chat_id: {participant_key: WebSocket}}
    participant_key = f"emp_{employee_id}" или f"guest_{token}"
    """

    def __init__(self):
        # {chat_id: {participant_key: WebSocket}}
        self.active: dict[int, dict[str, WebSocket]] = {}

    async def connect(self, chat_id: int, participant_key: str, ws: WebSocket):
        await ws.accept()
        if chat_id not in self.active:
            self.active[chat_id] = {}
        self.active[chat_id][participant_key] = ws
        logger.debug(f"WS connect: chat={chat_id} participant={participant_key}")

    def disconnect(self, chat_id: int, participant_key: str):
        if chat_id in self.active:
            self.active[chat_id].pop(participant_key, None)
            if not self.active[chat_id]:
                del self.active[chat_id]
        logger.debug(f"WS disconnect: chat={chat_id} participant={participant_key}")

    async def broadcast(self, chat_id: int, data: dict, exclude: Optional[str] = None):
        """Разослать сообщение всем участникам чата."""
        if chat_id not in self.active:
            return
        dead: set[str] = set()
        for key, ws in self.active[chat_id].items():
            if key == exclude:
                continue
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(key)
        for key in dead:
            self.active[chat_id].pop(key, None)

    async def send_personal(self, chat_id: int, participant_key: str, data: dict):
        """Отправить сообщение конкретному участнику."""
        ws = self.active.get(chat_id, {}).get(participant_key)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.active[chat_id].pop(participant_key, None)

    def is_online(self, chat_id: int, participant_key: str) -> bool:
        return participant_key in self.active.get(chat_id, {})

    def online_count(self, chat_id: int) -> int:
        return len(self.active.get(chat_id, {}))


# Глобальный экземпляр — один на приложение
manager = ChatConnectionManager()


# =========================
# Вспомогательные функции
# =========================


def _get_contract_for_card(db: Session, crm_card_id: int) -> Optional[Contract]:
    card = db.query(CRMCard).filter(CRMCard.id == crm_card_id).first()
    if not card:
        return None
    return db.query(Contract).filter(Contract.id == card.contract_id).first()


def _get_card_folder(db: Session, crm_card_id: Optional[int] = None, supervision_card_id: Optional[int] = None) -> str:
    """Вернуть yandex_folder_path карточки без disk: префикса."""
    if crm_card_id:
        contract = _get_contract_for_card(db, crm_card_id)
        if contract and contract.yandex_folder_path:
            return contract.yandex_folder_path.replace("disk:", "").rstrip("/")
    if supervision_card_id:
        card = db.query(SupervisionCard).filter(SupervisionCard.id == supervision_card_id).first()
        if card:
            contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
            if contract and contract.yandex_folder_path:
                return contract.yandex_folder_path.replace("disk:", "").rstrip("/")
    return "/CRM/Временные файлы"


def _chat_folder_name(chat_type: str) -> str:
    return "Чат сотрудников" if chat_type == "employee" else "Чат с клиентом"


def _ensure_yd_folder(folder_path: str) -> bool:
    """Создать папку на ЯД если не существует (рекурсивно). Возвращает True при успехе."""
    try:
        from yandex_disk_service import get_yandex_disk_service

        yd = get_yandex_disk_service()
        if not yd or not yd.token:
            return False
        # ensure_folder_exists создаёт все промежуточные папки (аналог os.makedirs)
        return yd.ensure_folder_exists(folder_path)
    except Exception as e:
        logger.warning(f"ЯД: не удалось создать папку {folder_path}: {e}")
        return False


def _message_to_dict(msg: InternalChatMessage) -> dict:
    return {
        "id": msg.id,
        "chat_id": msg.chat_id,
        "sender_employee_id": msg.sender_employee_id,
        "sender_guest_token": msg.sender_guest_token,
        "sender_display_name": msg.sender_display_name,
        "message_type": msg.message_type,
        "content": msg.content,
        "file_url": msg.file_url,
        "file_name": msg.file_name,
        "file_size": msg.file_size,
        "yandex_path": msg.yandex_path,
        "is_deleted": msg.is_deleted,
        "is_edited": getattr(msg, "is_edited", False),
        "created_at": (msg.created_at.isoformat() + "Z") if msg.created_at else None,
    }


def _get_assigned_employee_ids(db: Session, crm_card_id: int) -> list:
    """Вернуть список ID всех назначенных сотрудников по карточке."""
    card = db.query(CRMCard).filter(CRMCard.id == crm_card_id).first()
    if not card:
        return []
    ids = []
    for fid in [card.senior_manager_id, card.sdp_id, card.gap_id, card.manager_id, card.surveyor_id]:
        if fid:
            ids.append(fid)
    # StageExecutor — дизайнеры, чертёжники
    executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id == crm_card_id).all()
    for ex in executors:
        if ex.executor_id and ex.executor_id not in ids:
            ids.append(ex.executor_id)
    return ids


def _get_employee_display_name(emp: Employee) -> str:
    if emp.full_name:
        return emp.full_name
    return emp.login or f"Сотрудник #{emp.id}"


# =========================
# Создание чатов
# =========================


def create_employee_chat(db: Session, crm_card_id: int, created_by_id: int, supervision_card_id: Optional[int] = None) -> InternalChat:
    """Создать чат сотрудников для карточки.

    Автоматически:
    - Добавляет всех назначенных на карточку сотрудников
    - Создаёт папку {contract.yandex_folder_path}/Чат сотрудников на ЯД
    """
    # Проверить нет ли уже чата
    existing = (
        db.query(InternalChat)
        .filter(
            InternalChat.chat_type == "employee",
            InternalChat.crm_card_id == crm_card_id,
            InternalChat.is_active == True,
        )
        .first()
    )
    if existing:
        return existing

    # Получить заголовок из карточки
    title = None
    contract_id = None
    card = db.query(CRMCard).filter(CRMCard.id == crm_card_id).first()
    if card:
        contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
        if contract:
            title = contract.address or f"Договор #{contract.id}"
            contract_id = contract.id

    # Папка ЯД
    base_folder = _get_card_folder(db, crm_card_id=crm_card_id)
    chat_folder = f"{base_folder}/{_chat_folder_name('employee')}"
    _ensure_yd_folder(f"disk:{chat_folder}")

    chat = InternalChat(
        chat_type="employee",
        crm_card_id=crm_card_id,
        supervision_card_id=supervision_card_id,
        contract_id=contract_id,
        title=title,
        yandex_folder_path=f"disk:{chat_folder}",
        created_by=created_by_id,
        is_active=True,
    )
    db.add(chat)
    db.flush()  # получаем chat.id

    # Добавить создателя
    creator = db.query(Employee).filter(Employee.id == created_by_id).first()
    if creator:
        _add_employee_member(db, chat, creator)

    # Добавить всех назначенных сотрудников
    assigned_ids = _get_assigned_employee_ids(db, crm_card_id)
    for emp_id in assigned_ids:
        if emp_id == created_by_id:
            continue
        emp = db.query(Employee).filter(Employee.id == emp_id).first()
        if emp:
            _add_employee_member(db, chat, emp)

    # Системное сообщение
    _add_system_message(db, chat, "Чат сотрудников создан")

    db.commit()
    db.refresh(chat)
    return chat


def create_client_chat(db: Session, crm_card_id: int, created_by_id: int, supervision_card_id: Optional[int] = None) -> InternalChat:
    """Создать чат с клиентом для карточки.

    Генерирует UUID-токен для первой ссылки доступа.
    Создаёт папку {contract.yandex_folder_path}/Чат с клиентом на ЯД.
    """
    existing = (
        db.query(InternalChat)
        .filter(
            InternalChat.chat_type == "client",
            InternalChat.crm_card_id == crm_card_id,
            InternalChat.is_active == True,
        )
        .first()
    )
    if existing:
        return existing

    title = None
    contract_id = None
    card = db.query(CRMCard).filter(CRMCard.id == crm_card_id).first()
    if card:
        contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
        if contract:
            title = contract.address or f"Договор #{contract.id}"
            contract_id = contract.id

    base_folder = _get_card_folder(db, crm_card_id=crm_card_id)
    chat_folder = f"{base_folder}/{_chat_folder_name('client')}"
    _ensure_yd_folder(f"disk:{chat_folder}")

    chat = InternalChat(
        chat_type="client",
        crm_card_id=crm_card_id,
        supervision_card_id=supervision_card_id,
        contract_id=contract_id,
        title=title,
        yandex_folder_path=f"disk:{chat_folder}",
        client_access_token=str(uuid.uuid4()),
        created_by=created_by_id,
        is_active=True,
    )
    db.add(chat)
    db.flush()

    # Создатель как участник
    creator = db.query(Employee).filter(Employee.id == created_by_id).first()
    if creator:
        _add_employee_member(db, chat, creator)

    _add_system_message(db, chat, "Чат с клиентом создан")

    db.commit()
    db.refresh(chat)
    return chat


def _add_employee_member(db: Session, chat: InternalChat, emp: Employee):
    """Добавить сотрудника в чат если ещё не участник."""
    existing = (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.chat_id == chat.id,
            InternalChatMember.employee_id == emp.id,
            InternalChatMember.is_active == True,
        )
        .first()
    )
    if not existing:
        member = InternalChatMember(
            chat_id=chat.id,
            member_type="employee",
            employee_id=emp.id,
            is_active=True,
        )
        db.add(member)


def _add_system_message(db: Session, chat: InternalChat, text: str):
    msg = InternalChatMessage(
        chat_id=chat.id,
        sender_display_name="Система",
        message_type="system",
        content=text,
    )
    db.add(msg)


# =========================
# Управление участниками
# =========================


def add_member_to_chat(db: Session, chat_id: int, employee_id: int) -> InternalChatMember:
    """Добавить сотрудника в существующий чат."""
    chat = db.query(InternalChat).filter(InternalChat.id == chat_id).first()
    if not chat:
        raise ValueError(f"Чат {chat_id} не найден")
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise ValueError(f"Сотрудник {employee_id} не найден")
    _add_employee_member(db, chat, emp)
    # Системное уведомление
    _add_system_message(db, chat, f"{_get_employee_display_name(emp)} добавлен в чат")
    db.commit()
    return (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.chat_id == chat_id,
            InternalChatMember.employee_id == employee_id,
        )
        .first()
    )


def create_invite_link(db: Session, chat_id: int) -> InternalChatMember:
    """Создать новую ссылку (guest_token) для представителя клиента."""
    token = str(uuid.uuid4())
    member = InternalChatMember(
        chat_id=chat_id,
        member_type="client_guest",
        guest_access_token=token,
        is_active=True,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def register_guest(db: Session, guest_token: str, name: str, phone: str) -> InternalChatMember:
    """Первый вход гостя по ссылке — сохранить имя и телефон.

    Поддерживает два сценария:
    1. guest_token — персональный токен гостя (InternalChatMember.guest_access_token)
    2. guest_token — основная ссылка чата (InternalChat.client_access_token)
       В этом случае создаётся новый участник с уникальным персональным токеном.
    """
    member = (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.guest_access_token == guest_token,
            InternalChatMember.is_active == True,
        )
        .first()
    )

    if not member:
        # Проверяем: возможно, это основная ссылка чата
        chat = (
            db.query(InternalChat)
            .filter(
                InternalChat.client_access_token == guest_token,
                InternalChat.is_active == True,
            )
            .first()
        )
        if not chat:
            raise ValueError("Ссылка недействительна или устарела")
        # Создаём нового участника-гостя с уникальным персональным токеном
        member = InternalChatMember(
            chat_id=chat.id,
            member_type="client_guest",
            guest_access_token=str(uuid.uuid4()),
            is_active=True,
        )
        db.add(member)
        db.flush()

    member.guest_name = name
    member.guest_phone = phone
    db.commit()
    db.refresh(member)
    chat_obj = db.query(InternalChat).filter(InternalChat.id == member.chat_id).first()
    _add_system_message(db, chat_obj, f"{name} присоединился к чату")
    db.commit()
    return member


# =========================
# Сообщения
# =========================


def get_messages(db: Session, chat_id: int, limit: int = 50, offset: int = 0) -> list:
    """Получить историю сообщений (пагинация)."""
    msgs = (
        db.query(InternalChatMessage)
        .filter(
            InternalChatMessage.chat_id == chat_id,
            InternalChatMessage.is_deleted == False,
        )
        .order_by(InternalChatMessage.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return msgs


def add_text_message(
    db: Session, chat_id: int, content: str, sender_employee_id: Optional[int] = None, sender_guest_token: Optional[str] = None, sender_display_name: Optional[str] = None
) -> InternalChatMessage:
    """Сохранить текстовое сообщение."""
    if not sender_display_name:
        if sender_employee_id:
            emp = db.query(Employee).filter(Employee.id == sender_employee_id).first()
            sender_display_name = _get_employee_display_name(emp) if emp else "Сотрудник"
        elif sender_guest_token:
            member = db.query(InternalChatMember).filter(InternalChatMember.guest_access_token == sender_guest_token).first()
            sender_display_name = member.guest_name if member and member.guest_name else "Клиент"
        else:
            sender_display_name = "Система"

    msg = InternalChatMessage(
        chat_id=chat_id,
        sender_employee_id=sender_employee_id,
        sender_guest_token=sender_guest_token,
        sender_display_name=sender_display_name,
        message_type="text",
        content=content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def add_file_message(
    db: Session,
    chat_id: int,
    file_url: str,
    file_name: str,
    yandex_path: str,
    file_size: Optional[int] = None,
    message_type: str = "file",
    sender_employee_id: Optional[int] = None,
    sender_guest_token: Optional[str] = None,
    sender_display_name: Optional[str] = None,
) -> InternalChatMessage:
    """Сохранить сообщение с файлом/голосом/изображением."""
    if not sender_display_name:
        if sender_employee_id:
            emp = db.query(Employee).filter(Employee.id == sender_employee_id).first()
            sender_display_name = _get_employee_display_name(emp) if emp else "Сотрудник"
        elif sender_guest_token:
            member = db.query(InternalChatMember).filter(InternalChatMember.guest_access_token == sender_guest_token).first()
            sender_display_name = member.guest_name if member and member.guest_name else "Клиент"
        else:
            sender_display_name = "Система"

    msg = InternalChatMessage(
        chat_id=chat_id,
        sender_employee_id=sender_employee_id,
        sender_guest_token=sender_guest_token,
        sender_display_name=sender_display_name,
        message_type=message_type,
        file_url=file_url,
        file_name=file_name,
        file_size=file_size,
        yandex_path=yandex_path,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def edit_message(db: Session, message_id: int, employee_id: int, content: str) -> "InternalChatMessage | None":
    """Редактировать своё текстовое сообщение."""
    msg = (
        db.query(InternalChatMessage)
        .filter(
            InternalChatMessage.id == message_id,
            InternalChatMessage.sender_employee_id == employee_id,
            InternalChatMessage.message_type == "text",
            InternalChatMessage.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if not msg:
        return None
    msg.content = content.strip()
    msg.is_edited = True
    db.commit()
    db.refresh(msg)
    return msg


def delete_message(db: Session, message_id: int, employee_id: int) -> bool:
    """Мягкое удаление своего сообщения."""
    msg = (
        db.query(InternalChatMessage)
        .filter(
            InternalChatMessage.id == message_id,
            InternalChatMessage.sender_employee_id == employee_id,
        )
        .first()
    )
    if not msg:
        return False
    msg.is_deleted = True
    msg.content = "[Сообщение удалено]"
    db.commit()
    return True


def mark_read(db: Session, chat_id: int, employee_id: int, last_message_id: int):
    """Обновить last_read_message_id для участника."""
    member = (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.chat_id == chat_id,
            InternalChatMember.employee_id == employee_id,
            InternalChatMember.is_active == True,
        )
        .first()
    )
    if member:
        member.last_read_message_id = last_message_id
        db.commit()


def get_unread_count(db: Session, chat_id: int, employee_id: int) -> int:
    """Количество непрочитанных сообщений."""
    member = (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.chat_id == chat_id,
            InternalChatMember.employee_id == employee_id,
        )
        .first()
    )
    if not member:
        return 0
    last_read = member.last_read_message_id or 0
    count = (
        db.query(InternalChatMessage)
        .filter(
            InternalChatMessage.chat_id == chat_id,
            InternalChatMessage.id > last_read,
            InternalChatMessage.is_deleted == False,
            InternalChatMessage.sender_employee_id != employee_id,
            InternalChatMessage.message_type != "system",
        )
        .count()
    )
    return count


def get_first_unread_message_id(db: Session, chat_id: int, employee_id: int) -> Optional[int]:
    """ID первого непрочитанного сообщения для сотрудника (не своего, не системного)."""
    member = (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.chat_id == chat_id,
            InternalChatMember.employee_id == employee_id,
        )
        .first()
    )
    if not member:
        return None
    last_read = member.last_read_message_id or 0
    msg = (
        db.query(InternalChatMessage)
        .filter(
            InternalChatMessage.chat_id == chat_id,
            InternalChatMessage.id > last_read,
            InternalChatMessage.is_deleted == False,  # noqa: E712
            InternalChatMessage.sender_employee_id != employee_id,
            InternalChatMessage.message_type != "system",
        )
        .order_by(InternalChatMessage.id.asc())
        .first()
    )
    return msg.id if msg else None


# =========================
# Список чатов сотрудника
# =========================


def get_employee_chats(db: Session, employee_id: int, chat_type: Optional[str] = None) -> list:
    """Вернуть список активных чатов где сотрудник является участником."""
    q = (
        db.query(InternalChat)
        .join(InternalChatMember, InternalChatMember.chat_id == InternalChat.id)
        .filter(
            InternalChatMember.employee_id == employee_id,
            InternalChatMember.is_active == True,
            InternalChat.is_active == True,
        )
    )
    if chat_type:
        q = q.filter(InternalChat.chat_type == chat_type)
    return q.order_by(InternalChat.created_at.desc()).all()


def get_all_accessible_chats(db: Session, employee_id: int, chat_type: Optional[str] = None) -> list:
    """Все чаты, доступные сотруднику: явный участник + назначен на карточку."""
    # Чаты где сотрудник явно участник
    q_member_ids = (
        db.query(InternalChat.id)
        .join(InternalChatMember, InternalChatMember.chat_id == InternalChat.id)
        .filter(
            InternalChatMember.employee_id == employee_id,
            InternalChatMember.is_active == True,  # noqa: E712
            InternalChat.is_active == True,  # noqa: E712
        )
    )
    if chat_type:
        q_member_ids = q_member_ids.filter(InternalChat.chat_type == chat_type)
    member_chat_ids = {r[0] for r in q_member_ids.all()}

    # Карточки, к которым назначен сотрудник напрямую
    card_ids_fields = [
        r[0]
        for r in db.query(CRMCard.id)
        .filter(
            or_(
                CRMCard.senior_manager_id == employee_id,
                CRMCard.sdp_id == employee_id,
                CRMCard.gap_id == employee_id,
                CRMCard.manager_id == employee_id,
                CRMCard.surveyor_id == employee_id,
            )
        )
        .all()
    ]
    # Карточки через StageExecutor
    card_ids_exec = [r[0] for r in db.query(StageExecutor.crm_card_id).filter(StageExecutor.executor_id == employee_id).all()]
    all_card_ids = list(set(card_ids_fields + card_ids_exec))

    # Чаты для этих карточек (исключаем уже найденные через членство).
    # ВАЖНО: только чаты сотрудников — клиентские чаты доступны только явным участникам.
    extra_ids: set[int] = set()
    if all_card_ids and (chat_type is None or chat_type == "employee"):
        q_card = db.query(InternalChat.id).filter(
            InternalChat.crm_card_id.in_(all_card_ids),
            InternalChat.is_active == True,  # noqa: E712
            InternalChat.id.notin_(member_chat_ids),
            InternalChat.chat_type == "employee",  # только чаты сотрудников
        )
        extra_ids = {r[0] for r in q_card.all()}

    all_ids = member_chat_ids | extra_ids
    if not all_ids:
        return []

    chats = db.query(InternalChat).filter(InternalChat.id.in_(all_ids)).order_by(InternalChat.created_at.desc()).all()
    return chats


def get_card_chat_for_employee(db: Session, crm_card_id: int, chat_type: str, employee_id: int) -> Optional[InternalChat]:
    """Получить чат карточки.

    Чат сотрудников: авто-добавляет сотрудника в участники при первом доступе.
    Чат с клиентом: возвращает только если сотрудник уже явный участник (membership required).
    """
    chat = get_chat_by_card(db, crm_card_id, chat_type)
    if not chat:
        return None

    existing = (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.chat_id == chat.id,
            InternalChatMember.employee_id == employee_id,
            InternalChatMember.is_active == True,  # noqa: E712
        )
        .first()
    )

    if chat_type == "employee":
        # Авто-добавляем сотрудника если ещё не участник
        if not existing:
            emp = db.query(Employee).filter(Employee.id == employee_id).first()
            if emp:
                _add_employee_member(db, chat, emp)
                _add_system_message(db, chat, f"{_get_employee_display_name(emp)} присоединился к чату")
                db.commit()
        return chat
    else:
        # Клиентский чат: только для явных участников
        return chat if existing else None


def get_chat_by_card(db: Session, crm_card_id: int, chat_type: str) -> Optional[InternalChat]:
    """Получить чат карточки по типу."""
    return (
        db.query(InternalChat)
        .filter(
            InternalChat.crm_card_id == crm_card_id,
            InternalChat.chat_type == chat_type,
            InternalChat.is_active == True,
        )
        .first()
    )


def get_chat_by_token(db: Session, token: str) -> Optional[InternalChat]:
    """Найти клиентский чат по токену.

    Поддерживает два типа токенов:
    - InternalChat.client_access_token  — основная ссылка чата
    - InternalChatMember.guest_access_token — персональный токен гостя
    """
    chat = (
        db.query(InternalChat)
        .filter(
            InternalChat.client_access_token == token,
            InternalChat.is_active == True,
        )
        .first()
    )
    if chat:
        return chat
    # Fallback: токен принадлежит конкретному гостю
    member = (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.guest_access_token == token,
            InternalChatMember.is_active == True,
        )
        .first()
    )
    if member:
        return db.query(InternalChat).filter(InternalChat.id == member.chat_id, InternalChat.is_active == True).first()
    return None


def get_guest_by_token(db: Session, guest_token: str) -> Optional[InternalChatMember]:
    """Найти участника-гостя по токену."""
    return (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.guest_access_token == guest_token,
            InternalChatMember.is_active == True,
        )
        .first()
    )


# =========================
# Удаление чата
# =========================


def delete_chat(db: Session, chat_id: int, delete_yd_folder: bool = True):
    """Мягкое удаление чата. Опционально удаляет папку ЯД."""
    chat = db.query(InternalChat).filter(InternalChat.id == chat_id).first()
    if not chat:
        return
    if delete_yd_folder and chat.yandex_folder_path:
        try:
            from yandex_disk_service import get_yandex_disk_service

            yd = get_yandex_disk_service()
            if yd and yd.token:
                yd.delete_file(chat.yandex_folder_path.replace("disk:", ""), permanently=False)
        except Exception as e:
            logger.warning(f"Не удалось удалить папку ЯД {chat.yandex_folder_path}: {e}")
    chat.is_active = False
    db.commit()
