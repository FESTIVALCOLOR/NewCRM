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
    ForwardGroupRequest,
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
    get_all_accessible_chats,
    get_batch_last_messages,
    get_batch_member_counts,
    get_batch_reactions,
    get_batch_unread_counts,
    get_card_chat_for_employee,
    get_chat_by_card,
    get_chat_by_token,
    get_employee_chats,
    get_first_unread_message_id,
    get_guest_by_token,
    get_messages,
    get_unread_count,
    mark_read,
    pin_message,
    register_guest,
    toggle_reaction,
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

# Маппинг db_stage → префикс stage_name в StageWorkflowState
_DB_STAGE_TO_WF_PREFIX = {
    "stage1": "Стадия 1",
    "stage2_concept": "Стадия 2",
    "stage3": "Стадия 3",
}

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
    """Список чатов текущего сотрудника.

    Если передан crm_card_id: возвращает чат карточки напрямую (без фильтра по членству),
    для чата сотрудников — авто-добавляет текущего сотрудника как участника.
    Иначе: возвращает все доступные чаты (участник ИЛИ назначен на карточку).
    """
    if crm_card_id and chat_type:
        chat = get_card_chat_for_employee(db, crm_card_id, chat_type, current_user.id)
        if not chat:
            return []
        return [_chat_to_response(db, chat, current_user.id)]

    chats = get_all_accessible_chats(db, current_user.id, chat_type=chat_type)
    if crm_card_id:
        chats = [c for c in chats if c.crm_card_id == crm_card_id]

    chat_ids = [c.id for c in chats]
    last_msgs = get_batch_last_messages(db, chat_ids)
    member_counts = get_batch_member_counts(db, chat_ids)
    unread_counts = get_batch_unread_counts(db, chat_ids, current_user.id)

    return [_chat_to_response(db, c, current_user.id, last_msgs, member_counts, unread_counts) for c in chats]


@router.get("/{chat_id}", response_model=InternalChatDetailResponse)
def get_chat(
    chat_id: int,
    current_user: Employee = Depends(require_permission("chat.employee.view")),
    db: Session = Depends(get_db),
):
    """Детали чата с участниками и последними 150 сообщениями."""
    chat = _get_chat_or_404(db, chat_id)
    _check_member(db, chat_id, current_user.id)
    msgs = get_messages(db, chat_id, limit=150)
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
    limit: int = Query(150, ge=1, le=500),
    offset: int = Query(0, ge=0),
    before_id: Optional[int] = Query(None, ge=1),
    current_user: Employee = Depends(require_permission("chat.employee.view")),
    db: Session = Depends(get_db),
):
    _get_chat_or_404(db, chat_id)
    _check_member(db, chat_id, current_user.id)
    msgs = get_messages(db, chat_id, limit=limit, offset=offset, before_id=before_id)
    msg_dicts = [_message_to_dict(m) for m in msgs]
    if msg_dicts:
        reactions_map = get_batch_reactions(db, [d["id"] for d in msg_dicts])
        for d in msg_dicts:
            d["reactions"] = reactions_map.get(d["id"], {})
    return msg_dicts


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
        reply_to_id=getattr(data, "reply_to_id", None),
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


