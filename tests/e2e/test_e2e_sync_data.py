# -*- coding: utf-8 -*-
"""
E2E Tests: Синхронизация данных
5 тестов — GET/POST endpoints синхронизации.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get, api_post


class TestSyncData:
    """Тесты синхронизации данных"""

    def test_sync_stage_executors(self, api_base, admin_headers):
        """GET /api/sync/stage-executors — исполнители стадий"""
        resp = api_get(api_base, "/api/sync/stage-executors", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_sync_approval_deadlines(self, api_base, admin_headers):
        """GET /api/sync/approval-deadlines — дедлайны согласования"""
        resp = api_get(api_base, "/api/sync/approval-deadlines", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_sync_action_history(self, api_base, admin_headers):
        """GET /api/sync/action-history — история действий"""
        resp = api_get(api_base, "/api/sync/action-history", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_sync_supervision_history(self, api_base, admin_headers):
        """GET /api/sync/supervision-history — история надзора"""
        resp = api_get(api_base, "/api/sync/supervision-history", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_sync_requires_auth(self, api_base):
        """GET /api/sync/stage-executors без токена — 401"""
        resp = api_get(api_base, "/api/sync/stage-executors", {})
        assert resp.status_code in (401, 403)
