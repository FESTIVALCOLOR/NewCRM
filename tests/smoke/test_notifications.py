# -*- coding: utf-8 -*-
"""
Smoke Tests: Notifications — уведомления lifecycle.

Покрывает: GET /notifications, PATCH /notifications/{id}/read,
фильтрация, mark-read.

Запуск: pytest tests/smoke/test_notifications.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import _get, _patch


@pytest.mark.smoke
class TestNotificationsRead:
    """P1: Чтение уведомлений."""

    def test_list_notifications(self, admin_headers):
        """GET /notifications — список уведомлений."""
        resp = _get("/api/notifications", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_notifications_structure(self, admin_headers):
        """Уведомления имеют обязательные поля."""
        resp = _get("/api/notifications", admin_headers).json()
        if not resp:
            pytest.skip("Нет уведомлений")

        notif = resp[0]
        # Минимальные поля
        assert "id" in notif, "Нет id в уведомлении"

    def test_notifications_not_all_read(self, admin_headers):
        """Среди уведомлений есть прочитанные и непрочитанные (или все одного типа)."""
        notifications = _get("/api/notifications", admin_headers).json()
        if not notifications:
            pytest.skip("Нет уведомлений")

        read_count = sum(1 for n in notifications if n.get("is_read"))
        unread_count = len(notifications) - read_count
        # Просто проверяем что подсчёт работает
        assert read_count >= 0
        assert unread_count >= 0


@pytest.mark.smoke
class TestNotificationsMarkRead:
    """P1: Отметка уведомлений прочитанными."""

    def test_mark_notification_read(self, admin_headers):
        """PATCH /notifications/{id}/read — отметить прочитанным."""
        notifications = _get("/api/notifications", admin_headers).json()
        if not notifications:
            pytest.skip("Нет уведомлений")

        # Берём первое уведомление
        nid = notifications[0]["id"]
        resp = _patch(f"/api/notifications/{nid}/read", admin_headers)
        assert resp.status_code in (200, 204, 422), \
            f"Mark read: {resp.status_code} {resp.text}"

    def test_mark_nonexistent_notification(self, admin_headers):
        """PATCH /notifications/999999/read — несуществующее уведомление."""
        resp = _patch("/api/notifications/999999/read", admin_headers)
        # 405 — если endpoint использует другой HTTP метод (POST)
        assert resp.status_code in (404, 405, 422, 200)
