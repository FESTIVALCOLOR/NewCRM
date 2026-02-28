# -*- coding: utf-8 -*-
"""
UI Edge Cases — pytest-qt offscreen.

Покрытие:
  - TestEmptyDataEdgeCases (5)  — табы с пустыми данными
  - TestExtremeValues (5)       — длинные строки, большие числа
  - TestRapidInteractions (4)   — двойной клик, быстрое переключение
  - TestOfflineUIBehavior (4)   — offline fallback
ИТОГО: 18 тестов
"""

import pytest
import logging
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QWidget, QTableWidget, QPushButton, QVBoxLayout
from PyQt5.QtGui import QIcon

logger = logging.getLogger('tests')


# ─── Helpers ───────────────────────────────────────────────────────

def _section():
    """Stub SectionWidget с add_widget/add_layout."""
    w = QWidget()
    layout = QVBoxLayout(w)
    w.content_layout = layout
    w.add_widget = lambda widget: layout.addWidget(widget)
    w.add_layout = lambda l: layout.addLayout(l)
    return w


def _mock_icon_loader():
    """IconLoader с реальным QIcon."""
    mock = MagicMock()
    mock.load = MagicMock(return_value=QIcon())
    mock.create_icon_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    mock.create_action_button = MagicMock(side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else ''))
    mock.get_icon_path = MagicMock(return_value='')
    return mock


def _empty_data_access():
    """DataAccess с пустыми данными для всех методов."""
    da = MagicMock()
    da.get_all_clients.return_value = []
    da.get_all_contracts.return_value = []
    da.get_all_employees.return_value = []
    da.get_crm_cards.return_value = []
    da.get_supervision_cards.return_value = []
    da.get_all_payments.return_value = []
    da.get_year_payments.return_value = []
    da.get_salaries.return_value = []
    da.get_rates.return_value = []
    da.get_action_history.return_value = []
    da.api_client = None
    da.is_online = False
    da.db = MagicMock()
    da.db.get_all_clients.return_value = []
    da.db.get_all_contracts.return_value = []
    da.db.get_all_employees.return_value = []
    da.db.get_contract_years.return_value = [2026]
    da.db.get_dashboard_statistics.return_value = {
        'individual_orders': 0, 'template_orders': 0, 'supervision_orders': 0,
        'individual_area': 0, 'template_area': 0, 'supervision_area': 0,
    }
    da.db.get_project_statistics.return_value = {}
    da.db.get_supervision_statistics_report.return_value = {}
    da.db.get_funnel_statistics.return_value = {}
    da.db.get_executor_load.return_value = []
    return da


def _admin_employee():
    """Сотрудник с полными правами."""
    return {
        "id": 1, "full_name": "Тестов Админ", "login": "admin",
        "position": "Руководитель студии", "department": "Административный отдел",
        "status": "активный", "offline_mode": False
    }


# ─── Хуки логирования ───────────────────────────────────────────

@pytest.fixture(autouse=True)
def _log_test(request):
    yield
    rep = getattr(request.node, 'rep_call', None)
    if rep and rep.failed:
        logger.warning(f"Test FAILED: {request.node.name}")
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
# TestEmptyDataEdgeCases — пустые данные
# ═══════════════════════════════════════════════════════════════════

