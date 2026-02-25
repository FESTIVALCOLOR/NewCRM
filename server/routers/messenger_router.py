"""
Роутер мессенджера (messenger) — чаты, скрипты, настройки, MTProto.
Подключается в main.py через:
    app.include_router(messenger_router, prefix="/api/messenger")
    app.include_router(sync_messenger_router, prefix="/api/sync")
"""
import logging
import os
import asyncio
import tempfile
import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import (
    get_db, Employee, Client, Contract, ProjectFile,
    CRMCard, SupervisionCard,
    MessengerChat, MessengerChatMember, MessengerScript, MessengerSetting, MessengerMessageLog,
)
from auth import get_current_user
from permissions import require_permission
from pydantic import BaseModel
from messenger_schemas import (
    MessengerChatCreate, MessengerChatBind, SupervisionChatCreate,
    MessengerChatResponse, MessengerChatDetailResponse,
    ChatMemberInput, ChatMemberResponse,
    MessengerScriptCreate, MessengerScriptUpdate, MessengerScriptResponse,
    MessengerSettingUpdate, MessengerSettingResponse, MessengerSettingsBulkUpdate,
    SendMessageRequest, SendFilesRequest, SendScriptMessageRequest, MessageLogResponse,
    SendInvitesRequest
)
from telegram_service import get_telegram_service, PYROGRAM_AVAILABLE
from email_service import get_email_service
from services.notification_service import (
    send_invites_to_members, build_script_context, decline_name_dative,
    trigger_messenger_notification, trigger_supervision_notification,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["messenger"])
sync_messenger_router = APIRouter(tags=["sync"])


# =============================================
# HELPER-ФУНКЦИИ
# =============================================

_settings_cache = {'data': None, 'ts': 0}


def load_messenger_settings(db: Session, force: bool = False) -> dict:
    """Загрузить настройки мессенджера из БД с кэшированием (TTL 60 сек)"""
    if not force and _settings_cache['data'] is not None and time.time() - _settings_cache['ts'] < 60:
        return _settings_cache['data']
    result = {}
    for row in db.query(MessengerSetting).all():
        result[row.setting_key] = row.setting_value or ""
    _settings_cache['data'] = result
    _settings_cache['ts'] = time.time()
    return result


def seed_default_messenger_scripts(db: Session):
    """Заполнить дефолтные скрипты если таблица пуста"""
    existing = db.query(MessengerScript).count()
    if existing > 0:
        return

    defaults = [
        MessengerScript(
            script_type="project_start",
            project_type=None,
            stage_name=None,
            message_template=(
                "Всем доброго дня!\n"
                "Приветствую в рабочем чате!\n"
                "Прикрепляем памятку, это кратко описанные основные пункты договора простым языком, "
                "которые важны в первую очередь. Пишите сюда любые вопросы, мы будем сами распределять "
                "кто на какие вопросы отвечает ввиду своих внутренних распорядков и компетенций.\n"
                "{senior_manager} отвечает за организационную часть проекта. "
                "{sdp} у нас старший дизайнер - она будет вести с вами весь проект. "
                "{director} руководитель студии, с ним вы заключали договор."
            ),
            use_auto_deadline=False,
            is_enabled=True,
            sort_order=0,
        ),
        MessengerScript(
            script_type="stage_complete",
            project_type=None,
            stage_name=None,
            message_template=(
                "Добрый день!\n"
                "Прошу рассмотреть {stage_name}, собрать для нас вопросы/правки/замечания "
                "и при необходимости назначить время-день для обсуждения (видео-созвон), когда Вам удобно.\n"
                "Рассмотреть необходимо до {deadline} или напишите, пожалуйста, "
                "срок необходимый Вам для согласования этапа."
            ),
            use_auto_deadline=True,
            is_enabled=True,
            sort_order=1,
        ),
        MessengerScript(
            script_type="project_end",
            project_type=None,
            stage_name=None,
            message_template=(
                "Добрый день!\n"
                "Благодарим за сотрудничество, надеемся вы остались довольны нашей работой.\n"
                "Желаем успехов в ремонте!\n"
                "Прикрепляем памятку о дальнейших этапах реализации проекта. "
                "Обращайтесь если будет необходима помощь.\n"
                "Очень просим Вас оставить отзыв о нашей работе: "
                "https://yandex.ru/maps/org/festival_color/21058411145/"
            ),
            use_auto_deadline=False,
            is_enabled=True,
            sort_order=2,
        ),
    ]

    for script in defaults:
        db.add(script)
    db.commit()
    logger.info(f"Создано {len(defaults)} дефолтных скриптов мессенджера")


