# -*- coding: utf-8 -*-
"""
Smoke Tests: Locks — блокировка одновременного редактирования.

Запуск: pytest tests/smoke/test_locks_concurrency.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import _get, _post, _delete


@pytest.mark.smoke
class TestLocksCRUD:
    """P1: Concurrent editing locks."""

    def test_create_and_release_lock(self, admin_headers):
        """POST /locks → DELETE — создание и снятие блокировки."""
        # Создаём блокировку
        resp = _post("/api/locks", admin_headers, json={
            "entity_type": "contract",
            "entity_id": 99999,
        })
        assert resp.status_code in (200, 201), \
            f"Lock create: {resp.status_code} {resp.text}"

        try:
            # Проверяем
            check = _get("/api/locks/contract/99999", admin_headers)
            assert check.status_code == 200
            data = check.json()
            assert data.get("is_locked") is True
        finally:
            # Снимаем
            rel = _delete("/api/locks/contract/99999", admin_headers)
            assert rel.status_code == 200

    def test_lock_check_unlocked(self, admin_headers):
        """GET /locks для несуществующей блокировки → is_locked=False."""
        resp = _get("/api/locks/contract/88888", admin_headers)
        assert resp.status_code == 200
        assert resp.json().get("is_locked") is False

    def test_release_user_locks(self, admin_headers):
        """DELETE /locks/user/{id} — снятие всех блокировок пользователя."""
        # Создаём блокировку
        _post("/api/locks", admin_headers, json={
            "entity_type": "contract",
            "entity_id": 77777,
        })

        try:
            resp = _delete("/api/locks/user/1", admin_headers)
            assert resp.status_code in (200, 204)
        finally:
            # Cleanup на случай если не удалилось
            _delete("/api/locks/contract/77777", admin_headers)
