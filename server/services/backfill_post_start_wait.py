"""
Разовый перенос данных под единые правила сроков (services/project_deadline.py).

Раньше в crm_cards.deadline копились сдвиги (ожидание после START + согласование клиентом),
а total_pause_days включал дни согласования. Теперь:
  * deadline — только база (START + срок договора или заданный вручную);
  * post_start_wait_days — ожидание «В ожидании» после START;
  * total_pause_days — только «В ожидании» (до и после START).

Ожидание восстанавливается по истории действий (card_paused → card_resumed). Для карточек
без истории — оценка: сдвиг дедлайна относительно START + срок минус дни согласования клиентом.

Запуск в контейнере API:
  python -m services.backfill_post_start_wait            # пробный прогон, без записи
  python -m services.backfill_post_start_wait --apply    # запись + резервная копия в /app/uploads/_backups
"""

from datetime import datetime
import json
import os
import sys

from services.date_helpers import networkdays
from services.project_deadline import add_working_days, business_days_since, to_date

from database import ActionHistory, Contract, CRMCard, ProjectTimelineEntry, SessionLocal


def _approval_days(entries):
    return sum((e.actual_days or 0) for e in entries if e.executor_role == "Клиент" and "согласован" in (e.stage_name or "").lower() and to_date(e.actual_date) and e.status != "skipped")


def _waits_from_history(events, start):
    """(всего, после START) по завершённым интервалам «приостановлена → возобновлена»."""
    total = post = 0
    paused = None
    for action_type, when in events:
        if action_type == "card_paused":
            paused = when
        elif action_type == "card_resumed" and paused:
            days = business_days_since(paused, when)
            total += days
            if start and paused.date() >= start:
                post += days
            paused = None
    return total, post


def _estimate_from_shift(card, start, pure, stored, entries):
    if not stored or stored <= pure:
        return card.total_pause_days or 0, 0
    shift = networkdays(pure, stored)
    approval = min(shift, _approval_days(entries))
    post = max(0, shift - approval)
    return max(post, (card.total_pause_days or 0) - approval), post


def plan_card(card, contract, entries, events):
    start_entry = next((e for e in entries if e.stage_code == "START"), None)
    start = to_date(start_entry.actual_date) if start_entry else None
    period = int(contract.contract_period or 0) if contract and contract.contract_period else 0
    stored = to_date(card.deadline)
    pure = add_working_days(start, period) if start and period else None

    if events:
        total, post, source = *_waits_from_history(events, start), "история"
    elif pure:
        total, post, source = *_estimate_from_shift(card, start, pure, stored, entries), "оценка"
    else:
        return None
    # Сохранённый дедлайн позже базы — это накопленные сдвиги старой логики, оставляем базу
    new_deadline = pure.isoformat() if pure and stored and stored > pure else card.deadline

    new = {"deadline": new_deadline, "total_pause_days": total, "post_start_wait_days": post}
    old = {"deadline": card.deadline, "total_pause_days": card.total_pause_days or 0, "post_start_wait_days": getattr(card, "post_start_wait_days", 0) or 0}
    if new == old:
        return None
    return {"card_id": card.id, "contract_id": card.contract_id, "source": source, "old": old, "new": new}


def main(apply=False):
    db = SessionLocal()
    try:
        cards = db.query(CRMCard).all()
        contract_ids = list({c.contract_id for c in cards if c.contract_id})
        contracts = {c.id: c for c in db.query(Contract).filter(Contract.id.in_(contract_ids)).all()}
        entries = {}
        for e in db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id.in_(contract_ids)).all():
            entries.setdefault(e.contract_id, []).append(e)
        events = {}
        history = (
            db.query(ActionHistory.entity_id, ActionHistory.action_type, ActionHistory.action_date)
            .filter(ActionHistory.entity_type == "crm_card", ActionHistory.action_type.in_(("card_paused", "card_resumed")))
            .order_by(ActionHistory.action_date)
            .all()
        )
        for card_id, action_type, when in history:
            events.setdefault(card_id, []).append((action_type, when))

        plans = [p for c in cards if (p := plan_card(c, contracts.get(c.contract_id), entries.get(c.contract_id, []), events.get(c.id, [])))]
        for p in plans:
            print(f"card {p['card_id']} ({p['source']}): {p['old']} -> {p['new']}")
        print(f"Карточек к изменению: {len(plans)} из {len(cards)}")

        if not apply or not plans:
            return
        os.makedirs("/app/uploads/_backups", exist_ok=True)
        backup = f"/app/uploads/_backups/post_start_wait_backfill_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(backup, "w", encoding="utf-8") as f:
            json.dump(plans, f, ensure_ascii=False, indent=1, default=str)
        by_id = {c.id: c for c in cards}
        for p in plans:
            card = by_id[p["card_id"]]
            card.deadline = p["new"]["deadline"]
            card.total_pause_days = p["new"]["total_pause_days"]
            card.post_start_wait_days = p["new"]["post_start_wait_days"]
        db.commit()
        print(f"Записано. Резервная копия старых значений: {backup}")
    finally:
        db.close()


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
