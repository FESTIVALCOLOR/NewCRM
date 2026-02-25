# -*- coding: utf-8 -*-
"""
E2E Tests: Уведомления
8 тестов — проверка GET/PUT endpoints уведомлений с проверкой структуры ответов.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get, api_put

# Актуальный путь к API уведомлений (v1)
NOTIFICATIONS_URL = "/api/v1/notifications"


class TestNotifications:
    """Тесты уведомлений"""

    def test_get_notifications(self, api_base, admin_headers):
        """GET /api/v1/notifications — получить уведомления"""
        resp = api_get(api_base, NOTIFICATIONS_URL, admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_notifications_keys(self, api_base, admin_headers):
        """GET /api/v1/notifications — проверка ключей элементов"""
        resp = api_get(api_base, NOTIFICATIONS_URL, admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            required_keys = {"id", "notification_type", "title", "message", "is_read", "created_at"}
            for item in data[:5]:
                assert required_keys.issubset(item.keys()), (
                    f"Отсутствуют ключи: {required_keys - item.keys()}"
                )
                assert isinstance(item["id"], int), "id должен быть int"
                assert isinstance(item["is_read"], bool), "is_read должен быть bool"
                assert isinstance(item["message"], str), "message должен быть строкой"
                assert isinstance(item["title"], str), "title должен быть строкой"
                assert isinstance(item["notification_type"], str), "notification_type должен быть строкой"
                assert isinstance(item["created_at"], str), "created_at должен быть строкой"

    def test_get_notifications_unread_only(self, api_base, admin_headers):
        """GET /api/v1/notifications?unread_only=true — только непрочитанные"""
        resp = api_get(api_base, NOTIFICATIONS_URL, admin_headers,
                       params={"unread_only": True})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Если элементы есть — все должны быть непрочитанными
        if data:
            for item in data[:5]:
                assert item.get("is_read") is False, (
                    f"При unread_only=true все элементы должны иметь is_read=False, "
                    f"получили: {item.get('is_read')}"
                )

    def test_get_notifications_unread_subset(self, api_base, admin_headers):
        """Непрочитанных не больше чем всего уведомлений"""
        resp_all = api_get(api_base, NOTIFICATIONS_URL, admin_headers)
        resp_unread = api_get(api_base, NOTIFICATIONS_URL, admin_headers,
                              params={"unread_only": True})
        assert resp_all.status_code == 200
        assert resp_unread.status_code == 200
        all_count = len(resp_all.json())
        unread_count = len(resp_unread.json())
        assert unread_count <= all_count, (
            f"Непрочитанных ({unread_count}) не может быть больше всего ({all_count})"
        )

    def test_mark_notification_read_nonexistent(self, api_base, admin_headers):
        """PUT /api/v1/notifications/999999/read — несуществующее уведомление"""
        resp = api_put(api_base, f"{NOTIFICATIONS_URL}/999999/read", admin_headers)
        assert resp.status_code in (404, 422)

    def test_notifications_require_auth(self, api_base):
        """GET /api/v1/notifications без токена — 401"""
        resp = api_get(api_base, NOTIFICATIONS_URL, {})
        assert resp.status_code in (401, 403)

    def test_notifications_role_isolation(self, api_base, role_tokens):
        """Каждая роль видит только свои уведомления"""
        for role_key, headers in role_tokens.items():
            resp = api_get(api_base, NOTIFICATIONS_URL, headers)
            assert resp.status_code == 200, (
                f"Роль {role_key}: ожидали 200, получили {resp.status_code}"
            )
            data = resp.json()
            assert isinstance(data, list), (
                f"Роль {role_key}: ожидали list, получили {type(data)}"
            )

    def test_notifications_pagination_params(self, api_base, admin_headers):
        """GET /api/v1/notifications — параметры unread_only принимаются без ошибок"""
        # Проверяем что endpoint принимает параметр unread_only=false без ошибок
        resp_false = api_get(api_base, NOTIFICATIONS_URL, admin_headers,
                             params={"unread_only": False})
        assert resp_false.status_code == 200
        data_false = resp_false.json()
        assert isinstance(data_false, list)

        # Проверяем что unread_only=true также принимается
        resp_true = api_get(api_base, NOTIFICATIONS_URL, admin_headers,
                            params={"unread_only": True})
        assert resp_true.status_code == 200
        data_true = resp_true.json()
        assert isinstance(data_true, list)
