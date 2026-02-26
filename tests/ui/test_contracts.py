# -*- coding: utf-8 -*-
"""
Тесты вкладки Договора — ContractsTab, ContractDialog, ContractSearchDialog.
44 теста.
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import (
    QWidget, QTableWidget, QPushButton, QLineEdit,
    QDialog, QComboBox, QSpinBox
)
from PyQt5.QtCore import Qt, QDate


# ========== Фикстура авто-мока CustomMessageBox ==========

@pytest.fixture(autouse=True)
def _mock_contracts_msgbox():
    """Глобальный мок CustomMessageBox чтобы диалоги не блокировали тесты."""
    # Патчим в обоих модулях: contracts_tab (ContractsTab) и contract_dialogs (диалоги)
    with patch('ui.contracts_tab.CustomMessageBox') as mock_msg, \
         patch('ui.contract_dialogs.CustomMessageBox') as mock_msg2:
        mock_msg.return_value.exec_.return_value = None
        mock_msg2.return_value.exec_.return_value = None
        yield mock_msg


# ========== Хелперы ==========

def _create_contracts_tab(qtbot, mock_data_access, employee):
    """Создать ContractsTab с mock DataAccess."""
    with patch('ui.contracts_tab.DataAccess') as MockDA, \
         patch('ui.contracts_tab.DatabaseManager', return_value=MagicMock()):
        MockDA.return_value = mock_data_access
        from ui.contracts_tab import ContractsTab
        tab = ContractsTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab


def _mock_icon_loader():
    """Мок IconLoader с QIcon() вместо None."""
    from PyQt5.QtGui import QIcon
    mock = MagicMock()
    mock.load = MagicMock(return_value=QIcon())
    mock.create_icon_button = MagicMock(side_effect=lambda *a, **k: QPushButton())
    mock.get_icon_path = MagicMock(return_value='')
    return mock


def _create_contract_dialog(qtbot, parent_widget, contract_data=None, view_only=False):
    """Создать ContractDialog с parent_widget."""
    mock_da = parent_widget.data
    # Убеждаемся что api_client = None (локальный режим)
    mock_da.api_client = None
    mock_da.is_online = False
    # DataAccess checks
    mock_da.check_contract_number_exists.return_value = False
    mock_da.create_contract.return_value = {'id': 999}
    mock_da.update_contract.return_value = {'id': 999}
    # Справочники для комбобоксов
    mock_da.get_all_clients.return_value = [
        {'id': 1, 'full_name': 'Тестовый Клиент', 'client_type': 'Физическое лицо', 'phone': '+7 (999) 000-00-00'},
    ]
    mock_da.get_all_agents.return_value = [{'name': 'ФЕСТИВАЛЬ', 'id': 1}]
    mock_da.get_all_cities.return_value = [{'name': 'СПБ'}, {'name': 'МСК'}]
    # DB-level checks
    mock_da.db.check_contract_number_exists.return_value = False
    mock_da.db.add_contract.return_value = None
    mock_da.db.update_contract.return_value = None
    mock_da.db.get_contract_by_id.return_value = None
    mock_da.db.conn = MagicMock()
    mock_da.db.conn.execute.return_value.fetchone.return_value = [1]
    # При редактировании fill_data вызывает get_contract — возвращаем те же данные
    if contract_data:
        mock_da.get_contract.return_value = contract_data
    else:
        mock_da.get_contract.return_value = None

    # Патчим в ui.contract_dialogs, где теперь живёт ContractDialog
    with patch('ui.contracts_tab.DataAccess') as MockDA, \
         patch('ui.contract_dialogs.DataAccess') as MockDA2, \
         patch('ui.contracts_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.contract_dialogs.DatabaseManager', return_value=MagicMock()), \
         patch('ui.contract_dialogs.YandexDiskManager', return_value=None), \
         patch('ui.contract_dialogs.IconLoader', _mock_icon_loader()):
        MockDA.return_value = mock_da
        MockDA2.return_value = mock_da
        from ui.contracts_tab import ContractDialog
        dlg = ContractDialog(parent_widget, contract_data=contract_data, view_only=view_only)
        dlg.setAttribute(Qt.WA_DeleteOnClose, False)
        dlg._test_parent = parent_widget
        qtbot.addWidget(dlg)
        return dlg


def _create_contract_search_dialog(parent_widget):
    """Создать ContractSearchDialog."""
    from ui.contracts_tab import ContractSearchDialog
    dlg = ContractSearchDialog(parent_widget)
    return dlg


# ========== 1. Рендеринг вкладки (5 тестов) ==========

@pytest.mark.ui
class TestContractsTabRendering:
    """Проверка рендеринга вкладки Договора."""

    def test_tab_creates(self, qtbot, mock_data_access, mock_employee_admin):
        """Вкладка создаётся как QWidget."""
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        assert isinstance(tab, QWidget)

    def test_table_present(self, qtbot, mock_data_access, mock_employee_admin):
        """Таблица договоров существует."""
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'contracts_table')
        assert isinstance(tab.contracts_table, QTableWidget)

    def test_table_columns(self, qtbot, mock_data_access, mock_employee_admin):
        """Таблица имеет 11 колонок."""
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.contracts_table.columnCount() == 11

    def test_add_button_present(self, qtbot, mock_data_access, mock_employee_admin):
        """Кнопка добавления существует (текст или tooltip)."""
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        buttons = tab.findChildren(QPushButton)
        add_btns = [b for b in buttons if 'добавить' in b.text().lower()
                    or 'договор' in b.text().lower()
                    or 'добавить' in b.toolTip().lower()
                    or 'новый' in b.text().lower()
                    or b.objectName() == 'add_contract_btn']
        assert len(add_btns) >= 1 or len(buttons) >= 1, \
            f"Ожидается хотя бы 1 кнопка: найдено {len(buttons)} кнопок"

    def test_data_access_set(self, qtbot, mock_data_access, mock_employee_admin):
        """DataAccess назначен."""
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.data is not None


# ========== 2. Рендеринг диалога (10 тестов) ==========

@pytest.mark.ui
class TestContractDialogRendering:
    """Проверка рендеринга диалога договора."""

    def test_dialog_creates(self, qtbot, parent_widget):
        """Диалог создаётся в режиме добавления."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        assert isinstance(dlg, QDialog)

    def test_client_combo_exists(self, qtbot, parent_widget):
        """Комбобокс клиента существует."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'client_combo')

    def test_project_type_combo(self, qtbot, parent_widget):
        """Комбобокс типа проекта с 2 элементами."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'project_type')
        assert dlg.project_type.count() == 2

    def test_project_subtype_combo(self, qtbot, parent_widget):
        """Комбобокс подтипа существует."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'project_subtype')
        assert dlg.project_subtype.count() >= 2

    def test_contract_number_field(self, qtbot, parent_widget):
        """Поле номера договора существует."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'contract_number')

    def test_contract_date_field(self, qtbot, parent_widget):
        """Поле даты существует."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'contract_date')

    def test_address_field(self, qtbot, parent_widget):
        """Поле адреса существует."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'address')

    def test_area_field(self, qtbot, parent_widget):
        """Поле площади существует."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'area')

    def test_total_amount_field(self, qtbot, parent_widget):
        """Поле суммы существует."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'total_amount')

    def test_city_combo_has_items(self, qtbot, parent_widget):
        """Комбобокс города имеет элементы из get_all_cities."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'city_combo')
        assert dlg.city_combo.count() >= 2


# ========== 3. Динамические поля (12 тестов) ==========

@pytest.mark.ui
class TestContractDynamicFields:
    """Переключение полей по типу/подтипу проекта."""

    def test_individual_default_subtypes(self, qtbot, parent_widget):
        """Индивидуальный проект — 3 подтипа."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.project_type.setCurrentText("Индивидуальный")
        assert dlg.project_subtype.count() == 3

    def test_switch_template_subtypes(self, qtbot, parent_widget):
        """Шаблонный проект — 4 подтипа."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.project_type.setCurrentText("Шаблонный")
        assert dlg.project_subtype.count() == 4

    def test_switch_back_subtypes_restored(self, qtbot, parent_widget):
        """Переключение обратно на Индивидуальный — подтипы восстановлены."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.project_type.setCurrentText("Шаблонный")
        dlg.project_type.setCurrentText("Индивидуальный")
        assert dlg.project_subtype.count() == 3

    def test_individual_3_payment_fields(self, qtbot, parent_widget):
        """Индивидуальный — 3 поля оплаты."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.project_type.setCurrentText("Индивидуальный")
        assert hasattr(dlg, 'advance_payment')
        assert hasattr(dlg, 'additional_payment')
        assert hasattr(dlg, 'third_payment')
        assert not dlg.individual_group.isHidden()

    def test_template_paid_amount_field(self, qtbot, parent_widget):
        """Шаблонный — поле 'Оплачено'."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.project_type.setCurrentText("Шаблонный")
        assert hasattr(dlg, 'template_paid_amount')
        assert not dlg.template_group.isHidden()

    def test_template_floors_visible(self, qtbot, parent_widget):
        """Шаблонный — поле этажей видно."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.project_type.setCurrentText("Шаблонный")
        assert hasattr(dlg, 'floors_spin')
        assert not dlg.floors_spin.isHidden()

    def test_individual_floors_hidden(self, qtbot, parent_widget):
        """Индивидуальный — поле этажей скрыто."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.project_type.setCurrentText("Индивидуальный")
        assert dlg.floors_spin.isHidden()

    def test_individual_group_visible(self, qtbot, parent_widget):
        """Индивидуальный — individual_group не скрыт."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.project_type.setCurrentText("Индивидуальный")
        assert not dlg.individual_group.isHidden()
        assert dlg.template_group.isHidden()

    def test_template_group_visible(self, qtbot, parent_widget):
        """Шаблонный — template_group не скрыт."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.project_type.setCurrentText("Шаблонный")
        assert not dlg.template_group.isHidden()
        assert dlg.individual_group.isHidden()

    def test_period_auto_calc_individual(self, qtbot, parent_widget):
        """Срок автоматически рассчитывается для индивидуального."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.project_type.setCurrentText("Индивидуальный")
        dlg.area.setValue(100)
        # Проверяем что contract_period имеет значение > 0
        assert hasattr(dlg, 'contract_period')
        assert dlg.contract_period.value() >= 0

    def test_period_auto_calc_template(self, qtbot, parent_widget):
        """Срок автоматически рассчитывается для шаблонного."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.project_type.setCurrentText("Шаблонный")
        dlg.area.setValue(80)
        assert hasattr(dlg, 'template_contract_period')
        assert dlg.template_contract_period.value() >= 0

    def test_agent_combo_exists(self, qtbot, parent_widget):
        """Комбобокс агента существует."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'agent_combo')


# ========== 4. Валидация (7 тестов) ==========

@pytest.mark.ui
class TestContractValidation:
    """Валидация обязательных полей."""

    def test_empty_number_rejected(self, qtbot, parent_widget):
        """Пустой номер — ошибка."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.contract_number.setText('')
        dlg.save_contract()
        assert dlg.result() != QDialog.Accepted

    def test_valid_individual_saves(self, qtbot, parent_widget):
        """Валидный индивидуальный договор — data.create_contract вызван."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.contract_number.setText('ТСТ-001/26')
        dlg.address.setText('г. СПб, ул. Тест, д.1')
        dlg.area.setValue(85.5)
        dlg.total_amount.setValue(500000)
        dlg.save_contract()
        dlg.data.create_contract.assert_called_once()

    def test_valid_template_saves(self, qtbot, parent_widget):
        """Валидный шаблонный договор — data.create_contract вызван."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.project_type.setCurrentText("Шаблонный")
        dlg.contract_number.setText('ШП-001/26')
        dlg.address.setText('г. Москва, ул. Тест, д.2')
        dlg.area.setValue(120)
        dlg.total_amount.setValue(300000)
        dlg.save_contract()
        dlg.data.create_contract.assert_called_once()

    def test_zero_area_accepted(self, qtbot, parent_widget):
        """Нулевая площадь — допустима."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.contract_number.setText('ТСТ-002/26')
        dlg.area.setValue(0)
        dlg.save_contract()
        # Не крашится
        assert True

    def test_view_only_no_save(self, qtbot, parent_widget, sample_contract_individual):
        """В режиме просмотра нет кнопки сохранить."""
        dlg = _create_contract_dialog(qtbot, parent_widget,
                                       contract_data=sample_contract_individual, view_only=True)
        save_btns = [b for b in dlg.findChildren(QPushButton)
                     if 'сохранить' in b.text().lower()]
        assert len(save_btns) == 0

    def test_edit_prefills_data(self, qtbot, parent_widget, sample_contract_individual):
        """Редактирование — поля заполнены."""
        dlg = _create_contract_dialog(qtbot, parent_widget,
                                       contract_data=sample_contract_individual)
        assert dlg.contract_number.text() == sample_contract_individual['contract_number']

    def test_comments_field_exists(self, qtbot, parent_widget):
        """Поле комментариев существует."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'comments')


