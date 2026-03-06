# -*- coding: utf-8 -*-
"""
Smoke Tests: Statistics Filtered — статистика с фильтрами и расширенные endpoints.

Покрывает: employees stats, agent-types, cities, approvals,
crm/filtered, supervision/filtered, projects.

Запуск: pytest tests/smoke/test_statistics_filtered.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import _get


# ════════════════════════════════════════════════════════════
# 1. Statistics Read
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestStatisticsRead:
    """P1: Статистика — чтение базовых отчётов."""

    def test_statistics_employees(self, admin_headers):
        """GET /statistics/employees — статистика по сотрудникам."""
        resp = _get("/api/statistics/employees", admin_headers)
        assert resp.status_code == 200

    def test_statistics_agent_types(self, admin_headers):
        """GET /statistics/agent-types — статистика по типам агентов."""
        resp = _get("/api/statistics/agent-types", admin_headers)
        assert resp.status_code == 200

    def test_statistics_cities(self, admin_headers):
        """GET /statistics/cities — статистика по городам."""
        resp = _get("/api/statistics/cities", admin_headers)
        assert resp.status_code == 200

    def test_statistics_approvals(self, admin_headers):
        """GET /statistics/approvals — статистика согласований."""
        resp = _get("/api/statistics/approvals", admin_headers)
        assert resp.status_code in (200, 422)

    def test_statistics_projects(self, admin_headers):
        """GET /statistics/projects — статистика проектов."""
        resp = _get("/api/statistics/projects", admin_headers)
        assert resp.status_code == 200


# ════════════════════════════════════════════════════════════
# 2. Filtered Statistics
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestStatisticsFiltered:
    """P1: Статистика с фильтрами."""

    def test_crm_filtered_no_params(self, admin_headers):
        """GET /statistics/crm/filtered — CRM с обязательными параметрами."""
        resp = _get("/api/statistics/crm/filtered", admin_headers, params={
            "project_type": "Индивидуальный",
            "period": "all",
            "year": 2026,
        })
        assert resp.status_code == 200

    def test_crm_filtered_with_agent_type(self, admin_headers):
        """GET /statistics/crm/filtered?agent_type=... — CRM с фильтром агента."""
        resp = _get("/api/statistics/crm/filtered", admin_headers, params={
            "project_type": "Индивидуальный",
            "period": "all",
            "year": 2026,
            "agent_type": "ФЕСТИВАЛЬ",
        })
        assert resp.status_code == 200

    def test_supervision_filtered_no_params(self, admin_headers):
        """GET /statistics/supervision/filtered — надзор без фильтров."""
        resp = _get("/api/statistics/supervision/filtered", admin_headers)
        assert resp.status_code == 200

    def test_supervision_filtered_with_agent_type(self, admin_headers):
        """GET /statistics/supervision/filtered?agent_type=... — надзор с фильтром."""
        resp = _get("/api/statistics/supervision/filtered", admin_headers, params={
            "agent_type": "ФЕСТИВАЛЬ",
        })
        assert resp.status_code == 200

    def test_crm_statistics_base(self, admin_headers):
        """GET /statistics/crm — базовая CRM статистика."""
        resp = _get("/api/statistics/crm", admin_headers)
        assert resp.status_code == 200


# ════════════════════════════════════════════════════════════
# 3. Extended Reports
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestReportsExtended:
    """P1: Расширенные отчёты."""

    def test_employee_report_extended(self, admin_headers):
        """GET /reports/employee-report — расширенный отчёт по сотрудникам."""
        resp = _get("/api/reports/employee-report", admin_headers, params={
            "project_type": "Индивидуальный",
            "period": "За год",
            "year": 2026,
        })
        assert resp.status_code in (200, 422)

    def test_sync_supervision_history(self, admin_headers):
        """GET /sync/supervision-history — история надзора через sync."""
        resp = _get("/api/sync/supervision-history", admin_headers)
        assert resp.status_code == 200
