# -*- coding: utf-8 -*-
"""
E2E Tests: Heartbeat
3 теста — POST endpoint heartbeat.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_post, api_get


class TestHeartbeat:
    """Тесты heartbeat"""

    def test_heartbeat_returns_online_users(self, api_base, admin_headers):
        """POST /api/heartbeat — возвращает список онлайн пользователей"""
        resp = api_post(api_base, "/api/heartbeat", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (list, dict))

    def test_heartbeat_with_employee_id(self, api_base, admin_headers, test_employees):
        """POST /api/heartbeat?employee_id=X — heartbeat с указанием сотрудника"""
        # Безопасное получение первого сотрудника: пропускаем тест если словарь пуст
        if not test_employees:
            pytest.skip("Тестовые сотрудники не созданы — пропускаем тест")
        emp = next(iter(test_employees.values()))
        resp = api_post(
            api_base, "/api/heartbeat", admin_headers,
            params={"employee_id": emp["id"]}
        )
        assert resp.status_code == 200

    def test_heartbeat_requires_auth(self, api_base):
        """POST /api/heartbeat без токена — 401"""
        resp = api_post(api_base, "/api/heartbeat", {})
        assert resp.status_code in (401, 403)
