# -*- coding: utf-8 -*-
"""
Contract Tests: Проверка совместимости API ↔ клиент.

Тесты проверяют что API-ответы содержат ВСЕ ключи которые клиент ожидает.
Если сервер уберёт обязательный ключ — тест упадёт ДО того как клиент сломается.

Запуск: pytest tests/contract/ -v --timeout=60
Требует: работающий сервер (как E2E тесты)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get, api_post, api_delete, TEST_PREFIX
from tests.contract.conftest import assert_contract


@pytest.mark.e2e
class TestClientContract:
    """Контракт: GET /api/clients → ClientResponse"""

    def test_clients_list_contract(self, api_base, admin_headers, client_contract_keys):
        """Каждый клиент в списке содержит обязательные ключи"""
        resp = api_get(api_base, "/api/clients", admin_headers, params={"limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:5]:
            assert_contract(item, client_contract_keys, "Client")

    def test_client_id_is_int(self, api_base, admin_headers):
        """id клиента — целое число"""
        resp = api_get(api_base, "/api/clients", admin_headers, params={"limit": 1})
        assert resp.status_code == 200
        data = resp.json()
        if data:
            assert isinstance(data[0]["id"], int), "Client.id должен быть int"


@pytest.mark.e2e
class TestEmployeeContract:
    """Контракт: GET /api/employees → EmployeeResponse"""

    def test_employees_list_contract(self, api_base, admin_headers, employee_contract_keys):
        """Каждый сотрудник содержит обязательные ключи"""
        resp = api_get(api_base, "/api/employees", admin_headers, params={"limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:5]:
            assert_contract(item, employee_contract_keys, "Employee")

    def test_employee_is_online_is_bool(self, api_base, admin_headers):
        """is_online — булево значение"""
        resp = api_get(api_base, "/api/employees", admin_headers, params={"limit": 1})
        assert resp.status_code == 200
        data = resp.json()
        if data:
            assert isinstance(data[0]["is_online"], bool), "Employee.is_online должен быть bool"


@pytest.mark.e2e
class TestContractContract:
    """Контракт: GET /api/contracts → ContractResponse"""

    def test_contracts_list_contract(self, api_base, admin_headers, contract_contract_keys):
        """Каждый договор содержит обязательные ключи"""
        resp = api_get(api_base, "/api/contracts", admin_headers, params={"limit": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:5]:
            assert_contract(item, contract_contract_keys, "Contract")

    def test_contract_client_id_is_int(self, api_base, admin_headers):
        """client_id договора — целое число"""
        resp = api_get(api_base, "/api/contracts", admin_headers, params={"limit": 1})
        assert resp.status_code == 200
        data = resp.json()
        if data:
            assert isinstance(data[0]["client_id"], int), "Contract.client_id должен быть int"


@pytest.mark.e2e
class TestPaymentContract:
    """Контракт: GET /api/payments → PaymentResponse"""

    def test_payments_list_contract(self, api_base, admin_headers, payment_contract_keys):
        """Каждый платёж содержит обязательные ключи"""
        resp = api_get(api_base, "/api/payments", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:5]:
            assert_contract(item, payment_contract_keys, "Payment")

    def test_payment_is_paid_is_bool(self, api_base, admin_headers):
        """is_paid — булево значение"""
        resp = api_get(api_base, "/api/payments", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        if data:
            assert isinstance(data[0]["is_paid"], bool), "Payment.is_paid должен быть bool"


@pytest.mark.e2e
class TestAgentContract:
    """Контракт: GET /api/agents → AgentResponse"""

    def test_agents_list_contract(self, api_base, admin_headers, agent_contract_keys):
        """Каждый агент содержит обязательные ключи"""
        resp = api_get(api_base, "/api/agents", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:5]:
            assert_contract(item, agent_contract_keys, "Agent")


@pytest.mark.e2e
class TestNotificationContract:
    """Контракт: GET /api/notifications → NotificationResponse"""

    def test_notifications_list_contract(self, api_base, admin_headers, notification_contract_keys):
        """Каждое уведомление содержит обязательные ключи"""
        resp = api_get(api_base, "/api/notifications", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            for item in data[:5]:
                assert_contract(item, notification_contract_keys, "Notification")


@pytest.mark.e2e
class TestSyncContract:
    """Контракт: GET /api/sync/* → Sync*Response"""

    def test_stage_executors_contract(self, api_base, admin_headers, sync_stage_executor_contract_keys):
        """Sync stage-executors: обязательные ключи"""
        resp = api_get(api_base, "/api/sync/stage-executors", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:5]:
            assert_contract(item, sync_stage_executor_contract_keys, "StageExecutor")

    def test_approval_deadlines_contract(self, api_base, admin_headers, sync_approval_deadline_contract_keys):
        """Sync approval-deadlines: обязательные ключи"""
        resp = api_get(api_base, "/api/sync/approval-deadlines", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:5]:
            assert_contract(item, sync_approval_deadline_contract_keys, "ApprovalDeadline")

    def test_action_history_contract(self, api_base, admin_headers, sync_action_history_contract_keys):
        """Sync action-history: обязательные ключи"""
        resp = api_get(api_base, "/api/sync/action-history", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:5]:
            assert_contract(item, sync_action_history_contract_keys, "ActionHistory")

    def test_supervision_history_contract(self, api_base, admin_headers):
        """Sync supervision-history: обязательные ключи"""
        contract = {
            "required": {"id", "supervision_card_id", "entry_type"},
            "optional": {"message", "created_by", "created_at"},
        }
        resp = api_get(api_base, "/api/sync/supervision-history", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:5]:
            assert_contract(item, contract, "SupervisionHistory")


@pytest.mark.e2e
class TestDashboardContract:
    """Контракт: GET /api/dashboard/crm → DashboardResponse"""

    def test_dashboard_individual_contract(self, api_base, admin_headers):
        """Dashboard Individual содержит все обязательные ключи"""
        resp = api_get(
            api_base, "/api/dashboard/crm", admin_headers,
            params={"project_type": "Индивидуальный"}
        )
        assert resp.status_code == 200
        data = resp.json()
        required = {"total_orders", "active_orders", "archive_orders"}
        missing = required - data.keys()
        assert not missing, f"Dashboard: отсутствуют ключи: {missing}"

    def test_dashboard_values_are_ints(self, api_base, admin_headers):
        """Значения dashboard — целые числа >= 0"""
        resp = api_get(
            api_base, "/api/dashboard/crm", admin_headers,
            params={"project_type": "Индивидуальный"}
        )
        assert resp.status_code == 200
        data = resp.json()
        for key in ("total_orders", "active_orders", "archive_orders"):
            assert isinstance(data[key], int), f"Dashboard.{key} должен быть int"
            assert data[key] >= 0, f"Dashboard.{key} не может быть отрицательным"


@pytest.mark.e2e
class TestStatisticsContract:
    """Контракт: GET /api/statistics/* → Statistics*Response"""

    def test_agent_types_contract(self, api_base, admin_headers):
        """GET /api/statistics/agent-types возвращает список строк"""
        resp = api_get(api_base, "/api/statistics/agent-types", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert isinstance(data[0], str), "agent_type должен быть строкой"

    def test_cities_contract(self, api_base, admin_headers):
        """GET /api/statistics/cities возвращает список строк"""
        resp = api_get(api_base, "/api/statistics/cities", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert isinstance(data[0], str), "city должна быть строкой"
