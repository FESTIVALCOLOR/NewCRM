# -*- coding: utf-8 -*-
"""
E2E Tests: Отчёты по сотрудникам
14 тестов — GET endpoints отчётов, структура ответов, фильтрация, невалидные параметры.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get


@pytest.mark.e2e
class TestReports:
    """Тесты отчётов"""

    def test_employee_report_data(self, api_base, admin_headers, test_employees):
        """GET /api/reports/employee — данные отчёта сотрудника"""
        # Безопасное получение первого сотрудника: пропускаем тест если словарь пуст
        if not test_employees:
            pytest.skip("Тестовые сотрудники не созданы — пропускаем тест")
        emp = next(iter(test_employees.values()))
        resp = api_get(
            api_base, "/api/reports/employee", admin_headers,
            params={"employee_id": emp["id"], "year": 2026}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Проверяем обязательные ключи ответа
        assert "employee_id" in data, "Ожидается ключ employee_id"
        assert "employee_name" in data, "Ожидается ключ employee_name"
        assert "total_stages" in data, "Ожидается ключ total_stages"
        assert "completed_stages" in data, "Ожидается ключ completed_stages"
        assert "stages" in data, "Ожидается ключ stages"
        assert "payments" in data, "Ожидается ключ payments"
        # Числа неотрицательные
        assert data["employee_id"] == emp["id"]
        assert data["total_stages"] >= 0
        assert data["completed_stages"] >= 0
        # Списки этапов и платежей
        assert isinstance(data["stages"], list)
        assert isinstance(data["payments"], list)

    def test_employee_report_by_type(self, api_base, admin_headers):
        """GET /api/reports/employee-report — отчёт по типу проекта"""
        resp = api_get(
            api_base, "/api/reports/employee-report", admin_headers,
            params={"project_type": "Индивидуальный", "period": "year", "year": 2026}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Проверяем структуру ответа отчёта по типу проекта
        assert "completed" in data, "Ожидается ключ completed"
        assert "area" in data, "Ожидается ключ area"
        assert "deadlines" in data, "Ожидается ключ deadlines"
        assert "salaries" in data, "Ожидается ключ salaries"
        assert isinstance(data["completed"], list)
        assert isinstance(data["area"], list)
        assert isinstance(data["deadlines"], list)
        assert isinstance(data["salaries"], list)
        # Если данные есть — проверяем структуру элементов
        if data["completed"]:
            item = data["completed"][0]
            assert "employee_name" in item, "Ожидается ключ employee_name в completed"
            assert "count" in item, "Ожидается ключ count в completed"

    def test_employee_report_missing_params(self, api_base, admin_headers):
        """GET /api/reports/employee — без обязательных параметров → 422"""
        resp = api_get(api_base, "/api/reports/employee", admin_headers)
        # employee_id — обязательный параметр, FastAPI вернёт 422 Unprocessable Entity
        assert resp.status_code == 422, (
            f"Без employee_id ожидается 422, получено {resp.status_code}"
        )

    def test_employee_report_nonexistent(self, api_base, admin_headers):
        """GET /api/reports/employee с несуществующим employee_id=999999 — 404, не 500"""
        resp = api_get(
            api_base, "/api/reports/employee", admin_headers,
            params={"employee_id": 999999, "year": 2026}
        )
        # Несуществующий сотрудник: сервер должен вернуть 404, а не упасть с 500
        assert resp.status_code == 404, (
            f"Несуществующий сотрудник (999999): ожидается 404, получено {resp.status_code}"
        )

    def test_reports_require_auth(self, api_base):
        """GET /api/reports/employee без токена — 401"""
        resp = api_get(api_base, "/api/reports/employee", {},
                       params={"employee_id": 1})
        assert resp.status_code in (401, 403)

    def test_employee_report_all_keys_present(self, api_base, admin_headers, test_employees):
        """GET /api/reports/employee — полный набор ключей ответа"""
        if not test_employees:
            pytest.skip("Тестовые сотрудники не созданы — пропускаем тест")
        emp = next(iter(test_employees.values()))
        resp = api_get(
            api_base, "/api/reports/employee", admin_headers,
            params={"employee_id": emp["id"]}
        )
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = (
            "employee_id", "employee_name", "position",
            "total_stages", "completed_stages", "completion_rate",
            "total_payments", "stages", "payments"
        )
        for key in expected_keys:
            assert key in data, f"Ожидается ключ '{key}' в ответе /reports/employee"
        assert isinstance(data["completion_rate"], (int, float))
        assert isinstance(data["total_payments"], (int, float))

    def test_employee_report_filter_by_year(self, api_base, admin_headers, test_employees):
        """GET /api/reports/employee с фильтром по году возвращает корректный ответ"""
        if not test_employees:
            pytest.skip("Тестовые сотрудники не созданы — пропускаем тест")
        emp = next(iter(test_employees.values()))
        for year in (2024, 2025, 2026):
            resp = api_get(
                api_base, "/api/reports/employee", admin_headers,
                params={"employee_id": emp["id"], "year": year}
            )
            assert resp.status_code == 200, \
                f"Ожидается 200 для year={year}, получено {resp.status_code}"
            data = resp.json()
            assert "total_stages" in data

    def test_employee_report_filter_by_year_and_month(self, api_base, admin_headers, test_employees):
        """GET /api/reports/employee с фильтром по году и месяцу"""
        if not test_employees:
            pytest.skip("Тестовые сотрудники не созданы — пропускаем тест")
        emp = next(iter(test_employees.values()))
        resp = api_get(
            api_base, "/api/reports/employee", admin_headers,
            params={"employee_id": emp["id"], "year": 2026, "month": 1}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "stages" in data
        assert "payments" in data

    def test_employee_report_by_type_template(self, api_base, admin_headers):
        """GET /api/reports/employee-report для шаблонного проекта"""
        resp = api_get(
            api_base, "/api/reports/employee-report", admin_headers,
            params={"project_type": "Шаблонный", "period": "За год", "year": 2026}
        )
        assert resp.status_code == 200
        data = resp.json()
        for key in ("completed", "area", "deadlines", "salaries"):
            assert key in data, f"Ожидается ключ '{key}' для шаблонного проекта"

    def test_employee_report_by_type_period_month(self, api_base, admin_headers):
        """GET /api/reports/employee-report с периодом 'За месяц'"""
        resp = api_get(
            api_base, "/api/reports/employee-report", admin_headers,
            params={
                "project_type": "Индивидуальный",
                "period": "За месяц",
                "year": 2026,
                "month": 1,
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "completed" in data
        assert "salaries" in data

    def test_employee_report_by_type_period_quarter(self, api_base, admin_headers):
        """GET /api/reports/employee-report с периодом 'За квартал'"""
        resp = api_get(
            api_base, "/api/reports/employee-report", admin_headers,
            params={
                "project_type": "Индивидуальный",
                "period": "За квартал",
                "year": 2026,
                "quarter": 1,
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        for key in ("completed", "area", "deadlines", "salaries"):
            assert key in data, f"Ожидается ключ '{key}' в ответе за квартал"

    def test_employee_report_by_type_area_structure(self, api_base, admin_headers):
        """GET /api/reports/employee-report — структура элементов area"""
        resp = api_get(
            api_base, "/api/reports/employee-report", admin_headers,
            params={"project_type": "Индивидуальный", "period": "За год", "year": 2026}
        )
        assert resp.status_code == 200
        data = resp.json()
        if data["area"]:
            for item in data["area"][:5]:
                assert "employee_name" in item, "Ожидается ключ employee_name в area"
                assert "total_area" in item, "Ожидается ключ total_area в area"
                assert isinstance(item["total_area"], (int, float))

    def test_employee_report_by_type_deadlines_structure(self, api_base, admin_headers):
        """GET /api/reports/employee-report — структура элементов deadlines"""
        resp = api_get(
            api_base, "/api/reports/employee-report", admin_headers,
            params={"project_type": "Индивидуальный", "period": "За год", "year": 2026}
        )
        assert resp.status_code == 200
        data = resp.json()
        if data["deadlines"]:
            for item in data["deadlines"][:5]:
                assert "employee_name" in item, "Ожидается ключ employee_name в deadlines"
                assert "overdue_count" in item, "Ожидается ключ overdue_count в deadlines"
                assert "avg_overdue_days" in item, "Ожидается ключ avg_overdue_days в deadlines"

    def test_employee_report_by_type_missing_params(self, api_base, admin_headers):
        """GET /api/reports/employee-report без обязательных параметров → 422"""
        resp = api_get(api_base, "/api/reports/employee-report", admin_headers)
        assert resp.status_code == 422, \
            f"Без параметров ожидается 422, получено {resp.status_code}"

    def test_employee_report_by_type_require_auth(self, api_base):
        """GET /api/reports/employee-report без токена — 401"""
        resp = api_get(api_base, "/api/reports/employee-report", {},
                       params={"project_type": "Индивидуальный",
                               "period": "За год", "year": 2026})
        assert resp.status_code in (401, 403)