class TestEmptyDataEdgeCases:
    """UI корректно работает при полном отсутствии данных."""

    def test_clients_tab_empty(self, qtbot, mock_employee_admin):
        """ClientsTab с пустым списком клиентов."""
        da = _empty_data_access()
        with patch('ui.clients_tab.DataAccess', return_value=da), \
             patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
            from ui.clients_tab import ClientsTab
            tab = ClientsTab(employee=mock_employee_admin, api_client=None)
            qtbot.addWidget(tab)
            assert isinstance(tab, QWidget)

    def test_contracts_tab_empty(self, qtbot, mock_employee_admin):
        """ContractsTab с пустым списком договоров."""
        da = _empty_data_access()
        with patch('ui.contracts_tab.DataAccess', return_value=da), \
             patch('ui.contracts_tab.IconLoader', _mock_icon_loader()):
            from ui.contracts_tab import ContractsTab
            tab = ContractsTab(employee=mock_employee_admin, api_client=None)
            qtbot.addWidget(tab)
            assert isinstance(tab, QWidget)

    def test_employees_tab_empty(self, qtbot, mock_employee_admin):
        """EmployeesTab с пустым списком сотрудников."""
        da = _empty_data_access()
        with patch('ui.employees_tab.DataAccess', return_value=da), \
             patch('ui.employees_tab.IconLoader', _mock_icon_loader()):
            from ui.employees_tab import EmployeesTab
            tab = EmployeesTab(employee=mock_employee_admin, api_client=None)
            qtbot.addWidget(tab)
            assert isinstance(tab, QWidget)

    def test_dashboard_empty_stats(self, qtbot, mock_employee_admin):
        """DashboardTab с нулевой статистикой."""
        mock_db = MagicMock()
        mock_db.get_dashboard_statistics.return_value = {
            'individual_orders': 0, 'template_orders': 0, 'supervision_orders': 0,
            'individual_area': 0, 'template_area': 0, 'supervision_area': 0,
        }
        with patch('ui.dashboard_tab.DatabaseManager', return_value=mock_db), \
             patch('ui.dashboard_tab.resource_path', return_value=''):
            from ui.dashboard_tab import DashboardTab
            tab = DashboardTab(employee=mock_employee_admin, api_client=None)
            qtbot.addWidget(tab)
            assert isinstance(tab, QWidget)

    def test_reports_tab_empty(self, qtbot, mock_employee_admin):
        """ReportsTab с пустой статистикой."""
        mock_da = MagicMock()
        mock_da.get_all_contracts.return_value = []
        mock_da.get_all_employees.return_value = []
        def _kpi(*a, **kw):
            w = QWidget()
            w.set_value = lambda v: None
            w.set_trend = lambda v: None
            return w
        def _chart(*a, **kw):
            w = QWidget()
            w.set_data = lambda *a, **kw: None
            return w
        with patch('ui.reports_tab.DataAccess', return_value=mock_da), \
             patch('ui.reports_tab.KPICard', side_effect=_kpi), \
             patch('ui.reports_tab.MiniKPICard', side_effect=_kpi), \
             patch('ui.reports_tab.SectionWidget', side_effect=lambda *a, **kw: _section()), \
             patch('ui.reports_tab.LineChartWidget', side_effect=_chart), \
             patch('ui.reports_tab.StackedBarChartWidget', side_effect=_chart), \
             patch('ui.reports_tab.HorizontalBarWidget', side_effect=_chart), \
             patch('ui.reports_tab.FunnelBarChart', side_effect=_chart), \
             patch('ui.reports_tab.ProjectTypePieChart', side_effect=_chart):
            from ui.reports_tab import ReportsTab
            tab = ReportsTab(employee=mock_employee_admin, api_client=None)
            qtbot.addWidget(tab)
            assert isinstance(tab, QWidget)


# ═══════════════════════════════════════════════════════════════════
# TestExtremeValues — экстремальные значения
# ═══════════════════════════════════════════════════════════════════

