"""
Роутер внутреннего чата Interior Studio CRM.

REST:
  POST   /api/v1/chats/                                — создать чат
  GET    /api/v1/chats/                                — список чатов сотрудника
  GET    /api/v1/chats/{chat_id}                       — детали чата
  DELETE /api/v1/chats/{chat_id}                       — удалить чат

  GET    /api/v1/chats/{chat_id}/messages              — история (limit/offset)
  POST   /api/v1/chats/{chat_id}/messages              — отправить текст
  DELETE /api/v1/chats/{chat_id}/messages/{msg_id}     — удалить своё сообщение
  POST   /api/v1/chats/{chat_id}/messages/{msg_id}/read — отметить прочитанным

  POST   /api/v1/chats/{chat_id}/files                 — загрузить файл/голос/фото
  POST   /api/v1/chats/{chat_id}/members               — добавить участника
  DELETE /api/v1/chats/{chat_id}/members/{member_id}   — убрать участника

  POST   /api/v1/chats/{chat_id}/invite-links          — создать ссылку для клиента
  GET    /api/v1/chats/{chat_id}/invite-links          — список ссылок

  POST   /api/v1/chats/{chat_id}/forward/{target_chat_id} — переслать сообщение

Клиентский доступ (без JWT, только UUID-токен):
  GET    /api/v1/client-chat/{token}                   — получить чат по ссылке
  POST   /api/v1/client-chat/{token}/register          — регистрация гостя (имя + телефон)
  GET    /api/v1/client-chat/{token}/messages          — история
  POST   /api/v1/client-chat/{token}/messages          — отправить сообщение
  POST   /api/v1/client-chat/{token}/files             — загрузить файл

WebSocket:
  WS  /ws/chat/{chat_id}?token=<JWT>                   — сотрудник
  WS  /ws/client-chat/{access_token}                   — клиент
"""

import logging
import os
from typing import List, Optional

from auth import get_current_user
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from permissions import require_permission
from pydantic import BaseModel as PydanticBaseModel
from schemas import (
    ChatInviteLinkResponse,
    FileUploadToDataRequest,
    ForwardRequest,
    GuestRegistration,
    InternalChatCreate,
    InternalChatDetailResponse,
    InternalChatResponse,
    InternalMessageCreate,
    InternalMessageResponse,
)
from services.chat_service import (
    _ensure_yd_folder,
    _get_employee_display_name,
    _message_to_dict,
    add_file_message,
    add_member_to_chat,
    add_text_message,
    create_client_chat,
    create_employee_chat,
    create_invite_link,
    delete_chat,
    delete_message,
    edit_message,
    get_chat_by_card,
    get_chat_by_token,
    get_employee_chats,
    get_guest_by_token,
    get_messages,
    get_unread_count,
    mark_read,
    register_guest,
)
from services.chat_service import (
    manager as ws_manager,
)
from sqlalchemy.orm import Session

from database import (
    Employee,
    InternalChat,
    InternalChatMember,
    InternalChatMessage,
    get_db,
)

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_FILE_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".dwg",
    ".dxf",
    ".zip",
    ".rar",
    ".7z",
    ".txt",
    ".csv",
    ".webm",
    ".ogg",
    ".mp3",
    ".wav",
    ".m4a",  # голосовые
}
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", 50))


# ==============================================================
# REST — основные операции
# ==============================================================


@router.post("/", response_model=InternalChatResponse)
def create_chat(
    data: InternalChatCreate,
    current_user: Employee = Depends(require_permission("chat.employee.manage")),
    db: Session = Depends(get_db),
):
    """Создать чат (сотрудников или с клиентом)."""
    if data.chat_type not in ("employee", "client"):
        raise HTTPException(400, "chat_type должен быть 'employee' или 'client'")

    if data.chat_type == "client":
        _require_perm(current_user, "chat.client.manage", db)
        chat = create_client_chat(
            db,
            data.crm_card_id,
            current_user.id,
            supervision_card_id=data.supervision_card_id,
        )
    else:
        chat = create_employee_chat(
            db,
            data.crm_card_id,
            current_user.id,
            supervision_card_id=data.supervision_card_id,
        )
    return _chat_to_response(db, chat, current_user.id)


