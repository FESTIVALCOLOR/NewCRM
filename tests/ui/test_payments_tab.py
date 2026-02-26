# -*- coding: utf-8 -*-
"""
Расширенные тесты взаимодействий платежной подсистемы — SalariesTab, PaymentDialog, EditPaymentDialog.

Файл ui/payments_tab.py отсутствует; платежи реализованы в ui/salaries_tab.py.
Тесты покрывают: инициализацию, загрузку данных, фильтрацию, CRUD операции,
статусы оплаты, диалоги добавления/редактирования.

Покрытие:
  - TestPaymentsTabInit (4)         — инициализация SalariesTab, вкладки, таблицы
  - TestPaymentsDataLoad (3)        — загрузка всех выплат, кеш, отрисовка
  - TestPaymentsFilters (4)         — фильтрация по периоду/адресу/статусу
  - TestPaymentsStatus (3)          — set_payment_status, mark_as_paid, toggle
  - TestPaymentsDelete (3)          — удаление CRM-платежа, оклада, универсальный метод
  - TestPaymentDialogSalary (4)     — PaymentDialog для окладов: поля, save, DataAccess
  - TestEditPaymentDialogFields (3) — EditPaymentDialog: prefill, get_payment_data
ИТОГО: 24 теста
"""

import pytest
import logging
from unittest.mock import MagicMock, patch, call
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QTableWidget, QPushButton, QLabel,
    QDialog, QDoubleSpinBox, QSpinBox
)
from PyQt5.QtCore import Qt, QDate
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


