# -*- coding: utf-8 -*-
"""
Fixtures для клиентских тестов (DataAccess, APIClient, PyQt5 виджеты)
"""
import os
import sys
import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from contextlib import contextmanager

import pytest

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def clear_data_cache():
    """Очистить кеш DataAccess между тестами для изоляции."""
    try:
        from utils.data_access import _global_cache
        _global_cache.invalidate()
        yield
        _global_cache.invalidate()
    except (ImportError, AttributeError):
        # PyQt5 недоступен в CI без графического окружения — пропускаем очистку кэша
        yield


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """Temporary SQLite database path"""
    return tmp_path / 'test_client.db'


@pytest.fixture
def mock_db():
    """Mock DatabaseManager with all CRUD methods"""
    db = MagicMock()

    # Clients
    db.get_all_clients.return_value = [
        {'id': 1, 'full_name': 'Client A', 'phone': '+7 900 111 2233'},
        {'id': 2, 'full_name': 'Client B', 'phone': '+7 900 444 5566'},
    ]
    db.get_client_by_id.return_value = {'id': 1, 'full_name': 'Client A'}
    db.add_client.return_value = 10

    # Contracts
    db.get_all_contracts.return_value = [
        {'id': 1, 'contract_number': 'D-001', 'client_id': 1, 'project_type': 'Individual'},
    ]
    db.get_contract_by_id.return_value = {'id': 1, 'contract_number': 'D-001'}
    db.add_contract.return_value = 20

    # Employees
    db.get_all_employees.return_value = [
        {'id': 1, 'full_name': 'Admin', 'position': 'Administrator'},
    ]
    db.get_employee_by_id.return_value = {'id': 1, 'full_name': 'Admin'}
    db.add_employee.return_value = 30

    # CRM Cards
    db.get_crm_cards_by_project_type.return_value = [
        {'id': 1, 'contract_id': 1, 'column_name': 'new_order'},
    ]
    db.get_crm_card_data.return_value = {'id': 1, 'contract_id': 1}
    db.add_crm_card.return_value = 40

    # Supervision
    db.get_supervision_cards_active.return_value = []
    db.get_supervision_cards_archived.return_value = []
    db.get_supervision_card_data.return_value = None

    # Payments
    db.get_payments_for_contract.return_value = [
        {'id': 1, 'contract_id': 1, 'employee_id': 2, 'final_amount': 5000.0},
    ]

    # Rates
    db.get_rates.return_value = []
    db.get_rate_by_id.return_value = None

    # Salaries
    db.get_salaries.return_value = []
    db.get_salary_by_id.return_value = None

    # History
    db.get_action_history.return_value = []
    db.get_supervision_history.return_value = []

    # Files
    db.get_contract_files.return_value = []

    # Statistics
    db.get_dashboard_statistics.return_value = {'total_orders': 10}
    db.get_supervision_statistics_filtered.return_value = {}

    return db


