"""
Notification Dispatcher — центральный диспетчер уведомлений.
Создаёт запись Notification в БД и отправляет через активные каналы
(Telegram) в зависимости от настроек сотрудника.

Поддерживает:
- Фильтрацию по типу события (assigned, crm_stage_change, deadline, payment, supervision)
- Фильтрацию по типу проекта (individual, template, supervision)
- 4 правила дублирования уведомлений (docs/notifications-scripts-guide.md §5)
"""

from datetime import datetime
import logging
import re
from typing import List, Optional

from constants import (
    POSITION_DAN,
    POSITION_GAP,
    POSITION_MANAGER,
    POSITION_SDP,
    POSITION_SENIOR_MANAGER,
    POSITION_STUDIO_DIRECTOR,
    ROLE_ADMIN,
    ROLE_DIRECTOR,
)
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Фразы-призывы к действию, убираемые из дублей
_ACTION_PHRASES = [
    r"Проверьте\.",
    r"Вы — проверяющий\.",
    r"Приступайте к работе\.",
    r"Назначьте сотрудников[^.]*\.",
]
_ACTION_PATTERN = re.compile(r"\s*(?:" + "|".join(_ACTION_PHRASES) + r")\s*", re.IGNORECASE)


def _strip_action_phrases(text: str) -> str:
    """Убрать призывы к действию из текста (для информационных дублей)."""
    result = _ACTION_PATTERN.sub(" ", text).strip()
    # Убрать двойные пробелы
    result = re.sub(r" {2,}", " ", result)
    return result