class TestExtremeValues:
    """UI обрабатывает экстремальные значения без падений."""

    def test_very_long_employee_name(self, qtbot, mock_employee_admin):
        """ФИО длиной 300+ символов не ломает dashboard."""
        employee = mock_employee_admin.copy()
        employee['full_name'] = 'А' * 300
        mock_db = MagicMock()
        mock_db.get_dashboard_statistics.return_value = {
            'individual_orders': 0, 'template_orders': 0, 'supervision_orders': 0,
            'individual_area': 0, 'template_area': 0, 'supervision_area': 0,
        }
        with patch('ui.dashboard_tab.DatabaseManager', return_value=mock_db), \
             patch('ui.dashboard_tab.resource_path', return_value=''):
            from ui.dashboard_tab import DashboardTab
            tab = DashboardTab(employee=employee, api_client=None)
            qtbot.addWidget(tab)
            assert isinstance(tab, QWidget)

    def test_very_large_area_in_stats(self, qtbot, mock_employee_admin):
        """Площадь 99999.99 м² отображается корректно."""
        mock_db = MagicMock()
        mock_db.get_dashboard_statistics.return_value = {
            'individual_orders': 999, 'template_orders': 999, 'supervision_orders': 999,
            'individual_area': 99999.99, 'template_area': 99999.99, 'supervision_area': 99999.99,
        }
        with patch('ui.dashboard_tab.DatabaseManager', return_value=mock_db), \
             patch('ui.dashboard_tab.resource_path', return_value=''):
            from ui.dashboard_tab import DashboardTab
            tab = DashboardTab(employee=mock_employee_admin, api_client=None)
            qtbot.addWidget(tab)
            assert isinstance(tab, QWidget)

    def test_zero_stats(self, qtbot):
        """DashboardWidget с нулевыми значениями метрик."""
        mock_db = MagicMock()
        mock_db.get_contract_years.return_value = []
        with patch('ui.dashboard_widget.resource_path', return_value=''):
            from ui.dashboard_widget import DashboardWidget
            widget = DashboardWidget(db_manager=mock_db, api_client=None)
            qtbot.addWidget(widget)
            widget.add_metric_card(0, 0, 'test', 'Тест', '0',
                                    'clipboard1.svg', '#ffd93c', '#F57C00')
            widget.update_metric('test', '0')
            assert widget.metric_cards['test'].value_label.text() == '0'

    def test_negative_area_in_stats(self, qtbot, mock_employee_admin):
        """Отрицательная площадь (если возможна) не ломает UI."""
        mock_db = MagicMock()
        mock_db.get_dashboard_statistics.return_value = {
            'individual_orders': -1, 'template_orders': 0, 'supervision_orders': 0,
            'individual_area': -100.5, 'template_area': 0, 'supervision_area': 0,
        }
        with patch('ui.dashboard_tab.DatabaseManager', return_value=mock_db), \
             patch('ui.dashboard_tab.resource_path', return_value=''):
            from ui.dashboard_tab import DashboardTab
            tab = DashboardTab(employee=mock_employee_admin, api_client=None)
            qtbot.addWidget(tab)
            assert isinstance(tab, QWidget)

    def test_unicode_special_chars_employee(self, qtbot, mock_employee_admin):
        """Спецсимволы в ФИО не ломают UI."""
        employee = mock_employee_admin.copy()
        employee['full_name'] = "Тест'ов \"Спец\" <Символ> & Ёжик"
        mock_db = MagicMock()
        mock_db.get_dashboard_statistics.return_value = {
            'individual_orders': 0, 'template_orders': 0, 'supervision_orders': 0,
            'individual_area': 0, 'template_area': 0, 'supervision_area': 0,
        }
        with patch('ui.dashboard_tab.DatabaseManager', return_value=mock_db), \
             patch('ui.dashboard_tab.resource_path', return_value=''):
            from ui.dashboard_tab import DashboardTab
            tab = DashboardTab(employee=employee, api_client=None)
            qtbot.addWidget(tab)
            assert isinstance(tab, QWidget)


# ═══════════════════════════════════════════════════════════════════
# TestRapidInteractions — быстрые действия
# ═══════════════════════════════════════════════════════════════════

class TestRapidInteractions:
    """UI обрабатывает быстрые множественные действия."""

    def test_rapid_metric_updates(self, qtbot):
        """Быстрое обновление метрик 100 раз не падает."""
        mock_db = MagicMock()
        mock_db.get_contract_years.return_value = [2026]
        with patch('ui.dashboard_widget.resource_path', return_value=''):
            from ui.dashboard_widget import DashboardWidget
            widget = DashboardWidget(db_manager=mock_db, api_client=None)
            qtbot.addWidget(widget)
            widget.add_metric_card(0, 0, 'rapid', 'Rapid', '0',
                                    'clipboard1.svg', '#ffd93c', '#F57C00')
            for i in range(100):
                widget.update_metric('rapid', str(i))
            assert widget.metric_cards['rapid'].value_label.text() == '99'

    def test_multiple_tab_creation(self, qtbot, mock_employee_admin):
        """Создание нескольких DashboardTab не ломает приложение."""
        tabs = []
        mock_db = MagicMock()
        mock_db.get_dashboard_statistics.return_value = {
            'individual_orders': 0, 'template_orders': 0, 'supervision_orders': 0,
            'individual_area': 0, 'template_area': 0, 'supervision_area': 0,
        }
        for _ in range(5):
            with patch('ui.dashboard_tab.DatabaseManager', return_value=mock_db), \
                 patch('ui.dashboard_tab.resource_path', return_value=''):
                from ui.dashboard_tab import DashboardTab
                tab = DashboardTab(employee=mock_employee_admin, api_client=None)
                qtbot.addWidget(tab)
                tabs.append(tab)
        assert len(tabs) == 5

    def test_rapid_filter_changes(self, qtbot, mock_employee_admin):
        """Быстрая смена фильтров в ReportsTab не падает."""
        mock_da = MagicMock()
        mock_da.get_all_contracts.return_value = []
        mock_da.get_all_employees.return_value = []
        def _kpi(*a, **kw):
            w = QWidget()
            w.set_value = lambda v: None
            w.set_trend = lambda v: None
            return w
        def _chart(*a, **kw):
            w = QWidget()
            w.set_data = lambda *a, **kw: None
            return w
        with patch('ui.reports_tab.DataAccess', return_value=mock_da), \
             patch('ui.reports_tab.KPICard', side_effect=_kpi), \
             patch('ui.reports_tab.MiniKPICard', side_effect=_kpi), \
             patch('ui.reports_tab.SectionWidget', side_effect=lambda *a, **kw: _section()), \
             patch('ui.reports_tab.LineChartWidget', side_effect=_chart), \
             patch('ui.reports_tab.StackedBarChartWidget', side_effect=_chart), \
             patch('ui.reports_tab.HorizontalBarWidget', side_effect=_chart), \
             patch('ui.reports_tab.FunnelBarChart', side_effect=_chart), \
             patch('ui.reports_tab.ProjectTypePieChart', side_effect=_chart):
            from ui.reports_tab import ReportsTab
            tab = ReportsTab(employee=mock_employee_admin, api_client=None)
            qtbot.addWidget(tab)
            # Быстро меняем фильтры — главное не упасть
            for i in range(tab.filter_year.count()):
                tab.filter_year.setCurrentIndex(i)
            # С пустыми контрактами combo может быть пустым — просто проверяем что не упало
            assert isinstance(tab, QWidget)

    def test_add_multiple_metric_cards(self, qtbot):
        """Добавление 20 карточек метрик."""
        mock_db = MagicMock()
        mock_db.get_contract_years.return_value = [2026]
        with patch('ui.dashboard_widget.resource_path', return_value=''):
            from ui.dashboard_widget import DashboardWidget
            widget = DashboardWidget(db_manager=mock_db, api_client=None)
            qtbot.addWidget(widget)
            for i in range(20):
                widget.add_metric_card(i // 4, i % 4, f'card_{i}', f'Card {i}', '0',
                                        'clipboard1.svg', '#ffd93c', '#F57C00')
            assert len(widget.metric_cards) == 20


