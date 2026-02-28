# -*- coding: utf-8 -*-
"""
E2E Tests: Углублённые тесты агентов и городов (Этап 6)
~15 тестов — CRUD агентов и городов с мягким удалением,
дубликатами, include_deleted, восстановлением, конфликтами.
"""

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import (
    TEST_PREFIX, api_get, api_post, api_patch, api_delete,
    _http_session, REQUEST_TIMEOUT,
)


# ================================================================
# Вспомогательные функции
# ================================================================

def _find_agent_by_name(api_base, headers, name, include_deleted=False):
    """Найти агента по имени, вернуть dict или None."""
    resp = api_get(api_base, "/api/v1/agents", headers,
                   params={"include_deleted": str(include_deleted).lower()})
    if resp.status_code != 200:
        return None
    for agent in resp.json():
        if agent.get("name") == name:
            return agent
    return None


def _cleanup_agent(api_base, headers, name):
    """Удалить агента по имени (soft delete), если существует."""
    agent = _find_agent_by_name(api_base, headers, name, include_deleted=True)
    if agent:
        api_delete(api_base, f"/api/v1/agents/{agent['id']}", headers)


def _find_city_by_name(api_base, headers, name, include_deleted=False):
    """Найти город по имени, вернуть dict или None."""
    resp = api_get(api_base, "/api/v1/cities", headers,
                   params={"include_deleted": str(include_deleted).lower()})
    if resp.status_code != 200:
        return None
    for city in resp.json():
        if city.get("name") == name:
            return city
    return None


def _cleanup_city(api_base, headers, name):
    """Удалить город по имени (soft delete), если существует."""
    city = _find_city_by_name(api_base, headers, name, include_deleted=True)
    if city:
        api_delete(api_base, f"/api/v1/cities/{city['id']}", headers)


# ================================================================
# Агенты — CRUD и граничные случаи
# ================================================================

