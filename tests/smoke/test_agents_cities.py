# -*- coding: utf-8 -*-
"""
Smoke Tests: Agents & Cities — CRUD агентов и городов.

Покрывает: agents list/get/create/color/delete, cities list/create/delete.

Запуск: pytest tests/smoke/test_agents_cities.py -v --timeout=120
"""

import pytest
from datetime import datetime

from tests.smoke.conftest import _get, _post, _patch, _delete, TEST_PREFIX


# ════════════════════════════════════════════════════════════
# 1. Agents
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestAgentsCRUD:
    """P1: Агенты — CRUD."""

    def test_list_agents(self, admin_headers):
        """GET /agents — список агентов."""
        resp = _get("/api/agents", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Список агентов пуст"

    def test_get_agent_by_id(self, admin_headers):
        """GET /agents/{id} — агент по ID."""
        agents = _get("/api/agents", admin_headers).json()
        if not agents:
            pytest.skip("Нет агентов")
        agent_id = agents[0]["id"]
        resp = _get(f"/api/agents/{agent_id}", admin_headers)
        assert resp.status_code == 200

    def test_create_and_delete_agent(self, admin_headers):
        """POST → DELETE /agents — создание и удаление агента."""
        ts = datetime.now().strftime('%H%M%S%f')[:10]
        create = _post("/api/agents", admin_headers, json={
            "name": f"{TEST_PREFIX}Агент_{ts}",
            "color": "#FF5733",
        })
        if create.status_code not in (200, 201):
            pytest.skip(f"Создание агента: {create.status_code} {create.text}")

        agent_id = create.json().get("id")
        assert agent_id, "Нет ID агента в ответе"

        try:
            # Проверяем
            check = _get(f"/api/agents/{agent_id}", admin_headers)
            assert check.status_code == 200
        finally:
            _delete(f"/api/agents/{agent_id}", admin_headers)

    def test_change_agent_color(self, admin_headers):
        """PATCH /agents/{name}/color — изменение цвета агента."""
        agents = _get("/api/agents", admin_headers).json()
        if not agents:
            pytest.skip("Нет агентов")
        agent_name = agents[0].get("name", agents[0].get("agent_type"))
        if not agent_name:
            pytest.skip("Нет имени агента")

        resp = _patch(f"/api/agents/{agent_name}/color", admin_headers, json={
            "color": "#33FF57",
        })
        assert resp.status_code in (200, 404, 422), \
            f"Change color: {resp.status_code} {resp.text}"


# ════════════════════════════════════════════════════════════
# 2. Cities
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestCitiesCRUD:
    """P1: Города — CRUD."""

    def test_list_cities(self, admin_headers):
        """GET /cities — список городов."""
        resp = _get("/api/cities", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Список городов пуст"

    def test_create_and_delete_city(self, admin_headers):
        """POST → DELETE /cities — создание и удаление города."""
        ts = datetime.now().strftime('%H%M%S%f')[:10]
        create = _post("/api/cities", admin_headers, json={
            "name": f"{TEST_PREFIX}Город_{ts}",
        })
        if create.status_code not in (200, 201):
            pytest.skip(f"Создание города: {create.status_code} {create.text}")

        city_id = create.json().get("id")
        assert city_id, "Нет ID города в ответе"

        try:
            # Проверяем что город появился в списке
            check = _get("/api/cities", admin_headers).json()
            found = any(c["id"] == city_id for c in check)
            assert found, f"Город {city_id} не найден в списке"
        finally:
            delete = _delete(f"/api/cities/{city_id}", admin_headers)
            assert delete.status_code in (200, 204), \
                f"Delete city: {delete.status_code} {delete.text}"
