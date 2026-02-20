# -*- coding: utf-8 -*-
"""
E2E Tests: CRUD клиентов
5 тестов — создание, чтение, обновление, удаление клиентов.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_put, api_delete


class TestClientsCRUD:
    """CRUD операции с клиентами через API"""

    @pytest.mark.critical
    def test_create_client(self, api_base, admin_headers, module_factory):
        """Создание клиента"""
        client = module_factory.create_client(
            full_name=f"{TEST_PREFIX}Клиент Создание",
            client_type="Физическое лицо",
            phone="+79991000001",
        )
        assert client["id"] > 0
        assert client["full_name"] == f"{TEST_PREFIX}Клиент Создание"
        assert client["client_type"] == "Физическое лицо"

    def test_get_client_by_id(self, api_base, admin_headers, module_factory):
        """Получение клиента по ID"""
        client = module_factory.create_client()
        resp = api_get(api_base, f"/api/clients/{client['id']}", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == client["id"]
        assert data["phone"] == client["phone"]

    def test_update_client(self, api_base, admin_headers, module_factory):
        """Обновление клиента"""
        client = module_factory.create_client(full_name=f"{TEST_PREFIX}До Обновления")
        resp = api_put(api_base, f"/api/clients/{client['id']}", admin_headers, json={
            "full_name": f"{TEST_PREFIX}После Обновления",
        })
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["full_name"] == f"{TEST_PREFIX}После Обновления"

    def test_delete_client(self, api_base, admin_headers):
        """Удаление клиента"""
        # Создаём напрямую (не через фабрику) чтобы сами удалили
        resp = api_post(api_base, "/api/clients", admin_headers, json={
            "client_type": "Физическое лицо",
            "full_name": f"{TEST_PREFIX}Удаляемый Клиент",
            "phone": "+79991000099",
        })
        assert resp.status_code == 200
        client_id = resp.json()["id"]

        # Удаляем
        resp = api_delete(api_base, f"/api/clients/{client_id}", admin_headers)
        assert resp.status_code == 200

        # Проверяем что удалён
        resp = api_get(api_base, f"/api/clients/{client_id}", admin_headers)
        assert resp.status_code == 404

    def test_get_all_clients(self, api_base, admin_headers, module_factory):
        """Получение списка всех клиентов"""
        module_factory.create_client()
        resp = api_get(api_base, "/api/clients", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
