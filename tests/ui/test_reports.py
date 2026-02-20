# -*- coding: utf-8 -*-
"""
Тесты ReportsTab — pytest-qt offscreen.

Покрытие:
  - TestReportsRendering (4) — создание, вкладки, фильтры
  - TestReportsFilters (4)   — комбобоксы фильтров, сброс
ИТОГО: 8 тестов
"""

import pytest
import logging
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QWidget, QTabWidget, QPushButton
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
    mock.get_icon_path = MagicMock(return_value='')
    return mock


def _create_reports_tab(qtbot, employee):
    """Создание ReportsTab с замоканными зависимостями."""
    mock_db = MagicMock()
    mock_db.get_all_contracts.return_value = []
    mock_db.get_project_statistics.return_value = {}
    mock_db.get_supervision_statistics_report.return_value = {}
    mock_db.get_funnel_statistics.return_value = {}
    mock_db.get_executor_load.return_value = []

    with patch('ui.reports_tab.DatabaseManager', return_value=mock_db), \
         patch('ui.reports_tab.IconLoader', _mock_icon_loader()):
        from ui.reports_tab import ReportsTab
        tab = ReportsTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
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

    def test_has_tabs(self, qtbot, mock_employee_admin):
        """QTabWidget с вкладками статистики."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'tabs')
        assert isinstance(tab.tabs, QTabWidget)

    def test_4_tabs(self, qtbot, mock_employee_admin):
        """4 вкладки: Индивидуальные, Шаблонные, Надзор, Аналитика."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert tab.tabs.count() == 4

    def test_lazy_loading(self, qtbot, mock_employee_admin):
        """_data_loaded = False до вызова ensure_data_loaded."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert tab._data_loaded is False


# ═══════════════════════════════════════════════════════════════════
# TestReportsFilters — фильтры
# ═══════════════════════════════════════════════════════════════════

class TestReportsFilters:
    """Фильтры ReportsTab."""

    def test_year_combo(self, qtbot, mock_employee_admin):
        """Фильтр года существует."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'year_combo')
        # Должен содержать годы 2020-2040
        assert tab.year_combo.count() >= 20

    def test_quarter_combo(self, qtbot, mock_employee_admin):
        """Фильтр квартала: Все + Q1-Q4."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'quarter_combo')
        items = [tab.quarter_combo.itemText(i) for i in range(tab.quarter_combo.count())]
        assert 'Все' in items or 'Q1' in items

    def test_month_combo(self, qtbot, mock_employee_admin):
        """Фильтр месяца: Все + 12 месяцев."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'month_combo')
        assert tab.month_combo.count() >= 12

    def test_ensure_data_loaded(self, qtbot, mock_employee_admin):
        """ensure_data_loaded ставит _data_loaded = True."""
        tab = _create_reports_tab(qtbot, mock_employee_admin)
        assert tab._data_loaded is False
        tab.ensure_data_loaded()
        assert tab._data_loaded is True