@router.get("/", response_model=list[InternalChatResponse])
def list_chats(
    chat_type: Optional[str] = Query(None, description="'employee' или 'client'"),
    crm_card_id: Optional[int] = Query(None),
    current_user: Employee = Depends(require_permission("chat.employee.view")),
    db: Session = Depends(get_db),
):
    """Список чатов текущего сотрудника."""
    chats = get_employee_chats(db, current_user.id, chat_type=chat_type)
    if crm_card_id:
        chats = [c for c in chats if c.crm_card_id == crm_card_id]
    return [_chat_to_response(db, c, current_user.id) for c in chats]


@router.get("/{chat_id}", response_model=InternalChatDetailResponse)
def get_chat(
    chat_id: int,
    current_user: Employee = Depends(require_permission("chat.employee.view")),
    db: Session = Depends(get_db),
):
    """Детали чата с участниками и последними 50 сообщениями."""
    chat = _get_chat_or_404(db, chat_id)
    _check_member(db, chat_id, current_user.id)
    msgs = get_messages(db, chat_id, limit=50)
    return _chat_to_detail_response(db, chat, current_user.id, msgs)


@router.delete("/{chat_id}")
def remove_chat(
    chat_id: int,
    current_user: Employee = Depends(require_permission("chat.employee.manage")),
    db: Session = Depends(get_db),
):
    """Удалить чат (мягкое удаление + папка ЯД в корзину)."""
    chat = _get_chat_or_404(db, chat_id)
    if chat.chat_type == "client":
        _require_perm(current_user, "chat.client.manage", db)
    delete_chat(db, chat_id, delete_yd_folder=True)
    return {"status": "ok"}


# ==============================================================
# REST — сообщения
# ==============================================================


@router.get("/{chat_id}/messages", response_model=list[InternalMessageResponse])
def list_messages(
    chat_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Employee = Depends(require_permission("chat.employee.view")),
    db: Session = Depends(get_db),
):
    _get_chat_or_404(db, chat_id)
    _check_member(db, chat_id, current_user.id)
    msgs = get_messages(db, chat_id, limit=limit, offset=offset)
    return msgs


@router.post("/{chat_id}/messages", response_model=InternalMessageResponse)
async def send_message(
    chat_id: int,
    data: InternalMessageCreate,
    current_user: Employee = Depends(require_permission("chat.employee.send")),
    db: Session = Depends(get_db),
):
    _get_chat_or_404(db, chat_id)
    _check_member(db, chat_id, current_user.id)
    msg = add_text_message(
        db,
        chat_id,
        data.content,
        sender_employee_id=current_user.id,
    )
    # Рассылка по WebSocket
    await ws_manager.broadcast(
        chat_id,
        {
            "type": "new_message",
            "message": _message_to_dict(msg),
        },
    )
    return msg


@router.delete("/{chat_id}/messages/{msg_id}")
async def remove_message(
    chat_id: int,
    msg_id: int,
    current_user: Employee = Depends(require_permission("chat.employee.send")),
    db: Session = Depends(get_db),
):
    ok = delete_message(db, msg_id, current_user.id)
    if not ok:
        raise HTTPException(403, "Нет доступа или сообщение не найдено")
    await ws_manager.broadcast(
        chat_id,
        {
            "type": "message_deleted",
            "message_id": msg_id,
        },
    )
    return {"status": "ok"}


class EditMessageBody(PydanticBaseModel):
    content: str


@router.patch("/{chat_id}/messages/{msg_id}", response_model=InternalMessageResponse)
async def edit_message_endpoint(
    chat_id: int,
    msg_id: int,
    body: EditMessageBody,
    current_user: Employee = Depends(require_permission("chat.employee.send")),
    db: Session = Depends(get_db),
):
    """Редактировать своё текстовое сообщение."""
    msg = edit_message(db, msg_id, current_user.id, body.content)
    if not msg:
        raise HTTPException(403, "Нет доступа или сообщение не найдено")
    await ws_manager.broadcast(
        chat_id,
        {"type": "message_updated", "message": _message_to_dict(msg)},
    )
    return msg


