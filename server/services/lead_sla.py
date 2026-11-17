"""
Таймер на принятие заявки с сайта.

Отсчёт идёт только в рабочее время: будни (с учётом праздников РФ) с 10:00 до 19:00 по Москве.
Если заявка пришла в нерабочее время — отсчёт начинается с ближайшего начала рабочего дня.

Контрольные точки (рабочие часы от начала отсчёта):
  12 ч — время на принятие; затем 3 напоминания каждые 3 ч (15, 18, 21);
  затем 6 напоминаний каждый час (22…27). На 27-м часу заявка считается просроченной.
На каждой точке всем, у кого есть доступ к заявкам, уходит повторное уведомление (CRM, Telegram, push).
"""

import asyncio
from datetime import datetime, timedelta
import logging

from services.date_helpers import is_working_day
from sqlalchemy import text

from database import SessionLocal, SiteLead

logger = logging.getLogger(__name__)

MSK_OFFSET = timedelta(hours=3)  # Москва без перехода на летнее время
WORK_START_HOUR = 10
WORK_END_HOUR = 19
CHECKPOINTS_H = (12, 15, 18, 21, 22, 23, 24, 25, 26, 27)
CHECK_INTERVAL_SEC = 60


def _day_bounds(moment):
    start = moment.replace(hour=WORK_START_HOUR, minute=0, second=0, microsecond=0)
    return start, start.replace(hour=WORK_END_HOUR)


def next_working_moment(moment):
    """Ближайший момент рабочего времени, не раньше moment (московское время)."""
    while True:
        if is_working_day(moment.date()):
            start, end = _day_bounds(moment)
            if moment < start:
                return start
            if moment < end:
                return moment
        moment = (moment + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def is_working_time(moment):
    return next_working_moment(moment) == moment


def working_seconds_between(start, end):
    """Сколько рабочих секунд между двумя моментами (московское время)."""
    total = 0.0
    moment = next_working_moment(start)
    while moment < end:
        _, day_end = _day_bounds(moment)
        total += (min(day_end, end) - moment).total_seconds()
        moment = next_working_moment(day_end)
    return total


def add_working_seconds(start, seconds):
    """Момент, когда от start пройдёт seconds рабочих секунд (московское время)."""
    moment = next_working_moment(start)
    while True:
        _, day_end = _day_bounds(moment)
        available = (day_end - moment).total_seconds()
        if seconds <= available:
            return moment + timedelta(seconds=seconds)
        seconds -= available
        moment = next_working_moment(day_end)


def _phase(passed):
    """Подпись текущего интервала по числу пройденных контрольных точек."""
    if passed == 0:
        return "first", "на принятие"
    if passed <= 3:
        return "three", f"повтор {passed} из 3"
    return "hour", f"повтор {passed - 3} из 6"


def _utc_iso(moment_msk):
    return (moment_msk - MSK_OFFSET).isoformat() + "Z"


def lead_sla(lead, now=None):
    """Состояние таймера новой заявки; None — заявка уже обработана."""
    if lead.status != "new":
        return None
    now_msk = (now or datetime.utcnow()) + MSK_OFFSET
    origin_msk = (lead.sla_start or lead.created_at or datetime.utcnow()) + MSK_OFFSET
    start_msk = next_working_moment(origin_msk)
    elapsed = working_seconds_between(start_msk, now_msk)
    passed = sum(1 for hours in CHECKPOINTS_H if hours * 3600 <= elapsed)
    state = {
        "started": now_msk >= start_msk,
        "starts_at": _utc_iso(start_msk),
        "working_now": is_working_time(now_msk),
        "passed": passed,
        "elapsed_seconds": int(elapsed),
    }
    if passed >= len(CHECKPOINTS_H):
        return {**state, "overdue": True, "phase": "overdue", "label": "просрочена", "remaining_seconds": 0, "period_seconds": 0, "next_at": None}
    target = CHECKPOINTS_H[passed] * 3600
    previous = CHECKPOINTS_H[passed - 1] * 3600 if passed else 0
    phase, label = _phase(passed)
    return {
        **state,
        "overdue": False,
        "phase": phase,
        "label": label,
        "remaining_seconds": int(target - elapsed),
        "period_seconds": target - previous,
        "next_at": _utc_iso(add_working_seconds(start_msk, target)),
    }


def _fmt_hours(seconds):
    hours = round(seconds / 3600, 1)
    return f"{int(hours) if hours == int(hours) else hours} раб. ч"


def _reminder_text(sla):
    if sla["overdue"]:
        return "Заявка с сайта просрочена", f"Заявка не обработана за {CHECKPOINTS_H[-1]} рабочих часов."
    head = f"Прошло {_fmt_hours(sla['elapsed_seconds'])} без обработки. Следующее напоминание через {_fmt_hours(sla['remaining_seconds'])}."
    return f"Заявка не обработана — напоминание ({sla['label']})", head


async def check_lead_sla_once():
    """Отправить повторные уведомления по необработанным заявкам, дошедшим до контрольной точки."""
    from services.notification_dispatcher import dispatch_notification
    from services.site_leads import _recipients, lead_text

    db = SessionLocal()
    try:
        for lead in db.query(SiteLead).filter(SiteLead.status == "new").all():
            sla = lead_sla(lead)
            if not sla or sla["passed"] <= (lead.sla_notified or 0):
                continue
            # Атомарно «занимаем» отправку: сервер работает в нескольких процессах.
            # После простоя уходит одно уведомление о последней точке, а не пачка пропущенных.
            claimed = db.execute(
                text("UPDATE site_leads SET sla_notified = :passed WHERE id = :id AND COALESCE(sla_notified, 0) < :passed AND status = 'new'"),
                {"passed": sla["passed"], "id": lead.id},
            ).rowcount
            db.commit()
            if not claimed:
                continue
            title, head = _reminder_text(sla)
            message = f"{head}\n{lead_text(lead)}"
            for (employee_id,) in _recipients(db):
                await dispatch_notification(db, employee_id, "site_lead", title, message, related_entity_type="site_lead", related_entity_id=lead.id)
            db.commit()
    finally:
        db.close()


async def lead_sla_loop():
    from services.site_leads import check_contact_reminders_once

    while True:
        try:
            await check_lead_sla_once()
        except Exception as e:
            logger.error(f"Таймер заявок: {e}")
        try:
            await check_contact_reminders_once()
        except Exception as e:
            logger.error(f"Напоминания о созвонах по заявкам: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SEC)
