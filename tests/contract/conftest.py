# -*- coding: utf-8 -*-
"""
Contract Test Fixtures: общие фикстуры для проверки совместимости API ↔ клиент.

Эти фикстуры определяют «контракты» — минимальные наборы ключей,
которые сервер ОБЯЗАН возвращать, а клиент (api_client) ОБЯЗАН принимать.
Если сервер убирает ключ — тест падает ДО того как клиент сломается.
"""

import pytest
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import API_BASE_URL


# ============================================================
# AUTO-SKIP: пропуск contract тестов если сервер недоступен
# ============================================================

def _check_server():
    try:
        resp = requests.get(f"{API_BASE_URL}/health", timeout=3, verify=False)
        return resp.status_code == 200
    except Exception:
        return False

_server_available = _check_server()


def pytest_collection_modifyitems(config, items):
    """Пропустить contract тесты если сервер недоступен."""
    if _server_available:
        return
    skip_marker = pytest.mark.skip(reason="API сервер недоступен — contract тесты пропущены")
    for item in items:
        if "contract" in str(item.fspath):
            item.add_marker(skip_marker)


# ============================================================
# СЕРВЕРНЫЕ ФИКСТУРЫ
# ============================================================

@pytest.fixture(scope="session")
def api_base():
    """Базовый URL API сервера."""
    return API_BASE_URL


@pytest.fixture(scope="session")
def admin_token(api_base):
    """Авторизация admin -> Bearer token."""
    _session = requests.Session()
    _session.verify = False
    response = _session.post(
        f"{api_base}/api/auth/login",
        data={"username": "admin", "password": "admin123"},
        timeout=15
    )
    assert response.status_code == 200, (
        f"Не удалось авторизоваться: {response.status_code} {response.text}"
    )
    data = response.json()
    assert "access_token" in data
    _session.close()
    return data["access_token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    """HTTP headers с Bearer token администратора."""
    return {"Authorization": f"Bearer {admin_token}"}


# ============================================================
# КОНТРАКТЫ: наборы обязательных ключей для каждой сущности
# ============================================================

@pytest.fixture
def client_contract_keys():
    """Обязательные ключи ответа GET /api/clients"""
    return {
        "required": {"id", "client_type", "phone", "created_at", "updated_at"},
        "optional": {
            "full_name", "email", "passport_series", "passport_number",
            "passport_issued_by", "passport_issued_date", "registration_address",
            "organization_type", "organization_name", "inn", "ogrn",
            "account_details", "responsible_person",
        },
    }


@pytest.fixture
def employee_contract_keys():
    """Обязательные ключи ответа GET /api/employees"""
    return {
        "required": {"id", "full_name", "position", "status", "is_online", "created_at"},
        "optional": {
            "phone", "email", "address", "birth_date", "department",
            "role", "secondary_position", "login", "last_login", "agent_color",
        },
    }


@pytest.fixture
def contract_contract_keys():
    """Обязательные ключи ответа GET /api/contracts"""
    return {
        "required": {
            "id", "client_id", "project_type", "contract_number",
            "created_at", "updated_at",
        },
        "optional": {
            "project_subtype", "floors", "agent_type", "city",
            "contract_date", "address", "area", "total_amount",
            "advance_payment", "additional_payment", "third_payment",
            "contract_period", "status", "termination_reason",
            "client_name", "client_phone",
        },
    }


@pytest.fixture
def payment_contract_keys():
    """Обязательные ключи ответа GET /api/payments"""
    return {
        "required": {
            "id", "contract_id", "employee_id", "role",
            "final_amount", "is_paid", "created_at", "updated_at",
        },
        "optional": {
            "crm_card_id", "supervision_card_id", "stage_name",
            "calculated_amount", "manual_amount", "is_manual",
            "payment_type", "report_month", "payment_status",
            "reassigned", "old_employee_id", "employee_name",
            "paid_date", "paid_by",
        },
    }


@pytest.fixture
def agent_contract_keys():
    """Обязательные ключи ответа GET /api/agents"""
    return {
        "required": {"id", "name"},
        "optional": {"full_name", "color", "status"},
    }


@pytest.fixture
def notification_contract_keys():
    """Обязательные ключи ответа GET /api/notifications"""
    return {
        "required": {"id", "notification_type", "message", "is_read", "created_at"},
        "optional": {
            "user_id", "entity_type", "entity_id", "action_url",
        },
    }


@pytest.fixture
def sync_stage_executor_contract_keys():
    """Обязательные ключи ответа GET /api/sync/stage-executors"""
    return {
        "required": {"id", "crm_card_id", "stage_name", "executor_id"},
        "optional": {
            "assigned_date", "assigned_by", "deadline",
            "completed", "completed_date", "submitted_date",
        },
    }


@pytest.fixture
def sync_approval_deadline_contract_keys():
    """Обязательные ключи ответа GET /api/sync/approval-deadlines"""
    return {
        "required": {"id", "crm_card_id", "stage_name"},
        "optional": {"deadline", "is_completed", "completed_date", "created_at"},
    }


@pytest.fixture
def sync_action_history_contract_keys():
    """Обязательные ключи ответа GET /api/sync/action-history"""
    return {
        "required": {"id", "action_type", "entity_type"},
        "optional": {
            "user_id", "entity_id", "description", "action_date",
        },
    }


# ============================================================
# ХЕЛПЕРЫ
# ============================================================

def assert_contract(item: dict, contract: dict, entity_name: str = "entity"):
    """Проверить что объект соответствует контракту.

    Args:
        item: объект из API-ответа
        contract: словарь {"required": set, "optional": set}
        entity_name: имя сущности для сообщений об ошибке
    """
    required = contract["required"]
    optional = contract.get("optional", set())
    all_known = required | optional

    # Все обязательные ключи должны присутствовать
    missing = required - item.keys()
    assert not missing, (
        f"{entity_name}: отсутствуют обязательные ключи: {missing}. "
        f"Фактические ключи: {sorted(item.keys())}"
    )

    # Предупреждение о неизвестных ключах (не падаем, но логируем)
    unknown = item.keys() - all_known
    # unknown ключи допустимы — сервер может добавлять новые поля