async def dispatch_notification(
    db: Session,
    employee_id: int,
    event_type: str,
    title: str,
    message: str,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[int] = None,
    project_type: Optional[str] = None,
    card_id: Optional[int] = None,
    is_duplicate: bool = False,
    is_revision_info: bool = False,
) -> None:
    """
    Создать уведомление в БД и отправить через активные каналы.

    Запись Notification создаётся ТОЛЬКО после прохождения всех проверок настроек,
    чтобы сотрудник не видел в панели уведомлений записи, которые он не должен получать.

    Args:
        db: SQLAlchemy сессия
        employee_id: ID сотрудника-получателя
        event_type: Тип события ('assigned' | 'crm_stage_change' | 'deadline' | 'payment' | 'supervision')
        title: Заголовок уведомления
        message: Текст уведомления
        related_entity_type: Тип связанной сущности ('crm_card', 'supervision_card', etc.)
        related_entity_id: ID связанной сущности
        project_type: Тип проекта ('individual' | 'template' | 'supervision')
        card_id: ID CRM-карточки (для правил дублирования)
        is_duplicate: Это дублированное уведомление (предотвращение рекурсии)
    """
    from database import Employee, Notification, NotificationSettings

    try:
        # 0. Проверить что сотрудник активен (не уволен, не в резерве)
        employee_check = db.query(Employee).filter_by(id=employee_id).first()
        if not employee_check:
            logger.warning(f"dispatch_notification: сотрудник id={employee_id} не найден, пропуск")
            return
        if getattr(employee_check, "status", None) in ("уволен", "в резерве"):
            logger.info(f"dispatch_notification: сотрудник id={employee_id} имеет статус '{employee_check.status}', пропуск")
            return

        # 1. Загрузить настройки уведомлений сотрудника (создать если нет)
        settings = db.query(NotificationSettings).filter_by(employee_id=employee_id).first()

        if not settings:
            supervision_roles = {
                POSITION_DAN,
                POSITION_SENIOR_MANAGER,
                POSITION_STUDIO_DIRECTOR,
                ROLE_ADMIN,
                ROLE_DIRECTOR,
            }
            is_senior_manager = bool(employee_check.position == POSITION_SENIOR_MANAGER)
            default_supervision = bool(employee_check.position in supervision_roles or employee_check.role in supervision_roles)
            try:
                settings = NotificationSettings(
                    employee_id=employee_id,
                    telegram_enabled=True,
                    email_enabled=False,
                    notify_crm_stage=True,
                    notify_assigned=True,
                    notify_deadline=True,
                    notify_payment=False,
                    notify_supervision=default_supervision,
                    notify_individual=True,
                    notify_template=True,
                    notify_duplicate_info=is_senior_manager,
                    notify_revision_info=is_senior_manager,
                )
                db.add(settings)
                db.flush()
            except Exception:
                # Race condition: другой воркер уже создал запись
                db.rollback()
                settings = db.query(NotificationSettings).filter_by(employee_id=employee_id).first()
                if not settings:
                    logger.warning(f"dispatch_notification: не удалось создать настройки для employee_id={employee_id}")
                    return

        # 2. Проверить флаг типа события
        event_flag_map = {
            "assigned": settings.notify_assigned,
            "crm_stage_change": settings.notify_crm_stage,
            "deadline": settings.notify_deadline,
            "payment": settings.notify_payment,
            "supervision": settings.notify_supervision,
        }
        if not event_flag_map.get(event_type, False):
            return

        # 2.1 Проверить фильтр по типу проекта
        if project_type:
            project_type_flag_map = {
                "individual": settings.notify_individual,
                "template": settings.notify_template,
                "supervision": settings.notify_supervision,
            }
            if not project_type_flag_map.get(project_type, True):
                return

        # 2.2 Для дублированных уведомлений — проверить дубль-флаги
        if is_duplicate:
            if not settings.notify_duplicate_info:
                return

        # 2.3 Для уведомлений о возврате на исправление — проверить notify_revision_info
        if is_revision_info:
            if not getattr(settings, "notify_revision_info", True):
                return

        # 2.4 Для уведомлений об оплатах — проверить право доступа
        if event_type == "payment":
            from permissions import check_permission

            has_payment_access = check_permission(employee_check, "payments.create", db) or check_permission(employee_check, "payments.update", db)
            if not has_payment_access:
                return

        # Все проверки пройдены — создать запись Notification в БД
        notification = Notification(
            employee_id=employee_id,
            notification_type=event_type,
            title=title,
            message=message,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            is_read=False,
            created_at=datetime.utcnow(),
        )
        db.add(notification)
        db.commit()

        # 3. Отправить через каналы в зависимости от настроек
        channel = getattr(settings, "notification_channel", "telegram") or "telegram"
        employee = db.query(Employee).filter_by(id=employee_id).first()

        # Telegram
        if channel in ("telegram", "both") and settings.telegram_enabled:
            if employee and employee.telegram_user_id:
                await _send_telegram(employee.telegram_user_id, title, message)

        # Web Push
        if channel in ("push", "both") and getattr(settings, "push_enabled", False):
            push_sub = getattr(settings, "push_subscription", None)
            if push_sub:
                await _send_web_push(push_sub, title, message, related_entity_type, related_entity_id)

        # 4. Применить правила дублирования (только для основных уведомлений)
        if not is_duplicate and card_id:
            await _apply_duplication_rules(db, employee_id, event_type, title, message, related_entity_type, related_entity_id, project_type, card_id)

    except Exception as e:
        logger.error(f"Ошибка dispatch_notification для employee_id={employee_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass


async def _apply_duplication_rules(
    db: Session,
    original_recipient_id: int,
    event_type: str,
    title: str,
    message: str,
    related_entity_type: Optional[str],
    related_entity_id: Optional[int],
    project_type: Optional[str],
    card_id: int,
) -> None:
    """
    Применить 4 правила дублирования из docs/notifications-scripts-guide.md §5.

    Правило 1: Ст.менеджер → Руководитель студии + Менеджер
    Правило 2: СДП/ГАП → Ст.менеджер (без призывов к действию)
    Правило 3: Исправления исполнителям → Ст.менеджер (обрабатывается в crm_router)
    Правило 4: Шаблонные — Менеджер/ГАП → Ст.менеджер (без призывов)
    """
    from database import CRMCard, Employee

    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            return

        recipient = db.query(Employee).filter(Employee.id == original_recipient_id).first()
        if not recipient:
            return

        already_sent: set = {original_recipient_id}

        # Правило 1: Уведомления ст.менеджеру → дублируются руководителю студии + менеджеру
        if recipient.position == POSITION_SENIOR_MANAGER:
            # → Руководитель студии
            director = (
                db.query(Employee)
                .filter(
                    Employee.position == POSITION_STUDIO_DIRECTOR,
                    Employee.status == "активный",
                )
                .first()
            )
            if director and director.id not in already_sent:
                await dispatch_notification(
                    db,
                    director.id,
                    event_type,
                    title,
                    message,
                    related_entity_type,
                    related_entity_id,
                    project_type,
                    card_id,
                    is_duplicate=True,
                )
                already_sent.add(director.id)

            # → Менеджер (если назначен на карточку)
            if card.manager_id and card.manager_id not in already_sent:
                await dispatch_notification(
                    db,
                    card.manager_id,
                    event_type,
                    title,
                    message,
                    related_entity_type,
                    related_entity_id,
                    project_type,
                    card_id,
                    is_duplicate=True,
                )
                already_sent.add(card.manager_id)

        # Правило 2: Уведомления СДП/ГАП → дублируются ст.менеджеру (без призывов)
        if recipient.position in (POSITION_SDP, POSITION_GAP):
            if card.senior_manager_id and card.senior_manager_id not in already_sent:
                info_message = _strip_action_phrases(message)
                await dispatch_notification(
                    db,
                    card.senior_manager_id,
                    event_type,
                    title,
                    info_message,
                    related_entity_type,
                    related_entity_id,
                    project_type,
                    card_id,
                    is_duplicate=True,
                )
                already_sent.add(card.senior_manager_id)

        # Правило 4: Шаблонные — Менеджер/ГАП → дублируются ст.менеджеру (без призывов)
        if project_type == "template" and recipient.position in (POSITION_MANAGER, POSITION_GAP):
            if card.senior_manager_id and card.senior_manager_id not in already_sent:
                info_message = _strip_action_phrases(message)
                await dispatch_notification(
                    db,
                    card.senior_manager_id,
                    event_type,
                    title,
                    info_message,
                    related_entity_type,
                    related_entity_id,
                    project_type,
                    card_id,
                    is_duplicate=True,
                )
                already_sent.add(card.senior_manager_id)

    except Exception as e:
        logger.error(f"Ошибка _apply_duplication_rules для card_id={card_id}: {e}")


async def _send_web_push(
    push_subscription_json: str,
    title: str,
    message: str,
    entity_type: str = None,
    entity_id: int = None,
    url_override: str = None,
    tag: str = None,
) -> None:
    """Отправить Web Push уведомление"""
    try:
        import json

        from config import get_settings

        _s = get_settings()
        VAPID_PRIVATE_KEY = _s.vapid_private_key
        VAPID_CLAIMS = {"sub": _s.vapid_claims_email}
        if not VAPID_PRIVATE_KEY:
            logger.debug("VAPID ключи не настроены, Web Push пропущен")
            return
        try:
            from pywebpush import WebPushException, webpush
        except ImportError:
            logger.warning("pywebpush не установлен, Web Push пропущен")
            return

        subscription = json.loads(push_subscription_json)
        # Формируем URL для перехода при клике
        if url_override:
            url = url_override
        elif entity_type == "crm_card" and entity_id:
            url = f"/crm/{entity_id}"
        elif entity_type == "supervision_card" and entity_id:
            url = f"/supervision/{entity_id}"
        elif entity_type == "chat" and entity_id:
            url = f"/employee-chats/{entity_id}"
        elif entity_type == "client_chat" and entity_id:
            url = f"/client-chats/{entity_id}"
        else:
            url = "/"

        payload = json.dumps(
            {
                "title": title,
                "message": message,
                "url": url,
                "tag": tag or "crm-notification",
            }
        )

        webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS,
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить Web Push: {e}")


async def notify_chat_message(
    chat_id: int,
    sender_employee_id: int | None,
    sender_name: str,
    text_preview: str,
    reply_to_id: int | None = None,
) -> None:
    """Уведомления участникам чата при новом сообщении (Telegram + Web Push)."""
    try:
        from database import Employee, InternalChat, InternalChatMember, InternalChatMessage, NotificationSettings, SessionLocal

        db = SessionLocal()
        try:
            # Заголовок чата для контекста
            chat = db.query(InternalChat).filter(InternalChat.id == chat_id).first()
            chat_title = (chat.title or "Чат") if chat else "Чат"

            # Кому отвечают (если это reply)
            reply_target_employee_id: int | None = None
            if reply_to_id:
                orig = db.query(InternalChatMessage).filter(InternalChatMessage.id == reply_to_id).first()
                if orig and orig.sender_employee_id and orig.sender_employee_id != sender_employee_id:
                    reply_target_employee_id = orig.sender_employee_id

            members = (
                db.query(InternalChatMember)
                .filter(
                    InternalChatMember.chat_id == chat_id,
                    InternalChatMember.member_type == "employee",
                    InternalChatMember.is_active == True,  # noqa: E712
                    InternalChatMember.employee_id.isnot(None),
                )
                .all()
            )
            logger.info(f"notify_chat_message: chat_id={chat_id}, sender={sender_employee_id}, members={[m.employee_id for m in members]}")
            for m in members:
                if m.employee_id == sender_employee_id:
                    continue

                s = db.query(NotificationSettings).filter(NotificationSettings.employee_id == m.employee_id).first()
                # notify_chat=None (NULL) означает "включено по умолчанию", пропускаем только явный False
                if s and getattr(s, "notify_chat", None) is False:
                    logger.info(f"notify_chat_message: emp={m.employee_id} — notify_chat=False, пропуск")
                    continue

                is_reply_target = reply_target_employee_id == m.employee_id
                chat_url = f"https://crm.festivalcolor.ru/employee-chats/{chat_id}"
                crm_link = f'<a href="{chat_url}">Перейти в чат</a>'
                action = "ответил(а) вам" if is_reply_target else "написал(а) вам"
                title = f"Сотрудник: {sender_name} {action} в чате {chat_title}"
                body = f"{text_preview}\n\n{crm_link}"

                # None (не задан) → фолбек "telegram"
                channel = (getattr(s, "notification_channel", None) or "telegram") if s else "telegram"
                employee = db.query(Employee).filter(Employee.id == m.employee_id).first()
                tg_id = employee.telegram_user_id if employee else None
                logger.info(f"notify_chat_message: emp={m.employee_id} channel={channel} tg_id={tg_id}")

                # Telegram
                if channel in ("telegram", "both"):
                    tg_enabled = getattr(s, "telegram_enabled", True) if s else True
                    if tg_enabled and employee and employee.telegram_user_id:
                        logger.info(f"notify_chat_message: отправка Telegram → {employee.telegram_user_id}")
                        await _send_telegram(employee.telegram_user_id, title, body)

                # Web Push
                if channel in ("push", "both"):
                    push_enabled = getattr(s, "push_enabled", False) if s else False
                    sub = getattr(s, "push_subscription", None) if s else None
                    if push_enabled and sub:
                        await _send_web_push(
                            sub,
                            title,
                            body,
                            entity_type="chat",
                            entity_id=chat_id,
                            tag=f"chat-{chat_id}",
                        )
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"notify_chat_message error: {e}")


