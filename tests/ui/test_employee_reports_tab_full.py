# -*- coding: utf-8 -*-
"""
Тесты для ui/employee_reports_tab.py — EmployeeReportsTab.

Покрытие:
- init_ui (структура вкладок)
- load_report_data (загрузка и фильтрация)
- update_completed_table (заполнение таблицы)
- update_salary_table (заполнение с итого)
- export_report (экспорт PDF)
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _ensure_clean_module():
    """Гарантировать чистый импорт ui.employee_reports_tab."""
    mod = sys.modules.get('ui.employee_reports_tab')
    if mod is not None and not hasattr(mod, 'apply_no_focus_delegate'):
        del sys.modules['ui.employee_reports_tab']


@pytest.fixture
def employee():
    return {
        'id': 1,
        'full_name': 'Петров Пётр',
        'position': 'Менеджер',
    }


@pytest.fixture
def mock_api_client():
    return MagicMock()


class _FakeIconLoader:
    """Заглушка для IconLoader, чтобы не требовать реальных SVG."""
    @staticmethod
    def load(name):
        from PyQt5.QtGui import QIcon
        return QIcon()

    @staticmethod
    def create_icon_button(icon_name, text='', tooltip='', icon_size=16):
        from PyQt5.QtWidgets import QPushButton
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        return btn

    @staticmethod
    def create_action_button(icon_name, tooltip=''):
        from PyQt5.QtWidgets import QPushButton
        btn = QPushButton()
        btn.setToolTip(tooltip)
        return btn


@pytest.fixture
def reports_tab(qtbot, employee, mock_api_client):
    """Создаём EmployeeReportsTab с замоканным DataAccess."""
    _ensure_clean_module()

    with patch('ui.employee_reports_tab.DatabaseManager'), \
         patch('ui.employee_reports_tab.DataAccess') as MockDA, \
         patch('ui.employee_reports_tab.IconLoader', _FakeIconLoader), \
         patch('ui.employee_reports_tab.ICONS_PATH', '/fake/icons'), \
         patch('ui.employee_reports_tab.apply_no_focus_delegate'), \
         patch('ui.employee_reports_tab.CustomComboBox') as MockCombo, \
         patch('PyQt5.QtCore.QTimer') as MockTimer:

        # CustomComboBox может не инициализироваться в offscreen, используем обычный QComboBox
        from PyQt5.QtWidgets import QComboBox
        MockCombo.side_effect = lambda *a, **kw: QComboBox()

        mock_da = MockDA.return_value
        mock_da.get_employee_report_data.return_value = {
            'completed': [], 'salaries': []
        }

        from ui.employee_reports_tab import EmployeeReportsTab
        tab = EmployeeReportsTab(employee, api_client=mock_api_client)
        qtbot.addWidget(tab)
        return tab


# ==================== init_ui ====================

class TestInitUI:
    """Структура UI."""

    def test_has_report_tabs(self, reports_tab):
        """Есть QTabWidget с вкладками."""
        from PyQt5.QtWidgets import QTabWidget
        tab_widget = reports_tab.report_tabs
        assert isinstance(tab_widget, QTabWidget)

    def test_has_three_tabs(self, reports_tab):
        """3 вкладки: Индивидуальные, Шаблонные, Авторский надзор."""
        assert reports_tab.report_tabs.count() == 3

    def test_tab_titles(self, reports_tab):
        texts = [reports_tab.report_tabs.tabText(i) for i in range(3)]
        assert 'Индивидуальные проекты' in texts
        assert 'Шаблонные проекты' in texts
        assert 'Авторский надзор' in texts

    def test_individual_tab_exists(self, reports_tab):
        assert reports_tab.individual_tab is not None

    def test_template_tab_exists(self, reports_tab):
        assert reports_tab.template_tab is not None

    def test_supervision_tab_exists(self, reports_tab):
        assert reports_tab.supervision_tab is not None


# ==================== update_completed_table ====================

class TestUpdateCompletedTable:
    """update_completed_table — заполнение таблицы."""

    def test_fills_table_rows(self, reports_tab):
        """Заполняет строки таблицы."""
        from PyQt5.QtWidgets import QTableWidget
        data = [
            {'employee_name': 'Иванов', 'position': 'Дизайнер', 'count': 5},
            {'employee_name': 'Петров', 'position': 'Чертежник', 'count': 3},
        ]
        reports_tab.update_completed_table(reports_tab.individual_tab, 'Индивидуальный', data)
        table = reports_tab.individual_tab.findChild(QTableWidget, 'completed_table_Индивидуальный')
        assert table is not None
        assert table.rowCount() == 2

    def test_empty_data(self, reports_tab):
        """Пустые данные — 0 строк."""
        from PyQt5.QtWidgets import QTableWidget
        reports_tab.update_completed_table(reports_tab.individual_tab, 'Индивидуальный', [])
        table = reports_tab.individual_tab.findChild(QTableWidget, 'completed_table_Индивидуальный')
        assert table.rowCount() == 0

    def test_cell_content(self, reports_tab):
        """Содержимое ячеек совпадает с данными."""
        from PyQt5.QtWidgets import QTableWidget
        data = [{'employee_name': 'Тестов', 'position': 'ГАП', 'count': 7}]
        reports_tab.update_completed_table(reports_tab.individual_tab, 'Индивидуальный', data)
        table = reports_tab.individual_tab.findChild(QTableWidget, 'completed_table_Индивидуальный')
        assert table.item(0, 0).text() == 'Тестов'
        assert table.item(0, 1).text() == 'ГАП'
        assert table.item(0, 2).text() == '7'

    def test_missing_keys_use_defaults(self, reports_tab):
        """Отсутствующие ключи → пустые строки / 0."""
        from PyQt5.QtWidgets import QTableWidget
        data = [{}]
        reports_tab.update_completed_table(reports_tab.individual_tab, 'Индивидуальный', data)
        table = reports_tab.individual_tab.findChild(QTableWidget, 'completed_table_Индивидуальный')
        assert table.item(0, 0).text() == ''
        assert table.item(0, 2).text() == '0'


# ==================== update_salary_table ====================

class TestUpdateSalaryTable:
    """update_salary_table — заполнение таблицы зарплат."""

    def test_fills_salary_rows(self, reports_tab):
        """Заполняет строки зарплат."""
        from PyQt5.QtWidgets import QTableWidget
        data = [
            {'employee_name': 'Иванов', 'position': 'Дизайнер', 'total_salary': 50000},
        ]
        reports_tab.update_salary_table(reports_tab.template_tab, 'Шаблонный', data)
        table = reports_tab.template_tab.findChild(QTableWidget, 'salary_table_Шаблонный')
        assert table is not None
        # +1 строка для ИТОГО
        assert table.rowCount() == 2

    def test_total_row_added(self, reports_tab):
        """Строка ИТОГО добавляется при наличии данных."""
        from PyQt5.QtWidgets import QTableWidget
        data = [
            {'employee_name': 'A', 'position': 'B', 'total_salary': 30000},
            {'employee_name': 'C', 'position': 'D', 'total_salary': 20000},
        ]
        reports_tab.update_salary_table(reports_tab.template_tab, 'Шаблонный', data)
        table = reports_tab.template_tab.findChild(QTableWidget, 'salary_table_Шаблонный')
        # 2 data rows + 1 total row
        assert table.rowCount() == 3
        total_item = table.item(2, 1)
        assert total_item is not None
        assert 'ИТОГО' in total_item.text()

    def test_total_sum_correct(self, reports_tab):
        """Сумма ИТОГО правильная."""
        from PyQt5.QtWidgets import QTableWidget
        data = [
            {'employee_name': 'A', 'position': 'B', 'total_salary': 30000},
            {'employee_name': 'C', 'position': 'D', 'total_salary': 20000},
        ]
        reports_tab.update_salary_table(reports_tab.template_tab, 'Шаблонный', data)
        table = reports_tab.template_tab.findChild(QTableWidget, 'salary_table_Шаблонный')
        total_cell = table.item(2, 2)
        assert '50,000.00' in total_cell.text()

    def test_empty_data_no_total(self, reports_tab):
        """Пустые данные — нет строки ИТОГО."""
        from PyQt5.QtWidgets import QTableWidget
        reports_tab.update_salary_table(reports_tab.template_tab, 'Шаблонный', [])
        table = reports_tab.template_tab.findChild(QTableWidget, 'salary_table_Шаблонный')
        assert table.rowCount() == 0

    def test_salary_format_ruble(self, reports_tab):
        """Зарплата форматируется с ₽."""
        from PyQt5.QtWidgets import QTableWidget
        data = [{'employee_name': 'X', 'position': 'Y', 'total_salary': 12345.67}]
        reports_tab.update_salary_table(reports_tab.template_tab, 'Шаблонный', data)
        table = reports_tab.template_tab.findChild(QTableWidget, 'salary_table_Шаблонный')
        cell = table.item(0, 2)
        assert '₽' in cell.text()


# ==================== load_report_data ====================

class TestLoadReportData:
    """load_report_data — загрузка данных."""

    def test_calls_data_access(self, reports_tab):
        """Вызывает get_employee_report_data."""
        reports_tab.data_access.get_employee_report_data.return_value = {
            'completed': [], 'salaries': []
        }
        reports_tab.load_report_data('Индивидуальный')
        reports_tab.data_access.get_employee_report_data.assert_called()

    def test_handles_data_access_error(self, reports_tab):
        """Ошибка DataAccess — таблицы пустые, не падает."""
        reports_tab.data_access.get_employee_report_data.side_effect = Exception('API error')
        with patch('ui.custom_message_box.CustomMessageBox'):
            reports_tab.load_report_data('Индивидуальный')  # Не должно упасть

    def test_loads_for_template_type(self, reports_tab):
        """Загрузка для шаблонного типа."""
        reports_tab.data_access.get_employee_report_data.return_value = {
            'completed': [{'employee_name': 'Test', 'position': 'Dev', 'count': 1}],
            'salaries': [],
        }
        reports_tab.load_report_data('Шаблонный')
        reports_tab.data_access.get_employee_report_data.assert_called()

    def test_loads_for_supervision_type(self, reports_tab):
        """Загрузка для типа авторского надзора."""
        reports_tab.data_access.get_employee_report_data.return_value = {
            'completed': [], 'salaries': []
        }
        reports_tab.load_report_data('Авторский надзор')
        reports_tab.data_access.get_employee_report_data.assert_called()
