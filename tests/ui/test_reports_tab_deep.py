# -*- coding: utf-8 -*-
"""
Глубокие тесты вкладки Отчёты — ReportsTab.

Покрытие:
  - TestReportsTabCreation (4)        — создание, вкладки, lazy-loading, атрибуты
  - TestReportsTabFilters (5)         — комбобоксы год/квартал/месяц/агент/город
  - TestReportsTabFilterLogic (4)     — on_quarter_changed, on_month_changed, reset_filters
  - TestReportsTabLoadStatistics (4)  — load_all_statistics, load_project_statistics, load_supervision
  - TestReportsTabAnalytics (4)       — _load_analytics_charts, кэш, _contract_month_in_range
  - TestReportsTabExport (2)          — export_full_report, perform_pdf_export
  - TestReportsTabCharts (2)          — create_chart, update_pie_chart
ИТОГО: 25 тестов
"""

import pytest
import logging
from unittest.mock import MagicMock, patch, PropertyMock, call
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QGroupBox,
    QComboBox, QDialog, QLabel
)
from PyQt5.QtCore import Qt
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


def _make_mock_da():
    """Создание MagicMock DataAccess для ReportsTab."""
    da = MagicMock()
    da.get_all_contracts.return_value = []
    da.get_project_statistics.return_value = {
        'total_orders': 0, 'total_area': 0.0,
        'active': 0, 'completed': 0, 'cancelled': 0, 'overdue': 0,
        'by_cities': {}, 'by_agents': {}
    }
    da.get_supervision_statistics_report.return_value = {
        'total_orders': 0, 'total_area': 0.0,
        'active': 0, 'completed': 0, 'cancelled': 0, 'overdue': 0,
        'by_cities': {}, 'by_agents': {}
    }
    da.get_funnel_statistics.return_value = {'funnel': {}}
    da.get_executor_load.return_value = []
    da.get_cities.return_value = ['СПБ', 'МСК']
    da.get_agent_types.return_value = ['Риелтор', 'Дизайнер']
    da.api_client = None
    da.db = MagicMock()
    return da


def _create_reports_tab(qtbot, employee, mock_da=None):
    """Создание ReportsTab с полностью замоканными зависимостями."""
    if mock_da is None:
        mock_da = _make_mock_da()

    mock_db = MagicMock()

    with patch('ui.reports_tab.DatabaseManager', return_value=mock_db), \
         patch('ui.reports_tab.DataAccess', return_value=mock_da), \
         patch('ui.reports_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.reports_tab.FunnelBarChart', return_value=QWidget()), \
         patch('ui.reports_tab.ExecutorLoadChart', return_value=QWidget()), \
         patch('ui.reports_tab.ProjectTypePieChart', return_value=QWidget()), \
         patch('ui.reports_tab.MATPLOTLIB_AVAILABLE', False):
        from ui.reports_tab import ReportsTab
        tab = ReportsTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        # Прикрепляем mock_da для удобства проверок
        tab._test_da = mock_da
        return tab


# ═══════════════════════════════════════════════════════════════════
# 1. Создание виджета (4 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestReportsTabCreation:
    """Инициализация ReportsTab — виджет, вкладки, lazy-loading."""

    def test_creates_as_qwidget(self, qtbot, mock_employee_admin):
        """ReportsTab создаётся как QWidget без исключений."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert isinstance(tab, QWidget)

    def test_has_tabs_widget(self, qtbot, mock_employee_admin):
        """У ReportsTab есть атрибут tabs типа QTabWidget."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'tabs')
        assert isinstance(tab.tabs, QTabWidget)

    def test_four_tabs_created(self, qtbot, mock_employee_admin):
        """Создаётся 4 вкладки: Индивидуальные, Шаблонные, Надзор, Аналитика."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert tab.tabs.count() == 4

    def test_data_loaded_false_initially(self, qtbot, mock_employee_admin):
        """_data_loaded = False до первого вызова ensure_data_loaded."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert tab._data_loaded is False