@pytest.fixture
def mock_api():
    """Mock APIClient with all methods"""
    api = MagicMock()
    api.is_online = True

    # Clients
    api.get_clients.return_value = [
        {'id': 101, 'full_name': 'API Client A'},
        {'id': 102, 'full_name': 'API Client B'},
    ]
    api.get_client.return_value = {'id': 101, 'full_name': 'API Client A'}
    api.create_client.return_value = {'id': 101, 'full_name': 'API Client A'}
    api.update_client.return_value = {'id': 101, 'updated': True}
    api.delete_client.return_value = True

    # Contracts
    api.get_contracts.return_value = [
        {'id': 201, 'contract_number': 'D-API-001', 'client_id': 101},
    ]
    api.get_contract.return_value = {'id': 201, 'contract_number': 'D-API-001'}
    api.create_contract.return_value = {'id': 201}
    api.update_contract.return_value = {'id': 201, 'updated': True}
    api.delete_contract.return_value = True

    # Employees
    api.get_employees.return_value = [{'id': 301, 'full_name': 'API Admin'}]
    api.get_employee.return_value = {'id': 301, 'full_name': 'API Admin'}
    api.get_employees_by_position.return_value = [{'id': 301, 'position': 'Designer'}]
    api.create_employee.return_value = {'id': 301}
    api.update_employee.return_value = {'id': 301}
    api.delete_employee.return_value = True

    # CRM Cards
    api.get_crm_cards.return_value = [
        {'id': 401, 'contract_id': 201, 'column_name': 'new_order'},
    ]
    api.get_crm_card.return_value = {'id': 401, 'contract_id': 201}
    api.create_crm_card.return_value = {'id': 401}
    api.update_crm_card.return_value = {'id': 401}
    api.delete_crm_card.return_value = True

    # Supervision
    api.get_supervision_cards.return_value = []
    api.get_supervision_card.return_value = None
    api.create_supervision_card.return_value = {'id': 501}
    api.update_supervision_card.return_value = {'id': 501}

    # Payments
    api.get_payments_for_contract.return_value = [
        {'id': 601, 'contract_id': 201, 'final_amount': 10000.0},
    ]
    api.create_payment.return_value = {'id': 601}
    api.update_payment.return_value = {'id': 601}
    api.delete_payment.return_value = True

    # Rates
    api.get_rates.return_value = [{'id': 701, 'rate_type': 'individual'}]
    api.get_rate.return_value = {'id': 701}
    api.create_rate.return_value = {'id': 701}

    # Salaries
    api.get_salaries.return_value = [{'id': 801, 'amount': 50000}]
    api.get_salary.return_value = {'id': 801}
    api.create_salary.return_value = {'id': 801}

    # History
    api.get_action_history.return_value = [{'id': 1, 'action_type': 'create'}]
    api.create_action_history.return_value = {'id': 1}
    api.get_supervision_history.return_value = []
    api.add_supervision_history.return_value = {'id': 1}

    # Stage executors
    api.get_stage_executors.return_value = []
    api.update_stage_executor.return_value = {'id': 1}

    # Files
    api.get_contract_files.return_value = []
    api.create_file_record.return_value = {'id': 1}
    api.delete_file_record.return_value = True
    api.validate_files.return_value = []

    # Stats
    api.get_dashboard_statistics.return_value = {'total_orders': 50}

    # Agent types
    api.get_agent_types.return_value = ['FESTIVAL', 'PETROVICH']

    return api


@pytest.fixture
def mock_api_offline(mock_api):
    """Mock APIClient that raises ConnectionError on all calls"""
    from utils.api_client import APIConnectionError
    mock_api.is_online = False
    mock_api.get_clients.side_effect = APIConnectionError("Offline")
    mock_api.get_client.side_effect = APIConnectionError("Offline")
    mock_api.get_contracts.side_effect = APIConnectionError("Offline")
    mock_api.get_contract.side_effect = APIConnectionError("Offline")
    mock_api.get_employees.side_effect = APIConnectionError("Offline")
    mock_api.get_employee.side_effect = APIConnectionError("Offline")
    mock_api.get_employees_by_position.side_effect = APIConnectionError("Offline")
    mock_api.get_crm_cards.side_effect = APIConnectionError("Offline")
    mock_api.get_crm_card.side_effect = APIConnectionError("Offline")
    mock_api.get_supervision_cards.side_effect = APIConnectionError("Offline")
    mock_api.get_supervision_card.side_effect = APIConnectionError("Offline")
    mock_api.get_payments_for_contract.side_effect = APIConnectionError("Offline")
    mock_api.get_rates.side_effect = APIConnectionError("Offline")
    mock_api.get_rate.side_effect = APIConnectionError("Offline")
    mock_api.get_salaries.side_effect = APIConnectionError("Offline")
    mock_api.get_salary.side_effect = APIConnectionError("Offline")
    mock_api.get_action_history.side_effect = APIConnectionError("Offline")
    mock_api.get_supervision_history.side_effect = APIConnectionError("Offline")
    mock_api.get_stage_executors.side_effect = APIConnectionError("Offline")
    mock_api.get_contract_files.side_effect = APIConnectionError("Offline")
    mock_api.get_dashboard_statistics.side_effect = APIConnectionError("Offline")
    return mock_api
