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

    def test_employee_report_by_type(self, api_base, admin_headers):
        """GET /api/reports/employee-report — отчёт по типу проекта"""
        resp = api_get(
            api_base, "/api/reports/employee-report", admin_headers,
            params={"project_type": "Индивидуальный", "period": "year", "year": 2026}
        )
        assert resp.status_code == 200

    def test_employee_report_missing_params(self, api_base, admin_headers):
        """GET /api/reports/employee — без обязательных параметров"""
        resp = api_get(api_base, "/api/reports/employee", admin_headers)
        assert resp.status_code in (200, 422)  # 422 если employee_id обязателен

    def test_reports_require_auth(self, api_base):
        """GET /api/reports/employee без токена — 401"""
        resp = api_get(api_base, "/api/reports/employee", {},
                       params={"employee_id": 1})
        assert resp.status_code in (401, 403)
