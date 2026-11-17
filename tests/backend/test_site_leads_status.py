"""
Backend Tests — жизненный цикл заявки с сайта (server/services/site_leads.py):
new → done (обработана, в работе) → closed (итог positive / negative); возвраты; счётчики; создание договора.
"""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server"))

database = pytest.importorskip("database")
site_leads = pytest.importorskip("services.site_leads")

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


@pytest.fixture()
def db():
    from sqlalchemy.pool import StaticPool

    # Одна общая in-memory БД для всех сессий (фоновая проверка напоминаний открывает свою)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    tables = [
        database.Employee.__table__,
        database.Client.__table__,
        database.Contract.__table__,
        database.SiteLead.__table__,
        database.SiteLeadAction.__table__,
    ]
    database.Base.metadata.create_all(engine, tables=tables)
    session = sessionmaker(bind=engine)()
    manager = database.Employee(full_name="Иванова Светлана", login="man", position="Менеджер", phone="0", password_hash="x", department="Тест", status="активный")
    session.add(manager)
    session.commit()
    session.manager = manager
    session.factory = sessionmaker(bind=engine)
    yield session
    session.close()


def make_lead(db, source="pricing_plan"):
    lead = database.SiteLead(name="Тест", phone="+79990000000", source=source, status="new")
    db.add(lead)
    db.commit()
    return lead


def test_full_cycle_and_counts(db):
    lead = make_lead(db)
    with pytest.raises(HTTPException):
        site_leads.update_lead_status(db, lead.id, "done", "", db.manager)  # без результата нельзя
    data = site_leads.update_lead_status(db, lead.id, "done", "Перезвонить в среду", db.manager)
    assert data["status"] == "done" and data["processed_by_name"] == "Иванова Светлана"

    with pytest.raises(HTTPException):
        site_leads.update_lead_status(db, lead.id, "closed", "", db.manager)  # без итога нельзя
    data = site_leads.update_lead_status(db, lead.id, "closed", "", db.manager, "negative", "Дорого")
    assert (data["status"], data["outcome"], data["close_comment"], data["closed_by_name"]) == ("closed", "negative", "Дорого", "Иванова Светлана")
    assert data["result"] == "Перезвонить в среду"  # результат обработки сохраняется

    make_lead(db, source="ready_design")
    assert site_leads.count_by_status(db) == {"new": 1, "done": 0, "closed": 1}


def test_reopen_closed_to_work_clears_outcome(db):
    lead = make_lead(db)
    site_leads.update_lead_status(db, lead.id, "done", "Ждём ответ", db.manager)
    site_leads.update_lead_status(db, lead.id, "closed", "", db.manager, "positive")
    data = site_leads.update_lead_status(db, lead.id, "done", "", db.manager)  # «Вернуть в работу» без нового текста
    assert data["status"] == "done" and data["outcome"] is None and data["result"] == "Ждём ответ"


def test_back_to_new_restarts_timer(db):
    lead = make_lead(db)
    site_leads.update_lead_status(db, lead.id, "done", "Ок", db.manager)
    data = site_leads.update_lead_status(db, lead.id, "new", "", db.manager)
    assert data["status"] == "new" and data["sla"] is not None and data["sla_notified"] == 0


def test_several_actions_in_work(db):
    lead = make_lead(db)
    with pytest.raises(HTTPException):
        site_leads.add_lead_action(db, lead.id, "Позвонил", db.manager)  # новая — сначала «Обработать»
    site_leads.update_lead_status(db, lead.id, "done", "Перезвонить в среду", db.manager)
    with pytest.raises(HTTPException):
        site_leads.add_lead_action(db, lead.id, "   ", db.manager)  # пустое действие нельзя
    site_leads.add_lead_action(db, lead.id, "Перезвонил, договорились о замере", db.manager)
    data = site_leads.add_lead_action(db, lead.id, "Замер проведён, готовим КП", db.manager)
    assert [a["text"] for a in data["actions"]] == ["Перезвонил, договорились о замере", "Замер проведён, готовим КП"]
    assert data["actions"][0]["employee_name"] == "Иванова Светлана"
    assert data["result"] == "Перезвонить в среду" and data["status"] == "done"

    closed = site_leads.update_lead_status(db, lead.id, "closed", "", db.manager, "positive")
    assert len(closed["actions"]) == 2  # журнал виден и у закрытой
    site_leads.delete_lead(db, lead.id)
    assert db.query(database.SiteLeadAction).count() == 0


def test_next_contact_validation(db):
    from datetime import datetime, timedelta

    lead = make_lead(db)
    yesterday = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
    with pytest.raises(HTTPException):
        site_leads.update_lead_status(db, lead.id, "done", "Ок", db.manager, contact_date=yesterday)  # дата в прошлом
    with pytest.raises(HTTPException):
        site_leads.update_lead_status(db, lead.id, "done", "Ок", db.manager, contact_time="15:00")  # время без даты
    tomorrow = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
    data = site_leads.update_lead_status(db, lead.id, "done", "Созвон", db.manager, contact_date=tomorrow, contact_time="15:00")
    assert (data["next_contact_date"], data["next_contact_time"], data["next_contact_notified"]) == (tomorrow, "15:00", 0)
    # Новое действие без даты — назначение остаётся; с датой — переносится
    data = site_leads.add_lead_action(db, lead.id, "Клиент попросил перенести", db.manager)
    assert data["next_contact_date"] == tomorrow
    later = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d")
    data = site_leads.add_lead_action(db, lead.id, "Перенесли", db.manager, later, "")
    assert (data["next_contact_date"], data["next_contact_time"]) == (later, None)


