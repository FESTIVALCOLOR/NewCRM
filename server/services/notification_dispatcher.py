"""
Notification Dispatcher — центральный диспетчер уведомлений.
Создаёт запись Notification в БД и отправляет через активные каналы
(Telegram) в зависимости от настроек сотрудника.

Поддерживает:
- Фильтрацию по типу события (assigned, crm_stage_change, deadline, payment, supervision)
- Фильтрацию по типу проекта (individual, template, supervision)
- 4 правила дублирования уведомлений (docs/notifications-scripts-guide.md §5)
"""
import logging
import re
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Фразы-призывы к действию, убираемые из дублей
_ACTION_PHRASES = [
    r'Проверьте\.',
    r'Вы — проверяющий\.',
    r'Приступайте к работе\.',
    r'Назначьте сотрудников[^.]*\.',
]
_ACTION_PATTERN = re.compile(r'\s*(?:' + '|'.join(_ACTION_PHRASES) + r')\s*', re.IGNORECASE)


def _strip_action_phrases(text: str) -> str:
    """Убрать призывы к действию из текста (для информационных дублей)."""
    result = _ACTION_PATTERN.sub(' ', text).strip()
    # Убрать двойные пробелы
    result = re.sub(r' {2,}', ' ', result)
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
) -> None:
    """
    Создать уведомление в БД и отправить через активные каналы.

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
    from database import Notification, NotificationSettings, Employee

    try:
        # 1. Создать запись Notification в БД
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
        db.flush()

        # 2. Загрузить настройки уведомлений сотрудника
        settings = db.query(NotificationSettings).filter_by(
            employee_id=employee_id
        ).first()

        if not settings:
            # Роли, работающие с надзором, получают notify_supervision=True по умолчанию
            employee_obj = db.query(Employee).filter_by(id=employee_id).first()
            supervision_roles = {
                'ДАН', 'Старший менеджер проектов',
                'Руководитель студии', 'admin', 'director',
            }
            is_senior_manager = bool(
                employee_obj and employee_obj.position == 'Старший менеджер проектов'
            )
            default_supervision = bool(
                employee_obj and employee_obj.role in supervision_roles
            )
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

        # 3. Проверить флаг типа события
        event_flag_map = {
            'assigned': settings.notify_assigned,
            'crm_stage_change': settings.notify_crm_stage,
            'deadline': settings.notify_deadline,
            'payment': settings.notify_payment,
            'supervision': settings.notify_supervision,
        }
        if not event_flag_map.get(event_type, False):
            db.commit()
            return

        # 3.1 Проверить фильтр по типу проекта
        if project_type:
            project_type_flag_map = {
                'individual': settings.notify_individual,
                'template': settings.notify_template,
                'supervision': settings.notify_supervision,
            }
            if not project_type_flag_map.get(project_type, True):
                db.commit()
                return

        # 3.2 Для дублированных уведомлений — проверить дубль-флаги
        if is_duplicate:
            if not settings.notify_duplicate_info:
                db.commit()
                return

        # 3.3 Для уведомлений об оплатах — проверить право доступа
        if event_type == 'payment':
            from permissions import check_permission
            employee_obj = db.query(Employee).filter_by(id=employee_id).first()
            if not employee_obj:
                db.commit()
                return
            has_payment_access = (
                check_permission(employee_obj, 'payments.create', db) or
                check_permission(employee_obj, 'payments.update', db)
            )
            if not has_payment_access:
                db.commit()
                return

        db.commit()

        # 4. Отправить через Telegram если включён
        if settings.telegram_enabled:
            employee = db.query(Employee).filter_by(id=employee_id).first()
            if employee and employee.telegram_user_id:
                await _send_telegram(employee.telegram_user_id, title, message)

        # 5. Применить правила дублирования (только для основных уведомлений)
        if not is_duplicate and card_id:
            await _apply_duplication_rules(
                db, employee_id, event_type, title, message,
                related_entity_type, related_entity_id, project_type, card_id
            )

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
    from database import Employee, CRMCard

    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            return

        recipient = db.query(Employee).filter(Employee.id == original_recipient_id).first()
        if not recipient:
            return

        already_sent: set = {original_recipient_id}

        # Правило 1: Уведомления ст.менеджеру → дублируются руководителю студии + менеджеру
        if recipient.position == 'Старший менеджер проектов':
            # → Руководитель студии
            director = db.query(Employee).filter(
                Employee.position == 'Руководитель студии',
                Employee.status == 'активный',
            ).first()
            if director and director.id not in already_sent:
                await dispatch_notification(
                    db, director.id, event_type, title, message,
                    related_entity_type, related_entity_id,
                    project_type, card_id, is_duplicate=True,
                )
                already_sent.add(director.id)

            # → Менеджер (если назначен на карточку)
            if card.manager_id and card.manager_id not in already_sent:
                await dispatch_notification(
                    db, card.manager_id, event_type, title, message,
                    related_entity_type, related_entity_id,
                    project_type, card_id, is_duplicate=True,
                )
                already_sent.add(card.manager_id)

        # Правило 2: Уведомления СДП/ГАП → дублируются ст.менеджеру (без призывов)
        if recipient.position in ('СДП', 'ГАП'):
            if card.senior_manager_id and card.senior_manager_id not in already_sent:
                info_message = _strip_action_phrases(message)
                await dispatch_notification(
                    db, card.senior_manager_id, event_type, title, info_message,
                    related_entity_type, related_entity_id,
                    project_type, card_id, is_duplicate=True,
                )
                already_sent.add(card.senior_manager_id)

        # Правило 4: Шаблонные — Менеджер/ГАП → дублируются ст.менеджеру (без призывов)
        if project_type == 'template' and recipient.position in ('Менеджер', 'ГАП'):
            if card.senior_manager_id and card.senior_manager_id not in already_sent:
                info_message = _strip_action_phrases(message)
                await dispatch_notification(
                    db, card.senior_manager_id, event_type, title, info_message,
                    related_entity_type, related_entity_id,
                    project_type, card_id, is_duplicate=True,
                )
                already_sent.add(card.senior_manager_id)

    except Exception as e:
        logger.error(f"Ошибка _apply_duplication_rules для card_id={card_id}: {e}")


async def _send_telegram(telegram_user_id: int, title: str, message: str) -> None:
    """Отправить уведомление через Telegram Bot"""
    try:
        from telegram_service import get_telegram_service
        tg = get_telegram_service()
        if tg.bot_available:
            text = f"<b>{title}</b>\n{message}"
            await tg.send_message(telegram_user_id, text)
    except Exception as e:
        logger.warning(f"Не удалось отправить Telegram уведомление: {e}")