async def notify_client_chat_employees(
    chat_id: int,
    sender_name: str,
    text_preview: str,
) -> None:
    """Telegram + Push сотрудникам клиентского чата когда клиент отправил сообщение."""
    try:
        from database import Employee, InternalChat, InternalChatMember, NotificationSettings, SessionLocal

        db = SessionLocal()
        try:
            chat = db.query(InternalChat).filter(InternalChat.id == chat_id).first()
            chat_title = chat.title if chat else f"Чат #{chat_id}"

            members = (
                db.query(InternalChatMember)
                .filter(
                    InternalChatMember.chat_id == chat_id,
                    InternalChatMember.member_type == "employee",
                    InternalChatMember.is_active == True,  # noqa: E712
                    InternalChatMember.employee_id.isnot(None),
                )
                .all()
            )
            logger.info(f"notify_client_chat_employees: chat_id={chat_id}, sender={sender_name!r}, members={[m.employee_id for m in members]}")
            chat_url = f"https://crm.festivalcolor.ru/client-chats/{chat_id}"
            title = f"Клиент: {sender_name} написал(а) вам в чате {chat_title}"
            body = f'{text_preview}\n\n<a href="{chat_url}">Перейти в чат</a>'
            for m in members:
                s = db.query(NotificationSettings).filter(NotificationSettings.employee_id == m.employee_id).first()
                if s and getattr(s, "notify_chat", None) is False:
                    continue
                channel = (getattr(s, "notification_channel", None) or "telegram") if s else "telegram"
                employee = db.query(Employee).filter(Employee.id == m.employee_id).first()

                # Telegram
                if channel in ("telegram", "both"):
                    tg_enabled = getattr(s, "telegram_enabled", True) if s else True
                    if tg_enabled and employee and employee.telegram_user_id:
                        await _send_telegram(employee.telegram_user_id, title, body)

                # Web Push
                if channel in ("push", "both"):
                    push_enabled = getattr(s, "push_enabled", False) if s else False
                    sub = getattr(s, "push_subscription", None) if s else None
                    if push_enabled and sub:
                        await _send_web_push(
                            sub,
                            title,
                            body,
                            entity_type="client_chat",
                            entity_id=chat_id,
                            tag=f"client-chat-{chat_id}",
                        )
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"notify_client_chat_employees error: {e}")