# ═══════════════════════════════════════════════════════════════════
# 2. Фильтры — комбобоксы (5 тестов)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestReportsTabFilters:
    """Комбобоксы фильтров: год, квартал, месяц, тип агента, город."""

    def test_year_combo_exists_and_populated(self, qtbot, mock_employee_admin):
        """Фильтр года содержит годы 2020-2040."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'year_combo')
        assert tab.year_combo.count() == 21  # 2020..2040 включительно

    def test_quarter_combo_has_5_items(self, qtbot, mock_employee_admin):
        """Фильтр квартала: Все, Q1, Q2, Q3, Q4."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'quarter_combo')
        items = [tab.quarter_combo.itemText(i) for i in range(tab.quarter_combo.count())]
        assert items == ['Все', 'Q1', 'Q2', 'Q3', 'Q4']

    def test_month_combo_has_13_items(self, qtbot, mock_employee_admin):
        """Фильтр месяца: Все + 12 месяцев."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'month_combo')
        assert tab.month_combo.count() == 13
        assert tab.month_combo.itemText(0) == 'Все'
        assert tab.month_combo.itemText(1) == 'Январь'
        assert tab.month_combo.itemText(12) == 'Декабрь'

    def test_agent_type_combo_loaded(self, qtbot, mock_employee_admin):
        """Фильтр типа агента загружается из DataAccess."""
        da = _make_mock_da()
        da.get_agent_types.return_value = ['Риелтор', 'Дизайнер']
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        assert hasattr(tab, 'agent_type_combo')
        # 'Все' + агенты
        assert tab.agent_type_combo.count() >= 1

    def test_city_combo_loaded(self, qtbot, mock_employee_admin):
        """Фильтр города загружается из DataAccess."""
        da = _make_mock_da()
        da.get_cities.return_value = ['СПБ', 'МСК', 'Казань']
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        assert hasattr(tab, 'city_combo')
        # 'Все' + города
        assert tab.city_combo.count() >= 1


# ═══════════════════════════════════════════════════════════════════
# 3. Логика фильтров (4 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestReportsTabFilterLogic:
    """Логика взаимодействия фильтров: квартал/месяц сброс, reset_filters."""

    def test_on_quarter_changed_resets_month(self, qtbot, mock_employee_admin):
        """При выборе квартала месяц сбрасывается на 'Все'."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        # Ставим месяц
        tab.month_combo.blockSignals(True)
        tab.month_combo.setCurrentText('Март')
        tab.month_combo.blockSignals(False)
        # Меняем квартал
        tab.quarter_combo.blockSignals(True)
        tab.quarter_combo.setCurrentText('Q2')
        tab.quarter_combo.blockSignals(False)
        tab.on_quarter_changed()
        assert tab.month_combo.currentText() == 'Все'

    def test_on_month_changed_resets_quarter(self, qtbot, mock_employee_admin):
        """При выборе месяца квартал сбрасывается на 'Все'."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        # Ставим квартал
        tab.quarter_combo.blockSignals(True)
        tab.quarter_combo.setCurrentText('Q3')
        tab.quarter_combo.blockSignals(False)
        # Меняем месяц
        tab.month_combo.blockSignals(True)
        tab.month_combo.setCurrentText('Июнь')
        tab.month_combo.blockSignals(False)
        tab.on_month_changed()
        assert tab.quarter_combo.currentText() == 'Все'

    def test_reset_filters_sets_defaults(self, qtbot, mock_employee_admin):
        """reset_filters() сбрасывает все фильтры на значения по умолчанию."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        # Меняем фильтры
        tab.quarter_combo.blockSignals(True)
        tab.quarter_combo.setCurrentText('Q1')
        tab.quarter_combo.blockSignals(False)
        tab.month_combo.blockSignals(True)
        tab.month_combo.setCurrentText('Февраль')
        tab.month_combo.blockSignals(False)
        # Сброс
        tab.reset_filters()
        assert tab.quarter_combo.currentText() == 'Все'
        assert tab.month_combo.currentText() == 'Все'
        assert tab.agent_type_combo.currentText() == 'Все'
        assert tab.city_combo.currentText() == 'Все'

    def test_ensure_data_loaded_calls_load_all(self, qtbot, mock_employee_admin):
        """ensure_data_loaded() устанавливает флаг и вызывает load_all_statistics."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        assert tab._data_loaded is False
        with patch.object(tab, 'load_all_statistics') as mock_load:
            tab.ensure_data_loaded()
        assert tab._data_loaded is True
        mock_load.assert_called_once()


# ═══════════════════════════════════════════════════════════════════
# 4. Загрузка статистики (4 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestReportsTabLoadStatistics:
    """Вызовы load_all_statistics, load_project_statistics, load_supervision_statistics."""

    def test_load_all_statistics_calls_sub_methods(self, qtbot, mock_employee_admin):
        """load_all_statistics вызывает load_project_statistics для обоих типов + supervision."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        with patch.object(tab, 'load_project_statistics') as mock_proj, \
             patch.object(tab, 'load_supervision_statistics') as mock_sup, \
             patch.object(tab, '_load_analytics_charts') as mock_charts:
            tab.load_all_statistics()
            # Два вызова: Индивидуальный и Шаблонный
            assert mock_proj.call_count == 2
            call_args = [c[0][0] for c in mock_proj.call_args_list]
            assert 'Индивидуальный' in call_args
            assert 'Шаблонный' in call_args
            mock_sup.assert_called_once()
            mock_charts.assert_called_once()

    def test_load_project_statistics_calls_data_access(self, qtbot, mock_employee_admin):
        """load_project_statistics вызывает data_access.get_project_statistics."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        with patch.object(tab, 'update_pie_chart'):
            tab.load_project_statistics('Индивидуальный', 2026, None, None, None, None)
        da.get_project_statistics.assert_called_once_with(
            project_type='Индивидуальный', year=2026,
            quarter=None, month=None, agent_type=None, city=None
        )

    def test_load_supervision_statistics_calls_data_access(self, qtbot, mock_employee_admin):
        """load_supervision_statistics вызывает data_access.get_supervision_statistics_report."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        with patch.object(tab, 'update_pie_chart'):
            tab.load_supervision_statistics(2026, None, None, None, None)
        da.get_supervision_statistics_report.assert_called_once_with(
            year=2026, quarter=None, month=None, agent_type=None, city=None
        )

    def test_load_project_statistics_handles_exception(self, qtbot, mock_employee_admin):
        """Ошибка в get_project_statistics не приводит к краху."""
        da = _make_mock_da()
        da.get_project_statistics.side_effect = Exception("Ошибка БД")
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        # Не должно поднимать исключение
        tab.load_project_statistics('Индивидуальный', 2026, None, None, None, None)