# Допустимые назначения при копировании файла в поля CRMCard
_CARD_FILE_DESTINATIONS: dict[str, str] = {
    # Договор
    "contract_file_yandex_path": "Договор",
    "additional_agreement_yandex_path": "Договор",
    # Акты (неподписанные)
    "act_planning_yandex_path": "Акты",
    "act_concept_yandex_path": "Акты",
    "act_final_yandex_path": "Акты",
    "info_letter_yandex_path": "Акты",
    # Акты (подписанные)
    "act_planning_signed_yandex_path": "Акты подписанные",
    "act_concept_signed_yandex_path": "Акты подписанные",
    "act_final_signed_yandex_path": "Акты подписанные",
    "info_letter_signed_yandex_path": "Акты подписанные",
    # Чеки
    "advance_receipt_yandex_path": "Чеки",
    "additional_receipt_yandex_path": "Чеки",
    "third_receipt_yandex_path": "Чеки",
    # Общие данные
    "tech_task_yandex_path": "ТЗ",
    "photo_documentation_yandex_path": "Фотофиксация",
    "references_yandex_path": "Референсы",
    "measurement_yandex_path": "Замер",
}

# Назначения в файлы стадий (ProjectFile), ключ → имя стадии
_STAGE_FILE_DESTINATIONS: dict[str, str] = {
    "stage_1": "Стадия 1",
    "stage_2": "Стадия 2",
    "stage_3": "Стадия 3",
}


class CopyToCardBody(PydanticBaseModel):
    crm_card_id: int
    destination: str  # ключ поля CRMCard или stage_1/stage_2/stage_3


@router.post("/{chat_id}/messages/{msg_id}/copy-to-card")
async def copy_message_file_to_card(
    chat_id: int,
    msg_id: int,
    body: CopyToCardBody,
    current_user: Employee = Depends(require_permission("chat.employee.send")),
    db: Session = Depends(get_db),
):
    """Скопировать файл из сообщения в данные карточки CRM или ProjectFile."""
    is_stage = body.destination in _STAGE_FILE_DESTINATIONS
    if not is_stage and body.destination not in _CARD_FILE_DESTINATIONS:
        raise HTTPException(400, f"Неизвестное назначение: {body.destination}")

    msg = (
        db.query(InternalChatMessage)
        .filter(
            InternalChatMessage.id == msg_id,
            InternalChatMessage.chat_id == chat_id,
        )
        .first()
    )
    if not msg or not msg.yandex_path:
        raise HTTPException(404, "Файл сообщения не найден")

    from database import Contract, CRMCard, ProjectFile

    card = db.query(CRMCard).filter(CRMCard.id == body.crm_card_id).first()
    if not card:
        raise HTTPException(404, "Карточка не найдена")
    if not card.contract_id:
        raise HTTPException(400, "У карточки нет привязанного договора")

    # Поля назначения (yandex_path, акты, чеки и т.д.) хранятся в Contract, не в CRMCard
    contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
    if not contract:
        raise HTTPException(404, "Договор карточки не найден")
    if not contract.yandex_folder_path:
        raise HTTPException(400, "У договора нет папки на Яндекс.Диске")

    try:
        from yandex_disk_service import get_yandex_disk_service

        yd = get_yandex_disk_service()
        if not yd or not yd.token:
            raise HTTPException(503, "Яндекс.Диск не настроен")

        if is_stage:
            subfolder = _STAGE_FILE_DESTINATIONS[body.destination]
        else:
            subfolder = _CARD_FILE_DESTINATIONS[body.destination]

        card_root = contract.yandex_folder_path.replace("disk:", "").rstrip("/")
        file_name = os.path.basename(msg.yandex_path.replace("disk:", ""))
        dest_clean = f"{card_root}/{subfolder}/{file_name}"
        dest_yd = f"disk:{dest_clean}"

        _ensure_yd_folder(f"disk:{card_root}/{subfolder}")
        yd.copy_file(msg.yandex_path, dest_yd, overwrite=True)
        public_url = yd.get_public_link(dest_yd) or ""
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка копирования файла в карточку: {e}")
        raise HTTPException(500, "Ошибка копирования на Яндекс.Диске")

    if is_stage:
        ext = os.path.splitext(file_name)[1].lower()
        file_type = "image" if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"} else "pdf" if ext == ".pdf" else "file"
        stage_name = _STAGE_FILE_DESTINATIONS[body.destination]
        last = db.query(ProjectFile).filter(ProjectFile.contract_id == contract.id, ProjectFile.stage == stage_name).order_by(ProjectFile.variation.desc()).first()
        variation = (last.variation + 1) if last else 1
        pf = ProjectFile(
            contract_id=contract.id,
            stage=stage_name,
            file_type=file_type,
            yandex_path=dest_yd,
            file_name=file_name,
            public_link=public_url,
            variation=variation,
        )
        db.add(pf)
        db.commit()
    else:
        # Поля хранятся в Contract (contract_file_yandex_path, act_planning_yandex_path и т.д.)
        setattr(contract, body.destination, dest_yd)
        db.commit()

    return {"status": "ok", "yandex_path": dest_yd, "file_url": public_url}


