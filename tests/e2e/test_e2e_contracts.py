# -*- coding: utf-8 -*-
"""
E2E Tests: CRUD договоров
16 тестов — создание, чтение, обновление, удаление, фильтрация, пагинация, ключи ответа.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_put, api_patch, api_delete


@pytest.mark.e2e
class TestContractsCRUD:
    """CRUD операции с договорами"""

    @pytest.mark.critical
    def test_create_individual_contract(self, api_base, admin_headers, module_factory):
        """Создание индивидуального договора"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(
            client["id"],
            project_type="Индивидуальный",
            agent_type="ФЕСТИВАЛЬ",
            city="СПБ",
        )
        assert contract["id"] > 0
        assert contract["project_type"] == "Индивидуальный"
        assert contract["agent_type"] == "ФЕСТИВАЛЬ"
        assert contract["city"] == "СПБ"

    def test_create_template_contract(self, api_base, admin_headers, module_factory):
        """Создание шаблонного договора"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(
            client["id"],
            project_type="Шаблонный",
            agent_type="ПЕТРОВИЧ",
            city="МСК",
        )
        assert contract["project_type"] == "Шаблонный"

    def test_get_contract_by_id(self, api_base, admin_headers, module_factory):
        """Получение договора по ID"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])
        resp = api_get(api_base, f"/api/contracts/{contract['id']}", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == contract["id"]
        assert data["contract_number"] == contract["contract_number"]

    def test_update_contract(self, api_base, admin_headers, module_factory):
        """Обновление договора"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])
        resp = api_put(api_base, f"/api/contracts/{contract['id']}", admin_headers, json={
            "status": "СДАН",
            "area": 120.5,
        })
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["status"] == "СДАН"
        assert updated["area"] == 120.5

    def test_delete_contract(self, api_base, admin_headers, module_factory):
        """Удаление договора"""
        client = module_factory.create_client()
        # Создаём вручную (не отслеживаем, удалим сами)
        resp = api_post(api_base, "/api/contracts", admin_headers, json={
            "client_id": client["id"],
            "project_type": "Индивидуальный",
            "contract_number": f"{TEST_PREFIX}DEL_001",
            "status": "Новый заказ",
        })
        assert resp.status_code == 200
        cid = resp.json()["id"]

        resp = api_delete(api_base, f"/api/contracts/{cid}", admin_headers)
        assert resp.status_code == 200

        resp = api_get(api_base, f"/api/contracts/{cid}", admin_headers)
        assert resp.status_code == 404

    def test_get_all_contracts(self, api_base, admin_headers, module_factory):
        """Получение списка всех договоров"""
        client = module_factory.create_client()
        module_factory.create_contract(client["id"])
        resp = api_get(api_base, "/api/contracts", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_update_contract_file_fields(self, api_base, admin_headers, module_factory):
        """Обновление файловых полей договора"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])
        resp = api_patch(
            api_base,
            f"/api/contracts/{contract['id']}/files",
            admin_headers,
            json={
                "tech_task_link": "https://disk.yandex.ru/test_link",
                "measurement_date": "2026-01-15",
            }
        )
        assert resp.status_code == 200

    def test_contract_with_all_cities(self, api_base, admin_headers, module_factory):
        """Создание договоров для каждого города"""
        client = module_factory.create_client()
        for city in ['СПБ', 'МСК', 'ВН']:
            contract = module_factory.create_contract(client["id"], city=city)
            assert contract["city"] == city

    def test_contract_response_keys(self, api_base, admin_headers, module_factory):
        """Проверка всех обязательных ключей ответа при создании договора"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])
        # Проверяем обязательные ключи
        for key in ("id", "client_id", "project_type", "contract_number",
                    "status", "created_at", "updated_at"):
            assert key in contract, f"Ожидается ключ '{key}' в ответе договора"
        assert contract["client_id"] == client["id"]
        assert contract["id"] > 0

    def test_get_contracts_response_keys_in_list(self, api_base, admin_headers, module_factory):
        """Проверка ключей договоров в списке (GET /)"""
        client = module_factory.create_client()
        module_factory.create_contract(client["id"])
        resp = api_get(api_base, "/api/contracts", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            for item in data[:5]:
                for key in ("id", "client_id", "project_type", "contract_number", "status"):
                    assert key in item, f"Ожидается ключ '{key}' в элементе списка договоров"

    def test_contracts_x_total_count_header(self, api_base, admin_headers, module_factory):
        """Ответ GET / содержит заголовок X-Total-Count"""
        client = module_factory.create_client()
        module_factory.create_contract(client["id"])
        resp = api_get(api_base, "/api/contracts", admin_headers)
        assert resp.status_code == 200
        header_val = resp.headers.get("x-total-count") or resp.headers.get("X-Total-Count")
        assert header_val is not None, "Ожидается заголовок X-Total-Count"
        assert int(header_val) >= 1

    def test_contracts_pagination(self, api_base, admin_headers, module_factory):
        """Пагинация skip/limit: результат не превышает limit"""
        client = module_factory.create_client()
        for i in range(3):
            module_factory.create_contract(client["id"])
        resp = api_get(api_base, "/api/contracts", admin_headers,
                       params={"skip": 0, "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) <= 2, "Список договоров превышает limit=2"

    def test_contracts_count_endpoint(self, api_base, admin_headers, module_factory):
        """GET /count возвращает число договоров"""
        resp = api_get(api_base, "/api/contracts/count", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data, "Ожидается ключ 'count' в ответе /contracts/count"
        assert isinstance(data["count"], int)
        assert data["count"] >= 0

    def test_contracts_count_by_project_type(self, api_base, admin_headers, module_factory):
        """GET /count с фильтром project_type возвращает корректное число"""
        client = module_factory.create_client()
        module_factory.create_contract(client["id"], project_type="Индивидуальный")
        resp = api_get(api_base, "/api/contracts/count", admin_headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert data["count"] >= 1, "Должен быть хотя бы 1 индивидуальный договор"

    def test_update_contract_verifies_persisted(self, api_base, admin_headers, module_factory):
        """Обновление договора — проверка сохранения через повторный GET"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])
        new_area = 250.0
        new_status = "В РАБОТЕ"
        resp = api_put(api_base, f"/api/contracts/{contract['id']}", admin_headers, json={
            "area": new_area,
            "status": new_status,
        })
        assert resp.status_code == 200
        # Повторно получаем — проверяем сохранение
        resp2 = api_get(api_base, f"/api/contracts/{contract['id']}", admin_headers)
        assert resp2.status_code == 200
        refreshed = resp2.json()
        assert refreshed["area"] == new_area
        assert refreshed["status"] == new_status

    def test_create_supervision_contract(self, api_base, admin_headers, module_factory):
        """Создание договора типа 'Авторский надзор' — CRM карточка не создаётся автоматически"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(
            client["id"],
            project_type="Авторский надзор",
            agent_type="ФЕСТИВАЛЬ",
        )
        assert contract["id"] > 0
        assert contract["project_type"] == "Авторский надзор"

    def test_contracts_require_auth(self, api_base):
        """GET /api/contracts без токена — 401"""
        resp = api_get(api_base, "/api/contracts", {})
        assert resp.status_code in (401, 403), \
            f"Ожидается 401/403 без авторизации, получено {resp.status_code}"
