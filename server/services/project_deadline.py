"""
Единые правила сроков проекта CRM — используются карточкой, договором, выгрузками и дашбордом.

Норма — срок договора (contract_period, рабочие дни от START).
Не считаются просрочкой и сдвигают дедлайн:
  * время этапов вне объёма договора (is_in_contract_scope = False), включая текущий незавершённый;
  * ожидание после START («В ожидании»), включая идущее сейчас.
Ожидание до START сдвигает саму дату START и на дедлайн не влияет.

  дедлайн          = базовый дедлайн (card.deadline: START + норма или заданный вручную)
                     + дни вне объёма + ожидание после START
  факт с вне объёма = р.д. от START до закрытия/сегодня − ожидание после START
  факт по договору  = факт с вне объёма − дни вне объёма
  просрочка         = р.д. от дедлайна до закрытия/сегодня (если позже)
"""

from datetime import date, datetime, timedelta

from services.date_helpers import is_working_day, networkdays

CLOSED_COLUMN = "Выполненный проект"
WAIT_COLUMN = "В ожидании"
CLOSED_STATUSES = ("СДАН", "РАСТОРГНУТ")


def to_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def add_working_days(start, days):
    current, added = start, 0
    while added < days:
        current += timedelta(days=1)
        if is_working_day(current):
            added += 1
    return current


def business_days_since(start_dt, end_dt):
    """Рабочие дни ожидания так же, как их копит сервер при возобновлении (день постановки входит)."""
    if not start_dt or not end_dt:
        return 0
    current, days = start_dt, 0
    while current < end_dt:
        if is_working_day(current):
            days += 1
        current += timedelta(days=1)
    return days


def _is_work_entry(e):
    return e.executor_role != "header" and not (e.stage_code or "").endswith("_HDR") and e.status != "skipped"


def is_project_closed(card, contract):
    return card.column_name == CLOSED_COLUMN or (contract is not None and contract.status in CLOSED_STATUSES)


def _running_out_of_scope_days(work, dated, start, today, paused_since):
    """Дни текущего незавершённого этапа, если он вне объёма (например, ждём ответа клиента)."""
    last_order = max((e.sort_order or 0) for e in dated) if dated else -1
    pending = next((e for e in work if not to_date(e.actual_date) and (e.sort_order or 0) > last_order), None)
    if not pending or pending.is_in_contract_scope is not False:
        return 0
    last_date = max((to_date(e.actual_date) for e in dated), default=start)
    until = min(today, paused_since) if paused_since else today
    return networkdays(last_date, until)


def _iso(d):
    return d.isoformat() if d else None


def _waits(card, start):
    """(всего, после START, дата начала текущей паузы) — с учётом идущего сейчас «В ожидании»."""
    paused_since = to_date(card.paused_at) if card.column_name == WAIT_COLUMN and card.paused_at else None
    paused_now = business_days_since(card.paused_at, datetime.utcnow()) if paused_since else 0
    post = card.post_start_wait_days or 0
    if paused_since and start and paused_since >= start:
        post += paused_now
    return (card.total_pause_days or 0) + paused_now, post, paused_since


def _out_of_scope_days(work, dated, start, today, paused_since, closed):
    done = sum((e.actual_days or 0) for e in dated if e.is_in_contract_scope is False)
    if not start or closed:
        return done
    return done + _running_out_of_scope_days(work, dated, start, today, paused_since)


def _base_deadline(card, start, norm):
    stored = to_date(card.deadline)
    if stored:
        return stored
    return add_working_days(start, norm) if start and norm else None


def compute_project_metrics(card, contract, entries, today=None):
    """Метрики сроков проекта. entries — записи ProjectTimelineEntry договора."""
    today = today or date.today()
    entries = sorted(entries or [], key=lambda e: e.sort_order or 0)
    start_entry = next((e for e in entries if e.stage_code == "START"), None)
    start = to_date(start_entry.actual_date) if start_entry else None
    norm = int((contract.contract_period if contract else 0) or 0)
    closed = is_project_closed(card, contract)

    work = [e for e in entries if _is_work_entry(e)]
    dated = [e for e in work if to_date(e.actual_date)]
    closure = max((to_date(e.actual_date) for e in dated), default=None) if closed else None
    end = closure or today

    wait_total, wait_post, paused_since = _waits(card, start)
    out_scope_days = _out_of_scope_days(work, dated, start, today, paused_since, closed)

    base = _base_deadline(card, start, norm)
    deadline = add_working_days(base, out_scope_days + wait_post) if base else None
    overdue = networkdays(deadline, end) if deadline and end > deadline else 0
    fact_all = max(0, networkdays(start, end) - wait_post) if start else 0

    return {
        "start_date": _iso(start),
        "norm_days": norm,
        "deadline": _iso(deadline),
        "is_closed": closed,
        "closure_date": _iso(closure),
        "fact_days": max(0, fact_all - out_scope_days),
        "fact_days_all": fact_all,
        "out_of_scope_days": out_scope_days,
        "overdue_days": overdue,
        "wait_days_total": wait_total,
        "wait_days_pre_start": max(0, wait_total - wait_post),
        "wait_days_post_start": wait_post,
    }


def load_project_metrics(db, card, contract=None):
    from database import Contract, ProjectTimelineEntry

    if contract is None and card.contract_id:
        contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
    entries = db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == card.contract_id).all() if card.contract_id else []
    return compute_project_metrics(card, contract, entries)