async def notify_client_chat_guests(
    chat_id: int,
    sender_name: str,
    text_preview: str,
) -> None:
    """Push гостям клиентского чата когда сотрудник отправил сообщение."""
    try:
        from database import InternalChatMember, SessionLocal

        db = SessionLocal()
        try:
            guests = (
                db.query(InternalChatMember)
                .filter(
                    InternalChatMember.chat_id == chat_id,
                    InternalChatMember.member_type == "client_guest",
                    InternalChatMember.is_active == True,  # noqa: E712
                    InternalChatMember.guest_push_subscription.isnot(None),
                )
                .all()
            )
            for g in guests:
                if not g.guest_push_subscription:
                    continue
                await _send_web_push(
                    g.guest_push_subscription,
                    f"💬 {sender_name}",
                    text_preview,
                    url_override=f"/c/{g.guest_access_token}",
                    tag=f"chat-{chat_id}",
                )
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"notify_client_chat_guests error: {e}")


async def _send_telegram(telegram_user_id: int, title: str, message: str) -> None:
    """Отправить уведомление через Telegram Bot"""
    import asyncio

    try:
        from telegram_service import get_telegram_service

        tg = get_telegram_service()
        logger.info(f"_send_telegram: tg_user={telegram_user_id} bot_available={tg.bot_available}")
        if tg.bot_available:
            text = f"<b>{title}</b>\n{message}"
            result = await asyncio.wait_for(tg.send_message(telegram_user_id, text), timeout=15.0)
            logger.info(f"_send_telegram: отправлено, message_id={result}")
    except asyncio.TimeoutError:
        logger.warning(f"Telegram таймаут (15с) для user_id={telegram_user_id}")
    except Exception as e:
        logger.warning(f"Не удалось отправить Telegram уведомление: {e}")