@router.post("/{chat_id}/messages/{msg_id}/read")
def read_message(
    chat_id: int,
    msg_id: int,
    current_user: Employee = Depends(require_permission("chat.employee.view")),
    db: Session = Depends(get_db),
):
    mark_read(db, chat_id, current_user.id, msg_id)
    return {"status": "ok"}


# ==============================================================
# REST — файлы
# ==============================================================


@router.post("/{chat_id}/files", response_model=InternalMessageResponse)
async def upload_file(
    chat_id: int,
    file: UploadFile = File(...),
    message_type: str = Form("file"),  # file / image / voice
    current_user: Employee = Depends(require_permission("chat.employee.send")),
    db: Session = Depends(get_db),
):
    """Загрузить файл/изображение/голос на ЯД и сохранить как сообщение."""
    chat = _get_chat_or_404(db, chat_id)
    _check_member(db, chat_id, current_user.id)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext and ext not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(400, f"Тип файла '{ext}' не разрешён")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"Файл превышает {MAX_FILE_SIZE_MB} МБ")

    # Путь: disk:{contract_folder}/Чат .../filename
    safe_name = os.path.basename(file.filename or "unnamed")
    folder_clean = chat.yandex_folder_path.replace("disk:", "").rstrip("/") if chat.yandex_folder_path else f"/CRM/Chats/{chat_id}"
    yd_path = f"{folder_clean}/{safe_name}"

    try:
        from yandex_disk_service import get_yandex_disk_service

        yd = get_yandex_disk_service()
        if not yd or not yd.token:
            raise HTTPException(503, "Яндекс.Диск не настроен")
        _ensure_yd_folder(f"disk:{folder_clean}")
        yd.upload_file_from_bytes(file_bytes, yd_path)
        public_url = yd.get_public_link(yd_path) or ""
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка загрузки файла чата на ЯД: {e}")
        raise HTTPException(500, "Ошибка загрузки на Яндекс.Диск")

    msg = add_file_message(
        db,
        chat_id,
        file_url=public_url,
        file_name=safe_name,
        yandex_path=f"disk:{yd_path}",
        file_size=len(file_bytes),
        message_type=message_type,
        sender_employee_id=current_user.id,
    )
    await ws_manager.broadcast(
        chat_id,
        {
            "type": "new_message",
            "message": _message_to_dict(msg),
        },
    )
    return msg


# ==============================================================
# REST — участники
# ==============================================================


class AddMemberBody(PydanticBaseModel):
    employee_id: int


