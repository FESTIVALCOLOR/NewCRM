"""
Заявки с сайта (кнопки «Заказать» / «Заказать готовый дизайн»): сохранение и уведомление руководителей.
"""

import json
import logging

from constants import POSITION_STUDIO_DIRECTOR, ROLE_ADMIN, ROLE_DIRECTOR

from database import Employee, SessionLocal, SiteLead

logger = logging.getLogger(__name__)

METHOD_LABELS = {"call": "звонок", "whatsapp": "WhatsApp", "telegram": "Telegram", "max": "MAX"}
CONTEXT_LABELS = (
    ("design", "Дизайн"),
    ("plan", "Тариф"),
    ("city", "Город"),
    ("area", "Площадь, м²"),
    ("price", "Стоимость"),
    ("days", "Срок"),
)


def lead_text(lead):
    lines = [f"{lead.name}, {lead.phone}", f"Связаться: {METHOD_LABELS.get(lead.contact_method, lead.contact_method or 'звонок')}"]
    try:
        context = json.loads(lead.context or "{}")
    except ValueError:
        context = {}
    lines += [f"{label}: {context[key]}" for key, label in CONTEXT_LABELS if context.get(key)]
    if lead.comment:
        lines.append(f"Комментарий: {lead.comment}")
    return "\n".join(lines)


def _recipients(db):
    return (
        db.query(Employee.id)
        .filter(
            (Employee.position == POSITION_STUDIO_DIRECTOR) | (Employee.role.in_((ROLE_ADMIN, ROLE_DIRECTOR))),
            Employee.status == "активный",
        )
        .all()
    )


async def notify_new_lead(lead_id):
    """Уведомление в CRM (панель, Telegram, push) всем руководителям студии."""
    from services.notification_dispatcher import dispatch_notification

    db = SessionLocal()
    try:
        lead = db.query(SiteLead).filter(SiteLead.id == lead_id).first()
        if not lead:
            return
        message = lead_text(lead)
        for (employee_id,) in _recipients(db):
            await dispatch_notification(db, employee_id, "site_lead", "Новая заявка с сайта", message, related_entity_type="site_lead", related_entity_id=lead.id)
        db.commit()
    except Exception as e:
        logger.error(f"Уведомление о заявке с сайта #{lead_id}: {e}")
    finally:
        db.close()
