# -*- coding: utf-8 -*-
"""
Покрытие utils/data_access.py — основные CRUD методы.
Тестируем оба пути: offline (db only) и online (api_client + fallback).
~60 тестов.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.data_access import DataAccess


@pytest.fixture
def mock_db():
    """Мок DatabaseManager."""
    db = MagicMock()
    db.get_all_clients.return_value = [{'id': 1, 'full_name': 'Клиент'}]
    db.get_client_by_id.return_value = {'id': 1, 'full_name': 'Клиент'}
    db.get_clients_count.return_value = 1
    db.add_client.return_value = 1
    db.get_all_contracts.return_value = [{'id': 10, 'contract_number': '1/2026'}]
    db.get_contract_by_id.return_value = {'id': 10, 'contract_number': '1/2026'}
    db.get_contracts_count.return_value = 1
    db.add_contract.return_value = 10
    db.get_all_employees.return_value = [{'id': 5, 'full_name': 'Сотрудник'}]
    db.get_employee.return_value = {'id': 5}
    db.get_crm_cards.return_value = [{'id': 100}]
    db.get_crm_card_by_id.return_value = {'id': 100}
    db.get_supervision_cards.return_value = [{'id': 200}]
    db.check_contract_number_exists.return_value = False
    db.get_contracts_count_by_client.return_value = 3
    db.connect.return_value = MagicMock()
    db.get_employees_by_position.return_value = [{'id': 5, 'position': 'Менеджер'}]
    db.get_supervision_cards_active.return_value = [{'id': 200}]
    db.get_supervision_card_by_id.return_value = {'id': 200}
    db.get_payments_by_contract.return_value = [{'id': 300}]
    db.get_action_history.return_value = [{'id': 1, 'action': 'test'}]
    db.get_project_timeline.return_value = [{'stage_code': 'S1'}]
    db.get_project_files.return_value = [{'id': 1}]
    db.get_contract_years.return_value = [2025, 2026]
    db.get_cities.return_value = ['СПБ', 'МСК']
    return db


@pytest.fixture
def mock_api():
    """Мок API client."""
    api = MagicMock()
    api.get_clients.return_value = [{'id': 1, 'full_name': 'API Клиент'}]
    api.get_client.return_value = {'id': 1, 'full_name': 'API Клиент'}
    api.get_clients_paginated.return_value = ([{'id': 1}], 1)
    api.create_client.return_value = {'id': 1}
    api.update_client.return_value = {'id': 1}
    api.delete_client.return_value = True
    api.get_contracts.return_value = [{'id': 10, 'client_id': 1}]
    api.get_contract.return_value = {'id': 10}
    api.get_contracts_paginated.return_value = ([{'id': 10}], 1)
    api.get_contracts_count.return_value = 5
    api.create_contract.return_value = {'id': 10}
    api.update_contract.return_value = {'id': 10}
    api.delete_contract.return_value = True
    api.check_contract_number_exists.return_value = False
    api.get_employees.return_value = [{'id': 5}]
    api.get_employee.return_value = {'id': 5}
    api.get_crm_cards.return_value = [{'id': 100}]
    api.get_crm_card.return_value = {'id': 100}
    api.get_supervision_cards.return_value = [{'id': 200}]
    api.get_supervision_card.return_value = {'id': 200}
    api.get_supervision_cards_active.return_value = [{'id': 200}]
    api.get_payments_for_contract.return_value = [{'id': 300}]
    api.get_action_history.return_value = [{'id': 1}]
    api.get_project_timeline.return_value = [{'stage_code': 'S1'}]
    api.get_project_files.return_value = [{'id': 1}]
    return api


def _create_da(mock_db, mock_api=None):
    """Создать DataAccess с моками."""
    with patch('utils.data_access.get_offline_manager', return_value=None), \
         patch('utils.data_access.DatabaseManager', return_value=mock_db):
        da = DataAccess(api_client=mock_api, db=mock_db)
        return da


# ==================== КЛИЕНТЫ — Offline ====================

class TestClientsOffline:
    def test_get_all_clients(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_all_clients()
        mock_db.get_all_clients.assert_called_once()
        assert len(result) == 1

    def test_get_client(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_client(1)
        mock_db.get_client_by_id.assert_called_once_with(1)

    def test_get_clients_paginated(self, mock_db):
        da = _create_da(mock_db)
        clients, total = da.get_clients_paginated(skip=0, limit=10)
        assert total == 1

    def test_create_client(self, mock_db):
        da = _create_da(mock_db)
        result = da.create_client({'full_name': 'Новый'})
        mock_db.add_client.assert_called_once()
        assert result['id'] == 1

    def test_update_client(self, mock_db):
        da = _create_da(mock_db)
        result = da.update_client(1, {'full_name': 'Обновлённый'})
        mock_db.update_client.assert_called_once()
        assert result is True

    def test_delete_client(self, mock_db):
        da = _create_da(mock_db)
        result = da.delete_client(1)
        mock_db.delete_client.assert_called_once_with(1)
        assert result is True

    def test_get_contracts_count_by_client(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_contracts_count_by_client(1)
        assert result == 3


# ==================== КЛИЕНТЫ — Online ====================

class TestClientsOnline:
    def test_get_all_clients_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_all_clients()
        mock_api.get_clients.assert_called_once()
        assert result[0]['full_name'] == 'API Клиент'

    def test_get_client_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_client(1)
        mock_api.get_client.assert_called_once_with(1)

    def test_get_clients_paginated_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        clients, total = da.get_clients_paginated()
        mock_api.get_clients_paginated.assert_called_once()

    def test_api_fallback_on_error(self, mock_db, mock_api):
        mock_api.get_clients.side_effect = Exception('err')
        da = _create_da(mock_db, mock_api)
        result = da.get_all_clients()
        mock_db.get_all_clients.assert_called_once()

    def test_create_client_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.create_client({'full_name': 'Новый'})
        mock_db.add_client.assert_called_once()

    def test_update_client_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.update_client(1, {'full_name': 'Обновлённый'})
        mock_db.update_client.assert_called_once()

    def test_delete_client_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.delete_client(1)
        assert result is True


# ==================== ДОГОВОРА — Offline ====================

class TestContractsOffline:
    def test_get_all_contracts(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_all_contracts()
        mock_db.get_all_contracts.assert_called_once()

    def test_get_contract(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_contract(10)
        mock_db.get_contract_by_id.assert_called_once_with(10)

    def test_get_contracts_paginated(self, mock_db):
        da = _create_da(mock_db)
        contracts, total = da.get_contracts_paginated()
        assert total == 1

    def test_get_contracts_count(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_contracts_count()
        assert result == 1

    def test_check_contract_number_exists(self, mock_db):
        da = _create_da(mock_db)
        result = da.check_contract_number_exists('1/2026')
        assert result is False


# ==================== ДОГОВОРА — Online ====================

class TestContractsOnline:
    def test_get_all_contracts_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_all_contracts()
        mock_api.get_contracts.assert_called_once()

    def test_get_contract_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_contract(10)
        mock_api.get_contract.assert_called_once_with(10)

    def test_get_contracts_paginated_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        contracts, total = da.get_contracts_paginated()
        mock_api.get_contracts_paginated.assert_called_once()

    def test_get_contracts_count_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_contracts_count()
        mock_api.get_contracts_count.assert_called_once()

    def test_api_fallback_contracts(self, mock_db, mock_api):
        mock_api.get_contracts.side_effect = Exception('err')
        da = _create_da(mock_db, mock_api)
        result = da.get_all_contracts()
        mock_db.get_all_contracts.assert_called_once()

    def test_contracts_count_by_client_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_contracts_count_by_client(1)
        assert result == 1


# ==================== СОТРУДНИКИ ====================

class TestEmployees:
    def test_get_all_employees_offline(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_all_employees()
        mock_db.get_all_employees.assert_called_once()

    def test_get_all_employees_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_all_employees()
        mock_api.get_employees.assert_called_once()

    def test_get_employee_offline(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_employee(5)
        assert result is not None

    def test_get_employee_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_employee(5)
        mock_api.get_employee.assert_called_once_with(5)

    def test_get_employees_by_position(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_employees_by_position('Менеджер')
        assert len(result) == 1


# ==================== CRM КАРТОЧКИ ====================

class TestCrmCards:
    def test_get_crm_cards_offline(self, mock_db):
        mock_db.get_crm_cards_by_project_type.return_value = [{'id': 100}]
        da = _create_da(mock_db)
        result = da.get_crm_cards('Дизайн-проект')
        mock_db.get_crm_cards_by_project_type.assert_called_once()

    def test_get_crm_cards_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_crm_cards('Дизайн-проект')
        mock_api.get_crm_cards.assert_called_once()

    def test_get_crm_card_offline(self, mock_db):
        mock_db.get_crm_card_data.return_value = {'id': 100}
        da = _create_da(mock_db)
        result = da.get_crm_card(100)
        mock_db.get_crm_card_data.assert_called_once_with(100)

    def test_get_crm_card_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_crm_card(100)
        mock_api.get_crm_card.assert_called_once()


# ==================== SUPERVISION CARDS ====================

class TestSupervisionCards:
    def test_get_active_offline(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_supervision_cards_active()
        assert len(result) == 1

    def test_get_active_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_supervision_cards_active()
        mock_api.get_supervision_cards.assert_called_once_with(status="active")

    def test_get_supervision_card_offline(self, mock_db):
        mock_db.get_supervision_card_data.return_value = {'id': 200}
        da = _create_da(mock_db)
        result = da.get_supervision_card(200)
        mock_db.get_supervision_card_data.assert_called_once_with(200)

    def test_get_supervision_card_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_supervision_card(200)
        mock_api.get_supervision_card.assert_called_once()


# ==================== PROPERTIES ====================

class TestProperties:
    def test_is_multi_user_false(self, mock_db):
        da = _create_da(mock_db)
        assert da.is_multi_user is False

    def test_is_multi_user_true(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        assert da.is_multi_user is True

    def test_is_online_without_offline_manager(self, mock_db):
        da = _create_da(mock_db)
        with patch('utils.data_access.get_offline_manager', return_value=None):
            assert da.is_online is False

    def test_is_online_with_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=None):
            assert da.is_online is True

    def test_should_use_api_false(self, mock_db):
        da = _create_da(mock_db)
        assert da._should_use_api() is False

    def test_should_use_api_true(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        assert da._should_use_api() is True

    def test_prefer_local_skips_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        da.prefer_local = True
        assert da._should_use_api() is False


# ==================== PAYMENTS ====================

class TestPayments:
    def test_get_payments_for_contract_offline(self, mock_db):
        mock_db.get_payments_for_contract.return_value = [{'id': 300}]
        da = _create_da(mock_db)
        result = da.get_payments_for_contract(10)
        assert len(result) == 1

    def test_get_payments_for_contract_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_payments_for_contract(10)
        mock_api.get_payments_for_contract.assert_called_once()


# ==================== HISTORY ====================

class TestHistory:
    def test_get_action_history_offline(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_action_history('contract', 10)
        assert len(result) == 1

    def test_get_action_history_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_action_history('contract', 10)
        mock_api.get_action_history.assert_called_once()


# ==================== TIMELINE ====================

class TestTimeline:
    def test_get_project_timeline_offline(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_project_timeline(10)
        assert len(result) == 1

    def test_get_project_timeline_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_project_timeline(10)
        mock_api.get_project_timeline.assert_called_once()


# ==================== FILES ====================

class TestFiles:
    def test_get_project_files_offline(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_project_files(10)
        assert len(result) == 1

    def test_get_project_files_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.get_project_files(10)
        mock_api.get_project_files.assert_called_once()


# ==================== MISC ====================

class TestMisc:
    def test_get_pending_operations_count_no_om(self, mock_db):
        da = _create_da(mock_db)
        with patch('utils.data_access.get_offline_manager', return_value=None):
            assert da.get_pending_operations_count() == 0

    def test_get_pending_operations_count_with_om(self, mock_db):
        mock_om = MagicMock()
        mock_om.get_pending_operations_count.return_value = 5
        da = _create_da(mock_db)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            assert da.get_pending_operations_count() == 5

    def test_force_sync_no_om(self, mock_db):
        da = _create_da(mock_db)
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da.force_sync()

    def test_force_sync_with_om(self, mock_db):
        mock_om = MagicMock()
        da = _create_da(mock_db)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            da.force_sync()
            mock_om.force_sync.assert_called_once()

    def test_get_contract_years_offline(self, mock_db):
        da = _create_da(mock_db)
        result = da.get_contract_years()
        assert 2026 in result

    def test_get_cities_offline_returns_empty(self, mock_db):
        """get_cities без API возвращает пустой список."""
        da = _create_da(mock_db)
        result = da.get_cities()
        assert result == []

    def test_get_cities_api(self, mock_db, mock_api):
        """get_cities через API."""
        mock_api.get_cities.return_value = ['СПБ', 'МСК']
        da = _create_da(mock_db, mock_api)
        result = da.get_cities()
        assert 'СПБ' in result

    def test_check_contract_number_exists_api(self, mock_db, mock_api):
        da = _create_da(mock_db, mock_api)
        result = da.check_contract_number_exists('1/2026')
        mock_api.check_contract_number_exists.assert_called_once()
