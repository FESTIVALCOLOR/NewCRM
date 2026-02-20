# -*- coding: utf-8 -*-
"""
E2E Tests: Дашборд и статистика
8 тестов — проверка всех endpoints статистики и дашборда.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get


class TestDashboard:
    """Тесты дашборда"""

    def test_clients_dashboard_stats(self, api_base, admin_headers):
        """Статистика клиентов"""
        resp = api_get(api_base, "/api/dashboard/clients", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_contracts_dashboard_stats(self, api_base, admin_headers):
        """Статистика договоров"""
        resp = api_get(api_base, "/api/dashboard/contracts", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_crm_dashboard_stats(self, api_base, admin_headers):
        """Статистика CRM"""
        resp = api_get(api_base, "/api/dashboard/crm", admin_headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_employees_dashboard_stats(self, api_base, admin_headers):
        """Статистика сотрудников"""
        resp = api_get(api_base, "/api/dashboard/employees", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_salaries_dashboard_stats(self, api_base, admin_headers):
        """Статистика зарплат"""
        resp = api_get(api_base, "/api/dashboard/salaries", admin_headers)
        assert resp.status_code == 200

    def test_supervision_statistics(self, api_base, admin_headers):
        """Статистика надзора"""
        resp = api_get(api_base, "/api/statistics/supervision", admin_headers)
        assert resp.status_code == 200

    def test_contracts_by_period(self, api_base, admin_headers):
        """Статистика договоров по периодам"""
        resp = api_get(
            api_base,
            "/api/statistics/contracts-by-period",
            admin_headers,
            params={"year": 2026, "group_by": "month"}
        )
        assert resp.status_code == 200

    def test_general_statistics(self, api_base, admin_headers):
        """Общая статистика"""
        resp = api_get(
            api_base,
            "/api/statistics/general",
            admin_headers,
            params={"year": 2026}
        )
        assert resp.status_code == 200
