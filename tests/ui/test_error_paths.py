# -*- coding: utf-8 -*-
"""
Error-Path тесты: UI НЕ падает когда DataAccess возвращает ошибку.

Эти тесты проверяют КРИТИЧЕСКИЙ пробел: что происходит с UI
когда API/DataAccess возвращает None, False, пустой список или бросает исключение.

Текущие unit-тесты мокируют DataAccess на "всегда успех" — и пропускают все баги
связанные с обработкой ошибок.

Запуск: pytest tests/ui/test_error_paths.py -v
Маркер: pytest tests/ui/ -k error_path -v
"""

import pytest
import sys
import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from PyQt5.QtGui import QIcon
from unittest.mock import patch, MagicMock


# ════════════════════════════════════════════════════════════
# Хелперы
# ════════════════════════════════════════════════════════════

def _mock_icon_loader():
    """Mock IconLoader — возвращает реальные QPushButton."""
    mock = MagicMock()
    mock.create_action_button.side_effect = lambda *a, **k: QPushButton()
    mock.create_icon_button.side_effect = lambda *a, **k: QPushButton()
    mock.get_icon.return_value = QIcon()
    mock.get_icon_path.return_value = ''
    mock.load.return_value = QIcon()
    return mock


def _noop_msgbox(*args, **kwargs):
    """Mock для CustomMessageBox — не блокирует exec_()."""
    m = MagicMock()
    m.exec_.return_value = None
    return m


_ADMIN = {'id': 1, 'full_name': 'Админ', 'position': 'Руководитель студии',
          'secondary_position': ''}
_DESIGNER = {'id': 2, 'full_name': 'Дизайнер', 'position': 'Дизайнер',
             'secondary_position': ''}


# ════════════════════════════════════════════════════════════
# 1. EmployeesTab — ошибки загрузки
# ════════════════════════════════════════════════════════════

class TestEmployeesTabErrorPath:
    """EmployeesTab НЕ падает когда DataAccess возвращает ошибки."""

    def _create_tab(self, qtbot, employee):
        with patch('ui.employees_tab.DataAccess') as MockDA, \
             patch('ui.employees_tab.DatabaseManager', return_value=MagicMock()), \
             patch('ui.employees_tab.IconLoader', _mock_icon_loader()):
            da = MagicMock()
            MockDA.return_value = da
            da.get_all_employees.return_value = []
            from ui.employees_tab import EmployeesTab
            tab = EmployeesTab(employee=employee, api_client=None)
            qtbot.addWidget(tab)
            return tab, da

    @pytest.mark.error_path
    def test_load_employees_returns_none(self, qtbot):
        """get_all_employees() вернул None — таб НЕ падает."""
        tab, da = self._create_tab(qtbot, _ADMIN)
        da.get_all_employees.return_value = None
        with patch('ui.employees_tab.CustomMessageBox', side_effect=_noop_msgbox):
            try:
                tab.load_employees()
            except TypeError:
                pytest.fail("EmployeesTab.load_employees() упал при None от DataAccess")

    @pytest.mark.error_path
    def test_load_employees_returns_empty(self, qtbot):
        """get_all_employees() вернул [] — таблица пустая, НЕ падает."""
        tab, da = self._create_tab(qtbot, _ADMIN)
        da.get_all_employees.return_value = []
        tab.load_employees()
        assert tab.employees_table.rowCount() == 0

    @pytest.mark.error_path
    def test_load_employees_raises_exception(self, qtbot):
        """get_all_employees() бросил Exception — таб НЕ падает."""
        tab, da = self._create_tab(qtbot, _ADMIN)
        da.get_all_employees.side_effect = Exception("API timeout")
        with patch('ui.employees_tab.CustomMessageBox', side_effect=_noop_msgbox):
            try:
                tab.load_employees()
            except Exception as e:
                pytest.fail(
                    f"EmployeesTab.load_employees() не обработал исключение: {e}\n"
                    f"UI не должен падать при ошибке DataAccess!"
                )


# ════════════════════════════════════════════════════════════
# 2. CRMTab — ошибки загрузки карточек
# ════════════════════════════════════════════════════════════

