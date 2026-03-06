"""
Notification Dispatcher — центральный диспетчер уведомлений.
Создаёт запись Notification в БД и отправляет через активные каналы
(Telegram) в зависимости от настроек сотрудника.
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def dispatch_notification(
    db: Session,
    employee_id: int,
    event_type: str,
    title: str,
    message: str,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[int] = None,
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
            # Нет настроек — только запись в БД, без отправки
            db.commit()
            return

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

        # 3.1 Для уведомлений об оплатах — проверить право доступа
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

    except Exception as e:
        logger.error(f"Ошибка dispatch_notification для employee_id={employee_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass


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