def _create_salaries_tab(qtbot, mock_data_access, employee):
    """Создание SalariesTab с полностью замоканными зависимостями."""
    mock_data_access.api_client = None
    mock_data_access.db.get_year_payments = MagicMock(return_value=[])
    mock_data_access.get_all_employees.return_value = []
    mock_data_access.get_all_contracts.return_value = []
    mock_data_access.get_year_payments = MagicMock(return_value=[])
    mock_data_access.get_payments_by_type = MagicMock(return_value=[])

    with patch('ui.salaries_tab.DataAccess') as MockDA, \
         patch('ui.salaries_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
        MockDA.return_value = mock_data_access
        from ui.salaries_tab import SalariesTab
        tab = SalariesTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab


def _create_payment_dialog(qtbot, parent_widget, payment_type='Оклады',
                           payment_data=None):
    """Создание PaymentDialog."""
    mock_da = parent_widget.data
    mock_da.api_client = None
    mock_da.get_all_employees.return_value = [
        {'id': 1, 'full_name': 'Тестов Админ'},
        {'id': 6, 'full_name': 'Дизайнеров Тест'},
    ]
    mock_da.get_all_contracts.return_value = [
        {'id': 200, 'contract_number': 'ИП-ПОЛ-12345/26', 'address': 'г. СПб'},
    ]

    with patch('ui.salaries_tab.DataAccess') as MockDA, \
         patch('ui.salaries_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
        MockDA.return_value = mock_da
        from ui.salaries_tab import PaymentDialog
        dlg = PaymentDialog(parent_widget, payment_data=payment_data,
                            payment_type=payment_type)
        qtbot.addWidget(dlg)
        return dlg


def _create_edit_payment_dialog(qtbot, parent_widget, payment_data=None):
    """Создание EditPaymentDialog."""
    if payment_data is None:
        payment_data = {
            'id': 100,
            'employee_name': 'Тестовый Сотрудник',
            'payment_type': 'Аванс',
            'final_amount': 50000,
            'report_month': '2026-02',
            'source': 'CRM'
        }
    mock_da = parent_widget.data
    mock_da.api_client = None

    with patch('ui.salaries_tab.DataAccess') as MockDA, \
         patch('ui.salaries_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
        MockDA.return_value = mock_da
        from ui.salaries_tab import EditPaymentDialog
        dlg = EditPaymentDialog(parent_widget, payment_data=payment_data)
        qtbot.addWidget(dlg)
        return dlg


def _sample_payments():
    """Набор тестовых выплат для загрузки в таблицу."""
    return [
        {
            'id': 1, 'source': 'CRM', 'project_type': 'Индивидуальный',
            'agent_type': 'Фестиваль', 'employee_name': 'Иванов Иван',
            'position': 'Дизайнер', 'amount': 100000,
            'payment_subtype': 'Аванс', 'address': 'г. СПб, ул. Тестовая, д.1',
            'report_month': '2026-02', 'payment_status': 'to_pay',
            'reassigned': False
        },
        {
            'id': 2, 'source': 'CRM', 'project_type': 'Шаблонный',
            'agent_type': '', 'employee_name': 'Петров Пётр',
            'position': 'Чертёжник', 'amount': 50000,
            'payment_subtype': 'Доплата', 'address': 'г. МСК, ул. Шаблонная, д.5',
            'report_month': '2026-02', 'payment_status': 'paid',
            'reassigned': False
        },
        {
            'id': 3, 'source': 'Оклад', 'project_type': 'Индивидуальный',
            'agent_type': '', 'employee_name': 'Сидоров Сидор',
            'position': 'ГАП', 'amount': 80000,
            'payment_subtype': 'Оклад', 'address': '',
            'report_month': '2026-01', 'payment_status': None,
            'reassigned': False
        },
    ]


# ========== 1. Инициализация SalariesTab (4 теста) ==========

@pytest.mark.ui
class TestPaymentsTabInit:
    """Инициализация вкладки зарплат/платежей."""

    def test_tab_creates_as_qwidget(self, qtbot, mock_data_access, mock_employee_admin):
        """SalariesTab создаётся как QWidget без ошибок."""
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        assert isinstance(tab, QWidget)

    def test_tab_has_5_subtabs(self, qtbot, mock_data_access, mock_employee_admin):
        """Содержит 5 вкладок: Все, Индивидуальные, Шаблонные, Оклады, Надзор."""
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'tabs')
        assert isinstance(tab.tabs, QTabWidget)
        assert tab.tabs.count() == 5

    def test_all_payments_table_has_9_columns(self, qtbot, mock_data_access, mock_employee_admin):
        """Таблица 'Все выплаты' содержит 9 колонок."""
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'all_payments_table')
        assert tab.all_payments_table.columnCount() == 9

    def test_data_access_assigned(self, qtbot, mock_data_access, mock_employee_admin):
        """DataAccess назначен и не None."""
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.data is not None
        assert tab.data is mock_data_access


# ========== 2. Загрузка данных (3 теста) ==========

@pytest.mark.ui
class TestPaymentsDataLoad:
    """Загрузка выплат и отрисовка таблицы."""

    def test_load_all_payments_populates_table(self, qtbot, mock_data_access, mock_employee_admin):
        """load_all_payments() заполняет таблицу данными."""
        payments = _sample_payments()
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)

        # Настраиваем mock ПОСЛЕ создания таба (tab.data уже ссылается на mock_data_access)
        tab.data.get_year_payments = MagicMock(return_value=payments)

        # Устанавливаем период "Год" и year_filter = 2026 (совпадает с report_month в тестовых данных)
        tab.period_filter.blockSignals(True)
        tab.period_filter.setCurrentText('Год')
        tab.period_filter.blockSignals(False)
        tab.year_filter.blockSignals(True)
        tab.year_filter.setCurrentText('2026')
        tab.year_filter.blockSignals(False)
        tab.load_all_payments(force_reload=True)
        assert tab.all_payments_table.rowCount() == 3

    def test_ensure_data_loaded_once(self, qtbot, mock_data_access, mock_employee_admin):
        """ensure_data_loaded() загружает данные только один раз."""
        mock_data_access.get_year_payments = MagicMock(return_value=[])
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)

        tab.ensure_data_loaded()
        call_count_1 = mock_data_access.get_year_payments.call_count
        tab.ensure_data_loaded()
        call_count_2 = mock_data_access.get_year_payments.call_count
        assert call_count_1 == call_count_2  # Повторный вызов не загружает данные

    def test_totals_label_shows_amounts(self, qtbot, mock_data_access, mock_employee_admin):
        """Метка итогов отображает суммы."""
        payments = _sample_payments()
        mock_data_access.get_year_payments = MagicMock(return_value=payments)
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)

        tab.period_filter.setCurrentText('Год')
        tab.load_all_payments(force_reload=True)
        text = tab.totals_label.text()
        assert 'Итого' in text


# ========== 3. Фильтрация (4 теста) ==========

