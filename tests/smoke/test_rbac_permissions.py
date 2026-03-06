# -*- coding: utf-8 -*-
"""
Smoke: RBAC — проверка прав доступа от лица обычного сотрудника.

Создаём сотрудника-дизайнера, логинимся под ним, проверяем что он
НЕ может удалять/создавать сотрудников, но МОЖЕТ читать CRM карточки.

Запуск: pytest tests/smoke/test_rbac_permissions.py -v --timeout=120
"""
import pytest
from datetime import datetime
from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    TEST_PREFIX, TIMEOUT,
)

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import API_BASE_URL

_session = requests.Session()
_session.verify = False


def _login_as(username, password):
    """Авторизация под указанным пользователем. Возвращает headers или None."""
    resp = _session.post(f"{API_BASE_URL}/api/auth/login",
                         data={"username": username, "password": password},
                         timeout=TIMEOUT)
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    return None


def _create_test_employee(admin_headers, suffix=""):
    """Создать тестового сотрудника. Возвращает (employee_id, login, password)."""
    ts = datetime.now().strftime('%H%M%S%f')[:8]
    login = f"smoke_rbac_{suffix}_{ts}".lower()
    password = f"Test1pass{ts}"
    resp = _post("/api/employees", admin_headers, json={
        "full_name": f"{TEST_PREFIX}RBAC_{suffix}_{ts}",
        "position": "Дизайнер",
        "role": "Дизайнер",
        "status": "активный",
        "login": login,
        "password": password,
    })
    if resp.status_code not in (200, 201):
        return None, login, password
    return resp.json().get("id"), login, password


def _delete_employee(admin_headers, employee_id):
    """Удалить тестового сотрудника."""
    try:
        _delete(f"/api/employees/{employee_id}", admin_headers)
    except Exception:
        pass


@pytest.mark.smoke
class TestPermissionDefinitions:
    """Базовые endpoint'ы разрешений."""

    def test_permission_definitions_accessible(self, admin_headers):
        """GET /permissions/definitions доступен админу."""
        resp = _get("/api/permissions/definitions", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict)), "Определения разрешений должны быть списком или словарём"

    def test_admin_has_all_permissions(self, admin_headers):
        """Админ имеет полные права (логин admin = Руководитель отдела)."""
        me = _get("/api/auth/me", admin_headers)
        assert me.status_code == 200
        user_data = me.json()
        # Аккаунт admin в системе имеет роль "Руководитель отдела" + логин "admin"
        login = user_data.get("login", "")
        role = user_data.get("role", "")
        assert login == "admin" or role in (
            "Руководитель отдела", "Администратор", "admin"
        ), f"Ожидали логин admin или роль Руководитель, получили login='{login}' role='{role}'"


@pytest.mark.smoke
class TestDesignerRbac:
    """RBAC: Дизайнер — ограниченные права."""

    @pytest.fixture(scope="class")
    def designer_context(self, admin_headers):
        """Создать дизайнера и авторизоваться под ним."""
        emp_id, login, password = _create_test_employee(admin_headers, "DES")
        if not emp_id:
            pytest.skip("Не удалось создать тестового сотрудника")

        headers = _login_as(login, password)
        if not headers:
            _delete_employee(admin_headers, emp_id)
            pytest.skip(f"Не удалось авторизоваться как {login}")

        yield {"employee_id": emp_id, "headers": headers, "login": login}

        # Cleanup
        _delete_employee(admin_headers, emp_id)

    def test_designer_can_read_crm_cards(self, designer_context):
        """Дизайнер может читать CRM карточки."""
        headers = designer_context["headers"]
        resp = _get("/api/crm/cards", headers, params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200, \
            f"Дизайнер должен иметь доступ к CRM: {resp.status_code}"

    def test_designer_can_read_employees(self, designer_context):
        """Дизайнер может читать список сотрудников."""
        headers = designer_context["headers"]
        resp = _get("/api/employees", headers)
        assert resp.status_code == 200, \
            f"Дизайнер должен видеть сотрудников: {resp.status_code}"

    def test_designer_cannot_delete_employee(self, admin_headers, designer_context):
        """Дизайнер НЕ может удалить другого сотрудника."""
        headers = designer_context["headers"]
        # Пробуем удалить самого себя или другого — должен быть 403
        employees = _get("/api/employees", admin_headers).json()
        # Ищем любого НЕ-тестового сотрудника
        target = next((e for e in employees
                       if e["id"] != designer_context["employee_id"]
                       and TEST_PREFIX not in str(e.get("full_name", ""))), None)
        if not target:
            pytest.skip("Нет подходящего сотрудника для теста удаления")

        resp = _delete(f"/api/employees/{target['id']}", headers)
        assert resp.status_code in (403, 401, 405), \
            f"Дизайнер не должен удалять сотрудников: {resp.status_code} {resp.text}"

    def test_designer_cannot_create_employee(self, designer_context):
        """Дизайнер НЕ может создавать сотрудников."""
        headers = designer_context["headers"]
        ts = datetime.now().strftime('%H%M%S')
        resp = _post("/api/employees", headers, json={
            "full_name": f"{TEST_PREFIX}RBAC_DENY_{ts}",
            "position": "Тест",
            "login": f"rbac_deny_{ts}",
            "password": f"Test1pass{ts}",
        })
        # Может быть 403 или 401 или 422 (если нет прав, сервер может по-разному отвечать)
        assert resp.status_code in (403, 401, 405, 422), \
            f"Дизайнер не должен создавать сотрудников: {resp.status_code}"

    def test_designer_can_read_own_profile(self, designer_context):
        """Дизайнер может читать свой профиль."""
        headers = designer_context["headers"]
        resp = _get("/api/auth/me", headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("login") == designer_context["login"]

    def test_designer_cannot_update_permissions(self, admin_headers, designer_context):
        """Дизайнер НЕ может менять разрешения."""
        headers = designer_context["headers"]
        emp_id = designer_context["employee_id"]

        resp = _put(f"/api/permissions/{emp_id}", headers,
                    json={"can_delete_employees": True})
        assert resp.status_code in (403, 401, 405, 422), \
            f"Дизайнер не должен менять permissions: {resp.status_code}"
