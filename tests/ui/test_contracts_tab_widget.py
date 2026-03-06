# -*- coding: utf-8 -*-
"""
Тесты UI-рендеринга для ContractsTab и ContractDialog.

Покрытие:
  - ContractsTab: создание, таблица, кнопки, данные, контекстное меню, сортировка
  - ContractDialog: создание, fill_data, видимость полей, валидация
  - FormattedMoneyInput / FormattedAreaInput / FormattedPeriodInput
  - ContractSearchDialog: создание, поля, get_search_params
  - AgentDialog: создание
  - _calc_contract_term / _calc_template_contract_term: авторасчёт сроков
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QTableWidget, QPushButton, QLabel, QComboBox, QLineEdit, QMenu
from PyQt5.QtCore import Qt, QDate, QPoint
from unittest.mock import patch, MagicMock


# ========== ФИКСТУРЫ ==========

@pytest.fixture(autouse=True)
def _clear_permissions_cache():
    """Сброс кэша прав между тестами."""
    from ui.crm_tab import _user_permissions_cache
    _user_permissions_cache.clear()
    yield
    _user_permissions_cache.clear()


@pytest.fixture
def contracts_tab(qtbot, mock_data_access, mock_employee_admin):
    """ContractsTab с моками — пустая таблица."""
    with patch('ui.contracts_tab.DataAccess', return_value=mock_data_access), \
         patch('ui.contracts_tab.TableSettings') as MockTS:
        MockTS.return_value.get_sort_order.return_value = (None, None)
        from ui.contracts_tab import ContractsTab
        mock_data_access.get_all_contracts.return_value = []
        mock_data_access.get_all_clients.return_value = []
        mock_data_access.get_agent_color.return_value = None
        tab = ContractsTab(employee=mock_employee_admin, api_client=None)
        qtbot.addWidget(tab)
        yield tab


@pytest.fixture
def sample_contracts():
    """Набор тестовых договоров для заполнения таблицы."""
    return [
        {
            'id': 1,
            'contract_number': 'ИП-ПОЛ-001/26',
            'project_type': 'Индивидуальный',
            'project_subtype': 'Полный (с 3д визуализацией)',
            'client_id': 100,
            'contract_date': '2026-01-15',
            'city': 'СПБ',
            'address': 'ул. Тестовая, д.1',
            'area': 85.5,
            'total_amount': 500000,
            'advance_payment': 150000,
            'additional_payment': 200000,
            'third_payment': 150000,
            'agent_type': 'ПЕТРОВИЧ',
            'status': 'active',
            'comments': '',
            'termination_reason': '',
        },
        {
            'id': 2,
            'contract_number': 'ШП-СТД-002/26',
            'project_type': 'Шаблонный',
            'project_subtype': 'Стандарт',
            'client_id': 101,
            'contract_date': '2026-02-01',
            'city': 'МСК',
            'address': 'ул. Шаблонная, д.5',
            'area': 120,
            'total_amount': 300000,
            'advance_payment': 300000,
            'additional_payment': 0,
            'third_payment': 0,
            'agent_type': '',
            'status': 'СДАН',
            'comments': 'Готово',
            'termination_reason': '',
        },
        {
            'id': 3,
            'contract_number': 'ИП-ЭСК-003/26',
            'project_type': 'Индивидуальный',
            'project_subtype': 'Эскизный (с коллажами)',
            'client_id': 100,
            'contract_date': '2026-02-10',
            'city': 'СПБ',
            'address': 'пр. Невский, д.10',
            'area': 200,
            'total_amount': 800000,
            'advance_payment': 400000,
            'additional_payment': 400000,
            'third_payment': 0,
            'agent_type': 'ФЕСТИВАЛЬ',
            'status': 'РАСТОРГНУТ',
            'comments': '',
            'termination_reason': 'По соглашению сторон',
        },
    ]


@pytest.fixture
def sample_clients():
    """Набор тестовых клиентов."""
    return [
        {
            'id': 100,
            'client_type': 'Физическое лицо',
            'full_name': 'Иванов Иван Иванович',
            'phone': '+7 (999) 123-45-67',
            'organization_name': '',
        },
        {
            'id': 101,
            'client_type': 'Юридическое лицо',
            'full_name': '',
            'phone': '+7 (495) 987-65-43',
            'organization_name': 'ООО Тест',
        },
    ]


def _make_contracts_tab_with_data(qtbot, mock_data_access, mock_employee_admin,
                                   sample_contracts, sample_clients):
    """Вспомогательная функция: ContractsTab с данными."""
    mock_data_access.get_all_contracts.return_value = sample_contracts
    mock_data_access.get_all_clients.return_value = sample_clients
    mock_data_access.get_client.return_value = None
    mock_data_access.get_agent_color.return_value = '#FF5722'

    with patch('ui.contracts_tab.DataAccess', return_value=mock_data_access), \
         patch('ui.contracts_tab.TableSettings') as MockTS:
        MockTS.return_value.get_sort_order.return_value = (None, None)
        from ui.contracts_tab import ContractsTab
        tab = ContractsTab(employee=mock_employee_admin, api_client=None)
        qtbot.addWidget(tab)
        tab.load_contracts()
        return tab


# ========== ContractsTab: создание и структура ==========

class TestContractsTabCreation:
    """Тесты создания и структуры ContractsTab."""

    def test_widget_created(self, contracts_tab):
        """ContractsTab создаётся без ошибок."""
        assert contracts_tab is not None

    def test_table_exists(self, contracts_tab):
        """Таблица contracts_table существует и является QTableWidget."""
        assert hasattr(contracts_tab, 'contracts_table')
        assert isinstance(contracts_tab.contracts_table, QTableWidget)

    def test_table_has_11_columns(self, contracts_tab):
        """Таблица имеет 11 колонок."""
        assert contracts_tab.contracts_table.columnCount() == 11

    def test_table_header_labels(self, contracts_tab):
        """Заголовки колонок содержат ожидаемые названия."""
        headers = []
        for i in range(contracts_tab.contracts_table.columnCount()):
            headers.append(contracts_tab.contracts_table.horizontalHeaderItem(i).text().strip())
        assert '№' in headers[0]
        assert 'Дата' in headers[1]
        assert 'Адрес объекта' in headers[2]
        assert 'Статус' in headers[9]
        assert 'Действия' in headers[10]

    def test_empty_table(self, contracts_tab):
        """Пустая таблица имеет 0 строк."""
        contracts_tab.load_contracts()
        assert contracts_tab.contracts_table.rowCount() == 0

    def test_sorting_enabled(self, contracts_tab):
        """Сортировка по колонкам включена."""
        assert contracts_tab.contracts_table.isSortingEnabled()

    def test_selection_mode(self, contracts_tab):
        """Режим выделения — ExtendedSelection по строкам."""
        assert contracts_tab.contracts_table.selectionMode() == QTableWidget.ExtendedSelection
        assert contracts_tab.contracts_table.selectionBehavior() == QTableWidget.SelectRows

    def test_edit_triggers_disabled(self, contracts_tab):
        """Редактирование ячеек таблицы запрещено."""
        assert contracts_tab.contracts_table.editTriggers() == QTableWidget.NoEditTriggers

    def test_context_menu_policy(self, contracts_tab):
        """Контекстное меню подключено к таблице."""
        assert contracts_tab.contracts_table.contextMenuPolicy() == Qt.CustomContextMenu


# ========== ContractsTab: данные в таблице ==========

class TestContractsTabData:
    """Тесты заполнения таблицы данными."""

    def test_table_rows_count(self, qtbot, mock_data_access, mock_employee_admin,
                               sample_contracts, sample_clients):
        """Количество строк соответствует числу договоров."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        assert tab.contracts_table.rowCount() == 3

    def test_contract_number_in_table(self, qtbot, mock_data_access, mock_employee_admin,
                                       sample_contracts, sample_clients):
        """Номер договора отображается в первой колонке."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        assert tab.contracts_table.item(0, 0).text() == 'ИП-ПОЛ-001/26'

    def test_date_formatted(self, qtbot, mock_data_access, mock_employee_admin,
                            sample_contracts, sample_clients):
        """Дата договора отформатирована как dd.MM.yyyy."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        assert tab.contracts_table.item(0, 1).text() == '15.01.2026'

    def test_address_in_table(self, qtbot, mock_data_access, mock_employee_admin,
                               sample_contracts, sample_clients):
        """Адрес отображается в третьей колонке."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        assert tab.contracts_table.item(0, 2).text() == 'ул. Тестовая, д.1'

    def test_area_in_table(self, qtbot, mock_data_access, mock_employee_admin,
                            sample_contracts, sample_clients):
        """Площадь отображается в 4-й колонке."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        assert tab.contracts_table.item(0, 3).text() == '85.5'

    def test_city_in_table(self, qtbot, mock_data_access, mock_employee_admin,
                           sample_contracts, sample_clients):
        """Город отображается в 5-й колонке."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        assert tab.contracts_table.item(0, 4).text() == 'СПБ'

    def test_amount_formatted(self, qtbot, mock_data_access, mock_employee_admin,
                              sample_contracts, sample_clients):
        """Сумма отображается с разделителями и символом рубля."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        amount_text = tab.contracts_table.item(0, 7).text()
        assert '500' in amount_text
        assert '\u20bd' in amount_text  # символ рубля

    def test_client_name_individual(self, qtbot, mock_data_access, mock_employee_admin,
                                     sample_contracts, sample_clients):
        """Имя физ. лица отображается в колонке Клиент."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        assert tab.contracts_table.item(0, 8).text() == 'Иванов Иван Иванович'

    def test_client_name_legal(self, qtbot, mock_data_access, mock_employee_admin,
                                sample_contracts, sample_clients):
        """Название организации отображается для юр. лица."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        assert tab.contracts_table.item(1, 8).text() == 'ООО Тест'

    def test_status_sdan_green(self, qtbot, mock_data_access, mock_employee_admin,
                                sample_contracts, sample_clients):
        """Статус СДАН имеет зелёный фон."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        status_item = tab.contracts_table.item(1, 9)
        assert status_item.text() == 'СДАН'
        assert status_item.background().color() == Qt.green

    def test_status_rastorgnut_red(self, qtbot, mock_data_access, mock_employee_admin,
                                    sample_contracts, sample_clients):
        """Статус РАСТОРГНУТ имеет красный фон."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        status_item = tab.contracts_table.item(2, 9)
        assert status_item.text() == 'РАСТОРГНУТ'
        assert status_item.background().color() == Qt.red

    def test_termination_reason_tooltip(self, qtbot, mock_data_access, mock_employee_admin,
                                         sample_contracts, sample_clients):
        """РАСТОРГНУТ: tooltip содержит причину расторжения."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        status_item = tab.contracts_table.item(2, 9)
        assert 'По соглашению сторон' in status_item.toolTip()

    def test_actions_widget_exists(self, qtbot, mock_data_access, mock_employee_admin,
                                    sample_contracts, sample_clients):
        """В последней колонке размещён виджет с кнопками действий."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        actions_widget = tab.contracts_table.cellWidget(0, 10)
        assert actions_widget is not None

    def test_delete_btn_for_admin(self, qtbot, mock_data_access, mock_employee_admin,
                                  sample_contracts, sample_clients):
        """Руководитель студии видит кнопку удаления."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        actions_widget = tab.contracts_table.cellWidget(0, 10)
        buttons = actions_widget.findChildren(QPushButton)
        # Должно быть минимум 3 кнопки: просмотр, редактировать, удалить
        assert len(buttons) >= 3

    def test_no_delete_btn_for_designer(self, qtbot, mock_data_access, mock_employee_designer,
                                         sample_contracts, sample_clients):
        """Дизайнер не видит кнопку удаления."""
        mock_data_access.get_all_contracts.return_value = sample_contracts
        mock_data_access.get_all_clients.return_value = sample_clients
        mock_data_access.get_client.return_value = None
        mock_data_access.get_agent_color.return_value = None
        with patch('ui.contracts_tab.DataAccess', return_value=mock_data_access), \
             patch('ui.contracts_tab.TableSettings') as MockTS:
            MockTS.return_value.get_sort_order.return_value = (None, None)
            from ui.contracts_tab import ContractsTab
            tab = ContractsTab(employee=mock_employee_designer, api_client=None)
            qtbot.addWidget(tab)
            tab.load_contracts()
            actions_widget = tab.contracts_table.cellWidget(0, 10)
            buttons = actions_widget.findChildren(QPushButton)
            # Дизайнер: только просмотр + редактировать (2 кнопки), без удаления
            assert len(buttons) == 2

    def test_comment_icon_shown(self, qtbot, mock_data_access, mock_employee_admin,
                                 sample_contracts, sample_clients):
        """Иконка комментария отображается если comments заполнен."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        # Второй договор (index=1) имеет комментарий "Готово"
        actions_widget = tab.contracts_table.cellWidget(1, 10)
        buttons = actions_widget.findChildren(QPushButton)
        # Ожидаем: комментарий + просмотр + редактировать + удалить = 4
        assert len(buttons) >= 4


