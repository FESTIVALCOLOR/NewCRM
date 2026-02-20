# -*- coding: utf-8 -*-
"""
E2E Tests: CRUD договоров
8 тестов — создание, чтение, обновление, удаление договоров + файловые поля.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_put, api_patch, api_delete


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
