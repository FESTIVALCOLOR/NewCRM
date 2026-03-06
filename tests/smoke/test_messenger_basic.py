# -*- coding: utf-8 -*-
"""
Smoke Tests: Messenger Basic — read-only endpoints мессенджера.

Покрывает: settings, status, scripts list, mtproto session-status,
chats by card/supervision (read-only, не отправляет сообщения).

Запуск: pytest tests/smoke/test_messenger_basic.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import _get


# ════════════════════════════════════════════════════════════
# 1. Messenger Status & Settings
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestMessengerStatus:
    """P2: Мессенджер — статус и настройки."""

    def test_messenger_status(self, admin_headers):
        """GET /messenger/status — статус мессенджера."""
        resp = _get("/api/messenger/status", admin_headers)
        assert resp.status_code == 200

    def test_messenger_settings(self, admin_headers):
        """GET /messenger/settings — настройки мессенджера."""
        resp = _get("/api/messenger/settings", admin_headers)
        assert resp.status_code == 200

    def test_mtproto_session_status(self, admin_headers):
        """GET /messenger/mtproto/session-status — статус MTProto сессии."""
        resp = _get("/api/messenger/mtproto/session-status", admin_headers)
        assert resp.status_code in (200, 404, 503)


# ════════════════════════════════════════════════════════════
# 2. Scripts
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestMessengerScripts:
    """P2: Мессенджер — скрипты."""

    def test_scripts_list(self, admin_headers):
        """GET /messenger/scripts — список скриптов."""
        resp = _get("/api/messenger/scripts", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ════════════════════════════════════════════════════════════
# 3. Chats (read-only)
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestMessengerChats:
    """P2: Мессенджер — чаты (только чтение)."""

    def test_chat_by_crm_card(self, admin_headers):
        """GET /messenger/chats/by-card/{card_id} — чат по CRM карточке."""
        cards = _get("/api/crm/cards", admin_headers, params={
            "project_type": "Индивидуальный",
        })
        if cards.status_code != 200 or not cards.json():
            pytest.skip("Нет CRM карточек")
        card_id = cards.json()[0]["id"]
        resp = _get(f"/api/messenger/chats/by-card/{card_id}", admin_headers)
        # 200 если чат есть, 404 если нет
        assert resp.status_code in (200, 404)

    def test_chat_by_supervision_card(self, admin_headers):
        """GET /messenger/chats/by-supervision/{id} — чат по карточке надзора."""
        cards = _get("/api/supervision/cards", admin_headers)
        if cards.status_code != 200 or not cards.json():
            pytest.skip("Нет карточек надзора")
        sid = cards.json()[0]["id"]
        resp = _get(f"/api/messenger/chats/by-supervision/{sid}", admin_headers)
        assert resp.status_code in (200, 404)