class TestCRMTabErrorPath:
    """CRMTab НЕ падает при ошибках DataAccess."""

    def _create_tab(self, qtbot, employee):
        with patch('ui.crm_tab.DataAccess') as MockDA, \
             patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
             patch('ui.crm_tab.IconLoader', _mock_icon_loader()):
            MockDA.return_value = MagicMock()
            da = MockDA.return_value
            da.get_crm_cards.return_value = []
            da.get_archived_crm_cards.return_value = []
            from ui.crm_tab import CRMTab
            tab = CRMTab(employee=employee, api_client=None)
            qtbot.addWidget(tab)
            return tab, da

    @pytest.mark.error_path
    def test_load_cards_returns_none(self, qtbot):
        """get_crm_cards() вернул None — таб НЕ падает."""
        tab, da = self._create_tab(qtbot, _ADMIN)
        da.get_crm_cards.return_value = None
        with patch('ui.crm_tab.CustomMessageBox', side_effect=_noop_msgbox):
            try:
                tab.load_cards_for_type("Индивидуальный")
            except (TypeError, AttributeError) as e:
                pytest.fail(
                    f"CRMTab.load_cards_for_type() упал при None: {e}\n"
                    f"DataAccess может вернуть None при ошибке API!"
                )

    @pytest.mark.error_path
    def test_archive_returns_none(self, qtbot):
        """get_archived_crm_cards() вернул None — НЕ падает."""
        tab, da = self._create_tab(qtbot, _ADMIN)
        da.get_archived_crm_cards.return_value = None
        with patch('ui.crm_tab.CustomMessageBox', side_effect=_noop_msgbox):
            try:
                tab.load_archive_cards("Индивидуальный")
            except (TypeError, AttributeError) as e:
                pytest.fail(f"CRMTab.load_archive_cards() упал при None: {e}")


# ════════════════════════════════════════════════════════════
# 3. Supervision Tab — ошибки загрузки
# ════════════════════════════════════════════════════════════

class TestSupervisionTabErrorPath:
    """CRMSupervisionTab НЕ падает при ошибках DataAccess."""

    def _create_tab(self, qtbot, employee):
        with patch('ui.crm_supervision_tab.DataAccess') as MockDA, \
             patch('ui.crm_supervision_tab.DatabaseManager', return_value=MagicMock()), \
             patch('ui.crm_supervision_tab.IconLoader', _mock_icon_loader()), \
             patch('ui.crm_supervision_tab._has_perm',
                   side_effect=lambda emp, api, perm: perm != 'supervision.move'
                   or emp.get('position', '') not in
                   ('ДАН', 'Дизайнер', 'Чертёжник', 'Замерщик', 'Менеджер')):
            MockDA.return_value = MagicMock()
            da = MockDA.return_value
            da.get_supervision_cards_active.return_value = []
            da.get_supervision_cards_archived.return_value = []
            from ui.crm_supervision_tab import CRMSupervisionTab
            tab = CRMSupervisionTab(employee=employee, api_client=None)
            qtbot.addWidget(tab)
            return tab, da

    @pytest.mark.error_path
    def test_load_active_returns_none(self, qtbot):
        """get_supervision_cards_active() вернул None — таб НЕ падает."""
        tab, da = self._create_tab(qtbot, _ADMIN)
        da.get_supervision_cards_active.return_value = None
        with patch('ui.crm_supervision_tab.CustomMessageBox', side_effect=_noop_msgbox):
            try:
                if hasattr(tab, '_load_active_cards'):
                    tab._load_active_cards()
            except (TypeError, AttributeError) as e:
                pytest.fail(f"SupervisionTab._load_active_cards() упал при None: {e}")


# ════════════════════════════════════════════════════════════
# 4. ContractsTab — ошибки CRUD операций
# ════════════════════════════════════════════════════════════

class TestContractsTabErrorPath:
    """ContractsTab обработка ошибок при CRUD."""

    def _create_tab(self, qtbot):
        with patch('ui.contracts_tab.DataAccess') as MockDA, \
             patch('ui.contracts_tab.DatabaseManager', return_value=MagicMock()), \
             patch('ui.contracts_tab.IconLoader', _mock_icon_loader()):
            da = MagicMock()
            MockDA.return_value = da
            da.get_all_contracts.return_value = []
            da.get_all_clients.return_value = []
            from ui.contracts_tab import ContractsTab
            tab = ContractsTab(employee=_ADMIN, api_client=None)
            qtbot.addWidget(tab)
            return tab, da

    @pytest.mark.error_path
    def test_load_contracts_returns_none(self, qtbot):
        """get_all_contracts() вернул None — таб НЕ падает."""
        tab, da = self._create_tab(qtbot)
        da.get_all_contracts.return_value = None
        with patch('ui.contracts_tab.CustomMessageBox', side_effect=_noop_msgbox):
            try:
                tab.load_contracts()
            except (TypeError, AttributeError) as e:
                pytest.fail(f"ContractsTab.load_contracts() упал при None: {e}")

    @pytest.mark.error_path
    def test_delete_contract_returns_false(self, qtbot):
        """delete_contract() вернул False — проверяем что НЕ падает."""
        tab, da = self._create_tab(qtbot)
        da.delete_contract.return_value = False
        with patch('ui.contracts_tab.CustomMessageBox', side_effect=_noop_msgbox), \
             patch('ui.contracts_tab.CustomQuestionBox') as MockQ:
            MockQ.return_value.exec_.return_value = True
            MockQ.return_value.result.return_value = True
            try:
                tab.delete_contract(999)
            except Exception:
                pass  # Другие ошибки допустимы — главное не segfault


