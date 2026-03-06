# -*- coding: utf-8 -*-
"""
Smoke Tests: Permissions & RBAC — проверка что роли работают.

Запуск: pytest tests/smoke/test_permissions_rbac.py -v --timeout=120
"""

import pytest
from datetime import datetime

from tests.smoke.conftest import (
    _get, _post, _put, _delete, TEST_PREFIX,
)


@pytest.mark.smoke
class TestPermissionsRead:
    """P1: Чтение прав и матрицы ролей."""

    def test_permission_definitions(self, admin_headers):
        """GET /permissions/definitions — список всех прав."""
        resp = _get("/api/permissions/definitions", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_role_matrix(self, admin_headers):
        """GET /permissions/role-matrix — матрица ролей."""
        resp = _get("/api/permissions/role-matrix", admin_headers)
        assert resp.status_code == 200

    def test_get_admin_permissions(self, admin_headers):
        """GET /permissions/1 — права admin."""
        resp = _get("/api/permissions/1", admin_headers)
        assert resp.status_code == 200


@pytest.mark.smoke
class TestPermissionsRBACEnforcement:
    """P1: RBAC — дизайнер не может удалять сотрудников."""

    def test_designer_cannot_delete_employee(self, admin_headers):
        """Дизайнер не может удалить сотрудника → 403."""
        ts = datetime.now().strftime('%H%M%S%f')[:8]
        emp = _post("/api/employees", admin_headers, json={
            "full_name": f"{TEST_PREFIX}RBAC_{ts}",
            "username": f"{TEST_PREFIX}rbac{ts}",
            "password": "test12345",
            "position": "Дизайнер",
            "department": "Проектный",
            "phone": f"+7888{ts}",
            "status": "активный",
        })
        if emp.status_code not in (200, 201):
            pytest.skip(f"Не удалось создать сотрудника: {emp.status_code}")
        emp_id = emp.json()["id"]

        try:
            # Логин дизайнера
            login = _post("/api/auth/login", {},
                          data={"username": f"{TEST_PREFIX}rbac{ts}", "password": "test12345"})
            assert login.status_code == 200
            designer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            # Попытка удалить другого сотрудника
            del_resp = _delete("/api/employees/1", designer_headers)
            assert del_resp.status_code in (403, 401), \
                f"Дизайнер смог удалить сотрудника: {del_resp.status_code}"
        finally:
            _delete(f"/api/employees/{emp_id}", admin_headers)

    def test_designer_can_read_crm_cards(self, admin_headers):
        """Дизайнер может читать CRM-карточки."""
        ts = datetime.now().strftime('%H%M%S%f')[:8]
        emp = _post("/api/employees", admin_headers, json={
            "full_name": f"{TEST_PREFIX}RBAC_R_{ts}",
            "username": f"{TEST_PREFIX}rbacr{ts}",
            "password": "test12345",
            "position": "Дизайнер",
            "department": "Проектный",
            "phone": f"+7889{ts}",
            "status": "активный",
        })
        if emp.status_code not in (200, 201):
            pytest.skip(f"Не удалось создать сотрудника: {emp.status_code}")
        emp_id = emp.json()["id"]

        try:
            login = _post("/api/auth/login", {},
                          data={"username": f"{TEST_PREFIX}rbacr{ts}", "password": "test12345"})
            assert login.status_code == 200
            designer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            resp = _get("/api/crm/cards", designer_headers,
                        params={"project_type": "Индивидуальный"})
            assert resp.status_code == 200
        finally:
            _delete(f"/api/employees/{emp_id}", admin_headers)

    def test_reset_permissions_to_defaults(self, admin_headers):
        """POST /permissions/{id}/reset-to-defaults."""
        ts = datetime.now().strftime('%H%M%S%f')[:8]
        emp = _post("/api/employees", admin_headers, json={
            "full_name": f"{TEST_PREFIX}RBAC_D_{ts}",
            "username": f"{TEST_PREFIX}rbacd{ts}",
            "password": "test12345",
            "position": "Дизайнер",
            "department": "Проектный",
            "phone": f"+7887{ts}",
            "status": "активный",
        })
        if emp.status_code not in (200, 201):
            pytest.skip(f"Не удалось создать сотрудника: {emp.status_code}")
        emp_id = emp.json()["id"]

        try:
            resp = _post(f"/api/permissions/{emp_id}/reset-to-defaults", admin_headers)
            assert resp.status_code in (200, 204)
        finally:
            _delete(f"/api/employees/{emp_id}", admin_headers)
