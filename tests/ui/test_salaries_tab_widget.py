# -*- coding: utf-8 -*-
"""
Тесты для SalariesTab — вкладка управления зарплатами и платежами.

Проверяется создание виджета, наличие элементов UI (фильтры, вкладки, таблицы),
базовое взаимодействие (переключение вкладок, фильтров) и итоговые суммы.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import (QApplication, QTabWidget, QLabel, QPushButton,
                              QTableWidget, QComboBox, QSpinBox)
from PyQt5.QtCore import Qt
from unittest.mock import patch, MagicMock


# ========== Вспомогательные функции ==========

def _make_mock_data_access(payments=None, year_payments=None):
    """Создать MagicMock DataAccess для SalariesTab."""
    mock_da = MagicMock()
    mock_da.get_all_payments.return_value = payments or []
    mock_da.get_year_payments.return_value = year_payments or []
    mock_da.get_all_employees.return_value = []
    mock_da.get_all_contracts.return_value = []
    mock_da.db = MagicMock()
    mock_da.is_online = False
    mock_da.prefer_local = False
    return mock_da


class _FakeIconLoader:
    """Fake IconLoader — возвращает реальные Qt-объекты, без MagicMock."""
    @staticmethod
    def load(*args, **kwargs):
        from PyQt5.QtGui import QIcon
        return QIcon()
    @staticmethod
    def load_colored(*args, **kwargs):
        from PyQt5.QtGui import QIcon
        return QIcon()
    @staticmethod
    def create_action_button(*args, **kwargs):
        return QPushButton()
    @staticmethod
    def create_icon_button(*args, **kwargs):
        return QPushButton()


def _create_salaries_tab(qtbot, employee, mock_da=None):
    """Создать SalariesTab с замоканными зависимостями."""
    if mock_da is None:
        mock_da = _make_mock_data_access()
    with patch('ui.salaries_tab.DataAccess', return_value=mock_da), \
         patch('ui.salaries_tab.IconLoader', _FakeIconLoader):
        from ui.salaries_tab import SalariesTab
        tab = SalariesTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab, mock_da


# ========== Тестовые данные ==========

SAMPLE_PAYMENTS = [
    {
        'id': 1, 'employee_name': 'Иванов И.И.', 'position': 'Дизайнер',
        'amount': 50000.0, 'payment_type': 'Индивидуальные проекты',
        'payment_subtype': 'Аванс', 'contract_address': 'ул. Тестовая, д.1',
        'report_month': '2026-01', 'status': 'to_pay', 'agent_type': '',
        'source': 'CRM'
    },
    {
        'id': 2, 'employee_name': 'Петров П.П.', 'position': 'Чертёжник',
        'amount': 30000.0, 'payment_type': 'Шаблонные проекты',
        'payment_subtype': 'Доплата', 'contract_address': 'ул. Другая, д.5',
        'report_month': '2026-02', 'status': 'paid', 'agent_type': 'Петрович',
        'source': 'CRM'
    },
    {
        'id': 3, 'employee_name': 'Сидоров С.С.', 'position': 'ГАП',
        'amount': 80000.0, 'payment_type': 'Оклады',
        'payment_subtype': 'Оклад', 'contract_address': '',
        'report_month': '2026-01', 'status': 'paid', 'agent_type': '',
        'source': 'salaries'
    },
]


class TestSalariesTabCreation:
    """Тесты создания и инициализации SalariesTab."""

    def test_create_widget(self, qtbot, mock_employee_admin):
        """SalariesTab создаётся без ошибок."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert tab is not None

    def test_widget_is_visible(self, qtbot, mock_employee_admin):
        """SalariesTab видим после создания (show)."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        tab.show()
        assert tab.isVisible()

    def test_data_access_initialized(self, qtbot, mock_employee_admin):
        """Атрибут data (DataAccess) инициализирован."""
        tab, mock_da = _create_salaries_tab(qtbot, mock_employee_admin)
        assert tab.data is mock_da

    def test_employee_stored(self, qtbot, mock_employee_admin):
        """Атрибут employee сохраняет переданного сотрудника."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert tab.employee == mock_employee_admin


