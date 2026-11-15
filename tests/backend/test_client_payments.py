"""
Backend Tests — оплаты клиента по договору (server/services/client_payments.py).
Временная SQLite в памяти: план платежей, проведение оплаты и документ, нумерация, доп. соглашение,
уменьшение стоимости, расторжение, возврат, блокировка правки сумм.
"""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server"))

database = pytest.importorskip("database")
cp = pytest.importorskip("services.client_payments")

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    tables = [
        database.Employee.__table__,
        database.Client.__table__,
        database.Contract.__table__,
        database.ContractClientPayment.__table__,
        database.ClientPaymentDoc.__table__,
        database.ClientPaymentSetting.__table__,
        database.ActionHistory.__table__,
        database.CompanyRequisite.__table__,
        database.Payment.__table__,
    ]
    database.Base.metadata.create_all(engine, tables=[t for t in tables if t is not None])
    session = sessionmaker(bind=engine)()
    common = {"phone": "0", "password_hash": "x", "department": "Тест", "status": "активный"}
    director = database.Employee(full_name="Талер Илья", login="dir", position="Руководитель студии", **common)
    manager = database.Employee(full_name="Иванова Светлана", login="man", position="Менеджер", **common)
    client = database.Client(client_type="Физическое лицо", full_name="Петров Пётр", phone="+7 900 000-00-00")
    session.add_all([director, manager, client])
    session.commit()
    cp.save_settings(session, {"seller_name": "Талер Илья Игоревич", "seller_inn": "123456789012", "sbp_link": "https://qr.nspk.ru/TEST"})
    session.director, session.manager, session.client = director, manager, client
    yield session
    session.close()


def make_contract(db, project_type="Индивидуальный", **kw):
    data = {
        "client_id": db.client.id,
        "project_type": project_type,
        "contract_number": f"T-{project_type[:3]}-{kw.pop('n', 1)}",
        "contract_date": "2026-11-01",
        "area": 100,
        "total_amount": 300000,
        "advance_payment": 150000,
        "additional_payment": 90000,
        "third_payment": 60000,
    }
    data.update(kw)
    contract = database.Contract(**data)
    db.add(contract)
    db.commit()
    return contract


def rows(db, contract):
    return cp.contract_payments(db, contract)["payments"]


def pay(db, contract, kind_index, amount, method="sbp", date="2026-11-10", who=None):
    row = db.get(database.ContractClientPayment, rows(db, contract)[kind_index]["id"])
    return cp.pay(db, row, {"amount": amount, "date": date, "time": "14:30", "method": method}, who or db.manager)


def test_plan_created_from_contract_fields(db):
    individual = make_contract(db, advance_payment_paid_date="2026-11-05")
    plan = rows(db, individual)
    assert [p["kind"] for p in plan] == ["advance", "additional", "third"]
    assert plan[0]["status"] == "paid" and plan[0]["legacy"] is True and plan[0]["doc"] is None
    assert [p["amount"] for p in plan] == [150000, 90000, 60000]

    template = make_contract(db, "Шаблонный", n=2, advance_payment=None, additional_payment=None, third_payment=None, total_amount=80000)
    plan = rows(db, template)
    assert len(plan) == 1 and plan[0]["amount"] == 80000


def test_pay_issues_numbered_doc_with_director_as_cashier(db):
    contract = make_contract(db)
    doc1 = pay(db, contract, 0, 150000)
    doc2 = pay(db, contract, 1, 90000, method="cash")
    assert (doc1.number, doc2.number) == ("2026-0001", "2026-0002")
    assert doc1.data["cashier"] == "Руководитель студии Талер Илья"  # не менеджер, проводивший оплату
    assert doc1.data["calc_sign"] == "Приход" and "ПСН" in doc1.data["tax_system"]
    assert doc2.data["method_text"] == "наличные денежные средства"
    db.refresh(contract)
    assert contract.advance_payment_paid_date == "2026-11-10"  # зеркало в старое поле договора
    assert cp.summary(db, contract)["due"] == 60000
    pdf = cp.doc_pdf_bytes(db, doc1)
    assert pdf[:4] == b"%PDF"


def test_cancel_annuls_doc_and_number_not_reused(db):
    contract = make_contract(db)
    doc = pay(db, contract, 0, 150000)
    row = db.get(database.ContractClientPayment, rows(db, contract)[0]["id"])
    cp.cancel_paid(db, row, db.director)
    db.refresh(doc)
    assert doc.annulled_at is not None
    assert rows(db, contract)[0]["status"] == "planned"
    db.refresh(contract)
    assert contract.advance_payment_paid_date is None
    assert pay(db, contract, 0, 150000).number == "2026-0002"