def _build_chat_title(contract: Contract, card: CRMCard) -> str:
    """Сформировать название чата по контракту и CRM-карточке"""
    city = (contract.city or '').replace('_', '-')
    address = (contract.address or '').replace('_', '-')
    if city and address:
        city_map = {'спб': 'санкт-петербург', 'мск': 'москва', 'нск': 'новосибирск', 'екб': 'екатеринбург'}
        full_city = city_map.get(city.lower(), city.lower())
        addr_check = address.lower().replace('_', '-')
        for c in [full_city, city.lower()]:
            if addr_check.startswith(c):
                address = address[len(c):].lstrip('.,;:_ -')
                break
    # Определяем тип агента
    agent_type = (contract.agent_type or '').lower()
    if 'фестиваль' in agent_type or 'festival' in agent_type:
        prefix = "ФК"
    elif 'петрович' in agent_type or 'petrovich' in agent_type:
        prefix = "П"
    else:
        prefix = "ФК"
    return f"{prefix}-{city}-{address}"


def _add_chat_members(
    db: Session, chat: MessengerChat, members_input: list,
    contract: Contract, card: CRMCard = None
) -> list:
    """Добавить участников в чат"""
    members_resp = []

    for m in members_input:
        phone = None
        email = None

        if m.member_type == 'employee':
            emp = db.query(Employee).filter(Employee.id == m.member_id).first()
            if emp:
                phone = emp.phone
                email = emp.email
        elif m.member_type == 'client':
            cl = db.query(Client).filter(Client.id == m.member_id).first()
            if cl:
                phone = cl.phone
                email = cl.email

        member = MessengerChatMember(
            messenger_chat_id=chat.id,
            member_type=m.member_type,
            member_id=m.member_id,
            role_in_project=m.role_in_project,
            is_mandatory=m.is_mandatory,
            phone=phone,
            email=email,
            invite_status='pending',
        )
        db.add(member)
        db.flush()
        members_resp.append(ChatMemberResponse.model_validate(member))

    return members_resp


# =============================================
# TRIGGER SCRIPT (ручная отправка скрипта)
# =============================================

class TriggerScriptRequest(BaseModel):
    card_id: int
    script_type: str  # project_start, project_end, stage_complete, supervision_start, supervision_end
    entity_type: str = 'crm'  # 'crm' или 'supervision'


@router.post("/trigger-script")
async def trigger_script_endpoint(
    request: TriggerScriptRequest,
    current_user: Employee = Depends(require_permission("messenger.create_chat")),
    db: Session = Depends(get_db)
):
    """Ручная отправка скрипта мессенджера"""
    if request.entity_type == 'supervision':
        await trigger_supervision_notification(db, request.card_id, request.script_type)
    else:
        await trigger_messenger_notification(db, request.card_id, request.script_type)

    return {"status": "success"}


# =============================================
# MESSENGER CHATS ENDPOINTS
# Порядок: статические пути ПЕРЕД динамическими
# =============================================

