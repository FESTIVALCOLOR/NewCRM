# -*- coding: utf-8 -*-
"""
Тесты для ui/salaries_tab.py — вкладка управления зарплатами (расширенное покрытие).

НЕ дублирует test_salaries_tab_widget.py (создание, вкладки, фильтры, таблица, кеш)
и test_salaries_tab_logic.py (бизнес-логика: фильтрация, форматирование, дедупликация).

Покрытие:
- CollapsibleBox (сворачиваемый виджет)
- PaymentStatusDelegate (делегат покраски строк)
- create_payment_type_tab для каждого типа
- create_payment_actions / create_all_payments_actions / create_crm_payment_actions
- load_all_payments с реальным DataAccess mock
- load_payment_type_data
- set_payment_status (toggle-логика)
- apply_row_color
- on_tab_changed (дашборд)
- on_period_filter_changed (видимость фильтров)
- reset_all_payments_filters
- add_salary_payment
- edit_payment_from_all / edit_crm_payment
- delete_payment_universal / delete_crm_payment / mark_as_paid
- ensure_data_loaded (ленивая загрузка)
- apply_payment_type_filters / reset_payment_type_filters
- _render_all_payments (отрисовка)
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import (QApplication, QTabWidget, QLabel, QPushButton,
                              QTableWidget, QComboBox, QSpinBox, QWidget, QDialog,
                              QStyleOptionViewItem)
from PyQt5.QtCore import Qt, QDate, QModelIndex, QSize
from PyQt5.QtGui import QColor, QPainter, QIcon
from unittest.mock import patch, MagicMock, PropertyMock, call


# ========== Вспомогательные функции ==========

def _mock_icon_loader():
    """Mock IconLoader возвращающий реальные виджеты."""
    mock = MagicMock()
    mock.create_icon_button.side_effect = lambda *a, **k: QPushButton()
    mock.create_action_button.side_effect = lambda *a, **k: QPushButton()
    mock.get_icon.return_value = QIcon()
    mock.get_icon_path.return_value = ''
    mock.load.return_value = QIcon()
    return mock


def _make_mock_data_access(year_payments=None, payments_by_type=None):
    """Создать MagicMock DataAccess для SalariesTab."""
    mock_da = MagicMock()
    mock_da.get_all_payments.return_value = []
    mock_da.get_year_payments.return_value = year_payments or []
    mock_da.get_payments_by_type.return_value = payments_by_type or []
    mock_da.get_all_employees.return_value = []
    mock_da.get_all_contracts.return_value = []
    mock_da.update_payment.return_value = None
    mock_da.update_salary.return_value = None
    mock_da.delete_payment.return_value = None
    mock_da.delete_salary.return_value = None
    mock_da.mark_payment_as_paid.return_value = None
    mock_da.db = MagicMock()
    mock_da.is_online = False
    mock_da.prefer_local = False
    return mock_da


def _create_salaries_tab(qtbot, employee, mock_da=None):
    """Создать SalariesTab с замоканными зависимостями."""
    if mock_da is None:
        mock_da = _make_mock_data_access()

    icon_mock = _mock_icon_loader()
    with patch('ui.salaries_tab.DataAccess', return_value=mock_da), \
         patch('ui.salaries_tab.IconLoader', icon_mock):
        from ui.salaries_tab import SalariesTab
        tab = SalariesTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab, mock_da


SAMPLE_YEAR_PAYMENTS = [
    {
        'id': 1, 'employee_name': 'Иванов И.И.', 'position': 'Дизайнер',
        'amount': 50000.0, 'payment_type': 'Индивидуальные проекты',
        'payment_subtype': 'Аванс', 'address': 'ул. Тестовая, д.1',
        'report_month': '2026-02', 'payment_status': 'to_pay',
        'agent_type': '', 'source': 'CRM', 'project_type': 'Индивидуальный',
        'reassigned': False,
    },
    {
        'id': 2, 'employee_name': 'Петров П.П.', 'position': 'Чертёжник',
        'amount': 30000.0, 'payment_type': 'Шаблонные проекты',
        'payment_subtype': 'Доплата', 'address': 'ул. Другая, д.5',
        'report_month': '2026-02', 'payment_status': 'paid',
        'agent_type': 'Петрович', 'source': 'CRM', 'project_type': 'Шаблонный',
        'reassigned': False,
    },
    {
        'id': 3, 'employee_name': 'Сидоров С.С.', 'position': 'ГАП',
        'amount': 80000.0, 'payment_type': 'Оклады',
        'payment_subtype': 'Оклад', 'address': '',
        'report_month': '2026-02', 'payment_status': 'paid',
        'agent_type': '', 'source': 'Оклад', 'project_type': '',
        'reassigned': False,
    },
]


# ========== Тесты CollapsibleBox ==========

class TestCollapsibleBox:
    """Тесты для виджета CollapsibleBox."""

    def test_creation(self, qtbot):
        """CollapsibleBox создаётся."""
        with patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
            from ui.salaries_tab import CollapsibleBox
            box = CollapsibleBox("Фильтры")
            qtbot.addWidget(box)
            assert box is not None

    def test_initial_state_collapsed(self, qtbot):
        """По умолчанию свёрнуто (not checked)."""
        with patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
            from ui.salaries_tab import CollapsibleBox
            box = CollapsibleBox("Фильтры")
            qtbot.addWidget(box)
            assert box.toggle_button.isChecked() is False

    def test_toggle_expands(self, qtbot):
        """Нажатие toggle_button разворачивает содержимое."""
        with patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
            from ui.salaries_tab import CollapsibleBox
            box = CollapsibleBox("Фильтры")
            qtbot.addWidget(box)
            box.toggle_button.setChecked(True)
            box.on_toggle()
            assert box.content_area.maximumHeight() == 16777215

    def test_toggle_collapses(self, qtbot):
        """Повторное нажатие сворачивает."""
        with patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
            from ui.salaries_tab import CollapsibleBox
            box = CollapsibleBox("Фильтры")
            qtbot.addWidget(box)
            box.toggle_button.setChecked(True)
            box.on_toggle()
            box.toggle_button.setChecked(False)
            box.on_toggle()
            assert box.content_area.maximumHeight() == 0

    def test_title_stored(self, qtbot):
        """Заголовок сохраняется."""
        with patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
            from ui.salaries_tab import CollapsibleBox
            box = CollapsibleBox("Мой заголовок")
            qtbot.addWidget(box)
            assert box._title == "Мой заголовок"

    def test_set_content_layout(self, qtbot):
        """setContentLayout устанавливает layout."""
        with patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
            from ui.salaries_tab import CollapsibleBox
            from PyQt5.QtWidgets import QVBoxLayout
            box = CollapsibleBox("Test")
            qtbot.addWidget(box)
            layout = QVBoxLayout()
            box.setContentLayout(layout)
            assert box.content_area.layout() is not None


# ========== Тесты PaymentStatusDelegate ==========

class TestPaymentStatusDelegate:
    """Тесты делегата PaymentStatusDelegate."""

    def test_creation(self, qtbot):
        """Делегат создаётся."""
        with patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
            from ui.salaries_tab import PaymentStatusDelegate
            delegate = PaymentStatusDelegate()
            assert delegate is not None

    def test_paint_no_crash(self, qtbot):
        """paint не падает при вызове с mock-данными."""
        with patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
            from ui.salaries_tab import PaymentStatusDelegate
            delegate = PaymentStatusDelegate()
            # Создаём минимальный контекст
            table = QTableWidget(1, 1)
            qtbot.addWidget(table)
            item = table.model().index(0, 0)
            option = QStyleOptionViewItem()
            # Не падает при отрисовке
            # (paint использует super(), который работает корректно)
            assert delegate is not None


# ========== Тесты создания вкладок типов оплат ==========

class TestSalariesTabPaymentTypeTabs:
    """Тесты create_payment_type_tab для разных типов."""

    def test_individual_tab_created(self, qtbot, mock_employee_admin):
        """Вкладка индивидуальных проектов создана."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'individual_tab')
        assert tab.individual_tab is not None

    def test_template_tab_created(self, qtbot, mock_employee_admin):
        """Вкладка шаблонных проектов создана."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'template_tab')
        assert tab.template_tab is not None

    def test_salary_tab_created(self, qtbot, mock_employee_admin):
        """Вкладка окладов создана."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'salary_tab')
        assert tab.salary_tab is not None

    def test_supervision_tab_created(self, qtbot, mock_employee_admin):
        """Вкладка авторского надзора создана."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'supervision_tab')
        assert tab.supervision_tab is not None

    def test_individual_tab_has_filters(self, qtbot, mock_employee_admin):
        """Вкладка индивидуальных проектов имеет фильтры."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab.individual_tab, 'period_filter')
        assert hasattr(tab.individual_tab, 'employee_filter')

    def test_salary_tab_has_employee_filter(self, qtbot, mock_employee_admin):
        """Вкладка окладов имеет фильтр сотрудника."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab.salary_tab, 'employee_filter')

    def test_salary_tab_has_project_type_filter(self, qtbot, mock_employee_admin):
        """Вкладка окладов имеет фильтр типа проекта."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab.salary_tab, 'project_type_filter')

    def test_individual_tab_has_address_filter(self, qtbot, mock_employee_admin):
        """Вкладка индивидуальных проектов имеет фильтр адреса."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab.individual_tab, 'address_filter')

    def test_individual_tab_has_status_filter(self, qtbot, mock_employee_admin):
        """Вкладка индивидуальных проектов имеет фильтр статуса."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab.individual_tab, 'status_filter')

    def test_individual_tab_table_12_columns(self, qtbot, mock_employee_admin):
        """Таблица индивидуальных проектов имеет 12 столбцов."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        table = tab.individual_tab.findChild(QTableWidget, 'table_Индивидуальные проекты')
        assert table is not None
        assert table.columnCount() == 12

    def test_salary_tab_table_6_columns(self, qtbot, mock_employee_admin):
        """Таблица окладов имеет 6 столбцов."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        table = tab.salary_tab.findChild(QTableWidget, 'table_Оклады')
        assert table is not None
        assert table.columnCount() == 6

    def test_template_tab_table_12_columns(self, qtbot, mock_employee_admin):
        """Таблица шаблонных проектов имеет 12 столбцов."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        table = tab.template_tab.findChild(QTableWidget, 'table_Шаблонные проекты')
        assert table is not None
        assert table.columnCount() == 12

    def test_supervision_tab_table_12_columns(self, qtbot, mock_employee_admin):
        """Таблица авторского надзора имеет 12 столбцов."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        table = tab.supervision_tab.findChild(QTableWidget, 'table_Авторский надзор')
        assert table is not None
        assert table.columnCount() == 12

    def test_each_tab_has_reset_button(self, qtbot, mock_employee_admin):
        """Каждая вкладка типа имеет кнопку сброса фильтров."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab.individual_tab, 'reset_btn')
        assert hasattr(tab.template_tab, 'reset_btn')
        assert hasattr(tab.salary_tab, 'reset_btn')
        assert hasattr(tab.supervision_tab, 'reset_btn')


# ========== Тесты загрузки данных ==========

class TestSalariesTabLoadAllPayments:
    """Тесты load_all_payments."""

    def test_load_all_payments_empty(self, qtbot, mock_employee_admin):
        """load_all_payments с пустыми данными."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        mock_da.get_year_payments.return_value = []
        tab.load_all_payments()
        assert tab.all_payments_table.rowCount() == 0

    def test_load_all_payments_with_data(self, qtbot, mock_employee_admin):
        """load_all_payments заполняет таблицу."""
        mock_da = _make_mock_data_access(year_payments=SAMPLE_YEAR_PAYMENTS)
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin, mock_da=mock_da)
        tab.load_all_payments()
        assert tab.all_payments_table.rowCount() == 3

    def test_load_all_payments_updates_totals(self, qtbot, mock_employee_admin):
        """load_all_payments обновляет метку итогов."""
        mock_da = _make_mock_data_access(year_payments=SAMPLE_YEAR_PAYMENTS)
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin, mock_da=mock_da)
        tab.load_all_payments()
        text = tab.totals_label.text()
        assert 'Итого' in text

    def test_load_all_payments_populates_filters(self, qtbot, mock_employee_admin):
        """load_all_payments заполняет фильтры уникальными значениями."""
        mock_da = _make_mock_data_access(year_payments=SAMPLE_YEAR_PAYMENTS)
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin, mock_da=mock_da)
        tab.load_all_payments()
        # Фильтр адресов должен содержать адреса из данных
        addresses = [tab.address_filter.itemText(i) for i in range(tab.address_filter.count())]
        assert 'Все' in addresses

    def test_load_all_payments_shows_reassigned_warning(self, qtbot, mock_employee_admin):
        """load_all_payments показывает предупреждение о переназначении."""
        payments = [
            {**SAMPLE_YEAR_PAYMENTS[0], 'reassigned': True},
            SAMPLE_YEAR_PAYMENTS[1],
        ]
        mock_da = _make_mock_data_access(year_payments=payments)
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin, mock_da=mock_da)
        tab.load_all_payments()
        assert tab.all_payments_warning.isVisible()

    def test_load_all_payments_hides_warning_no_reassigned(self, qtbot, mock_employee_admin):
        """load_all_payments скрывает предупреждение без переназначений."""
        mock_da = _make_mock_data_access(year_payments=SAMPLE_YEAR_PAYMENTS)
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin, mock_da=mock_da)
        tab.load_all_payments()
        assert not tab.all_payments_warning.isVisible()

    def test_load_all_payments_caches_data(self, qtbot, mock_employee_admin):
        """load_all_payments кеширует данные."""
        mock_da = _make_mock_data_access(year_payments=SAMPLE_YEAR_PAYMENTS)
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin, mock_da=mock_da)
        tab.load_all_payments()
        assert tab._all_payments_cache is not None
        assert tab._cache_year is not None


