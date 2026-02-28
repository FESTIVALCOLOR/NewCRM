# -*- coding: utf-8 -*-
"""
Тесты ReportsTab — pytest-qt offscreen.

Покрытие:
  - TestReportsRendering (4) — создание, секции, фильтры
  - TestReportsFilters (4)   — комбобоксы фильтров, сброс
ИТОГО: 8 тестов

Адаптировано под переписанный ReportsTab (bc2790b):
  - Архитектура: QScrollArea с секциями (не QTabWidget)
  - Фильтры: filter_year, filter_quarter, filter_month, filter_agent, filter_city
  - DataAccess вместо DatabaseManager
"""

import pytest
import logging
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QWidget, QComboBox, QFrame
from PyQt5.QtCore import Qt

logger = logging.getLogger('tests')


# ─── Helpers ───────────────────────────────────────────────────────

def _make_section_widget():
    """Создать mock-SectionWidget с нужными методами."""
    from PyQt5.QtWidgets import QVBoxLayout
    w = QFrame()
    layout = QVBoxLayout(w)
    w.add_widget = lambda widget: layout.addWidget(widget)
    w.add_layout = lambda lo: layout.addLayout(lo)
    return w


def _make_mock_da():
    """Создание MagicMock DataAccess для ReportsTab."""
    da = MagicMock()
    da.get_contract_years.return_value = [2024, 2025, 2026]
    da.get_all_agents.return_value = [{'name': 'Риелтор'}]
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


def _create_reports_tab(qtbot, employee):
    """Создание ReportsTab с замоканными зависимостями."""
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


# ─── Хуки логирования ───────────────────────────────────────────

@pytest.fixture(autouse=True)
def _log_test(request):
    yield
    rep = getattr(request.node, 'rep_call', None)
    if rep and rep.failed:
        logger.warning(f"Test FAILED: {request.node.name}")
        logger.warning(f"Error: {rep.longreprtext[:200]}")
    else:
        logger.info(f"Test PASSED: {request.node.name}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    import pytest
    outcome = yield
    rep = outcome.get_result()
    if rep.when == 'call':
        item.rep_call = rep


# ═══════════════════════════════════════════════════════════════════
# TestReportsRendering — базовое создание и структура
# ═══════════════════════════════════════════════════════════════════

class TestReportsRendering:
    """ReportsTab — создание и структура."""

    def test_tab_creates(self, qtbot, mock_employee_admin):
        """ReportsTab создаётся как QWidget."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert isinstance(tab, QWidget)

    def test_has_sections_layout(self, qtbot, mock_employee_admin):
        """ReportsTab имеет sections_layout для секций."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'sections_layout')

    def test_has_filter_combos(self, qtbot, mock_employee_admin):
        """ReportsTab имеет фильтры filter_year, filter_quarter, filter_month."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'filter_year')
        assert hasattr(tab, 'filter_quarter')
        assert hasattr(tab, 'filter_month')

    def test_lazy_loading(self, qtbot, mock_employee_admin):
        """_data_loaded = False до вызова ensure_data_loaded."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert tab._data_loaded is False


# ═══════════════════════════════════════════════════════════════════
# TestReportsFilters — фильтры
# ═══════════════════════════════════════════════════════════════════

class TestReportsFilters:
    """Фильтры ReportsTab."""

    def test_filter_year(self, qtbot, mock_employee_admin):
        """Фильтр года существует как QComboBox."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'filter_year')
        assert isinstance(tab.filter_year, QComboBox)

    def test_filter_quarter(self, qtbot, mock_employee_admin):
        """Фильтр квартала: Все + Q1-Q4."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'filter_quarter')
        items = [tab.filter_quarter.itemText(i) for i in range(tab.filter_quarter.count())]
        assert 'Все' in items
        assert 'Q1' in items

    def test_filter_month(self, qtbot, mock_employee_admin):
        """Фильтр месяца: Все + 12 месяцев."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'filter_month')
        assert tab.filter_month.count() == 13

    def test_ensure_data_loaded(self, qtbot, mock_employee_admin):
        """ensure_data_loaded ставит запуск загрузки."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert tab._data_loaded is False
        with patch.object(tab, 'reload_all_sections'), \
             patch.object(tab, '_load_filter_options'):
            tab.ensure_data_loaded()