@pytest.mark.ui
class TestPaymentsFilters:
    """Фильтрация платежей по различным параметрам."""

    def test_period_filter_month_shows_controls(self, qtbot, mock_data_access, mock_employee_admin):
        """Выбор периода 'Месяц' показывает month_filter и year_filter (не скрыты)."""
        mock_data_access.get_year_payments = MagicMock(return_value=[])
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.period_filter.setCurrentText('Месяц')
        # isVisible() зависит от показа самого виджета;
        # в offscreen проверяем через isHidden() — скрытость управляется .hide()/.show()
        assert not tab.month_filter.isHidden()
        assert not tab.year_filter.isHidden()

    def test_period_filter_all_hides_controls(self, qtbot, mock_data_access, mock_employee_admin):
        """Выбор периода 'Все' скрывает month_filter, year_filter, quarter_filter."""
        mock_data_access.get_year_payments = MagicMock(return_value=[])
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.period_filter.setCurrentText('Все')
        assert tab.month_filter.isHidden()
        assert tab.year_filter.isHidden()
        assert tab.quarter_filter.isHidden()

    def test_reset_filters_restores_defaults(self, qtbot, mock_data_access, mock_employee_admin):
        """Сброс фильтров возвращает период в 'Все'."""
        mock_data_access.get_year_payments = MagicMock(return_value=[])
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.period_filter.setCurrentText('Месяц')
        tab.reset_all_payments_filters()
        assert tab.period_filter.currentText() == 'Все'

    def test_invalidate_cache_clears_data(self, qtbot, mock_data_access, mock_employee_admin):
        """invalidate_cache() очищает кеш данных."""
        mock_data_access.get_year_payments = MagicMock(return_value=[])
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab._all_payments_cache = [{'id': 1}]
        tab._cache_year = 2026
        tab.invalidate_cache()
        assert tab._all_payments_cache is None
        assert tab._cache_year is None


# ========== 4. Статусы оплаты (3 теста) ==========

@pytest.mark.ui
class TestPaymentsStatus:
    """Управление статусами оплаты: to_pay, paid, toggle."""

    def test_set_payment_status_calls_data_access(self, qtbot, mock_data_access, mock_employee_admin):
        """set_payment_status() вызывает DataAccess.update_payment."""
        mock_data_access.get_year_payments = MagicMock(return_value=[])
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)

        payment = {'id': 1, 'payment_status': None, 'report_month': '2026-02'}
        table = tab.all_payments_table
        tab.set_payment_status(payment, 'to_pay', table, 0, is_salary=False)

        mock_data_access.update_payment.assert_called_once()
        call_args = mock_data_access.update_payment.call_args[0]
        assert call_args[0] == 1
        assert call_args[1]['payment_status'] == 'to_pay'

    def test_set_payment_status_toggle_resets(self, qtbot, mock_data_access, mock_employee_admin):
        """Повторная установка того же статуса — toggle, сбрасывает в None."""
        mock_data_access.get_year_payments = MagicMock(return_value=[])
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)

        payment = {'id': 2, 'payment_status': 'paid', 'report_month': '2026-02'}
        table = tab.all_payments_table
        tab.set_payment_status(payment, 'paid', table, 0, is_salary=False)

        mock_data_access.update_payment.assert_called_once()
        call_args = mock_data_access.update_payment.call_args[0]
        assert call_args[1]['payment_status'] is None  # Toggle — сброс

    def test_set_salary_status_calls_update_salary(self, qtbot, mock_data_access, mock_employee_admin):
        """set_payment_status с is_salary=True вызывает DataAccess.update_salary."""
        mock_data_access.get_year_payments = MagicMock(return_value=[])
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)

        payment = {'id': 3, 'payment_status': None, 'report_month': '2026-01'}
        table = tab.all_payments_table
        tab.set_payment_status(payment, 'to_pay', table, 0, is_salary=True)

        mock_data_access.update_salary.assert_called_once()


# ========== 5. Удаление платежей (3 теста) ==========

