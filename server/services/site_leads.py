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
    from services.lead_sla import lead_sla

    data = {c.name: getattr(lead, c.name) for c in SiteLead.__table__.columns if c.name != "ip"}
    data["sla"] = lead_sla(lead)
    data["processed_by_name"] = None
    if lead.processed_by:
        emp = db.query(Employee.full_name).filter(Employee.id == lead.processed_by).first()
        data["processed_by_name"] = emp[0] if emp else None
    data["contract_number"] = None
    if lead.contract_id:
        from database import Contract

        row = db.query(Contract.contract_number).filter(Contract.id == lead.contract_id).first()
        data["contract_number"] = row[0] if row else None
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
    elif lead.status == "done":
        # Заявку вернули в работу — таймер на принятие начинается заново
        lead.sla_start = datetime.utcnow()
        lead.sla_notified = 0
    lead.status = status
    db.commit()
    db.refresh(lead)
    return serialize_lead(db, lead)


CITY_CODES = {"москва": "МСК", "санкт-петербург": "СПБ"}


def _number(text):
    """«от 150 000 ₽» → 150000.0"""
    import re

    digits = re.sub(r"[^\d,.]", "", str(text or "")).replace(",", ".")
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def prepare_contract(db, lead_id, employee):
    """Кнопка «Создать договор» в заявке: найти клиента по телефону (последние 10 цифр) или создать,
    и подготовить предзаполнение формы договора из того, что посетитель выбрал на сайте."""
    import re

    from permissions import check_permission
    from sqlalchemy import func

    from database import Client

    lead = get_lead_or_404(db, lead_id)
    digits = re.sub(r"\D", "", lead.phone or "")[-10:]
    client = None
    if len(digits) == 10:
        client = db.query(Client).filter(func.right(func.regexp_replace(Client.phone, r"\D", "", "g"), 10) == digits).order_by(Client.id.desc()).first()
    created = False
    if not client:
        if not check_permission(employee, "clients.create", db):
            raise HTTPException(403, "Нет права создавать клиентов")
        client = Client(client_type="Физическое лицо", full_name=lead.name, phone=lead.phone)
        db.add(client)
        db.commit()
        db.refresh(client)
        created = True

    try:
        context = json.loads(lead.context or "{}")
    except ValueError:
        context = {}
    price = _number(context.get("price"))
    area = _number(context.get("area"))
    city = CITY_CODES.get((context.get("city") or "").strip().lower())
    prefill = {
        "client_id": client.id,
        "project_type": "Шаблонный" if lead.source == "ready_design" else "Индивидуальный",
        "agent_type": "ФЕСТИВАЛЬ",
        "comments": f"Заявка с сайта №{lead.id}\n{lead_text(lead)}",
    }
    if area:
        prefill["area"] = area
    if city:
        prefill["city"] = city
    if price and lead.source == "ready_design":
        prefill["total_amount"] = price
        prefill["advance_payment"] = price
    return {
        "client": {"id": client.id, "label": client.full_name or client.phone},
        "client_created": created,
        "prefill": prefill,
    }


def link_contract(db, lead_id, contract_id, employee):
    """Договор создан из заявки: привязываем и отмечаем заявку обработанной (таймер останавливается)."""
    from database import Contract

    lead = get_lead_or_404(db, lead_id)
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(404, "Договор не найден")
    lead.contract_id = contract.id
    lead.status = "done"
    lead.result = f"Создан договор № {contract.contract_number}" + (f"\n{lead.result}" if lead.result and "Создан договор" not in lead.result else "")
    lead.processed_by = employee.id
    lead.processed_at = datetime.utcnow()
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
