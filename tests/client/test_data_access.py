# -*- coding: utf-8 -*-
"""
Unit-тесты DataAccess — fallback логика API -> DB, offline очередь
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# Мокаем PyQt5 ДО импорта DataAccess, чтобы не требовать реального Qt
@pytest.fixture(autouse=True)
def mock_pyqt():
    """Мокаем PyQt5 сигналы для DataAccess"""
    with patch('utils.data_access.get_offline_manager', return_value=None):
        yield


def _make_data_access(mock_api=None, mock_db=None):
    """Создать DataAccess с моками"""
    from utils.data_access import DataAccess
    da = DataAccess.__new__(DataAccess)
    da.api_client = mock_api
    da.db = mock_db or MagicMock()
    da._is_online = mock_api is not None
    da.prefer_local = False
    return da


# ============================================================================
# ЧТЕНИЕ: API доступен -> читаем из API
# ============================================================================

class TestReadFromAPI:
    """Когда API доступен, DataAccess читает из API"""

    def test_get_all_clients_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_all_clients()
        assert result == mock_api.get_clients.return_value
        mock_api.get_clients.assert_called_once()
        mock_db.get_all_clients.assert_not_called()

    def test_get_client_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_client(101)
        assert result == mock_api.get_client.return_value
        mock_api.get_client.assert_called_once_with(101)

    def test_get_all_contracts_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_all_contracts()
        assert result == mock_api.get_contracts.return_value
        mock_api.get_contracts.assert_called_once()

    def test_get_contract_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_contract(201)
        assert result == mock_api.get_contract.return_value

    def test_get_all_employees_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_all_employees()
        assert result == mock_api.get_employees.return_value

    def test_get_employees_by_position_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_employees_by_position('Designer')
        assert result == mock_api.get_employees_by_position.return_value
        mock_api.get_employees_by_position.assert_called_once_with('Designer')

    def test_get_crm_cards_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_crm_cards('Individual')
        assert result == mock_api.get_crm_cards.return_value
        mock_api.get_crm_cards.assert_called_once_with('Individual')

    def test_get_payments_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_payments_for_contract(201)
        assert result == mock_api.get_payments_for_contract.return_value

    def test_get_rates_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_rates('Individual', 'Designer')
        assert result == mock_api.get_rates.return_value
        mock_api.get_rates.assert_called_once_with('Individual', 'Designer')

    def test_get_salaries_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_salaries('2025-01', 1)
        assert result == mock_api.get_salaries.return_value

    def test_get_action_history_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_action_history('client', 1)
        assert result == mock_api.get_action_history.return_value

    def test_get_supervision_history_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_supervision_history(1)
        assert result == mock_api.get_supervision_history.return_value

    def test_get_contract_files_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_contract_files(1, 'design')
        mock_api.get_contract_files.assert_called_once_with(1, 'design')

    def test_get_dashboard_statistics_from_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.get_dashboard_statistics(2025, 1)
        assert result == mock_api.get_dashboard_statistics.return_value


# ============================================================================
# ЧТЕНИЕ: API упал -> fallback на локальную БД
# ============================================================================

class TestFallbackToDB:
    """Когда API падает, DataAccess переключается на локальную БД"""

    def test_get_all_clients_fallback(self, mock_api_offline, mock_db):
        da = _make_data_access(mock_api_offline, mock_db)
        result = da.get_all_clients()
        assert result == mock_db.get_all_clients.return_value
        mock_db.get_all_clients.assert_called_once()

    def test_get_client_fallback(self, mock_api_offline, mock_db):
        da = _make_data_access(mock_api_offline, mock_db)
        result = da.get_client(1)
        assert result == mock_db.get_client_by_id.return_value
        mock_db.get_client_by_id.assert_called_once_with(1)

    def test_get_all_contracts_fallback(self, mock_api_offline, mock_db):
        da = _make_data_access(mock_api_offline, mock_db)
        result = da.get_all_contracts()
        assert result == mock_db.get_all_contracts.return_value

    def test_get_contract_fallback(self, mock_api_offline, mock_db):
        da = _make_data_access(mock_api_offline, mock_db)
        result = da.get_contract(1)
        assert result == mock_db.get_contract_by_id.return_value

    def test_get_all_employees_fallback(self, mock_api_offline, mock_db):
        da = _make_data_access(mock_api_offline, mock_db)
        result = da.get_all_employees()
        assert result == mock_db.get_all_employees.return_value

    def test_get_employees_by_position_fallback(self, mock_api_offline, mock_db):
        da = _make_data_access(mock_api_offline, mock_db)
        result = da.get_employees_by_position('Designer')
        assert result == mock_db.get_employees_by_position.return_value

    def test_get_crm_cards_fallback(self, mock_api_offline, mock_db):
        da = _make_data_access(mock_api_offline, mock_db)
        result = da.get_crm_cards('Individual')
        assert result == mock_db.get_crm_cards_by_project_type.return_value
        mock_db.get_crm_cards_by_project_type.assert_called_once_with('Individual')

    def test_get_payments_fallback(self, mock_api_offline, mock_db):
        da = _make_data_access(mock_api_offline, mock_db)
        result = da.get_payments_for_contract(1)
        assert result == mock_db.get_payments_for_contract.return_value

    def test_get_rates_fallback(self, mock_api_offline, mock_db):
        da = _make_data_access(mock_api_offline, mock_db)
        result = da.get_rates('Individual')
        assert result == mock_db.get_rates.return_value

    def test_get_salaries_fallback(self, mock_api_offline, mock_db):
        da = _make_data_access(mock_api_offline, mock_db)
        result = da.get_salaries()
        assert result == mock_db.get_salaries.return_value

    def test_get_action_history_fallback(self, mock_api_offline, mock_db):
        da = _make_data_access(mock_api_offline, mock_db)
        result = da.get_action_history('client', 1)
        assert result == mock_db.get_action_history.return_value

    def test_get_dashboard_statistics_fallback(self, mock_api_offline, mock_db):
        da = _make_data_access(mock_api_offline, mock_db)
        result = da.get_dashboard_statistics()
        assert result == mock_db.get_dashboard_statistics.return_value


# ============================================================================
# АВТОНОМНЫЙ РЕЖИМ: нет api_client -> только локальная БД
# ============================================================================

class TestLocalOnlyMode:
    """Без api_client DataAccess работает только с локальной БД"""

    def test_get_all_clients_local(self, mock_db):
        da = _make_data_access(None, mock_db)
        result = da.get_all_clients()
        assert result == mock_db.get_all_clients.return_value

    def test_get_contract_local(self, mock_db):
        da = _make_data_access(None, mock_db)
        result = da.get_contract(1)
        assert result == mock_db.get_contract_by_id.return_value

    def test_is_multi_user_false(self, mock_db):
        da = _make_data_access(None, mock_db)
        assert da.is_multi_user is False

    def test_is_multi_user_true(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        assert da.is_multi_user is True

    def test_create_client_local_only(self, mock_db):
        da = _make_data_access(None, mock_db)
        result = da.create_client({'full_name': 'New Client'})
        assert result is not None
        assert result['id'] == mock_db.add_client.return_value
        mock_db.add_client.assert_called_once()

    def test_create_contract_local_only(self, mock_db):
        da = _make_data_access(None, mock_db)
        result = da.create_contract({'contract_number': 'D-NEW'})
        assert result is not None
        mock_db.add_contract.assert_called_once()

    def test_update_client_local_only(self, mock_db):
        da = _make_data_access(None, mock_db)
        result = da.update_client(1, {'full_name': 'Updated'})
        assert result is True
        mock_db.update_client.assert_called_once_with(1, {'full_name': 'Updated'})

    def test_delete_employee_local_only(self, mock_db):
        da = _make_data_access(None, mock_db)
        result = da.delete_employee(1)
        assert result is True
        mock_db.delete_employee.assert_called_once_with(1)


# ============================================================================
# ЗАПИСЬ: API online -> пишем в DB + API
# ============================================================================

class TestWriteOnline:
    """При записи: сначала DB, потом API"""

    def test_create_client_writes_to_both(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da._is_online = True
        result = da.create_client({'full_name': 'New Client'})
        # DB called first
        mock_db.add_client.assert_called_once()
        # API called too
        mock_api.create_client.assert_called_once()
        # Returns API result
        assert result == mock_api.create_client.return_value

    def test_update_client_writes_to_both(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da._is_online = True
        result = da.update_client(1, {'full_name': 'Updated'})
        mock_db.update_client.assert_called_once()
        mock_api.update_client.assert_called_once()

    def test_create_employee_writes_to_both(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da._is_online = True
        result = da.create_employee({'full_name': 'New Employee'})
        mock_db.add_employee.assert_called_once()
        mock_api.create_employee.assert_called_once()

    def test_update_crm_card_writes_to_both(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da._is_online = True
        result = da.update_crm_card(1, {'column_name': 'in_progress'})
        mock_db.update_crm_card.assert_called_once()
        mock_api.update_crm_card.assert_called_once()

    def test_update_supervision_card_writes_to_both(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da._is_online = True
        result = da.update_supervision_card(1, {'column_name': 'done'})
        mock_db.update_supervision_card.assert_called_once()
        mock_api.update_supervision_card.assert_called_once()


# ============================================================================
# ЗАПИСЬ: API offline -> пишем в DB + очередь
# ============================================================================

class TestWriteOffline:
    """При записи с недоступным API: DB + offline queue"""

    def test_create_client_queued_on_api_error(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da._is_online = True
        mock_api.create_client.side_effect = Exception("Server down")
        with patch.object(da, '_queue_operation') as mock_queue:
            result = da.create_client({'full_name': 'Offline Client'})
            mock_db.add_client.assert_called_once()
            mock_queue.assert_called_once()
            assert mock_queue.call_args[0][0] == 'create'
            assert mock_queue.call_args[0][1] == 'client'

    def test_update_client_queued_on_api_error(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da._is_online = True
        mock_api.update_client.side_effect = Exception("Server down")
        with patch.object(da, '_queue_operation') as mock_queue:
            da.update_client(1, {'full_name': 'Updated'})
            mock_db.update_client.assert_called_once()
            mock_queue.assert_called_once()
            assert mock_queue.call_args[0][0] == 'update'

    def test_delete_client_queued_on_api_error(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da._is_online = True
        mock_api.delete_client.side_effect = Exception("Server down")
        with patch.object(da, '_queue_operation') as mock_queue:
            da.delete_client(1)
            mock_db.delete_client.assert_called_once()
            mock_queue.assert_called_once()
            assert mock_queue.call_args[0][0] == 'delete'

    def test_update_employee_queued_on_api_error(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da._is_online = True
        mock_api.update_employee.side_effect = Exception("Server down")
        with patch.object(da, '_queue_operation') as mock_queue:
            da.update_employee(1, {'full_name': 'Updated'})
            mock_queue.assert_called_once()

    def test_update_crm_card_queued_on_api_error(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da._is_online = True
        mock_api.update_crm_card.side_effect = Exception("Server down")
        with patch.object(da, '_queue_operation') as mock_queue:
            da.update_crm_card(1, {'column_name': 'done'})
            mock_queue.assert_called_once()


# ============================================================================
# PREFER_LOCAL MODE: читаем из DB, пишем в API
# ============================================================================

class TestPreferLocalMode:
    """prefer_local=True: чтение из DB, запись через API"""

    def test_prefer_local_reads_from_db(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da.prefer_local = True
        result = da.get_all_clients()
        assert result == mock_db.get_all_clients.return_value
        mock_api.get_clients.assert_not_called()

    def test_prefer_local_contracts_from_db(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da.prefer_local = True
        result = da.get_all_contracts()
        assert result == mock_db.get_all_contracts.return_value
        mock_api.get_contracts.assert_not_called()

    def test_prefer_local_employees_from_db(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da.prefer_local = True
        result = da.get_all_employees()
        assert result == mock_db.get_all_employees.return_value

    def test_prefer_local_still_writes_to_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        da.prefer_local = True
        da._is_online = True
        da.create_client({'full_name': 'New Client'})
        mock_api.create_client.assert_called_once()


# ============================================================================
# ПРЯМЫЕ ОПЕРАЦИИ (без fallback)
# ============================================================================

class TestDirectOperations:
    """Операции, которые идут напрямую через API или DB без fallback"""

    def test_create_crm_card_local_first(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.create_crm_card({'contract_id': 1})
        assert result == mock_api.create_crm_card.return_value
        # local-first: всегда сохраняем локально перед API
        mock_db.add_crm_card.assert_called_once()

    def test_create_crm_card_db_only(self, mock_db):
        da = _make_data_access(None, mock_db)
        result = da.create_crm_card({'contract_id': 1})
        assert result is not None
        mock_db.add_crm_card.assert_called_once()

    def test_delete_contract_api_only(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        mock_api.delete_contract.return_value = True
        result = da.delete_contract(1)
        assert result is True
        mock_api.delete_contract.assert_called_once_with(1)
        # Также удаляется локально для консистентности кэша
        mock_db.delete_order.assert_called_once()

    def test_create_payment_api_only(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.create_payment({'contract_id': 1, 'amount': 5000})
        mock_api.create_payment.assert_called_once()

    def test_update_crm_card_column_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.update_crm_card_column(1, 'in_progress')
        mock_api.update_crm_card.assert_called_once_with(1, {'column_name': 'in_progress'})

    def test_add_action_history_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.add_action_history(1, 'create', 'client', 1, 'Created client')
        mock_api.create_action_history.assert_called_once()

    def test_add_supervision_history_api(self, mock_api, mock_db):
        da = _make_data_access(mock_api, mock_db)
        result = da.add_supervision_history(1, 1, 'move', 'Moved card')
        mock_api.add_supervision_history.assert_called_once()
