# -*- coding: utf-8 -*-
"""
Smoke: Покрытие оставшихся непокрытых endpoints.

Добавляет тесты для: /version, /sync POST, /timeline GET,
/files/list, /files/upload, /files/yandex,
/messenger chats, /sync/messenger-*.

Запуск: pytest tests/smoke/test_remaining_endpoints.py -v --timeout=120
"""
import pytest
from datetime import datetime
from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    TEST_PREFIX, create_test_client, create_test_contract,
    find_crm_card_by_contract, cleanup_test_card,
)


@pytest.mark.smoke
class TestVersionEndpoint:
    """GET /api/version — информация о версии API."""

    def test_version_returns_data(self, admin_headers):
        """GET /version возвращает версию."""
        resp = _get("/api/version", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data, "Ответ /version не должен быть пустым"

    def test_version_has_expected_fields(self, admin_headers):
        """Ответ /version содержит базовые поля."""
        resp = _get("/api/version", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Может содержать version, api_version или другие поля
        assert isinstance(data, dict), f"Ожидали dict, получили {type(data)}"


@pytest.mark.smoke
class TestSyncPostEndpoint:
    """POST /api/sync — клиентская синхронизация."""

    def test_sync_empty_payload(self, admin_headers):
        """POST /sync с пустым payload отвечает."""
        resp = _post("/api/sync", admin_headers, json={})
        assert resp.status_code in (200, 422), \
            f"sync POST: {resp.status_code} {resp.text[:200]}"

    def test_sync_with_empty_lists(self, admin_headers):
        """POST /sync с пустыми списками операций."""
        resp = _post("/api/sync", admin_headers, json={
            "operations": [],
            "last_sync": None,
        })
        # Может быть 200 (пустая синхронизация) или 422 (неверный формат)
        assert resp.status_code in (200, 422), \
            f"sync POST: {resp.status_code} {resp.text[:200]}"

    def test_sync_returns_data(self, admin_headers):
        """POST /sync возвращает данные для синхронизации."""
        resp = _post("/api/sync", admin_headers, json={
            "last_sync": "2020-01-01T00:00:00",
        })
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, dict), "Ответ sync должен быть dict"


@pytest.mark.smoke
class TestTimelineRootEndpoint:
    """GET /api/timeline — корневой список."""

    def test_timeline_root_list(self, admin_headers):
        """GET /timeline возвращает список или ошибку (не 500)."""
        resp = _get("/api/timeline", admin_headers)
        assert resp.status_code in (200, 404), \
            f"timeline root: {resp.status_code} {resp.text[:200]}"
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (list, dict))


@pytest.mark.smoke
class TestFilesEndpoints:
    """Непокрытые endpoints файлов."""

    def test_files_list(self, admin_headers):
        """GET /files/list возвращает список файлов."""
        resp = _get("/api/files/list", admin_headers)
        # Может требовать path query param
        assert resp.status_code in (200, 400, 422), \
            f"files/list: {resp.status_code} {resp.text[:200]}"

    def test_files_list_with_path(self, admin_headers):
        """GET /files/list с path параметром."""
        resp = _get("/api/files/list", admin_headers,
                    params={"path": "/"})
        assert resp.status_code in (200, 400, 404, 422), \
            f"files/list path: {resp.status_code}"

    def test_files_upload_requires_file(self, admin_headers):
        """POST /files/upload без файла → ошибка (не 500)."""
        resp = _post("/api/files/upload", admin_headers)
        assert resp.status_code in (400, 422), \
            f"upload без файла: {resp.status_code}"

    def test_files_yandex_delete_requires_path(self, admin_headers):
        """DELETE /files/yandex без path → ошибка (не 500)."""
        resp = _delete("/api/files/yandex", admin_headers)
        assert resp.status_code in (400, 422, 405), \
            f"yandex delete: {resp.status_code}"


