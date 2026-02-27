# -*- coding: utf-8 -*-
"""
Покрытие utils/data_access.py — contracts, employees, CRM cards, payments, supervision.
Расширение test_data_access_full.py.
~50 тестов, 3 сценария на каждый метод: API OK, offline fallback, API fails → fallback.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.data_access import DataAccess
from utils.api_client.exceptions import APIConnectionError, APITimeoutError


# ==================== ФИКСТУРЫ ====================

def _make_da(mock_db, mock_api=None):
    """Создать DataAccess с моками, обходя OfflineManager."""
    with patch('utils.data_access.get_offline_manager', return_value=None), \
         patch('utils.data_access.DatabaseManager', return_value=mock_db):
        da = DataAccess(api_client=mock_api, db=mock_db)
        return da


@pytest.fixture
def mock_db():
    """Мок DatabaseManager со всеми нужными методами."""
    db = MagicMock()
    # Договора
    db.get_all_contracts.return_value = [{'id': 10, 'contract_number': '1/2026'}]
    db.get_contract_by_id.return_value = {'id': 10, 'contract_number': '1/2026'}
    db.get_contracts_count.return_value = 1
    db.add_contract.return_value = 10
    db.update_contract.return_value = True
    db.get_crm_card_id_by_contract.return_value = 100
    db.delete_order.return_value = True
    db.check_contract_number_exists.return_value = False
    # Сотрудники
    db.get_all_employees.return_value = [{'id': 5, 'full_name': 'Сотрудник'}]
    db.get_employee_by_id.return_value = {'id': 5, 'full_name': 'Сотрудник'}
    db.add_employee.return_value = 5
    db.update_employee.return_value = True
    db.delete_employee.return_value = True
    db.get_employees_by_position.return_value = [{'id': 5, 'position': 'Дизайнер'}]
    # CRM карточки
    db.get_crm_cards_by_project_type.return_value = [{'id': 100, 'column_name': 'Новый заказ'}]
    db.get_crm_card_data.return_value = {'id': 100, 'column_name': 'Новый заказ'}
    db.add_crm_card.return_value = 100
    db.update_crm_card.return_value = True
    db.update_crm_card_column.return_value = True
    db.get_contract_id_by_crm_card.return_value = 10
    db.get_archived_crm_cards.return_value = [{'id': 101, 'column_name': 'Архив'}]
    # Платежи
    db.get_payments_for_contract.return_value = [{'id': 300, 'amount': 50000}]
    db.add_payment.return_value = 300
    db.update_payment.return_value = True
    db.delete_payment.return_value = True
    db.get_payment.return_value = {'id': 300, 'amount': 50000}
    db.get_payments_by_type.return_value = [{'id': 300}]
    db.get_payments_by_supervision_card.return_value = [{'id': 301}]
    db.mark_payment_as_paid.return_value = True
    # Supervision
    db.get_supervision_cards_active.return_value = [{'id': 200}]
    db.get_supervision_cards_archived.return_value = [{'id': 201}]
    db.get_supervision_card_data.return_value = {'id': 200, 'column_name': 'В работе'}
    db.add_supervision_card.return_value = 200
    db.update_supervision_card.return_value = True
    db.update_supervision_card_column.return_value = True
    db.get_contract_id_by_supervision_card.return_value = 10
    db.get_supervision_addresses.return_value = ['Адрес 1']
    db.complete_supervision_stage.return_value = True
    db.reset_supervision_stage_completion.return_value = True
    db.pause_supervision_card.return_value = True
    db.resume_supervision_card.return_value = True
    db.delete_supervision_order.return_value = True
    # Соединение
    db.connect.return_value = MagicMock()
    return db


@pytest.fixture
def mock_api():
    """Мок API client со всеми нужными методами."""
    api = MagicMock()
    # Договора
    api.get_contracts.return_value = [{'id': 10, 'client_id': 1}]
    api.get_contract.return_value = {'id': 10}
    api.get_contracts_paginated.return_value = ([{'id': 10}], 1)
    api.create_contract.return_value = {'id': 10}
    api.update_contract.return_value = {'id': 10}
    api.delete_contract.return_value = True
    # Сотрудники
    api.get_employees.return_value = [{'id': 5, 'full_name': 'API Сотрудник'}]
    api.get_employee.return_value = {'id': 5, 'full_name': 'API Сотрудник'}
    api.create_employee.return_value = {'id': 5}
    api.update_employee.return_value = {'id': 5}
    api.delete_employee.return_value = True
    api.get_employees_by_position.return_value = [{'id': 5}]
    # CRM карточки
    api.get_crm_cards.return_value = [{'id': 100}]
    api.get_crm_card.return_value = {'id': 100}
    api.create_crm_card.return_value = {'id': 100}
    api.update_crm_card.return_value = {'id': 100}
    api.delete_crm_card.return_value = True
    api.move_crm_card.return_value = {'id': 100}
    api.get_archived_crm_cards.return_value = [{'id': 101}]
    # Платежи
    api.get_payments_for_contract.return_value = [{'id': 300}]
    api.create_payment.return_value = {'id': 300}
    api.update_payment.return_value = {'id': 300}
    api.delete_payment.return_value = True
    api.get_payment.return_value = {'id': 300}
    api.get_payments_by_type.return_value = [{'id': 300}]
    api.get_payments_by_supervision_card.return_value = [{'id': 301}]
    api.mark_payment_as_paid.return_value = True
    # Supervision
    api.get_supervision_cards.return_value = [{'id': 200}]
    api.get_supervision_card.return_value = {'id': 200}
    api.create_supervision_card.return_value = {'id': 200}
    api.update_supervision_card.return_value = {'id': 200}
    api.move_supervision_card.return_value = {'id': 200}
    api.complete_supervision_stage.return_value = {'success': True}
    api.reset_supervision_stage_completion.return_value = {'success': True}
    api.pause_supervision_card.return_value = {'success': True}
    api.resume_supervision_card.return_value = {'success': True}
    api.delete_supervision_order.return_value = True
    api.get_contract_id_by_supervision_card.return_value = 10
    api.get_supervision_addresses.return_value = ['API Адрес']
    return api


# ==================== ДОГОВОРА: API OK ====================

class TestContractsApiOk:
    """Договора — API доступен, работает корректно."""

    def test_get_all_contracts_api(self, mock_db, mock_api):
        """get_all_contracts вызывает API, не вызывает DB."""
        da = _make_da(mock_db, mock_api)
        result = da.get_all_contracts()
        mock_api.get_contracts.assert_called_once_with(skip=0, limit=10000)
        mock_db.get_all_contracts.assert_not_called()
        assert result == [{'id': 10, 'client_id': 1}]

    def test_get_contract_api(self, mock_db, mock_api):
        """get_contract вызывает API, не вызывает DB."""
        da = _make_da(mock_db, mock_api)
        result = da.get_contract(10)
        mock_api.get_contract.assert_called_once_with(10)
        mock_db.get_contract_by_id.assert_not_called()

    def test_create_contract_api_online(self, mock_db, mock_api):
        """create_contract сохраняет локально и через API."""
        da = _make_da(mock_db, mock_api)
        # is_online зависит от OfflineManager — мокаем
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.create_contract({'contract_number': '2/2026'})
        mock_db.add_contract.assert_called_once()
        mock_api.create_contract.assert_called_once()

    def test_update_contract_api_online(self, mock_db, mock_api):
        """update_contract обновляет локально и через API."""
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.update_contract(10, {'status': 'Закрыт'})
        mock_db.update_contract.assert_called_once_with(10, {'status': 'Закрыт'})
        mock_api.update_contract.assert_called_once_with(10, {'status': 'Закрыт'})
        assert result is True

    def test_delete_contract_api_online(self, mock_db, mock_api):
        """delete_contract удаляет через API и локально."""
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.delete_contract(10)
        mock_api.delete_contract.assert_called_once_with(10)
        # Локально тоже удаляется при успехе API
        mock_db.get_crm_card_id_by_contract.assert_called_once_with(10)
        assert result is True


# ==================== ДОГОВОРА: Offline (нет API) ====================

class TestContractsOffline:
    """Договора — API отсутствует, работа только через локальную БД."""

    def test_get_all_contracts_offline(self, mock_db):
        """get_all_contracts берёт из DB."""
        da = _make_da(mock_db)
        result = da.get_all_contracts()
        mock_db.get_all_contracts.assert_called_once()
        assert len(result) == 1

    def test_get_contract_offline(self, mock_db):
        """get_contract берёт из DB по ID."""
        da = _make_da(mock_db)
        result = da.get_contract(10)
        mock_db.get_contract_by_id.assert_called_once_with(10)

    def test_create_contract_offline(self, mock_db):
        """create_contract сохраняет только в DB."""
        da = _make_da(mock_db)
        result = da.create_contract({'contract_number': '3/2026'})
        mock_db.add_contract.assert_called_once()
        assert result['id'] == 10

    def test_update_contract_offline(self, mock_db):
        """update_contract обновляет только DB."""
        da = _make_da(mock_db)
        result = da.update_contract(10, {'status': 'Закрыт'})
        mock_db.update_contract.assert_called_once()
        assert result is True

    def test_delete_contract_offline(self, mock_db):
        """delete_contract удаляет только из DB."""
        da = _make_da(mock_db)
        result = da.delete_contract(10)
        mock_db.get_crm_card_id_by_contract.assert_called()
        mock_db.delete_order.assert_called_once()
        assert result is True


# ==================== ДОГОВОРА: API fails → fallback ====================

class TestContractsApiFails:
    """Договора — API кидает ошибку, fallback на DB."""

    def test_get_all_contracts_fallback(self, mock_db, mock_api):
        """get_all_contracts: API Exception → fallback на DB."""
        mock_api.get_contracts.side_effect = APIConnectionError("Connection refused")
        da = _make_da(mock_db, mock_api)
        result = da.get_all_contracts()
        mock_db.get_all_contracts.assert_called_once()
        assert len(result) == 1

    def test_get_contract_fallback(self, mock_db, mock_api):
        """get_contract: API Exception → fallback на DB."""
        mock_api.get_contract.side_effect = APITimeoutError("Timeout")
        da = _make_da(mock_db, mock_api)
        result = da.get_contract(10)
        mock_db.get_contract_by_id.assert_called_once_with(10)

    def test_create_contract_api_fail_queues(self, mock_db, mock_api):
        """create_contract: API ошибка → операция ставится в offline-очередь."""
        mock_api.create_contract.side_effect = APIConnectionError("Connection refused")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.create_contract({'contract_number': '4/2026'})
        # Локально сохранено
        mock_db.add_contract.assert_called_once()
        # В очередь поставлено (через _queue_operation → get_offline_manager)
        mock_om.queue_operation.assert_called_once()

    def test_update_contract_api_fail_queues(self, mock_db, mock_api):
        """update_contract: API ошибка → offline-очередь."""
        mock_api.update_contract.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.update_contract(10, {'status': 'Закрыт'})
        mock_db.update_contract.assert_called_once()
        mock_om.queue_operation.assert_called_once()
        assert result is True

    def test_delete_contract_api_fail_queues(self, mock_db, mock_api):
        """delete_contract: API ошибка → offline-очередь + локальное удаление."""
        mock_api.delete_contract.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.delete_contract(10)
        mock_om.queue_operation.assert_called_once()
        mock_db.delete_order.assert_called_once()


# ==================== СОТРУДНИКИ: API OK ====================

class TestEmployeesApiOk:
    """Сотрудники — API доступен и работает."""

    def test_get_all_employees_api(self, mock_db, mock_api):
        """get_all_employees вызывает API."""
        da = _make_da(mock_db, mock_api)
        result = da.get_all_employees()
        mock_api.get_employees.assert_called_once_with(skip=0, limit=10000)
        mock_db.get_all_employees.assert_not_called()

    def test_get_employee_api(self, mock_db, mock_api):
        """get_employee вызывает API."""
        da = _make_da(mock_db, mock_api)
        result = da.get_employee(5)
        mock_api.get_employee.assert_called_once_with(5)
        mock_db.get_employee_by_id.assert_not_called()

    def test_create_employee_api_online(self, mock_db, mock_api):
        """create_employee сохраняет локально и через API."""
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.create_employee({'full_name': 'Новый'})
        mock_db.add_employee.assert_called_once()
        mock_api.create_employee.assert_called_once()
        assert result == {'id': 5}

    def test_update_employee_api_online(self, mock_db, mock_api):
        """update_employee обновляет через API."""
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.update_employee(5, {'full_name': 'Обновлённый'})
        mock_api.update_employee.assert_called_once_with(5, {'full_name': 'Обновлённый'})
        assert result is True

    def test_delete_employee_api_online(self, mock_db, mock_api):
        """delete_employee удаляет через API."""
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.delete_employee(5)
        mock_api.delete_employee.assert_called_once_with(5)
        assert result is True

    def test_get_employees_by_position_api(self, mock_db, mock_api):
        """get_employees_by_position вызывает API."""
        da = _make_da(mock_db, mock_api)
        result = da.get_employees_by_position('Дизайнер')
        mock_api.get_employees_by_position.assert_called_once_with('Дизайнер')
        mock_db.get_employees_by_position.assert_not_called()


# ==================== СОТРУДНИКИ: Offline ====================

class TestEmployeesOffline:
    """Сотрудники — API отсутствует."""

    def test_get_all_employees_offline(self, mock_db):
        da = _make_da(mock_db)
        result = da.get_all_employees()
        mock_db.get_all_employees.assert_called_once()
        assert len(result) == 1

    def test_get_employee_offline(self, mock_db):
        da = _make_da(mock_db)
        result = da.get_employee(5)
        mock_db.get_employee_by_id.assert_called_once_with(5)

    def test_create_employee_offline(self, mock_db):
        da = _make_da(mock_db)
        result = da.create_employee({'full_name': 'Локальный'})
        mock_db.add_employee.assert_called_once()
        assert result['id'] == 5


# ==================== СОТРУДНИКИ: API fails ====================

class TestEmployeesApiFails:
    """Сотрудники — API кидает ошибку, fallback на DB."""

    def test_get_all_employees_fallback(self, mock_db, mock_api):
        mock_api.get_employees.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        result = da.get_all_employees()
        mock_db.get_all_employees.assert_called_once()

    def test_get_employee_fallback(self, mock_db, mock_api):
        mock_api.get_employee.side_effect = APITimeoutError("timeout")
        da = _make_da(mock_db, mock_api)
        result = da.get_employee(5)
        mock_db.get_employee_by_id.assert_called_once_with(5)

    def test_create_employee_api_fail_queues(self, mock_db, mock_api):
        """create_employee: API ошибка → offline-очередь."""
        mock_api.create_employee.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.create_employee({'full_name': 'Тест'})
        mock_db.add_employee.assert_called_once()
        mock_om.queue_operation.assert_called_once()

    def test_update_employee_api_fail_queues(self, mock_db, mock_api):
        mock_api.update_employee.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.update_employee(5, {'full_name': 'X'})
        mock_om.queue_operation.assert_called_once()
        assert result is True

    def test_delete_employee_api_fail_queues(self, mock_db, mock_api):
        mock_api.delete_employee.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.delete_employee(5)
        mock_db.delete_employee.assert_called_once_with(5)
        mock_om.queue_operation.assert_called_once()
        assert result is True


# ==================== CRM КАРТОЧКИ: API OK ====================

class TestCrmCardsApiOk:
    """CRM карточки — API доступен и работает."""

    def test_get_crm_cards_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        result = da.get_crm_cards('Индивидуальный')
        mock_api.get_crm_cards.assert_called_once_with('Индивидуальный')
        mock_db.get_crm_cards_by_project_type.assert_not_called()

    def test_get_crm_card_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        result = da.get_crm_card(100)
        mock_api.get_crm_card.assert_called_once_with(100)
        mock_db.get_crm_card_data.assert_not_called()

    def test_update_crm_card_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.update_crm_card(100, {'column_name': 'В работе'})
        mock_api.update_crm_card.assert_called_once_with(100, {'column_name': 'В работе'})
        assert result is True

    def test_move_crm_card_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.move_crm_card(100, 'На проверке')
        mock_api.move_crm_card.assert_called_once_with(100, 'На проверке')
        mock_db.update_crm_card_column.assert_called_once_with(100, 'На проверке')
        assert result is True

    def test_create_crm_card_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.create_crm_card({'contract_id': 10, 'column_name': 'Новый заказ'})
        mock_db.add_crm_card.assert_called_once()
        mock_api.create_crm_card.assert_called_once()

    def test_delete_crm_card_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.delete_crm_card(100)
        mock_api.delete_crm_card.assert_called_once_with(100)
        assert result is True

    def test_get_archived_crm_cards_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        result = da.get_archived_crm_cards('Индивидуальный')
        mock_api.get_archived_crm_cards.assert_called_once_with('Индивидуальный')
        mock_db.get_archived_crm_cards.assert_not_called()


# ==================== CRM КАРТОЧКИ: Offline ====================

class TestCrmCardsOffline:
    """CRM карточки — без API."""

    def test_get_crm_cards_offline(self, mock_db):
        da = _make_da(mock_db)
        result = da.get_crm_cards('Индивидуальный')
        mock_db.get_crm_cards_by_project_type.assert_called_once_with('Индивидуальный')

    def test_get_crm_card_offline(self, mock_db):
        da = _make_da(mock_db)
        result = da.get_crm_card(100)
        mock_db.get_crm_card_data.assert_called_once_with(100)

    def test_update_crm_card_offline(self, mock_db):
        da = _make_da(mock_db)
        result = da.update_crm_card(100, {'column_name': 'Готово'})
        mock_db.update_crm_card.assert_called_once()
        assert result is True

    def test_move_crm_card_offline(self, mock_db):
        """move_crm_card без API обновляет только DB."""
        da = _make_da(mock_db)
        result = da.move_crm_card(100, 'В работе')
        mock_db.update_crm_card_column.assert_called_once_with(100, 'В работе')
        assert result is True


# ==================== CRM КАРТОЧКИ: API fails ====================

class TestCrmCardsApiFails:
    """CRM карточки — API ошибка → fallback."""

    def test_get_crm_cards_fallback(self, mock_db, mock_api):
        mock_api.get_crm_cards.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        result = da.get_crm_cards('Индивидуальный')
        mock_db.get_crm_cards_by_project_type.assert_called_once()

    def test_get_crm_card_fallback(self, mock_db, mock_api):
        mock_api.get_crm_card.side_effect = APITimeoutError("timeout")
        da = _make_da(mock_db, mock_api)
        result = da.get_crm_card(100)
        mock_db.get_crm_card_data.assert_called_once_with(100)

    def test_update_crm_card_api_fail_queues(self, mock_db, mock_api):
        mock_api.update_crm_card.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.update_crm_card(100, {'column_name': 'В работе'})
        mock_db.update_crm_card.assert_called_once()
        mock_om.queue_operation.assert_called_once()
        assert result is True

    def test_move_crm_card_api_fail_queues(self, mock_db, mock_api):
        mock_api.move_crm_card.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.move_crm_card(100, 'На проверке')
        mock_db.update_crm_card_column.assert_called_once()
        mock_om.queue_operation.assert_called_once()
        assert result is True


# ==================== ПЛАТЕЖИ: API OK ====================

class TestPaymentsApiOk:
    """Платежи — API доступен."""

    def test_get_payments_for_contract_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        result = da.get_payments_for_contract(10)
        mock_api.get_payments_for_contract.assert_called_once_with(10)
        mock_db.get_payments_for_contract.assert_not_called()

    def test_create_payment_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.create_payment({'contract_id': 10, 'amount': 50000})
        mock_db.add_payment.assert_called_once()
        mock_api.create_payment.assert_called_once()

    def test_update_payment_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.update_payment(300, {'amount': 60000})
        mock_api.update_payment.assert_called_once_with(300, {'amount': 60000})
        assert result is True

    def test_delete_payment_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.delete_payment(300)
        mock_api.delete_payment.assert_called_once_with(300)

    def test_get_payment_api(self, mock_db, mock_api):
        """get_payment по ID через API."""
        da = _make_da(mock_db, mock_api)
        result = da.get_payment(300)
        mock_api.get_payment.assert_called_once_with(300)
        mock_db.get_payment.assert_not_called()

    def test_mark_payment_as_paid_api(self, mock_db, mock_api):
        """mark_payment_as_paid через API."""
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.mark_payment_as_paid(300, employee_id=5)
        mock_db.mark_payment_as_paid.assert_called_once_with(300, 5)
        mock_api.mark_payment_as_paid.assert_called_once_with(300, 5)
        assert result is True


# ==================== ПЛАТЕЖИ: Offline ====================

class TestPaymentsOffline:
    """Платежи — без API."""

    def test_get_payments_for_contract_offline(self, mock_db):
        da = _make_da(mock_db)
        result = da.get_payments_for_contract(10)
        mock_db.get_payments_for_contract.assert_called_once_with(10)
        assert len(result) == 1

    def test_create_payment_offline(self, mock_db):
        da = _make_da(mock_db)
        result = da.create_payment({'contract_id': 10, 'amount': 50000})
        mock_db.add_payment.assert_called_once()
        assert result['id'] == 300

    def test_get_payment_offline(self, mock_db):
        da = _make_da(mock_db)
        result = da.get_payment(300)
        mock_db.get_payment.assert_called_once_with(300)


# ==================== ПЛАТЕЖИ: API fails ====================

class TestPaymentsApiFails:
    """Платежи — API ошибка → fallback."""

    def test_get_payments_fallback(self, mock_db, mock_api):
        mock_api.get_payments_for_contract.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        result = da.get_payments_for_contract(10)
        mock_db.get_payments_for_contract.assert_called_once()

    def test_create_payment_api_fail_queues(self, mock_db, mock_api):
        mock_api.create_payment.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.create_payment({'contract_id': 10, 'amount': 50000})
        mock_db.add_payment.assert_called_once()
        mock_om.queue_operation.assert_called_once()

    def test_update_payment_api_fail_queues(self, mock_db, mock_api):
        mock_api.update_payment.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.update_payment(300, {'amount': 60000})
        mock_om.queue_operation.assert_called_once()
        assert result is True

    def test_delete_payment_api_fail_queues(self, mock_db, mock_api):
        mock_api.delete_payment.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.delete_payment(300)
        mock_db.delete_payment.assert_called_once_with(300)
        mock_om.queue_operation.assert_called_once()
        assert result is True

    def test_get_payment_fallback(self, mock_db, mock_api):
        """get_payment: API ошибка → fallback на DB."""
        mock_api.get_payment.side_effect = APITimeoutError("timeout")
        da = _make_da(mock_db, mock_api)
        result = da.get_payment(300)
        mock_db.get_payment.assert_called_once_with(300)


# ==================== SUPERVISION: API OK ====================

class TestSupervisionApiOk:
    """Supervision карточки — API доступен."""

    def test_get_supervision_cards_active_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        result = da.get_supervision_cards_active()
        mock_api.get_supervision_cards.assert_called_once_with(status="active")
        mock_db.get_supervision_cards_active.assert_not_called()

    def test_get_supervision_cards_archived_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        result = da.get_supervision_cards_archived()
        mock_api.get_supervision_cards.assert_called_once_with(status="archived")

    def test_get_supervision_card_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        result = da.get_supervision_card(200)
        mock_api.get_supervision_card.assert_called_once_with(200)
        mock_db.get_supervision_card_data.assert_not_called()

    def test_create_supervision_card_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.create_supervision_card({'contract_id': 10, 'column_name': 'Новый заказ'})
        mock_db.add_supervision_card.assert_called_once()
        mock_api.create_supervision_card.assert_called_once()

    def test_create_supervision_card_from_int(self, mock_db, mock_api):
        """create_supervision_card принимает int contract_id → оборачивает в dict."""
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.create_supervision_card(10)
        # Должен преобразовать int в {'contract_id': 10, 'column_name': 'Новый заказ'}
        mock_api.create_supervision_card.assert_called_once_with(
            {'contract_id': 10, 'column_name': 'Новый заказ'})

    def test_update_supervision_card_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.update_supervision_card(200, {'column_name': 'Готово'})
        mock_api.update_supervision_card.assert_called_once_with(200, {'column_name': 'Готово'})
        assert result is True

    def test_move_supervision_card_api(self, mock_db, mock_api):
        da = _make_da(mock_db, mock_api)
        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=lambda: True)):
            result = da.move_supervision_card(200, 'Завершён')
        mock_api.move_supervision_card.assert_called_once_with(200, 'Завершён')
        assert result is True


# ==================== SUPERVISION: Offline ====================

class TestSupervisionOffline:
    """Supervision — без API."""

    def test_get_supervision_cards_active_offline(self, mock_db):
        da = _make_da(mock_db)
        result = da.get_supervision_cards_active()
        mock_db.get_supervision_cards_active.assert_called_once()

    def test_get_supervision_card_offline(self, mock_db):
        da = _make_da(mock_db)
        result = da.get_supervision_card(200)
        mock_db.get_supervision_card_data.assert_called_once_with(200)

    def test_create_supervision_card_offline(self, mock_db):
        da = _make_da(mock_db)
        result = da.create_supervision_card({'contract_id': 10})
        mock_db.add_supervision_card.assert_called_once()
        assert result['id'] == 200


# ==================== SUPERVISION: API fails ====================

class TestSupervisionApiFails:
    """Supervision — API ошибка → fallback."""

    def test_get_supervision_cards_active_fallback(self, mock_db, mock_api):
        mock_api.get_supervision_cards.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        result = da.get_supervision_cards_active()
        mock_db.get_supervision_cards_active.assert_called_once()

    def test_get_supervision_card_fallback(self, mock_db, mock_api):
        mock_api.get_supervision_card.side_effect = APITimeoutError("timeout")
        da = _make_da(mock_db, mock_api)
        result = da.get_supervision_card(200)
        mock_db.get_supervision_card_data.assert_called_once_with(200)

    def test_create_supervision_card_api_fail_queues(self, mock_db, mock_api):
        mock_api.create_supervision_card.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.create_supervision_card({'contract_id': 10})
        mock_om.queue_operation.assert_called_once()

    def test_update_supervision_card_api_fail_queues(self, mock_db, mock_api):
        mock_api.update_supervision_card.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.update_supervision_card(200, {'column_name': 'Готово'})
        mock_om.queue_operation.assert_called_once()
        assert result is True

    def test_move_supervision_card_api_fail_queues(self, mock_db, mock_api):
        mock_api.move_supervision_card.side_effect = APIConnectionError("fail")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.move_supervision_card(200, 'Завершён')
        mock_db.update_supervision_card_column.assert_called_once()
        mock_om.queue_operation.assert_called_once()
        assert result is True


# ==================== OFFLINE QUEUE — бизнес-ошибки НЕ в очередь ====================

class TestQueueOperationFiltering:
    """Проверка что _queue_operation ставит в очередь только сетевые ошибки."""

    def test_business_error_not_queued(self, mock_db, mock_api):
        """Бизнес-ошибка (не APIConnectionError/APITimeoutError) НЕ ставится в очередь."""
        mock_api.create_contract.side_effect = Exception("409 Conflict")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.create_contract({'contract_number': 'X'})
        # Бизнес-ошибка — НЕ попадает в очередь
        mock_om.queue_operation.assert_not_called()

    def test_connection_error_queued(self, mock_db, mock_api):
        """APIConnectionError ставится в очередь."""
        mock_api.update_employee.side_effect = APIConnectionError("refused")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            da.update_employee(5, {'full_name': 'X'})
        mock_om.queue_operation.assert_called_once()

    def test_timeout_error_queued(self, mock_db, mock_api):
        """APITimeoutError ставится в очередь."""
        mock_api.create_payment.side_effect = APITimeoutError("timeout")
        da = _make_da(mock_db, mock_api)
        mock_om = MagicMock(is_online=lambda: True)
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            da.create_payment({'contract_id': 10, 'amount': 1000})
        mock_om.queue_operation.assert_called_once()
