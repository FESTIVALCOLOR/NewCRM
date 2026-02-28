# -*- coding: utf-8 -*-
"""
Углублённые тесты диалогов договоров — FormattedMoneyInput, FormattedAreaInput,
FormattedPeriodInput, ContractDialog (save/validation/fill), ContractSearchDialog.
~32 теста.  НЕ дублирует test_contracts.py (44 теста на ContractsTab).
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, QApplication
from PyQt5.QtCore import Qt, QDate, QEvent
from PyQt5.QtGui import QFocusEvent, QIcon


# ========== Авто-мок CustomMessageBox ==========

@pytest.fixture(autouse=True)
def _mock_contract_deep_msgbox():
    """Мок CustomMessageBox / CustomQuestionBox — не блокирует тесты."""
    with patch('ui.contract_dialogs.CustomMessageBox') as m1, \
         patch('ui.contract_dialogs.CustomQuestionBox', MagicMock()):
        m1.return_value.exec_.return_value = None
        yield m1


@pytest.fixture(autouse=True)
def _clear_debounce():
    """Сброс глобального состояния debounce_click между тестами."""
    from utils.button_debounce import _last_click_time
    _last_click_time.clear()
    yield
    _last_click_time.clear()


# ========== Хелпер IconLoader ==========

def _mock_icon_loader():
    """Создать мок IconLoader с QIcon() вместо None."""
    mock = MagicMock()
    mock.load = MagicMock(return_value=QIcon())
    mock.create_icon_button = MagicMock(side_effect=lambda *a, **k: QPushButton())
    mock.get_icon_path = MagicMock(return_value='')
    return mock


# ========== Хелперы ==========

def _make_parent(qtbot, mock_data_access, mock_employee_admin):
    """Родительский виджет с data / employee / db."""
    from PyQt5.QtWidgets import QWidget
    w = QWidget()
    w.data = mock_data_access
    w.employee = mock_employee_admin
    w.db = mock_data_access.db
    w.api_client = None
    w.load_contracts = MagicMock()
    qtbot.addWidget(w)
    return w


# ========================================================================
# 1. FormattedMoneyInput (6 тестов)
# ========================================================================

@pytest.mark.ui
class TestFormattedMoneyInput:
    """Тесты поля ввода суммы с форматированием."""

    def test_initial_value_zero(self, qtbot):
        """Начальное значение = 0."""
        from ui.contract_dialogs import FormattedMoneyInput
        w = FormattedMoneyInput()
        qtbot.addWidget(w)
        assert w.value() == 0

    def test_set_value_formats_text(self, qtbot):
        """setValue показывает отформатированный текст."""
        from ui.contract_dialogs import FormattedMoneyInput
        w = FormattedMoneyInput()
        qtbot.addWidget(w)
        w.setValue(1500000)
        assert w.value() == 1500000
        assert '₽' in w.text()

    def test_set_value_zero_clears(self, qtbot):
        """setValue(0) очищает текст."""
        from ui.contract_dialogs import FormattedMoneyInput
        w = FormattedMoneyInput()
        qtbot.addWidget(w)
        w.setValue(0)
        assert w.text() == ''

    def test_focus_in_shows_raw_number(self, qtbot):
        """При focusIn показываем чистое число."""
        from ui.contract_dialogs import FormattedMoneyInput
        w = FormattedMoneyInput()
        qtbot.addWidget(w)
        w.setValue(250000)
        ev = QFocusEvent(QEvent.FocusIn)
        w.focusInEvent(ev)
        assert w.text() == '250000'

    def test_focus_out_formats(self, qtbot):
        """При focusOut форматируем обратно."""
        from ui.contract_dialogs import FormattedMoneyInput
        w = FormattedMoneyInput()
        qtbot.addWidget(w)
        w.setText('300000')
        ev = QFocusEvent(QEvent.FocusOut)
        w.focusOutEvent(ev)
        assert w.value() == 300000
        assert '₽' in w.text()

    def test_focus_out_invalid_resets(self, qtbot):
        """Невалидный текст сбрасывается при focusOut."""
        from ui.contract_dialogs import FormattedMoneyInput
        w = FormattedMoneyInput()
        qtbot.addWidget(w)
        w.setText('abc')
        ev = QFocusEvent(QEvent.FocusOut)
        w.focusOutEvent(ev)
        assert w.value() == 0
        assert w.text() == ''


# ========================================================================
# 2. FormattedAreaInput (5 тестов)
# ========================================================================

@pytest.mark.ui
class TestFormattedAreaInput:
    """Тесты поля ввода площади с форматированием."""

    def test_initial_value_zero(self, qtbot):
        from ui.contract_dialogs import FormattedAreaInput
        w = FormattedAreaInput()
        qtbot.addWidget(w)
        assert w.value() == 0.0

    def test_set_value_formats(self, qtbot):
        from ui.contract_dialogs import FormattedAreaInput
        w = FormattedAreaInput()
        qtbot.addWidget(w)
        w.setValue(85.5)
        assert w.value() == 85.5
        assert 'м²' in w.text()

    def test_max_area_10000(self, qtbot):
        """Площадь ограничена 10 000 м²."""
        from ui.contract_dialogs import FormattedAreaInput
        w = FormattedAreaInput()
        qtbot.addWidget(w)
        w.setText('15000')
        ev = QFocusEvent(QEvent.FocusOut)
        w.focusOutEvent(ev)
        assert w.value() == 10000

    def test_focus_in_shows_raw(self, qtbot):
        from ui.contract_dialogs import FormattedAreaInput
        w = FormattedAreaInput()
        qtbot.addWidget(w)
        w.setValue(120.0)
        ev = QFocusEvent(QEvent.FocusIn)
        w.focusInEvent(ev)
        assert w.text() == '120.0'

    def test_empty_text_resets(self, qtbot):
        from ui.contract_dialogs import FormattedAreaInput
        w = FormattedAreaInput()
        qtbot.addWidget(w)
        w.setText('')
        ev = QFocusEvent(QEvent.FocusOut)
        w.focusOutEvent(ev)
        assert w.value() == 0.0


# ========================================================================
# 3. FormattedPeriodInput (5 тестов)
# ========================================================================

@pytest.mark.ui
class TestFormattedPeriodInput:
    """Тесты поля ввода срока (раб. дней)."""

    def test_initial_value_zero(self, qtbot):
        from ui.contract_dialogs import FormattedPeriodInput
        w = FormattedPeriodInput()
        qtbot.addWidget(w)
        assert w.value() == 0

    def test_set_value_formats(self, qtbot):
        from ui.contract_dialogs import FormattedPeriodInput
        w = FormattedPeriodInput()
        qtbot.addWidget(w)
        w.setValue(45)
        assert w.value() == 45
        assert 'раб. дней' in w.text()

    def test_max_period_365(self, qtbot):
        """Срок ограничен 365 днями."""
        from ui.contract_dialogs import FormattedPeriodInput
        w = FormattedPeriodInput()
        qtbot.addWidget(w)
        w.setText('500')
        ev = QFocusEvent(QEvent.FocusOut)
        w.focusOutEvent(ev)
        assert w.value() == 365

    def test_focus_in_shows_raw(self, qtbot):
        from ui.contract_dialogs import FormattedPeriodInput
        w = FormattedPeriodInput()
        qtbot.addWidget(w)
        w.setValue(30)
        ev = QFocusEvent(QEvent.FocusIn)
        w.focusInEvent(ev)
        assert w.text() == '30'

    def test_invalid_text_resets(self, qtbot):
        from ui.contract_dialogs import FormattedPeriodInput
        w = FormattedPeriodInput()
        qtbot.addWidget(w)
        w.setText('xyz')
        ev = QFocusEvent(QEvent.FocusOut)
        w.focusOutEvent(ev)
        assert w.value() == 0


# ========================================================================
# 4. ContractDialog — валидация и save (10 тестов)
# ========================================================================

@pytest.mark.ui
class TestContractDialogDeep:
    """Углублённые тесты ContractDialog."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        """Создать ContractDialog — патчи активны на время теста."""
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        mock_da = parent.data
        mock_da.api_client = None
        mock_da.is_online = False
        mock_da.check_contract_number_exists.return_value = False
        mock_da.db.add_contract.return_value = None
        mock_da.db.conn = MagicMock()
        mock_da.db.conn.execute.return_value.fetchone.return_value = [1]
        mock_da.get_all_clients.return_value = [
            {'id': 1, 'full_name': 'Тестовый Клиент', 'client_type': 'Физическое лицо', 'phone': '+7 (999) 000-00-00'},
        ]
        mock_da.get_all_agents.return_value = [{'name': 'ФЕСТИВАЛЬ', 'id': 1}]
        mock_da.get_all_cities.return_value = [{'name': 'СПБ'}, {'name': 'МСК'}]
        mock_da.get_contract.return_value = None

        with patch('ui.contract_dialogs.DataAccess', return_value=mock_da), \
             patch('ui.contract_dialogs.DatabaseManager', return_value=MagicMock()), \
             patch('ui.contract_dialogs.YandexDiskManager', return_value=None), \
             patch('ui.contract_dialogs.IconLoader', _mock_icon_loader()):
            from ui.contract_dialogs import ContractDialog
            d = ContractDialog(parent)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_save_duplicate_number_rejected(self, dlg):
        dlg.data.check_contract_number_exists.return_value = True
        dlg.contract_number.setText('ДУБЛЬ-001/26')
        dlg.save_contract()
        assert dlg.result() != QDialog.Accepted

    def test_save_contract_data_keys(self, dlg):
        dlg.contract_number.setText('КЛЮЧИ-001/26')
        dlg.address.setText('ул. Тестовая')
        dlg.area.setValue(100)
        dlg.total_amount.setValue(500000)
        dlg.data.create_contract.return_value = {'id': 999}
        dlg.save_contract()
        call_args = dlg.data.create_contract.call_args[0][0]
        for key in ['client_id', 'project_type', 'project_subtype',
                     'contract_number', 'contract_date', 'address',
                     'area', 'total_amount', 'advance_payment', 'city']:
            assert key in call_args, f"Ключ '{key}' отсутствует"

    def test_advance_payment_value_saved(self, dlg):
        dlg.contract_number.setText('АВАНС-001/26')
        dlg.advance_payment.setValue(150000)
        dlg.data.create_contract.return_value = {'id': 999}
        dlg.save_contract()
        assert dlg.data.create_contract.call_args[0][0]['advance_payment'] == 150000

    def test_additional_payment_value_saved(self, dlg):
        dlg.contract_number.setText('ДОП-001/26')
        dlg.additional_payment.setValue(200000)
        dlg.data.create_contract.return_value = {'id': 999}
        dlg.save_contract()
        assert dlg.data.create_contract.call_args[0][0]['additional_payment'] == 200000

    def test_third_payment_value_saved(self, dlg):
        dlg.contract_number.setText('ТРЕТ-001/26')
        dlg.third_payment.setValue(100000)
        dlg.data.create_contract.return_value = {'id': 999}
        dlg.save_contract()
        assert dlg.data.create_contract.call_args[0][0]['third_payment'] == 100000

    def test_template_zero_additional_third(self, dlg):
        dlg.project_type.setCurrentText('Шаблонный')
        dlg.contract_number.setText('ШП-001/26')
        dlg.data.create_contract.return_value = {'id': 999}
        dlg.save_contract()
        call = dlg.data.create_contract.call_args[0][0]
        assert call['additional_payment'] == 0
        assert call['third_payment'] == 0

    def test_static_calc_contract_term(self, qtbot, mock_data_access, mock_employee_admin):
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_contract_term(1, 100) == 60
        assert ContractDialog._calc_contract_term(1, 50) == 50
        assert ContractDialog._calc_contract_term(3, 50) == 10

    def test_static_calc_template_term(self, qtbot, mock_data_access, mock_employee_admin):
        from ui.contract_dialogs import ContractDialog
        assert ContractDialog._calc_template_contract_term('Стандарт', 80, 1) == 20
        assert ContractDialog._calc_template_contract_term('Стандарт', 100, 1) == 30

    def test_project_subtype_saved(self, dlg):
        dlg.contract_number.setText('ПОДТИП-001/26')
        dlg.project_subtype.setCurrentIndex(0)
        expected = dlg.project_subtype.currentText()
        dlg.data.create_contract.return_value = {'id': 999}
        dlg.save_contract()
        assert dlg.data.create_contract.call_args[0][0]['project_subtype'] == expected

    def test_city_saved(self, dlg):
        dlg.contract_number.setText('ГОРОД-001/26')
        dlg.city_combo.setCurrentIndex(0)
        expected_city = dlg.city_combo.currentText()
        dlg.data.create_contract.return_value = {'id': 999}
        dlg.save_contract()
        assert dlg.data.create_contract.call_args[0][0]['city'] == expected_city


# ========================================================================
# 5. ContractSearchDialog (6 тестов)
# ========================================================================

@pytest.mark.ui
class TestContractSearchDialogDeep:
    """Тесты ContractSearchDialog: фильтры, сброс, get_search_params."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.contract_dialogs.IconLoader', _mock_icon_loader()):
            from ui.contract_dialogs import ContractSearchDialog
            d = ContractSearchDialog(parent)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_get_search_params_empty(self, dlg):
        params = dlg.get_search_params()
        assert params['contract_number'] == ''
        assert params['address'] == ''
        assert params['client_name'] == ''
        assert 'date_from' not in params

    def test_get_search_params_with_number(self, dlg):
        dlg.contract_number_input.setText('ТСТ-001')
        assert dlg.get_search_params()['contract_number'] == 'ТСТ-001'

    def test_get_search_params_with_date_filter(self, dlg):
        dlg.use_date_filter.setChecked(True)
        params = dlg.get_search_params()
        assert 'date_from' in params
        assert 'date_to' in params

    def test_reset_filters_clears_fields(self, dlg):
        dlg.contract_number_input.setText('ТСТ-001')
        dlg.address_input.setText('ул. Тестовая')
        dlg.client_name_input.setText('Иванов')
        dlg.reset_filters()
        assert dlg.contract_number_input.text() == ''
        assert dlg.address_input.text() == ''
        assert dlg.client_name_input.text() == ''

    def test_client_name_input_exists(self, dlg):
        assert hasattr(dlg, 'client_name_input')
        assert isinstance(dlg.client_name_input, QLineEdit)

    def test_date_fields_disabled_by_default(self, dlg):
        assert not dlg.date_from.isEnabled()
        assert not dlg.date_to.isEnabled()
