# -*- coding: utf-8 -*-
"""
E2E Tests: Города (cities)
Тесты CRUD endpoints городов.

Endpoints:
  GET    /api/cities         — список городов (только активные по умолчанию)
  POST   /api/cities         — создать город (требует rights: cities.create)
  DELETE /api/cities/{id}    — мягкое удаление города (требует rights: cities.delete)
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import (
    TEST_PREFIX,
    api_get,
    api_post,
    api_delete,
    _http_session,
    REQUEST_TIMEOUT,
)

# Имя тестового города с TEST_PREFIX для изоляции
TEST_CITY_NAME = f"{TEST_PREFIX}ТестГород"


@pytest.mark.e2e
class TestCities:
    """E2E тесты для endpoints городов"""

    # ------------------------------------------------------------------ #
    #  1. GET /api/cities — список городов
    # ------------------------------------------------------------------ #

    def test_get_cities_returns_list(self, api_base, admin_headers):
        """GET /api/cities возвращает список (list), каждый элемент содержит id и name"""
        resp = api_get(api_base, "/api/cities", admin_headers)

        assert resp.status_code == 200, (
            f"Ожидался 200, получено {resp.status_code}: {resp.text}"
        )

        data = resp.json()
        assert isinstance(data, list), f"Ответ должен быть списком, получено: {type(data)}"

        # Каждый элемент должен быть dict с полями id и name
        for item in data:
            assert isinstance(item, dict), f"Элемент списка должен быть dict: {item}"
            assert "id" in item, f"Элемент должен содержать 'id': {item}"
            assert "name" in item, f"Элемент должен содержать 'name': {item}"
            assert isinstance(item["id"], int), f"id должен быть int: {item['id']}"
            assert isinstance(item["name"], str), f"name должен быть str: {item['name']}"

    # ------------------------------------------------------------------ #
    #  2. POST /api/cities — создать город
    # ------------------------------------------------------------------ #

    def test_create_city(self, api_base, admin_headers):
        """POST /api/cities создаёт новый город, возвращает 200 или 201"""
        # Предварительно чистим, если осталось с прошлого запуска
        _cleanup_test_city(api_base, admin_headers, TEST_CITY_NAME)

        resp = api_post(
            api_base,
            "/api/cities",
            admin_headers,
            json={"name": TEST_CITY_NAME},
        )

        assert resp.status_code in (200, 201), (
            f"Ожидался 200 или 201, получено {resp.status_code}: {resp.text}"
        )

        data = resp.json()
        assert data.get("status") == "success", f"Поле status должно быть 'success': {data}"
        assert "id" in data, f"Ответ должен содержать id нового города: {data}"
        assert data.get("name") == TEST_CITY_NAME, (
            f"Имя города в ответе не совпадает: ожидалось '{TEST_CITY_NAME}', получено '{data.get('name')}'"
        )

    # ------------------------------------------------------------------ #
    #  3. GET после POST — новый город в списке
    # ------------------------------------------------------------------ #

    def test_created_city_appears_in_list(self, api_base, admin_headers):
        """После создания GET /api/cities содержит новый город"""
        # Убедиться что город создан
        _ensure_test_city_exists(api_base, admin_headers, TEST_CITY_NAME)

        resp = api_get(api_base, "/api/cities", admin_headers)
        assert resp.status_code == 200

        cities = resp.json()
        names = [c.get("name") for c in cities]
        assert TEST_CITY_NAME in names, (
            f"Город '{TEST_CITY_NAME}' не найден в списке городов: {names}"
        )

    # ------------------------------------------------------------------ #
    #  4. DELETE — удалить созданный город
    # ------------------------------------------------------------------ #

    def test_delete_city(self, api_base, admin_headers):
        """DELETE /api/cities/{id} успешно удаляет город (мягкое удаление)"""
        city_id = _ensure_test_city_exists(api_base, admin_headers, TEST_CITY_NAME)
        assert city_id is not None, "Не удалось создать тестовый город для удаления"

        resp = api_delete(api_base, f"/api/cities/{city_id}", admin_headers)
        assert resp.status_code in (200, 204), (
            f"Ожидался 200 или 204, получено {resp.status_code}: {resp.text}"
        )

        # Проверяем что город исчез из активного списка
        list_resp = api_get(api_base, "/api/cities", admin_headers)
        assert list_resp.status_code == 200
        names = [c.get("name") for c in list_resp.json()]
        assert TEST_CITY_NAME not in names, (
            f"Город '{TEST_CITY_NAME}' должен быть удалён, но всё ещё есть в списке"
        )

    # ------------------------------------------------------------------ #
    #  5. POST дубликат — 400 или 409
    # ------------------------------------------------------------------ #

    def test_create_duplicate_city_returns_error(self, api_base, admin_headers):
        """POST /api/cities с уже существующим именем возвращает 400"""
        # Создать город
        _ensure_test_city_exists(api_base, admin_headers, TEST_CITY_NAME)

        # Попытка создать дубликат
        resp = api_post(
            api_base,
            "/api/cities",
            admin_headers,
            json={"name": TEST_CITY_NAME},
        )

        assert resp.status_code in (400, 409), (
            f"Ожидался 400 или 409 при дубликате, получено {resp.status_code}: {resp.text}"
        )

        # Чистим после теста
        _cleanup_test_city(api_base, admin_headers, TEST_CITY_NAME)

    # ------------------------------------------------------------------ #
    #  6. GET без авторизации — 401 или 403
    # ------------------------------------------------------------------ #

    def test_get_cities_without_auth_returns_401(self, api_base):
        """GET /api/cities без токена авторизации возвращает 401 или 403"""
        resp = api_get(api_base, "/api/cities", headers={})

        assert resp.status_code in (401, 403), (
            f"Ожидался 401 или 403 без авторизации, получено {resp.status_code}: {resp.text}"
        )

    # ------------------------------------------------------------------ #
    #  7. DELETE несуществующего — 404
    # ------------------------------------------------------------------ #

    def test_delete_nonexistent_city_returns_404(self, api_base, admin_headers):
        """DELETE /api/cities/{id} для несуществующего id возвращает 404"""
        nonexistent_id = 999999999

        resp = api_delete(api_base, f"/api/cities/{nonexistent_id}", admin_headers)

        assert resp.status_code == 404, (
            f"Ожидался 404 для несуществующего города, получено {resp.status_code}: {resp.text}"
        )


# ------------------------------------------------------------------ #
# Вспомогательные функции
# ------------------------------------------------------------------ #

def _get_city_id_by_name(api_base: str, admin_headers: dict, name: str) -> int | None:
    """Найти id города по имени (включая удалённые)"""
    resp = _http_session.get(
        f"{api_base}/api/cities",
        headers=admin_headers,
        params={"include_deleted": True},
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code != 200:
        return None
    for city in resp.json():
        if city.get("name") == name:
            return city.get("id")
    return None


def _ensure_test_city_exists(api_base: str, admin_headers: dict, name: str) -> int | None:
    """Убедиться что тестовый город существует (создать если нет), вернуть его id"""
    existing_id = _get_city_id_by_name(api_base, admin_headers, name)
    if existing_id:
        # Город может быть удалён — попробуем пересоздать (роутер восстанавливает удалённые)
        resp = api_post(api_base, "/api/cities", admin_headers, json={"name": name})
        if resp.status_code in (200, 201):
            return resp.json().get("id")
        # Уже активен — вернуть существующий id
        return existing_id

    resp = api_post(api_base, "/api/cities", admin_headers, json={"name": name})
    if resp.status_code in (200, 201):
        return resp.json().get("id")
    return None


def _cleanup_test_city(api_base: str, admin_headers: dict, name: str) -> None:
    """Удалить тестовый город по имени (soft delete)"""
    city_id = _get_city_id_by_name(api_base, admin_headers, name)
    if city_id:
        try:
            _http_session.delete(
                f"{api_base}/api/cities/{city_id}",
                headers=admin_headers,
                timeout=REQUEST_TIMEOUT,
            )
        except Exception:
            pass