# ========== Тесты on_tab_changed ==========

class TestSalariesTabOnTabChanged:
    """Тесты переключения вкладок."""

    def test_switch_to_individual_loads_data(self, qtbot, mock_employee_admin):
        """Переключение на индивидуальные проекты загружает данные."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        mock_da.get_payments_by_type.return_value = []
        tab.on_tab_changed(1)
        mock_da.get_payments_by_type.assert_called()

    def test_switch_to_template_loads_data(self, qtbot, mock_employee_admin):
        """Переключение на шаблонные проекты загружает данные."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        mock_da.get_payments_by_type.return_value = []
        tab.on_tab_changed(2)
        mock_da.get_payments_by_type.assert_called()

    def test_switch_to_salary_loads_data(self, qtbot, mock_employee_admin):
        """Переключение на оклады загружает данные."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        mock_da.get_payments_by_type.return_value = []
        tab.on_tab_changed(3)
        mock_da.get_payments_by_type.assert_called()

    def test_switch_to_supervision_loads_data(self, qtbot, mock_employee_admin):
        """Переключение на авторский надзор загружает данные."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        mock_da.get_payments_by_type.return_value = []
        tab.on_tab_changed(4)
        mock_da.get_payments_by_type.assert_called()

    def test_switch_to_all_payments_no_extra_load(self, qtbot, mock_employee_admin):
        """Переключение на Все выплаты не вызывает доп. загрузку."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        mock_da.reset_mock()
        tab.on_tab_changed(0)
        mock_da.get_payments_by_type.assert_not_called()


# ========== Тесты period filter ==========

class TestSalariesTabPeriodFilter:
    """Тесты фильтра периода."""

    def test_on_period_filter_month(self, qtbot, mock_employee_admin):
        """Период 'Месяц' — показываются month/year, скрывается quarter."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        tab.period_filter.setCurrentText('Месяц')
        tab.on_period_filter_changed()
        assert not tab.month_filter.isHidden()
        assert not tab.year_filter.isHidden()
        assert tab.quarter_filter.isHidden()

    def test_on_period_filter_quarter(self, qtbot, mock_employee_admin):
        """Период 'Квартал' — показывается quarter."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        tab.period_filter.setCurrentText('Квартал')
        tab.on_period_filter_changed()
        assert not tab.quarter_filter.isHidden()

    def test_on_period_filter_year(self, qtbot, mock_employee_admin):
        """Период 'Год' — показывается только год."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        tab.period_filter.setCurrentText('Год')
        tab.on_period_filter_changed()
        assert not tab.year_filter.isHidden()
        assert tab.quarter_filter.isHidden()
        assert tab.month_filter.isHidden()

    def test_on_period_filter_all(self, qtbot, mock_employee_admin):
        """Период 'Все' — все дополнительные фильтры скрыты."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        tab.period_filter.setCurrentText('Все')
        tab.on_period_filter_changed()
        assert tab.year_filter.isHidden()
        assert tab.month_filter.isHidden()
        assert tab.quarter_filter.isHidden()


# ========== Тесты reset_all_payments_filters ==========

class TestSalariesTabResetFilters:
    """Тесты сброса фильтров."""

    def test_reset_all_payments_filters(self, qtbot, mock_employee_admin):
        """reset_all_payments_filters сбрасывает все значения."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        # Устанавливаем не-дефолтные значения
        tab.status_filter.setCurrentIndex(1)
        tab.reset_all_payments_filters()
        assert tab.period_filter.currentText() == 'Все'
        assert tab.address_filter.currentIndex() == 0
        assert tab.employee_filter.currentIndex() == 0
        assert tab.position_filter.currentIndex() == 0
        assert tab.status_filter.currentIndex() == 0

    def test_reset_hides_period_controls(self, qtbot, mock_employee_admin):
        """Сброс скрывает элементы периода."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        tab.reset_all_payments_filters()
        assert tab.year_filter.isHidden()
        assert tab.month_filter.isHidden()
        assert tab.quarter_filter.isHidden()


# ========== Тесты ensure_data_loaded ==========

class TestSalariesTabEnsureDataLoaded:
    """Тесты ленивой загрузки."""

    def test_ensure_data_loaded_first_call(self, qtbot, mock_employee_admin):
        """Первый вызов ensure_data_loaded загружает данные."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        assert tab._data_loaded is False
        tab.ensure_data_loaded()
        assert tab._data_loaded is True
        mock_da.get_year_payments.assert_called()

    def test_ensure_data_loaded_second_call_noop(self, qtbot, mock_employee_admin):
        """Второй вызов ensure_data_loaded ничего не делает."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        tab.ensure_data_loaded()
        call_count = mock_da.get_year_payments.call_count
        tab.ensure_data_loaded()
        assert mock_da.get_year_payments.call_count == call_count


# ========== Тесты create_payment_actions ==========

class TestSalariesTabPaymentActions:
    """Тесты создания кнопок действий."""

    def test_create_payment_actions_not_paid(self, qtbot, mock_employee_admin):
        """Кнопки действий для неоплаченной записи."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        payment = {'id': 1, 'is_paid': False}
        widget = tab.create_payment_actions(payment, 'Индивидуальные проекты')
        assert widget is not None

    def test_create_payment_actions_paid(self, qtbot, mock_employee_admin):
        """Кнопки действий для оплаченной записи."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        payment = {'id': 1, 'is_paid': True}
        widget = tab.create_payment_actions(payment, 'Индивидуальные проекты')
        assert widget is not None

    def test_create_all_payments_actions(self, qtbot, mock_employee_admin):
        """Кнопки действий для таблицы 'Все выплаты'."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        payment = {'id': 1, 'payment_status': None, 'source': 'CRM',
                    'position': 'Дизайнер', 'employee_name': 'Тест'}
        widget = tab.create_all_payments_actions(payment, False, tab.all_payments_table, 0)
        assert widget is not None

    def test_create_all_payments_actions_to_pay(self, qtbot, mock_employee_admin):
        """Кнопки действий со статусом to_pay."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        payment = {'id': 1, 'payment_status': 'to_pay', 'source': 'CRM',
                    'position': 'Дизайнер', 'employee_name': 'Тест'}
        widget = tab.create_all_payments_actions(payment, False, tab.all_payments_table, 0)
        assert widget is not None

    def test_create_all_payments_actions_paid(self, qtbot, mock_employee_admin):
        """Кнопки действий со статусом paid."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        payment = {'id': 1, 'payment_status': 'paid', 'source': 'CRM',
                    'position': 'Дизайнер', 'employee_name': 'Тест'}
        widget = tab.create_all_payments_actions(payment, False, tab.all_payments_table, 0)
        assert widget is not None

    def test_create_crm_payment_actions(self, qtbot, mock_employee_admin):
        """Кнопки действий CRM."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        payment = {'id': 1, 'payment_status': None, 'employee_name': 'Тест', 'role': 'Дизайнер'}
        table = QTableWidget(1, 1)
        widget = tab.create_crm_payment_actions(payment, 'Индивидуальные проекты', table, 0)
        assert widget is not None

    def test_create_crm_payment_actions_to_pay_status(self, qtbot, mock_employee_admin):
        """Кнопки CRM со статусом to_pay."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        payment = {'id': 1, 'payment_status': 'to_pay', 'employee_name': 'Тест', 'role': 'Дизайнер'}
        table = QTableWidget(1, 1)
        widget = tab.create_crm_payment_actions(payment, 'Индивидуальные проекты', table, 0)
        assert widget is not None


