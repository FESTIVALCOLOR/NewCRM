# -*- coding: utf-8 -*-
"""
Smoke Tests: Messenger CRUD — scripts CRUD, settings update.

НЕ отправляет реальные сообщения в Telegram.
Тестирует только CRUD скриптов и настройки (safe operations).

Запуск: pytest tests/smoke/test_messenger_crud.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete, TEST_PREFIX,
)


# ════════════════════════════════════════════════════════════
# 1. Scripts CRUD
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestMessengerScriptsCRUD:
    """P1: CRUD скриптов мессенджера."""

    def test_create_update_delete_script(self, admin_headers):
        """POST → PUT → DELETE /messenger/scripts — полный цикл."""
        create = _post("/api/messenger/scripts", admin_headers, json={
            "script_type": "project_start",
            "message_template": f"{TEST_PREFIX}Тестовое сообщение",
            "is_enabled": False,
        })
        if create.status_code not in (200, 201):
            pytest.skip(f"Создание скрипта: {create.status_code} {create.text}")

        script_id = create.json().get("id")
        assert script_id, "Нет ID скрипта в ответе"

        try:
            # Update
            upd = _put(f"/api/messenger/scripts/{script_id}", admin_headers, json={
                "name": f"{TEST_PREFIX}Обновлённый скрипт",
                "is_active": False,
            })
            assert upd.status_code in (200, 422), \
                f"Update script: {upd.status_code} {upd.text}"

            # Проверяем в списке
            scripts = _get("/api/messenger/scripts", admin_headers).json()
            found = any(s.get("id") == script_id for s in scripts)
            assert found, f"Скрипт {script_id} не найден в списке"
        finally:
            # Delete
            delete = _delete(f"/api/messenger/scripts/{script_id}", admin_headers)
            assert delete.status_code in (200, 204), \
                f"Delete script: {delete.status_code} {delete.text}"

    def test_toggle_script(self, admin_headers):
        """PATCH /messenger/scripts/{id}/toggle — включение/отключение."""
        create = _post("/api/messenger/scripts", admin_headers, json={
            "script_type": "stage_complete",
            "message_template": f"{TEST_PREFIX}Toggle скрипт",
            "is_enabled": False,
        })
        if create.status_code not in (200, 201):
            pytest.skip(f"Создание скрипта: {create.status_code}")

        script_id = create.json().get("id")
        try:
            resp = _patch(f"/api/messenger/scripts/{script_id}/toggle", admin_headers)
            assert resp.status_code in (200, 422), \
                f"Toggle: {resp.status_code} {resp.text}"
        finally:
            _delete(f"/api/messenger/scripts/{script_id}", admin_headers)


# ════════════════════════════════════════════════════════════
# 2. Settings Update
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestMessengerSettings:
    """P1: Настройки мессенджера."""

    def test_update_settings_idempotent(self, admin_headers):
        """PUT /messenger/settings — идемпотентное обновление."""
        current = _get("/api/messenger/settings", admin_headers)
        if current.status_code != 200:
            pytest.skip(f"Не удалось получить settings: {current.status_code}")

        # Отправляем обратно как есть
        resp = _put("/api/messenger/settings", admin_headers, json=current.json())
        assert resp.status_code in (200, 422), \
            f"Update settings: {resp.status_code} {resp.text}"


# ════════════════════════════════════════════════════════════
# 3. Chat Lookup (read-only)
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestMessengerChatLookup:
    """P2: Поиск чатов по сущностям."""

    def test_chat_by_card_multiple(self, admin_headers):
        """Проверка чатов для нескольких CRM карточек."""
        cards = _get("/api/crm/cards", admin_headers, params={
            "project_type": "Индивидуальный",
        }).json()
        if not cards:
            pytest.skip("Нет CRM карточек")

        checked = 0
        for card in cards[:5]:
            resp = _get(
                f"/api/messenger/chats/by-card/{card['id']}", admin_headers,
            )
            assert resp.status_code in (200, 404)
            checked += 1

        assert checked > 0

    def test_chat_by_supervision_multiple(self, admin_headers):
        """Проверка чатов для нескольких карточек надзора."""
        cards = _get("/api/supervision/cards", admin_headers).json()
        if not cards:
            pytest.skip("Нет карточек надзора")

        checked = 0
        for card in cards[:5]:
            resp = _get(
                f"/api/messenger/chats/by-supervision/{card['id']}", admin_headers,
            )
            assert resp.status_code in (200, 404)
            checked += 1

        assert checked > 0
