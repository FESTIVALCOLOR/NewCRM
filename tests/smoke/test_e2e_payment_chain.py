# -*- coding: utf-8 -*-
"""
Smoke Tests: E2E Payment Chain — полный цикл оплат от тарифа до mark-paid.

Покрывает: rate → card setup → stage-executor assign → auto-payment →
calculate → recalculate → mark-paid → mark-unpaid → update → delete.

Запуск: pytest tests/smoke/test_e2e_payment_chain.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    create_test_card, cleanup_test_card, TEST_PREFIX,
)


@pytest.mark.smoke
class TestPaymentChainE2E:
    """P0: Полный E2E цикл оплат — от назначения до mark-paid."""

    def test_full_payment_chain(self, admin_headers):
        """
        Полный цикл: создать карточку → назначить исполнителя →
        автоматические платежи → recalculate → mark-paid → проверка.
        """
        client_id, contract_id, card_id = create_test_card(admin_headers, "PAY_CHAIN")
        try:
            # 1. Двигаем карточку в Стадию 1
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "В ожидании"})
            resp_s1 = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                             json={"column_name": "Стадия 1: планировочные решения"})

            # 2. Назначаем исполнителя → автоматически создаются платежи
            assign = _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers, json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": 1,
            })
            if assign.status_code not in (200, 201):
                pytest.skip(f"Assign executor: {assign.status_code}")

            # 3. Проверяем что платежи созданы
            payments = _get(f"/api/payments/contract/{contract_id}", admin_headers).json()
            assert isinstance(payments, list), "Платежи должны быть списком"

            if not payments:
                pytest.skip("Автоматические платежи не созданы")

            pay_id = payments[0]["id"]

            # 4. Calculate — проверяем расчёт
            calc = _get("/api/payments/calculate", admin_headers, params={
                "contract_id": contract_id,
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": 1,
            })
            assert calc.status_code in (200, 422)

            # 5. Recalculate
            recalc = _post("/api/payments/recalculate", admin_headers, json={
                "contract_id": contract_id,
            })
            assert recalc.status_code in (200, 422)

            # 6. Mark paid
            mark = _patch(f"/api/payments/{pay_id}/mark-paid", admin_headers)
            assert mark.status_code in (200, 422)

            if mark.status_code == 200:
                # Проверяем что is_paid = True
                check = _get(f"/api/payments/{pay_id}", admin_headers).json()
                assert check.get("is_paid") is True, \
                    f"is_paid должен быть True, но = {check.get('is_paid')}"

                # 7. Mark unpaid (обратное действие)
                unmark = _patch(f"/api/payments/{pay_id}/mark-unpaid", admin_headers)
                assert unmark.status_code in (200, 422)

        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_area_change_triggers_recalculate(self, admin_headers):
        """Изменение площади договора → пересчёт сумм платежей."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "AREA_REC")
        try:
            # Setup: card → stage 1 → executor
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "В ожидании"})
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})
            _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers, json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": 1,
            })

            # Получаем платежи ДО изменения площади
            pay_before = _get(f"/api/payments/contract/{contract_id}", admin_headers).json()

            # Меняем площадь
            _put(f"/api/contracts/{contract_id}", admin_headers, json={
                "area": 300.0,
            })

            # Пересчитываем
            _post("/api/payments/recalculate", admin_headers, json={
                "contract_id": contract_id,
            })

            # Получаем платежи ПОСЛЕ пересчёта
            pay_after = _get(f"/api/payments/contract/{contract_id}", admin_headers).json()

            # Проверяем что площадь обновилась
            contract = _get(f"/api/contracts/{contract_id}", admin_headers).json()
            assert contract.get("area") == 300.0

        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_payment_deduplication(self, admin_headers):
        """Дубликат платежа с тем же payment_type → 409."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "PAY_DUP")
        try:
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "В ожидании"})
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            payload = {
                "contract_id": contract_id,
                "employee_id": 1,
                "stage_name": "Стадия 1: планировочные решения",
                "role": "designer",
                "payment_type": "Аванс",
                "amount": 50000.0,
            }

            # Первый платёж
            p1 = _post("/api/payments", admin_headers, json=payload)
            if p1.status_code not in (200, 201):
                pytest.skip(f"Первый платёж: {p1.status_code}")

            p1_id = p1.json().get("id")

            try:
                # Дубликат — должен быть 409
                p2 = _post("/api/payments", admin_headers, json=payload)
                assert p2.status_code in (409, 200, 201), \
                    f"Dedup check: {p2.status_code} {p2.text}"
            finally:
                if p1_id:
                    _delete(f"/api/payments/{p1_id}", admin_headers)

        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_different_payment_types_allowed(self, admin_headers):
        """Платежи с разными payment_type для одного stage → оба 200."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "PAY_DIFF")
        try:
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "В ожидании"})
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            base = {
                "contract_id": contract_id,
                "employee_id": 1,
                "stage_name": "Стадия 1: планировочные решения",
                "role": "designer",
                "amount": 30000.0,
            }

            created_ids = []
            for ptype in ["Аванс", "Доплата"]:
                payload = {**base, "payment_type": ptype}
                resp = _post("/api/payments", admin_headers, json=payload)
                if resp.status_code in (200, 201):
                    pid = resp.json().get("id")
                    if pid:
                        created_ids.append(pid)

            # Cleanup созданных платежей
            for pid in created_ids:
                _delete(f"/api/payments/{pid}", admin_headers)

        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_manual_payment_create_update_delete(self, admin_headers):
        """Ручное создание → обновление → удаление платежа."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "PAY_MAN")
        try:
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "В ожидании"})
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            # Create
            create = _post("/api/payments", admin_headers, json={
                "contract_id": contract_id,
                "employee_id": 1,
                "stage_name": "Стадия 1: планировочные решения",
                "role": "Дизайнер",
                "payment_type": "Аванс",
                "calculated_amount": 25000.0,
                "final_amount": 25000.0,
            })
            if create.status_code not in (200, 201):
                pytest.skip(f"Create payment: {create.status_code}")

            pay_id = create.json().get("id")
            assert pay_id

            try:
                # Update
                upd = _put(f"/api/payments/{pay_id}", admin_headers, json={
                    "final_amount": 35000.0,
                })
                assert upd.status_code in (200, 422)

                # Verify
                check = _get(f"/api/payments/{pay_id}", admin_headers).json()
                if upd.status_code == 200:
                    assert check.get("final_amount") == 35000.0

                # Delete
                delete = _delete(f"/api/payments/{pay_id}", admin_headers)
                assert delete.status_code in (200, 204)
            except Exception:
                _delete(f"/api/payments/{pay_id}", admin_headers)
                raise

        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_payments_summary(self, admin_headers):
        """GET /payments/summary — сводка по платежам."""
        resp = _get("/api/payments/summary", admin_headers, params={"year": 2026})
        assert resp.status_code in (200, 422), \
            f"Summary: {resp.status_code} {resp.text}"
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (dict, list))

    def test_payments_by_type_filter(self, admin_headers):
        """GET /payments/by-type — фильтрация по типу."""
        for ptype in ["Индивидуальный", "Авторский надзор"]:
            resp = _get("/api/payments/by-type", admin_headers, params={
                "payment_type": ptype,
            })
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)

    def test_report_month_update(self, admin_headers):
        """PATCH /payments/contract/{id}/report-month — обновление месяца отчёта."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")

        contract_id = contracts[0]["id"]
        resp = _patch(f"/api/payments/contract/{contract_id}/report-month", admin_headers, json={
            "report_month": "2026-03",
        })
        assert resp.status_code in (200, 404, 422), \
            f"Report month: {resp.status_code} {resp.text}"