@router.get("/{chat_id}/messages/search", response_model=list[InternalMessageResponse])
def search_messages(
    chat_id: int,
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(20, ge=1, le=100),
    current_user: Employee = Depends(require_permission("chat.employee.view")),
    db: Session = Depends(get_db),
):
    """Полнотекстовый поиск по сообщениям чата (PostgreSQL ilike)."""
    _get_chat_or_404(db, chat_id)
    _check_member(db, chat_id, current_user.id)
    msgs = (
        db.query(InternalChatMessage)
        .filter(
            InternalChatMessage.chat_id == chat_id,
            InternalChatMessage.is_deleted == False,
            InternalChatMessage.message_type == "text",
            InternalChatMessage.content.ilike(f"%{q}%"),
        )
        .order_by(InternalChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(msgs))


class LinkProjectFileRequest(PydanticBaseModel):
    yandex_path: str
    file_name: str
    public_link: Optional[str] = None
    message_type: str = "file"
    group_id: Optional[str] = None


@router.post("/{chat_id}/messages/from-project-file", response_model=InternalMessageResponse)
async def link_project_file_to_chat(
    chat_id: int,
    body: LinkProjectFileRequest,
    current_user: Employee = Depends(require_permission("chat.employee.send")),
    db: Session = Depends(get_db),
):
    """Создать сообщение-ссылку на существующий файл проекта (без повторной загрузки байт)."""
    _get_chat_or_404(db, chat_id)
    _check_member(db, chat_id, current_user.id)

    public_url = body.public_link or ""
    if not public_url:
        yd_path_clean = body.yandex_path.removeprefix("disk:")
        try:
            from yandex_disk_service import get_yandex_disk_service

            yd = get_yandex_disk_service()
            if yd and yd.token:
                public_url = yd.get_public_link(yd_path_clean) or ""
        except Exception:
            pass

    msg = add_file_message(
        db,
        chat_id,
        file_url=public_url,
        file_name=body.file_name,
        yandex_path=body.yandex_path,
        file_size=None,
        message_type=body.message_type,
        sender_employee_id=current_user.id,
        group_id=body.group_id or None,
    )
    await ws_manager.broadcast(chat_id, {"type": "new_message", "message": _message_to_dict(msg)})
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

# Назначения в файлы стадий (ProjectFile)
# yd_folder — подпапка в папке договора на ЯД (точно как в десктопной версии)
# db_stage  — значение поля ProjectFile.stage (должно совпадать с ContractDetailPage)
# Только stage_2 / stage_2_concept использует подпапку "Вариация N" (как в get_stage_folder_path)
_STAGE_FILE_DESTINATIONS: dict[str, dict[str, str]] = {
    "stage_1": {"yd_folder": "1 стадия - Планировочное решение", "db_stage": "stage1"},
    "stage_2": {"yd_folder": "2 стадия - Концепция дизайна/Концепция-коллажи", "db_stage": "stage2_concept"},
    "stage_3": {"yd_folder": "3 стадия - Чертежный проект", "db_stage": "stage3"},
    # правки (lowercase, как в десктопе) — без подпапки "Вариация N"
    "stage_1_revisions": {"yd_folder": "1 стадия - Планировочное решение/правки", "db_stage": "stage1"},
    "stage_2_revisions": {"yd_folder": "2 стадия - Концепция дизайна/Концепция-коллажи/правки", "db_stage": "stage2_concept"},
    "stage_3_revisions": {"yd_folder": "3 стадия - Чертежный проект/правки", "db_stage": "stage3"},
}

# Только эти назначения добавляют "Вариация N" подпапку на ЯД (как в desktopver. get_stage_folder_path)
_STAGES_WITH_VARIATION_FOLDER = {"stage_2"}


class CopyToCardBody(PydanticBaseModel):
    crm_card_id: int
    destination: str  # ключ поля Contract или stage_1/stage_2/stage_3
    variation: Optional[int] = None  # None = auto-increment, число = конкретная вариация


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

        card_root = contract.yandex_folder_path.replace("disk:", "").rstrip("/")
        file_name = os.path.basename(msg.yandex_path.replace("disk:", ""))

        if is_stage:
            info = _STAGE_FILE_DESTINATIONS[body.destination]
            base_subfolder = info["yd_folder"]
            stage_name = info["db_stage"]
            is_revisions = body.destination.endswith("_revisions")
            uses_var_folder = body.destination in _STAGES_WITH_VARIATION_FOLDER

            # Определяем номер вариации для ProjectFile
            if body.variation is not None:
                variation = body.variation
            else:
                last = db.query(ProjectFile).filter(ProjectFile.contract_id == contract.id, ProjectFile.stage == stage_name).order_by(ProjectFile.variation.desc()).first()
                variation = (last.variation + 1) if last else 1

            # Физическая подпапка на ЯД: только stage_2 добавляет "Вариация N" (не правки)
            if uses_var_folder and not is_revisions:
                subfolder = f"{base_subfolder}/Вариация {variation}"
            else:
                subfolder = base_subfolder
        else:
            subfolder = _CARD_FILE_DESTINATIONS[body.destination]

        dest_clean = f"{card_root}/{subfolder}/{file_name}"
        dest_yd = f"disk:{dest_clean}"

        # Создаём все промежуточные папки (рекурсивно)
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

        # Для правок: обновляем StageWorkflowState → revision_file_path + status='revision'
        if is_revisions:
            from database import StageWorkflowState

            wf_prefix = _DB_STAGE_TO_WF_PREFIX.get(stage_name, "")
            if wf_prefix:
                wf = (
                    db.query(StageWorkflowState)
                    .filter(
                        StageWorkflowState.crm_card_id == card.id,
                        StageWorkflowState.stage_name.like(f"{wf_prefix}%"),
                    )
                    .order_by(StageWorkflowState.id.desc())
                    .first()
                )
                if wf:
                    wf.revision_file_path = dest_yd
                    if wf.status != "revision":
                        wf.status = "revision"

        db.commit()
    else:
        # Поля хранятся в Contract (contract_file_yandex_path, act_planning_yandex_path и т.д.)
        setattr(contract, body.destination, dest_yd)
        db.commit()

    return {"status": "ok", "yandex_path": dest_yd, "file_url": public_url}


@router.get("/{chat_id}/card-stage-variations")
def get_card_stage_variations(
    chat_id: int,
    crm_card_id: int = Query(...),
    destination: str = Query(...),
    current_user: Employee = Depends(require_permission("chat.employee.send")),
    db: Session = Depends(get_db),
):
    """Получить существующие вариации для стадии карточки CRM."""
    if destination not in _STAGE_FILE_DESTINATIONS:
        return {"variations": [], "next_variation": 1}
    from database import CRMCard, ProjectFile

    card = db.query(CRMCard).filter(CRMCard.id == crm_card_id).first()
    if not card or not card.contract_id:
        return {"variations": [], "next_variation": 1}
    stage_name = _STAGE_FILE_DESTINATIONS[destination]["db_stage"]
    rows = (
        db.query(ProjectFile)
        .filter(
            ProjectFile.contract_id == card.contract_id,
            ProjectFile.stage == stage_name,
        )
        .order_by(ProjectFile.variation.asc(), ProjectFile.id.asc())
        .all()
    )
    var_dict: dict[int, list[str]] = {}
    for pf in rows:
        v = pf.variation or 1
        if v not in var_dict:
            var_dict[v] = []
        var_dict[v].append(pf.file_name or "")
    next_var = (max(var_dict.keys()) + 1) if var_dict else 1
    return {
        "variations": [{"variation": v, "files": fnames} for v, fnames in sorted(var_dict.items())],
        "next_variation": next_var,
    }


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
    group_id: Optional[str] = Form(None),  # UUID медиа-группы (несколько изображений за раз)
    caption: Optional[str] = Form(None),  # Подпись к изображению/файлу
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

    # Путь: disk:{contract_folder}/Чат .../[group_id[:8]/]filename
    safe_name = os.path.basename(file.filename or "unnamed")
    folder_clean = chat.yandex_folder_path.replace("disk:", "").rstrip("/") if chat.yandex_folder_path else f"/CRM/Chats/{chat_id}"
    # Если файл часть медиа-группы — создаём подпапку по первым 8 символам group_id
    if group_id:
        target_folder = f"{folder_clean}/{group_id[:8]}"
    else:
        target_folder = folder_clean
    yd_path = f"{target_folder}/{safe_name}"

    try:
        from yandex_disk_service import get_yandex_disk_service

        yd = get_yandex_disk_service()
        if not yd or not yd.token:
            raise HTTPException(503, "Яндекс.Диск не настроен")
        _ensure_yd_folder(f"disk:{target_folder}")
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
        group_id=group_id or None,
        content=caption.strip() if caption else None,
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
# REST — публичная ссылка на папку галереи
# ==============================================================


@router.post("/{chat_id}/messages/{msg_id}/gallery-link")
async def get_gallery_public_link(
    chat_id: int,
    msg_id: int,
    current_user: Employee = Depends(require_permission("chat.employee.send")),
    db: Session = Depends(get_db),
):
    """Опубликовать папку галереи на ЯД и вернуть публичную ссылку."""
    _get_chat_or_404(db, chat_id)
    msg = (
        db.query(InternalChatMessage)
        .filter(
            InternalChatMessage.id == msg_id,
            InternalChatMessage.chat_id == chat_id,
        )
        .first()
    )
    if not msg or not msg.yandex_path:
        raise HTTPException(404, "Сообщение не найдено или нет пути на ЯД")

    clean = msg.yandex_path.replace("disk:", "").rstrip("/")
    folder_path = "disk:" + clean.rsplit("/", 1)[0]

    try:
        from yandex_disk_service import get_yandex_disk_service

        yd = get_yandex_disk_service()
        if not yd or not yd.token:
            raise HTTPException(503, "Яндекс.Диск не настроен")
        public_url = yd.get_public_link(folder_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка публикации папки галереи: {e}")
        raise HTTPException(500, "Ошибка публикации папки на Яндекс.Диск")

    return {"public_url": public_url}


# ==============================================================
# REST — закрепление сообщения
# ==============================================================


@router.post("/{chat_id}/messages/{msg_id}/pin")
async def pin_message_endpoint(
    chat_id: int,
    msg_id: int,
    current_user: Employee = Depends(require_permission("chat.employee.send")),
    db: Session = Depends(get_db),
):
    """Закрепить / открепить сообщение (toggle). Один чат — одно закреплённое сообщение."""
    _check_member(db, chat_id, current_user.id)
    result = pin_message(db, chat_id, msg_id)
    if result is None:
        raise HTTPException(404, "Сообщение не найдено")
    # Уведомить остальных участников
    await ws_manager.broadcast(
        chat_id,
        {
            "type": "message_pinned",
            "message_id": msg_id,
            "pinned": result["pinned"],
            "message": result.get("message"),
        },
    )
    return result


class ReactBody(PydanticBaseModel):
    emoji: str


@router.post("/{chat_id}/messages/{msg_id}/react")
async def react_to_message(
    chat_id: int,
    msg_id: int,
    body: ReactBody,
    current_user: Employee = Depends(require_permission("chat.employee.send")),
    db: Session = Depends(get_db),
):
    """Добавить / убрать emoji-реакцию (toggle). Рассылает reaction_updated через WS."""
    _check_member(db, chat_id, current_user.id)
    msg = (
        db.query(InternalChatMessage)
        .filter(InternalChatMessage.id == msg_id, InternalChatMessage.chat_id == chat_id, InternalChatMessage.is_deleted == False)  # noqa: E712
        .first()
    )
    if not msg:
        raise HTTPException(404, "Сообщение не найдено")
    reactions = toggle_reaction(db, msg_id, body.emoji, employee_id=current_user.id)
    await ws_manager.broadcast(chat_id, {"type": "reaction_updated", "message_id": msg_id, "reactions": reactions})
    return {"reactions": reactions}


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


@router.delete("/{chat_id}/invite-links/{member_id}")
async def revoke_invite_link(
    chat_id: int,
    member_id: int,
    current_user: Employee = Depends(require_permission("chat.client.manage")),
    db: Session = Depends(get_db),
):
    """Аннулировать доступ клиента (гостя) к чату."""
    member = (
        db.query(InternalChatMember)
        .filter(
            InternalChatMember.id == member_id,
            InternalChatMember.chat_id == chat_id,
            InternalChatMember.member_type == "client_guest",
        )
        .first()
    )
    if not member:
        raise HTTPException(404, "Участник не найден")
    member.is_active = False
    display_name = member.guest_name or "Клиент"
    sys_msg = InternalChatMessage(
        chat_id=chat_id,
        sender_display_name="Система",
        message_type="system",
        content=f"Доступ клиента {display_name} аннулирован",
    )
    db.add(sys_msg)
    db.commit()
    db.refresh(sys_msg)
    await ws_manager.broadcast(chat_id, {"type": "new_message", "message": _message_to_dict(sys_msg)})
    await ws_manager.broadcast(chat_id, {"type": "member_removed", "member_id": member_id})
    return {"status": "ok"}


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

    # Если пересылаемое сообщение — ответ на другое, сначала пересылаем оригинал
    fwd_reply_to_id = None
    if src_msg.reply_to_id:
        reply_src = (
            db.query(InternalChatMessage)
            .filter(
                InternalChatMessage.id == src_msg.reply_to_id,
                InternalChatMessage.is_deleted == False,
            )
            .first()
        )
        if reply_src:
            if reply_src.message_type == "text":
                fwd_reply = add_text_message(
                    db,
                    target_chat_id,
                    content=reply_src.content or "",
                    sender_employee_id=current_user.id,
                    sender_display_name=fwd_display,
                )
            else:
                fwd_reply = add_file_message(
                    db,
                    target_chat_id,
                    file_url=reply_src.file_url or "",
                    file_name=reply_src.file_name or "",
                    yandex_path=reply_src.yandex_path or "",
                    file_size=reply_src.file_size,
                    message_type=reply_src.message_type,
                    sender_employee_id=current_user.id,
                    sender_display_name=fwd_display,
                )
            fwd_reply_to_id = fwd_reply.id
            await ws_manager.broadcast(
                target_chat_id,
                {"type": "new_message", "message": _message_to_dict(fwd_reply)},
            )

    if src_msg.message_type == "text":
        new_msg = add_text_message(
            db,
            target_chat_id,
            content=src_msg.content or "",
            sender_employee_id=current_user.id,
            sender_display_name=fwd_display,
            reply_to_id=fwd_reply_to_id,
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
            reply_to_id=fwd_reply_to_id,
        )

    await ws_manager.broadcast(
        target_chat_id,
        {"type": "new_message", "message": _message_to_dict(new_msg)},
    )
    return {"status": "ok", "new_message_id": new_msg.id}


@router.post("/{chat_id}/forward-group/{target_chat_id}")
async def forward_message_group(
    chat_id: int,
    target_chat_id: int,
    data: ForwardGroupRequest,
    current_user: Employee = Depends(require_permission("chat.employee.send")),
    db: Session = Depends(get_db),
):
    """Переслать группу сообщений (галерею) как единую медиа-группу."""
    _get_chat_or_404(db, chat_id)
    _get_chat_or_404(db, target_chat_id)
    _check_member(db, chat_id, current_user.id)

    import uuid

    new_group_id = str(uuid.uuid4())
    fwd_display = f"{_get_employee_display_name(current_user)} (переслано)"
    new_msgs = []

    for msg_id in data.msg_ids:
        src_msg = (
            db.query(InternalChatMessage)
            .filter(
                InternalChatMessage.id == msg_id,
                InternalChatMessage.chat_id == chat_id,
                InternalChatMessage.is_deleted == False,
            )
            .first()
        )
        if not src_msg:
            continue
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
                group_id=new_group_id,
            )
        new_msgs.append(new_msg)

    # Батч-трансляция: одно событие new_message_group со всеми сообщениями
    await ws_manager.broadcast(
        target_chat_id,
        {
            "type": "new_message_group",
            "messages": [_message_to_dict(m) for m in new_msgs],
        },
    )

    return {"status": "ok", "forwarded": len(new_msgs), "group_id": new_group_id}


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


def _chat_to_response(
    db: Session,
    chat: InternalChat,
    employee_id: int,
    last_msgs: Optional[dict] = None,
    member_counts: Optional[dict] = None,
    unread_counts: Optional[dict] = None,
) -> InternalChatResponse:
    # Используем preloaded данные если переданы, иначе lazy-запрос (для единичных вызовов)
    if last_msgs is not None:
        last_msg = last_msgs.get(chat.id)
    else:
        last_msg = (
            db.query(InternalChatMessage)
            .filter(
                InternalChatMessage.chat_id == chat.id,
                InternalChatMessage.is_deleted == False,
            )
            .order_by(InternalChatMessage.id.desc())
            .first()
        )
    if member_counts is not None:
        member_count = member_counts.get(chat.id, 0)
    else:
        member_count = (
            db.query(InternalChatMember)
            .filter(
                InternalChatMember.chat_id == chat.id,
                InternalChatMember.is_active == True,
            )
            .count()
        )
    if unread_counts is not None:
        unread = unread_counts.get(chat.id, 0)
    else:
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
        is_online = None
        last_login = None
        if m.employee_id:
            emp = db.query(Employee).filter(Employee.id == m.employee_id).first()
            if emp:
                display = _get_employee_display_name(emp)
                role_in_project = emp.position or emp.secondary_position
                is_online = bool(emp.is_online)
                last_login = emp.last_login
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
                is_online=is_online,
                last_login=last_login,
            )
        )
    first_unread_id = get_first_unread_message_id(db, chat.id, employee_id)

    # Найти закреплённые сообщения (до 10, как в Telegram)
    pinned_objs = (
        db.query(InternalChatMessage)
        .filter(
            InternalChatMessage.chat_id == chat.id,
            InternalChatMessage.is_pinned == True,  # noqa: E712
            InternalChatMessage.is_deleted == False,  # noqa: E712
        )
        .order_by(InternalChatMessage.id.desc())
        .limit(10)
        .all()
    )
    from schemas import InternalMessageResponse

    pinned_responses = [InternalMessageResponse.model_validate(_message_to_dict(p)) for p in pinned_objs]

    has_more = (
        (
            db.query(InternalChatMessage)
            .filter(
                InternalChatMessage.chat_id == chat.id,
                InternalChatMessage.is_deleted == False,  # noqa: E712
                InternalChatMessage.id < msgs[0].id,
            )
            .first()
            is not None
        )
        if msgs
        else False
    )

    msg_dicts = [_message_to_dict(m) for m in msgs]
    if msg_dicts:
        reactions_map = get_batch_reactions(db, [d["id"] for d in msg_dicts])
        for d in msg_dicts:
            d["reactions"] = reactions_map.get(d["id"], {})

    return InternalChatDetailResponse(
        **base.model_dump(),
        members=member_responses,
        messages=msg_dicts,
        first_unread_message_id=first_unread_id,
        pinned_messages=pinned_responses,
        has_more_messages=has_more,
    )
