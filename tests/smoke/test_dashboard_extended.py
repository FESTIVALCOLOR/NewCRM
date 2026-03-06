# -*- coding: utf-8 -*-
"""
Smoke Tests: Dashboard Extended — зарплаты, отчёты, аналитика.

Покрывает: salary dashboard endpoints (7), reports dynamics (5),
agent-types, contract-years.

Запуск: pytest tests/smoke/test_dashboard_extended.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import _get


# ════════════════════════════════════════════════════════════
# 1. Salary Dashboard
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardSalaries:
    """P1: Зарплатная панель dashboard."""

    def test_salaries_dashboard(self, admin_headers):
        """GET /dashboard/salaries — сводка зарплат."""
        resp = _get("/api/dashboard/salaries", admin_headers)
        assert resp.status_code == 200

    def test_salaries_by_type(self, admin_headers):
        """GET /dashboard/salaries-by-type — зарплаты по типам."""
        resp = _get("/api/dashboard/salaries-by-type", admin_headers, params={
            "payment_type": "all",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (dict, list))

    def test_salaries_all(self, admin_headers):
        """GET /dashboard/salaries-all — все зарплаты."""
        resp = _get("/api/dashboard/salaries-all", admin_headers)
        assert resp.status_code == 200

    def test_salaries_individual(self, admin_headers):
        """GET /dashboard/salaries-individual — индивидуальные зарплаты."""
        resp = _get("/api/dashboard/salaries-individual", admin_headers)
        assert resp.status_code == 200

    def test_salaries_template(self, admin_headers):
        """GET /dashboard/salaries-template — шаблонные зарплаты."""
        resp = _get("/api/dashboard/salaries-template", admin_headers)
        assert resp.status_code == 200

    def test_salaries_salary(self, admin_headers):
        """GET /dashboard/salaries-salary — основная зарплата."""
        resp = _get("/api/dashboard/salaries-salary", admin_headers)
        assert resp.status_code == 200

    def test_salaries_supervision(self, admin_headers):
        """GET /dashboard/salaries-supervision — зарплаты надзора."""
        resp = _get("/api/dashboard/salaries-supervision", admin_headers)
        assert resp.status_code == 200


# ════════════════════════════════════════════════════════════
# 2. Dashboard Metadata
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardMetadata:
    """P1: Метаданные dashboard."""

    def test_agent_types(self, admin_headers):
        """GET /dashboard/agent-types — типы агентов."""
        resp = _get("/api/dashboard/agent-types", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Типы агентов не должны быть пустыми"

    def test_contract_years(self, admin_headers):
        """GET /dashboard/contract-years — годы договоров."""
        resp = _get("/api/dashboard/contract-years", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


# ════════════════════════════════════════════════════════════
# 3. Reports & Analytics
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardReports:
    """P1: Отчёты и аналитика dashboard."""

    def test_reports_summary(self, admin_headers):
        """GET /dashboard/reports/summary — сводный отчёт."""
        resp = _get("/api/dashboard/reports/summary", admin_headers)
        assert resp.status_code == 200

    def test_reports_clients_dynamics(self, admin_headers):
        """GET /dashboard/reports/clients-dynamics — динамика клиентов."""
        resp = _get("/api/dashboard/reports/clients-dynamics", admin_headers)
        assert resp.status_code == 200

    def test_reports_contracts_dynamics(self, admin_headers):
        """GET /dashboard/reports/contracts-dynamics — динамика договоров."""
        resp = _get("/api/dashboard/reports/contracts-dynamics", admin_headers)
        assert resp.status_code == 200

    def test_reports_crm_analytics(self, admin_headers):
        """GET /dashboard/reports/crm-analytics — аналитика CRM."""
        resp = _get("/api/dashboard/reports/crm-analytics", admin_headers)
        assert resp.status_code == 200

    def test_reports_supervision_analytics(self, admin_headers):
        """GET /dashboard/reports/supervision-analytics — аналитика надзора."""
        resp = _get("/api/dashboard/reports/supervision-analytics", admin_headers)
        assert resp.status_code == 200

    def test_reports_distribution(self, admin_headers):
        """GET /dashboard/reports/distribution — распределение."""
        resp = _get("/api/dashboard/reports/distribution", admin_headers, params={
            "dimension": "city",
        })
        assert resp.status_code == 200
