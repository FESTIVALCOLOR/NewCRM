"""
Заявки с сайта (кнопки «Заказать» / «Заказать готовый дизайн»): сохранение, обработка и уведомление ответственных.
"""

from datetime import datetime
import json
import logging

from fastapi import HTTPException

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
    """Все активные сотрудники с доступом к странице «Заявки» (по умолчанию: Руководитель студии,
    Старший менеджер, Менеджер — настраивается в ролях админки CRM)."""
    from permissions import check_permission

    employees = db.query(Employee).filter(Employee.status == "активный").all()
    return [(emp.id,) for emp in employees if check_permission(emp, "access.leads", db)]


# ── Общие операции для страницы «Заявки» в CRM и вкладки «Заявки» в панели сайта ──


def serialize_lead(db, lead):
    data = {c.name: getattr(lead, c.name) for c in SiteLead.__table__.columns if c.name != "ip"}
    data["processed_by_name"] = None
    if lead.processed_by:
        emp = db.query(Employee.full_name).filter(Employee.id == lead.processed_by).first()
        data["processed_by_name"] = emp[0] if emp else None
    return data


def list_leads(db, status=""):
    query = db.query(SiteLead)
    if status in ("new", "done"):
        query = query.filter(SiteLead.status == status)
    leads = query.order_by(SiteLead.created_at.desc()).limit(300).all()
    return [serialize_lead(db, lead) for lead in leads]


def get_lead_or_404(db, lead_id):
    lead = db.query(SiteLead).filter(SiteLead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Заявка не найдена")
    return lead


def update_lead_status(db, lead_id, status, result, employee):
    """«Обработана» — только с результатом обработки; «Вернуть в новые» — результат сохраняется для истории."""
    lead = get_lead_or_404(db, lead_id)
    result = (result or "").strip()
    if status == "done":
        if not result:
            raise HTTPException(400, "Опишите результат обработки заявки")
        lead.result = result
        lead.processed_by = employee.id
        lead.processed_at = datetime.utcnow()
    lead.status = status
    db.commit()
    db.refresh(lead)
    return serialize_lead(db, lead)


def delete_lead(db, lead_id):
    lead = get_lead_or_404(db, lead_id)
    db.delete(lead)
    db.commit()


async def notify_new_lead(lead_id):
    """Уведомление в CRM (панель, Telegram, push) всем, у кого есть доступ к заявкам."""
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