@router.post("/{chat_id}/members")
async def add_member(
    chat_id: int,
    body: AddMemberBody,
    current_user: Employee = Depends(require_permission("chat.employee.manage")),
    db: Session = Depends(get_db),
):
    _get_chat_or_404(db, chat_id)
    try:
        member = add_member_to_chat(db, chat_id, body.employee_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    # Рассылаем системное сообщение (созданное add_member_to_chat) через WS
    sys_msg = db.query(InternalChatMessage).filter(InternalChatMessage.chat_id == chat_id, InternalChatMessage.message_type == "system").order_by(InternalChatMessage.id.desc()).first()
    if sys_msg:
        await ws_manager.broadcast(chat_id, {"type": "new_message", "message": _message_to_dict(sys_msg)})
    await ws_manager.broadcast(chat_id, {"type": "member_added", "employee_id": body.employee_id, "member_id": member.id})
    return {"status": "ok", "member_id": member.id}


@router.delete("/{chat_id}/members/{member_id}")
async def remove_member(
    chat_id: int,
    member_id: int,
    current_user: Employee = Depends(require_permission("chat.employee.manage")),
    db: Session = Depends(get_db),
):
    member = (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.id == member_id,
            InternalChatMember.chat_id == chat_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(404, "Участник не найден")
    # Имя участника для системного сообщения
    display_name = member.guest_name or ""
    if member.employee_id:
        emp = db.query(Employee).filter(Employee.id == member.employee_id).first()
        if emp:
            display_name = _get_employee_display_name(emp)
    member.is_active = False
    # Создаём системное сообщение об удалении
    sys_msg = InternalChatMessage(
        chat_id=chat_id,
        sender_display_name="Система",
        message_type="system",
        content=f"{display_name or 'Участник'} удалён из чата",
    )
    db.add(sys_msg)
    db.commit()
    db.refresh(sys_msg)
    await ws_manager.broadcast(chat_id, {"type": "new_message", "message": _message_to_dict(sys_msg)})
    await ws_manager.broadcast(chat_id, {"type": "member_removed", "member_id": member_id})
    return {"status": "ok"}


# ==============================================================
# REST — ссылки для клиентов
# ==============================================================


@router.post("/{chat_id}/invite-links", response_model=ChatInviteLinkResponse)
def create_link(
    chat_id: int,
    current_user: Employee = Depends(require_permission("chat.client.manage")),
    db: Session = Depends(get_db),
):
    """Создать новую UUID-ссылку для представителя заказчика."""
    chat = _get_chat_or_404(db, chat_id)
    if chat.chat_type != "client":
        raise HTTPException(400, "Только для чатов с клиентами")
    member = create_invite_link(db, chat_id)
    base_url = os.environ.get("APP_BASE_URL", "https://crm.interior-studio.ru")
    return ChatInviteLinkResponse(
        token=member.guest_access_token,
        url=f"{base_url}/c/{member.guest_access_token}",
        guest_name=member.guest_name,
        guest_phone=member.guest_phone,
        created_at=member.joined_at,
    )


@router.get("/{chat_id}/invite-links", response_model=list[ChatInviteLinkResponse])
def list_links(
    chat_id: int,
    current_user: Employee = Depends(require_permission("chat.client.manage")),
    db: Session = Depends(get_db),
):
    _get_chat_or_404(db, chat_id)
    members = (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.chat_id == chat_id,
            InternalChatMember.member_type == "client_guest",
            InternalChatMember.is_active == True,
        )
        .all()
    )
    base_url = os.environ.get("APP_BASE_URL", "https://crm.interior-studio.ru")
    return [
        ChatInviteLinkResponse(
            token=m.guest_access_token,
            url=f"{base_url}/c/{m.guest_access_token}",
            guest_name=m.guest_name,
            guest_phone=m.guest_phone,
            created_at=m.joined_at,
        )
        for m in members
    ]


# ==============================================================
# REST — пересылка
# ==============================================================


@router.post("/{chat_id}/forward/{target_chat_id}")
async def forward_message(
    chat_id: int,
    target_chat_id: int,
    data: ForwardRequest,
    current_user: Employee = Depends(require_permission("chat.employee.send")),
    db: Session = Depends(get_db),
):
    """Переслать сообщение из одного чата в другой."""
    _get_chat_or_404(db, chat_id)
    _get_chat_or_404(db, target_chat_id)
    _check_member(db, chat_id, current_user.id)
    # Проверяем только членство в исходном чате; целевой может быть клиентским

    src_msg = (
        db.query(InternalChatMessage)
        .filter(
            InternalChatMessage.id == data.msg_id,
            InternalChatMessage.chat_id == chat_id,
            InternalChatMessage.is_deleted == False,
        )
        .first()
    )
    if not src_msg:
        raise HTTPException(404, "Сообщение не найдено")

    fwd_display = f"{_get_employee_display_name(current_user)} (переслано)"
    if src_msg.message_type == "text":
        new_msg = add_text_message(
            db,
            target_chat_id,
            content=src_msg.content or "",
            sender_employee_id=current_user.id,
            sender_display_name=fwd_display,
        )
    else:
        new_msg = add_file_message(
            db,
            target_chat_id,
            file_url=src_msg.file_url or "",
            file_name=src_msg.file_name or "",
            yandex_path=src_msg.yandex_path or "",
            file_size=src_msg.file_size,
            message_type=src_msg.message_type,
            sender_employee_id=current_user.id,
            sender_display_name=fwd_display,
        )

    await ws_manager.broadcast(
        target_chat_id,
        {
            "type": "new_message",
            "message": _message_to_dict(new_msg),
        },
    )
    return {"status": "ok", "new_message_id": new_msg.id}


# ==============================================================
# Вспомогательные функции
# ==============================================================


def _get_chat_or_404(db: Session, chat_id: int) -> InternalChat:
    chat = (
        db.query(InternalChat)
        .filter(
            InternalChat.id == chat_id,
            InternalChat.is_active == True,
        )
        .first()
    )
    if not chat:
        raise HTTPException(404, "Чат не найден")
    return chat


def _check_member(db: Session, chat_id: int, employee_id: int):
    member = (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.chat_id == chat_id,
            InternalChatMember.employee_id == employee_id,
            InternalChatMember.is_active == True,
        )
        .first()
    )
    if not member:
        raise HTTPException(403, "Вы не являетесь участником этого чата")


