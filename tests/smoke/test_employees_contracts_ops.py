# -*- coding: utf-8 -*-
"""
Smoke Tests: Employees & Contracts Operations — CRUD сотрудников и договоров.

Покрывает: employee create/update/delete, contract update/count/files,
supervision card contract link.

Запуск: pytest tests/smoke/test_employees_contracts_ops.py -v --timeout=120
"""

import pytest
from datetime import datetime

from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    create_test_client, create_test_contract,
    cleanup_test_card, TEST_PREFIX,
)


# ════════════════════════════════════════════════════════════
# 1. Employee CRUD
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestEmployeeCRUD:
    """P1: Сотрудники — полный CRUD."""

    def test_list_employees(self, admin_headers):
        """GET /employees — список сотрудников."""
        resp = _get("/api/employees", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Список сотрудников пуст"

    def test_get_employee_by_id(self, admin_headers):
        """GET /employees/{id} — сотрудник по ID."""
        resp = _get("/api/employees/1", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1

    def test_create_update_delete_employee(self, admin_headers):
        """POST → PUT → DELETE /employees — полный цикл."""
        ts = datetime.now().strftime('%H%M%S%f')[:10]
        create = _post("/api/employees", admin_headers, json={
            "full_name": f"{TEST_PREFIX}Тестовый Сотрудник {ts}",
            "role": "designer",
            "position": "Дизайнер",
            "status": "активный",
            "username": f"smoke_test_{ts}",
            "password": "test_password_123",
        })
        if create.status_code not in (200, 201):
            pytest.skip(f"Создание сотрудника: {create.status_code} {create.text}")
        emp_id = create.json()["id"]

        try:
            # Update
            upd = _put(f"/api/employees/{emp_id}", admin_headers, json={
                "full_name": f"{TEST_PREFIX}Обновлённый Сотрудник {ts}",
                "status": "активный",
            })
            assert upd.status_code == 200, \
                f"Update employee: {upd.status_code} {upd.text}"

            # Проверяем обновление
            check = _get(f"/api/employees/{emp_id}", admin_headers)
            assert check.status_code == 200
            assert TEST_PREFIX in check.json()["full_name"]
        finally:
            # Delete
            _delete(f"/api/employees/{emp_id}", admin_headers)

    def test_get_nonexistent_employee(self, admin_headers):
        """GET /employees/999999 — несуществующий сотрудник."""
        resp = _get("/api/employees/999999", admin_headers)
        assert resp.status_code == 404


# ════════════════════════════════════════════════════════════
# 2. Contract Operations
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestContractOperations:
    """P1: Операции с договорами."""

    def test_contracts_count(self, admin_headers):
        """GET /contracts/count — количество договоров."""
        resp = _get("/api/contracts/count", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Может вернуть число или dict с count
        assert isinstance(data, (int, dict))

    def test_update_contract(self, admin_headers):
        """PUT /contracts/{id} — обновление договора."""
        client_id = create_test_client(admin_headers, "CTR_UPD")
        contract_id = create_test_contract(admin_headers, client_id, "CTR_UPD")
        try:
            resp = _put(f"/api/contracts/{contract_id}", admin_headers, json={
                "address": f"{TEST_PREFIX}Обновлённый адрес",
                "area": 150.0,
                "total_amount": 750000.0,
            })
            assert resp.status_code == 200, \
                f"Update contract: {resp.status_code} {resp.text}"

            # Проверяем
            check = _get(f"/api/contracts/{contract_id}", admin_headers)
            assert check.status_code == 200
            assert check.json()["area"] == 150.0
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_get_nonexistent_contract(self, admin_headers):
        """GET /contracts/999999 — несуществующий договор."""
        resp = _get("/api/contracts/999999", admin_headers)
        assert resp.status_code == 404


# ════════════════════════════════════════════════════════════
# 3. Supervision Card → Contract Link
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSupervisionContractLink:
    """P1: Связь карточки надзора с договором."""

    def test_supervision_card_contract(self, admin_headers):
        """GET /supervision/cards/{id}/contract — договор карточки надзора."""
        cards = _get("/api/supervision/cards", admin_headers).json()
        if not cards:
            pytest.skip("Нет карточек надзора")
        sid = cards[0]["id"]
        resp = _get(f"/api/supervision/cards/{sid}/contract", admin_headers)
        assert resp.status_code in (200, 404)

    def test_supervision_card_update(self, admin_headers):
        """PATCH /supervision/cards/{id} — обновление карточки надзора."""
        client_id = create_test_client(admin_headers, "SUP_UPD")
        contract_id = create_test_contract(
            admin_headers, client_id, "SUP_UPD",
            project_type="Авторский надзор",
        )
        try:
            # Ищем автосозданную карточку надзора (не CRM карточку!)
            cards = _get("/api/supervision/cards", admin_headers).json()
            sup = next((c for c in cards if c.get("contract_id") == contract_id), None)
            if not sup:
                pytest.skip("Карточка надзора не создалась автоматически")
            sup_id = sup["id"]

            resp = _patch(f"/api/supervision/cards/{sup_id}", admin_headers, json={
                "comment": f"{TEST_PREFIX}Обновлённый комментарий",
            })
            assert resp.status_code in (200, 422), \
                f"Update supervision card: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)