@router.post("/chats", response_model=MessengerChatDetailResponse)
async def create_messenger_chat(
    data: MessengerChatCreate,
    current_user: Employee = Depends(require_permission("messenger.create_chat")),
    db: Session = Depends(get_db)
):
    """Создать чат автоматически (MTProto) для CRM-карточки"""
    # Перечитываем настройки (для консистентности между воркерами)
    messenger_settings = load_messenger_settings(db)
    tg_svc = get_telegram_service()
    tg_svc.configure(messenger_settings)

    # Проверка: уже есть активный чат
    existing = db.query(MessengerChat).filter(
        MessengerChat.crm_card_id == data.crm_card_id,
        MessengerChat.is_active == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Чат для этой карточки уже существует")

    # Получаем карточку и контракт
    card = db.query(CRMCard).filter(CRMCard.id == data.crm_card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="CRM-карточка не найдена")
    contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    tg = get_telegram_service()
    if not tg.mtproto_available:
        raise HTTPException(status_code=503, detail="MTProto не настроен. Используйте привязку чата.")

    # Формируем название чата
    chat_title = _build_chat_title(contract, card)

    # Определяем фото
    avatar_type = (contract.agent_type or '').lower()
    if 'фестиваль' in avatar_type or 'festival' in avatar_type:
        avatar_type = 'festival'
    elif 'петрович' in avatar_type or 'petrovich' in avatar_type:
        avatar_type = 'petrovich'
    else:
        avatar_type = 'festival'

    photo_path = os.path.join(os.path.dirname(__file__), '..', 'resources', f'{avatar_type}_logo.png')
    if not os.path.exists(photo_path):
        photo_path = None

    # Получаем username бота
    bot_username = None
    if tg.bot_available:
        try:
            bot_info = await tg._bot.get_me()
            bot_username = bot_info.username
        except Exception:
            pass

    # Создаём группу
    result = await tg.create_group(
        title=chat_title,
        photo_path=photo_path,
        bot_username=bot_username,
    )

    # Сохраняем в БД
    chat = MessengerChat(
        contract_id=contract.id,
        crm_card_id=data.crm_card_id,
        messenger_type=data.messenger_type,
        telegram_chat_id=result["chat_id"],
        chat_title=result["title"],
        invite_link=result["invite_link"],
        avatar_type=avatar_type,
        creation_method="auto",
        created_by=current_user.id,
        is_active=True,
    )
    db.add(chat)
    db.flush()

    # Добавляем участников
    members_resp = _add_chat_members(db, chat, data.members, contract, card)

    db.commit()

    # Рассылаем invite-ссылки асинхронно
    asyncio.create_task(send_invites_to_members(chat.id, db))

    # Авто-триггер начального скрипта project_start
    try:
        if data.crm_card_id:
            asyncio.create_task(
                trigger_messenger_notification(db, data.crm_card_id, 'project_start')
            )
    except Exception as e:
        logger.warning(f"Не удалось отправить project_start: {e}")

    return MessengerChatDetailResponse(
        chat=MessengerChatResponse.model_validate(chat),
        members=members_resp
    )


@router.post("/chats/bind", response_model=MessengerChatDetailResponse)
async def bind_messenger_chat(
    data: MessengerChatBind,
    current_user: Employee = Depends(require_permission("messenger.create_chat")),
    db: Session = Depends(get_db)
):
    """Привязать существующий чат по invite-ссылке"""
    # Проверка: уже есть активный чат
    existing = db.query(MessengerChat).filter(
        MessengerChat.crm_card_id == data.crm_card_id,
        MessengerChat.is_active == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Чат для этой карточки уже существует")

    card = db.query(CRMCard).filter(CRMCard.id == data.crm_card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="CRM-карточка не найдена")
    contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    chat_title = _build_chat_title(contract, card)

    # Определяем avatar_type
    avatar_type = (contract.agent_type or '').lower()
    if 'фестиваль' in avatar_type or 'festival' in avatar_type:
        avatar_type = 'festival'
    else:
        avatar_type = 'petrovich'

    # Пробуем получить chat_id через бота (бот должен быть в группе)
    tg = get_telegram_service()
    telegram_chat_id = None

    if tg.bot_available:
        resolved = await tg.resolve_invite_link(data.invite_link)
        if resolved:
            telegram_chat_id = resolved

    chat = MessengerChat(
        contract_id=contract.id,
        crm_card_id=data.crm_card_id,
        messenger_type=data.messenger_type,
        telegram_chat_id=telegram_chat_id,
        chat_title=chat_title,
        invite_link=data.invite_link,
        avatar_type=avatar_type,
        creation_method="manual",
        created_by=current_user.id,
        is_active=True,
    )
    db.add(chat)
    db.flush()

    # Участники
    members_resp = _add_chat_members(db, chat, data.members, contract, card)

    db.commit()

    # Рассылаем invite-ссылки
    asyncio.create_task(send_invites_to_members(chat.id, db))

    return MessengerChatDetailResponse(
        chat=MessengerChatResponse.model_validate(chat),
        members=members_resp
    )


@router.post("/chats/supervision", response_model=MessengerChatDetailResponse)
async def create_supervision_chat(
    data: SupervisionChatCreate,
    current_user: Employee = Depends(require_permission("messenger.create_chat")),
    db: Session = Depends(get_db)
):
    """Создать чат автоматически (MTProto) для карточки надзора"""
    # Перечитываем настройки
    messenger_settings = load_messenger_settings(db)
    tg_svc = get_telegram_service()
    tg_svc.configure(messenger_settings)

    # Проверка: уже есть активный чат
    existing = db.query(MessengerChat).filter(
        MessengerChat.supervision_card_id == data.supervision_card_id,
        MessengerChat.is_active == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Чат для этой карточки надзора уже существует")

    # Получаем карточку надзора и контракт
    sv_card = db.query(SupervisionCard).filter(SupervisionCard.id == data.supervision_card_id).first()
    if not sv_card:
        raise HTTPException(status_code=404, detail="Карточка надзора не найдена")
    contract = db.query(Contract).filter(Contract.id == sv_card.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    tg = get_telegram_service()
    if not tg.mtproto_available:
        raise HTTPException(status_code=503, detail="MTProto не настроен")

    # Формируем название чата: АН-Город-Адрес
    city = (contract.city or '').replace('_', '-')
    address = (contract.address or '').replace('_', '-')
    if city and address:
        city_map = {'спб': 'санкт-петербург', 'мск': 'москва', 'нск': 'новосибирск', 'екб': 'екатеринбург'}
        full_city = city_map.get(city.lower(), city.lower())
        addr_check = address.lower().replace('_', '-')
        for c in [full_city, city.lower()]:
            if addr_check.startswith(c):
                address = address[len(c):].lstrip('.,;:_ -')
                break
    chat_title = f"АН-{city}-{address}"

    # Определяем фото
    avatar_type = (contract.agent_type or '').lower()
    if 'фестиваль' in avatar_type or 'festival' in avatar_type:
        avatar_type = 'festival'
    elif 'петрович' in avatar_type or 'petrovich' in avatar_type:
        avatar_type = 'petrovich'
    else:
        avatar_type = 'festival'

    photo_path = os.path.join(os.path.dirname(__file__), '..', 'resources', f'{avatar_type}_logo.png')
    if not os.path.exists(photo_path):
        photo_path = None

    # Получаем username бота
    bot_username = None
    if tg.bot_available:
        try:
            bot_info = await tg._bot.get_me()
            bot_username = bot_info.username
        except Exception:
            pass

    # Создаём группу
    result = await tg.create_group(
        title=chat_title,
        photo_path=photo_path,
        bot_username=bot_username,
    )

    # Сохраняем в БД
    chat = MessengerChat(
        contract_id=contract.id,
        supervision_card_id=data.supervision_card_id,
        messenger_type=data.messenger_type,
        telegram_chat_id=result["chat_id"],
        chat_title=result["title"],
        invite_link=result["invite_link"],
        avatar_type=avatar_type,
        creation_method="auto",
        created_by=current_user.id,
        is_active=True,
    )
    db.add(chat)
    db.flush()

    # Добавляем участников (переиспользуем _add_chat_members)
    members_resp = _add_chat_members(db, chat, data.members, contract)

    db.commit()

    # Рассылаем invite-ссылки
    asyncio.create_task(send_invites_to_members(chat.id, db))

    return MessengerChatDetailResponse(
        chat=MessengerChatResponse.model_validate(chat),
        members=members_resp
    )


@router.get("/chats/by-card/{card_id}", response_model=MessengerChatDetailResponse)
async def get_messenger_chat_by_card(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить чат по CRM-карточке"""
    chat = db.query(MessengerChat).filter(
        MessengerChat.crm_card_id == card_id,
        MessengerChat.is_active == True
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    members = db.query(MessengerChatMember).filter(
        MessengerChatMember.messenger_chat_id == chat.id
    ).all()

    return MessengerChatDetailResponse(
        chat=MessengerChatResponse.model_validate(chat),
        members=[ChatMemberResponse.model_validate(m) for m in members]
    )


@router.get("/chats/by-supervision/{supervision_card_id}", response_model=MessengerChatDetailResponse)
async def get_messenger_chat_by_supervision(
    supervision_card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить чат по карточке надзора"""
    chat = db.query(MessengerChat).filter(
        MessengerChat.supervision_card_id == supervision_card_id,
        MessengerChat.is_active == True
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    members = db.query(MessengerChatMember).filter(
        MessengerChatMember.messenger_chat_id == chat.id
    ).all()

    return MessengerChatDetailResponse(
        chat=MessengerChatResponse.model_validate(chat),
        members=[ChatMemberResponse.model_validate(m) for m in members]
    )


@router.delete("/chats/{chat_id}")
async def delete_messenger_chat(
    chat_id: int,
    current_user: Employee = Depends(require_permission("messenger.delete_chat")),
    db: Session = Depends(get_db)
):
    """Удалить/отвязать чат"""
    chat = db.query(MessengerChat).filter(MessengerChat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    tg = get_telegram_service()

    # Если чат был создан автоматически — пробуем удалить группу
    if chat.creation_method == 'auto' and chat.telegram_chat_id:
        await tg.delete_group(chat.telegram_chat_id)
    elif chat.telegram_chat_id and tg.bot_available:
        # Для привязанного чата — бот просто покидает
        await tg.leave_chat(chat.telegram_chat_id)

    # Помечаем как неактивный
    chat.is_active = False
    db.commit()

    return {"status": "deleted", "chat_id": chat_id}


@router.post("/chats/{chat_id}/message")
async def send_chat_message(
    chat_id: int,
    data: SendMessageRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправить сообщение в чат"""
    chat = db.query(MessengerChat).filter(
        MessengerChat.id == chat_id, MessengerChat.is_active == True
    ).first()
    if not chat or not chat.telegram_chat_id:
        raise HTTPException(status_code=404, detail="Чат не найден или не привязан")

    tg = get_telegram_service()
    msg_id = await tg.send_message(chat.telegram_chat_id, data.text)

    # Логируем
    log = MessengerMessageLog(
        messenger_chat_id=chat.id,
        message_type='manual',
        message_text=data.text,
        sent_by=current_user.id,
        telegram_message_id=msg_id,
        delivery_status='sent' if msg_id else 'failed',
    )
    db.add(log)
    db.commit()

    return {"status": "sent" if msg_id else "failed", "telegram_message_id": msg_id}


@router.post("/chats/{chat_id}/send-invites")
async def send_chat_invites(
    chat_id: int,
    data: SendInvitesRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Разослать invite-ссылки участникам"""
    chat = db.query(MessengerChat).filter(MessengerChat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")

    await send_invites_to_members(chat.id, db)
    return {"status": "invites_sent"}


@router.post("/chats/{chat_id}/files")
async def send_files_to_chat(
    chat_id: int,
    data: SendFilesRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отправить файлы в чат (с Яндекс.Диска)"""
    from yandex_disk_service import get_yandex_disk_service

    chat = db.query(MessengerChat).filter(
        MessengerChat.id == chat_id, MessengerChat.is_active == True
    ).first()
    if not chat or not chat.telegram_chat_id:
        raise HTTPException(status_code=404, detail="Чат не найден или не привязан")

    tg = get_telegram_service()
    yd = get_yandex_disk_service()
    sent_ids = []

    # Собираем Yandex пути: из file_ids + из прямых yandex_paths
    yandex_files = []
    for file_id in (data.file_ids or []):
        pf = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
        if pf and pf.yandex_path:
            yandex_files.append({
                "yandex_path": pf.yandex_path,
                "file_name": pf.file_name or os.path.basename(pf.yandex_path),
                "file_type": pf.file_type or "file",
            })

    for yp in (data.yandex_paths or []):
        yandex_files.append({
            "yandex_path": yp,
            "file_name": os.path.basename(yp),
            "file_type": "image" if any(yp.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']) else "file",
        })

    if not yandex_files:
        raise HTTPException(status_code=400, detail="Нет файлов для отправки")

    # Определяем тип отправки: галерея (изображения) или документы
    image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

    if data.as_gallery:
        # Отправка изображений галереей
        images_for_gallery = []
        docs_to_send = []

        for yf in yandex_files:
            ext = os.path.splitext(yf["file_name"])[1].lower()
            if ext in image_exts:
                images_for_gallery.append(yf)
            else:
                docs_to_send.append(yf)

        # Скачиваем и отправляем изображения галереей
        if images_for_gallery:
            photo_bytes_list = []
            for img in images_for_gallery[:10]:  # Telegram ограничение: 10 фото в галерее
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(img["file_name"])[1]) as tmp:
                        yd.download_file(img["yandex_path"], tmp.name)
                        with open(tmp.name, 'rb') as f:
                            photo_bytes_list.append({
                                "bytes": f.read(),
                                "filename": img["file_name"],
                            })
                    os.unlink(tmp.name)
                except Exception as e:
                    logger.warning(f"Ошибка скачивания {img['yandex_path']}: {e}")

            if photo_bytes_list:
                msg_ids = await tg.send_media_group_from_bytes(
                    chat.telegram_chat_id, photo_bytes_list, caption=data.caption
                )
                if msg_ids:
                    sent_ids.extend(msg_ids)

        # Документы отправляем отдельно
        for doc in docs_to_send:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(doc["file_name"])[1]) as tmp:
                    yd.download_file(doc["yandex_path"], tmp.name)
                    msg_id = await tg.send_document(
                        chat.telegram_chat_id, tmp.name, caption=doc["file_name"]
                    )
                    if msg_id:
                        sent_ids.append(msg_id)
                os.unlink(tmp.name)
            except Exception as e:
                logger.warning(f"Ошибка отправки документа {doc['file_name']}: {e}")
    else:
        # Все файлы как документы (со ссылками)
        links = []
        for yf in yandex_files:
            try:
                public_link = yd.get_public_link(yf["yandex_path"])
                links.append(f'<a href="{public_link}">{yf["file_name"]}</a>')
            except Exception:
                links.append(yf["file_name"])

        if links:
            text = data.caption + "\n\n" if data.caption else ""
            text += "\n".join(links)
            msg_id = await tg.send_message(chat.telegram_chat_id, text, parse_mode="HTML")
            if msg_id:
                sent_ids.append(msg_id)

    # Логируем
    file_names = [yf["file_name"] for yf in yandex_files]
    log = MessengerMessageLog(
        messenger_chat_id=chat.id,
        message_type='files',
        message_text=data.caption or "",
        file_links=",".join(file_names),
        sent_by=current_user.id,
        telegram_message_id=sent_ids[0] if sent_ids else None,
        delivery_status='sent' if sent_ids else 'failed',
    )
    db.add(log)
    db.commit()

    return {
        "status": "sent" if sent_ids else "failed",
        "files_count": len(yandex_files),
        "telegram_message_ids": sent_ids,
    }


# =============================================
# MESSENGER SCRIPTS ENDPOINTS
# =============================================

@router.get("/scripts", response_model=list[MessengerScriptResponse])
async def get_messenger_scripts(
    project_type: str = None,
    script_type: str = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить скрипты (с фильтрацией)"""
    query = db.query(MessengerScript)
    if project_type:
        query = query.filter(
            (MessengerScript.project_type == project_type) | (MessengerScript.project_type == None)
        )
    if script_type:
        query = query.filter(MessengerScript.script_type == script_type)

    scripts = query.order_by(MessengerScript.sort_order).all()
    return [MessengerScriptResponse.model_validate(s) for s in scripts]


@router.post("/scripts", response_model=MessengerScriptResponse)
async def create_messenger_script(
    data: MessengerScriptCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать скрипт"""
    script = MessengerScript(**data.model_dump())
    db.add(script)
    db.commit()
    db.refresh(script)
    return MessengerScriptResponse.model_validate(script)


@router.put("/scripts/{script_id}", response_model=MessengerScriptResponse)
async def update_messenger_script(
    script_id: int,
    data: MessengerScriptUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить скрипт"""
    script = db.query(MessengerScript).filter(MessengerScript.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Скрипт не найден")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(script, key, value)
    script.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(script)
    return MessengerScriptResponse.model_validate(script)


@router.delete("/scripts/{script_id}")
async def delete_messenger_script(
    script_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить скрипт"""
    script = db.query(MessengerScript).filter(MessengerScript.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Скрипт не найден")
    db.delete(script)
    db.commit()
    return {"status": "deleted"}


@router.patch("/scripts/{script_id}/toggle")
async def toggle_messenger_script(
    script_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Включить/выключить скрипт"""
    script = db.query(MessengerScript).filter(MessengerScript.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Скрипт не найден")
    script.is_enabled = not script.is_enabled
    script.updated_at = datetime.utcnow()
    db.commit()
    return {"id": script.id, "is_enabled": script.is_enabled}


# =============================================
# MESSENGER SETTINGS ENDPOINTS
# =============================================

@router.get("/settings", response_model=list[MessengerSettingResponse])
async def get_messenger_settings(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить все настройки мессенджера"""
    settings_list = db.query(MessengerSetting).all()
    return [MessengerSettingResponse.model_validate(s) for s in settings_list]


@router.put("/settings")
async def update_messenger_settings(
    data: MessengerSettingsBulkUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить настройки мессенджера (массовое обновление)"""
    for item in data.settings:
        setting = db.query(MessengerSetting).filter(
            MessengerSetting.setting_key == item.setting_key
        ).first()
        if setting:
            setting.setting_value = item.setting_value
            setting.updated_at = datetime.utcnow()
            setting.updated_by = current_user.id
        else:
            setting = MessengerSetting(
                setting_key=item.setting_key,
                setting_value=item.setting_value,
                updated_by=current_user.id,
            )
            db.add(setting)

    db.commit()

    # Инвалидируем кэш и переинициализируем сервисы с новыми настройками
    messenger_settings = load_messenger_settings(db, force=True)

    tg = get_telegram_service()
    tg.configure(messenger_settings)

    email_svc = get_email_service()
    email_svc.configure(messenger_settings)

    return {"status": "updated", "bot_available": tg.bot_available, "email_available": email_svc.available}


@router.get("/status")
async def get_messenger_status(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Статус сервисов мессенджера (перечитывает настройки из БД для консистентности между воркерами)"""
    # Перечитываем настройки из БД чтобы учесть изменения от другого воркера
    messenger_settings = {}
    for row in db.query(MessengerSetting).all():
        messenger_settings[row.setting_key] = row.setting_value or ""

    tg = get_telegram_service()
    tg.configure(messenger_settings)

    email_svc = get_email_service()
    email_svc.configure(messenger_settings)

    return {
        "telegram_bot_available": tg.bot_available,
        "telegram_mtproto_available": tg.mtproto_available,
        "email_available": email_svc.available,
    }


# =============================================
# MESSENGER MTPROTO AUTHORIZATION
# =============================================

@router.post("/mtproto/send-code")
async def mtproto_send_code(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Шаг 1: Отправить код подтверждения на телефон для MTProto авторизации"""
    if current_user.role not in ("admin", "director", "Руководитель студии"):
        raise HTTPException(status_code=403, detail="Только администратор или директор")

    # Перечитываем настройки из БД
    messenger_settings = {}
    for row in db.query(MessengerSetting).all():
        messenger_settings[row.setting_key] = row.setting_value or ""

    tg = get_telegram_service()
    tg.configure(messenger_settings)

    if not PYROGRAM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Pyrogram не установлен на сервере")

    if not messenger_settings.get("telegram_api_id") or not messenger_settings.get("telegram_api_hash"):
        raise HTTPException(status_code=400, detail="API ID и API Hash не заполнены")
    if not messenger_settings.get("telegram_phone"):
        raise HTTPException(status_code=400, detail="Телефон не указан")

    try:
        phone_code_hash = await tg.send_auth_code()
        # Сохраняем hash в БД чтобы любой воркер мог его прочитать
        existing = db.query(MessengerSetting).filter_by(setting_key="telegram_phone_code_hash").first()
        if existing:
            existing.setting_value = phone_code_hash
        else:
            db.add(MessengerSetting(setting_key="telegram_phone_code_hash", setting_value=phone_code_hash))
        db.commit()
        return {"status": "code_sent", "phone": messenger_settings["telegram_phone"]}
    except Exception as e:
        logger.exception(f"Ошибка при отправке кода MTProto: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/mtproto/resend-sms")
async def mtproto_resend_sms(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отправить код сразу по SMS (send_code + resend_code за один вызов)"""
    if current_user.role not in ("admin", "director", "Руководитель студии"):
        raise HTTPException(status_code=403, detail="Только администратор или директор")

    messenger_settings = {}
    for row in db.query(MessengerSetting).all():
        messenger_settings[row.setting_key] = row.setting_value or ""

    tg = get_telegram_service()
    tg.configure(messenger_settings)

    try:
        new_hash = await tg.send_auth_code_sms()
        # Сохраняем hash в БД
        existing = db.query(MessengerSetting).filter_by(setting_key="telegram_phone_code_hash").first()
        if existing:
            existing.setting_value = new_hash
        else:
            db.add(MessengerSetting(setting_key="telegram_phone_code_hash", setting_value=new_hash))
        db.commit()
        return {"status": "sms_sent", "phone": messenger_settings.get("telegram_phone", "")}
    except Exception as e:
        logger.exception(f"Ошибка при отправке кода по SMS MTProto: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/mtproto/verify-code")
async def mtproto_verify_code(
    data: dict,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Шаг 2: Подтвердить код и активировать MTProto сессию"""
    if current_user.role not in ("admin", "director", "Руководитель студии"):
        raise HTTPException(status_code=403, detail="Только администратор или директор")

    code = str(data.get("code", "")).strip()
    if not code:
        raise HTTPException(status_code=400, detail="Код не указан")

    # Перечитываем настройки и hash из БД
    messenger_settings = {}
    for row in db.query(MessengerSetting).all():
        messenger_settings[row.setting_key] = row.setting_value or ""

    phone_code_hash = messenger_settings.get("telegram_phone_code_hash", "")
    if not phone_code_hash:
        raise HTTPException(status_code=400, detail="Сначала запросите код через send-code")

    tg = get_telegram_service()
    tg.configure(messenger_settings)

    try:
        user_info = await tg.verify_auth_code(phone_code_hash, code)
        # Удаляем hash — больше не нужен
        hash_row = db.query(MessengerSetting).filter_by(setting_key="telegram_phone_code_hash").first()
        if hash_row:
            db.delete(hash_row)
            db.commit()
        return {"status": "success", "user": user_info}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Ошибка при верификации MTProto: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/mtproto/session-status")
async def mtproto_session_status(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Проверить статус Pyrogram-сессии"""
    if current_user.role not in ("admin", "director", "Руководитель студии"):
        raise HTTPException(status_code=403, detail="Только администратор или директор")

    messenger_settings = {}
    for row in db.query(MessengerSetting).all():
        messenger_settings[row.setting_key] = row.setting_value or ""

    tg = get_telegram_service()
    tg.configure(messenger_settings)

    try:
        result = await tg.check_session_valid()
        return result
    except Exception as e:
        logger.error(f"Ошибка проверки MTProto сессии: {e}")
        return {"valid": False, "error": str(e)}


# =============================================
# SYNC MESSENGER DATA (sync_messenger_router)
# =============================================

@sync_messenger_router.get("/messenger-chats")
async def sync_messenger_chats(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Синхронизация чатов"""
    chats = db.query(MessengerChat).all()
    return [{
        'id': c.id,
        'contract_id': c.contract_id,
        'crm_card_id': c.crm_card_id,
        'messenger_type': c.messenger_type,
        'telegram_chat_id': c.telegram_chat_id,
        'chat_title': c.chat_title,
        'invite_link': c.invite_link,
        'avatar_type': c.avatar_type,
        'creation_method': c.creation_method,
        'created_by': c.created_by,
        'created_at': c.created_at.isoformat() if c.created_at else None,
        'is_active': c.is_active,
    } for c in chats]


@sync_messenger_router.get("/messenger-scripts")
async def sync_messenger_scripts(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Синхронизация скриптов"""
    scripts = db.query(MessengerScript).all()
    return [{
        'id': s.id,
        'script_type': s.script_type,
        'project_type': s.project_type,
        'stage_name': s.stage_name,
        'message_template': s.message_template,
        'use_auto_deadline': s.use_auto_deadline,
        'is_enabled': s.is_enabled,
        'sort_order': s.sort_order,
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'updated_at': s.updated_at.isoformat() if s.updated_at else None,
    } for s in scripts]
