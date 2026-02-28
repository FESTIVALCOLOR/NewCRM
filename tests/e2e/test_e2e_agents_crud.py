# -*- coding: utf-8 -*-
"""
E2E Tests: Агенты (CRUD)
5 тестов — GET/POST/PATCH endpoints агентов.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get, api_post, api_patch, api_delete, TEST_PREFIX


class TestAgentsCrud:
    """Тесты CRUD агентов"""

    def test_get_all_agents(self, api_base, admin_headers):
        """GET /api/v1/agents — получить список агентов"""
        resp = api_get(api_base, "/api/v1/agents", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Каждый агент должен содержать id, name (и full_name как алиас)
        for agent in data:
            assert "id" in agent, f"Агент должен иметь поле id: {agent}"
            assert "name" in agent, f"Агент должен иметь поле name: {agent}"
            assert isinstance(agent["id"], int), "id агента должен быть целым числом"
            assert isinstance(agent["name"], str), "name агента должен быть строкой"
            assert len(agent["name"]) > 0, "name агента не должен быть пустым"

    def test_add_agent(self, api_base, admin_headers):
        """POST /api/v1/agents — добавить нового агента"""
        agent_name = f"{TEST_PREFIX}АГЕНТ"
        resp = api_post(
            api_base, "/api/v1/agents", admin_headers,
            json={"name": agent_name, "color": "#FF5733"}
        )
        assert resp.status_code in (200, 400)  # 400 если уже существует
        if resp.status_code == 200:
            data = resp.json()
            # Проверяем что созданный агент содержит id в ответе
            assert "id" in data, "Ответ создания агента должен содержать id"
            assert isinstance(data["id"], int), "id в ответе создания агента должен быть целым числом"
            assert data["id"] > 0, "id агента должен быть положительным"
            # Проверяем что агент появился в списке
            list_resp = api_get(api_base, "/api/v1/agents", admin_headers)
            agents = list_resp.json()
            assert any(a.get("full_name") == agent_name or a.get("name") == agent_name for a in agents)

    def test_update_agent_color(self, api_base, admin_headers):
        """PATCH /api/v1/agents/{name}/color — обновить цвет агента"""
        # Используем существующего агента
        resp = api_get(api_base, "/api/v1/agents", admin_headers)
        agents = resp.json()
        if agents:
            agent_name = agents[0].get("full_name") or agents[0].get("name", "ФЕСТИВАЛЬ")
            patch_resp = api_patch(
                api_base, f"/api/v1/agents/{agent_name}/color", admin_headers,
                json={"color": "#FFD93C"}
            )
            assert patch_resp.status_code in (200, 404)

    def test_update_nonexistent_agent(self, api_base, admin_headers):
        """PATCH /api/v1/agents/NONEXISTENT/color — несуществующий агент"""
        resp = api_patch(
            api_base, "/api/v1/agents/NONEXISTENT_999/color", admin_headers,
            json={"color": "#000000"}
        )
        assert resp.status_code in (404, 422)

    def test_delete_agent(self, api_base, admin_headers):
        """POST создать агента → DELETE удалить → GET проверить отсутствие в списке"""
        # Создаём агента специально для удаления
        agent_name = f"{TEST_PREFIX}УДАЛЯЕМЫЙ"
        create_resp = api_post(
            api_base, "/api/v1/agents", admin_headers,
            json={"name": agent_name, "color": "#AABBCC"}
        )
        if create_resp.status_code == 400:
            # Агент уже существует — найдём его id
            list_resp = api_get(api_base, "/api/v1/agents", admin_headers,
                                params={"include_deleted": "false"})
            agents = list_resp.json()
            agent = next((a for a in agents if a.get("name") == agent_name), None)
            if not agent:
                # Агент не найден (возможно удалён ранее) — пропускаем
                return
            agent_id = agent["id"]
        else:
            assert create_resp.status_code == 200
            agent_id = create_resp.json()["id"]

        # Удаляем агента
        del_resp = api_delete(api_base, f"/api/v1/agents/{agent_id}", admin_headers)
        assert del_resp.status_code in (200, 204, 409), (
            f"DELETE агента: ожидается 200/204/409, получено {del_resp.status_code}"
        )

        if del_resp.status_code in (200, 204):
            # Проверяем что агент больше не в активном списке
            list_resp = api_get(api_base, "/api/v1/agents", admin_headers)
            assert list_resp.status_code == 200
            agents = list_resp.json()
            # После мягкого удаления агент должен отсутствовать в списке (без include_deleted)
            assert not any(a.get("id") == agent_id for a in agents), (
                f"Удалённый агент id={agent_id} не должен присутствовать в активном списке"
            )

    def test_create_duplicate_agent(self, api_base, admin_headers):
        """POST с одинаковым именем дважды → второй запрос должен вернуть 400"""
        agent_name = f"{TEST_PREFIX}ДУБЛИКАТ"

        # Первый запрос — создаём агента
        first_resp = api_post(
            api_base, "/api/v1/agents", admin_headers,
            json={"name": agent_name, "color": "#123456"}
        )
        # Первый запрос: 200 (создан) или 400 (уже был создан ранее)
        assert first_resp.status_code in (200, 400)

        # Второй запрос с тем же именем — обязательно 400
        second_resp = api_post(
            api_base, "/api/v1/agents", admin_headers,
            json={"name": agent_name, "color": "#654321"}
        )
        assert second_resp.status_code == 400, (
            f"Дубликат агента '{agent_name}': ожидается 400, получено {second_resp.status_code}"
        )
        # В теле ответа должно быть описание ошибки
        error_data = second_resp.json()
        assert "detail" in error_data, "Ответ ошибки должен содержать ключ detail"

    def test_agents_require_auth(self, api_base):
        """GET /api/v1/agents без токена — 401"""
        resp = api_get(api_base, "/api/v1/agents", {})
        assert resp.status_code in (401, 403)
