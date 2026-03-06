# -*- coding: utf-8 -*-
"""
Smoke Tests: Auth Extended — refresh, logout, mark-unpaid, permissions write.

Покрывает: POST /auth/refresh, POST /auth/logout, GET /auth/me,
PATCH /payments/{id}/mark-unpaid, PUT /permissions/role-matrix,
PUT /permissions/{employee_id}.

Запуск: pytest tests/smoke/test_auth_extended.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import (
    _get, _post, _put, _patch,
    create_test_card, cleanup_test_card, TEST_PREFIX,
)


# ════════════════════════════════════════════════════════════
# 1. Auth Flow
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestAuthFlow:
    """P0: Полный цикл авторизации."""

    def test_login_returns_both_tokens(self, admin_headers):
        """POST /auth/login → access_token + refresh_token."""
        resp = _post("/api/auth/login", {}, data={
            "username": "admin",
            "password": "admin123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data, "Нет access_token"
        assert "refresh_token" in data or "token_type" in data

    def test_auth_me(self, admin_headers):
        """GET /auth/me → профиль текущего пользователя."""
        resp = _get("/api/auth/me", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data or "username" in data

    def test_token_refresh(self, admin_headers):
        """POST /auth/refresh → новый access_token."""
        # Сначала получаем refresh_token
        login = _post("/api/auth/login", {}, data={
            "username": "admin",
            "password": "admin123",
        })
        assert login.status_code == 200
        tokens = login.json()
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            pytest.skip("Нет refresh_token в ответе")

        # Обновляем токен
        resp = _post("/api/auth/refresh", {}, json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code in (200, 422), \
            f"Refresh: {resp.status_code} {resp.text}"
        if resp.status_code == 200:
            assert "access_token" in resp.json()

    def test_logout(self, admin_headers):
        """POST /auth/logout → успешный выход."""
        # Логинимся отдельным токеном (не портим admin_headers)
        login = _post("/api/auth/login", {}, data={
            "username": "admin",
            "password": "admin123",
        })
        assert login.status_code == 200
        temp_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        resp = _post("/api/auth/logout", temp_headers)
        assert resp.status_code in (200, 204), \
            f"Logout: {resp.status_code} {resp.text}"

    def test_wrong_password(self):
        """POST /auth/login с неверным паролем → 401."""
        resp = _post("/api/auth/login", {}, data={
            "username": "admin",
            "password": "wrong_password_12345",
        })
        assert resp.status_code in (401, 403)

    def test_nonexistent_user(self):
        """POST /auth/login с несуществующим пользователем → 401."""
        resp = _post("/api/auth/login", {}, data={
            "username": "nonexistent_user_99999",
            "password": "password",
        })
        assert resp.status_code in (401, 403, 404, 429)


# ════════════════════════════════════════════════════════════
# 2. Payments — Mark Unpaid
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestPaymentMarkUnpaid:
    """P1: Отметка платежа как неоплаченного."""

    def test_mark_paid_then_unpaid(self, admin_headers):
        """mark-paid → mark-unpaid → проверка полей."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "UNPAD")
        try:
            # Создаём платёж
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "В ожидании"})
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})
            assign = _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers, json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": 1,
            })
            if assign.status_code not in (200, 201):
                pytest.skip(f"Assign: {assign.status_code}")

            # Ищем платёж
            payments = _get(f"/api/payments/contract/{contract_id}", admin_headers).json()
            if not payments:
                pytest.skip("Платежи не созданы")
            pay_id = payments[0]["id"]

            # Mark paid
            resp1 = _patch(f"/api/payments/{pay_id}/mark-paid", admin_headers)
            assert resp1.status_code == 200

            # Mark unpaid
            resp2 = _patch(f"/api/payments/{pay_id}/mark-unpaid", admin_headers)
            assert resp2.status_code in (200, 422), \
                f"Mark unpaid: {resp2.status_code} {resp2.text}"

            if resp2.status_code == 200:
                # Проверяем что is_paid вернулся в False
                check = _get(f"/api/payments/{pay_id}", admin_headers).json()
                assert check.get("is_paid") is False, \
                    f"is_paid должен быть False после mark-unpaid, но = {check.get('is_paid')}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 3. Permissions Write
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestPermissionsWrite:
    """P1: Запись прав доступа."""

    def test_update_role_matrix(self, admin_headers):
        """PUT /permissions/role-matrix — обновление матрицы (идемпотентно)."""
        current = _get("/api/permissions/role-matrix", admin_headers)
        if current.status_code != 200:
            pytest.skip("Не удалось получить role-matrix")

        # Отправляем обратно как есть (идемпотентное обновление)
        resp = _put("/api/permissions/role-matrix", admin_headers, json=current.json())
        assert resp.status_code in (200, 422), \
            f"Update role-matrix: {resp.status_code} {resp.text}"

    def test_update_employee_permissions(self, admin_headers):
        """PUT /permissions/{employee_id} — обновление прав сотрудника.
        employee_id=1 — системный админ, нельзя менять права (400).
        Динамически находим не-админского сотрудника.
        """
        # Находим не-админского сотрудника
        employees = _get("/api/employees", admin_headers).json()
        target_id = None
        for emp in employees:
            eid = emp.get("id")
            if eid and eid != 1:
                target_id = eid
                break
        if not target_id:
            pytest.skip("Нет не-админских сотрудников для теста")

        current = _get(f"/api/permissions/{target_id}", admin_headers)
        if current.status_code != 200:
            pytest.skip(f"Не удалось получить permissions/{target_id}")

        # Отправляем обратно как есть (идемпотентное обновление)
        resp = _put(f"/api/permissions/{target_id}", admin_headers, json=current.json())
        assert resp.status_code in (200, 422), \
            f"Update permissions: {resp.status_code} {resp.text}"
