# -*- coding: utf-8 -*-
"""
Расширенные тесты взаимодействий вкладки Клиенты — ClientsTab.

Покрытие:
  - TestClientsTabInit (4)          — инициализация виджета, таблица, кнопки
  - TestClientsTabLoadData (4)      — загрузка клиентов, populate_table_row
  - TestClientsTabSearch (4)        — поиск, фильтрация по параметрам
  - TestClientsTabCRUD (5)          — добавление, редактирование, удаление
  - TestClientsTabContextMenu (3)   — контекстное меню, копирование
  - TestClientsTabSorting (2)       — сортировка, сохранение настроек
ИТОГО: 22 теста
"""

import pytest
import logging
from unittest.mock import MagicMock, patch, call
from PyQt5.QtWidgets import (
    QWidget, QTableWidget, QPushButton, QDialog, QMenu, QApplication
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QIcon

logger = logging.getLogger('tests')


# ─── Helpers ───────────────────────────────────────────────────────

def _mock_icon_loader():
    """IconLoader с реальным QIcon."""
    mock = MagicMock()
    mock.load = MagicMock(return_value=QIcon())
    mock.create_icon_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    mock.create_action_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    mock.get_icon_path = MagicMock(return_value='')
    return mock


def _create_clients_tab(qtbot, mock_data_access, employee):
    """Создание ClientsTab с полностью замоканными зависимостями."""
    mock_data_access.api_client = None
    mock_data_access.get_contracts_count_by_client = MagicMock(return_value=0)

    with patch('ui.clients_tab.DataAccess') as MockDA, \
         patch('ui.clients_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
        MockDA.return_value = mock_data_access
        from ui.clients_tab import ClientsTab
        tab = ClientsTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab


def _create_client_dialog(qtbot, parent_widget, client_data=None, view_only=False):
    """Создание ClientDialog с mock parent."""
    with patch('ui.clients_tab.DataAccess') as MockDA, \
         patch('ui.clients_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.clients_tab.CustomMessageBox'), \
         patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
        MockDA.return_value = parent_widget.data
        from ui.clients_tab import ClientDialog
        dlg = ClientDialog(parent_widget, client_data=client_data, view_only=view_only)
        qtbot.addWidget(dlg)
        return dlg


def _sample_clients():
    """Набор тестовых клиентов для загрузки в таблицу."""
    return [
        {
            'id': 1, 'client_type': 'Физическое лицо',
            'full_name': 'Иванов Иван', 'organization_name': '',
            'phone': '+7 (999) 111-11-11', 'email': 'ivanov@test.ru',
            'inn': ''
        },
        {
            'id': 2, 'client_type': 'Юридическое лицо',
            'full_name': '', 'organization_name': 'ООО Тест',
            'phone': '+7 (495) 222-22-22', 'email': 'info@test.ru',
            'inn': '7712345678'
        },
        {
            'id': 3, 'client_type': 'Физическое лицо',
            'full_name': 'Петров Пётр', 'organization_name': '',
            'phone': '+7 (999) 333-33-33', 'email': 'petrov@test.ru',
            'inn': ''
        },
    ]


# ========== 1. Инициализация виджета (4 теста) ==========

@pytest.mark.ui
class TestClientsTabInit:
    """Инициализация ClientsTab: таблица, колонки, кнопки, DataAccess."""

    def test_tab_creates_as_qwidget(self, qtbot, mock_data_access, mock_employee_admin):
        """Вкладка создаётся как QWidget без ошибок."""
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)
        assert isinstance(tab, QWidget)

    def test_table_has_7_columns(self, qtbot, mock_data_access, mock_employee_admin):
        """Таблица клиентов содержит 7 колонок (ID, Тип, ФИО, Телефон, Email, ИНН, Действия)."""
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'clients_table')
        assert isinstance(tab.clients_table, QTableWidget)
        assert tab.clients_table.columnCount() == 7

    def test_buttons_exist(self, qtbot, mock_data_access, mock_employee_admin):
        """На панели есть минимум 4 кнопки (поиск, сброс, обновить, добавить)."""
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)
        buttons = tab.findChildren(QPushButton)
        assert len(buttons) >= 4

    def test_data_access_assigned(self, qtbot, mock_data_access, mock_employee_admin):
        """DataAccess назначен и не None."""
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.data is not None
        assert tab.data is mock_data_access