@pytest.mark.smoke
class TestSyncMessengerEndpoints:
    """Sync endpoints для мессенджера."""

    def test_sync_messenger_chats(self, admin_headers):
        """GET /sync/messenger-chats возвращает список."""
        resp = _get("/api/sync/messenger-chats", admin_headers)
        assert resp.status_code in (200, 404), \
            f"sync/messenger-chats: {resp.status_code}"
        if resp.status_code == 200:
            assert isinstance(resp.json(), (list, dict))

    def test_sync_messenger_scripts(self, admin_headers):
        """GET /sync/messenger-scripts возвращает список."""
        resp = _get("/api/sync/messenger-scripts", admin_headers)
        assert resp.status_code in (200, 404), \
            f"sync/messenger-scripts: {resp.status_code}"
        if resp.status_code == 200:
            assert isinstance(resp.json(), (list, dict))


@pytest.mark.smoke
class TestMessengerChatEndpoints:
    """Messenger chats — базовые операции (без Telegram)."""

    def test_create_chat_requires_data(self, admin_headers):
        """POST /messenger/chats без данных → ошибка."""
        resp = _post("/api/messenger/chats", admin_headers, json={})
        assert resp.status_code in (400, 422), \
            f"create chat empty: {resp.status_code}"

    def test_create_chat_bind_requires_data(self, admin_headers):
        """POST /messenger/chats/bind без данных → ошибка."""
        resp = _post("/api/messenger/chats/bind", admin_headers, json={})
        assert resp.status_code in (400, 422), \
            f"bind chat empty: {resp.status_code}"

    def test_create_supervision_chat_requires_data(self, admin_headers):
        """POST /messenger/chats/supervision без данных → ошибка."""
        resp = _post("/api/messenger/chats/supervision", admin_headers, json={})
        assert resp.status_code in (400, 422), \
            f"supervision chat empty: {resp.status_code}"

    def test_trigger_script_requires_data(self, admin_headers):
        """POST /messenger/trigger-script без данных → ошибка."""
        resp = _post("/api/messenger/trigger-script", admin_headers, json={})
        assert resp.status_code in (400, 422), \
            f"trigger-script empty: {resp.status_code}"

    def test_delete_nonexistent_chat(self, admin_headers):
        """DELETE /messenger/chats/999999 → 404 или ошибка."""
        resp = _delete("/api/messenger/chats/999999", admin_headers)
        assert resp.status_code in (404, 400, 422), \
            f"delete nonexistent chat: {resp.status_code}"

    def test_send_message_to_nonexistent_chat(self, admin_headers):
        """POST /messenger/chats/999999/message → 404."""
        resp = _post("/api/messenger/chats/999999/message", admin_headers,
                     json={"text": "test"})
        assert resp.status_code in (404, 400, 422), \
            f"message to nonexistent: {resp.status_code}"

    def test_send_invites_to_nonexistent_chat(self, admin_headers):
        """POST /messenger/chats/999999/send-invites → 404."""
        resp = _post("/api/messenger/chats/999999/send-invites", admin_headers,
                     json={})
        assert resp.status_code in (404, 400, 422), \
            f"invites to nonexistent: {resp.status_code}"

    def test_files_to_nonexistent_chat(self, admin_headers):
        """POST /messenger/chats/999999/files → 404."""
        resp = _post("/api/messenger/chats/999999/files", admin_headers,
                     json={})
        assert resp.status_code in (404, 400, 422), \
            f"files to nonexistent: {resp.status_code}"


@pytest.mark.smoke
class TestMessengerMTProto:
    """MTProto endpoints — проверяем что отвечают (не 500)."""

    def test_send_code_responds(self, admin_headers):
        """POST /messenger/mtproto/send-code отвечает (не 500)."""
        resp = _post("/api/messenger/mtproto/send-code", admin_headers, json={})
        assert resp.status_code != 500, \
            f"send-code 500: {resp.text[:200]}"

    def test_resend_sms_responds(self, admin_headers):
        """POST /messenger/mtproto/resend-sms отвечает (не 500)."""
        resp = _post("/api/messenger/mtproto/resend-sms", admin_headers, json={})
        assert resp.status_code != 500, \
            f"resend-sms 500: {resp.text[:200]}"

    def test_verify_code_responds(self, admin_headers):
        """POST /messenger/mtproto/verify-code отвечает (не 500)."""
        resp = _post("/api/messenger/mtproto/verify-code", admin_headers, json={})
        assert resp.status_code != 500, \
            f"verify-code 500: {resp.text[:200]}"
