# -*- coding: utf-8 -*-
"""
E2E Tests: Управление сотрудниками
16 тестов -- CRUD сотрудников, каскадное удаление, отчёты, проверка прав.
"""

import pytest
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import (
    TEST_PREFIX, TEST_PASSWORD, REQUEST_TIMEOUT,
    api_get, api_post, api_put, api_delete, _http_session
)


# ==============================================================
# CRUD СОТРУДНИКОВ
# ==============================================================

class TestEmployeeCRUD:
    """CRUD операции с сотрудниками через API"""

    def _create_test_employee(self, api_base, admin_headers, suffix="crud",
                              phone="+79990099901", **overrides):
        """Вспомогательный метод: создать тестового сотрудника напрямую"""
        payload = {
            "full_name": f"{TEST_PREFIX}Employee {suffix}",
            "login": f"{TEST_PREFIX}emp_{suffix}",
            "phone": phone,
            "position": "Дизайнер",
            "department": "Проектный",
            "role": "Дизайнер",
            "password": TEST_PASSWORD,
            "status": "активный",
        }
        payload.update(overrides)
        resp = api_post(api_base, "/api/employees", admin_headers, json=payload)
        assert resp.status_code in (200, 201), (
            f"Ошибка создания сотрудника: {resp.status_code} {resp.text}"
        )
        return resp.json()

    def _delete_test_employee(self, api_base, admin_headers, employee_id):
        """Вспомогательный метод: удалить тестового сотрудника"""
        try:
            api_delete(api_base, f"/api/employees/{employee_id}", admin_headers)
        except Exception:
            pass

    @pytest.mark.critical
    def test_create_employee(self, api_base, admin_headers):
        """Создание сотрудника"""
        employee = self._create_test_employee(
            api_base, admin_headers,
            suffix="create",
            phone="+79990099001",
        )
        try:
            assert employee["id"] > 0
            assert employee["full_name"] == f"{TEST_PREFIX}Employee create"
            assert employee["position"] == "Дизайнер"
            assert employee["department"] == "Проектный"
            assert employee["role"] == "Дизайнер"
            assert employee["status"] == "активный"
        finally:
            self._delete_test_employee(api_base, admin_headers, employee["id"])

    def test_create_employee_duplicate_login(self, api_base, admin_headers):
        """Создание сотрудника с дублирующимся логином -> 400"""
        employee = self._create_test_employee(
            api_base, admin_headers,
            suffix="dup_login",
            phone="+79990099002",
        )
        try:
            # Повторная попытка с тем же логином
            resp = api_post(api_base, "/api/employees", admin_headers, json={
                "full_name": f"{TEST_PREFIX}Employee dup_login_2",
                "login": f"{TEST_PREFIX}emp_dup_login",
                "phone": "+79990099003",
                "position": "Чертёжник",
                "department": "Проектный",
                "role": "Чертёжник",
                "password": TEST_PASSWORD,
                "status": "активный",
            })
            assert resp.status_code == 400
            assert "занят" in resp.text.lower() or "login" in resp.text.lower()
        finally:
            self._delete_test_employee(api_base, admin_headers, employee["id"])

    def test_get_all_employees(self, api_base, admin_headers):
        """Получение списка всех сотрудников"""
        resp = api_get(api_base, "/api/employees", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # Как минимум admin

    def test_get_employee_by_id(self, api_base, admin_headers):
        """Получение сотрудника по ID"""
        employee = self._create_test_employee(
            api_base, admin_headers,
            suffix="get_by_id",
            phone="+79990099004",
        )
        try:
            resp = api_get(
                api_base,
                f"/api/employees/{employee['id']}",
                admin_headers
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == employee["id"]
            assert data["full_name"] == employee["full_name"]
            assert data["login"] == employee["login"]
        finally:
            self._delete_test_employee(api_base, admin_headers, employee["id"])

    def test_get_employee_not_found(self, api_base, admin_headers):
        """Получение несуществующего сотрудника -> 404"""
        resp = api_get(api_base, "/api/employees/999999", admin_headers)
        assert resp.status_code == 404

    def test_update_employee(self, api_base, admin_headers):
        """Обновление сотрудника"""
        employee = self._create_test_employee(
            api_base, admin_headers,
            suffix="update",
            phone="+79990099005",
        )
        try:
            resp = api_put(
                api_base,
                f"/api/employees/{employee['id']}",
                admin_headers,
                json={
                    "full_name": f"{TEST_PREFIX}Employee Updated",
                    "phone": "+79990099006",
                }
            )
            assert resp.status_code == 200
            updated = resp.json()
            assert updated["full_name"] == f"{TEST_PREFIX}Employee Updated"
            assert updated["phone"] == "+79990099006"

            # Проверяем через GET
            resp2 = api_get(
                api_base,
                f"/api/employees/{employee['id']}",
                admin_headers
            )
            assert resp2.status_code == 200
            assert resp2.json()["full_name"] == f"{TEST_PREFIX}Employee Updated"
        finally:
            self._delete_test_employee(api_base, admin_headers, employee["id"])

    def test_update_employee_not_found(self, api_base, admin_headers):
        """Обновление несуществующего сотрудника -> 404"""
        resp = api_put(
            api_base,
            "/api/employees/999999",
            admin_headers,
            json={"full_name": f"{TEST_PREFIX}Ghost"}
        )
        assert resp.status_code == 404

    def test_delete_employee(self, api_base, admin_headers):
        """Удаление сотрудника"""
        employee = self._create_test_employee(
            api_base, admin_headers,
            suffix="delete",
            phone="+79990099007",
        )
        # Удаляем
        resp = api_delete(
            api_base,
            f"/api/employees/{employee['id']}",
            admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

        # Проверяем что удалён
        resp2 = api_get(
            api_base,
            f"/api/employees/{employee['id']}",
            admin_headers
        )
        assert resp2.status_code == 404

    def test_delete_employee_not_found(self, api_base, admin_headers):
        """Удаление несуществующего сотрудника -> 404"""
        resp = api_delete(api_base, "/api/employees/999999", admin_headers)
        assert resp.status_code == 404


# ==============================================================
# КАСКАДНОЕ УДАЛЕНИЕ
# ==============================================================

class TestEmployeeCascadeDelete:
    """Каскадное удаление: сотрудник + user_session + activity_log"""

    @pytest.mark.critical
    def test_cascade_delete_with_session(self, api_base, admin_headers):
        """
        Каскадное удаление: создать сотрудника, залогиниться (создаст user_session),
        затем удалить и убедиться что всё каскадно удалено.
        """
        # 1. Создаём нового тестового сотрудника
        payload = {
            "full_name": f"{TEST_PREFIX}Cascade Employee",
            "login": f"{TEST_PREFIX}cascade_emp",
            "phone": "+79990099010",
            "position": "Менеджер",
            "department": "Исполнительный",
            "role": "Менеджер",
            "password": TEST_PASSWORD,
            "status": "активный",
        }
        resp = api_post(api_base, "/api/employees", admin_headers, json=payload)
        assert resp.status_code in (200, 201), (
            f"Ошибка создания сотрудника для каскадного теста: {resp.status_code} {resp.text}"
        )
        employee = resp.json()
        employee_id = employee["id"]

        try:
            # 2. Логинимся как этот сотрудник (создаёт user_session)
            login_resp = _http_session.post(
                f"{api_base}/api/auth/login",
                data={
                    "username": f"{TEST_PREFIX}cascade_emp",
                    "password": TEST_PASSWORD,
                },
                timeout=REQUEST_TIMEOUT
            )
            assert login_resp.status_code == 200, (
                f"Логин каскадного сотрудника не удался: {login_resp.status_code} {login_resp.text}"
            )
            assert "access_token" in login_resp.json()

            # 3. Удаляем сотрудника (каскадно удалит user_sessions, activity_log и т.д.)
            del_resp = api_delete(
                api_base,
                f"/api/employees/{employee_id}",
                admin_headers
            )
            assert del_resp.status_code == 200
            assert del_resp.json()["status"] == "success"

            # 4. Проверяем что сотрудник удалён
            get_resp = api_get(
                api_base,
                f"/api/employees/{employee_id}",
                admin_headers
            )
            assert get_resp.status_code == 404

            # 5. Логин удалённого сотрудника должен не работать
            login_resp2 = _http_session.post(
                f"{api_base}/api/auth/login",
                data={
                    "username": f"{TEST_PREFIX}cascade_emp",
                    "password": TEST_PASSWORD,
                },
                timeout=REQUEST_TIMEOUT
            )
            assert login_resp2.status_code == 401

        except Exception:
            # Гарантируем очистку при ошибке
            try:
                api_delete(api_base, f"/api/employees/{employee_id}", admin_headers)
            except Exception:
                pass
            raise

    def test_cascade_delete_with_activity_log(self, api_base, admin_headers):
        """
        Каскадное удаление: создание сотрудника генерирует activity_log,
        удаление должно каскадно удалить эти записи.
        """
        # Создаём сотрудника (это создаст запись в activity_log)
        payload = {
            "full_name": f"{TEST_PREFIX}Cascade Log Employee",
            "login": f"{TEST_PREFIX}cascade_log",
            "phone": "+79990099011",
            "position": "Замерщик",
            "department": "Исполнительный",
            "role": "Замерщик",
            "password": TEST_PASSWORD,
            "status": "активный",
        }
        resp = api_post(api_base, "/api/employees", admin_headers, json=payload)
        assert resp.status_code in (200, 201)
        employee = resp.json()
        employee_id = employee["id"]

        try:
            # Удаляем -- каскадное удаление activity_log не должно вызывать ошибок
            del_resp = api_delete(
                api_base,
                f"/api/employees/{employee_id}",
                admin_headers
            )
            assert del_resp.status_code == 200
            assert del_resp.json()["status"] == "success"

            # Убеждаемся что удалён
            get_resp = api_get(
                api_base,
                f"/api/employees/{employee_id}",
                admin_headers
            )
            assert get_resp.status_code == 404

        except Exception:
            try:
                api_delete(api_base, f"/api/employees/{employee_id}", admin_headers)
            except Exception:
                pass
            raise


# ==============================================================
# ОТЧЁТЫ ПО СОТРУДНИКАМ
# ==============================================================

class TestEmployeeReport:
    """Тесты endpoint отчёта по сотрудникам"""

    def test_employee_report_basic(self, api_base, admin_headers, test_employees):
        """Получение отчёта по сотруднику"""
        designer = test_employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        resp = api_get(
            api_base,
            "/api/reports/employee",
            admin_headers,
            params={"employee_id": designer["id"]}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["employee_id"] == designer["id"]
        assert data["employee_name"] == designer["full_name"]
        assert "total_stages" in data
        assert "completed_stages" in data
        assert "completion_rate" in data
        assert "total_payments" in data
        assert "stages" in data
        assert "payments" in data
        assert isinstance(data["stages"], list)
        assert isinstance(data["payments"], list)

    def test_employee_report_with_year_month(self, api_base, admin_headers, test_employees):
        """Получение отчёта по сотруднику за конкретный месяц"""
        sdp = test_employees.get('sdp')
        if not sdp:
            pytest.skip("Нет тестового СДП")

        resp = api_get(
            api_base,
            "/api/reports/employee",
            admin_headers,
            params={
                "employee_id": sdp["id"],
                "year": 2026,
                "month": 1,
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["employee_id"] == sdp["id"]
        assert isinstance(data["total_stages"], int)
        assert isinstance(data["total_payments"], (int, float))

    def test_employee_report_nonexistent(self, api_base, admin_headers):
        """Отчёт по несуществующему сотруднику -> 404"""
        resp = api_get(
            api_base,
            "/api/reports/employee",
            admin_headers,
            params={"employee_id": 999999}
        )
        assert resp.status_code == 404


# ==============================================================
# ПРОВЕРКА ПРАВ ДОСТУПА ПО РОЛЯМ
# ==============================================================

class TestEmployeeRolePermissions:
    """Проверка что не-админ роли не могут создавать/удалять сотрудников"""

    def test_designer_cannot_create_employee(self, api_base, role_tokens):
        """Дизайнер НЕ может создать сотрудника -> 403"""
        if 'designer' not in role_tokens:
            pytest.skip("Нет токена Дизайнера")

        resp = api_post(api_base, "/api/employees", role_tokens['designer'], json={
            "full_name": f"{TEST_PREFIX}No Create Designer",
            "login": f"{TEST_PREFIX}no_create_des",
            "phone": "+79990099020",
            "position": "Дизайнер",
            "department": "Проектный",
            "role": "Дизайнер",
            "password": TEST_PASSWORD,
            "status": "активный",
        })
        assert resp.status_code == 403

    def test_designer_cannot_delete_employee(self, api_base, role_tokens, test_employees):
        """Дизайнер НЕ может удалить сотрудника -> 403"""
        if 'designer' not in role_tokens:
            pytest.skip("Нет токена Дизайнера")

        surveyor = test_employees.get('surveyor')
        if not surveyor:
            pytest.skip("Нет тестового замерщика")

        resp = api_delete(
            api_base,
            f"/api/employees/{surveyor['id']}",
            role_tokens['designer']
        )
        assert resp.status_code == 403

    def test_gap_cannot_create_employee(self, api_base, role_tokens):
        """ГАП НЕ может создать сотрудника -> 403"""
        if 'gap' not in role_tokens:
            pytest.skip("Нет токена ГАП")

        resp = api_post(api_base, "/api/employees", role_tokens['gap'], json={
            "full_name": f"{TEST_PREFIX}No Create GAP",
            "login": f"{TEST_PREFIX}no_create_gap",
            "phone": "+79990099021",
            "position": "Замерщик",
            "department": "Исполнительный",
            "role": "Замерщик",
            "password": TEST_PASSWORD,
            "status": "активный",
        })
        assert resp.status_code == 403

    def test_gap_cannot_delete_employee(self, api_base, role_tokens, test_employees):
        """ГАП НЕ может удалить сотрудника -> 403"""
        if 'gap' not in role_tokens:
            pytest.skip("Нет токена ГАП")

        surveyor = test_employees.get('surveyor')
        if not surveyor:
            pytest.skip("Нет тестового замерщика")

        resp = api_delete(
            api_base,
            f"/api/employees/{surveyor['id']}",
            role_tokens['gap']
        )
        assert resp.status_code == 403

    def test_manager_cannot_create_employee(self, api_base, role_tokens):
        """Менеджер НЕ может создать сотрудника -> 403"""
        if 'manager' not in role_tokens:
            pytest.skip("Нет токена Менеджера")

        resp = api_post(api_base, "/api/employees", role_tokens['manager'], json={
            "full_name": f"{TEST_PREFIX}No Create Manager",
            "login": f"{TEST_PREFIX}no_create_mgr",
            "phone": "+79990099022",
            "position": "Замерщик",
            "department": "Исполнительный",
            "role": "Замерщик",
            "password": TEST_PASSWORD,
            "status": "активный",
        })
        assert resp.status_code == 403

    def test_sdp_cannot_create_employee(self, api_base, role_tokens):
        """СДП НЕ может создать сотрудника -> 403"""
        if 'sdp' not in role_tokens:
            pytest.skip("Нет токена СДП")

        resp = api_post(api_base, "/api/employees", role_tokens['sdp'], json={
            "full_name": f"{TEST_PREFIX}No Create SDP",
            "login": f"{TEST_PREFIX}no_create_sdp",
            "phone": "+79990099023",
            "position": "Замерщик",
            "department": "Исполнительный",
            "role": "Замерщик",
            "password": TEST_PASSWORD,
            "status": "активный",
        })
        assert resp.status_code == 403