# ========== 2. Загрузка данных (4 теста) ==========

@pytest.mark.ui
class TestClientsTabLoadData:
    """Загрузка и отображение клиентов в таблице."""

    def test_load_clients_populates_table(self, qtbot, mock_data_access, mock_employee_admin):
        """load_clients() заполняет таблицу данными из DataAccess."""
        clients = _sample_clients()
        mock_data_access.get_all_clients.return_value = clients
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_clients()
        assert tab.clients_table.rowCount() == 3

    def test_load_clients_shows_name_for_individual(self, qtbot, mock_data_access, mock_employee_admin):
        """Для физ.лица в колонке ФИО/Название отображается full_name."""
        clients = _sample_clients()
        mock_data_access.get_all_clients.return_value = clients
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_clients()
        item = tab.clients_table.item(0, 2)  # Колонка ФИО/Название
        assert item is not None
        assert item.text() == 'Иванов Иван'

    def test_load_clients_shows_org_name_for_legal(self, qtbot, mock_data_access, mock_employee_admin):
        """Для юр.лица в колонке ФИО/Название отображается organization_name."""
        clients = _sample_clients()
        mock_data_access.get_all_clients.return_value = clients
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_clients()
        # Таблица может быть отсортирована, ищем по содержимому
        found = False
        for row in range(tab.clients_table.rowCount()):
            item = tab.clients_table.item(row, 2)
            if item and item.text() == 'ООО Тест':
                found = True
                break
        assert found, "Не найдена строка с 'ООО Тест' в таблице"

    def test_load_empty_clients_list(self, qtbot, mock_data_access, mock_employee_admin):
        """Пустой список клиентов — таблица с 0 строками, без ошибок."""
        mock_data_access.get_all_clients.return_value = []
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_clients()
        assert tab.clients_table.rowCount() == 0


# ========== 3. Поиск и фильтрация (4 теста) ==========

@pytest.mark.ui
class TestClientsTabSearch:
    """Поиск клиентов через apply_search с параметрами."""

    def test_search_by_name_filters_results(self, qtbot, mock_data_access, mock_employee_admin):
        """Поиск по имени фильтрует таблицу — остаётся только совпадение."""
        clients = _sample_clients()
        mock_data_access.get_all_clients.return_value = clients
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch.object(tab, '_show_search_result_message', create=True):
            with patch('ui.clients_tab.CustomMessageBox'):
                tab.apply_search({'name': 'Иванов'})

        assert tab.clients_table.rowCount() == 1
        assert tab.clients_table.item(0, 2).text() == 'Иванов Иван'

    def test_search_by_phone(self, qtbot, mock_data_access, mock_employee_admin):
        """Поиск по телефону фильтрует данные."""
        clients = _sample_clients()
        mock_data_access.get_all_clients.return_value = clients
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch('ui.clients_tab.CustomMessageBox'):
            tab.apply_search({'phone': '222-22-22'})

        assert tab.clients_table.rowCount() == 1

    def test_search_by_inn(self, qtbot, mock_data_access, mock_employee_admin):
        """Поиск по ИНН фильтрует данные."""
        clients = _sample_clients()
        mock_data_access.get_all_clients.return_value = clients
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch('ui.clients_tab.CustomMessageBox'):
            tab.apply_search({'inn': '7712345678'})

        assert tab.clients_table.rowCount() == 1

    def test_search_no_match_empty_table(self, qtbot, mock_data_access, mock_employee_admin):
        """Поиск без совпадений — таблица пуста."""
        clients = _sample_clients()
        mock_data_access.get_all_clients.return_value = clients
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch('ui.clients_tab.CustomMessageBox'):
            tab.apply_search({'name': 'Несуществующий'})

        assert tab.clients_table.rowCount() == 0


# ========== 4. CRUD операции (5 тестов) ==========

