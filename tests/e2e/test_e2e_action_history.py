# -*- coding: utf-8 -*-
"""
E2E Tests: История действий (Action History)
8 тестов — CRUD записей истории и автоматическое создание записей при операциях.
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


# Примечание: автоматическое логирование действий (при создании клиентов,
# перемещении карточек и т.д.) выполняется на стороне клиентского UI,
# а не на сервере. Поэтому тесты автоматического создания записей
# при API-операциях здесь не включены.
