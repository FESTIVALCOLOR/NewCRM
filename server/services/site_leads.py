"""
Заявки с сайта (кнопки «Заказать» / «Заказать готовый дизайн»): сохранение, обработка и уведомление ответственных.
"""

from datetime import datetime
import json
import logging

from fastapi import HTTPException

from database import Employee, SessionLocal, SiteLead, SiteLeadAction

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
    data["closed_by_name"] = None
    if lead.closed_by:
        emp = db.query(Employee.full_name).filter(Employee.id == lead.closed_by).first()
        data["closed_by_name"] = emp[0] if emp else None
    data["contract_number"] = None
    if lead.contract_id:
        from database import Contract

        row = db.query(Contract.contract_number).filter(Contract.id == lead.contract_id).first()
        data["contract_number"] = row[0] if row else None
    data["actions"] = lead_actions(db, lead.id)
    return data


def lead_actions(db, lead_id):
    """Журнал действий по заявке (по порядку): [{id, text, employee_name, created_at}]."""
    rows = (
        db.query(SiteLeadAction, Employee.full_name)
        .outerjoin(Employee, Employee.id == SiteLeadAction.employee_id)
        .filter(SiteLeadAction.lead_id == lead_id)
        .order_by(SiteLeadAction.created_at, SiteLeadAction.id)
        .all()
    )
    return [{"id": a.id, "text": a.text, "employee_name": name, "created_at": a.created_at} for a, name in rows]


def add_lead_action(db, lead_id, text, employee, contact_date="", contact_time=""):
    """«Добавить действие» у обработанной заявки: ещё один шаг работы с клиентом (их может быть сколько угодно).
    Можно сразу назначить следующий созвон / встречу."""
    lead = get_lead_or_404(db, lead_id)
    text = (text or "").strip()
    if not text:
        raise HTTPException(400, "Опишите действие и его результат")
    if lead.status != "done":
        raise HTTPException(400, "Действия добавляются к заявкам в «Обработанных»")
    set_next_contact(lead, contact_date, contact_time, employee)
    db.add(SiteLeadAction(lead_id=lead.id, text=text, employee_id=employee.id, created_at=datetime.utcnow()))
    db.commit()
    db.refresh(lead)
    return serialize_lead(db, lead)


def list_leads(db, status=""):
    query = db.query(SiteLead)
    if status in ("new", "done", "closed"):
        query = query.filter(SiteLead.status == status)
    leads = query.order_by(SiteLead.created_at.desc()).limit(300).all()
    return [serialize_lead(db, lead) for lead in leads]


def count_by_status(db):
    """Счётчики вкладок: {"new": N, "done": N, "closed": N} (бейдж в меню — по новым)."""
    from sqlalchemy import func

    counts = dict(db.query(SiteLead.status, func.count(SiteLead.id)).group_by(SiteLead.status).all())
    return {key: counts.get(key, 0) for key in ("new", "done", "closed")}


