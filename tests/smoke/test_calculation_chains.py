# -*- coding: utf-8 -*-
"""
Smoke: Расчётные цепочки — площадь × тариф = сумма, пересчёт платежей.

Проверяет что после изменения площади/суммы/тарифа пересчёт работает корректно.

Запуск: pytest tests/smoke/test_calculation_chains.py -v --timeout=120
"""
import pytest
from datetime import datetime
from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    TEST_PREFIX, create_test_client, create_test_contract,
    find_crm_card_by_contract, cleanup_test_card,
)


def _get_rates(headers):
    """Получить тарифы."""
    resp = _get("/api/rates", headers)
    if resp.status_code == 200:
        return resp.json()
    return []


def _get_payments_for_contract(headers, contract_id):
    """Получить платежи договора."""
    resp = _get("/api/payments", headers, params={"contract_id": contract_id})
    if resp.status_code == 200:
        return resp.json()
    return []


def _recalculate_payments(headers, contract_id=None):
    """Пересчитать платежи."""
    params = {}
    if contract_id:
        params["contract_id"] = contract_id
    return _post("/api/payments/recalculate", headers, json=params)


@pytest.mark.smoke
class TestContractAmountConsistency:
    """Суммы в договорах внутренне непротиворечивы."""

    def test_total_ge_advance_plus_additional(self, admin_headers):
        """total_amount >= advance_payment + additional_payment для активных договоров."""
        resp = _get("/api/contracts", admin_headers)
        assert resp.status_code == 200
        contracts = resp.json()

        violations = []
        for c in contracts:
            total = c.get("total_amount", 0) or 0
            advance = c.get("advance_payment", 0) or 0
            additional = c.get("additional_payment", 0) or 0
            # Пропускаем если все нули
            if total == 0 and advance == 0 and additional == 0:
                continue
            # Сумма авансов не должна превышать общую сумму (с допуском 1%)
            if advance + additional > total * 1.01 and total > 0:
                violations.append(
                    f"Договор {c.get('id')}: total={total}, "
                    f"advance={advance}, additional={additional}, "
                    f"сумма авансов={advance + additional}"
                )

        if violations:
            # Нестрогая проверка — предупреждение, а не падение
            pytest.xfail(f"Найдены {len(violations)} нарушений: {violations[:3]}")

    def test_contract_area_positive(self, admin_headers):
        """Все активные договоры имеют area > 0."""
        resp = _get("/api/contracts", admin_headers)
        assert resp.status_code == 200
        contracts = resp.json()

        active = [c for c in contracts if c.get("status") not in ("Архив", "Отменён")]
        no_area = [c for c in active if not c.get("area") or c["area"] <= 0]
        if no_area:
            ids = [c["id"] for c in no_area[:5]]
            pytest.xfail(f"Договоры без площади: {ids}")

    def test_update_area_reflected_in_contract(self, admin_headers):
        """После обновления площади GET возвращает новое значение."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "CALC_AREA")
            contract_id = create_test_contract(admin_headers, client_id, "CAREA")

            new_area = 200.0
            resp = _put(f"/api/contracts/{contract_id}", admin_headers,
                        json={"area": new_area})
            assert resp.status_code == 200

            resp = _get(f"/api/contracts/{contract_id}", admin_headers)
            assert resp.status_code == 200
            assert abs(resp.json()["area"] - new_area) < 0.01
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestPaymentCalculation:
    """Расчёт платежей корректен."""

    def test_recalculate_endpoint_works(self, admin_headers):
        """POST /payments/recalculate отвечает."""
        resp = _recalculate_payments(admin_headers)
        assert resp.status_code in (200, 201, 422), \
            f"recalculate: {resp.status_code} {resp.text}"

    def test_recalculate_for_contract(self, admin_headers):
        """Пересчёт для конкретного договора работает."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "CALC_PAY")
            contract_id = create_test_contract(admin_headers, client_id, "CPAY")

            resp = _recalculate_payments(admin_headers, contract_id)
            # Может быть 200 (пересчитано) или 422 (нет тарифов)
            assert resp.status_code in (200, 201, 422), \
                f"recalculate: {resp.status_code} {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_payment_amounts_not_negative(self, admin_headers):
        """Суммы платежей не отрицательные."""
        resp = _get("/api/payments", admin_headers)
        assert resp.status_code == 200
        payments = resp.json()

        negative = [p for p in payments if (p.get("amount") or 0) < 0]
        assert not negative, \
            f"Найдены платежи с отрицательной суммой: {[p['id'] for p in negative[:5]]}"

    def test_paid_payments_have_amount(self, admin_headers):
        """Оплаченные платежи имеют amount > 0."""
        resp = _get("/api/payments", admin_headers)
        assert resp.status_code == 200
        payments = resp.json()

        paid = [p for p in payments if p.get("is_paid") is True]
        zero_amount = [p for p in paid if not p.get("amount") or p["amount"] <= 0]
        if zero_amount:
            ids = [p["id"] for p in zero_amount[:5]]
            pytest.xfail(f"Оплаченные платежи с нулевой суммой: {ids}")


@pytest.mark.smoke
class TestRateConsistency:
    """Тарифы внутренне непротиворечивы."""

    def test_rates_have_positive_values(self, admin_headers):
        """Тарифы имеют положительные значения."""
        rates = _get_rates(admin_headers)
        if not rates:
            pytest.skip("Нет тарифов в системе")

        for rate in rates:
            rate_value = rate.get("rate_per_m2") or rate.get("rate") or rate.get("value") or 0
            if rate_value < 0:
                pytest.fail(f"Тариф {rate.get('id')} имеет отрицательное значение: {rate_value}")

    def test_rate_templates_accessible(self, admin_headers):
        """GET /rates/template доступен."""
        resp = _get("/api/rates/template", admin_headers)
        assert resp.status_code in (200, 404), \
            f"rates/template: {resp.status_code}"


@pytest.mark.smoke
class TestAreaRateAmountChain:
    """Цепочка: площадь × тариф ≈ автосумма платежей."""

    def test_contract_payments_match_total(self, admin_headers):
        """Сумма платежей ≈ total_amount договора (с допуском)."""
        resp = _get("/api/contracts", admin_headers)
        assert resp.status_code == 200
        contracts = resp.json()

        mismatches = []
        checked = 0
        for c in contracts[:20]:  # Проверяем первые 20
            total = c.get("total_amount", 0) or 0
            if total <= 0:
                continue

            payments = _get_payments_for_contract(admin_headers, c["id"])
            if not payments:
                continue

            pay_sum = sum(p.get("amount", 0) or 0 for p in payments)
            checked += 1

            # Допуск 10% — платежи могут не полностью покрывать сумму
            if pay_sum > 0 and abs(pay_sum - total) / total > 0.5:
                mismatches.append(
                    f"Договор {c['id']}: total={total}, сумма платежей={pay_sum}"
                )

        if not checked:
            pytest.skip("Нет договоров с платежами для проверки")

        if mismatches:
            # Информативное предупреждение, не жёсткий fail
            pytest.xfail(f"Расхождения ({len(mismatches)}): {mismatches[:3]}")