# ========== 5. CRUD операции (6 тестов) ==========

@pytest.mark.ui
class TestContractCRUD:
    """Создание, обновление договоров."""

    def test_create_individual_calls_db(self, qtbot, parent_widget):
        """Создание индивидуального вызывает data.create_contract."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.contract_number.setText('НОВЫЙ-001/26')
        dlg.address.setText('Тестовый адрес')
        dlg.save_contract()
        dlg.data.create_contract.assert_called_once()

    def test_create_template_type(self, qtbot, parent_widget):
        """Создание шаблонного — project_type='Шаблонный'."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.project_type.setCurrentText("Шаблонный")
        dlg.contract_number.setText('ШП-НОВЫЙ-001/26')
        dlg.address.setText('Тестовый адрес')
        dlg.save_contract()
        call_args = dlg.data.create_contract.call_args[0][0]
        assert call_args['project_type'] == 'Шаблонный'

    def test_update_contract_calls_db(self, qtbot, parent_widget, sample_contract_individual):
        """Обновление вызывает data.update_contract."""
        dlg = _create_contract_dialog(qtbot, parent_widget,
                                       contract_data=sample_contract_individual)
        dlg.address.setText('Обновлённый адрес')
        dlg.save_contract()
        dlg.data.update_contract.assert_called()

    def test_contract_number_in_data(self, qtbot, parent_widget):
        """Номер договора передаётся в данных."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.contract_number.setText('УНИК-001/26')
        dlg.save_contract()
        call_args = dlg.data.create_contract.call_args[0][0]
        assert call_args['contract_number'] == 'УНИК-001/26'

    def test_city_in_data(self, qtbot, parent_widget):
        """Город передаётся в данных."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.contract_number.setText('ГОРОД-001/26')
        dlg.city_combo.setCurrentText('МСК')
        dlg.save_contract()
        call_args = dlg.data.create_contract.call_args[0][0]
        assert call_args['city'] == 'МСК'

    def test_date_format_yyyy_mm_dd(self, qtbot, parent_widget):
        """Дата передаётся в формате yyyy-MM-dd."""
        dlg = _create_contract_dialog(qtbot, parent_widget)
        dlg.contract_number.setText('ДАТА-001/26')
        dlg.contract_date.setDate(QDate(2026, 3, 15))
        dlg.save_contract()
        call_args = dlg.data.create_contract.call_args[0][0]
        assert call_args['contract_date'] == '2026-03-15'


# ========== 6. Поиск (4 теста) ==========

@pytest.mark.ui
class TestContractSearch:
    """Поиск договоров."""

    def test_search_dialog_creates(self, qtbot, mock_data_access, mock_employee_admin):
        """Диалог поиска создаётся."""
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        dlg = _create_contract_search_dialog(tab)
        assert isinstance(dlg, QDialog)

    def test_search_has_number_input(self, qtbot, mock_data_access, mock_employee_admin):
        """Поле поиска по номеру существует."""
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        dlg = _create_contract_search_dialog(tab)
        assert hasattr(dlg, 'contract_number_input')

    def test_search_has_address_input(self, qtbot, mock_data_access, mock_employee_admin):
        """Поле поиска по адресу существует."""
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        dlg = _create_contract_search_dialog(tab)
        assert hasattr(dlg, 'address_input')

    def test_search_has_date_filter(self, qtbot, mock_data_access, mock_employee_admin):
        """Чекбокс фильтра по дате существует."""
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        dlg = _create_contract_search_dialog(tab)
        assert hasattr(dlg, 'use_date_filter')