# ═══════════════════════════════════════════════════════════════════
# 5. Аналитика (4 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestReportsTabAnalytics:
    """_load_analytics_charts, кэширование, _contract_month_in_range."""

    def test_contract_month_in_range_true(self, qtbot, mock_employee_admin):
        """_contract_month_in_range возвращает True для даты в диапазоне."""
        from ui.reports_tab import ReportsTab
        contract = {'contract_date': '2026-03-15'}
        assert ReportsTab._contract_month_in_range(contract, 1, 3) is True

    def test_contract_month_in_range_false(self, qtbot, mock_employee_admin):
        """_contract_month_in_range возвращает False для даты вне диапазона."""
        from ui.reports_tab import ReportsTab
        contract = {'contract_date': '2026-07-01'}
        assert ReportsTab._contract_month_in_range(contract, 1, 3) is False

    def test_contract_month_in_range_empty_date(self, qtbot, mock_employee_admin):
        """_contract_month_in_range возвращает False для пустой даты."""
        from ui.reports_tab import ReportsTab
        contract = {'contract_date': ''}
        assert ReportsTab._contract_month_in_range(contract, 1, 12) is False

    def test_analytics_cache_prevents_reload(self, qtbot, mock_employee_admin):
        """Повторный вызов _load_analytics_charts с теми же параметрами использует кэш."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        # Первый вызов
        tab._load_analytics_charts(year=2026, quarter=None, month=None,
                                    agent_type=None, city=None)
        call_count_after_first = da.get_all_contracts.call_count
        # Второй вызов с теми же параметрами — кэш
        tab._load_analytics_charts(year=2026, quarter=None, month=None,
                                    agent_type=None, city=None)
        assert da.get_all_contracts.call_count == call_count_after_first


# ═══════════════════════════════════════════════════════════════════
# 6. Экспорт (2 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestReportsTabExport:
    """Экспорт полного отчёта в PDF."""

    def test_export_full_report_opens_dialog(self, qtbot, mock_employee_admin):
        """export_full_report() открывает диалог экспорта."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        with patch('ui.reports_tab.QDialog') as MockDialog:
            # Мокаем QDialog чтобы не блокировал exec_
            mock_dlg = MagicMock()
            MockDialog.return_value = mock_dlg
            # Просто проверяем что метод не падает и содержит диалог-логику
            # Мокаем exec_ самого диалога, создаваемого внутри
            with patch.object(QDialog, 'exec_', return_value=QDialog.Rejected):
                tab.export_full_report()

    def test_perform_pdf_export_no_folder_returns(self, qtbot, mock_employee_admin):
        """perform_pdf_export без выбора папки — ничего не происходит."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        parent_dialog = MagicMock()
        filename_input = MagicMock()
        filename_input.text.return_value = 'test_report'

        with patch('ui.reports_tab.QFileDialog.getExistingDirectory', return_value=''):
            tab.perform_pdf_export(parent_dialog, filename_input)
        # Диалог не должен быть принят (accept не вызван)
        parent_dialog.accept.assert_not_called()


# ═══════════════════════════════════════════════════════════════════
# 7. Графики (2 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestReportsTabCharts:
    """Создание и обновление графиков."""

    def test_create_chart_returns_groupbox(self, qtbot, mock_employee_admin):
        """create_chart возвращает QGroupBox с заданным objectName."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        chart = tab.create_chart('test_chart', 'Тестовый график')
        assert isinstance(chart, QGroupBox)
        assert chart.objectName() == 'test_chart'

    def test_update_pie_chart_no_matplotlib_no_crash(self, qtbot, mock_employee_admin):
        """update_pie_chart без matplotlib не падает (MATPLOTLIB_AVAILABLE=False)."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        # Вызов не должен поднимать исключение
        tab.update_pie_chart('nonexistent_chart', {'СПБ': 10, 'МСК': 5})
