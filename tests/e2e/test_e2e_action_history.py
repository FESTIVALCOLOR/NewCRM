# -*- coding: utf-8 -*-
"""
E2E Tests: История действий (Action History)
12 тестов — CRUD записей истории, ключи ответа, фильтрация, пагинация, авторизация.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import API_BASE_URL
from tests.e2e.conftest import TEST_PREFIX, REQUEST_TIMEOUT, api_get, api_post


# ==============================================================
# CRUD ИСТОРИИ ДЕЙСТВИЙ
# ==============================================================

@pytest.mark.e2e
class TestActionHistoryCRUD:
    """CRUD операции с историей действий"""

    @pytest.mark.critical
    def test_create_action_history_entry(self, api_base, admin_headers):
        """Создание записи в истории действий"""
        resp = api_post(api_base, "/api/action-history", admin_headers, json={
            "action_type": "test_create",
            "entity_type": "contract",
            "entity_id": 1,
            "description": f"{TEST_PREFIX} create action history entry",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0
        assert data["action_type"] == "test_create"
        assert data["entity_type"] == "contract"
        assert data["entity_id"] == 1
        assert data["description"] == f"{TEST_PREFIX} create action history entry"
        assert "user_id" in data
        assert "action_date" in data

    def test_get_history_by_entity(self, api_base, admin_headers):
        """Получение истории по entity_type и entity_id"""
        # Создаём запись с уникальным entity_id
        resp_create = api_post(api_base, "/api/action-history", admin_headers, json={
            "action_type": "test_entity_lookup",
            "entity_type": "contract",
            "entity_id": 999999,
            "description": f"{TEST_PREFIX} entity lookup test",
        })
        assert resp_create.status_code == 200

        # Получаем историю для этой сущности
        resp = api_get(api_base, "/api/action-history/contract/999999", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Проверяем что запись содержит нужные поля
        entry = data[0]
        assert entry["entity_type"] == "contract"
        assert entry["entity_id"] == 999999
        assert "user_name" in entry
        assert "action_date" in entry

    def test_get_all_history(self, api_base, admin_headers):
        """Получение всей истории действий"""
        # Создаём запись чтобы гарантировать непустой результат
        api_post(api_base, "/api/action-history", admin_headers, json={
            "action_type": "test_list_all",
            "entity_type": "contract",
            "entity_id": 1,
            "description": f"{TEST_PREFIX} list all test",
        })

        resp = api_get(api_base, "/api/action-history", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_filter_by_entity_type(self, api_base, admin_headers):
        """Фильтрация истории по entity_type"""
        # Создаём записи с разными entity_type
        api_post(api_base, "/api/action-history", admin_headers, json={
            "action_type": "test_filter",
            "entity_type": "client",
            "entity_id": 888888,
            "description": f"{TEST_PREFIX} filter by entity_type",
        })

        resp = api_get(api_base, "/api/action-history", admin_headers,
                       params={"entity_type": "client"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Все записи должны быть для client
        for entry in data:
            assert entry["entity_type"] == "client"

    def test_filter_by_user_id(self, api_base, admin_headers):
        """Фильтрация истории по user_id"""
        # Создаём запись (будет привязана к admin user)
        resp_create = api_post(api_base, "/api/action-history", admin_headers, json={
            "action_type": "test_filter_user",
            "entity_type": "contract",
            "entity_id": 777777,
            "description": f"{TEST_PREFIX} filter by user_id",
        })
        assert resp_create.status_code == 200
        admin_user_id = resp_create.json()["user_id"]

        resp = api_get(api_base, "/api/action-history", admin_headers,
                       params={"user_id": admin_user_id})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Все записи должны быть от этого пользователя
        for entry in data:
            assert entry["user_id"] == admin_user_id


    def test_action_history_response_keys(self, api_base, admin_headers):
        """Проверка обязательных ключей в записи истории при создании"""
        resp = api_post(api_base, "/api/action-history", admin_headers, json={
            "action_type": "test_keys_check",
            "entity_type": "contract",
            "entity_id": 555555,
            "description": f"{TEST_PREFIX} response keys check",
        })
        assert resp.status_code == 200
        data = resp.json()
        # Все обязательные ключи должны присутствовать
        for key in ("id", "action_type", "entity_type", "entity_id", "description",
                    "action_date", "user_id"):
            assert key in data, f"Ожидается ключ '{key}' в ответе action-history"
        assert data["id"] > 0
        assert data["action_type"] == "test_keys_check"
        assert data["entity_id"] == 555555

    def test_action_history_entity_response_keys(self, api_base, admin_headers):
        """Проверка ключей у записей при GET по entity_type/entity_id"""
        entity_id = 444444
        api_post(api_base, "/api/action-history", admin_headers, json={
            "action_type": "test_entity_keys",
            "entity_type": "client",
            "entity_id": entity_id,
            "description": f"{TEST_PREFIX} entity keys check",
        })
        resp = api_get(api_base, f"/api/action-history/client/{entity_id}", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Записи по entity endpoint возвращают расширенный набор ключей включая user_name
        entry = data[0]
        for key in ("id", "action_type", "entity_type", "entity_id",
                    "description", "action_date", "user_id", "user_name"):
            assert key in entry, f"Ожидается ключ '{key}' в записи истории по сущности"
        assert entry["entity_type"] == "client"
        assert entry["entity_id"] == entity_id

    def test_action_history_pagination(self, api_base, admin_headers):
        """Пагинация: skip/limit ограничивает количество записей"""
        # Создаём несколько записей
        for i in range(3):
            api_post(api_base, "/api/action-history", admin_headers, json={
                "action_type": f"test_page_{i}",
                "entity_type": "contract",
                "entity_id": 1,
                "description": f"{TEST_PREFIX} pagination test {i}",
            })
        # Запрашиваем максимум 2 записи
        resp = api_get(api_base, "/api/action-history", admin_headers,
                       params={"skip": 0, "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) <= 2, "Список превышает limit=2"

    def test_action_history_multiple_entity_types(self, api_base, admin_headers):
        """Разные типы сущностей можно сохранять в историю"""
        entity_types = ["client", "contract", "crm_card", "employee", "payment"]
        created_ids = []
        for etype in entity_types:
            resp = api_post(api_base, "/api/action-history", admin_headers, json={
                "action_type": f"test_{etype}_type",
                "entity_type": etype,
                "entity_id": 123,
                "description": f"{TEST_PREFIX} type test for {etype}",
            })
            assert resp.status_code == 200, \
                f"Ошибка создания записи с entity_type='{etype}': {resp.status_code}"
            created_ids.append(resp.json()["id"])
        # Все записи успешно созданы
        assert len(created_ids) == len(entity_types)

    def test_action_history_without_auth(self, api_base):
        """GET /api/action-history без токена — 401"""
        resp = api_get(api_base, "/api/action-history", {})
        assert resp.status_code in (401, 403), \
            f"Ожидается 401/403 без авторизации, получено {resp.status_code}"

    def test_action_history_post_without_auth(self, api_base):
        """POST /api/action-history без токена — 401"""
        resp = api_post(api_base, "/api/action-history", {}, json={
            "action_type": "test_no_auth",
            "entity_type": "contract",
            "entity_id": 1,
            "description": "без авторизации",
        })
        assert resp.status_code in (401, 403), \
            f"Ожидается 401/403 без авторизации, получено {resp.status_code}"

    def test_filter_entity_type_excludes_other_types(self, api_base, admin_headers):
        """Фильтрация по entity_type не возвращает записи других типов"""
        # Создаём записи разных типов
        api_post(api_base, "/api/action-history", admin_headers, json={
            "action_type": "test_exclude_mix",
            "entity_type": "payment",
            "entity_id": 333333,
            "description": f"{TEST_PREFIX} payment entry for exclusion test",
        })
        api_post(api_base, "/api/action-history", admin_headers, json={
            "action_type": "test_exclude_mix",
            "entity_type": "contract",
            "entity_id": 333333,
            "description": f"{TEST_PREFIX} contract entry for exclusion test",
        })
        # Фильтруем по payment — не должно быть contract
        resp = api_get(api_base, "/api/action-history", admin_headers,
                       params={"entity_type": "payment"})
        assert resp.status_code == 200
        data = resp.json()
        for entry in data:
            assert entry["entity_type"] == "payment", \
                f"При фильтре entity_type=payment встретилась запись с типом '{entry['entity_type']}'"


# Примечание: автоматическое логирование действий (при создании клиентов,
# перемещении карточек и т.д.) выполняется на стороне клиентского UI,
# а не на сервере. Поэтому тесты автоматического создания записей
# при API-операциях здесь не включены.
