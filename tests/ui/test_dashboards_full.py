# -*- coding: utf-8 -*-
"""Тесты для ui/dashboards.py и ui/dashboard_widget.py — дашборды метрик"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime


# ─── Фикстуры ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_da():
    """Мок DataAccess для дашбордов"""
    da = MagicMock()
    da.get_agent_types.return_value = ['Прямой', 'Агент', 'Партнер']
    da.get_contract_years.return_value = [2026, 2025, 2024, 2023]
    da.get_clients_dashboard_stats.return_value = {
        'total_clients': 100, 'total_individual': 70, 'total_legal': 30,
        'clients_by_year': 25, 'agent_clients_total': 15,
        'agent_clients_by_year': 10,
    }
    da.get_contracts_dashboard_stats.return_value = {
        'individual_orders': 50, 'individual_area': 5000,
        'template_orders': 30, 'template_area': 3000,
        'agent_orders_by_year': 10, 'agent_area_by_year': 1000,
    }
    da.get_crm_dashboard_stats.return_value = {
        'total_orders': 80, 'total_area': 8000,
        'active_orders': 40, 'archive_orders': 40,
        'agent_active_orders': 15, 'agent_archive_orders': 12,
    }
    da.get_employees_dashboard_stats.return_value = {
        'active_employees': 20, 'reserve_employees': 5,
        'active_admin': 3, 'active_project': 8,
        'active_execution': 9, 'nearest_birthday': 'Иванов И.И. (01.03)',
    }
    da.get_salaries_dashboard_stats.return_value = {
        'total_paid': 5000000, 'paid_by_year': 3000000,
        'paid_by_month': 500000, 'avg_salary': 250000,
        'employees_paid': 18, 'max_salary': 600000,
    }
    return da


PATCHES_BASE = {
    'ui.dashboard_widget.DataAccess': None,
    'ui.dashboard_widget.create_colored_icon': lambda *a, **k: None,
    'ui.dashboard_widget.resource_path': lambda p: p,
    'ui.dashboard_widget.os.path.exists': lambda p: False,
}


def _make_patches(extra=None):
    """Создать контекст патчей для дашбордов"""
    d = dict(PATCHES_BASE)
    if extra:
        d.update(extra)
    return d


# ─── dashboard_widget.py — утилиты ──────────────────────────────────────

class TestCreateColoredIcon:
    """Тесты create_colored_icon"""

    def test_file_not_found(self):
        with patch('ui.dashboard_widget.resource_path', return_value='/fake'), \
             patch('ui.dashboard_widget.os.path.exists', return_value=False), \
             patch('builtins.print'):
            from ui.dashboard_widget import create_colored_icon
            result = create_colored_icon('icon.svg', '#FF0000')
            assert result is None

    def test_replaces_current_color(self, tmp_path):
        svg = '<svg><path stroke="currentColor" fill="currentColor"/></svg>'
        f = tmp_path / 'icon.svg'
        f.write_text(svg, encoding='utf-8')
        with patch('ui.dashboard_widget.resource_path', return_value=str(f)), \
             patch('ui.dashboard_widget.os.path.exists', return_value=True):
            from ui.dashboard_widget import create_colored_icon
            result = create_colored_icon(str(f), '#FF0000')
            assert result is not None
            assert b'#FF0000' in result
            assert b'currentColor' not in result

    def test_replaces_black_stroke_fill(self, tmp_path):
        svg = '<svg><path stroke="black" fill="#000000"/></svg>'
        f = tmp_path / 'icon.svg'
        f.write_text(svg, encoding='utf-8')
        with patch('ui.dashboard_widget.resource_path', return_value=str(f)), \
             patch('ui.dashboard_widget.os.path.exists', return_value=True):
            from ui.dashboard_widget import create_colored_icon
            result = create_colored_icon(str(f), '#00FF00')
            assert b'#00FF00' in result
            assert b'black' not in result

    def test_replaces_white_stroke(self, tmp_path):
        svg = '<svg><path stroke="white" fill="white"/></svg>'
        f = tmp_path / 'icon.svg'
        f.write_text(svg, encoding='utf-8')
        with patch('ui.dashboard_widget.resource_path', return_value=str(f)), \
             patch('ui.dashboard_widget.os.path.exists', return_value=True):
            from ui.dashboard_widget import create_colored_icon
            result = create_colored_icon(str(f), '#0000FF')
            assert b'#0000FF' in result

    def test_adds_fill_if_no_attrs(self, tmp_path):
        svg = '<svg><path d="M0 0"/></svg>'
        f = tmp_path / 'icon.svg'
        f.write_text(svg, encoding='utf-8')
        with patch('ui.dashboard_widget.resource_path', return_value=str(f)), \
             patch('ui.dashboard_widget.os.path.exists', return_value=True):
            from ui.dashboard_widget import create_colored_icon
            result = create_colored_icon(str(f), '#ABC123')
            text = result.decode('utf-8')
            assert 'fill="#ABC123"' in text

    def test_read_error_returns_none(self):
        with patch('ui.dashboard_widget.resource_path', return_value='/exists'), \
             patch('ui.dashboard_widget.os.path.exists', return_value=True), \
             patch('builtins.open', side_effect=IOError('read error')):
            from ui.dashboard_widget import create_colored_icon
            result = create_colored_icon('/exists', '#FF0000')
            assert result is None


class TestFilterButton:
    """Тесты FilterButton"""

    def test_creation(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import FilterButton
            btn = FilterButton('year', [2024, 2025, 2026], border_color='#F57C00')
            qtbot.addWidget(btn)
            assert btn.filter_type == 'year'
            assert btn.options == [2024, 2025, 2026]
            assert btn.current_value is None

    def test_select_option_emits_signal(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import FilterButton
            btn = FilterButton('agent', ['Прямой', 'Агент'], border_color='#F57C00')
            qtbot.addWidget(btn)
            signals = []
            btn.filter_changed.connect(lambda v: signals.append(v))
            btn.select_option('Агент')
            assert btn.current_value == 'Агент'
            assert 'Агент' in signals

    def test_get_value(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import FilterButton
            btn = FilterButton('month', ['01', '02'], border_color='#F57C00')
            qtbot.addWidget(btn)
            assert btn.get_value() is None
            btn.select_option('02')
            assert btn.get_value() == '02'

    def test_set_options_updates_menu(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import FilterButton
            btn = FilterButton('year', [2024], border_color='#F57C00')
            qtbot.addWidget(btn)
            btn.set_options([2025, 2026])
            assert btn.options == [2025, 2026]

    def test_get_filter_name(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import FilterButton
            btn = FilterButton('agent', ['A'], border_color='#F57C00')
            qtbot.addWidget(btn)
            assert btn._get_filter_name() == 'Агент'
            btn2 = FilterButton('year', [2024], border_color='#F57C00')
            qtbot.addWidget(btn2)
            assert btn2._get_filter_name() == 'Год'
            btn3 = FilterButton('month', ['01'], border_color='#F57C00')
            qtbot.addWidget(btn3)
            assert btn3._get_filter_name() == 'Месяц'
            btn4 = FilterButton('custom', ['X'], border_color='#F57C00')
            qtbot.addWidget(btn4)
            assert btn4._get_filter_name() == 'Фильтр'


class TestMetricCard:
    """Тесты MetricCard"""

    def test_creation(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import MetricCard
            card = MetricCard(
                object_name='test_card', title='Тест', value='42',
                icon_path='resources/icons/test.svg',
                bg_color='#ffffff', border_color='#F57C00'
            )
            qtbot.addWidget(card)
            assert card.objectName() == 'test_card'
            assert card.value_label.text() == '42'

    def test_update_value(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import MetricCard
            card = MetricCard(
                object_name='vc', title='T', value='0',
                icon_path='i.svg', bg_color='#fff', border_color='#000'
            )
            qtbot.addWidget(card)
            card.update_value('99')
            assert card.value_label.text() == '99'

    def test_with_filters(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import MetricCard
            card = MetricCard(
                object_name='fc', title='T', value='0',
                icon_path='i.svg', bg_color='#fff', border_color='#F57C00',
                filters=[{'type': 'year', 'options': [2024, 2025]}]
            )
            qtbot.addWidget(card)
            assert 'year' in card.filter_buttons

    def test_connect_filter(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import MetricCard
            card = MetricCard(
                object_name='cf', title='T', value='0',
                icon_path='i.svg', bg_color='#fff', border_color='#F57C00',
                filters=[{'type': 'agent', 'options': ['A', 'B']}]
            )
            qtbot.addWidget(card)
            calls = []
            card.connect_filter('agent', lambda v: calls.append(v))
            card.filter_buttons['agent'].select_option('A')
            assert 'A' in calls

    def test_get_filter_value(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import MetricCard
            card = MetricCard(
                object_name='gfv', title='T', value='0',
                icon_path='i.svg', bg_color='#fff', border_color='#F57C00',
                filters=[{'type': 'year', 'options': [2024]}]
            )
            qtbot.addWidget(card)
            assert card.get_filter_value('year') is None
            card.filter_buttons['year'].select_option(2024)
            assert card.get_filter_value('year') == 2024

    def test_no_filters(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import MetricCard
            card = MetricCard(
                object_name='nf', title='T', value='0',
                icon_path='i.svg', bg_color='#fff', border_color='#000'
            )
            qtbot.addWidget(card)
            assert card.filter_buttons == {}
            assert card.get_filter_value('year') is None

    def test_update_filter_label_shows_label(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import MetricCard
            card = MetricCard(
                object_name='ufl', title='T', value='0',
                icon_path='i.svg', bg_color='#fff', border_color='#F57C00',
                filters=[{'type': 'year', 'options': [2025]}, {'type': 'agent', 'options': ['Агент']}]
            )
            qtbot.addWidget(card)
            card.filter_buttons['year'].select_option(2025)
            # Проверяем что select_option сработал
            assert card.filter_buttons['year'].current_value == 2025


class TestDashboardWidget:
    """Тесты базового DashboardWidget"""

    def test_creation(self, qtbot):
        with patch('ui.dashboard_widget.DataAccess') as MockDA:
            MockDA.return_value = MagicMock()
            from ui.dashboard_widget import DashboardWidget
            dw = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(dw)
            assert dw.metric_cards == {}
            assert dw.height() == 105

    def test_add_metric_card(self, qtbot):
        with patch('ui.dashboard_widget.DataAccess') as MockDA, \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            MockDA.return_value = MagicMock()
            from ui.dashboard_widget import DashboardWidget
            dw = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(dw)
            card = dw.add_metric_card(0, 0, 'test', 'Тест', '42', 'icon.svg')
            assert 'test' in dw.metric_cards
            assert card is dw.metric_cards['test']

    def test_update_metric(self, qtbot):
        with patch('ui.dashboard_widget.DataAccess') as MockDA, \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            MockDA.return_value = MagicMock()
            from ui.dashboard_widget import DashboardWidget
            dw = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(dw)
            dw.add_metric_card(0, 0, 'mc', 'M', '0', 'i.svg')
            dw.update_metric('mc', '123')
            assert dw.metric_cards['mc'].value_label.text() == '123'

    def test_update_metric_missing_key(self, qtbot):
        with patch('ui.dashboard_widget.DataAccess') as MockDA:
            MockDA.return_value = MagicMock()
            from ui.dashboard_widget import DashboardWidget
            dw = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(dw)
            dw.update_metric('nonexistent', '0')  # не падает

    def test_get_metric_card(self, qtbot):
        with patch('ui.dashboard_widget.DataAccess') as MockDA, \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            MockDA.return_value = MagicMock()
            from ui.dashboard_widget import DashboardWidget
            dw = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(dw)
            dw.add_metric_card(0, 0, 'g', 'G', '0', 'i.svg')
            assert dw.get_metric_card('g') is not None
            assert dw.get_metric_card('missing') is None

    def test_set_column_stretch(self, qtbot):
        with patch('ui.dashboard_widget.DataAccess') as MockDA:
            MockDA.return_value = MagicMock()
            from ui.dashboard_widget import DashboardWidget
            dw = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(dw)
            dw.set_column_stretch(4)  # не падает

    def test_load_data_base(self, qtbot):
        with patch('ui.dashboard_widget.DataAccess') as MockDA:
            MockDA.return_value = MagicMock()
            from ui.dashboard_widget import DashboardWidget
            dw = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(dw)
            dw.load_data()  # базовая — пустая

    def test_get_years_from_data_access(self, qtbot):
        with patch('ui.dashboard_widget.DataAccess') as MockDA:
            mock_da = MagicMock()
            mock_da.get_contract_years.return_value = [2026, 2025, 2024]
            MockDA.return_value = mock_da
            from ui.dashboard_widget import DashboardWidget
            dw = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(dw)
            years = dw.get_years()
            assert years == [2026, 2025, 2024]

    def test_get_years_fallback(self, qtbot):
        with patch('ui.dashboard_widget.DataAccess') as MockDA:
            mock_da = MagicMock()
            mock_da.get_contract_years.side_effect = Exception('fail')
            MockDA.return_value = mock_da
            from ui.dashboard_widget import DashboardWidget
            dw = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(dw)
            years = dw.get_years()
            assert len(years) == 11  # current+1 ... current-9

    def test_get_years_empty_returns_fallback(self, qtbot):
        with patch('ui.dashboard_widget.DataAccess') as MockDA:
            mock_da = MagicMock()
            mock_da.get_contract_years.return_value = []
            MockDA.return_value = mock_da
            from ui.dashboard_widget import DashboardWidget
            dw = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(dw)
            years = dw.get_years()
            assert len(years) > 0

    def test_refresh_calls_load_data(self, qtbot):
        with patch('ui.dashboard_widget.DataAccess') as MockDA:
            MockDA.return_value = MagicMock()
            from ui.dashboard_widget import DashboardWidget
            dw = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(dw)
            dw.load_data = MagicMock()
            dw.refresh()
            dw.load_data.assert_called_once()

    def test_refresh_handles_error(self, qtbot):
        with patch('ui.dashboard_widget.DataAccess') as MockDA:
            MockDA.return_value = MagicMock()
            from ui.dashboard_widget import DashboardWidget
            dw = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(dw)
            dw.load_data = MagicMock(side_effect=Exception('boom'))
            dw.refresh()  # не падает


# ─── dashboards.py — конкретные дашборды ─────────────────────────────────

class TestClientsDashboard:
    """Тесты ClientsDashboard"""

    def test_creation(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import ClientsDashboard
            d = ClientsDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            assert 'total_clients' in d.metric_cards
            assert 'total_individual' in d.metric_cards
            assert 'total_legal' in d.metric_cards
            assert 'clients_by_year' in d.metric_cards

    def test_load_data(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import ClientsDashboard
            d = ClientsDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            d.load_data()
            assert d.metric_cards['total_clients'].value_label.text() == '100'
            assert d.metric_cards['total_individual'].value_label.text() == '70'

    def test_agent_types_fallback(self, qtbot):
        mock_da2 = MagicMock()
        mock_da2.get_agent_types.return_value = []
        mock_da2.get_contract_years.return_value = [2026]
        with patch('ui.dashboards.DataAccess', return_value=mock_da2), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da2), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import ClientsDashboard
            d = ClientsDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            assert d.agent_types == ['Прямой', 'Агент', 'Партнер']

    def test_agent_types_exception(self, qtbot):
        mock_da2 = MagicMock()
        mock_da2.get_agent_types.side_effect = Exception('fail')
        mock_da2.get_contract_years.return_value = [2026]
        with patch('ui.dashboards.DataAccess', return_value=mock_da2), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da2), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import ClientsDashboard
            d = ClientsDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            assert d.agent_types == ['Прямой', 'Агент', 'Партнер']

    def test_on_clients_by_year_changed(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import ClientsDashboard
            d = ClientsDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            d.on_clients_by_year_changed('2025')
            assert d.filter_clients_by_year_year == 2025

    def test_on_agent_clients_total_changed(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import ClientsDashboard
            d = ClientsDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            d.on_agent_clients_total_changed('Агент')
            assert d.filter_agent_clients_total_agent == 'Агент'

    def test_load_data_error(self, qtbot):
        mock_da2 = MagicMock()
        mock_da2.get_agent_types.return_value = ['Прямой']
        mock_da2.get_contract_years.return_value = [2026]
        mock_da2.get_clients_dashboard_stats.side_effect = Exception('db error')
        with patch('ui.dashboards.DataAccess', return_value=mock_da2), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da2), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import ClientsDashboard
            d = ClientsDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            d.load_data()  # не падает


class TestContractsDashboard:
    """Тесты ContractsDashboard"""

    def test_creation(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import ContractsDashboard
            d = ContractsDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            assert 'individual_orders' in d.metric_cards
            assert 'agent_orders_by_year' in d.metric_cards

    def test_load_data(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import ContractsDashboard
            d = ContractsDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            d.load_data()
            assert d.metric_cards['individual_orders'].value_label.text() == '50'

    def test_on_year_changed(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import ContractsDashboard
            d = ContractsDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            d.on_year_changed('2024')
            assert d.filter_agent_year == 2024

    def test_on_agent_changed(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import ContractsDashboard
            d = ContractsDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            d.on_agent_changed('Партнер')
            assert d.filter_agent_type == 'Партнер'


class TestCRMDashboard:
    """Тесты CRMDashboard"""

    @pytest.mark.parametrize('project_type', ['Индивидуальный', 'Шаблонный', 'Авторский надзор'])
    def test_creation_per_type(self, qtbot, mock_da, project_type):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import CRMDashboard
            d = CRMDashboard(db_manager=MagicMock(), project_type=project_type)
            qtbot.addWidget(d)
            assert d.project_type == project_type
            assert 'total_orders' in d.metric_cards

    def test_load_data(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import CRMDashboard
            d = CRMDashboard(db_manager=MagicMock(), project_type='Индивидуальный')
            qtbot.addWidget(d)
            d.load_data()
            assert d.metric_cards['total_orders'].value_label.text() == '80'

    def test_on_agent_active_changed(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import CRMDashboard
            d = CRMDashboard(db_manager=MagicMock(), project_type='Индивидуальный')
            qtbot.addWidget(d)
            d.on_agent_active_changed('Агент')
            assert d.filter_agent_active == 'Агент'

    def test_on_agent_archive_changed(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import CRMDashboard
            d = CRMDashboard(db_manager=MagicMock(), project_type='Шаблонный')
            qtbot.addWidget(d)
            d.on_agent_archive_changed('Партнер')
            assert d.filter_agent_archive == 'Партнер'


class TestEmployeesDashboard:
    """Тесты EmployeesDashboard"""

    def test_creation(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import EmployeesDashboard
            d = EmployeesDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            assert 'active_employees' in d.metric_cards

    def test_load_data(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import EmployeesDashboard
            d = EmployeesDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            d.load_data()
            assert d.metric_cards['active_employees'].value_label.text() == '20'

    def test_load_data_alternative_keys(self, qtbot):
        mock_da2 = MagicMock()
        mock_da2.get_contract_years.return_value = [2026]
        mock_da2.get_employees_dashboard_stats.return_value = {
            'active_employees': 10, 'reserve_employees': 2,
            'active_management': 3, 'active_projects_dept': 4,
            'active_execution_dept': 5, 'upcoming_birthdays': 2,
        }
        with patch('ui.dashboards.DataAccess', return_value=mock_da2), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da2), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import EmployeesDashboard
            d = EmployeesDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            d.load_data()
            assert d.metric_cards['active_admin'].value_label.text() == '3'

    def test_birthday_truncation(self, qtbot):
        mock_da2 = MagicMock()
        mock_da2.get_contract_years.return_value = [2026]
        mock_da2.get_employees_dashboard_stats.return_value = {
            'active_employees': 1, 'reserve_employees': 0,
            'active_admin': 0, 'active_project': 0,
            'active_execution': 0,
            'nearest_birthday': 'Очень длинное имя сотрудника которое не помещается в карточку',
        }
        with patch('ui.dashboards.DataAccess', return_value=mock_da2), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da2), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import EmployeesDashboard
            d = EmployeesDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            d.load_data()
            text = d.metric_cards['nearest_birthday'].value_label.text()
            assert len(text) <= 30


class TestSalariesDashboard:
    """Тесты SalariesDashboard"""

    def test_creation(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import SalariesDashboard
            d = SalariesDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            assert 'total_paid' in d.metric_cards

    def test_load_data(self, qtbot, mock_da):
        with patch('ui.dashboards.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.DataAccess', return_value=mock_da), \
             patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboards import SalariesDashboard
            d = SalariesDashboard(db_manager=MagicMock())
            qtbot.addWidget(d)
            d.load_data()
            mock_da.get_salaries_dashboard_stats.assert_called()
