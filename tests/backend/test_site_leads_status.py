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
    engine = create_engine("sqlite://")
    tables = [database.Employee.__table__, database.Client.__table__, database.Contract.__table__, database.SiteLead.__table__]
    database.Base.metadata.create_all(engine, tables=tables)
    session = sessionmaker(bind=engine)()
    manager = database.Employee(full_name="Иванова Светлана", login="man", position="Менеджер", phone="0", password_hash="x", department="Тест", status="активный")
    session.add(manager)
    session.commit()
    session.manager = manager
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
