# -*- coding: utf-8 -*-
"""
E2E Tests: страница «Заявки» в CRM (/api/v1/leads) и вкладка заявок в панели сайта.
Заявки здесь не создаются: новая заявка рассылает уведомления (в т.ч. Telegram) реальным сотрудникам.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_delete, api_get, api_put

MISSING_ID = 999999999


@pytest.mark.e2e
class TestCrmLeads:
    def test_list_and_filters(self, api_base, admin_headers):
        for status in ("", "new", "done"):
            resp = api_get(api_base, "/api/v1/leads", admin_headers, params={"status": status} if status else None)
            assert resp.status_code == 200, resp.text
            assert isinstance(resp.json(), list)

    def test_count_route_not_shadowed(self, api_base, admin_headers):
        resp = api_get(api_base, "/api/v1/leads/count", admin_headers)
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json().get("new"), int)

    def test_update_missing_lead_404(self, api_base, admin_headers):
        resp = api_put(api_base, f"/api/v1/leads/{MISSING_ID}", admin_headers, json={"status": "done", "result": "тест"})
        assert resp.status_code == 404, resp.text

    def test_bad_status_422(self, api_base, admin_headers):
        resp = api_put(api_base, f"/api/v1/leads/{MISSING_ID}", admin_headers, json={"status": "lost"})
        assert resp.status_code == 422, resp.text

    def test_delete_missing_lead_404(self, api_base, admin_headers):
        resp = api_delete(api_base, f"/api/v1/leads/{MISSING_ID}", admin_headers)
        assert resp.status_code == 404, resp.text

    def test_permissions_registered(self, api_base, admin_headers):
        resp = api_get(api_base, "/api/v1/permissions/definitions", admin_headers)
        assert resp.status_code == 200, resp.text
        names = str(resp.json())
        assert "access.leads" in names and "leads.delete" in names


@pytest.mark.e2e
class TestSiteAdminLeads:
    def test_delete_missing_lead_404(self, api_base, admin_headers):
        resp = api_delete(api_base, f"/api/v1/site/admin/leads/{MISSING_ID}", admin_headers)
        assert resp.status_code == 404, resp.text
