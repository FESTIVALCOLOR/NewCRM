# -*- coding: utf-8 -*-
"""
E2E Tests: Агенты (CRUD)
5 тестов — GET/POST/PATCH endpoints агентов.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get, api_post, api_patch, TEST_PREFIX


class TestAgentsCrud:
    """Тесты CRUD агентов"""

    def test_get_all_agents(self, api_base, admin_headers):
        """GET /api/agents — получить список агентов"""
        resp = api_get(api_base, "/api/agents", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_add_agent(self, api_base, admin_headers):
        """POST /api/agents — добавить нового агента"""
        agent_name = f"{TEST_PREFIX}АГЕНТ"
        resp = api_post(
            api_base, "/api/agents", admin_headers,
            json={"name": agent_name, "color": "#FF5733"}
        )
        assert resp.status_code in (200, 400)  # 400 если уже существует
        if resp.status_code == 200:
            # Очистка: проверяем что агент создан
            list_resp = api_get(api_base, "/api/agents", admin_headers)
            agents = list_resp.json()
            assert any(a.get("full_name") == agent_name or a.get("name") == agent_name for a in agents)

    def test_update_agent_color(self, api_base, admin_headers):
        """PATCH /api/agents/{name}/color — обновить цвет агента"""
        # Используем существующего агента
        resp = api_get(api_base, "/api/agents", admin_headers)
        agents = resp.json()
        if agents:
            agent_name = agents[0].get("full_name") or agents[0].get("name", "ФЕСТИВАЛЬ")
            patch_resp = api_patch(
                api_base, f"/api/agents/{agent_name}/color", admin_headers,
                json={"color": "#FFD93C"}
            )
            assert patch_resp.status_code in (200, 404)

    def test_update_nonexistent_agent(self, api_base, admin_headers):
        """PATCH /api/agents/NONEXISTENT/color — несуществующий агент"""
        resp = api_patch(
            api_base, "/api/agents/NONEXISTENT_999/color", admin_headers,
            json={"color": "#000000"}
        )
        assert resp.status_code in (404, 422)

    def test_agents_require_auth(self, api_base):
        """GET /api/agents без токена — 401"""
        resp = api_get(api_base, "/api/agents", {})
        assert resp.status_code in (401, 403)
