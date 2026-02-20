# -*- coding: utf-8 -*-
"""
E2E Tests: Статистика (расширенная)
9 тестов — непокрытые endpoints статистики.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get


class TestStatistics:
    """Тесты расширенной статистики"""

    def test_dashboard_statistics(self, api_base, admin_headers):
        """GET /api/statistics/dashboard — статистика дашборда"""
        resp = api_get(api_base, "/api/statistics/dashboard", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_employees_statistics(self, api_base, admin_headers):
        """GET /api/statistics/employees — статистика по сотрудникам"""
        resp = api_get(api_base, "/api/statistics/employees", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200

    def test_agent_types_statistics(self, api_base, admin_headers):
        """GET /api/statistics/agent-types — список типов агентов"""
        resp = api_get(api_base, "/api/statistics/agent-types", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_cities_statistics(self, api_base, admin_headers):
        """GET /api/statistics/cities — список городов"""
        resp = api_get(api_base, "/api/statistics/cities", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_projects_statistics(self, api_base, admin_headers):
        """GET /api/statistics/projects — статистика проектов"""
        resp = api_get(api_base, "/api/statistics/projects", admin_headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200

    def test_supervision_filtered_statistics(self, api_base, admin_headers):
        """GET /api/statistics/supervision/filtered — фильтрованная статистика надзора"""
        resp = api_get(api_base, "/api/statistics/supervision/filtered", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200

    def test_crm_statistics(self, api_base, admin_headers):
        """GET /api/statistics/crm — статистика CRM"""
        resp = api_get(api_base, "/api/statistics/crm", admin_headers,
                       params={"project_type": "Индивидуальный", "period": "year", "year": 2026})
        assert resp.status_code == 200

    def test_crm_filtered_statistics(self, api_base, admin_headers):
        """GET /api/statistics/crm/filtered — статистика CRM с фильтрами"""
        resp = api_get(api_base, "/api/statistics/crm/filtered", admin_headers,
                       params={"project_type": "Индивидуальный", "period": "year", "year": 2026})
        assert resp.status_code == 200

    def test_approvals_statistics(self, api_base, admin_headers):
        """GET /api/statistics/approvals — статистика согласований"""
        resp = api_get(api_base, "/api/statistics/approvals", admin_headers,
                       params={"project_type": "Индивидуальный", "period": "year", "year": 2026})
        assert resp.status_code == 200