@pytest.mark.ui
class TestPaymentsDelete:
    """Удаление платежей: CRM-платёж, оклад, универсальный метод."""

    def test_delete_payment_universal_confirmed(self, qtbot, mock_data_access, mock_employee_admin):
        """Подтверждённое удаление CRM-платежа вызывает DataAccess.delete_payment."""
        mock_data_access.get_year_payments = MagicMock(return_value=[])
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch('ui.salaries_tab.CustomQuestionBox') as MockQ, \
             patch('ui.salaries_tab.CustomMessageBox'):
            MockQ.return_value.exec_.return_value = QDialog.Accepted
            tab.delete_payment_universal(10, 'CRM', 'Дизайнер', 'Иванов')

        mock_data_access.delete_payment.assert_called_once_with(10)

    def test_delete_salary_universal_confirmed(self, qtbot, mock_data_access, mock_employee_admin):
        """Подтверждённое удаление оклада вызывает DataAccess.delete_salary."""
        mock_data_access.get_year_payments = MagicMock(return_value=[])
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch('ui.salaries_tab.CustomQuestionBox') as MockQ, \
             patch('ui.salaries_tab.CustomMessageBox'):
            MockQ.return_value.exec_.return_value = QDialog.Accepted
            tab.delete_payment_universal(20, 'Оклад', 'ГАП', 'Сидоров')

        mock_data_access.delete_salary.assert_called_once_with(20)

    def test_delete_payment_cancelled_no_call(self, qtbot, mock_data_access, mock_employee_admin):
        """Отмена удаления — DataAccess не вызывается."""
        mock_data_access.get_year_payments = MagicMock(return_value=[])
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch('ui.salaries_tab.CustomQuestionBox') as MockQ:
            MockQ.return_value.exec_.return_value = QDialog.Rejected
            tab.delete_payment_universal(10, 'CRM', 'Дизайнер', 'Иванов')

        mock_data_access.delete_payment.assert_not_called()
        mock_data_access.delete_salary.assert_not_called()


# ========== 6. PaymentDialog для окладов (4 теста) ==========

@pytest.mark.ui
class TestPaymentDialogSalary:
    """Диалог добавления выплаты оклада."""

    def test_dialog_creates(self, qtbot, parent_widget):
        """PaymentDialog для окладов создаётся как QDialog."""
        dlg = _create_payment_dialog(qtbot, parent_widget, payment_type='Оклады')
        assert isinstance(dlg, QDialog)

    def test_salary_dialog_has_employee_combo(self, qtbot, parent_widget):
        """Диалог содержит комбобокс исполнителя с сотрудниками."""
        dlg = _create_payment_dialog(qtbot, parent_widget, payment_type='Оклады')
        assert hasattr(dlg, 'employee_combo')
        assert dlg.employee_combo.count() == 2  # 2 сотрудника из mock

    def test_salary_dialog_has_amount_field(self, qtbot, parent_widget):
        """Диалог содержит поле суммы с максимумом 1 000 000."""
        dlg = _create_payment_dialog(qtbot, parent_widget, payment_type='Оклады')
        assert hasattr(dlg, 'amount')
        assert isinstance(dlg.amount, QDoubleSpinBox)
        assert dlg.amount.maximum() == 1000000

    def test_save_salary_calls_create(self, qtbot, parent_widget):
        """Сохранение оклада вызывает DataAccess.create_salary."""
        dlg = _create_payment_dialog(qtbot, parent_widget, payment_type='Оклады')
        dlg.amount.setValue(75000)
        dlg.save_payment()
        parent_widget.data.create_salary.assert_called_once()
        call_args = parent_widget.data.create_salary.call_args[0][0]
        assert call_args['amount'] == 75000
        assert call_args['payment_type'] == 'Оклады'


# ========== 7. EditPaymentDialog (3 теста) ==========

@pytest.mark.ui
class TestEditPaymentDialogFields:
    """Диалог редактирования выплаты: предзаполнение, извлечение данных."""

    def test_dialog_creates(self, qtbot, parent_widget):
        """EditPaymentDialog создаётся как QDialog."""
        dlg = _create_edit_payment_dialog(qtbot, parent_widget)
        assert isinstance(dlg, QDialog)

    def test_prefills_employee_name(self, qtbot, parent_widget):
        """Имя исполнителя предзаполнено из payment_data."""
        dlg = _create_edit_payment_dialog(qtbot, parent_widget)
        assert dlg.employee_label.text() == 'Тестовый Сотрудник'

    def test_get_payment_data_returns_dict(self, qtbot, parent_widget):
        """get_payment_data() возвращает dict с amount, payment_type, report_month."""
        dlg = _create_edit_payment_dialog(qtbot, parent_widget)
        dlg.amount_spin.setValue(120000)
        result = dlg.get_payment_data()
        assert isinstance(result, dict)
        assert result['amount'] == 120000
        assert 'payment_type' in result
        assert 'report_month' in result