def _fake_dispatch(monkeypatch, db):
    import services.notification_dispatcher as dispatcher

    sent = []

    async def fake_dispatch(_db, employee_id, _type, title, message, **_kw):
        sent.append((employee_id, title, message))

    monkeypatch.setattr(dispatcher, "dispatch_notification", fake_dispatch)
    monkeypatch.setattr(site_leads, "SessionLocal", db.factory)
    return sent


def test_contact_reminders_morning_and_before_time(db, monkeypatch):
    import asyncio
    from datetime import datetime

    sent = _fake_dispatch(monkeypatch, db)
    lead = make_lead(db)
    site_leads.update_lead_status(db, lead.id, "done", "Перезвонить", db.manager)
    lead.next_contact_date, lead.next_contact_time, lead.next_contact_by, lead.next_contact_notified = "2030-03-12", "15:30", db.manager.id, 0
    db.commit()

    def run(utc):
        return asyncio.run(site_leads.check_contact_reminders_once(utc))

    assert run(datetime(2030, 3, 12, 4, 0)) == []  # 07:00 МСК — рано
    assert run(datetime(2030, 3, 12, 7, 0)) == [(lead.id, "morning")]  # 10:00 МСК — утреннее
    assert run(datetime(2030, 3, 12, 7, 0)) == []  # повторно не шлём
    assert run(datetime(2030, 3, 12, 12, 10)) == []  # 15:10 МСК — ещё рано (за 15 мин — в 15:15)
    assert run(datetime(2030, 3, 12, 12, 16)) == [(lead.id, "soon")]  # 15:16 МСК
    assert run(datetime(2030, 3, 12, 12, 20)) == []
    assert len(sent) == 2 and all(s[0] == db.manager.id for s in sent)
    assert "12.03.2030 в 15:30" in sent[0][2] and "через 14 мин" in sent[1][1]


def test_contact_set_today_after_morning_still_reminds_before_time(db, monkeypatch):
    """Сценарий из жалобы: в 16:34 назначили созвон на сегодня 16:40 — напоминание должно прийти."""
    import asyncio
    from datetime import datetime

    sent = _fake_dispatch(monkeypatch, db)
    monkeypatch.setattr(site_leads, "_today_msk", lambda: datetime(2030, 3, 12, 16, 34))
    lead = make_lead(db)
    data = site_leads.update_lead_status(db, lead.id, "done", "Перезвонить", db.manager, contact_date="2030-03-12", contact_time="16:40")
    assert data["next_contact_notified"] == site_leads.CONTACT_MORNING_SENT  # утреннее пропускаем, перед временем — ждём
    assert asyncio.run(site_leads.check_contact_reminders_once(datetime(2030, 3, 12, 13, 34))) == [(lead.id, "soon")]
    assert "через 6 мин" in sent[0][1]

    # Время уже прошло на момент назначения — ничего не шлём; без времени после 9:00 — тоже
    data = site_leads.add_lead_action(db, lead.id, "Перенос", db.manager, "2030-03-12", "10:00")
    assert data["next_contact_notified"] == site_leads.CONTACT_ALL_SENT
    data = site_leads.add_lead_action(db, lead.id, "Без времени", db.manager, "2030-03-12", "")
    assert data["next_contact_notified"] == site_leads.CONTACT_ALL_SENT
    # На завтра — оба напоминания впереди
    data = site_leads.add_lead_action(db, lead.id, "На завтра", db.manager, "2030-03-13", "11:00")
    assert data["next_contact_notified"] == site_leads.CONTACT_NONE_SENT


def test_contract_created_normally_closes_open_leads_by_phone(db):
    done = make_lead(db)
    site_leads.update_lead_status(db, done.id, "done", "Думает", db.manager)
    new = make_lead(db)
    other = database.SiteLead(name="Другой", phone="+7 (911) 000-00-00", source="pricing_plan", status="new")
    db.add(other)
    db.commit()
    client = database.Client(client_type="Физическое лицо", full_name="Клиент", phone="8 999 000-00-00")
    db.add(client)
    db.commit()
    contract = database.Contract(client_id=client.id, project_type="Индивидуальный", contract_number="Д-7")
    db.add(contract)
    db.commit()
    closed = site_leads.close_leads_for_contract(db, contract, client, db.manager)
    assert sorted(closed) == sorted([done.id, new.id])
    db.refresh(done)
    db.refresh(other)
    assert (done.status, done.outcome, done.contract_id, done.result) == ("closed", "positive", contract.id, "Думает")
    assert other.status == "new"


def test_contract_from_lead_closes_positive(db):
    lead = make_lead(db, source="ready_design")
    client = database.Client(client_type="Физическое лицо", full_name="Клиент", phone="+79990000000")
    db.add(client)
    db.commit()
    contract = database.Contract(client_id=client.id, project_type="Шаблонный", contract_number="Д-1")
    db.add(contract)
    db.commit()
    data = site_leads.link_contract(db, lead.id, contract.id, db.manager)
    assert (data["status"], data["outcome"], data["contract_number"]) == ("closed", "positive", "Д-1")
    assert "Д-1" in data["close_comment"]
