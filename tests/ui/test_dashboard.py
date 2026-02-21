# -*- coding: utf-8 -*-
"""
Тесты DashboardTab + DashboardWidget — pytest-qt offscreen.

Покрытие:
  - TestDashboardTabRendering (6)  — создание, карточки, юзер-инфо
  - TestDashboardStatCards (4)     — 6 карточек метрик
  - TestDashboardWidget (4)        — DashboardWidget / MetricCard
ИТОГО: 14 тестов
"""

import pytest
import logging
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QWidget, QGroupBox, QLabel, QPushButton
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
    mock.create_action_button = MagicMock(side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else ''))
    mock.get_icon_path = MagicMock(return_value='')
    return mock


def _create_dashboard_tab(qtbot, employee):
    """Создание DashboardTab с замоканными зависимостями."""
    mock_db = MagicMock()
    mock_db.get_dashboard_statistics.return_value = {
        'individual_orders': 10,
        'template_orders': 5,
        'supervision_orders': 3,
        'individual_area': 850.5,
        'template_area': 600.0,
        'supervision_area': 400.0,
    }

    with patch('ui.dashboard_tab.DatabaseManager', return_value=mock_db), \
         patch('ui.dashboard_tab.resource_path', return_value=''):
        from ui.dashboard_tab import DashboardTab
        tab = DashboardTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab


def _create_dashboard_widget(qtbot):
    """Создание DashboardWidget с замоканными зависимостями."""
    mock_db = MagicMock()
    mock_db.get_contract_years.return_value = [2024, 2025, 2026]

    with patch('ui.dashboard_widget.resource_path', return_value=''):
        from ui.dashboard_widget import DashboardWidget
        widget = DashboardWidget(db_manager=mock_db, api_client=None)
        qtbot.addWidget(widget)
        return widget


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
# TestDashboardTabRendering — базовое создание
# ═══════════════════════════════════════════════════════════════════

class TestDashboardTabRendering:
    """DashboardTab — создание и структура."""

    def test_tab_creates(self, qtbot, mock_employee_admin):
        """DashboardTab создаётся как QWidget."""
        tab = _create_dashboard_tab(qtbot, mock_employee_admin)
        assert isinstance(tab, QWidget)

    def test_employee_stored(self, qtbot, mock_employee_admin):
        """employee атрибут сохранён."""
        tab = _create_dashboard_tab(qtbot, mock_employee_admin)
        assert tab.employee == mock_employee_admin

    def test_user_info_displayed(self, qtbot, mock_employee_admin):
        """Информация о пользователе отображается."""
        tab = _create_dashboard_tab(qtbot, mock_employee_admin)
        labels = tab.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        combined = ' '.join(texts)
        assert 'Тестов Админ' in combined or mock_employee_admin['full_name'] in combined

    def test_6_stat_cards(self, qtbot, mock_employee_admin):
        """6 карточек статистики (QGroupBox)."""
        tab = _create_dashboard_tab(qtbot, mock_employee_admin)
        cards = tab.findChildren(QGroupBox)
        assert len(cards) >= 6

    def test_has_individual_orders_card(self, qtbot, mock_employee_admin):
        """Карточка individual_orders_card существует."""
        tab = _create_dashboard_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'individual_orders_card')

    def test_has_template_orders_card(self, qtbot, mock_employee_admin):
        """Карточка template_orders_card существует."""
        tab = _create_dashboard_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'template_orders_card')


# ═══════════════════════════════════════════════════════════════════
# TestDashboardStatCards — карточки статистики
# ═══════════════════════════════════════════════════════════════════

class TestDashboardStatCards:
    """Карточки статистики DashboardTab."""

    def test_supervision_orders_card(self, qtbot, mock_employee_admin):
        """Карточка supervision_orders_card существует."""
        tab = _create_dashboard_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'supervision_orders_card')

    def test_individual_area_card(self, qtbot, mock_employee_admin):
        """Карточка individual_area_card существует."""
        tab = _create_dashboard_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'individual_area_card')

    def test_template_area_card(self, qtbot, mock_employee_admin):
        """Карточка template_area_card существует."""
        tab = _create_dashboard_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'template_area_card')

    def test_supervision_area_card(self, qtbot, mock_employee_admin):
        """Карточка supervision_area_card существует."""
        tab = _create_dashboard_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'supervision_area_card')


# ═══════════════════════════════════════════════════════════════════
# TestDashboardWidget — DashboardWidget / MetricCard
# ═══════════════════════════════════════════════════════════════════

class TestDashboardWidget:
    """DashboardWidget — базовый виджет метрик."""

    def test_widget_creates(self, qtbot):
        """DashboardWidget создаётся."""
        widget = _create_dashboard_widget(qtbot)
        assert isinstance(widget, QWidget)

    def test_metric_cards_dict(self, qtbot):
        """metric_cards — пустой dict при создании."""
        widget = _create_dashboard_widget(qtbot)
        assert hasattr(widget, 'metric_cards')
        assert isinstance(widget.metric_cards, dict)

    def test_add_metric_card(self, qtbot):
        """add_metric_card добавляет карточку в metric_cards."""
        widget = _create_dashboard_widget(qtbot)
        card = widget.add_metric_card(0, 0, 'test_card', 'Тест', '0',
                                       'clipboard1.svg', '#ffd93c', '#F57C00')
        assert 'test_card' in widget.metric_cards

    def test_update_metric(self, qtbot):
        """update_metric обновляет значение карточки."""
        widget = _create_dashboard_widget(qtbot)
        widget.add_metric_card(0, 0, 'test_card', 'Тест', '0',
                                'clipboard1.svg', '#ffd93c', '#F57C00')
        widget.update_metric('test_card', '42')
        card = widget.metric_cards['test_card']
        assert card.value_label.text() == '42'