# ========== ContractsTab: контекстное меню ==========

class TestContractsTabContextMenu:
    """Тесты контекстного меню таблицы."""

    def test_show_context_menu(self, contracts_tab):
        """show_context_menu создаёт QMenu без ошибок."""
        with patch.object(QMenu, 'exec_'):
            contracts_tab.show_context_menu(QPoint(10, 10))

    def test_copy_empty_selection(self, contracts_tab):
        """copy_selected_cells не падает при пустом выделении."""
        contracts_tab.copy_selected_cells()


# ========== ContractsTab: поиск и фильтры ==========

class TestContractsTabSearch:
    """Тесты поиска и фильтрации."""

    def test_apply_search_by_number(self, qtbot, mock_data_access, mock_employee_admin,
                                     sample_contracts, sample_clients):
        """Фильтрация по номеру договора."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        tab.apply_search({'contract_number': 'ШП-СТД'})
        assert tab.contracts_table.rowCount() == 1
        assert tab.contracts_table.item(0, 0).text() == 'ШП-СТД-002/26'

    def test_apply_search_by_address(self, qtbot, mock_data_access, mock_employee_admin,
                                      sample_contracts, sample_clients):
        """Фильтрация по адресу объекта."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        tab.apply_search({'address': 'Невский'})
        assert tab.contracts_table.rowCount() == 1
        assert 'Невский' in tab.contracts_table.item(0, 2).text()

    def test_apply_search_by_client(self, qtbot, mock_data_access, mock_employee_admin,
                                     sample_contracts, sample_clients):
        """Фильтрация по имени клиента."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        tab.apply_search({'client_name': 'Иванов'})
        assert tab.contracts_table.rowCount() == 2  # У Иванова 2 договора

    def test_apply_search_no_results(self, qtbot, mock_data_access, mock_employee_admin,
                                      sample_contracts, sample_clients):
        """Фильтрация не находит совпадений."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        tab.apply_search({'contract_number': 'НЕСУЩЕСТВУЮЩИЙ'})
        assert tab.contracts_table.rowCount() == 0

    def test_apply_search_by_date_range(self, qtbot, mock_data_access, mock_employee_admin,
                                         sample_contracts, sample_clients):
        """Фильтрация по диапазону дат."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        tab.apply_search({
            'date_from': QDate(2026, 2, 1),
            'date_to': QDate(2026, 2, 28),
        })
        # Договоры от 01.02 и 10.02
        assert tab.contracts_table.rowCount() == 2

    def test_reset_filters(self, qtbot, mock_data_access, mock_employee_admin,
                           sample_contracts, sample_clients):
        """Сброс фильтров перезагружает все данные."""
        tab = _make_contracts_tab_with_data(
            qtbot, mock_data_access, mock_employee_admin,
            sample_contracts, sample_clients)
        tab.apply_search({'contract_number': 'ШП-СТД'})
        assert tab.contracts_table.rowCount() == 1
        # Сброс — через load_contracts (reset_filters вызывает QTimer)
        tab.load_contracts()
        assert tab.contracts_table.rowCount() == 3


# ========== FormattedMoneyInput ==========

class TestFormattedMoneyInput:
    """Тесты виджета ввода суммы."""

    def test_create_widget(self, qapp):
        """FormattedMoneyInput создаётся без ошибок."""
        from ui.contract_dialogs import FormattedMoneyInput
        w = FormattedMoneyInput()
        assert w is not None

    def test_initial_value_zero(self, qapp):
        """Начальное значение = 0."""
        from ui.contract_dialogs import FormattedMoneyInput
        w = FormattedMoneyInput()
        assert w.value() == 0

    def test_set_value(self, qapp):
        """setValue устанавливает значение и форматирует текст."""
        from ui.contract_dialogs import FormattedMoneyInput
        w = FormattedMoneyInput()
        w.setValue(500000)
        assert w.value() == 500000
        assert '\u20bd' in w.text()  # символ рубля
        assert '500' in w.text()

    def test_set_value_zero_clears(self, qapp):
        """setValue(0) очищает текст."""
        from ui.contract_dialogs import FormattedMoneyInput
        w = FormattedMoneyInput()
        w.setValue(0)
        assert w.value() == 0
        assert w.text() == ''

    def test_alignment_right(self, qapp):
        """Выравнивание текста по правому краю."""
        from ui.contract_dialogs import FormattedMoneyInput
        w = FormattedMoneyInput()
        assert w.alignment() == Qt.AlignRight


# ========== FormattedAreaInput ==========

class TestFormattedAreaInput:
    """Тесты виджета ввода площади."""

    def test_create_widget(self, qapp):
        """FormattedAreaInput создаётся без ошибок."""
        from ui.contract_dialogs import FormattedAreaInput
        w = FormattedAreaInput()
        assert w is not None

    def test_initial_value_zero(self, qapp):
        """Начальное значение = 0.0."""
        from ui.contract_dialogs import FormattedAreaInput
        w = FormattedAreaInput()
        assert w.value() == 0.0

    def test_set_value(self, qapp):
        """setValue устанавливает площадь и форматирует."""
        from ui.contract_dialogs import FormattedAreaInput
        w = FormattedAreaInput()
        w.setValue(85.5)
        assert w.value() == 85.5
        assert '\u043c\u00b2' in w.text()  # м²

    def test_max_area_10000(self, qapp):
        """Площадь ограничена 10000 через focusOut."""
        from ui.contract_dialogs import FormattedAreaInput
        from PyQt5.QtGui import QFocusEvent
        from PyQt5.QtCore import QEvent
        w = FormattedAreaInput()
        w.setText('15000')
        # Симулируем потерю фокуса
        w.focusOutEvent(QFocusEvent(QEvent.FocusOut))
        assert w.value() <= 10000

    def test_alignment_right(self, qapp):
        """Выравнивание текста по правому краю."""
        from ui.contract_dialogs import FormattedAreaInput
        w = FormattedAreaInput()
        assert w.alignment() == Qt.AlignRight


# ========== FormattedPeriodInput ==========

class TestFormattedPeriodInput:
    """Тесты виджета ввода срока (раб. дней)."""

    def test_create_widget(self, qapp):
        """FormattedPeriodInput создаётся без ошибок."""
        from ui.contract_dialogs import FormattedPeriodInput
        w = FormattedPeriodInput()
        assert w is not None

    def test_set_value(self, qapp):
        """setValue устанавливает срок."""
        from ui.contract_dialogs import FormattedPeriodInput
        w = FormattedPeriodInput()
        w.setValue(45)
        assert w.value() == 45
        assert 'раб. дней' in w.text()

    def test_max_period_365(self, qapp):
        """Срок ограничен 365 через focusOut."""
        from ui.contract_dialogs import FormattedPeriodInput
        from PyQt5.QtGui import QFocusEvent
        from PyQt5.QtCore import QEvent
        w = FormattedPeriodInput()
        w.setText('500')
        w.focusOutEvent(QFocusEvent(QEvent.FocusOut))
        assert w.value() <= 365


# ========== ContractDialog ==========

def _make_contract_dialog(qtbot, mock_data_access, contract_data=None, view_only=False):
    """Вспомогательная функция: создать ContractDialog с моками."""
    from PyQt5.QtWidgets import QWidget
    mock_data_access.get_all_clients.return_value = []
    mock_data_access.get_all_agents.return_value = [
        {'name': 'ПЕТРОВИЧ', 'color': '#FF5722'},
        {'name': 'ФЕСТИВАЛЬ', 'color': '#4CAF50'},
    ]
    mock_data_access.get_all_cities.return_value = [
        {'id': 1, 'name': 'СПБ'},
        {'id': 2, 'name': 'МСК'},
    ]
    mock_data_access.get_contract.return_value = contract_data
    mock_data_access.get_agent_color.return_value = None
    # Блокируем fallback на локальную БД в fill_data
    mock_data_access.db.get_contract_by_id.return_value = None

    # Реальный QWidget-родитель с атрибутом data (ContractDialog читает parent.data)
    parent_widget = QWidget()
    parent_widget.data = mock_data_access
    qtbot.addWidget(parent_widget)

    with patch('ui.contract_dialogs.YandexDiskManager'), \
         patch('ui.contract_dialogs.YANDEX_DISK_TOKEN', 'fake-token'), \
         patch('ui.contract_dialogs.DataAccess', return_value=mock_data_access):
        from ui.contract_dialogs import ContractDialog
        dialog = ContractDialog(parent_widget, contract_data=contract_data, view_only=view_only)
        # Сохраняем ссылку на parent чтобы не был удалён GC
        dialog._test_parent_ref = parent_widget
        qtbot.addWidget(dialog)
        return dialog


class TestContractDialogCreation:
    """Тесты создания ContractDialog."""

    def test_create_new_dialog(self, qtbot, mock_data_access):
        """Диалог создания нового договора открывается."""
        dialog = _make_contract_dialog(qtbot, mock_data_access)
        assert dialog is not None

    def test_create_edit_dialog(self, qtbot, mock_data_access, sample_contract_individual):
        """Диалог редактирования открывается с данными."""
        dialog = _make_contract_dialog(qtbot, mock_data_access, sample_contract_individual)
        assert dialog is not None

    def test_create_view_dialog(self, qtbot, mock_data_access, sample_contract_individual):
        """Диалог просмотра (view_only) открывается."""
        dialog = _make_contract_dialog(qtbot, mock_data_access, sample_contract_individual, view_only=True)
        assert dialog is not None
        assert dialog.view_only is True

    def test_new_dialog_has_save_button(self, qtbot, mock_data_access):
        """Диалог создания имеет кнопку Сохранить."""
        dialog = _make_contract_dialog(qtbot, mock_data_access)
        assert hasattr(dialog, 'save_btn')
        assert dialog.save_btn.text() == 'Сохранить'

    def test_view_dialog_no_save_button(self, qtbot, mock_data_access, sample_contract_individual):
        """Диалог просмотра не имеет кнопки Сохранить."""
        dialog = _make_contract_dialog(qtbot, mock_data_access, sample_contract_individual, view_only=True)
        assert not hasattr(dialog, 'save_btn')

    def test_dialog_has_client_combo(self, qtbot, mock_data_access):
        """Диалог содержит ComboBox выбора клиента."""
        dialog = _make_contract_dialog(qtbot, mock_data_access)
        assert hasattr(dialog, 'client_combo')

    def test_dialog_has_project_type(self, qtbot, mock_data_access):
        """Диалог содержит ComboBox типа проекта."""
        dialog = _make_contract_dialog(qtbot, mock_data_access)
        assert hasattr(dialog, 'project_type')

    def test_dialog_has_contract_number(self, qtbot, mock_data_access):
        """Диалог содержит поле номера договора."""
        dialog = _make_contract_dialog(qtbot, mock_data_access)
        assert hasattr(dialog, 'contract_number')
        assert isinstance(dialog.contract_number, QLineEdit)


# ========== ContractDialog: видимость полей ==========

class TestContractDialogVisibility:
    """Тесты видимости полей при переключении типа проекта."""

    def test_individual_group_visible_by_default(self, qtbot, mock_data_access):
        """По умолчанию (Индивидуальный) виден блок индивидуального проекта."""
        dialog = _make_contract_dialog(qtbot, mock_data_access)
        # Первый элемент PROJECT_TYPES = 'Индивидуальный'
        dialog.on_project_type_changed('Индивидуальный')
        # В offscreen isVisible() зависит от show() родителя,
        # используем isHidden() для проверки собственного состояния виджета
        assert not dialog.individual_group.isHidden()
        assert dialog.template_group.isHidden()

    def test_template_group_visible(self, qtbot, mock_data_access):
        """При выборе Шаблонный — виден блок шаблонного проекта."""
        dialog = _make_contract_dialog(qtbot, mock_data_access)
        dialog.on_project_type_changed('Шаблонный')
        assert dialog.individual_group.isHidden()
        assert not dialog.template_group.isHidden()

    def test_floors_visible_for_template(self, qtbot, mock_data_access):
        """Поле этажей видимо для шаблонного проекта."""
        dialog = _make_contract_dialog(qtbot, mock_data_access)
        dialog.on_project_type_changed('Шаблонный')
        assert not dialog.floors_label.isHidden()
        assert not dialog.floors_spin.isHidden()

    def test_floors_hidden_for_individual(self, qtbot, mock_data_access):
        """Поле этажей скрыто для индивидуального проекта."""
        dialog = _make_contract_dialog(qtbot, mock_data_access)
        dialog.on_project_type_changed('Индивидуальный')
        assert dialog.floors_label.isHidden()
        assert dialog.floors_spin.isHidden()

    def test_subtypes_change_for_template(self, qtbot, mock_data_access):
        """При переключении на Шаблонный подтипы обновляются."""
        dialog = _make_contract_dialog(qtbot, mock_data_access)
        dialog.on_project_type_changed('Шаблонный')
        items = [dialog.project_subtype.itemText(i) for i in range(dialog.project_subtype.count())]
        assert 'Стандарт' in items
        assert 'Проект ванной комнаты' in items

    def test_subtypes_change_for_individual(self, qtbot, mock_data_access):
        """При переключении на Индивидуальный подтипы обновляются."""
        dialog = _make_contract_dialog(qtbot, mock_data_access)
        dialog.on_project_type_changed('Шаблонный')  # сначала шаблонный
        dialog.on_project_type_changed('Индивидуальный')  # обратно
        items = [dialog.project_subtype.itemText(i) for i in range(dialog.project_subtype.count())]
        assert 'Полный (с 3д визуализацией)' in items
        assert 'Планировочный' in items


# ========== ContractDialog: fill_data ==========

class TestContractDialogFillData:
    """Тесты заполнения полей при редактировании."""

    def test_fill_contract_number(self, qtbot, mock_data_access, sample_contract_individual):
        """fill_data устанавливает номер договора."""
        dialog = _make_contract_dialog(qtbot, mock_data_access, sample_contract_individual)
        assert dialog.contract_number.text() == 'ИП-ПОЛ-12345/26'

    def test_fill_address(self, qtbot, mock_data_access, sample_contract_individual):
        """fill_data устанавливает адрес."""
        dialog = _make_contract_dialog(qtbot, mock_data_access, sample_contract_individual)
        assert dialog.address.text() == 'г. СПб, ул. Тестовая, д.1'

    def test_fill_area(self, qtbot, mock_data_access, sample_contract_individual):
        """fill_data устанавливает площадь."""
        dialog = _make_contract_dialog(qtbot, mock_data_access, sample_contract_individual)
        assert dialog.area.value() == 85.5

    def test_fill_total_amount(self, qtbot, mock_data_access, sample_contract_individual):
        """fill_data устанавливает сумму договора."""
        dialog = _make_contract_dialog(qtbot, mock_data_access, sample_contract_individual)
        assert dialog.total_amount.value() == 500000

    def test_fill_advance_payment(self, qtbot, mock_data_access, sample_contract_individual):
        """fill_data устанавливает аванс."""
        dialog = _make_contract_dialog(qtbot, mock_data_access, sample_contract_individual)
        assert dialog.advance_payment.value() == 150000

    def test_fill_contract_period(self, qtbot, mock_data_access, sample_contract_individual):
        """fill_data устанавливает срок договора."""
        dialog = _make_contract_dialog(qtbot, mock_data_access, sample_contract_individual)
        assert dialog.contract_period.value() == 45

    def test_fill_template_contract(self, qtbot, mock_data_access, sample_contract_template):
        """fill_data для шаблонного договора корректно заполняет поля."""
        dialog = _make_contract_dialog(qtbot, mock_data_access, sample_contract_template)
        assert dialog.contract_number.text() == 'ШП-СТДЗ-12346/26'
        assert dialog.area.value() == 120.0


# ========== ContractDialog: валидация ==========

class TestContractDialogValidation:
    """Тесты валидации при сохранении."""

    def test_save_empty_number_shows_warning(self, qtbot, mock_data_access):
        """Сохранение с пустым номером показывает предупреждение."""
        dialog = _make_contract_dialog(qtbot, mock_data_access)
        dialog.contract_number.setText('')
        with patch('ui.contract_dialogs.CustomMessageBox') as MockMsg:
            MockMsg.return_value.exec_.return_value = None
            dialog.save_contract()
            MockMsg.assert_called_once()
            args = MockMsg.call_args[0]
            assert 'Ошибка' in args[1] or 'номер' in args[2].lower()

    def test_save_duplicate_number_shows_error(self, qtbot, mock_data_access):
        """Сохранение с существующим номером показывает ошибку."""
        dialog = _make_contract_dialog(qtbot, mock_data_access)
        dialog.contract_number.setText('ДУП-001')
        mock_data_access.check_contract_number_exists.return_value = True
        with patch('ui.contract_dialogs.CustomMessageBox') as MockMsg:
            MockMsg.return_value.exec_.return_value = None
            dialog.save_contract()
            MockMsg.assert_called_once()
            args = MockMsg.call_args[0]
            assert 'уже существует' in args[2]


# ========== ContractDialog: авторасчёт сроков ==========

class TestContractTermCalculation:
    """Тесты авторасчёта сроков договоров."""

    def test_calc_full_project_70m(self):
        """Полный проект, площадь <= 70 м2 => 50 раб. дней."""
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_contract_term(1, 70) == 50

    def test_calc_full_project_100m(self):
        """Полный проект, площадь 71-100 м2 => 60 раб. дней."""
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_contract_term(1, 100) == 60

    def test_calc_full_project_300m(self):
        """Полный проект, площадь 251-300 м2 => 120 раб. дней."""
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_contract_term(1, 300) == 120

    def test_calc_planning_project_70m(self):
        """Планировочный проект, площадь <= 70 м2 => 10 раб. дней."""
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_contract_term(3, 70) == 10

    def test_calc_sketch_project_70m(self):
        """Эскизный проект, площадь <= 70 м2 => 30 раб. дней."""
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_contract_term(2, 70) == 30

    def test_calc_full_project_over_500m(self):
        """Полный проект, площадь > 500 м2 => максимальный срок (160 дней)."""
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_contract_term(1, 600) == 160

    def test_calc_template_standard_90m(self):
        """Шаблонный Стандарт, <= 90 м2, 1 этаж => 20 раб. дней."""
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_template_contract_term('Стандарт', 90) == 20

    def test_calc_template_standard_140m(self):
        """Шаблонный Стандарт, 91-140 м2, 1 этаж => 30 раб. дней."""
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_template_contract_term('Стандарт', 140) == 30

    def test_calc_template_standard_2floors(self):
        """Шаблонный Стандарт, <= 90 м2, 2 этажа => 30 раб. дней."""
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_template_contract_term('Стандарт', 90, floors=2) == 30

    def test_calc_template_bathroom(self):
        """Шаблонный Проект ванной комнаты => 10 раб. дней."""
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_template_contract_term('Проект ванной комнаты', 50) == 10

    def test_calc_template_bathroom_visualization(self):
        """Шаблонный Проект ванной комнаты с визуализацией => 20 раб. дней."""
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_template_contract_term(
            'Проект ванной комнаты с визуализацией', 50) == 20

    def test_calc_template_standard_visualization_90m(self):
        """Шаблонный Стандарт с визуализацией, <= 90 м2 => 45 раб. дней."""
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_template_contract_term(
            'Стандарт с визуализацией', 90) == 45


# ========== ContractSearchDialog ==========

class TestContractSearchDialog:
    """Тесты диалога поиска договоров."""

    def _make_search_dialog(self, qtbot, mock_data_access, mock_employee_admin):
        """Создать ContractSearchDialog с моками."""
        mock_data_access.get_all_contracts.return_value = []
        mock_data_access.get_all_clients.return_value = []
        mock_data_access.get_agent_color.return_value = None

        with patch('ui.contracts_tab.DataAccess', return_value=mock_data_access), \
             patch('ui.contracts_tab.TableSettings'):
            from ui.contracts_tab import ContractsTab
            parent_tab = ContractsTab(employee=mock_employee_admin, api_client=None)
            qtbot.addWidget(parent_tab)

            from ui.contract_dialogs import ContractSearchDialog
            dialog = ContractSearchDialog(parent_tab)
            qtbot.addWidget(dialog)
            return dialog

    def test_create_dialog(self, qtbot, mock_data_access, mock_employee_admin):
        """ContractSearchDialog создаётся без ошибок."""
        dialog = self._make_search_dialog(qtbot, mock_data_access, mock_employee_admin)
        assert dialog is not None

    def test_has_search_fields(self, qtbot, mock_data_access, mock_employee_admin):
        """Диалог содержит поля поиска."""
        dialog = self._make_search_dialog(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(dialog, 'contract_number_input')
        assert hasattr(dialog, 'address_input')
        assert hasattr(dialog, 'client_name_input')

    def test_has_date_filter_checkbox(self, qtbot, mock_data_access, mock_employee_admin):
        """Диалог содержит чекбокс фильтра по дате."""
        dialog = self._make_search_dialog(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(dialog, 'use_date_filter')
        assert not dialog.use_date_filter.isChecked()

    def test_date_fields_disabled_by_default(self, qtbot, mock_data_access, mock_employee_admin):
        """Поля дат отключены по умолчанию."""
        dialog = self._make_search_dialog(qtbot, mock_data_access, mock_employee_admin)
        assert not dialog.date_from.isEnabled()
        assert not dialog.date_to.isEnabled()

    def test_date_fields_enabled_on_check(self, qtbot, mock_data_access, mock_employee_admin):
        """Поля дат включаются при активации чекбокса."""
        dialog = self._make_search_dialog(qtbot, mock_data_access, mock_employee_admin)
        dialog.use_date_filter.setChecked(True)
        assert dialog.date_from.isEnabled()
        assert dialog.date_to.isEnabled()

    def test_get_search_params_empty(self, qtbot, mock_data_access, mock_employee_admin):
        """get_search_params возвращает пустые строки по умолчанию."""
        dialog = self._make_search_dialog(qtbot, mock_data_access, mock_employee_admin)
        params = dialog.get_search_params()
        assert params['contract_number'] == ''
        assert params['address'] == ''
        assert params['client_name'] == ''
        assert 'date_from' not in params

    def test_get_search_params_with_values(self, qtbot, mock_data_access, mock_employee_admin):
        """get_search_params возвращает введённые значения."""
        dialog = self._make_search_dialog(qtbot, mock_data_access, mock_employee_admin)
        dialog.contract_number_input.setText('ИП-001')
        dialog.address_input.setText('Невский')
        params = dialog.get_search_params()
        assert params['contract_number'] == 'ИП-001'
        assert params['address'] == 'Невский'

    def test_get_search_params_with_dates(self, qtbot, mock_data_access, mock_employee_admin):
        """get_search_params включает даты когда чекбокс активен."""
        dialog = self._make_search_dialog(qtbot, mock_data_access, mock_employee_admin)
        dialog.use_date_filter.setChecked(True)
        params = dialog.get_search_params()
        assert 'date_from' in params
        assert 'date_to' in params


# ========== AgentDialog ==========

class TestAgentDialog:
    """Тесты диалога управления агентами."""

    def test_create_dialog(self, qtbot, mock_data_access):
        """AgentDialog создаётся без ошибок."""
        from PyQt5.QtWidgets import QWidget
        mock_data_access.get_all_agents.return_value = [
            {'name': 'ПЕТРОВИЧ', 'color': '#FF5722'},
        ]
        parent_w = QWidget()
        parent_w.data = mock_data_access
        qtbot.addWidget(parent_w)

        from ui.contract_dialogs import AgentDialog
        dialog = AgentDialog(parent_w)
        qtbot.addWidget(dialog)
        assert dialog is not None

    def test_agent_name_input_exists(self, qtbot, mock_data_access):
        """AgentDialog содержит поле ввода имени агента."""
        from PyQt5.QtWidgets import QWidget
        mock_data_access.get_all_agents.return_value = []
        parent_w = QWidget()
        parent_w.data = mock_data_access
        qtbot.addWidget(parent_w)

        from ui.contract_dialogs import AgentDialog
        dialog = AgentDialog(parent_w)
        qtbot.addWidget(dialog)
        assert hasattr(dialog, 'agent_name_input')
        assert isinstance(dialog.agent_name_input, QLineEdit)
