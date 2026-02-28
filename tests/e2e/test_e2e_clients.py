# -*- coding: utf-8 -*-
"""
E2E Tests: CRUD клиентов
12 тестов — создание, чтение, обновление, удаление, поиск, пагинация, X-Total-Count.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_put, api_delete


@pytest.mark.e2e
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

    def test_create_client_all_fields(self, api_base, admin_headers, module_factory):
        """Создание клиента с полными данными — проверка всех ключей ответа"""
        client = module_factory.create_client(
            full_name=f"{TEST_PREFIX}Полные Данные",
            client_type="Физическое лицо",
            phone="+79991000777",
            email="full_data@test.com",
            passport_series="4520",
            passport_number="123456",
            passport_issued_by="УМВД России",
            passport_issued_date="2015-01-01",
            registration_address="г. Санкт-Петербург, ул. Ленина, д. 1",
        )
        assert client["id"] > 0
        # Проверяем все обязательные ключи ответа
        for key in ("id", "client_type", "full_name", "phone", "email",
                    "created_at", "updated_at"):
            assert key in client, f"Ожидается ключ '{key}' в ответе"
        assert client["full_name"] == f"{TEST_PREFIX}Полные Данные"
        assert client["email"] == "full_data@test.com"
        assert client["passport_series"] == "4520"
        assert client["registration_address"] == "г. Санкт-Петербург, ул. Ленина, д. 1"

    def test_create_legal_entity_client(self, api_base, admin_headers, module_factory):
        """Создание клиента — юридическое лицо"""
        client = module_factory.create_client(
            client_type="Юридическое лицо",
            full_name=f"{TEST_PREFIX}ООО Тест",
            phone="+79991000888",
            organization_name="ООО Тест Компания",
            inn="7701234567",
            ogrn="1027700132195",
            responsible_person=f"{TEST_PREFIX}Директор Иванов",
        )
        assert client["id"] > 0
        assert client["client_type"] == "Юридическое лицо"
        assert client["organization_name"] == "ООО Тест Компания"
        assert client["inn"] == "7701234567"
        assert client["ogrn"] == "1027700132195"
        assert client["responsible_person"] == f"{TEST_PREFIX}Директор Иванов"

    def test_update_client_verifies_persisted(self, api_base, admin_headers, module_factory):
        """Обновление клиента — проверка сохранения изменений через повторный GET"""
        client = module_factory.create_client(
            full_name=f"{TEST_PREFIX}Клиент До PUT",
            phone="+79991001111",
        )
        new_phone = "+79991002222"
        new_email = "updated@test.com"
        resp = api_put(api_base, f"/api/clients/{client['id']}", admin_headers, json={
            "full_name": f"{TEST_PREFIX}Клиент После PUT",
            "phone": new_phone,
            "email": new_email,
        })
        assert resp.status_code == 200
        # Повторно получаем и проверяем что данные сохранились
        resp2 = api_get(api_base, f"/api/clients/{client['id']}", admin_headers)
        assert resp2.status_code == 200
        refreshed = resp2.json()
        assert refreshed["full_name"] == f"{TEST_PREFIX}Клиент После PUT"
        assert refreshed["phone"] == new_phone
        assert refreshed["email"] == new_email

    def test_search_client_by_name(self, api_base, admin_headers, module_factory):
        """Поиск клиента по имени через query-параметр search"""
        unique_name = f"{TEST_PREFIX}УникальноеИмя999"
        client = module_factory.create_client(full_name=unique_name, phone="+79991009999")
        resp = api_get(api_base, "/api/clients", admin_headers,
                       params={"search": unique_name, "search_type": "name"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        found_ids = [c["id"] for c in data]
        assert client["id"] in found_ids, "Созданный клиент не найден в результатах поиска"

    def test_search_client_by_phone(self, api_base, admin_headers, module_factory):
        """Поиск клиента по телефону"""
        unique_phone = "+79991007878"
        client = module_factory.create_client(
            full_name=f"{TEST_PREFIX}Клиент Поиск Телефон",
            phone=unique_phone,
        )
        resp = api_get(api_base, "/api/clients", admin_headers,
                       params={"search": unique_phone, "search_type": "phone"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        found_ids = [c["id"] for c in data]
        assert client["id"] in found_ids, "Клиент не найден по телефону"

    def test_clients_pagination(self, api_base, admin_headers, module_factory):
        """Пагинация: skip/limit ограничивает количество записей"""
        # Создаём несколько клиентов для гарантии непустого набора
        for i in range(3):
            module_factory.create_client()
        # Запрашиваем максимум 2 записи
        resp = api_get(api_base, "/api/clients", admin_headers,
                       params={"skip": 0, "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) <= 2, "Список клиентов превышает limit=2"

    def test_clients_x_total_count_header(self, api_base, admin_headers, module_factory):
        """Ответ содержит заголовок X-Total-Count с числом записей"""
        module_factory.create_client()
        resp = api_get(api_base, "/api/clients", admin_headers)
        assert resp.status_code == 200
        assert "x-total-count" in resp.headers or "X-Total-Count" in resp.headers, \
            "Ожидается заголовок X-Total-Count"
        header_val = resp.headers.get("x-total-count") or resp.headers.get("X-Total-Count")
        assert int(header_val) >= 1, "X-Total-Count должен быть не менее 1"

    def test_delete_client_not_in_list(self, api_base, admin_headers):
        """Удалённый клиент не возвращается в списке"""
        resp = api_post(api_base, "/api/clients", admin_headers, json={
            "client_type": "Физическое лицо",
            "full_name": f"{TEST_PREFIX}Удаляемый Для Проверки",
            "phone": "+79991000055",
        })
        assert resp.status_code == 200
        client_id = resp.json()["id"]

        # Удаляем
        del_resp = api_delete(api_base, f"/api/clients/{client_id}", admin_headers)
        assert del_resp.status_code == 200

        # Проверяем что отсутствует в общем списке
        list_resp = api_get(api_base, "/api/clients", admin_headers)
        assert list_resp.status_code == 200
        ids_in_list = [c["id"] for c in list_resp.json()]
        assert client_id not in ids_in_list, "Удалённый клиент присутствует в списке"

    def test_clients_require_auth(self, api_base):
        """GET /api/clients без токена — 401"""
        resp = api_get(api_base, "/api/clients", {})
        assert resp.status_code in (401, 403)
