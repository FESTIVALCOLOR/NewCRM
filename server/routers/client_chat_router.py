"""
Роутер клиентского доступа к чату и WebSocket эндпоинты.

Монтируется с prefix="/api/v1":
  GET  /api/v1/client-chat/{token}              — информация о чате (без JWT)
  POST /api/v1/client-chat/{token}/register     — регистрация гостя
  GET  /api/v1/client-chat/{token}/messages     — история
  POST /api/v1/client-chat/{token}/messages     — отправить сообщение
  POST /api/v1/client-chat/{token}/files        — загрузить файл

  WS   /api/v1/ws/chat/{chat_id}?token=JWT      — сотрудник
  WS   /api/v1/ws/client-chat/{access_token}    — клиент
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from schemas import GuestRegistration, InternalMessageCreate
from services.chat_service import (
    _ensure_yd_folder,
    _get_employee_display_name,
    _message_to_dict,
    add_file_message,
    add_text_message,
    get_chat_by_token,
    get_guest_by_token,
    get_messages,
    mark_read,
    register_guest,
)
from services.chat_service import (
    manager as ws_manager,
)
from sqlalchemy.orm import Session

from database import Employee, InternalChatMember, get_db

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
    ".m4a",
}
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", 50))


# ==============================================================
# REST — клиентский доступ (без JWT)
# ==============================================================


@router.get("/client-chat/{token}")
def client_get_chat(
    token: str,
    db: Session = Depends(get_db),
):
    """Получить чат по UUID-токену (без авторизации)."""
    chat = get_chat_by_token(db, token)
    if not chat:
        raise HTTPException(404, "Чат не найден или ссылка устарела")
    guest = get_guest_by_token(db, token)
    requires_registration = not (guest and guest.guest_name)
    msgs = [] if requires_registration else [_message_to_dict(m) for m in get_messages(db, chat.id, limit=5000)]
    return {
        "chat_id": chat.id,
        "title": chat.title,
        "client_access_token": token,
        "requires_registration": requires_registration,
        "guest_name": guest.guest_name if guest else None,
        "messages": msgs,
    }


@router.post("/client-chat/{token}/register")
def client_register(
    token: str,
    data: GuestRegistration,
    db: Session = Depends(get_db),
):
    """Первый вход: сохранить имя и телефон гостя."""
    try:
        member = register_guest(db, token, data.guest_name, data.guest_phone)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {
        "status": "ok",
        "guest_name": member.guest_name,
        "chat_id": member.chat_id,
        "access_token": member.guest_access_token,  # персональный токен для повторных входов
    }


@router.get("/client-chat/{token}/messages")
def client_list_messages(
    token: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """История сообщений для клиента."""
    chat = get_chat_by_token(db, token)
    if not chat:
        raise HTTPException(404, "Чат не найден")
    msgs = get_messages(db, chat.id, limit=limit, offset=offset)
    return [_message_to_dict(m) for m in msgs]


@router.post("/client-chat/{token}/messages")
async def client_send_message(
    token: str,
    data: InternalMessageCreate,
    db: Session = Depends(get_db),
):
    """Клиент отправляет текстовое сообщение."""
    chat = get_chat_by_token(db, token)
    if not chat:
        raise HTTPException(404, "Чат не найден")
    guest = get_guest_by_token(db, token)
    if not guest or not guest.guest_name:
        raise HTTPException(403, "Сначала пройдите регистрацию")
    msg = add_text_message(
        db,
        chat.id,
        data.content,
        sender_guest_token=token,
        sender_display_name=guest.guest_name,
        reply_to_id=getattr(data, "reply_to_id", None),
    )
    await ws_manager.broadcast(
        chat.id,
        {
            "type": "new_message",
            "message": _message_to_dict(msg),
        },
    )
    return _message_to_dict(msg)


@router.patch("/client-chat/{token}/messages/{msg_id}")
async def client_edit_message(
    token: str,
    msg_id: int,
    data: InternalMessageCreate,
    db: Session = Depends(get_db),
):
    """Клиент редактирует своё текстовое сообщение."""
    from database import InternalChatMessage

    chat = get_chat_by_token(db, token)
    if not chat:
        raise HTTPException(404, "Чат не найден")
    guest = get_guest_by_token(db, token)
    if not guest or not guest.guest_name:
        raise HTTPException(403, "Сначала пройдите регистрацию")

    msg = (
        db.query(InternalChatMessage)
        .filter(
            InternalChatMessage.id == msg_id,
            InternalChatMessage.chat_id == chat.id,
            InternalChatMessage.sender_guest_token == token,
            InternalChatMessage.is_deleted == False,  # noqa: E712
            InternalChatMessage.message_type == "text",
        )
        .first()
    )
    if not msg:
        raise HTTPException(404, "Сообщение не найдено или не принадлежит вам")

    new_content = (data.content or "").strip()
    if not new_content:
        raise HTTPException(400, "Сообщение не может быть пустым")

    msg.content = new_content
    msg.is_edited = True
    db.commit()
    db.refresh(msg)

    updated = _message_to_dict(msg)
    await ws_manager.broadcast(chat.id, {"type": "message_edited", "message": updated})
    return updated


@router.post("/client-chat/{token}/files")
async def client_upload_file(
    token: str,
    file: UploadFile = File(...),
    message_type: str = Form("file"),
    db: Session = Depends(get_db),
):
    """Клиент загружает файл/голос/фото."""
    chat = get_chat_by_token(db, token)
    if not chat:
        raise HTTPException(404, "Чат не найден")
    guest = get_guest_by_token(db, token)
    if not guest or not guest.guest_name:
        raise HTTPException(403, "Сначала пройдите регистрацию")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext and ext not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(400, f"Тип файла '{ext}' не разрешён")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"Файл превышает {MAX_FILE_SIZE_MB} МБ")

    folder_clean = chat.yandex_folder_path.replace("disk:", "").rstrip("/") if chat.yandex_folder_path else f"/CRM/Chats/{chat.id}"
    safe_name = os.path.basename(file.filename or "unnamed")
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
        logger.exception(f"Ошибка загрузки файла клиента на ЯД: {e}")
        raise HTTPException(500, "Ошибка загрузки на Яндекс.Диск")

    msg = add_file_message(
        db,
        chat.id,
        file_url=public_url,
        file_name=safe_name,
        yandex_path=f"disk:{yd_path}",
        file_size=len(file_bytes),
        message_type=message_type,
        sender_guest_token=token,
        sender_display_name=guest.guest_name,
    )
    await ws_manager.broadcast(
        chat.id,
        {
            "type": "new_message",
            "message": _message_to_dict(msg),
        },
    )
    return _message_to_dict(msg)


@router.get("/client-chat/{token}/stream")
async def client_stream_file(
    token: str,
    yandex_path: str,
    db: Session = Depends(get_db),
):
    """Стримить файл чата для клиента (аутентификация по chat-токену, без JWT)."""
    chat = get_chat_by_token(db, token)
    if not chat:
        raise HTTPException(404, "Чат не найден")
    if ".." in yandex_path:
        raise HTTPException(400, "Недопустимый путь")
    try:
        import tempfile

        from fastapi.responses import FileResponse as _FileResponse
        from yandex_disk_service import get_yandex_disk_service

        yd_svc = get_yandex_disk_service()
        if not yd_svc or not yd_svc.token:
            raise HTTPException(503, "Яндекс.Диск не настроен")
        clean_path = yandex_path.replace("disk:", "").strip()
        if not clean_path.startswith("/"):
            clean_path = "/" + clean_path
        ext = os.path.splitext(clean_path)[1].lower()
        ct_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".heic": "image/heic",
        }
        ct = ct_map.get(ext, "application/octet-stream")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp_path = tmp.name
        tmp.close()
        yd_svc.download_file(f"disk:{clean_path}", tmp_path)
        return _FileResponse(tmp_path, media_type=ct, filename=os.path.basename(clean_path))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка стриминга файла клиента: {e}")
        raise HTTPException(500, "Ошибка получения файла")


# ==============================================================
# WebSocket — сотрудник
# ==============================================================


@router.websocket("/ws/chat/{chat_id}")
async def ws_employee_chat(
    chat_id: int,
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """WebSocket для сотрудника. ?token=<JWT>"""
    from auth import decode_token

    try:
        payload = decode_token(token)
        employee_id = int(payload.get("sub", 0))
    except Exception:
        await websocket.close(code=4001)
        return

    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        await websocket.close(code=4001)
        return

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
        await websocket.close(code=4003)
        return

    participant_key = f"emp_{employee_id}"
    await ws_manager.connect(chat_id, participant_key, websocket)

    await ws_manager.broadcast(
        chat_id,
        {
            "type": "user_online",
            "employee_id": employee_id,
            "name": _get_employee_display_name(emp),
        },
        exclude=participant_key,
    )

    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif event_type == "message":
                msg = add_text_message(
                    db,
                    chat_id,
                    data.get("content", ""),
                    sender_employee_id=employee_id,
                    sender_display_name=_get_employee_display_name(emp),
                    reply_to_id=data.get("reply_to_id"),
                )
                await ws_manager.broadcast(
                    chat_id,
                    {
                        "type": "new_message",
                        "message": _message_to_dict(msg),
                    },
                )

            elif event_type == "typing_start":
                await ws_manager.broadcast(
                    chat_id,
                    {
                        "type": "typing_start",
                        "employee_id": employee_id,
                        "sender_name": _get_employee_display_name(emp),
                    },
                    exclude=participant_key,
                )

            elif event_type == "typing_stop":
                await ws_manager.broadcast(
                    chat_id,
                    {
                        "type": "typing_stop",
                        "employee_id": employee_id,
                        "sender_name": _get_employee_display_name(emp),
                    },
                    exclude=participant_key,
                )

            elif event_type == "read":
                last_id = data.get("last_message_id")
                if last_id:
                    mark_read(db, chat_id, employee_id, last_id)
                    await ws_manager.broadcast(
                        chat_id,
                        {
                            "type": "read",
                            "employee_id": employee_id,
                            "last_message_id": last_id,
                        },
                        exclude=participant_key,
                    )

    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(chat_id, participant_key)
        await ws_manager.broadcast(
            chat_id,
            {
                "type": "user_offline",
                "employee_id": employee_id,
                "name": _get_employee_display_name(emp),
            },
        )


# ==============================================================
# WebSocket — клиент (без JWT)
# ==============================================================


@router.websocket("/ws/client-chat/{access_token}")
async def ws_client_chat(
    access_token: str,
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """WebSocket для клиента. Доступ по UUID-токену без JWT."""
    chat = get_chat_by_token(db, access_token)
    if not chat:
        await websocket.close(code=4004)
        return

    guest = get_guest_by_token(db, access_token)
    if not guest or not guest.guest_name:
        await websocket.close(code=4003)
        return

    participant_key = f"guest_{access_token[:8]}"
    await ws_manager.connect(chat.id, participant_key, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif event_type == "message":
                msg = add_text_message(
                    db,
                    chat.id,
                    data.get("content", ""),
                    sender_guest_token=access_token,
                    sender_display_name=guest.guest_name,
                    reply_to_id=data.get("reply_to_id"),
                )
                await ws_manager.broadcast(
                    chat.id,
                    {
                        "type": "new_message",
                        "message": _message_to_dict(msg),
                    },
                )

            elif event_type == "typing_start":
                await ws_manager.broadcast(
                    chat.id,
                    {
                        "type": "typing_start",
                        "sender_name": guest.guest_name,
                    },
                    exclude=participant_key,
                )

            elif event_type == "typing_stop":
                await ws_manager.broadcast(
                    chat.id,
                    {
                        "type": "typing_stop",
                        "sender_name": guest.guest_name,
                    },
                    exclude=participant_key,
                )

    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(chat.id, participant_key)