@pytest.mark.ui
class TestClientsTabCRUD:
    """Добавление, редактирование и удаление клиентов."""

    def test_add_client_opens_dialog(self, qtbot, mock_data_access, mock_employee_admin):
        """add_client() открывает ClientDialog, при accept — перезагружает таблицу."""
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch('ui.clients_tab.ClientDialog') as MockDialog, \
             patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
            MockDialog.return_value.exec_.return_value = QDialog.Accepted
            tab.add_client()
            MockDialog.assert_called_once()
            mock_data_access.get_all_clients.assert_called()

    def test_view_client_opens_readonly(self, qtbot, mock_data_access, mock_employee_admin):
        """view_client() открывает ClientDialog с view_only=True."""
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)
        client = _sample_clients()[0]

        with patch('ui.clients_tab.ClientDialog') as MockDialog, \
             patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
            MockDialog.return_value.exec_.return_value = QDialog.Rejected
            tab.view_client(client)
            MockDialog.assert_called_once_with(tab, client, view_only=True)

    def test_edit_client_opens_dialog(self, qtbot, mock_data_access, mock_employee_admin):
        """edit_client() открывает ClientDialog для редактирования."""
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)
        client = _sample_clients()[0]

        with patch('ui.clients_tab.ClientDialog') as MockDialog, \
             patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
            MockDialog.return_value.exec_.return_value = QDialog.Accepted
            tab.edit_client(client)
            MockDialog.assert_called_once_with(tab, client)
            mock_data_access.get_all_clients.assert_called()

    def test_delete_client_with_contracts_blocked(self, qtbot, mock_data_access, mock_employee_admin):
        """Удаление клиента с договорами — показ ошибки, DataAccess.delete_client не вызван."""
        mock_data_access.get_contracts_count_by_client.return_value = 2
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch('ui.clients_tab.CustomMessageBox') as MockMsg, \
             patch('ui.custom_message_box.CustomQuestionBox'):
            MockMsg.return_value.exec_.return_value = None
            tab.delete_client(1)

        mock_data_access.delete_client.assert_not_called()

    def test_delete_client_confirmed_calls_data(self, qtbot, mock_data_access, mock_employee_admin):
        """Удаление клиента без договоров + подтверждение — вызывает DataAccess.delete_client."""
        mock_data_access.get_contracts_count_by_client.return_value = 0
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch('ui.custom_message_box.CustomQuestionBox') as MockQ, \
             patch('ui.clients_tab.CustomMessageBox'):
            MockQ.return_value.exec_.return_value = QDialog.Accepted
            tab.delete_client(42)

        mock_data_access.delete_client.assert_called_once_with(42)


# ========== 5. Контекстное меню (3 теста) ==========

@pytest.mark.ui
class TestClientsTabContextMenu:
    """Контекстное меню и копирование ячеек."""

    def test_context_menu_policy_set(self, qtbot, mock_data_access, mock_employee_admin):
        """Таблица использует CustomContextMenu."""
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.clients_table.contextMenuPolicy() == Qt.CustomContextMenu

    def test_show_context_menu_creates_menu(self, qtbot, mock_data_access, mock_employee_admin):
        """show_context_menu создаёт QMenu с действием 'Копировать'."""
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch.object(QMenu, 'exec_', return_value=None) as mock_exec:
            tab.show_context_menu(QPoint(10, 10))
            mock_exec.assert_called_once()

    def test_copy_selected_cells_to_clipboard(self, qtbot, mock_data_access, mock_employee_admin):
        """copy_selected_cells копирует выделенный текст в буфер обмена."""
        clients = _sample_clients()
        mock_data_access.get_all_clients.return_value = clients
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_clients()

        # Выбираем ячейку
        tab.clients_table.setCurrentCell(0, 2)
        tab.clients_table.item(0, 2).setSelected(True)
        tab.copy_selected_cells()

        clipboard = QApplication.clipboard()
        assert 'Иванов Иван' in clipboard.text()


# ========== 6. Сортировка (2 теста) ==========

@pytest.mark.ui
class TestClientsTabSorting:
    """Сортировка таблицы и сохранение настроек."""

    def test_sorting_enabled(self, qtbot, mock_data_access, mock_employee_admin):
        """Сортировка таблицы включена."""
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.clients_table.isSortingEnabled()

    def test_on_sort_changed_saves_settings(self, qtbot, mock_data_access, mock_employee_admin):
        """on_sort_changed сохраняет колонку и направление сортировки."""
        tab = _create_clients_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch.object(tab.table_settings, 'save_sort_order') as mock_save:
            tab.on_sort_changed(2)
            mock_save.assert_called_once()
            args = mock_save.call_args[0]
            assert args[0] == 'clients'
            assert args[1] == 2