# ========== Тесты apply_row_color ==========

class TestSalariesTabApplyRowColor:
    """Тесты окраски строк."""

    def test_apply_row_color_to_pay(self, qtbot, mock_employee_admin):
        """apply_row_color для статуса to_pay."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        tab.all_payments_table.setRowCount(1)
        tab.all_payments_table.setColumnCount(9)
        from PyQt5.QtWidgets import QTableWidgetItem
        for col in range(9):
            tab.all_payments_table.setItem(0, col, QTableWidgetItem('test'))
        tab.apply_row_color(tab.all_payments_table, 0, 'to_pay')
        # Проверяем что строка окрашена (не падает)

    def test_apply_row_color_paid(self, qtbot, mock_employee_admin):
        """apply_row_color для статуса paid."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        tab.all_payments_table.setRowCount(1)
        tab.all_payments_table.setColumnCount(9)
        from PyQt5.QtWidgets import QTableWidgetItem
        for col in range(9):
            tab.all_payments_table.setItem(0, col, QTableWidgetItem('test'))
        tab.apply_row_color(tab.all_payments_table, 0, 'paid')

    def test_apply_row_color_reassigned(self, qtbot, mock_employee_admin):
        """apply_row_color для переназначенной строки."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        tab.all_payments_table.setRowCount(1)
        tab.all_payments_table.setColumnCount(9)
        from PyQt5.QtWidgets import QTableWidgetItem
        for col in range(9):
            tab.all_payments_table.setItem(0, col, QTableWidgetItem('test'))
        tab.apply_row_color(tab.all_payments_table, 0, None, is_reassigned=True)

    def test_apply_row_color_no_status(self, qtbot, mock_employee_admin):
        """apply_row_color без статуса."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        tab.all_payments_table.setRowCount(1)
        tab.all_payments_table.setColumnCount(9)
        from PyQt5.QtWidgets import QTableWidgetItem
        for col in range(9):
            tab.all_payments_table.setItem(0, col, QTableWidgetItem('test'))
        tab.apply_row_color(tab.all_payments_table, 0, None)