class TestSalariesTabTabs:
    """Тесты наличия и структуры вкладок QTabWidget."""

    def test_has_tabs_widget(self, qtbot, mock_employee_admin):
        """SalariesTab содержит QTabWidget."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'tabs')
        assert isinstance(tab.tabs, QTabWidget)

    def test_tab_count(self, qtbot, mock_employee_admin):
        """Должно быть 5 вкладок: Все выплаты, Индивидуальные, Шаблонные, Оклады, Авторский надзор."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert tab.tabs.count() == 5

    def test_tab_names(self, qtbot, mock_employee_admin):
        """Проверка названий вкладок."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        expected_names = [
            'Все выплаты', 'Индивидуальные проекты',
            'Шаблонные проекты', 'Оклады', 'Авторский надзор'
        ]
        for i, name in enumerate(expected_names):
            assert name in tab.tabs.tabText(i), \
                f"Вкладка {i}: ожидалось '{name}', получено '{tab.tabs.tabText(i)}'"

    def test_default_tab_is_first(self, qtbot, mock_employee_admin):
        """По умолчанию выбрана первая вкладка (Все выплаты)."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert tab.tabs.currentIndex() == 0

    def test_switch_to_individual_tab(self, qtbot, mock_employee_admin):
        """Переключение на вкладку 'Индивидуальные проекты'."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        tab.tabs.setCurrentIndex(1)
        assert tab.tabs.currentIndex() == 1


class TestSalariesTabFilters:
    """Тесты наличия и работы фильтров."""

    def test_has_period_filter(self, qtbot, mock_employee_admin):
        """Наличие фильтра периода."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'period_filter')

    def test_period_filter_items(self, qtbot, mock_employee_admin):
        """Фильтр периода содержит варианты: Месяц, Квартал, Год, Все."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        items = [tab.period_filter.itemText(i) for i in range(tab.period_filter.count())]
        assert 'Месяц' in items
        assert 'Квартал' in items
        assert 'Год' in items
        assert 'Все' in items

    def test_period_filter_default_all(self, qtbot, mock_employee_admin):
        """Фильтр периода по умолчанию = 'Все' на вкладке Все выплаты."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert tab.period_filter.currentText() == 'Все'

    def test_has_year_filter(self, qtbot, mock_employee_admin):
        """Наличие фильтра года."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'year_filter')

    def test_has_month_filter(self, qtbot, mock_employee_admin):
        """Наличие фильтра месяца."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'month_filter')

    def test_has_status_filter(self, qtbot, mock_employee_admin):
        """Наличие фильтра статуса."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'status_filter')

    def test_status_filter_items(self, qtbot, mock_employee_admin):
        """Фильтр статуса содержит: Все, К оплате, Оплачено."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        items = [tab.status_filter.itemText(i) for i in range(tab.status_filter.count())]
        assert 'Все' in items
        assert 'К оплате' in items
        assert 'Оплачено' in items

    def test_has_address_filter(self, qtbot, mock_employee_admin):
        """Наличие фильтра адреса."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'address_filter')

    def test_has_employee_filter(self, qtbot, mock_employee_admin):
        """Наличие фильтра исполнителя."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'employee_filter')

    def test_has_position_filter(self, qtbot, mock_employee_admin):
        """Наличие фильтра должности."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'position_filter')

    def test_has_payment_subtype_filter(self, qtbot, mock_employee_admin):
        """Наличие фильтра типа выплаты."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'payment_subtype_filter')

    def test_has_project_type_filter(self, qtbot, mock_employee_admin):
        """Наличие фильтра типа проекта."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'project_type_filter')

    def test_has_agent_type_filter(self, qtbot, mock_employee_admin):
        """Наличие фильтра типа агента."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'agent_type_filter')

    def test_has_reset_button(self, qtbot, mock_employee_admin):
        """Наличие кнопки сброса фильтров."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'all_reset_btn')
        assert isinstance(tab.all_reset_btn, QPushButton)


class TestSalariesTabTable:
    """Тесты таблицы платежей."""

    def test_has_all_payments_table(self, qtbot, mock_employee_admin):
        """Наличие таблицы всех выплат."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'all_payments_table')

    def test_table_column_count(self, qtbot, mock_employee_admin):
        """Таблица всех выплат имеет 9 столбцов."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert tab.all_payments_table.columnCount() == 9

    def test_table_column_headers(self, qtbot, mock_employee_admin):
        """Проверка заголовков столбцов таблицы."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        expected = [
            'Тип проекта', 'Тип агента', 'Исполнитель', 'Должность',
            'Сумма к выплате', 'Тип выплаты', 'Адрес договора',
            'Отчетный месяц', 'Действия'
        ]
        for i, header_text in enumerate(expected):
            item = tab.all_payments_table.horizontalHeaderItem(i)
            assert item is not None, f"Столбец {i} не имеет заголовка"
            assert header_text == item.text(), \
                f"Столбец {i}: ожидалось '{header_text}', получено '{item.text()}'"

    def test_empty_table_on_init(self, qtbot, mock_employee_admin):
        """При пустых данных таблица имеет 0 строк."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert tab.all_payments_table.rowCount() == 0

    def test_has_totals_label(self, qtbot, mock_employee_admin):
        """Наличие лейбла итогов."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'totals_label')
        assert isinstance(tab.totals_label, QLabel)


class TestSalariesTabCache:
    """Тесты кеширования данных."""

    def test_cache_initially_none(self, qtbot, mock_employee_admin):
        """Кеш платежей изначально None."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert tab._all_payments_cache is None
        assert tab._cache_year is None

    def test_invalidate_cache(self, qtbot, mock_employee_admin):
        """invalidate_cache сбрасывает кеш."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        tab._all_payments_cache = [1, 2, 3]
        tab._cache_year = 2026
        tab._payment_type_cache = {'test': []}
        tab.invalidate_cache()
        assert tab._all_payments_cache is None
        assert tab._cache_year is None
        assert tab._payment_type_cache == {}


class TestSalariesTabMonthsMapping:
    """Тесты вспомогательных данных."""

    def test_months_ru_list(self, qtbot, mock_employee_admin):
        """Список русских месяцев содержит 12 элементов."""
        tab, _ = _create_salaries_tab(qtbot, mock_employee_admin)
        assert len(tab._months_ru) == 12
        assert tab._months_ru[0] == 'Январь'
        assert tab._months_ru[11] == 'Декабрь'
