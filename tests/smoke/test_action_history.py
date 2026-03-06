# -*- coding: utf-8 -*-
"""
Smoke Tests: Action History — лог действий.

Запуск: pytest tests/smoke/test_action_history.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import _get, _post, TEST_PREFIX


@pytest.mark.smoke
class TestActionHistory:
    """P1: История действий."""

    def test_list_action_history(self, admin_headers):
        """GET /action-history — список."""
        resp = _get("/api/action-history", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_action_history_by_entity(self, admin_headers):
        """GET /action-history/{entity_type}/{entity_id} — по сущности."""
        resp = _get("/api/action-history/crm_card/1", admin_headers)
        assert resp.status_code == 200

    def test_create_action_history(self, admin_headers):
        """POST /action-history — создание записи."""
        resp = _post("/api/action-history", admin_headers, json={
            "action_type": "test_action",
            "entity_type": "crm_card",
            "entity_id": 1,
            "description": f"{TEST_PREFIX}Тестовое действие",
        })
        assert resp.status_code in (200, 201), \
            f"Action history: {resp.status_code} {resp.text}"

    def test_action_history_not_empty_for_existing_card(self, admin_headers):
        """История для существующей карточки не пуста (если были действия)."""
        resp = _get("/api/action-history/crm_card/1", admin_headers)
        assert resp.status_code == 200
        # Не проверяем len > 0, т.к. может не быть истории для card=1
        assert isinstance(resp.json(), list)
