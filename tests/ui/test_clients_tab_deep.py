# -*- coding: utf-8 -*-
"""
Глубокие тесты вкладки Клиенты — ClientsTab, ClientDialog, ClientSearchDialog.

Покрытие:
  - TestClientsTabCreation (3)        — создание виджета, атрибуты, data_loaded
  - TestClientsTabTable (4)           — таблица, колонки, настройки
  - TestClientsTabLoadClients (5)     — загрузка, populate_table_row, пустой список, ошибка
  - TestClientsTabSearch (4)          — apply_search по имени, телефону, email, нет результатов
  - TestClientsTabCRUDDeep (5)        — add/view/edit/delete с договорами и без
  - TestClientsTabContextMenuDeep (3) — контекстное меню, copy_selected_cells
  - TestClientsTabSortAndSync (3)     — сортировка, ensure_data_loaded, on_sync_update
  - TestClientDialogDeep (5)          — создание, fill_data, on_type_changed, save, валидация
  - TestClientSearchDialogDeep (3)    — создание, get_search_params, reset_filters
ИТОГО: 35 тестов
"""

import pytest
import logging
from unittest.mock import MagicMock, patch, PropertyMock
from PyQt5.QtWidgets import (
    QWidget, QTableWidget, QPushButton, QDialog, QMenu,
    QApplication, QLineEdit, QComboBox, QGroupBox
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QIcon

logger = logging.getLogger('tests')


# ─── Helpers ───────────────────────────────────────────────────────

def _mock_icon_loader():
    """IconLoader с реальным QIcon — для корректного создания виджетов."""
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


def _sample_clients():
    """Набор тестовых клиентов для загрузки в таблицу."""
    return [
        {
            'id': 1, 'client_type': 'Физическое лицо',
            'full_name': 'Иванов Иван Иванович', 'organization_name': '',
            'phone': '+7 (999) 111-11-11', 'email': 'ivanov@test.ru',
            'inn': ''
        },
        {
            'id': 2, 'client_type': 'Юридическое лицо',
            'full_name': '', 'organization_name': 'ООО ТестКомпания',
            'phone': '+7 (495) 222-22-22', 'email': 'info@testcompany.ru',
            'inn': '7712345678'
        },
        {
            'id': 3, 'client_type': 'Физическое лицо',
            'full_name': 'Петров Пётр Петрович', 'organization_name': '',
            'phone': '+7 (999) 333-33-33', 'email': 'petrov@mail.ru',
            'inn': ''
        },
        {
            'id': 4, 'client_type': 'Юридическое лицо',
            'full_name': '', 'organization_name': 'ИП Сидоров',
            'phone': '+7 (812) 444-44-44', 'email': 'sidorov@ip.ru',
            'inn': '7801234567'
        },
    ]


def _make_mock_da():
    """Создание MagicMock DataAccess с дефолтными возвратами."""
    da = MagicMock()
    da.get_all_clients.return_value = []
    da.get_contracts_count_by_client.return_value = 0
    da.create_client.return_value = {"id": 99}
    da.update_client.return_value = {"id": 1}
    da.delete_client.return_value = True
    da.api_client = None
    da.db = MagicMock()
    da.is_online = False
    da.prefer_local = False
    return da


def _create_clients_tab(qtbot, mock_da, employee):
    """Создание ClientsTab с замоканными зависимостями."""
    with patch('ui.clients_tab.DataAccess') as MockDA, \
         patch('ui.clients_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
        MockDA.return_value = mock_da
        from ui.clients_tab import ClientsTab
        tab = ClientsTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab


def _create_client_dialog(qtbot, parent_widget, client_data=None, view_only=False):
    """Создание ClientDialog с mock parent.
    НЕ добавляем qtbot.addWidget(dlg) — диалог дочерний, parent владеет им.
    """
    with patch('ui.clients_tab.DataAccess') as MockDA, \
         patch('ui.clients_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.clients_tab.CustomMessageBox'), \
         patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
        MockDA.return_value = parent_widget.data
        from ui.clients_tab import ClientDialog
        dlg = ClientDialog(parent_widget, client_data=client_data, view_only=view_only)
        return dlg


def _create_search_dialog(qtbot, parent_tab):
    """Создание ClientSearchDialog с mock parent.
    НЕ добавляем qtbot.addWidget(dlg) — диалог дочерний, parent владеет им.
    """
    with patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
        from ui.clients_tab import ClientSearchDialog
        dlg = ClientSearchDialog(parent_tab)
        return dlg


# ═══════════════════════════════════════════════════════════════════
# 1. Создание виджета (3 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestClientsTabCreation:
    """Инициализация ClientsTab — виджет, атрибуты, lazy-loading."""

    def test_creates_as_qwidget(self, qtbot, mock_employee_admin):
        """ClientsTab создаётся как QWidget без исключений."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        assert isinstance(tab, QWidget)

    def test_employee_attribute_stored(self, qtbot, mock_employee_admin):
        """Атрибут employee сохраняется после инициализации."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        assert tab.employee is mock_employee_admin
        assert tab.employee['position'] == 'Руководитель студии'

    def test_data_loaded_false_initially(self, qtbot, mock_employee_admin):
        """_data_loaded = False до вызова ensure_data_loaded."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        assert tab._data_loaded is False


# ═══════════════════════════════════════════════════════════════════
# 2. Таблица (4 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestClientsTabTable:
    """Таблица клиентов — колонки, настройки, виджет."""

    def test_table_exists_and_is_qtablewidget(self, qtbot, mock_employee_admin):
        """clients_table существует и является QTableWidget."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        assert hasattr(tab, 'clients_table')
        assert isinstance(tab.clients_table, QTableWidget)

    def test_table_has_7_columns(self, qtbot, mock_employee_admin):
        """Таблица содержит 7 колонок: ID, Тип, ФИО/Название, Телефон, Email, ИНН, Действия."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        assert tab.clients_table.columnCount() == 7

    def test_table_sorting_enabled(self, qtbot, mock_employee_admin):
        """Сортировка таблицы включена."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        assert tab.clients_table.isSortingEnabled() is True

    def test_table_context_menu_policy(self, qtbot, mock_employee_admin):
        """Установлена политика CustomContextMenu для копирования."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        assert tab.clients_table.contextMenuPolicy() == Qt.CustomContextMenu


# ═══════════════════════════════════════════════════════════════════
# 3. Загрузка клиентов (5 тестов)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestClientsTabLoadClients:
    """Загрузка и отображение списка клиентов в таблице."""

    def test_load_clients_populates_rows(self, qtbot, mock_employee_admin):
        """load_clients() заполняет таблицу строками из DataAccess."""
        da = _make_mock_da()
        clients = _sample_clients()
        da.get_all_clients.return_value = clients
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        tab.load_clients()
        assert tab.clients_table.rowCount() == 4

    def test_load_clients_individual_name(self, qtbot, mock_employee_admin):
        """Для физ. лица в колонке ФИО отображается full_name."""
        da = _make_mock_da()
        da.get_all_clients.return_value = [_sample_clients()[0]]
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        tab.load_clients()
        item = tab.clients_table.item(0, 2)
        assert item is not None
        assert item.text() == 'Иванов Иван Иванович'

    def test_load_clients_legal_org_name(self, qtbot, mock_employee_admin):
        """Для юр. лица в колонке ФИО отображается organization_name."""
        da = _make_mock_da()
        da.get_all_clients.return_value = [_sample_clients()[1]]
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        tab.load_clients()
        item = tab.clients_table.item(0, 2)
        assert item is not None
        assert item.text() == 'ООО ТестКомпания'

    def test_load_clients_empty_list(self, qtbot, mock_employee_admin):
        """Пустой список клиентов — таблица с 0 строк, без ошибок."""
        da = _make_mock_da()
        da.get_all_clients.return_value = []
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        tab.load_clients()
        assert tab.clients_table.rowCount() == 0

    def test_load_clients_error_shows_message(self, qtbot, mock_employee_admin):
        """Ошибка при загрузке клиентов — показывается CustomMessageBox."""
        da = _make_mock_da()
        da.get_all_clients.side_effect = Exception("Ошибка БД")
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        with patch('ui.clients_tab.CustomMessageBox') as MockMsg:
            MockMsg.return_value.exec_.return_value = None
            tab.load_clients()
            MockMsg.assert_called_once()


# ═══════════════════════════════════════════════════════════════════
# 4. Поиск и фильтрация (4 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestClientsTabSearchDeep:
    """Применение фильтров поиска через apply_search."""

    def test_search_by_name(self, qtbot, mock_employee_admin):
        """Поиск по имени — остаются только совпадения."""
        da = _make_mock_da()
        da.get_all_clients.return_value = _sample_clients()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        with patch('ui.clients_tab.CustomMessageBox'):
            tab.apply_search({'name': 'Иванов'})
        assert tab.clients_table.rowCount() == 1
        assert tab.clients_table.item(0, 2).text() == 'Иванов Иван Иванович'

    def test_search_by_phone(self, qtbot, mock_employee_admin):
        """Поиск по телефону — подстрока в номере."""
        da = _make_mock_da()
        da.get_all_clients.return_value = _sample_clients()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        with patch('ui.clients_tab.CustomMessageBox'):
            tab.apply_search({'phone': '444-44-44'})
        assert tab.clients_table.rowCount() == 1

    def test_search_by_email(self, qtbot, mock_employee_admin):
        """Поиск по email — регистронезависимый."""
        da = _make_mock_da()
        da.get_all_clients.return_value = _sample_clients()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        with patch('ui.clients_tab.CustomMessageBox'):
            tab.apply_search({'email': 'PETROV@MAIL.RU'})
        assert tab.clients_table.rowCount() == 1

    def test_search_no_results(self, qtbot, mock_employee_admin):
        """Поиск без совпадений — пустая таблица."""
        da = _make_mock_da()
        da.get_all_clients.return_value = _sample_clients()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        with patch('ui.clients_tab.CustomMessageBox'):
            tab.apply_search({'name': 'НесуществующийКлиент'})
        assert tab.clients_table.rowCount() == 0


# ═══════════════════════════════════════════════════════════════════
# 5. CRUD операции (5 тестов)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestClientsTabCRUDDeep:
    """Добавление, просмотр, редактирование и удаление клиентов."""

    def test_add_client_opens_dialog_and_reloads(self, qtbot, mock_employee_admin):
        """add_client() открывает ClientDialog, при Accepted перезагружает таблицу."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        with patch('ui.clients_tab.ClientDialog') as MockDialog, \
             patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
            MockDialog.return_value.exec_.return_value = QDialog.Accepted
            tab.add_client()
            MockDialog.assert_called_once()
            da.get_all_clients.assert_called()

    def test_view_client_opens_readonly_dialog(self, qtbot, mock_employee_admin):
        """view_client() открывает диалог с view_only=True."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        client = _sample_clients()[0]
        with patch('ui.clients_tab.ClientDialog') as MockDialog, \
             patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
            MockDialog.return_value.exec_.return_value = QDialog.Rejected
            tab.view_client(client)
            MockDialog.assert_called_once_with(tab, client, view_only=True)

    def test_edit_client_accepted_reloads_table(self, qtbot, mock_employee_admin):
        """edit_client() при Accepted вызывает повторную загрузку клиентов."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        client = _sample_clients()[1]
        with patch('ui.clients_tab.ClientDialog') as MockDialog, \
             patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
            MockDialog.return_value.exec_.return_value = QDialog.Accepted
            tab.edit_client(client)
            MockDialog.assert_called_once_with(tab, client)
            da.get_all_clients.assert_called()

    def test_delete_client_with_contracts_shows_error(self, qtbot, mock_employee_admin):
        """Удаление клиента с договорами — блокируется, показывается ошибка."""
        da = _make_mock_da()
        da.get_contracts_count_by_client.return_value = 3
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        with patch('ui.clients_tab.CustomMessageBox') as MockMsg:
            MockMsg.return_value.exec_.return_value = None
            tab.delete_client(1)
        da.delete_client.assert_not_called()

    def test_delete_client_no_contracts_confirmed(self, qtbot, mock_employee_admin):
        """Удаление клиента без договоров + подтверждение — вызывает delete_client."""
        da = _make_mock_da()
        da.get_contracts_count_by_client.return_value = 0
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        with patch('ui.custom_message_box.CustomQuestionBox') as MockQ, \
             patch('ui.clients_tab.CustomMessageBox'):
            MockQ.return_value.exec_.return_value = QDialog.Accepted
            tab.delete_client(42)
        da.delete_client.assert_called_once_with(42)


# ═══════════════════════════════════════════════════════════════════
# 6. Контекстное меню (3 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestClientsTabContextMenuDeep:
    """Контекстное меню таблицы и копирование ячеек."""

    def test_show_context_menu_creates_qmenu(self, qtbot, mock_employee_admin):
        """show_context_menu открывает QMenu."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        with patch.object(QMenu, 'exec_', return_value=None):
            tab.show_context_menu(QPoint(10, 10))

    def test_copy_selected_cells_no_selection(self, qtbot, mock_employee_admin):
        """copy_selected_cells при пустом выделении — не падает."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        # Нет выделения — метод просто возвращает None
        tab.copy_selected_cells()

    def test_copy_selected_cells_to_clipboard(self, qtbot, mock_employee_admin):
        """copy_selected_cells копирует текст выделенных ячеек в буфер."""
        da = _make_mock_da()
        da.get_all_clients.return_value = _sample_clients()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        tab.load_clients()

        # Выделяем ячейку с именем
        tab.clients_table.setCurrentCell(0, 2)
        item = tab.clients_table.item(0, 2)
        if item:
            item.setSelected(True)
            tab.copy_selected_cells()
            clipboard = QApplication.clipboard()
            assert clipboard.text() != ''


# ═══════════════════════════════════════════════════════════════════
# 7. Сортировка, lazy-loading, sync (3 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestClientsTabSortAndSync:
    """Сортировка, ленивая загрузка и обработка синхронизации."""

    def test_on_sort_changed_saves_settings(self, qtbot, mock_employee_admin):
        """on_sort_changed сохраняет колонку и порядок сортировки."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        with patch.object(tab.table_settings, 'save_sort_order') as mock_save:
            tab.on_sort_changed(3)
            mock_save.assert_called_once()
            args = mock_save.call_args[0]
            assert args[0] == 'clients'
            assert args[1] == 3

    def test_ensure_data_loaded_sets_flag(self, qtbot, mock_employee_admin):
        """ensure_data_loaded() устанавливает _data_loaded=True и вызывает load_clients."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        assert tab._data_loaded is False
        tab.ensure_data_loaded()
        assert tab._data_loaded is True
        da.get_all_clients.assert_called()

    def test_on_sync_update_reloads(self, qtbot, mock_employee_admin):
        """on_sync_update перезагружает таблицу клиентов."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        da.get_all_clients.reset_mock()
        tab.on_sync_update([{'id': 1, 'full_name': 'Обновлённый'}])
        da.get_all_clients.assert_called()


# ═══════════════════════════════════════════════════════════════════
# 8. ClientDialog — глубокие тесты (5 тестов)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestClientDialogDeep:
    """ClientDialog — создание, заполнение, переключение типа, сохранение."""

    def test_dialog_creates_without_data(self, qtbot, mock_data_access, mock_employee_admin):
        """Диалог создаётся для нового клиента (без client_data)."""
        parent = QWidget()
        parent.data = mock_data_access
        qtbot.addWidget(parent)
        dlg = _create_client_dialog(qtbot, parent)
        assert isinstance(dlg, QDialog)
        assert dlg.client_data is None

    def test_dialog_fill_data_individual(self, qtbot, mock_data_access, mock_employee_admin,
                                          sample_client_individual):
        """fill_data() заполняет поля для физического лица."""
        parent = QWidget()
        parent.data = mock_data_access
        qtbot.addWidget(parent)
        dlg = _create_client_dialog(qtbot, parent, client_data=sample_client_individual)
        # Проверяем что ФИО заполнено
        assert dlg.full_name.text() == 'Иванов Иван Иванович'
        assert dlg.client_type.currentText() == 'Физическое лицо'

    def test_dialog_fill_data_legal(self, qtbot, mock_data_access, mock_employee_admin,
                                     sample_client_legal):
        """fill_data() заполняет поля для юридического лица."""
        parent = QWidget()
        parent.data = mock_data_access
        qtbot.addWidget(parent)
        dlg = _create_client_dialog(qtbot, parent, client_data=sample_client_legal)
        assert dlg.org_name.text() == 'ООО Тест'
        assert dlg.client_type.currentText() == 'Юридическое лицо'
        assert dlg.inn.text() == '7712345678'

    def test_on_type_changed_toggles_groups(self, qtbot, mock_data_access):
        """on_type_changed переключает видимость групп полей."""
        parent = QWidget()
        parent.data = mock_data_access
        qtbot.addWidget(parent)
        dlg = _create_client_dialog(qtbot, parent)
        # Начальное состояние — Физическое лицо
        dlg.on_type_changed('Физическое лицо')
        assert not dlg.individual_group.isHidden()
        assert dlg.legal_group.isHidden()
        # Переключаем на юридическое
        dlg.on_type_changed('Юридическое лицо')
        assert dlg.individual_group.isHidden()
        assert not dlg.legal_group.isHidden()

    def test_view_only_disables_fields(self, qtbot, mock_data_access,
                                        sample_client_individual):
        """В режиме view_only поля ввода заблокированы (readOnly)."""
        parent = QWidget()
        parent.data = mock_data_access
        qtbot.addWidget(parent)
        dlg = _create_client_dialog(
            qtbot, parent, client_data=sample_client_individual, view_only=True
        )
        # Все QLineEdit должны быть readOnly
        line_edits = dlg.findChildren(QLineEdit)
        assert len(line_edits) > 0
        for le in line_edits:
            assert le.isReadOnly() is True, f"Поле {le.objectName()} не заблокировано"


# ═══════════════════════════════════════════════════════════════════
# 9. ClientSearchDialog (3 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestClientSearchDialogDeep:
    """ClientSearchDialog — создание, параметры, сброс."""

    def test_dialog_creates(self, qtbot, mock_employee_admin):
        """ClientSearchDialog создаётся без ошибок."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        dlg = _create_search_dialog(qtbot, tab)
        assert isinstance(dlg, QDialog)

    def test_get_search_params_returns_dict(self, qtbot, mock_employee_admin):
        """get_search_params() возвращает словарь с полями поиска."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        dlg = _create_search_dialog(qtbot, tab)
        # Вводим данные
        dlg.name_input.setText('Тест')
        dlg.email_input.setText('test@mail.ru')
        dlg.inn_input.setText('12345')
        params = dlg.get_search_params()
        assert params['name'] == 'Тест'
        assert params['email'] == 'test@mail.ru'
        assert params['inn'] == '12345'

    def test_reset_filters_clears_inputs(self, qtbot, mock_employee_admin):
        """reset_filters() очищает все поля ввода."""
        da = _make_mock_da()
        tab = _create_clients_tab(qtbot, da, mock_employee_admin)
        dlg = _create_search_dialog(qtbot, tab)
        dlg.name_input.setText('Иванов')
        dlg.email_input.setText('test@test.ru')
        dlg.inn_input.setText('999')
        # reset_filters вызывает parent().load_clients() и reject()
        with patch.object(dlg, 'reject'):
            dlg.reset_filters()
        assert dlg.name_input.text() == ''
        assert dlg.email_input.text() == ''
        assert dlg.inn_input.text() == ''
