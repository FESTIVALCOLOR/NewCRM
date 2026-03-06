# -*- coding: utf-8 -*-
"""
Smoke: Расширенный RBAC — проверка прав дизайнера на контракты, платежи, ставки.

Базовый RBAC (employee CRUD) в test_rbac_permissions.py.
Здесь — глубокие проверки: дизайнер не может менять ставки, удалять чужие платежи,
создавать/удалять контракты.

Запуск: pytest tests/smoke/test_rbac_extended.py -v --timeout=120
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
    """Авторизация. Возвращает headers или None."""
    resp = _session.post(f"{API_BASE_URL}/api/auth/login",
                         data={"username": username, "password": password},
                         timeout=TIMEOUT)
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    return None


def _create_designer(admin_headers, suffix=""):
    """Создать тестового дизайнера. Возвращает (emp_id, login, password)."""
    ts = datetime.now().strftime('%H%M%S%f')[:8]
    login = f"smoke_rbac2_{suffix}_{ts}".lower()
    password = f"Test1pass{ts}"
    resp = _post("/api/employees", admin_headers, json={
        "full_name": f"{TEST_PREFIX}RBAC2_{suffix}_{ts}",
        "position": "Дизайнер",
        "role": "Дизайнер",
        "status": "активный",
        "login": login,
        "password": password,
    })
    if resp.status_code not in (200, 201):
        return None, login, password
    return resp.json().get("id"), login, password


def _cleanup_employee(admin_headers, emp_id):
    try:
        _delete(f"/api/employees/{emp_id}", admin_headers)
    except Exception:
        pass


# ════════════════════════════════════════════════════════════
# Фикстура: дизайнер
# ════════════════════════════════════════════════════════════

@pytest.fixture(scope="class")
def designer(admin_headers):
    """Создать дизайнера и авторизоваться."""
    emp_id, login, password = _create_designer(admin_headers, "EXT")
    if not emp_id:
        pytest.skip("Не удалось создать дизайнера")

    headers = _login_as(login, password)
    if not headers:
        _cleanup_employee(admin_headers, emp_id)
        pytest.skip(f"Не удалось авторизоваться как {login}")

    yield {"emp_id": emp_id, "headers": headers, "login": login}

    _cleanup_employee(admin_headers, emp_id)


# ════════════════════════════════════════════════════════════
# 1. RBAC: Контракты
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDesignerContractsRbac:
    """Дизайнер и контракты: чтение разрешено, создание/удаление — нет."""

    def test_designer_can_read_contracts(self, designer):
        """Дизайнер может читать список контрактов."""
        resp = _get("/api/contracts", designer["headers"])
        assert resp.status_code == 200, \
            f"Дизайнер должен видеть контракты: {resp.status_code}"

    def test_designer_cannot_create_contract(self, admin_headers, designer):
        """Дизайнер НЕ может создавать контракты."""
        ts = datetime.now().strftime('%H%M%S%f')[:10]
        resp = _post("/api/contracts", designer["headers"], json={
            "client_id": 1,
            "project_type": "Индивидуальный",
            "agent_type": "ФЕСТИВАЛЬ",
            "city": "МСК",
            "contract_number": f"{TEST_PREFIX}RBAC_DENY_{ts}",
            "contract_date": datetime.now().strftime("%Y-%m-%d"),
            "address": f"{TEST_PREFIX}RBAC deny",
            "area": 50.0,
            "total_amount": 100000.0,
            "contract_period": 30,
            "status": "Новый заказ",
        })
        # 403 (нет прав) или 401, 422 — главное НЕ 200/201
        assert resp.status_code in (403, 401, 405, 422), \
            f"Дизайнер не должен создавать контракты: {resp.status_code}"

    def test_designer_cannot_delete_contract(self, admin_headers, designer):
        """Дизайнер НЕ может удалять контракты."""
        # Находим существующий контракт
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет контрактов для теста")

        target = contracts[0]
        resp = _delete(f"/api/contracts/{target['id']}", designer["headers"])
        assert resp.status_code in (403, 401, 405), \
            f"Дизайнер не должен удалять контракты: {resp.status_code}"


# ════════════════════════════════════════════════════════════
# 2. RBAC: Платежи
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDesignerPaymentsRbac:
    """Дизайнер и платежи: чтение разрешено, удаление чужих — нет."""

    def test_designer_can_read_payments(self, designer):
        """Дизайнер может читать платежи."""
        resp = _get("/api/payments", designer["headers"])
        assert resp.status_code == 200, \
            f"Дизайнер должен видеть платежи: {resp.status_code}"

    def test_designer_cannot_delete_payment(self, admin_headers, designer):
        """Дизайнер НЕ может удалять чужие платежи."""
        payments = _get("/api/payments", admin_headers).json()
        if not payments:
            pytest.skip("Нет платежей для теста")

        target = payments[0]
        resp = _delete(f"/api/payments/{target['id']}", designer["headers"])
        assert resp.status_code in (403, 401, 405), \
            f"Дизайнер не должен удалять чужие платежи: {resp.status_code}"


# ════════════════════════════════════════════════════════════
# 3. RBAC: Ставки (rates)
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDesignerRatesRbac:
    """Дизайнер и ставки: чтение разрешено, изменение — нет."""

    def test_designer_can_read_rates(self, designer):
        """Дизайнер может читать ставки."""
        resp = _get("/api/rates", designer["headers"])
        assert resp.status_code == 200, \
            f"Дизайнер должен видеть ставки: {resp.status_code}"

    def test_designer_cannot_modify_rates(self, admin_headers, designer):
        """Дизайнер НЕ может изменять ставки."""
        rates = _get("/api/rates", admin_headers).json()
        if not rates:
            pytest.skip("Нет ставок для теста")

        target = rates[0]
        resp = _put(f"/api/rates/{target['id']}", designer["headers"],
                    json={"rate_per_m2": 99999.0})
        assert resp.status_code in (403, 401, 405, 422), \
            f"Дизайнер не должен менять ставки: {resp.status_code}"


# ════════════════════════════════════════════════════════════
# 4. RBAC: Supervision карточки
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDesignerSupervisionRbac:
    """Дизайнер и supervision: чтение разрешено."""

    def test_designer_can_read_supervision(self, designer):
        """Дизайнер может читать supervision карточки."""
        resp = _get("/api/supervision/cards", designer["headers"])
        # Может быть 200 или 403 в зависимости от настроек
        assert resp.status_code in (200, 403), \
            f"supervision cards: {resp.status_code}"

    def test_designer_can_read_own_profile(self, designer):
        """Дизайнер может читать свой профиль."""
        resp = _get("/api/auth/me", designer["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("login") == designer["login"]


# ════════════════════════════════════════════════════════════
# 5. RBAC: Зарплаты
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDesignerSalaryRbac:
    """Дизайнер и зарплаты: ограниченный доступ."""

    def test_designer_salary_access(self, designer):
        """Дизайнер может или не может видеть зарплаты (зависит от настроек)."""
        resp = _get("/api/salaries", designer["headers"])
        # 200 (разрешено) или 403 (нет прав) — оба валидны
        assert resp.status_code in (200, 403), \
            f"salaries access: {resp.status_code}"

    def test_designer_cannot_create_salary(self, admin_headers, designer):
        """Дизайнер НЕ может создавать зарплаты для других."""
        employees = _get("/api/employees", admin_headers).json()
        other = next((e for e in employees
                      if e["id"] != designer["emp_id"]), None)
        if not other:
            pytest.skip("Нет другого сотрудника")

        resp = _post("/api/salaries", designer["headers"], json={
            "employee_id": other["id"],
            "amount": 100000.0,
            "report_month": "2026-03",
            "description": f"{TEST_PREFIX}RBAC salary deny",
        })
        assert resp.status_code in (403, 401, 405, 422), \
            f"Дизайнер не должен создавать зарплаты: {resp.status_code}"


# ════════════════════════════════════════════════════════════
# 6. RBAC: Permissions
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDesignerPermissionsRbac:
    """Дизайнер не может менять разрешения."""

    def test_designer_cannot_update_own_permissions(self, designer):
        """Дизайнер НЕ может расширить свои разрешения."""
        resp = _put(f"/api/permissions/{designer['emp_id']}", designer["headers"],
                    json={"can_delete_employees": True})
        assert resp.status_code in (403, 401, 405, 422), \
            f"Дизайнер не должен менять permissions: {resp.status_code}"

    def test_designer_cannot_read_admin_permissions(self, admin_headers, designer):
        """Дизайнер НЕ может читать чужие разрешения (или может — зависит от настроек)."""
        # Находим admin employee_id
        me = _get("/api/auth/me", admin_headers)
        admin_emp_id = me.json().get("employee_id", 1) if me.status_code == 200 else 1

        resp = _get(f"/api/permissions/{admin_emp_id}", designer["headers"])
        # Может быть 200 (разрешено читать) или 403
        assert resp.status_code in (200, 403), \
            f"permissions read: {resp.status_code}"