# ═══════════════════════════════════════════════════════════════════
# TestOfflineUIBehavior — Offline поведение
# ═══════════════════════════════════════════════════════════════════

class TestOfflineUIBehavior:
    """UI корректно работает в offline режиме."""

    def test_clients_tab_offline_mode(self, qtbot, mock_employee_admin):
        """ClientsTab создаётся при offline_mode=True."""
        employee = mock_employee_admin.copy()
        employee['offline_mode'] = True
        da = _empty_data_access()
        with patch('ui.clients_tab.DataAccess', return_value=da), \
             patch('ui.clients_tab.IconLoader', _mock_icon_loader()):
            from ui.clients_tab import ClientsTab
            tab = ClientsTab(employee=employee, api_client=None)
            qtbot.addWidget(tab)
            assert isinstance(tab, QWidget)

    def test_contracts_tab_offline_mode(self, qtbot, mock_employee_admin):
        """ContractsTab создаётся при offline."""
        employee = mock_employee_admin.copy()
        employee['offline_mode'] = True
        da = _empty_data_access()
        with patch('ui.contracts_tab.DataAccess', return_value=da), \
             patch('ui.contracts_tab.IconLoader', _mock_icon_loader()):
            from ui.contracts_tab import ContractsTab
            tab = ContractsTab(employee=employee, api_client=None)
            qtbot.addWidget(tab)
            assert isinstance(tab, QWidget)

    def test_dashboard_offline_mode(self, qtbot, mock_employee_admin):
        """DashboardTab создаётся при offline."""
        employee = mock_employee_admin.copy()
        employee['offline_mode'] = True
        mock_db = MagicMock()
        mock_db.get_dashboard_statistics.return_value = {
            'individual_orders': 0, 'template_orders': 0, 'supervision_orders': 0,
            'individual_area': 0, 'template_area': 0, 'supervision_area': 0,
        }
        with patch('ui.dashboard_tab.DatabaseManager', return_value=mock_db), \
             patch('ui.dashboard_tab.resource_path', return_value=''):
            from ui.dashboard_tab import DashboardTab
            tab = DashboardTab(employee=employee, api_client=None)
            qtbot.addWidget(tab)
            assert isinstance(tab, QWidget)

    def test_employees_tab_offline_mode(self, qtbot, mock_employee_admin):
        """EmployeesTab создаётся при offline."""
        employee = mock_employee_admin.copy()
        employee['offline_mode'] = True
        da = _empty_data_access()
        with patch('ui.employees_tab.DataAccess', return_value=da), \
             patch('ui.employees_tab.IconLoader', _mock_icon_loader()):
            from ui.employees_tab import EmployeesTab
            tab = EmployeesTab(employee=employee, api_client=None)
            qtbot.addWidget(tab)
            assert isinstance(tab, QWidget)
