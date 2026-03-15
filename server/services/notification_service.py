"""
Сервис автоуведомлений в мессенджере.
Хуки для отправки сообщений при событиях CRM и надзора.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from database import (
    Employee, Client, Contract,
    CRMCard, SupervisionCard, Payment,
    MessengerChat, MessengerChatMember, MessengerScript, MessengerMessageLog,
    MessengerSetting, ProjectFile, StageWorkflowState,
    SessionLocal,
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


def _get_first_name(full_name: str) -> str:
    """Извлечь имя клиента из ФИО (Фамилия Имя Отчество → Имя)."""
    if not full_name:
        return ''
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return parts[1]  # Фамилия Имя → Имя
    return parts[0]


def _tg_mention(employee) -> str:
    """Форматировать имя сотрудника как Telegram-упоминание (кликабельная ссылка).
    Если telegram_user_id задан — HTML-ссылка tg://user?id=XXX, иначе просто имя."""
    name = employee.full_name or ''
    tg_id = getattr(employee, 'telegram_user_id', None)
    if tg_id:
        return f'<a href="tg://user?id={tg_id}">{name}</a>'
    return name


def _get_username(employee) -> str:
    """Получить telegram_username сотрудника (без @)."""
    return getattr(employee, 'telegram_username', '') or ''


def _get_stage_files(db: Session, contract_id: int, stage: str) -> str:
    """Получить ссылки на файлы стадии для подстановки в {stage_files}."""
    if not contract_id or not stage:
        return ''
    files = db.query(ProjectFile).filter(
        ProjectFile.contract_id == contract_id,
        ProjectFile.stage == stage,
    ).order_by(ProjectFile.file_order).all()

    if not files:
        return ''

    links = []
    for f in files:
        if f.public_link:
            links.append(f'📎 {f.file_name}: {f.public_link}')
        elif f.yandex_path:
            links.append(f'📎 {f.file_name} (Яндекс.Диск: {f.yandex_path})')
    if not links:
        return ''
    return '\n'.join(links)


def _get_review_link(db: Session) -> str:
    """Получить ссылку на отзывы из MessengerSetting."""
    setting = db.query(MessengerSetting).filter(
        MessengerSetting.setting_key == 'review_link'
    ).first()
    return setting.setting_value if setting and setting.setting_value else ''


