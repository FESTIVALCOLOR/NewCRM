# -*- coding: utf-8 -*-
"""
E2E Tests: Авторизация и роли
14 тестов — проверка аутентификации, ролей и прав доступа.
"""

import pytest
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import (
    TEST_PREFIX, TEST_PASSWORD, REQUEST_TIMEOUT,
    api_get, api_post, api_patch, api_delete, _http_session
)


# ==============================================================
# АУТЕНТИФИКАЦИЯ
# ==============================================================

class TestAuthentication:
    """Тесты аутентификации"""

    @pytest.mark.critical
    def test_admin_login_success(self, api_base):
        """ADMIN: успешная авторизация"""
        resp = _http_session.post(
            f"{api_base}/api/auth/login",
            data={"username": "admin", "password": "admin123"},
            timeout=REQUEST_TIMEOUT
        )
        if resp.status_code == 429:
            pytest.skip("Rate limit достигнут (conftest уже авторизовался)")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "employee_id" in data
        assert data["token_type"] == "bearer"

    def test_wrong_password_fails(self, api_base):
        """Неверный пароль: 401 (или 429 при rate-limit)"""
        resp = _http_session.post(
            f"{api_base}/api/auth/login",
            data={"username": "admin", "password": "wrong_password"},
            timeout=REQUEST_TIMEOUT
        )
        assert resp.status_code in (401, 429), f"Ожидался 401/429, получен {resp.status_code}"

    def test_nonexistent_user_fails(self, api_base):
        """Несуществующий пользователь: 401 (или 429 при rate-limit)"""
        resp = _http_session.post(
            f"{api_base}/api/auth/login",
            data={"username": "nonexistent_user_xyz", "password": "test"},
            timeout=REQUEST_TIMEOUT
        )
        assert resp.status_code in (401, 429), f"Ожидался 401/429, получен {resp.status_code}"

    def test_token_required_for_protected_endpoints(self, api_base):
        """Без токена: 401 на защищённых endpoints"""
        resp = _http_session.get(f"{api_base}/api/clients", timeout=REQUEST_TIMEOUT)
        assert resp.status_code in [401, 403], f"Ожидался 401/403, получен {resp.status_code}"

    def test_test_employees_can_login(self, api_base, test_employees):
        """Тестовые сотрудники могут авторизоваться"""
        import time
        for role_key, emp in test_employees.items():
            login = emp.get('login')
            if not login:
                continue
            resp = _http_session.post(
                f"{api_base}/api/auth/login",
                data={"username": login, "password": TEST_PASSWORD},
                timeout=REQUEST_TIMEOUT
            )
            if resp.status_code == 429:
                pytest.skip("Rate limit достигнут, пропускаем тест")
            assert resp.status_code == 200, (
                f"Авторизация {role_key} ({login}) не удалась: {resp.status_code}"
            )


# ==============================================================
# ДОСТУП ПО РОЛЯМ
# ==============================================================

class TestRoleAccess:
    """Проверка прав доступа по ролям"""

    def test_sdp_can_access_crm_cards(self, api_base, role_tokens):
        """СДП может получить CRM карточки"""
        if 'sdp' not in role_tokens:
            pytest.skip("Нет токена СДП")
        resp = api_get(api_base, "/api/crm/cards", role_tokens['sdp'],
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200

    def test_designer_can_access_crm_cards(self, api_base, role_tokens):
        """Дизайнер может получить CRM карточки (просмотр)"""
        if 'designer' not in role_tokens:
            pytest.skip("Нет токена Дизайнера")
        resp = api_get(api_base, "/api/crm/cards", role_tokens['designer'],
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200

    def test_dan_can_access_supervision_cards(self, api_base, role_tokens):
        """ДАН может получить карточки надзора"""
        if 'dan' not in role_tokens:
            pytest.skip("Нет токена ДАН")
        resp = api_get(api_base, "/api/supervision/cards", role_tokens['dan'])
        assert resp.status_code == 200

    def test_senior_manager_can_access_employees(self, api_base, role_tokens):
        """Старший менеджер может получить список сотрудников"""
        if 'senior_manager' not in role_tokens:
            pytest.skip("Нет токена Старшего менеджера")
        resp = api_get(api_base, "/api/employees", role_tokens['senior_manager'])
        assert resp.status_code == 200

    def test_manager_can_access_payments(self, api_base, role_tokens):
        """Менеджер может получить платежи"""
        if 'manager' not in role_tokens:
            pytest.skip("Нет токена Менеджера")
        resp = api_get(api_base, "/api/payments", role_tokens['manager'])
        assert resp.status_code == 200


# ==============================================================
# ОПЕРАЦИИ ПО РОЛЯМ
# ==============================================================

class TestRoleOperations:
    """Тесты операций с проверкой прав"""

    def test_designer_cannot_create_employee(self, api_base, role_tokens):
        """Дизайнер НЕ может создавать сотрудников"""
        if 'designer' not in role_tokens:
            pytest.skip("Нет токена Дизайнера")
        resp = api_post(api_base, "/api/employees", role_tokens['designer'], json={
            "full_name": f"{TEST_PREFIX}НеСоздастся",
            "phone": "+79990000099",
            "position": "Тест",
            "department": "Тест",
            "login": f"{TEST_PREFIX}no_create",
            "password": "test123",
            "status": "активный",
        })
        assert resp.status_code == 403, f"Дизайнер смог создать сотрудника: {resp.status_code}"

    def test_designer_cannot_delete_employee(self, api_base, role_tokens, test_employees):
        """Дизайнер НЕ может удалять сотрудников"""
        if 'designer' not in role_tokens:
            pytest.skip("Нет токена Дизайнера")
        # Попытка удалить замерщика (другого тестового сотрудника)
        surveyor = test_employees.get('surveyor')
        if not surveyor:
            pytest.skip("Нет тестового замерщика")
        resp = api_delete(api_base, f"/api/employees/{surveyor['id']}", role_tokens['designer'])
        assert resp.status_code == 403

    def test_admin_can_create_and_delete_client(self, api_base, admin_headers):
        """Администратор может создавать и удалять клиентов"""
        # Создание
        resp = api_post(api_base, "/api/clients", admin_headers, json={
            "client_type": "Физическое лицо",
            "full_name": f"{TEST_PREFIX}РОЛЬ_ТЕСТ",
            "phone": "+79990000098",
        })
        assert resp.status_code == 200
        client_id = resp.json()["id"]

        # Удаление
        resp = api_delete(api_base, f"/api/clients/{client_id}", admin_headers)
        assert resp.status_code == 200

    def test_gap_can_access_statistics(self, api_base, role_tokens):
        """ГАП может получить статистику"""
        if 'gap' not in role_tokens:
            pytest.skip("Нет токена ГАП")
        resp = api_get(api_base, "/api/statistics/dashboard", role_tokens['gap'])
        assert resp.status_code == 200