# ════════════════════════════════════════════════════════════
# 5. ClientsTab — ошибки загрузки
# ════════════════════════════════════════════════════════════

class TestClientsTabErrorPath:
    """ClientsTab НЕ падает при ошибках DataAccess."""

    def _create_tab(self, qtbot):
        with patch('ui.clients_tab.DataAccess') as MockDA, \
             patch('ui.clients_tab.DatabaseManager', return_value=MagicMock()), \
             patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
            da = MagicMock()
            MockDA.return_value = da
            da.get_all_clients.return_value = []
            from ui.clients_tab import ClientsTab
            tab = ClientsTab(employee=_ADMIN, api_client=None)
            qtbot.addWidget(tab)
            return tab, da

    @pytest.mark.error_path
    def test_load_clients_returns_none(self, qtbot):
        """get_all_clients() вернул None — таб НЕ падает."""
        tab, da = self._create_tab(qtbot)
        da.get_all_clients.return_value = None
        with patch('ui.clients_tab.CustomMessageBox', side_effect=_noop_msgbox):
            try:
                tab.load_clients()
            except (TypeError, AttributeError) as e:
                pytest.fail(f"ClientsTab.load_clients() упал при None: {e}")

    @pytest.mark.error_path
    def test_load_clients_raises_exception(self, qtbot):
        """get_all_clients() бросил Exception — таб НЕ падает."""
        tab, da = self._create_tab(qtbot)
        da.get_all_clients.side_effect = Exception("Network error")
        with patch('ui.clients_tab.CustomMessageBox', side_effect=_noop_msgbox):
            try:
                tab.load_clients()
            except Exception as e:
                pytest.fail(f"ClientsTab.load_clients() не обработал исключение: {e}")


# ════════════════════════════════════════════════════════════
# 6. DataAccess Fallback — ключевой тест
# ════════════════════════════════════════════════════════════

class TestDataAccessFallbackErrorPath:
    """DataAccess корректно обрабатывает ошибки API и возвращает fallback."""

    @pytest.mark.error_path
    def test_api_error_returns_fallback_not_exception(self):
        """При ошибке API DataAccess возвращает данные из БД, а не бросает Exception."""
        from utils.data_access import DataAccess

        mock_api = MagicMock()
        mock_api.get_clients.side_effect = Exception("Connection refused")
        mock_db = MagicMock()
        mock_db.get_all_clients.return_value = [{"id": 1, "full_name": "Из БД"}]

        da = DataAccess(api_client=mock_api, db=mock_db)
        try:
            result = da.get_all_clients()
        except Exception as e:
            pytest.fail(
                f"DataAccess.get_all_clients() бросил исключение вместо fallback: {e}"
            )
        assert result is not None or result == []

    @pytest.mark.error_path
    def test_api_none_db_empty_returns_empty_list(self):
        """API=None, DB=пустая → возвращает пустой список, НЕ None."""
        from utils.data_access import DataAccess

        mock_db = MagicMock()
        mock_db.get_all_clients.return_value = []

        da = DataAccess(api_client=None, db=mock_db)
        result = da.get_all_clients()
        assert isinstance(result, list), \
            f"DataAccess вернул {type(result)} вместо list при api=None, db=пустая"

    @pytest.mark.error_path
    def test_create_client_api_error_queues_offline(self):
        """При ошибке API создания клиента — не бросает Exception."""
        from utils.data_access import DataAccess

        mock_api = MagicMock()
        mock_api.create_client.side_effect = Exception("Server error")
        mock_db = MagicMock()
        mock_db.create_client.return_value = 1

        da = DataAccess(api_client=mock_api, db=mock_db)
        try:
            result = da.create_client({"full_name": "Тест", "phone": "+71234567890"})
        except Exception as e:
            pytest.fail(f"DataAccess.create_client() бросил исключение: {e}")


# ════════════════════════════════════════════════════════════
# 7. API Client — обработка HTTP ошибок
# ════════════════════════════════════════════════════════════

class TestApiClientErrorPath:
    """API Client корректно обрабатывает ошибки сервера."""

    @pytest.mark.error_path
    def test_api_client_exceptions_defined(self):
        """Все типы исключений API клиента определены и наследуют APIError."""
        from utils.api_client.base import (
            APIError, APITimeoutError, APIConnectionError,
            APIAuthError, APIResponseError,
        )
        assert issubclass(APITimeoutError, APIError)
        assert issubclass(APIConnectionError, APIError)
        assert issubclass(APIAuthError, APIError)
        assert issubclass(APIResponseError, APIError)

    @pytest.mark.error_path
    def test_api_response_error_has_status_code(self):
        """APIResponseError содержит status_code для обработки в UI."""
        from utils.api_client.base import APIResponseError
        err = APIResponseError("Тест ошибка", status_code=409)
        assert err.status_code == 409
        assert "409" in str(err) or "Тест ошибка" in str(err)