def build_script_context(db: Session, card, contract) -> dict:
    """Собрать контекст переменных для скриптов"""
    ctx = {
        'client_name': '',
        'client_first_name': '',
        'stage_name': '',
        'deadline': '',
        'deadline_date': '',
        'manager_name': '',
        'senior_manager': '',
        'sdp': '',
        'director': '',
        'dan': '',
        'address': contract.address or '',
        'city': contract.city or '',
        'project_type': contract.project_type or '',
        'contract_number': contract.contract_number or '',
        'area': str(contract.area or ''),
        # Usernames
        'senior_manager_username': '',
        'manager_username': '',
        'sdp_username': '',
        'director_username': '',
        'dan_username': '',
        # Дательный падеж
        'client_name_dat': '',
        'manager_name_dat': '',
        'senior_manager_dat': '',
        'sdp_dat': '',
        'director_dat': '',
        # Файлы и ссылки
        'stage_files': '',
        'review_link': _get_review_link(db),
        'revision_count': '',
        'visit_date': '',
        'pause_reason': '',
        'amount': '',
    }

    # Клиент
    if contract.client_id:
        client = db.query(Client).filter(Client.id == contract.client_id).first()
        if client:
            ctx['client_name'] = client.full_name or ''
            ctx['client_first_name'] = _get_first_name(client.full_name or '')
            ctx['client_name_dat'] = decline_name_dative(client.full_name or '')

    # Менеджер
    if card.manager_id:
        mgr = db.query(Employee).filter(Employee.id == card.manager_id).first()
        if mgr:
            ctx['manager_name'] = _tg_mention(mgr)
            ctx['manager_username'] = _get_username(mgr)
            ctx['manager_name_dat'] = decline_name_dative(mgr.full_name or '')

    # Старший менеджер
    if card.senior_manager_id:
        sm = db.query(Employee).filter(Employee.id == card.senior_manager_id).first()
        if sm:
            ctx['senior_manager'] = _tg_mention(sm)
            ctx['senior_manager_username'] = _get_username(sm)
            ctx['senior_manager_dat'] = decline_name_dative(sm.full_name or '')

    # СДП
    if card.sdp_id:
        sdp = db.query(Employee).filter(Employee.id == card.sdp_id).first()
        if sdp:
            ctx['sdp'] = _tg_mention(sdp)
            ctx['sdp_username'] = _get_username(sdp)
            ctx['sdp_dat'] = decline_name_dative(sdp.full_name or '')

    # Руководитель студии
    director = db.query(Employee).filter(Employee.position == 'Руководитель студии').first()
    if director:
        ctx['director'] = _tg_mention(director)
        ctx['director_username'] = _get_username(director)
        ctx['director_dat'] = decline_name_dative(director.full_name or '')

    # ДАН (для надзора — у CRMCard может не быть dan_id)
    dan_id = getattr(card, 'dan_id', None)
    if dan_id:
        dan = db.query(Employee).filter(Employee.id == dan_id).first()
        if dan:
            ctx['dan'] = _tg_mention(dan)
            ctx['dan_username'] = _get_username(dan)

    # revision_count из StageWorkflowState
    card_id = getattr(card, 'id', None)
    column_name = getattr(card, 'column_name', None)
    if card_id and column_name:
        wf = db.query(StageWorkflowState).filter(
            StageWorkflowState.crm_card_id == card_id,
            StageWorkflowState.stage_name == column_name,
        ).first()
        if wf and wf.revision_count:
            ctx['revision_count'] = str(wf.revision_count)

    # Сумма последнего платежа по договору
    if contract.id:
        last_payment = db.query(Payment).filter(
            Payment.contract_id == contract.id,
        ).order_by(Payment.id.desc()).first()
        if last_payment and last_payment.final_amount:
            ctx['amount'] = f"{last_payment.final_amount:,.0f}".replace(',', ' ')

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
    # С7: Создаём собственную сессию — переданная db может быть закрыта
    own_db = SessionLocal()
    try:
        # Найти активный чат для карточки
        chat = own_db.query(MessengerChat).filter(
            MessengerChat.crm_card_id == crm_card_id,
            MessengerChat.is_active == True
        ).first()
        if not chat or not chat.telegram_chat_id:
            return  # Чат не создан или не привязан к Telegram

        # Получить card и contract для определения project_type
        card = own_db.query(CRMCard).filter(CRMCard.id == crm_card_id).first()
        if not card:
            return
        contract = own_db.query(Contract).filter(Contract.id == card.contract_id).first()
        if not contract:
            return

        # Определить тип проекта для фильтрации скриптов
        card_project_type = contract.project_type or ''

        # Найти подходящий скрипт с фильтром по project_type
        script = _find_matching_script(
            own_db, script_type, stage_name, card_project_type
        )

        if not script:
            return  # Нет включённого скрипта для этого события

        # Собрать контекст
        ctx = build_script_context(own_db, card, contract)
        ctx['stage_name'] = stage_name or card.column_name or ''
        if extra_context:
            ctx.update(extra_context)

        # Добавить stage_files если скрипт требует
        if script.attach_stage_files and contract.id:
            stage_for_files = stage_name or card.column_name or ''
            files_text = _get_stage_files(own_db, contract.id, stage_for_files)
            if files_text:
                ctx['stage_files'] = files_text

        # Отправить через Telegram
        tg = get_telegram_service()
        msg_id = await tg.send_script_message(
            chat_id=chat.telegram_chat_id,
            template=script.message_template,
            context=ctx,
        )

        # Отправить PDF-памятку, если привязана к скрипту
        if msg_id and script.memo_file_path:
            try:
                import tempfile
                import os
                from yandex_disk_service import get_yandex_disk_service
                yd = get_yandex_disk_service()
                # Определяем имя файла из пути
                memo_filename = os.path.basename(script.memo_file_path)
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=os.path.splitext(memo_filename)[1]
                ) as tmp:
                    yd.download_file(script.memo_file_path, tmp.name)
                    await tg.send_document(
                        chat_id=chat.telegram_chat_id,
                        file_path=tmp.name,
                        caption=memo_filename,
                    )
                os.unlink(tmp.name)
                logger.info(f"PDF-памятка отправлена: {memo_filename}")
            except Exception as e:
                logger.warning(f"Не удалось отправить PDF-памятку: {e}")

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
            own_db.add(log_entry)
            own_db.commit()
            logger.info(
                f"Автоуведомление отправлено: card={crm_card_id}, "
                f"type={script_type}, stage={stage_name}"
            )
    except Exception as e:
        logger.error(f"Ошибка автоуведомления (card={crm_card_id}): {e}")
    finally:
        own_db.close()