def _require_perm(user: Employee, perm: str, db: Session):
    from permissions import get_employee_permissions

    perms = get_employee_permissions(user.id, db)
    if perm not in perms:
        raise HTTPException(403, f"Нет права: {perm}")


def _chat_to_response(db: Session, chat: InternalChat, employee_id: int) -> InternalChatResponse:
    # Последнее сообщение
    last_msg = (
        db.query(InternalChatMessage)
        .filter(
            InternalChatMessage.chat_id == chat.id,
            InternalChatMessage.is_deleted == False,
        )
        .order_by(InternalChatMessage.created_at.desc())
        .first()
    )
    member_count = (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.chat_id == chat.id,
            InternalChatMember.is_active == True,
        )
        .count()
    )
    unread = get_unread_count(db, chat.id, employee_id)

    return InternalChatResponse(
        id=chat.id,
        chat_type=chat.chat_type,
        crm_card_id=chat.crm_card_id,
        supervision_card_id=chat.supervision_card_id,
        contract_id=chat.contract_id,
        title=chat.title,
        yandex_folder_path=chat.yandex_folder_path,
        client_access_token=chat.client_access_token,
        created_by=chat.created_by,
        created_at=chat.created_at,
        is_active=chat.is_active,
        last_message=last_msg.content if last_msg and last_msg.message_type == "text" else (f"[{last_msg.message_type}]" if last_msg else None),
        last_message_at=last_msg.created_at if last_msg else None,
        unread_count=unread,
        member_count=member_count,
    )


def _chat_to_detail_response(db: Session, chat: InternalChat, employee_id: int, msgs: list) -> InternalChatDetailResponse:
    base = _chat_to_response(db, chat, employee_id)
    members = (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.chat_id == chat.id,
            InternalChatMember.is_active == True,
        )
        .all()
    )
    from schemas import InternalChatMemberResponse

    member_responses = []
    for m in members:
        display = m.guest_name or ""
        role_in_project = None
        if m.employee_id:
            emp = db.query(Employee).filter(Employee.id == m.employee_id).first()
            if emp:
                display = _get_employee_display_name(emp)
                role_in_project = emp.position or emp.secondary_position
        elif m.member_type == "guest":
            role_in_project = "Клиент"
        member_responses.append(
            InternalChatMemberResponse(
                id=m.id,
                member_type=m.member_type,
                employee_id=m.employee_id,
                guest_name=m.guest_name,
                guest_phone=m.guest_phone,
                joined_at=m.joined_at,
                is_active=m.is_active,
                display_name=display,
                role_in_project=role_in_project,
            )
        )
    return InternalChatDetailResponse(
        **base.model_dump(),
        members=member_responses,
        messages=msgs,
    )
