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


# ==============================================================
# КЛЮЧИ СКРИПТОВ МЕССЕНДЖЕРА
# ==============================================================

@pytest.mark.e2e
class TestMessengerScriptKeys:
    """Проверка структуры ключей объектов скриптов мессенджера"""

    def test_script_keys_structure(self, api_base, admin_headers):
        """Проверка ключей объекта скрипта: id, script_type, stage_name, message_template, is_enabled, sort_order"""
        resp = api_get(api_base, "/api/messenger/scripts", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            for item in data[:5]:
                assert "id" in item, "Скрипт должен содержать поле 'id'"
                assert "script_type" in item, "Скрипт должен содержать поле 'script_type'"
                assert "message_template" in item, "Скрипт должен содержать поле 'message_template'"
                assert "is_enabled" in item, "Скрипт должен содержать поле 'is_enabled'"
                assert "sort_order" in item, "Скрипт должен содержать поле 'sort_order'"
                assert "use_auto_deadline" in item, "Скрипт должен содержать поле 'use_auto_deadline'"

    def test_script_types_are_valid(self, api_base, admin_headers):
        """Типы скриптов принимают только допустимые значения"""
        valid_types = {"project_start", "stage_complete", "project_end", "supervision_start", "supervision_end"}
        resp = api_get(api_base, "/api/messenger/scripts", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        for script in data[:10]:
            assert script["script_type"] in valid_types, (
                f"Тип скрипта '{script['script_type']}' не входит в допустимые: {valid_types}"
            )

    def test_script_is_enabled_is_bool(self, api_base, admin_headers):
        """Поле is_enabled всегда булево"""
        resp = api_get(api_base, "/api/messenger/scripts", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        if data:
            for item in data[:5]:
                assert isinstance(item["is_enabled"], bool), (
                    f"is_enabled должно быть bool, получили: {type(item['is_enabled'])}"
                )

    def test_create_script_returns_full_keys(self, api_base, admin_headers):
        """POST /api/messenger/scripts — ответ содержит все ключи"""
        payload = {
            "script_type": "project_start",
            "project_type": None,
            "stage_name": None,
            "message_template": f"{TEST_PREFIX} проверка ключей скрипта",
            "use_auto_deadline": True,
            "is_enabled": True,
            "sort_order": 200
        }
        resp = api_post(api_base, "/api/messenger/scripts", admin_headers, json=payload)
        assert resp.status_code == 200
        data = resp.json()
        # Проверяем все ожидаемые ключи
        required_keys = ["id", "script_type", "message_template", "is_enabled",
                         "sort_order", "use_auto_deadline"]
        for key in required_keys:
            assert key in data, f"Ответ должен содержать ключ '{key}'"
        assert data["use_auto_deadline"] is True
        assert data["script_type"] == "project_start"
        # Очищаем
        api_delete(api_base, f"/api/messenger/scripts/{data['id']}", admin_headers)

    def test_filter_scripts_by_project_type(self, api_base, admin_headers):
        """GET /api/messenger/scripts?project_type=Индивидуальный — фильтрация по типу проекта"""
        resp = api_get(
            api_base, "/api/messenger/scripts", admin_headers,
            params={"project_type": "Индивидуальный"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Результаты должны быть либо с project_type=Индивидуальный, либо project_type=null (общие)
        for script in data:
            assert script.get("project_type") in (None, "Индивидуальный"), (
                f"Фильтр по project_type вернул скрипт с project_type='{script.get('project_type')}'"
            )

    def test_filter_scripts_by_stage_complete_type(self, api_base, admin_headers):
        """GET /api/messenger/scripts?script_type=stage_complete — проверка наличия поля stage_name"""
        resp = api_get(
            api_base, "/api/messenger/scripts", admin_headers,
            params={"script_type": "stage_complete"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for script in data:
            assert script["script_type"] == "stage_complete"
            # stage_name может быть null (шаблон для любой стадии), но ключ обязан присутствовать
            assert "stage_name" in script, "Скрипт stage_complete должен содержать ключ 'stage_name'"


# ==============================================================
# НАСТРОЙКИ МЕССЕНДЖЕРА — РАСШИРЕННЫЕ ПРОВЕРКИ
# ==============================================================

@pytest.mark.e2e
class TestMessengerSettingsExtended:
    """Расширенные тесты настроек и статуса мессенджера"""

    def test_settings_keys_structure(self, api_base, admin_headers):
        """GET /api/messenger/settings — проверка структуры ключей настройки"""
        resp = api_get(api_base, "/api/messenger/settings", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            for item in data[:5]:
                assert "setting_key" in item, "Настройка должна содержать поле 'setting_key'"
                assert "setting_value" in item, "Настройка должна содержать поле 'setting_value'"

    def test_update_settings_bulk(self, api_base, admin_headers):
        """PUT /api/messenger/settings — массовое обновление настроек"""
        payload = {
            "settings": [
                {
                    "setting_key": f"test_key_{TEST_PREFIX}",
                    "setting_value": "test_value"
                }
            ]
        }
        resp = api_put(api_base, "/api/messenger/settings", admin_headers, json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] == "updated"
        assert "bot_available" in data
        assert "email_available" in data

    def test_status_returns_all_service_flags(self, api_base, admin_headers):
        """GET /api/messenger/status — возвращает флаги всех сервисов"""
        resp = api_get(api_base, "/api/messenger/status", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "telegram_bot_available" in data
        assert "telegram_mtproto_available" in data
        assert "email_available" in data
        assert isinstance(data["telegram_bot_available"], bool)
        assert isinstance(data["telegram_mtproto_available"], bool)
        assert isinstance(data["email_available"], bool)

    def test_status_requires_auth(self, api_base):
        """GET /api/messenger/status без токена — 401/403"""
        resp = api_get(api_base, "/api/messenger/status", {})
        assert resp.status_code in (401, 403)

    def test_update_settings_requires_auth(self, api_base):
        """PUT /api/messenger/settings без токена — 401/403"""
        payload = {"settings": [{"setting_key": "test", "setting_value": "val"}]}
        resp = api_put(api_base, "/api/messenger/settings", {}, json=payload)
        assert resp.status_code in (401, 403)


# ==============================================================
# СИНХРОНИЗАЦИЯ ДАННЫХ МЕССЕНДЖЕРА
# ==============================================================

@pytest.mark.e2e
class TestMessengerSync:
    """Тесты sync-эндпоинтов мессенджера"""

    def test_sync_scripts_endpoint(self, api_base, admin_headers):
        """GET /api/sync/messenger-scripts — синхронизация скриптов"""
        resp = api_get(api_base, "/api/sync/messenger-scripts", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            for item in data[:5]:
                assert "id" in item
                assert "script_type" in item
                assert "message_template" in item
                assert "is_enabled" in item
                assert "sort_order" in item

    def test_sync_chats_endpoint(self, api_base, admin_headers):
        """GET /api/sync/messenger-chats — синхронизация чатов"""
        resp = api_get(api_base, "/api/sync/messenger-chats", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            for item in data[:5]:
                assert "id" in item
                assert "contract_id" in item
                assert "messenger_type" in item
                assert "is_active" in item
                assert "creation_method" in item

    def test_sync_scripts_requires_auth(self, api_base):
        """GET /api/sync/messenger-scripts без токена — 401/403"""
        resp = api_get(api_base, "/api/sync/messenger-scripts", {})
        assert resp.status_code in (401, 403)


# ==============================================================
# ЧАТЫ МЕССЕНДЖЕРА — ПОЛУЧЕНИЕ ПО КАРТОЧКЕ (несуществующие)
# ==============================================================

@pytest.mark.e2e
class TestMessengerChatRetrieval:
    """Тесты получения чатов мессенджера"""

    def test_get_chat_by_nonexistent_card(self, api_base, admin_headers):
        """GET /api/messenger/chats/by-card/999999 — несуществующая карточка возвращает 404"""
        resp = api_get(api_base, "/api/messenger/chats/by-card/999999", admin_headers)
        assert resp.status_code == 404

    def test_get_chat_by_supervision_nonexistent(self, api_base, admin_headers):
        """GET /api/messenger/chats/by-supervision/999999 — несуществующий надзор возвращает 404"""
        resp = api_get(api_base, "/api/messenger/chats/by-supervision/999999", admin_headers)
        assert resp.status_code == 404

    def test_chat_by_card_requires_auth(self, api_base):
        """GET /api/messenger/chats/by-card/1 без токена — 401/403"""
        resp = api_get(api_base, "/api/messenger/chats/by-card/1", {})
        assert resp.status_code in (401, 403)