class TestAgentsDeep:
    """Углублённые тесты CRUD агентов"""

    def test_create_and_get_agent(self, api_base, admin_headers):
        """POST /api/v1/agents -> GET /api/v1/agents/{id} — создание и получение."""
        name = f"{TEST_PREFIX}АГЕНТ_DEEP_{int(time.time()) % 100000}"
        _cleanup_agent(api_base, admin_headers, name)

        # Создаём
        resp = api_post(api_base, "/api/v1/agents", admin_headers,
                        json={"name": name, "color": "#11AAFF"})
        assert resp.status_code == 200, f"Ожидался 200, получен {resp.status_code}: {resp.text}"
        data = resp.json()
        agent_id = data["id"]
        assert agent_id > 0

        # Получаем по ID
        resp2 = api_get(api_base, f"/api/v1/agents/{agent_id}", admin_headers)
        assert resp2.status_code == 200
        agent_data = resp2.json()
        assert agent_data["name"] == name
        assert agent_data["color"] == "#11AAFF"
        assert agent_data["status"] == "активный"

        # Очистка
        api_delete(api_base, f"/api/v1/agents/{agent_id}", admin_headers)

    def test_duplicate_agent_returns_400(self, api_base, admin_headers):
        """POST /api/v1/agents дважды с одинаковым именем -> 400 на втором запросе."""
        name = f"{TEST_PREFIX}ДУБЛИКАТ_DEEP_{int(time.time()) % 100000}"
        _cleanup_agent(api_base, admin_headers, name)

        # Первый — создаём
        resp1 = api_post(api_base, "/api/v1/agents", admin_headers,
                         json={"name": name, "color": "#AABB00"})
        assert resp1.status_code == 200

        # Второй — дубликат
        resp2 = api_post(api_base, "/api/v1/agents", admin_headers,
                         json={"name": name, "color": "#CCDD00"})
        assert resp2.status_code == 400, \
            f"Дубликат агента должен вернуть 400, получен {resp2.status_code}"
        assert "detail" in resp2.json(), "Ответ ошибки должен содержать detail"

        # Очистка
        agent = _find_agent_by_name(api_base, admin_headers, name)
        if agent:
            api_delete(api_base, f"/api/v1/agents/{agent['id']}", admin_headers)

    def test_soft_delete_agent(self, api_base, admin_headers):
        """DELETE /api/v1/agents/{id} — мягкое удаление, агент исчезает из активного списка."""
        name = f"{TEST_PREFIX}УДАЛЯЕМЫЙ_DEEP_{int(time.time()) % 100000}"
        _cleanup_agent(api_base, admin_headers, name)

        resp = api_post(api_base, "/api/v1/agents", admin_headers,
                        json={"name": name, "color": "#FF0000"})
        assert resp.status_code == 200
        agent_id = resp.json()["id"]

        # Удаляем
        del_resp = api_delete(api_base, f"/api/v1/agents/{agent_id}", admin_headers)
        assert del_resp.status_code == 200

        # Проверяем отсутствие в активном списке
        active_agent = _find_agent_by_name(api_base, admin_headers, name, include_deleted=False)
        assert active_agent is None, "Удалённый агент не должен быть в активном списке"

    def test_include_deleted_shows_deleted(self, api_base, admin_headers):
        """GET /api/v1/agents?include_deleted=true — удалённый агент виден."""
        name = f"{TEST_PREFIX}ВИДЕН_DEEP_{int(time.time()) % 100000}"
        _cleanup_agent(api_base, admin_headers, name)

        resp = api_post(api_base, "/api/v1/agents", admin_headers,
                        json={"name": name, "color": "#00FF00"})
        assert resp.status_code == 200
        agent_id = resp.json()["id"]

        # Удаляем
        api_delete(api_base, f"/api/v1/agents/{agent_id}", admin_headers)

        # С include_deleted — виден
        deleted_agent = _find_agent_by_name(api_base, admin_headers, name, include_deleted=True)
        assert deleted_agent is not None, "С include_deleted=true удалённый агент должен быть виден"
        assert deleted_agent["status"] == "удалён"

    def test_update_agent_color(self, api_base, admin_headers):
        """PATCH /api/v1/agents/{name}/color — обновление цвета."""
        name = f"{TEST_PREFIX}ЦВЕТ_DEEP_{int(time.time()) % 100000}"
        _cleanup_agent(api_base, admin_headers, name)

        resp = api_post(api_base, "/api/v1/agents", admin_headers,
                        json={"name": name, "color": "#000000"})
        assert resp.status_code == 200

        # Обновляем цвет
        patch_resp = api_patch(api_base, f"/api/v1/agents/{name}/color", admin_headers,
                               json={"color": "#FFFFFF"})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["color"] == "#FFFFFF"

        # Очистка
        agent = _find_agent_by_name(api_base, admin_headers, name)
        if agent:
            api_delete(api_base, f"/api/v1/agents/{agent['id']}", admin_headers)

    def test_get_nonexistent_agent_404(self, api_base, admin_headers):
        """GET /api/v1/agents/999999 — несуществующий агент -> 404."""
        resp = api_get(api_base, "/api/v1/agents/999999", admin_headers)
        assert resp.status_code == 404

    def test_delete_nonexistent_agent_404(self, api_base, admin_headers):
        """DELETE /api/v1/agents/999999 — несуществующий агент -> 404."""
        resp = api_delete(api_base, "/api/v1/agents/999999", admin_headers)
        assert resp.status_code == 404

    def test_agents_require_auth(self, api_base):
        """GET /api/v1/agents без авторизации -> 401."""
        resp = api_get(api_base, "/api/v1/agents", {})
        assert resp.status_code in (401, 403)


# ================================================================
# Города — CRUD и граничные случаи
# ================================================================

