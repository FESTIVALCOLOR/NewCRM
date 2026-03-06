# -*- coding: utf-8 -*-
"""
Contract Tests: Проверка POST/PUT/PATCH/DELETE ответов API.

Расширение contract-тестов на запись. Проверяем что ответы мутирующих операций
содержат ожидаемые ключи и правильные типы данных.

Запуск: pytest tests/contract/test_api_write_contracts.py -v --timeout=60
Требует: работающий сервер
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import (
    api_get, api_post, api_patch, api_put, api_delete, TEST_PREFIX,
)
from tests.contract.conftest import assert_contract


# ════════════════════════════════════════════════════════════
# CRM Cards Contract (отсутствовали в оригинальных тестах)
# ════════════════════════════════════════════════════════════

CRM_CARD_CONTRACT = {
    "required": {"id", "contract_id", "column_name"},
    "optional": {
        "project_type", "client_name", "address", "city", "area",
        "agent_name", "agent_type", "survey_date", "tech_task_date",
        "yandex_folder_path", "status", "order_position",
        "contract_number", "contract_type", "contract_subtype",
        "created_at", "updated_at",
    },
}

SUPERVISION_CARD_CONTRACT = {
    "required": {"id", "contract_id", "column_name"},
    "optional": {
        "address", "city", "area", "stage_name", "status",
        "client_name", "contract_number", "agent_name", "agent_type",
        "pause_start", "pause_end", "pause_reason",
        "created_at", "updated_at",
    },
}


@pytest.mark.e2e
class TestCrmCardReadContract:
    """Контракт: GET /api/crm/cards — ключи которые UI ожидает."""

    def test_crm_cards_list_contract(self, api_base, admin_headers):
        """Каждая CRM карточка содержит обязательные ключи."""
        resp = api_get(api_base, "/api/crm/cards", admin_headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:5]:
            assert_contract(item, CRM_CARD_CONTRACT, "CRMCard")

    def test_crm_cards_archived_contract(self, api_base, admin_headers):
        """Архивные CRM карточки содержат те же обязательные ключи."""
        resp = api_get(api_base, "/api/crm/cards", admin_headers,
                       params={"archived": True, "project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:5]:
            assert_contract(item, CRM_CARD_CONTRACT, "CRMCard(archived)")

    def test_crm_card_id_is_int(self, api_base, admin_headers):
        """id CRM карточки — целое число."""
        resp = api_get(api_base, "/api/crm/cards", admin_headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        if data:
            assert isinstance(data[0]["id"], int), "CRMCard.id должен быть int"
            assert isinstance(data[0]["contract_id"], int), "CRMCard.contract_id должен быть int"


@pytest.mark.e2e
class TestSupervisionCardReadContract:
    """Контракт: GET /api/supervision/cards — ключи которые UI ожидает."""

    def test_supervision_cards_list_contract(self, api_base, admin_headers):
        """Каждая карточка надзора содержит обязательные ключи."""
        resp = api_get(api_base, "/api/supervision/cards", admin_headers,
                       params={"status": "active"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:5]:
            assert_contract(item, SUPERVISION_CARD_CONTRACT, "SupervisionCard")

    def test_supervision_cards_archived_contract(self, api_base, admin_headers):
        """Архивные карточки надзора содержат те же ключи."""
        resp = api_get(api_base, "/api/supervision/cards", admin_headers,
                       params={"status": "archived"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:5]:
            assert_contract(item, SUPERVISION_CARD_CONTRACT, "SupervisionCard(archived)")


# ════════════════════════════════════════════════════════════
# Write Operations: POST/PUT/PATCH ответы
# ════════════════════════════════════════════════════════════

@pytest.mark.e2e
class TestClientWriteContract:
    """Контракт: POST/PUT /api/clients — ответ содержит созданный объект."""

    def test_create_client_returns_object(self, api_base, admin_headers, client_contract_keys):
        """POST /api/clients возвращает объект с обязательными ключами."""
        data = {
            "client_type": "Физическое лицо",
            "full_name": f"{TEST_PREFIX}ContractTest",
            "phone": "+79991234567",
        }
        resp = api_post(api_base, "/api/clients", admin_headers, json=data)
        assert resp.status_code == 200
        client = resp.json()
        assert_contract(client, client_contract_keys, "Client(created)")
        # Cleanup
        api_delete(api_base, f"/api/clients/{client['id']}", admin_headers)

    def test_update_client_returns_object(self, api_base, admin_headers, client_contract_keys):
        """PUT /api/clients/{id} возвращает обновлённый объект."""
        # Create
        data = {
            "client_type": "Физическое лицо",
            "full_name": f"{TEST_PREFIX}ContractTestUpd",
            "phone": "+79991234568",
        }
        resp = api_post(api_base, "/api/clients", admin_headers, json=data)
        assert resp.status_code == 200
        client_id = resp.json()["id"]
        # Update
        resp = api_put(api_base, f"/api/clients/{client_id}", admin_headers,
                       json={"full_name": f"{TEST_PREFIX}Updated"})
        assert resp.status_code == 200
        updated = resp.json()
        assert_contract(updated, client_contract_keys, "Client(updated)")
        assert updated["full_name"] == f"{TEST_PREFIX}Updated"
        # Cleanup
        api_delete(api_base, f"/api/clients/{client_id}", admin_headers)


@pytest.mark.e2e
class TestContractWriteContract:
    """Контракт: POST /api/contracts — ответ содержит созданный договор."""

    def test_create_contract_returns_object(self, api_base, admin_headers,
                                            contract_contract_keys, factory):
        """POST /api/contracts возвращает объект с обязательными ключами."""
        client = factory.create_client()
        contract = factory.create_contract(client["id"])
        assert_contract(contract, contract_contract_keys, "Contract(created)")


@pytest.mark.e2e
class TestEmployeeWriteContract:
    """Контракт: POST /api/employees — ответ содержит созданного сотрудника."""

    def test_create_employee_returns_object(self, api_base, admin_headers, employee_contract_keys):
        """POST /api/employees возвращает объект с обязательными ключами."""
        data = {
            "full_name": f"{TEST_PREFIX}EmpContract",
            "login": f"{TEST_PREFIX}emp_contract",
            "password": "test123456",
            "position": "Дизайнер",
            "department": "Проектный",
            "phone": "+79997654321",
            "status": "активный",
        }
        resp = api_post(api_base, "/api/employees", admin_headers, json=data)
        assert resp.status_code in (200, 201)
        emp = resp.json()
        assert_contract(emp, employee_contract_keys, "Employee(created)")
        # Cleanup
        api_delete(api_base, f"/api/employees/{emp['id']}", admin_headers)


# ════════════════════════════════════════════════════════════
# Error Responses: проверка что ошибки возвращают понятную структуру
# ════════════════════════════════════════════════════════════

@pytest.mark.e2e
class TestErrorResponseContract:
    """Контракт: ошибки API возвращают JSON с ключом 'detail'."""

    def test_404_returns_json(self, api_base, admin_headers):
        """GET на несуществующий ресурс возвращает 404 с detail."""
        resp = api_get(api_base, "/api/clients/999999", admin_headers)
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data, "404 ответ должен содержать ключ 'detail'"

    def test_401_without_token(self, api_base):
        """Запрос без токена возвращает 401/403."""
        resp = api_get(api_base, "/api/clients", {})
        assert resp.status_code in (401, 403)

    def test_400_invalid_data(self, api_base, admin_headers):
        """POST с невалидными данными возвращает 400/422."""
        resp = api_post(api_base, "/api/clients", admin_headers, json={})
        assert resp.status_code in (400, 422)

    def test_duplicate_login_returns_400(self, api_base, admin_headers):
        """POST /api/employees с занятым логином возвращает 400."""
        # admin уже существует
        data = {
            "full_name": f"{TEST_PREFIX}DuplicateLogin",
            "login": "admin",
            "password": "test123456",
            "position": "Дизайнер",
            "department": "Проектный",
            "phone": "+79990000099",
            "status": "активный",
        }
        resp = api_post(api_base, "/api/employees", admin_headers, json=data)
        assert resp.status_code == 400


# ════════════════════════════════════════════════════════════
# Stage Executors Contract
# ════════════════════════════════════════════════════════════

STAGE_EXECUTOR_CONTRACT = {
    "required": {"id", "stage_name", "executor_id"},
    "optional": {
        "crm_card_id", "assigned_date", "assigned_by", "deadline",
        "completed", "completed_date", "submitted_date",
        "executor_name",
    },
}


@pytest.mark.e2e
class TestStageExecutorReadContract:
    """Контракт: stage_executors вложены в ответ GET /api/crm/cards/{id}."""

    def test_stage_executors_per_card(self, api_base, admin_headers):
        """Stage executors внутри карточки содержат обязательные ключи."""
        # Найдём любую CRM карточку с исполнителями
        cards_resp = api_get(api_base, "/api/crm/cards", admin_headers,
                             params={"project_type": "Индивидуальный"})
        if cards_resp.status_code != 200:
            pytest.skip("Нет CRM карточек для теста")
        cards = cards_resp.json()
        if not cards:
            pytest.skip("Нет CRM карточек для теста")

        # Stage executors вложены в ответ карточки
        checked = 0
        for card in cards[:5]:
            resp = api_get(api_base, f"/api/crm/cards/{card['id']}", admin_headers)
            if resp.status_code != 200:
                continue
            card_data = resp.json()
            executors = card_data.get("stage_executors", [])
            for ex in executors[:3]:
                assert_contract(ex, STAGE_EXECUTOR_CONTRACT, "StageExecutor")
                checked += 1
        if checked == 0:
            pytest.skip("Нет исполнителей для проверки контракта")
