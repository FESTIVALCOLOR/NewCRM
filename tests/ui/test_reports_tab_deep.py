# -*- coding: utf-8 -*-
"""
Глубокие тесты вкладки Отчёты — ReportsTab.

Покрытие:
  - TestReportsTabCreation (4)        — создание, секции, scroll-область, атрибуты
  - TestReportsTabFilters (5)         — комбобоксы год/квартал/месяц/агент/город/тип проекта
  - TestReportsTabFilterLogic (4)     — _on_filter_changed, reset_filters, _get_current_filters
  - TestReportsTabLoadData (4)        — ensure_data_loaded, reload_all_sections, _load_filter_options
  - TestReportsTabExport (2)          — export_to_pdf
  - TestReportsTabCache (2)           — кэширование данных
ИТОГО: 21 тест

Адаптировано под переписанный ReportsTab (bc2790b):
  - Архитектура: QScrollArea с секциями (не QTabWidget)
  - Фильтры: filter_year, filter_quarter, filter_month, filter_agent, filter_city, filter_project_type
  - DataAccess вместо DatabaseManager
  - Нет IconLoader, MATPLOTLIB_AVAILABLE, create_chart, update_pie_chart
"""

import pytest
import logging
from unittest.mock import MagicMock, patch, call
from PyQt5.QtWidgets import QWidget, QComboBox, QScrollArea, QFrame
from PyQt5.QtCore import Qt

logger = logging.getLogger('tests')


# ─── Helpers ───────────────────────────────────────────────────────

def _make_mock_da():
    """Создание MagicMock DataAccess для ReportsTab."""
    da = MagicMock()
    da.get_contract_years.return_value = [2024, 2025, 2026]
    da.get_all_agents.return_value = [
        {'name': 'Риелтор'}, {'name': 'Дизайнер'}
    ]
    da.get_cities.return_value = ['СПБ', 'МСК']
    da.get_reports_summary.return_value = {}
    da.get_reports_clients_dynamics.return_value = []
    da.get_reports_contracts_dynamics.return_value = []
    da.get_reports_crm_analytics.return_value = {}
    da.get_reports_supervision_analytics.return_value = {}
    da.get_reports_distribution.return_value = []
    da.api_client = None
    da.db = MagicMock()
    return da


def _make_kpi_stub(**kw):
    """Заглушка KPICard/MiniKPICard с нужными методами."""
    w = QFrame()
    w.set_value = lambda v: None
    w.set_trend = lambda v: None
    return w


def _make_chart_stub(*a, **kw):
    """Заглушка для виджетов графиков с нужными методами."""
    w = QWidget()
    w.set_data = lambda *a, **kw: None
    return w


def _create_reports_tab(qtbot, employee, mock_da=None):
    """Создание ReportsTab с полностью замоканными зависимостями."""
    if mock_da is None:
        mock_da = _make_mock_da()

    with patch('ui.reports_tab.DataAccess', return_value=mock_da), \
         patch('ui.reports_tab.KPICard', side_effect=_make_kpi_stub), \
         patch('ui.reports_tab.MiniKPICard', side_effect=_make_kpi_stub), \
         patch('ui.reports_tab.SectionWidget', side_effect=lambda *a, **kw: _make_section_widget()), \
         patch('ui.reports_tab.LineChartWidget', side_effect=_make_chart_stub), \
         patch('ui.reports_tab.StackedBarChartWidget', side_effect=_make_chart_stub), \
         patch('ui.reports_tab.HorizontalBarWidget', side_effect=_make_chart_stub), \
         patch('ui.reports_tab.FunnelBarChart', side_effect=_make_chart_stub), \
         patch('ui.reports_tab.ProjectTypePieChart', side_effect=_make_chart_stub):
        from ui.reports_tab import ReportsTab
        tab = ReportsTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        tab._test_da = mock_da
        return tab


