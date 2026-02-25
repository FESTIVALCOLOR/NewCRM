# -*- coding: utf-8 -*-
"""
E2E Tests: Отчёты по сотрудникам
4 теста — GET endpoints отчётов.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get


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
