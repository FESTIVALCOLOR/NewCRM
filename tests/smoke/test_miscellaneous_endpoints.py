# -*- coding: utf-8 -*-
"""
Smoke Tests: Miscellaneous Endpoints — norm days, sync, heartbeat, statistics.

Запуск: pytest tests/smoke/test_miscellaneous_endpoints.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import _get, _post


# ════════════════════════════════════════════════════════════
# 1. Norm Days
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestNormDays:
    """P2: Нормативные сроки."""

    def test_norm_days_templates(self, admin_headers):
        """GET /norm-days/templates — шаблоны нормативных сроков."""
        resp = _get("/api/norm-days/templates", admin_headers, params={
            "project_type": "Индивидуальный",
            "project_subtype": "Стандарт",
        })
        assert resp.status_code in (200, 422)


# ════════════════════════════════════════════════════════════
# 2. Heartbeat
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestHeartbeat:
    """P2: Heartbeat."""

    def test_heartbeat_post(self, admin_headers):
        """POST /heartbeat — отправка heartbeat."""
        resp = _post("/api/heartbeat", admin_headers, json={})
        assert resp.status_code in (200, 201, 204)


# ════════════════════════════════════════════════════════════
# 3. Sync Endpoints
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSync:
    """P2: Синхронизация данных."""

    def test_sync_stage_executors(self, admin_headers):
        """GET /sync/stage-executors — исполнители стадий."""
        resp = _get("/api/sync/stage-executors", admin_headers)
        assert resp.status_code == 200

    def test_sync_approval_deadlines(self, admin_headers):
        """GET /sync/approval-deadlines — дедлайны согласований."""
        resp = _get("/api/sync/approval-deadlines", admin_headers)
        assert resp.status_code == 200

    def test_sync_action_history(self, admin_headers):
        """GET /sync/action-history — история действий через sync."""
        resp = _get("/api/sync/action-history", admin_headers)
        assert resp.status_code == 200


# ════════════════════════════════════════════════════════════
# 4. Statistics Extended
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestStatisticsExtended:
    """P2: Расширенная статистика."""

    def test_statistics_dashboard(self, admin_headers):
        """GET /statistics/dashboard — главная статистика."""
        resp = _get("/api/statistics/dashboard", admin_headers)
        assert resp.status_code == 200

    def test_statistics_general(self, admin_headers):
        """GET /statistics/general — общая статистика."""
        resp = _get("/api/statistics/general", admin_headers, params={
            "project_type": "Индивидуальный",
        })
        assert resp.status_code in (200, 422)

    def test_statistics_funnel(self, admin_headers):
        """GET /statistics/funnel — воронка."""
        resp = _get("/api/statistics/funnel", admin_headers)
        assert resp.status_code == 200

    def test_statistics_executor_load(self, admin_headers):
        """GET /statistics/executor-load — нагрузка исполнителей."""
        resp = _get("/api/statistics/executor-load", admin_headers)
        assert resp.status_code == 200

    def test_statistics_crm_filtered(self, admin_headers):
        """GET /statistics/crm — CRM статистика."""
        resp = _get("/api/statistics/crm", admin_headers)
        assert resp.status_code == 200

    def test_statistics_supervision(self, admin_headers):
        """GET /statistics/supervision — надзор статистика."""
        resp = _get("/api/statistics/supervision", admin_headers)
        assert resp.status_code == 200


# ════════════════════════════════════════════════════════════
# 5. Supervision Timeline
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSupervisionTimeline:
    """P2: Timeline авторского надзора."""

    def test_supervision_timeline_list(self, admin_headers):
        """GET /supervision-timeline — список."""
        resp = _get("/api/supervision-timeline", admin_headers)
        assert resp.status_code == 200


# ════════════════════════════════════════════════════════════
# 6. Reports
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestReports:
    """P2: Отчёты."""

    def test_employee_report(self, admin_headers):
        """GET /reports/employee — отчёт по сотрудникам."""
        resp = _get("/api/reports/employee", admin_headers, params={
            "project_type": "Индивидуальный",
            "period": "За год",
            "year": 2026,
        })
        assert resp.status_code in (200, 422)

    def test_contracts_by_period(self, admin_headers):
        """GET /statistics/contracts-by-period — договоры по периодам."""
        resp = _get("/api/statistics/contracts-by-period", admin_headers, params={
            "year": 2026,
        })
        assert resp.status_code in (200, 422)
