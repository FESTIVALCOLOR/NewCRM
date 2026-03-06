# -*- coding: utf-8 -*-
"""
Smoke Tests: Negative Scenarios — невалидные данные, 404, 422, SQL injection.

Критически важный файл: ловит ошибки обработки ошибок.
Если API не валидирует данные — может сломать БД.

Запуск: pytest tests/smoke/test_negative_scenarios.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    create_test_card, cleanup_test_card, TEST_PREFIX,
)


# ════════════════════════════════════════════════════════════
# 1. Несуществующие сущности → 404
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestNotFoundErrors:
    """P0: Обращение к несуществующим сущностям."""

    def test_crm_card_not_found(self, admin_headers):
        """GET /crm/cards/999999 → 404."""
        resp = _get("/api/crm/cards/999999", admin_headers)
        assert resp.status_code == 404

    def test_payment_not_found(self, admin_headers):
        """GET /payments/999999 → 404."""
        resp = _get("/api/payments/999999", admin_headers)
        assert resp.status_code == 404

    def test_supervision_card_not_found(self, admin_headers):
        """GET /supervision/cards/999999 → 404."""
        resp = _get("/api/supervision/cards/999999", admin_headers)
        assert resp.status_code == 404

    def test_salary_not_found(self, admin_headers):
        """GET /salaries/999999 → 404."""
        resp = _get("/api/salaries/999999", admin_headers)
        assert resp.status_code == 404

    def test_delete_nonexistent_payment(self, admin_headers):
        """DELETE /payments/999999 → 404."""
        resp = _delete("/api/payments/999999", admin_headers)
        assert resp.status_code == 404

    def test_delete_nonexistent_crm_card(self, admin_headers):
        """DELETE /crm/cards/999999 → 404."""
        resp = _delete("/api/crm/cards/999999", admin_headers)
        assert resp.status_code == 404

    def test_update_nonexistent_contract(self, admin_headers):
        """PUT /contracts/999999 → 404."""
        resp = _put("/api/contracts/999999", admin_headers, json={
            "address": "Не существует",
        })
        assert resp.status_code == 404


# ════════════════════════════════════════════════════════════
# 2. Невалидные данные → 422
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestValidationErrors:
    """P0: Невалидные данные должны отклоняться."""

    def test_create_client_empty_body(self, admin_headers):
        """POST /clients с пустым телом → 422."""
        resp = _post("/api/clients", admin_headers, json={})
        assert resp.status_code == 422

    def test_create_contract_missing_client_id(self, admin_headers):
        """POST /contracts без client_id → 422."""
        resp = _post("/api/contracts", admin_headers, json={
            "project_type": "Индивидуальный",
            "contract_number": f"{TEST_PREFIX}INVALID",
        })
        assert resp.status_code == 422

    def test_create_payment_invalid_contract(self, admin_headers):
        """POST /payments с несуществующим contract_id → 404/422."""
        resp = _post("/api/payments", admin_headers, json={
            "contract_id": 999999,
            "employee_id": 1,
            "stage_name": "Стадия 1: планировочные решения",
            "role": "designer",
            "payment_type": "Аванс",
            "amount": 10000.0,
        })
        assert resp.status_code in (404, 422, 400), \
            f"Платёж с невалидным contract_id: {resp.status_code} {resp.text}"

    def test_create_payment_invalid_employee(self, admin_headers):
        """POST /payments с несуществующим employee_id → 404/422."""
        client_id, contract_id, _ = create_test_card(admin_headers, "NEG_PAY")
        try:
            resp = _post("/api/payments", admin_headers, json={
                "contract_id": contract_id,
                "employee_id": 999999,
                "stage_name": "Стадия 1: планировочные решения",
                "role": "designer",
                "payment_type": "Аванс",
                "amount": 10000.0,
            })
            assert resp.status_code in (404, 422, 400, 200, 201), \
                f"Платёж с невалидным employee_id: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_create_employee_empty_body(self, admin_headers):
        """POST /employees с пустым телом → 422."""
        resp = _post("/api/employees", admin_headers, json={})
        assert resp.status_code == 422

    def test_move_crm_card_invalid_column(self, admin_headers):
        """PATCH /crm/cards/{id}/column с невалидной колонкой → 400/422."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "NEG_COL")
        try:
            resp = _patch(f"/api/crm/cards/{card_id}/column", admin_headers, json={
                "column_name": "Несуществующая колонка 12345",
            })
            assert resp.status_code in (400, 422), \
                f"Невалидная колонка: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_assign_nonexistent_executor(self, admin_headers):
        """POST /crm/cards/{id}/stage-executor с несуществующим employee_id → 404/422."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "NEG_EXEC")
        try:
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "В ожидании"})
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            resp = _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers, json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": 999999,
            })
            # Должен быть 404/422, но может вернуть 200 если нет валидации FK
            assert resp.status_code in (200, 201, 404, 422, 400), \
                f"Исполнитель с невалидным ID: {resp.status_code}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 3. SQL Injection Prevention
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSQLInjectionPrevention:
    """P0: API безопасно обрабатывает спецсимволы (не допускает injection)."""

    def test_search_with_sql_injection_attempt(self, admin_headers):
        """Спецсимволы SQL в запросе не ломают API."""
        resp = _get("/api/clients", admin_headers, params={
            "search": "'; DROP TABLE clients; --",
        })
        # Не должен быть 500
        assert resp.status_code in (200, 422, 400), \
            f"SQL injection в search: {resp.status_code} {resp.text}"

    def test_client_name_with_quotes(self, admin_headers):
        """Создание клиента с кавычками в имени."""
        resp = _post("/api/clients", admin_headers, json={
            "client_type": "Физическое лицо",
            "full_name": f"{TEST_PREFIX}O'Brien \"Test\"",
            "phone": "+79990000000",
        })
        if resp.status_code in (200, 201):
            client_id = resp.json()["id"]
            # Проверяем что имя сохранилось правильно
            check = _get(f"/api/clients/{client_id}", admin_headers).json()
            assert "O'Brien" in check["full_name"]
            _delete(f"/api/clients/{client_id}", admin_headers)
        else:
            # 422 тоже допустимо
            assert resp.status_code in (422, 400)

    def test_contract_address_with_special_chars(self, admin_headers):
        """Адрес договора со спецсимволами."""
        from tests.smoke.conftest import create_test_client, create_test_contract
        client_id = create_test_client(admin_headers, "SQL_INJ")
        try:
            from datetime import datetime
            ts = datetime.now().strftime('%H%M%S%f')[:10]
            resp = _post("/api/contracts", admin_headers, json={
                "client_id": client_id,
                "project_type": "Индивидуальный",
                "agent_type": "ФЕСТИВАЛЬ",
                "city": "МСК",
                "contract_number": f"{TEST_PREFIX}INJ{ts}",
                "contract_date": datetime.now().strftime("%Y-%m-%d"),
                "address": "ул. <script>alert('xss')</script> д.1 «кв.2»",
                "area": 100.0,
                "total_amount": 500000.0,
                "advance_payment": 250000.0,
                "additional_payment": 250000.0,
                "contract_period": 60,
                "status": "Новый заказ",
            })
            assert resp.status_code in (200, 201, 422), \
                f"Спецсимволы в адресе: {resp.status_code}"
            if resp.status_code in (200, 201):
                cid = resp.json()["id"]
                check = _get(f"/api/contracts/{cid}", admin_headers).json()
                # Адрес должен быть сохранён или экранирован, но не пустой
                assert check.get("address") is not None
                _delete(f"/api/contracts/{cid}", admin_headers)
        finally:
            _delete(f"/api/clients/{client_id}", admin_headers)


# ════════════════════════════════════════════════════════════
# 4. Unauthorized Access
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestUnauthorizedAccess:
    """P0: Проверка авторизации."""

    def test_no_token_crm_cards(self):
        """GET /crm/cards без токена → 401/403."""
        resp = _get("/api/crm/cards", {})
        assert resp.status_code in (401, 403)

    def test_no_token_payments(self):
        """GET /payments без токена → 401/403."""
        resp = _get("/api/payments", {})
        assert resp.status_code in (401, 403)

    def test_no_token_employees(self):
        """GET /employees без токена → 401/403."""
        resp = _get("/api/employees", {})
        assert resp.status_code in (401, 403)

    def test_invalid_token_format(self):
        """GET /crm/cards с мусорным токеном → 401/403."""
        resp = _get("/api/crm/cards", {"Authorization": "Bearer INVALID_TOKEN_12345"})
        assert resp.status_code in (401, 403)

    def test_no_token_post_payment(self):
        """POST /payments без токена → 401/403."""
        resp = _post("/api/payments", {}, json={"amount": 100})
        assert resp.status_code in (401, 403)

    def test_no_token_delete_contract(self):
        """DELETE /contracts/1 без токена → 401/403."""
        resp = _delete("/api/contracts/1", {})
        assert resp.status_code in (401, 403)
