# -*- coding: utf-8 -*-
"""
E2E Tests: Мессенджер (messenger)
10 тестов — скрипты, настройки, статус мессенджера.
Endpoint prefix: /api/messenger

Примечание: тесты создания/удаления чатов через MTProto не включены,
поскольку MTProto требует реального Telegram-аккаунта и не может быть
протестирован в автоматическом режиме без сессии.
Тесты фокусируются на публичных endpoints: scripts, settings, status.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import (
    TEST_PREFIX, api_get, api_post, api_put, api_delete, api_patch
)


# ==============================================================
# СКРИПТЫ МЕССЕНДЖЕРА
# ==============================================================

@pytest.mark.e2e
class TestMessengerScripts:
    """Тесты CRUD скриптов мессенджера"""

    def test_get_scripts_list(self, api_base, admin_headers):
        """GET /api/messenger/scripts — получить список скриптов"""
        resp = api_get(api_base, "/api/messenger/scripts", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_scripts_filter_by_type(self, api_base, admin_headers):
        """GET /api/messenger/scripts?script_type=project_start — фильтрация по типу"""
        resp = api_get(
            api_base, "/api/messenger/scripts", admin_headers,
            params={"script_type": "project_start"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Если есть записи — все должны быть нужного типа
        for script in data:
            assert script["script_type"] == "project_start"

    def test_create_script(self, api_base, admin_headers):
        """POST /api/messenger/scripts — создать скрипт"""
        payload = {
            "script_type": "stage_complete",
            "project_type": None,
            "stage_name": f"{TEST_PREFIX}Этап",
            "message_template": f"{TEST_PREFIX} тестовое сообщение",
            "use_auto_deadline": False,
            "is_enabled": True,
            "sort_order": 99
        }
        resp = api_post(api_base, "/api/messenger/scripts", admin_headers, json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["script_type"] == "stage_complete"
        assert data["is_enabled"] is True

        # Очищаем созданный скрипт
        script_id = data["id"]
        api_delete(api_base, f"/api/messenger/scripts/{script_id}", admin_headers)

    def test_update_script(self, api_base, admin_headers):
        """PUT /api/messenger/scripts/{id} — обновить скрипт"""
        # Создаём скрипт для обновления
        create_resp = api_post(
            api_base, "/api/messenger/scripts", admin_headers,
            json={
                "script_type": "project_end",
                "project_type": None,
                "stage_name": None,
                "message_template": f"{TEST_PREFIX} оригинальный текст",
                "use_auto_deadline": False,
                "is_enabled": True,
                "sort_order": 100
            }
        )
        assert create_resp.status_code == 200
        script_id = create_resp.json()["id"]

        # Обновляем
        update_resp = api_put(
            api_base, f"/api/messenger/scripts/{script_id}", admin_headers,
            json={
                "message_template": f"{TEST_PREFIX} обновлённый текст",
                "is_enabled": False
            }
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["message_template"] == f"{TEST_PREFIX} обновлённый текст"
        assert updated["is_enabled"] is False

        # Очищаем
        api_delete(api_base, f"/api/messenger/scripts/{script_id}", admin_headers)

    def test_toggle_script(self, api_base, admin_headers):
        """PATCH /api/messenger/scripts/{id}/toggle — включить/выключить скрипт"""
        # Создаём скрипт
        create_resp = api_post(
            api_base, "/api/messenger/scripts", admin_headers,
            json={
                "script_type": "stage_complete",
                "project_type": None,
                "stage_name": None,
                "message_template": f"{TEST_PREFIX} toggle test",
                "use_auto_deadline": False,
                "is_enabled": True,
                "sort_order": 101
            }
        )
        assert create_resp.status_code == 200
        script_id = create_resp.json()["id"]
        original_enabled = create_resp.json()["is_enabled"]

        # Переключаем
        toggle_resp = api_patch(
            api_base, f"/api/messenger/scripts/{script_id}/toggle", admin_headers
        )
        assert toggle_resp.status_code == 200
        toggled = toggle_resp.json()
        assert toggled["is_enabled"] == (not original_enabled)

        # Очищаем
        api_delete(api_base, f"/api/messenger/scripts/{script_id}", admin_headers)

    def test_delete_script(self, api_base, admin_headers):
        """DELETE /api/messenger/scripts/{id} — удалить скрипт"""
        # Создаём скрипт для удаления
        create_resp = api_post(
            api_base, "/api/messenger/scripts", admin_headers,
            json={
                "script_type": "project_start",
                "project_type": None,
                "stage_name": None,
                "message_template": f"{TEST_PREFIX} to be deleted",
                "use_auto_deadline": False,
                "is_enabled": True,
                "sort_order": 102
            }
        )
        assert create_resp.status_code == 200
        script_id = create_resp.json()["id"]

        # Удаляем
        delete_resp = api_delete(api_base, f"/api/messenger/scripts/{script_id}", admin_headers)
        assert delete_resp.status_code == 200

        # Проверяем что удалён — обновление должно вернуть 404
        check_resp = api_put(
            api_base, f"/api/messenger/scripts/{script_id}", admin_headers,
            json={"is_enabled": True}
        )
        assert check_resp.status_code == 404

    def test_update_nonexistent_script(self, api_base, admin_headers):
        """PUT /api/messenger/scripts/999999 — несуществующий скрипт"""
        resp = api_put(
            api_base, "/api/messenger/scripts/999999", admin_headers,
            json={"is_enabled": True}
        )
        assert resp.status_code == 404

    def test_scripts_require_auth(self, api_base):
        """GET /api/messenger/scripts без токена — 401/403"""
        resp = api_get(api_base, "/api/messenger/scripts", {})
        assert resp.status_code in (401, 403)


# ==============================================================
# НАСТРОЙКИ МЕССЕНДЖЕРА
# ==============================================================

@pytest.mark.e2e
class TestMessengerSettings:
    """Тесты настроек мессенджера"""

    def test_get_settings(self, api_base, admin_headers):
        """GET /api/messenger/settings — получить настройки"""
        resp = api_get(api_base, "/api/messenger/settings", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_messenger_status(self, api_base, admin_headers):
        """GET /api/messenger/status — статус сервисов мессенджера"""
        resp = api_get(api_base, "/api/messenger/status", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Проверяем наличие ключевых полей статуса
        assert "telegram_bot_available" in data
        assert "telegram_mtproto_available" in data
        assert "email_available" in data

    def test_settings_require_auth(self, api_base):
        """GET /api/messenger/settings без токена — 401/403"""
        resp = api_get(api_base, "/api/messenger/settings", {})
        assert resp.status_code in (401, 403)