async def trigger_supervision_notification(
    db: Session,
    supervision_card_id: int,
    script_type: str,
    stage_name: str = "",
    extra_context: dict = None,
):
    """
    Хук автоуведомлений для надзора: найти чат -> скрипт -> отправить.
    script_type: 'supervision_start' | 'supervision_stage_complete' | 'supervision_visit' | 'supervision_end'
    """
    # С7: Создаём собственную сессию — переданная db может быть закрыта
    own_db = SessionLocal()
    try:
        # Найти активный чат для карточки надзора
        chat = own_db.query(MessengerChat).filter(
            MessengerChat.supervision_card_id == supervision_card_id,
            MessengerChat.is_active == True
        ).first()
        if not chat or not chat.telegram_chat_id:
            return

        # Найти подходящий скрипт
        script = _find_matching_script(
            own_db, script_type, stage_name, 'Авторский надзор'
        )

        if not script:
            return

        # Собрать контекст
        sv_card = own_db.query(SupervisionCard).filter(SupervisionCard.id == supervision_card_id).first()
        if not sv_card:
            return
        contract = own_db.query(Contract).filter(Contract.id == sv_card.contract_id).first()
        if not contract:
            return

        # N6: Расширенный контекст для надзора (все переменные из руководства)
        ctx = {
            'stage_name': stage_name or sv_card.column_name or '',
            'client_name': '',
            'client_first_name': '',
            'client_name_dat': '',
            'address': contract.address or '',
            'city': contract.city or '',
            'area': str(contract.area) if getattr(contract, 'area', None) else '',
            'contract_number': contract.contract_number or '',
            'senior_manager': '',
            'senior_manager_username': '',
            'senior_manager_dat': '',
            'manager_name': '',
            'manager_username': '',
            'manager_name_dat': '',
            'sdp': '',
            'sdp_username': '',
            'sdp_dat': '',
            'dan': '',
            'dan_username': '',
            'dan_dat': '',
            'director': '',
            'director_username': '',
            'director_dat': '',
            'deadline': str(sv_card.deadline) if sv_card.deadline else '',
            'deadline_date': str(sv_card.deadline) if sv_card.deadline else '',
            'review_link': _get_review_link(own_db),
            'visit_date': '',
            'pause_reason': sv_card.pause_reason or '',
            'amount': '',
            'stage_files': '',
            'revision_count': '',
        }

        # Клиент
        if contract.client_id:
            client = own_db.query(Client).filter(Client.id == contract.client_id).first()
            if client:
                ctx['client_name'] = client.full_name or ''
                ctx['client_first_name'] = _get_first_name(client.full_name or '')
                ctx['client_name_dat'] = decline_name_dative(client.full_name or '')

        # Ст. менеджер
        if sv_card.senior_manager_id:
            sm = own_db.query(Employee).filter(Employee.id == sv_card.senior_manager_id).first()
            if sm:
                ctx['senior_manager'] = _tg_mention(sm)
                ctx['senior_manager_username'] = _get_username(sm)
                ctx['senior_manager_dat'] = decline_name_dative(sm.full_name or '')

        # ДАН
        if sv_card.dan_id:
            dan = own_db.query(Employee).filter(Employee.id == sv_card.dan_id).first()
            if dan:
                ctx['dan'] = _tg_mention(dan)
                ctx['dan_username'] = _get_username(dan)
                ctx['dan_dat'] = decline_name_dative(dan.full_name or '')

        # Руководитель студии
        director = own_db.query(Employee).filter(Employee.position == 'Руководитель студии').first()
        if director:
            ctx['director'] = _tg_mention(director)
            ctx['director_username'] = _get_username(director)
            ctx['director_dat'] = decline_name_dative(director.full_name or '')

        # Сумма последнего платежа по договору
        if contract.id:
            last_payment = own_db.query(Payment).filter(
                Payment.contract_id == contract.id,
            ).order_by(Payment.id.desc()).first()
            if last_payment and last_payment.final_amount:
                ctx['amount'] = f"{last_payment.final_amount:,.0f}".replace(',', ' ')

        # Extra context
        if extra_context:
            ctx.update(extra_context)

        # Stage files для промежуточных скриптов
        if script.attach_stage_files and contract.id:
            stage_for_files = stage_name or sv_card.column_name or ''
            files_text = _get_stage_files(own_db, contract.id, stage_for_files)
            if files_text:
                ctx['stage_files'] = files_text

        # Отправить через Telegram
        tg = get_telegram_service()
        msg_id = await tg.send_script_message(
            chat_id=chat.telegram_chat_id,
            template=script.message_template,
            context=ctx,
        )

        # Отправить PDF-памятку, если привязана
        if msg_id and script.memo_file_path:
            try:
                import tempfile
                import os
                from yandex_disk_service import get_yandex_disk_service
                yd = get_yandex_disk_service()
                memo_filename = os.path.basename(script.memo_file_path)
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=os.path.splitext(memo_filename)[1]
                ) as tmp:
                    yd.download_file(script.memo_file_path, tmp.name)
                    await tg.send_document(
                        chat_id=chat.telegram_chat_id,
                        file_path=tmp.name,
                        caption=memo_filename,
                    )
                os.unlink(tmp.name)
            except Exception as e:
                logger.warning(f"Не удалось отправить PDF-памятку надзора: {e}")

        if msg_id:
            log_entry = MessengerMessageLog(
                messenger_chat_id=chat.id,
                message_type=f'auto_{script_type}',
                message_text=tg.render_template(script.message_template, ctx),
                sent_by=None,
                telegram_message_id=msg_id,
                delivery_status='sent',
            )
            own_db.add(log_entry)
            own_db.commit()
            logger.info(
                f"Автоуведомление надзора: sv_card={supervision_card_id}, "
                f"type={script_type}, stage={stage_name}"
            )
    except Exception as e:
        logger.error(f"Ошибка автоуведомления надзора (sv_card={supervision_card_id}): {e}")
    finally:
        own_db.close()