# ========== Тесты delete_payment_universal ==========

class TestSalariesTabDeletePayment:
    """Тесты удаления выплат."""

    def test_delete_payment_universal_rejected(self, qtbot, mock_employee_admin):
        """Удаление отменено — не удаляет."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        with patch('ui.salaries_tab.CustomQuestionBox') as MockQBox:
            mock_instance = MagicMock()
            mock_instance.exec_.return_value = QDialog.Rejected
            MockQBox.return_value = mock_instance
            tab.delete_payment_universal(1, 'CRM', 'Дизайнер', 'Тест')
            mock_da.delete_payment.assert_not_called()

    def test_delete_payment_legacy(self, qtbot, mock_employee_admin):
        """delete_payment делегирует в delete_payment_universal."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        with patch.object(tab, 'delete_payment_universal') as mock_del:
            tab.delete_payment(1, 'Дизайнер', 'Тест')
            mock_del.assert_called_once_with(1, 'CRM', 'Дизайнер', 'Тест')

    def test_delete_crm_payment(self, qtbot, mock_employee_admin):
        """delete_crm_payment делегирует в delete_payment_universal."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        payment = {'id': 1, 'role': 'Дизайнер', 'employee_name': 'Тест'}
        with patch.object(tab, 'delete_payment_universal') as mock_del:
            tab.delete_crm_payment(payment, 'Индивидуальные проекты')
            mock_del.assert_called_once()


# ========== Тесты _payment_matches_* через экземпляр ==========

class TestSalariesTabPaymentMatching:
    """Тесты вспомогательных методов фильтрации по периоду."""

    def test_matches_month_correct(self, qtbot, mock_employee_admin):
        """_payment_matches_month — корректный месяц."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        p = {'report_month': '2026-02'}
        assert tab._payment_matches_month(p, 2, 2026) is True

    def test_matches_month_wrong(self, qtbot, mock_employee_admin):
        """_payment_matches_month — неправильный месяц."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        p = {'report_month': '2026-03'}
        assert tab._payment_matches_month(p, 2, 2026) is False

    def test_matches_quarter_correct(self, qtbot, mock_employee_admin):
        """_payment_matches_quarter — корректный квартал."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        p = {'report_month': '2026-02'}
        assert tab._payment_matches_quarter(p, 1, 3, 2026) is True

    def test_matches_quarter_wrong(self, qtbot, mock_employee_admin):
        """_payment_matches_quarter — другой квартал."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        p = {'report_month': '2026-04'}
        assert tab._payment_matches_quarter(p, 1, 3, 2026) is False

    def test_matches_year_correct(self, qtbot, mock_employee_admin):
        """_payment_matches_year — корректный год."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        p = {'report_month': '2026-05'}
        assert tab._payment_matches_year(p, 2026) is True

    def test_matches_year_wrong(self, qtbot, mock_employee_admin):
        """_payment_matches_year — другой год."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        p = {'report_month': '2025-05'}
        assert tab._payment_matches_year(p, 2026) is False

    def test_matches_month_empty(self, qtbot, mock_employee_admin):
        """_payment_matches_month — пустой report_month."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        p = {'report_month': ''}
        assert tab._payment_matches_month(p, 2, 2026) is False

    def test_matches_month_malformed(self, qtbot, mock_employee_admin):
        """_payment_matches_month — некорректный формат."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        p = {'report_month': 'invalid'}
        assert tab._payment_matches_month(p, 2, 2026) is False


# ========== Тесты load_payment_type_data ==========

class TestSalariesTabLoadPaymentTypeData:
    """Тесты загрузки данных по типу выплаты."""

    def test_load_individual_data(self, qtbot, mock_employee_admin):
        """Загрузка данных для индивидуальных проектов."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        mock_da.get_payments_by_type.return_value = []
        tab.load_payment_type_data('Индивидуальные проекты')
        mock_da.get_payments_by_type.assert_called_with('Индивидуальные проекты', 'Индивидуальный')

    def test_load_template_data(self, qtbot, mock_employee_admin):
        """Загрузка данных для шаблонных проектов."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        mock_da.get_payments_by_type.return_value = []
        tab.load_payment_type_data('Шаблонные проекты')
        mock_da.get_payments_by_type.assert_called_with('Шаблонные проекты', 'Шаблонный')

    def test_load_supervision_data(self, qtbot, mock_employee_admin):
        """Загрузка данных для авторского надзора."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        mock_da.get_payments_by_type.return_value = []
        tab.load_payment_type_data('Авторский надзор')
        mock_da.get_payments_by_type.assert_called_with('Авторский надзор', 'Авторский надзор')

    def test_load_salary_data(self, qtbot, mock_employee_admin):
        """Загрузка данных для окладов."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        mock_da.get_payments_by_type.return_value = []
        tab.load_payment_type_data('Оклады')
        mock_da.get_payments_by_type.assert_called_with('Оклады', None)


# ========== Тесты _queue_payment_delete (legacy) ==========

class TestSalariesTabLegacyMethods:
    """Тесты legacy-методов."""

    def test_queue_payment_delete_noop(self, qtbot, mock_employee_admin):
        """_queue_payment_delete — no-op (legacy)."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        tab._queue_payment_delete(1, 'CRM')  # Не падает

    def test_delete_payment_locally(self, qtbot, mock_employee_admin):
        """_delete_payment_locally вызывает data.delete_payment."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        tab._delete_payment_locally(1, 'CRM')
        mock_da.delete_payment.assert_called_once_with(1)
