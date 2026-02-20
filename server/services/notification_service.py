"""
Сервис автоуведомлений в мессенджере.
Хуки для отправки сообщений при событиях CRM и надзора.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from database import (
    Employee, Client, Contract,
    CRMCard, SupervisionCard,
    MessengerChat, MessengerChatMember, MessengerScript, MessengerMessageLog,
)
from telegram_service import get_telegram_service
from email_service import get_email_service

logger = logging.getLogger(__name__)


def decline_name_dative(full_name: str) -> str:
    """Склоняет ФИО в дательный падеж (кому?)."""
    if not full_name:
        return ''
    try:
        import pymorphy3
        morph = pymorphy3.MorphAnalyzer()
        parts = full_name.strip().split()
        result = []
        for part in parts:
            parsed = morph.parse(part)
            # Ищем вариант с тегом Name/Surn/Patr
            best = parsed[0]
            for p in parsed:
                if {'Name', 'Surn', 'Patr'} & p.tag.grammemes:
                    best = p
                    break
            inflected = best.inflect({'datv'})
            result.append(inflected.word.title() if inflected else part)
        return ' '.join(result)
    except Exception:
        return full_name


def build_script_context(db: Session, card, contract) -> dict:
    """Собрать контекст переменных для скриптов"""
    ctx = {
        'client_name': '',
        'stage_name': '',
        'deadline': '',
        'manager_name': '',
        'senior_manager': '',
        'sdp': '',
        'director': '',
        'address': contract.address or '',
        'city': contract.city or '',
        'project_type': contract.project_type or '',
        'contract_number': contract.contract_number or '',
        'area': str(contract.area or ''),
        # Дательный падеж (будут заполнены ниже)
        'client_name_dat': '',
        'manager_name_dat': '',
        'senior_manager_dat': '',
        'sdp_dat': '',
        'director_dat': '',
    }

    # Клиент
    if contract.client_id:
        client = db.query(Client).filter(Client.id == contract.client_id).first()
        if client:
            ctx['client_name'] = client.full_name or ''
            ctx['client_name_dat'] = decline_name_dative(client.full_name or '')

    # Менеджер
    if card.manager_id:
        mgr = db.query(Employee).filter(Employee.id == card.manager_id).first()
        if mgr:
            ctx['manager_name'] = mgr.full_name or ''
            ctx['manager_name_dat'] = decline_name_dative(mgr.full_name or '')

    # Старший менеджер
    if card.senior_manager_id:
        sm = db.query(Employee).filter(Employee.id == card.senior_manager_id).first()
        if sm:
            ctx['senior_manager'] = sm.full_name or ''
            ctx['senior_manager_dat'] = decline_name_dative(sm.full_name or '')

    # СДП
    if card.sdp_id:
        sdp = db.query(Employee).filter(Employee.id == card.sdp_id).first()
        if sdp:
            ctx['sdp'] = sdp.full_name or ''
            ctx['sdp_dat'] = decline_name_dative(sdp.full_name or '')

    # Руководитель студии
    director = db.query(Employee).filter(Employee.position == 'Руководитель студии').first()
    if director:
        ctx['director'] = director.full_name or ''
        ctx['director_dat'] = decline_name_dative(director.full_name or '')

    return ctx


async def send_invites_to_members(chat_id: int, db: Session):
    """Разослать invite-ссылки участникам чата"""
    chat = db.query(MessengerChat).filter(MessengerChat.id == chat_id).first()
    if not chat or not chat.invite_link:
        return

    members = db.query(MessengerChatMember).filter(
        MessengerChatMember.messenger_chat_id == chat_id,
        MessengerChatMember.invite_status == 'pending'
    ).all()

    tg = get_telegram_service()
    email_svc = get_email_service()

    for member in members:
        sent = False

        # Пробуем через Telegram бота (личное сообщение)
        if member.telegram_user_id and tg.bot_available:
            try:
                await tg.send_message(
                    member.telegram_user_id,
                    f"Вас пригласили в проектный чат: {chat.chat_title}\n"
                    f"Присоединяйтесь: {chat.invite_link}"
                )
                member.invite_status = 'sent'
                sent = True
            except Exception:
                pass

        # Если не получилось через Telegram — отправляем email
        if not sent and member.email and email_svc.available:
            # Получаем имя участника
            name = ""
            if member.member_type == 'employee':
                emp = db.query(Employee).filter(Employee.id == member.member_id).first()
                name = emp.full_name if emp else ""
            elif member.member_type == 'client':
                cl = db.query(Client).filter(Client.id == member.member_id).first()
                name = cl.full_name if cl else ""

            success = await email_svc.send_chat_invite(
                to_email=member.email,
                recipient_name=name,
                chat_title=chat.chat_title or "",
                invite_link=chat.invite_link,
            )
            if success:
                member.invite_status = 'email_sent'
                sent = True

        member.invited_at = datetime.utcnow() if sent else None

    db.commit()


async def trigger_messenger_notification(
    db: Session,
    crm_card_id: int,
    script_type: str,
    stage_name: str = "",
    extra_context: dict = None,
):
    """
    Хук автоуведомлений: найти чат карточки -> найти подходящий скрипт -> отправить.
    Вызывается из workflow-эндпоинтов через asyncio.create_task().
    script_type: 'project_start' | 'stage_complete' | 'project_end'
    """
    try:
        # Найти активный чат для карточки
        chat = db.query(MessengerChat).filter(
            MessengerChat.crm_card_id == crm_card_id,
            MessengerChat.is_active == True
        ).first()
        if not chat or not chat.telegram_chat_id:
            return  # Чат не создан или не привязан к Telegram

        # Найти подходящий скрипт
        scripts_query = db.query(MessengerScript).filter(
            MessengerScript.script_type == script_type,
            MessengerScript.is_enabled == True
        )
        # Для stage_complete — ищем скрипт конкретной стадии или общий
        if script_type == 'stage_complete' and stage_name:
            specific = scripts_query.filter(
                MessengerScript.stage_name == stage_name
            ).first()
            if specific:
                script = specific
            else:
                script = scripts_query.filter(
                    (MessengerScript.stage_name == None) | (MessengerScript.stage_name == '')
                ).first()
        else:
            script = scripts_query.first()

        if not script:
            return  # Нет включённого скрипта для этого события

        # Собрать контекст
        card = db.query(CRMCard).filter(CRMCard.id == crm_card_id).first()
        if not card:
            return
        contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
        if not contract:
            return

        ctx = build_script_context(db, card, contract)
        ctx['stage_name'] = stage_name or card.column_name or ''
        if extra_context:
            ctx.update(extra_context)

        # Отправить через Telegram
        tg = get_telegram_service()
        msg_id = await tg.send_script_message(
            chat_id=chat.telegram_chat_id,
            template=script.message_template,
            context=ctx,
        )

        # Записать в лог
        if msg_id:
            log_entry = MessengerMessageLog(
                messenger_chat_id=chat.id,
                message_type=f'auto_{script_type}',
                message_text=tg.render_template(script.message_template, ctx),
                sent_by=None,
                telegram_message_id=msg_id,
                delivery_status='sent',
            )
            db.add(log_entry)
            db.commit()
            logger.info(
                f"Автоуведомление отправлено: card={crm_card_id}, "
                f"type={script_type}, stage={stage_name}"
            )
    except Exception as e:
        logger.error(f"Ошибка автоуведомления (card={crm_card_id}): {e}")


async def trigger_supervision_notification(
    db: Session,
    supervision_card_id: int,
    script_type: str,
    stage_name: str = "",
):
    """
    Хук автоуведомлений для надзора: найти чат -> скрипт -> отправить.
    script_type: 'supervision_stage_complete' | 'supervision_move'
    """
    try:
        # Найти активный чат для карточки надзора
        chat = db.query(MessengerChat).filter(
            MessengerChat.supervision_card_id == supervision_card_id,
            MessengerChat.is_active == True
        ).first()
        if not chat or not chat.telegram_chat_id:
            return

        # Найти подходящий скрипт
        scripts_query = db.query(MessengerScript).filter(
            MessengerScript.script_type == script_type,
            MessengerScript.is_enabled == True
        )
        if stage_name:
            specific = scripts_query.filter(
                MessengerScript.stage_name == stage_name
            ).first()
            if specific:
                script = specific
            else:
                script = scripts_query.filter(
                    (MessengerScript.stage_name == None) | (MessengerScript.stage_name == '')
                ).first()
        else:
            script = scripts_query.first()

        if not script:
            return

        # Собрать контекст
        sv_card = db.query(SupervisionCard).filter(SupervisionCard.id == supervision_card_id).first()
        if not sv_card:
            return
        contract = db.query(Contract).filter(Contract.id == sv_card.contract_id).first()
        if not contract:
            return

        # Контекст для надзора
        ctx = {
            'stage_name': stage_name or sv_card.column_name or '',
            'client_name': '',
            'address': contract.address or '',
            'city': contract.city or '',
            'contract_number': contract.contract_number or '',
            'senior_manager': '',
            'dan': '',
            'deadline': '',
        }

        # Клиент
        if contract.client_id:
            client = db.query(Client).filter(Client.id == contract.client_id).first()
            if client:
                ctx['client_name'] = client.full_name or ''

        # Ст. менеджер
        if sv_card.senior_manager_id:
            sm = db.query(Employee).filter(Employee.id == sv_card.senior_manager_id).first()
            if sm:
                ctx['senior_manager'] = sm.full_name or ''

        # ДАН
        if sv_card.dan_id:
            dan = db.query(Employee).filter(Employee.id == sv_card.dan_id).first()
            if dan:
                ctx['dan'] = dan.full_name or ''

        # Отправить через Telegram
        tg = get_telegram_service()
        msg_id = await tg.send_script_message(
            chat_id=chat.telegram_chat_id,
            template=script.message_template,
            context=ctx,
        )

        if msg_id:
            log_entry = MessengerMessageLog(
                messenger_chat_id=chat.id,
                message_type=f'auto_{script_type}',
                message_text=tg.render_template(script.message_template, ctx),
                sent_by=None,
                telegram_message_id=msg_id,
                delivery_status='sent',
            )
            db.add(log_entry)
            db.commit()
            logger.info(
                f"Автоуведомление надзора: sv_card={supervision_card_id}, "
                f"type={script_type}, stage={stage_name}"
            )
    except Exception as e:
        logger.error(f"Ошибка автоуведомления надзора (sv_card={supervision_card_id}): {e}")