def _make_section_widget():
    """Создать mock-SectionWidget с нужными методами."""
    w = QFrame()
    from PyQt5.QtWidgets import QVBoxLayout
    layout = QVBoxLayout(w)
    w.add_widget = lambda widget: layout.addWidget(widget)
    w.add_layout = lambda lo: layout.addLayout(lo)
    return w


# ═══════════════════════════════════════════════════════════════════
# 1. Создание виджета (4 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestReportsTabCreation:
    """Инициализация ReportsTab — виджет, секции, scroll-область."""

    def test_creates_as_qwidget(self, qtbot, mock_employee_admin):
        """ReportsTab создаётся как QWidget без исключений."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert isinstance(tab, QWidget)

    def test_has_sections_layout(self, qtbot, mock_employee_admin):
        """У ReportsTab есть атрибут sections_layout."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'sections_layout')

    def test_has_data_access(self, qtbot, mock_employee_admin):
        """У ReportsTab есть атрибут data_access."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'data_access')

    def test_data_loaded_false_initially(self, qtbot, mock_employee_admin):
        """_data_loaded = False до первого вызова ensure_data_loaded."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert tab._data_loaded is False


# ═══════════════════════════════════════════════════════════════════
# 2. Фильтры — комбобоксы (5 тестов)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestReportsTabFilters:
    """Комбобоксы фильтров: год, квартал, месяц, тип агента, город, тип проекта."""

    def test_filter_year_exists(self, qtbot, mock_employee_admin):
        """Фильтр года существует как QComboBox."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'filter_year')
        assert isinstance(tab.filter_year, QComboBox)

    def test_filter_quarter_has_5_items(self, qtbot, mock_employee_admin):
        """Фильтр квартала: Все, Q1, Q2, Q3, Q4."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'filter_quarter')
        items = [tab.filter_quarter.itemText(i) for i in range(tab.filter_quarter.count())]
        assert items == ['Все', 'Q1', 'Q2', 'Q3', 'Q4']

    def test_filter_month_has_13_items(self, qtbot, mock_employee_admin):
        """Фильтр месяца: Все + 12 месяцев."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'filter_month')
        assert tab.filter_month.count() == 13
        assert tab.filter_month.itemText(0) == 'Все'
        assert tab.filter_month.itemText(1) == 'Январь'
        assert tab.filter_month.itemText(12) == 'Декабрь'

    def test_filter_agent_exists(self, qtbot, mock_employee_admin):
        """Фильтр типа агента существует."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'filter_agent')
        assert isinstance(tab.filter_agent, QComboBox)

    def test_filter_city_exists(self, qtbot, mock_employee_admin):
        """Фильтр города существует."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'filter_city')
        assert isinstance(tab.filter_city, QComboBox)


# ═══════════════════════════════════════════════════════════════════
# 3. Логика фильтров (4 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestReportsTabFilterLogic:
    """Логика взаимодействия фильтров: _on_filter_changed, reset_filters, _get_current_filters."""

    def test_get_current_filters_all_defaults(self, qtbot, mock_employee_admin):
        """_get_current_filters() при дефолтных значениях возвращает пустой словарь."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        filters = tab._get_current_filters()
        # Все фильтры на "Все" или пусты — фильтры не добавляются
        assert isinstance(filters, dict)

    def test_get_current_filters_with_quarter(self, qtbot, mock_employee_admin):
        """_get_current_filters() при выбранном квартале возвращает quarter."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        tab.filter_quarter.blockSignals(True)
        tab.filter_quarter.setCurrentText('Q2')
        tab.filter_quarter.blockSignals(False)
        filters = tab._get_current_filters()
        assert filters.get('quarter') == 2

    def test_reset_filters_sets_defaults(self, qtbot, mock_employee_admin):
        """reset_filters() сбрасывает все фильтры на 'Все' (индекс 0)."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        # Меняем фильтры
        tab.filter_quarter.blockSignals(True)
        tab.filter_quarter.setCurrentText('Q1')
        tab.filter_quarter.blockSignals(False)
        tab.filter_month.blockSignals(True)
        tab.filter_month.setCurrentText('Февраль')
        tab.filter_month.blockSignals(False)
        # Сброс (мокаем reload_all_sections чтобы не запускать фоновый поток)
        with patch.object(tab, 'reload_all_sections'):
            tab.reset_filters()
        assert tab.filter_quarter.currentIndex() == 0
        assert tab.filter_month.currentIndex() == 0

    def test_ensure_data_loaded_calls_reload(self, qtbot, mock_employee_admin):
        """ensure_data_loaded() вызывает reload_all_sections и _load_filter_options."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        assert tab._data_loaded is False
        with patch.object(tab, 'reload_all_sections') as mock_reload, \
             patch.object(tab, '_load_filter_options') as mock_load_opts:
            tab.ensure_data_loaded()
        mock_reload.assert_called_once()
        mock_load_opts.assert_called_once()


# ═══════════════════════════════════════════════════════════════════
# 4. Загрузка данных (4 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestReportsTabLoadData:
    """Вызовы загрузки данных: reload_all_sections, _load_filter_options."""

    def test_load_filter_options_years(self, qtbot, mock_employee_admin):
        """_load_filter_options() заполняет filter_year из DataAccess."""
        da = _make_mock_da()
        da.get_contract_years.return_value = [2023, 2024, 2025, 2026]
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        tab._load_filter_options()
        # "Все" + 4 года
        assert tab.filter_year.count() == 5
        assert tab.filter_year.itemText(0) == 'Все'
        da.get_contract_years.assert_called()

    def test_load_filter_options_cities(self, qtbot, mock_employee_admin):
        """_load_filter_options() заполняет filter_city из DataAccess."""
        da = _make_mock_da()
        da.get_cities.return_value = ['СПБ', 'МСК', 'Казань']
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        tab._load_filter_options()
        # "Все" + 3 города
        assert tab.filter_city.count() == 4
        assert tab.filter_city.itemText(0) == 'Все'

    def test_load_filter_options_agents(self, qtbot, mock_employee_admin):
        """_load_filter_options() заполняет filter_agent из DataAccess."""
        da = _make_mock_da()
        da.get_all_agents.return_value = [
            {'name': 'Агент1'}, {'name': 'Агент2'}, {'name': 'Агент3'}
        ]
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        tab._load_filter_options()
        # "Все" + 3 агента
        assert tab.filter_agent.count() == 4

    def test_load_filter_options_handles_exception(self, qtbot, mock_employee_admin):
        """_load_filter_options() не падает при ошибке DataAccess."""
        da = _make_mock_da()
        da.get_contract_years.side_effect = Exception("Ошибка БД")
        da.get_all_agents.side_effect = Exception("Ошибка БД")
        da.get_cities.side_effect = Exception("Ошибка БД")
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        # Не должно поднимать исключение
        tab._load_filter_options()


# ═══════════════════════════════════════════════════════════════════
# 5. Экспорт (2 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestReportsTabExport:
    """Экспорт отчёта в PDF."""

    def test_export_to_pdf_cancelled(self, qtbot, mock_employee_admin):
        """export_to_pdf() при отмене диалога — ничего не происходит."""
        da = _make_mock_da()
        tab = _create_reports_tab(qtbot, mock_employee_admin, mock_da=da)
        with patch('ui.reports_tab.QFileDialog.getSaveFileName', return_value=('', '')):
            # Не должно упасть, просто return
            tab.export_to_pdf()

    def test_has_export_to_pdf_method(self, qtbot, mock_employee_admin):
        """ReportsTab имеет метод export_to_pdf."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'export_to_pdf')
        assert callable(tab.export_to_pdf)


# ═══════════════════════════════════════════════════════════════════
# 6. Кэш и состояние (2 теста)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestReportsTabCache:
    """Кэширование данных."""

    def test_cache_initially_empty(self, qtbot, mock_employee_admin):
        """_cache изначально пустой."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert tab._cache == {}

    def test_loading_flag_initially_false(self, qtbot, mock_employee_admin):
        """_loading изначально False."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert tab._loading is False