class TestCitiesDeep:
    """Углублённые тесты CRUD городов"""

    def test_create_and_list_city(self, api_base, admin_headers):
        """POST /api/v1/cities -> GET /api/v1/cities — город появляется в списке."""
        name = f"{TEST_PREFIX}ГОРОД_DEEP_{int(time.time()) % 100000}"
        _cleanup_city(api_base, admin_headers, name)

        resp = api_post(api_base, "/api/v1/cities", admin_headers,
                        json={"name": name})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data.get("status") == "success"
        city_id = data["id"]

        # Проверяем наличие в списке
        list_resp = api_get(api_base, "/api/v1/cities", admin_headers)
        assert list_resp.status_code == 200
        names = [c["name"] for c in list_resp.json()]
        assert name in names, f"Город '{name}' не найден в списке"

        # Очистка
        api_delete(api_base, f"/api/v1/cities/{city_id}", admin_headers)

    def test_duplicate_city_returns_400(self, api_base, admin_headers):
        """POST /api/v1/cities с дубликатом -> 400."""
        name = f"{TEST_PREFIX}ДУБГОРОД_DEEP_{int(time.time()) % 100000}"
        _cleanup_city(api_base, admin_headers, name)

        # Создаём первый
        resp1 = api_post(api_base, "/api/v1/cities", admin_headers,
                         json={"name": name})
        assert resp1.status_code in (200, 201)

        # Дубликат
        resp2 = api_post(api_base, "/api/v1/cities", admin_headers,
                         json={"name": name})
        assert resp2.status_code in (400, 409), \
            f"Дубликат города должен вернуть 400/409, получен {resp2.status_code}"

        # Очистка
        city = _find_city_by_name(api_base, admin_headers, name)
        if city:
            api_delete(api_base, f"/api/v1/cities/{city['id']}", admin_headers)

    def test_soft_delete_city(self, api_base, admin_headers):
        """DELETE /api/v1/cities/{id} — мягкое удаление."""
        name = f"{TEST_PREFIX}УДАЛГОРОД_DEEP_{int(time.time()) % 100000}"
        _cleanup_city(api_base, admin_headers, name)

        resp = api_post(api_base, "/api/v1/cities", admin_headers,
                        json={"name": name})
        assert resp.status_code in (200, 201)
        city_id = resp.json()["id"]

        # Удаляем
        del_resp = api_delete(api_base, f"/api/v1/cities/{city_id}", admin_headers)
        assert del_resp.status_code in (200, 204)

        # Проверяем отсутствие в активном списке
        city = _find_city_by_name(api_base, admin_headers, name, include_deleted=False)
        assert city is None, "Удалённый город не должен быть в активном списке"

    def test_restore_deleted_city(self, api_base, admin_headers):
        """POST /api/v1/cities с именем удалённого города — восстановление."""
        name = f"{TEST_PREFIX}ВОССТГОРОД_DEEP_{int(time.time()) % 100000}"
        _cleanup_city(api_base, admin_headers, name)

        # Создаём
        resp1 = api_post(api_base, "/api/v1/cities", admin_headers,
                         json={"name": name})
        assert resp1.status_code in (200, 201)
        city_id = resp1.json()["id"]

        # Удаляем
        api_delete(api_base, f"/api/v1/cities/{city_id}", admin_headers)

        # Восстанавливаем: POST с тем же именем -> роутер восстановит удалённый
        resp2 = api_post(api_base, "/api/v1/cities", admin_headers,
                         json={"name": name})
        assert resp2.status_code in (200, 201), \
            f"Восстановление удалённого города: ожидался 200/201, получен {resp2.status_code}"
        data = resp2.json()
        assert data.get("status") == "success"

        # Город снова в активном списке
        city = _find_city_by_name(api_base, admin_headers, name, include_deleted=False)
        assert city is not None, "Восстановленный город должен быть в активном списке"

        # Очистка
        api_delete(api_base, f"/api/v1/cities/{city['id']}", admin_headers)

    def test_include_deleted_shows_city(self, api_base, admin_headers):
        """GET /api/v1/cities?include_deleted=true — удалённый город виден."""
        name = f"{TEST_PREFIX}ВИДЕНГОРОД_DEEP_{int(time.time()) % 100000}"
        _cleanup_city(api_base, admin_headers, name)

        resp = api_post(api_base, "/api/v1/cities", admin_headers,
                        json={"name": name})
        assert resp.status_code in (200, 201)
        city_id = resp.json()["id"]

        api_delete(api_base, f"/api/v1/cities/{city_id}", admin_headers)

        # С include_deleted — виден
        city = _find_city_by_name(api_base, admin_headers, name, include_deleted=True)
        assert city is not None, "С include_deleted=true удалённый город должен быть виден"

    def test_delete_nonexistent_city_404(self, api_base, admin_headers):
        """DELETE /api/v1/cities/999999 — несуществующий город -> 404."""
        resp = api_delete(api_base, "/api/v1/cities/999999", admin_headers)
        assert resp.status_code == 404

    def test_cities_require_auth(self, api_base):
        """GET /api/v1/cities без авторизации -> 401."""
        resp = api_get(api_base, "/api/v1/cities", {})
        assert resp.status_code in (401, 403)
