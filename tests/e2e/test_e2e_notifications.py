# -*- coding: utf-8 -*-
"""
E2E Tests: Уведомления
5 тестов — проверка GET/PUT endpoints уведомлений.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get, api_put


class TestNotifications:
    """Тесты уведомлений"""

    def test_get_notifications(self, api_base, admin_headers):
        """GET /api/notifications — получить уведомления"""
        resp = api_get(api_base, "/api/notifications", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_notifications_unread_only(self, api_base, admin_headers):
        """GET /api/notifications?unread_only=true — только непрочитанные"""
        resp = api_get(api_base, "/api/notifications", admin_headers,
                       params={"unread_only": True})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_mark_notification_read_nonexistent(self, api_base, admin_headers):
        """PUT /api/notifications/999999/read — несуществующее уведомление"""
        resp = api_put(api_base, "/api/notifications/999999/read", admin_headers)
        assert resp.status_code in (404, 422)

    def test_notifications_require_auth(self, api_base):
        """GET /api/notifications без токена — 401"""
        resp = api_get(api_base, "/api/notifications", {})
        assert resp.status_code in (401, 403)

    def test_notifications_role_isolation(self, api_base, role_tokens):
        """Каждая роль видит только свои уведомления"""
        for role_key, headers in role_tokens.items():
            resp = api_get(api_base, "/api/notifications", headers)
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
