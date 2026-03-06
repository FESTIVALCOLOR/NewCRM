# -*- coding: utf-8 -*-
"""
Smoke Tests: Payments Extended — расчёты, фильтры, ручные операции.

Покрывает: calculate, summary, all-optimized, recalculate,
supervision payments, crm payments, manual, by-supervision-card.

Запуск: pytest tests/smoke/test_payments_extended.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import (
    _get, _post, _patch,
    create_test_card, cleanup_test_card,
)


# ════════════════════════════════════════════════════════════
# 1. Summary & Calculate
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestPaymentsSummary:
    """P1: Сводка и расчёт платежей."""

    def test_payments_summary(self, admin_headers):
        """GET /payments/summary — общая сводка платежей."""
        resp = _get("/api/payments/summary", admin_headers, params={"year": 2026})
        assert resp.status_code in (200, 422), \
            f"Summary: {resp.status_code} {resp.text}"
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (dict, list))

    def test_payments_all_optimized(self, admin_headers):
        """GET /payments/all-optimized — оптимизированный список всех платежей."""
        resp = _get("/api/payments/all-optimized", admin_headers)
        assert resp.status_code == 200

    def test_payments_calculate_with_params(self, admin_headers):
        """GET /payments/calculate с параметрами — расчёт по формуле."""
        resp = _get("/api/payments/calculate", admin_headers, params={
            "area": 100,
            "rate_per_m2": 5000,
        })
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, dict)


# ════════════════════════════════════════════════════════════
# 2. Payments by Contract / Supervision
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestPaymentsFilters:
    """P1: Фильтрация платежей по контракту и типу."""

    def test_payments_by_contract(self, admin_headers):
        """GET /payments/contract/{id} — платежи конкретного договора."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        cid = contracts[0]["id"]
        resp = _get(f"/api/payments/contract/{cid}", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_payments_crm_by_contract(self, admin_headers):
        """GET /payments/crm/{contract_id} — CRM-платежи договора."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        cid = contracts[0]["id"]
        resp = _get(f"/api/payments/crm/{cid}", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_payments_supervision_by_contract(self, admin_headers):
        """GET /payments/supervision/{contract_id} — платежи надзора."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        cid = contracts[0]["id"]
        resp = _get(f"/api/payments/supervision/{cid}", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_payments_by_supervision_card(self, admin_headers):
        """GET /payments/by-supervision-card/{id} — платежи по карточке надзора."""
        cards = _get("/api/supervision/cards", admin_headers).json()
        if not cards:
            pytest.skip("Нет карточек надзора")
        sid = cards[0]["id"]
        resp = _get(f"/api/payments/by-supervision-card/{sid}", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ════════════════════════════════════════════════════════════
# 3. Recalculate & Manual
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestPaymentsOperations:
    """P1: Операции пересчёта и ручного редактирования."""

    def test_recalculate_payments(self, admin_headers):
        """POST /payments/recalculate — пересчёт платежей."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        cid = contracts[0]["id"]
        resp = _post("/api/payments/recalculate", admin_headers, json={
            "contract_id": cid,
        })
        assert resp.status_code in (200, 204, 422), \
            f"Recalculate: {resp.status_code} {resp.text}"

    def test_manual_payment_update(self, admin_headers):
        """PATCH /payments/{id}/manual — ручное изменение платежа."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "PAY_MAN")
        try:
            # Создаём платёж
            pay = _post("/api/payments", admin_headers, json={
                "contract_id": contract_id,
                "employee_id": 1,
                "stage_name": "Стадия 1: планировочные решения",
                "role": "designer",
                "payment_type": "Аванс",
                "amount": 10000.0,
            })
            if pay.status_code not in (200, 201):
                pytest.skip(f"Создание платежа: {pay.status_code}")
            pay_id = pay.json()["id"]

            # Ручное изменение
            resp = _patch(f"/api/payments/{pay_id}/manual", admin_headers, json={
                "amount": 15000.0,
                "is_manual": True,
            })
            assert resp.status_code in (200, 422), \
                f"Manual update: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)