def test_partial_payment_creates_rest(db):
    contract = make_contract(db)
    pay(db, contract, 0, 100000)
    plan = rows(db, contract)
    rest = [p for p in plan if p["kind"] == "rest"]
    assert len(rest) == 1 and rest[0]["amount"] == 50000
    assert cp.summary(db, contract)["due"] == 50000 + 90000 + 60000


def test_contract_amounts_locked_after_payment(db):
    contract = make_contract(db)
    cp.check_contract_update(db, contract, {"total_amount": 350000})  # до оплаты — можно
    pay(db, contract, 0, 150000)
    with pytest.raises(HTTPException) as err:
        cp.check_contract_update(db, contract, {"total_amount": 350000})
    assert err.value.status_code == 409
    cp.check_contract_update(db, contract, {"total_amount": 300000.0, "address": "новый"})  # без изменения суммы — можно


def test_extra_payment_increases_total(db):
    contract = make_contract(db)
    pay(db, contract, 0, 150000)
    cp.add_extra(db, contract, {"reason": "services", "amount": 40000, "basis": "ДС №1 от 12.11.2026"}, db.manager)
    db.refresh(contract)
    assert contract.total_amount == 340000
    extra = [p for p in rows(db, contract) if p["kind"] == "extra"][0]
    assert extra["amount"] == 40000 and extra["status"] == "planned"
    assert cp.summary(db, contract)["due"] == 90000 + 60000 + 40000


def test_decrease_cuts_unpaid_then_refunds(db):
    contract = make_contract(db)
    pay(db, contract, 0, 150000)
    pay(db, contract, 1, 90000)
    # Неоплачен только 3-й платёж (60 000); уменьшаем на 100 000 → 60 000 списывается, 40 000 к возврату
    info = cp.decrease(db, contract, {"amount": 100000, "basis": "ДС №2"}, db.manager)
    assert info["refund"] == 40000
    db.refresh(contract)
    assert contract.total_amount == 200000 and contract.third_payment == 0
    state = cp.summary(db, contract)
    assert state["due"] == 0 and state["to_refund"] == 40000

    refund_row = db.get(database.ContractClientPayment, [p for p in rows(db, contract) if p["direction"] == "out"][0]["id"])
    doc = cp.pay(db, refund_row, {"amount": 40000, "date": "2026-11-12", "method": "transfer"}, db.director)
    assert doc.data["calc_sign"] == "Возврат прихода"
    assert cp.summary(db, contract)["net_paid"] == 200000


def test_termination_refund_and_debt(db):
    refund_case = make_contract(db, n=3)
    pay(db, refund_case, 0, 150000)
    info = cp.terminate(db, refund_case, {"retained": 100000, "reason": "Соглашение о расторжении"}, db.manager)
    assert info == {"refund": 50000, "debt": 0}
    assert all(p["status"] == "cancelled" for p in rows(db, refund_case) if p["kind"] in ("additional", "third"))
    with pytest.raises(HTTPException):
        cp.terminate(db, refund_case, {"retained": 100000, "reason": "повтор"}, db.manager)

    debt_case = make_contract(db, n=4)
    pay(db, debt_case, 0, 150000)
    info = cp.terminate(db, debt_case, {"retained": 200000, "reason": "Расторжение"}, db.manager)
    assert info == {"refund": 0, "debt": 50000}


def test_link_message_and_qr(db):
    contract = make_contract(db)
    row = db.get(database.ContractClientPayment, rows(db, contract)[0]["id"])
    link = cp.payment_link(db, row, db.manager)
    assert link["amount"] == 150000 and "https://qr.nspk.ru/TEST" in link["message"]
    assert "Петров Пётр" in link["message"] and "150 000 ₽" in link["message"]
    assert link["qr_svg"].startswith("<svg")
    assert rows(db, contract)[0]["status"] == "link_sent"


def test_template_single_payment_follows_total_until_paid(db):
    contract = make_contract(db, "Шаблонный", n=5, advance_payment=None, additional_payment=None, third_payment=None, total_amount=80000)
    rows(db, contract)
    contract.total_amount = 95000
    db.commit()
    cp.sync_from_contract(db, contract)
    assert rows(db, contract)[0]["amount"] == 95000
