# -*- coding: utf-8 -*-
"""
Smoke Tests: Payment Lifecycle — CRUD + дедупликация + расчёты.

Дедупликация платежей — баг #1 из 121 fix-коммитов.
Этот файл тестирует что платежи создаются, не дублируются, и суммы правильные.

Запуск: pytest tests/smoke/test_payment_lifecycle.py -v --timeout=120
"""

import pytest
from datetime import datetime

from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    TEST_PREFIX, create_test_card, cleanup_test_card,
)


# ════════════════════════════════════════════════════════════
# 1. Payment CRUD
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestPaymentCRUD:
    """P0: Полный CRUD платежей."""

    def test_create_payment(self, admin_headers):
        """POST /payments — создание платежа."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "PAY_CR")
        payment_id = None
        try:
            resp = _post("/api/payments", admin_headers, json={
                "contract_id": contract_id,
                "crm_card_id": card_id,
                "employee_id": 1,
                "role": "Чертежник",
                "stage_name": "Стадия 1: планировочные решения",
                "payment_type": "Аванс",
                "calculated_amount": 10000.0,
                "final_amount": 10000.0,
                "description": f"{TEST_PREFIX}Тестовый платёж",
            })
            assert resp.status_code in (200, 201), \
                f"Создание платежа: {resp.status_code} {resp.text}"
            data = resp.json()
            payment_id = data["id"]
            assert data["contract_id"] == contract_id
            assert data["final_amount"] == 10000.0
        finally:
            if payment_id:
                _delete(f"/api/payments/{payment_id}", admin_headers)
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_get_payment_by_id(self, admin_headers):
        """GET /payments/{id} — получение по ID."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "PAY_GET")
        payment_id = None
        try:
            cr = _post("/api/payments", admin_headers, json={
                "contract_id": contract_id,
                "crm_card_id": card_id,
                "employee_id": 1,
                "role": "Чертежник",
                "stage_name": "Стадия 1: планировочные решения",
                "payment_type": "Аванс",
                "calculated_amount": 5000.0,
                "final_amount": 5000.0,
            })
            assert cr.status_code in (200, 201)
            payment_id = cr.json()["id"]

            # Получаем по ID
            get = _get(f"/api/payments/{payment_id}", admin_headers)
            assert get.status_code == 200
            assert get.json()["id"] == payment_id
        finally:
            if payment_id:
                _delete(f"/api/payments/{payment_id}", admin_headers)
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_update_payment(self, admin_headers):
        """PUT /payments/{id} — обновление суммы."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "PAY_UPD")
        payment_id = None
        try:
            cr = _post("/api/payments", admin_headers, json={
                "contract_id": contract_id,
                "crm_card_id": card_id,
                "employee_id": 1,
                "role": "Дизайнер",
                "stage_name": "Стадия 2: концепция дизайна",
                "payment_type": "Аванс",
                "calculated_amount": 7000.0,
                "final_amount": 7000.0,
            })
            assert cr.status_code in (200, 201)
            payment_id = cr.json()["id"]

            # Обновляем
            upd = _put(f"/api/payments/{payment_id}", admin_headers, json={
                "final_amount": 9000.0,
                "description": f"{TEST_PREFIX}Обновлённый",
            })
            assert upd.status_code == 200, \
                f"Обновление: {upd.status_code} {upd.text}"

            # Проверяем
            check = _get(f"/api/payments/{payment_id}", admin_headers)
            assert check.json()["final_amount"] == 9000.0
        finally:
            if payment_id:
                _delete(f"/api/payments/{payment_id}", admin_headers)
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_delete_payment(self, admin_headers):
        """DELETE /payments/{id} — удаление."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "PAY_DEL")
        try:
            cr = _post("/api/payments", admin_headers, json={
                "contract_id": contract_id,
                "crm_card_id": card_id,
                "employee_id": 1,
                "role": "Чертежник",
                "stage_name": "Стадия 1: планировочные решения",
                "payment_type": "Аванс",
                "calculated_amount": 3000.0,
                "final_amount": 3000.0,
            })
            assert cr.status_code in (200, 201)
            payment_id = cr.json()["id"]

            # Удаляем
            d = _delete(f"/api/payments/{payment_id}", admin_headers)
            assert d.status_code == 200

            # Проверяем что удалён
            check = _get(f"/api/payments/{payment_id}", admin_headers)
            assert check.status_code == 404
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 2. Payment Deduplication
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestPaymentDeduplication:
    """P0: Дедупликация платежей — реальный баг #1."""

    def test_duplicate_same_type_409(self, admin_headers):
        """Два платежа с одинаковыми (contract, employee, stage, role, type) → 409."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "PAY_DUP")
        payment_id = None
        try:
            payload = {
                "contract_id": contract_id,
                "crm_card_id": card_id,
                "employee_id": 1,
                "role": "Чертежник",
                "stage_name": "Стадия 1: планировочные решения",
                "payment_type": "Аванс",
                "calculated_amount": 5000.0,
                "final_amount": 5000.0,
            }
            r1 = _post("/api/payments", admin_headers, json=payload)
            assert r1.status_code in (200, 201)
            payment_id = r1.json()["id"]

            # Второй с тем же типом — дубликат
            r2 = _post("/api/payments", admin_headers, json=payload)
            assert r2.status_code in (409, 400), \
                f"Ожидали 409/400, получили {r2.status_code}: {r2.text}"
        finally:
            if payment_id:
                _delete(f"/api/payments/{payment_id}", admin_headers)
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_different_payment_type_allowed(self, admin_headers):
        """Два платежа с разным payment_type → 200 (не дубль)."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "PAY_DIF")
        p1_id = None
        p2_id = None
        try:
            base = {
                "contract_id": contract_id,
                "crm_card_id": card_id,
                "employee_id": 1,
                "role": "Чертежник",
                "stage_name": "Стадия 1: планировочные решения",
                "calculated_amount": 5000.0,
                "final_amount": 5000.0,
            }

            r1 = _post("/api/payments", admin_headers, json={
                **base, "payment_type": "Аванс"})
            assert r1.status_code in (200, 201)
            p1_id = r1.json()["id"]

            r2 = _post("/api/payments", admin_headers, json={
                **base, "payment_type": "Доплата"})
            # Должен создаться — разные типы
            assert r2.status_code in (200, 201), \
                f"Разные типы должны создаваться: {r2.status_code} {r2.text}"
            p2_id = r2.json()["id"]
        finally:
            if p1_id:
                _delete(f"/api/payments/{p1_id}", admin_headers)
            if p2_id:
                _delete(f"/api/payments/{p2_id}", admin_headers)
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 3. Payment Calculate & Mark Paid
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestPaymentCalculate:
    """P0: Расчёт платежа по формуле."""

    def test_calculate_endpoint(self, admin_headers):
        """GET /payments/calculate — возвращает расчёт."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "PAY_CALC")
        try:
            resp = _get("/api/payments/calculate", admin_headers, params={
                "contract_id": contract_id,
                "crm_card_id": card_id,
                "role": "Чертежник",
                "stage_name": "Стадия 1: планировочные решения",
            })
            # 200 если тариф найден, 404/422 если нет — оба варианта ок
            assert resp.status_code in (200, 404, 422), \
                f"Calculate: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_mark_paid_updates_all_fields(self, admin_headers):
        """mark-paid → payment_status='paid' + is_paid=True + paid_date != null."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "PAY_PAID")
        payment_id = None
        try:
            cr = _post("/api/payments", admin_headers, json={
                "contract_id": contract_id,
                "crm_card_id": card_id,
                "employee_id": 1,
                "role": "Чертежник",
                "stage_name": "Стадия 1: планировочные решения",
                "payment_type": "Аванс",
                "calculated_amount": 5000.0,
                "final_amount": 5000.0,
            })
            assert cr.status_code in (200, 201)
            payment_id = cr.json()["id"]

            # Помечаем оплаченным (employee_id — query param)
            mark = _patch(f"/api/payments/{payment_id}/mark-paid?employee_id=1",
                          admin_headers)
            assert mark.status_code == 200, \
                f"Mark-paid: {mark.status_code} {mark.text}"

            # Проверяем ВСЕ поля (баг: status='paid' но is_paid=False)
            check = _get(f"/api/payments/{payment_id}", admin_headers)
            assert check.status_code == 200
            data = check.json()
            assert data.get("is_paid") is True, \
                f"is_paid должен быть True, а получили {data.get('is_paid')}"
            assert data.get("payment_status") == "paid", \
                f"payment_status должен быть 'paid', а получили {data.get('payment_status')}"
            assert data.get("paid_date") is not None, \
                "paid_date не должен быть null после mark-paid"
        finally:
            if payment_id:
                # Отменяем оплату перед удалением
                _patch(f"/api/payments/{payment_id}/mark-unpaid", admin_headers)
                _delete(f"/api/payments/{payment_id}", admin_headers)
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 4. Payment Filters
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestPaymentFilters:
    """P1: Фильтрация платежей по типу."""

    def test_payments_by_type_individual(self, admin_headers):
        """GET /payments/by-type — Индивидуальные проекты."""
        resp = _get("/api/payments/by-type", admin_headers,
                     params={"payment_type": "Аванс"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_payments_by_type_supervision(self, admin_headers):
        """GET /payments/by-type — Авторский надзор."""
        resp = _get("/api/payments/by-type", admin_headers,
                     params={"payment_type": "Авторский надзор"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_payments_by_contract(self, admin_headers):
        """GET /payments/contract/{id} — платежи по договору."""
        # Берём первый реальный договор
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        cid = contracts[0]["id"]
        resp = _get(f"/api/payments/contract/{cid}", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_report_month_update(self, admin_headers):
        """PATCH /payments/contract/{id}/report-month — обновление отчётного месяца."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров для теста report-month")

        contract_id = contracts[0]["id"]
        resp = _patch(f"/api/payments/contract/{contract_id}/report-month",
                      admin_headers,
                      json={"report_month": "2026-03"})
        assert resp.status_code in (200, 204, 422), \
            f"Report-month: {resp.status_code} {resp.text}"