def _find_matching_script(
    db: Session,
    script_type: str,
    stage_name: str,
    project_type: str,
) -> MessengerScript | None:
    """
    Найти подходящий скрипт с фильтрацией по project_type.

    Приоритет:
    1. Точное совпадение script_type + project_type + stage_name
    2. script_type + project_type + stage_name=NULL (общий для project_type)
    3. script_type + project_type=NULL + stage_name (общий для всех типов)
    4. script_type + project_type=NULL + stage_name=NULL (универсальный fallback)
    """
    base = db.query(MessengerScript).filter(
        MessengerScript.script_type == script_type,
        MessengerScript.is_enabled == True,
    )

    # 1. Точное совпадение: project_type + stage_name
    if stage_name and project_type:
        script = base.filter(
            MessengerScript.project_type == project_type,
            MessengerScript.stage_name == stage_name,
        ).first()
        if script:
            return script

    # 2. project_type + без stage_name
    if project_type:
        script = base.filter(
            MessengerScript.project_type == project_type,
            (MessengerScript.stage_name == None) | (MessengerScript.stage_name == ''),
        ).first()
        if script:
            return script

    # 3. Без project_type + stage_name
    if stage_name:
        script = base.filter(
            (MessengerScript.project_type == None) | (MessengerScript.project_type == ''),
            MessengerScript.stage_name == stage_name,
        ).first()
        if script:
            return script

    # 4. Универсальный fallback
    return base.filter(
        (MessengerScript.project_type == None) | (MessengerScript.project_type == ''),
        (MessengerScript.stage_name == None) | (MessengerScript.stage_name == ''),
    ).first()