def get_lead_or_404(db, lead_id):
    lead = db.query(SiteLead).filter(SiteLead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Заявка не найдена")
    return lead


def _clear_close(lead):
    lead.outcome = None
    lead.close_comment = None
    lead.closed_by = None
    lead.closed_at = None


def _today_msk():
    from services.lead_sla import MSK_OFFSET

    return datetime.utcnow() + MSK_OFFSET


def set_next_contact(lead, contact_date, contact_time, employee):
    """Назначить созвон / встречу по заявке: в этот день назначившему придёт напоминание (CRM, Telegram, push).
    Пустая дата — назначение не меняется."""
    contact_date = (contact_date or "").strip()
    contact_time = (contact_time or "").strip() or None
    if not contact_date:
        if contact_time:
            raise HTTPException(400, "Укажите дату созвона или встречи")
        return
    try:
        day = datetime.strptime(contact_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Неверная дата созвона или встречи")
    now_msk = _today_msk()
    if day < now_msk.date():
        raise HTTPException(400, "Дата созвона или встречи уже прошла")
    if contact_time:
        try:
            datetime.strptime(contact_time, "%H:%M")
        except ValueError:
            raise HTTPException(400, "Неверное время созвона или встречи")
    lead.next_contact_date = contact_date
    lead.next_contact_time = contact_time
    lead.next_contact_by = employee.id
    stage = CONTACT_NONE_SENT
    if day == now_msk.date():
        # Назначили на сегодня после утреннего напоминания — его не шлём (сотрудник и так в курсе),
        # но напоминание перед назначенным временем придёт; если и время уже прошло — ничего не шлём
        if now_msk.hour >= CONTACT_REMIND_HOUR:
            stage = CONTACT_MORNING_SENT
        moment = _contact_moment(lead)
        if (moment is None and stage == CONTACT_MORNING_SENT) or (moment is not None and now_msk >= moment):
            stage = CONTACT_ALL_SENT
    lead.next_contact_notified = stage


CONTACT_REMIND_HOUR = 9  # во сколько (МСК) в день созвона / встречи уходит утреннее напоминание
CONTACT_BEFORE_MIN = 15  # за сколько минут до назначенного времени — второе напоминание
# next_contact_notified: что уже отправлено
CONTACT_NONE_SENT, CONTACT_MORNING_SENT, CONTACT_ALL_SENT = 0, 1, 2


def _contact_moment(lead):
    """Назначенный момент созвона (МСК, без зоны) или None, если время не указано."""
    if not lead.next_contact_date or not lead.next_contact_time:
        return None
    return datetime.strptime(f"{lead.next_contact_date} {lead.next_contact_time}", "%Y-%m-%d %H:%M")


def contact_reminder_due(lead, now_msk):
    """Какое напоминание пора отправить: (kind, новое значение next_contact_notified) или None.
    kind: morning — утром в день созвона, soon — за CONTACT_BEFORE_MIN минут до назначенного времени."""
    from datetime import timedelta

    stage = lead.next_contact_notified or CONTACT_NONE_SENT
    if lead.status != "done" or stage >= CONTACT_ALL_SENT or lead.next_contact_date != now_msk.strftime("%Y-%m-%d"):
        return None
    moment = _contact_moment(lead)
    if moment is not None and now_msk >= moment - timedelta(minutes=CONTACT_BEFORE_MIN):
        return "soon", CONTACT_ALL_SENT
    if stage < CONTACT_MORNING_SENT and now_msk.hour >= CONTACT_REMIND_HOUR:
        return "morning", CONTACT_MORNING_SENT if moment is not None else CONTACT_ALL_SENT
    return None


def update_lead_status(db, lead_id, status, result, employee, outcome=None, comment="", contact_date="", contact_time=""):
    """Жизненный цикл заявки: new (новая) → done (обработана, в работе: ждём клиента, перезвон…)
    → closed (закрыта с итогом positive / negative).

    - new → done: обязателен результат обработки;
    - closed → done («Вернуть в работу»): итог снимается, результат обработки остаётся;
    - → closed: обязателен итог; комментарий необязателен;
    - → new («Вернуть в новые»): таймер на принятие начинается заново, результат хранится для истории.
    """
    lead = get_lead_or_404(db, lead_id)
    result = (result or "").strip()
    if status == "done":
        if lead.status == "closed":
            _clear_close(lead)
            if result:
                lead.result = result
        else:
            if not result:
                raise HTTPException(400, "Опишите результат обработки заявки")
            lead.result = result
            lead.processed_by = employee.id
            lead.processed_at = datetime.utcnow()
        set_next_contact(lead, contact_date, contact_time, employee)
    elif status == "closed":
        if outcome not in ("positive", "negative"):
            raise HTTPException(400, "Выберите итог: положительный или отрицательный")
        if lead.status == "new" and not lead.result:
            # Закрыли сразу из новых — считаем это и обработкой
            lead.processed_by = employee.id
            lead.processed_at = datetime.utcnow()
        lead.outcome = outcome
        lead.close_comment = (comment or "").strip() or None
        lead.closed_by = employee.id
        lead.closed_at = datetime.utcnow()
    else:
        if lead.status != "new":
            # Заявку вернули в новые — таймер на принятие начинается заново
            lead.sla_start = datetime.utcnow()
            lead.sla_notified = 0
        _clear_close(lead)
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
    """Договор создан из заявки: привязываем и закрываем заявку с положительным итогом (таймер останавливается)."""
    from database import Contract

    lead = get_lead_or_404(db, lead_id)
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(404, "Договор не найден")
    lead.contract_id = contract.id
    if not lead.result:
        lead.result = f"Создан договор № {contract.contract_number}"
        lead.processed_by = employee.id
        lead.processed_at = datetime.utcnow()
    lead.status = "closed"
    lead.outcome = "positive"
    lead.close_comment = f"Создан договор № {contract.contract_number}"
    lead.closed_by = employee.id
    lead.closed_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    return serialize_lead(db, lead)


def _phone_key(phone):
    import re

    digits = re.sub(r"\D", "", phone or "")
    return digits[-10:] if len(digits) >= 10 else None


def close_leads_for_contract(db, contract, client, employee):
    """Договор создан не кнопкой из заявки (обычным порядком) — открытые заявки (новые и обработанные)
    с тем же телефоном клиента закрываются положительно и привязываются к договору."""
    key = _phone_key(getattr(client, "phone", None))
    if not key:
        return []
    closed = []
    for lead in db.query(SiteLead).filter(SiteLead.status.in_(("new", "done"))).all():
        if _phone_key(lead.phone) != key:
            continue
        lead.contract_id = contract.id
        if not lead.result:
            lead.result = f"Создан договор № {contract.contract_number}"
            lead.processed_by = employee.id
            lead.processed_at = datetime.utcnow()
        lead.status = "closed"
        lead.outcome = "positive"
        lead.close_comment = f"Создан договор № {contract.contract_number}"
        lead.closed_by = employee.id
        lead.closed_at = datetime.utcnow()
        closed.append(lead.id)
    if closed:
        db.commit()
    return closed


def _fmt_contact(lead):
    day = datetime.strptime(lead.next_contact_date, "%Y-%m-%d").strftime("%d.%m.%Y")
    return f"{day} в {lead.next_contact_time}" if lead.next_contact_time else day


async def check_contact_reminders_once(now=None):
    """Напоминания о назначенном созвоне / встрече тому, кто назначил (если его нет или он уволен — всем,
    у кого есть доступ к заявкам): утром в этот день (CONTACT_REMIND_HOUR МСК) и, если указано время,
    за CONTACT_BEFORE_MIN минут до него. Возвращает [(lead_id, kind)]."""
    from services.lead_sla import MSK_OFFSET
    from services.notification_dispatcher import dispatch_notification
    from sqlalchemy import func
    from sqlalchemy import text as sql

    now_msk = (now or datetime.utcnow()) + MSK_OFFSET
    today = now_msk.strftime("%Y-%m-%d")
    db = SessionLocal()
    sent = []
    try:
        leads = db.query(SiteLead).filter(SiteLead.status == "done", SiteLead.next_contact_date == today, func.coalesce(SiteLead.next_contact_notified, 0) < CONTACT_ALL_SENT).all()
        for lead in leads:
            due = contact_reminder_due(lead, now_msk)
            if not due:
                continue
            kind, new_stage = due
            # Атомарно «занимаем» отправку — сервер работает в нескольких процессах
            claimed = db.execute(
                sql("UPDATE site_leads SET next_contact_notified = :new WHERE id = :id AND COALESCE(next_contact_notified, 0) = :old"),
                {"new": new_stage, "id": lead.id, "old": lead.next_contact_notified or CONTACT_NONE_SENT},
            ).rowcount
            db.commit()
            if not claimed:
                continue
            last = lead_actions(db, lead.id)
            note = last[-1]["text"] if last else (lead.result or "")
            message = f"Запланировано: {_fmt_contact(lead)}\n{lead_text(lead)}" + (f"\nПоследнее действие: {note}" if note else "")
            if kind == "soon":
                left = int((_contact_moment(lead) - now_msk).total_seconds() // 60)
                when = f"через {left} мин" if left > 0 else "сейчас"
                title = f"Созвон / встреча {when} ({lead.next_contact_time}) по заявке: {lead.name}"
            else:
                title = f"Сегодня созвон / встреча по заявке: {lead.name}"
            author = db.query(Employee).filter(Employee.id == lead.next_contact_by, Employee.status == "активный").first() if lead.next_contact_by else None
            recipients = [author.id] if author else [r[0] for r in _recipients(db)]
            for employee_id in recipients:
                await dispatch_notification(db, employee_id, "site_lead", title, message, related_entity_type="site_lead", related_entity_id=lead.id)
            db.commit()
            sent.append((lead.id, kind))
    finally:
        db.close()
    return sent


def delete_lead(db, lead_id):
    lead = get_lead_or_404(db, lead_id)
    db.query(SiteLeadAction).filter(SiteLeadAction.lead_id == lead.id).delete(synchronize_session=False)
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
