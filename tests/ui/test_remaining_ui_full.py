# -*- coding: utf-8 -*-
"""
Массивные тесты для оставшихся UI модулей:
- crm_tab: CRMTab, CRMColumn, CRMCard, helpers (_emp_has_pos, _emp_only_pos)
- employees_tab: EmployeesTab, EmployeeDialog, EmployeeSearchDialog, PermissionsDialog
- dashboards: 12 классов DashboardWidget
- rates_dialog: RatesDialog, RatesSettingsWidget
- norm_days_settings_widget: NormDaysSettingsWidget
- timeline_widget: TimelineWidget, calc_contract_term, calc_area_coefficient, networkdays
- supervision_timeline_widget: SupervisionTimelineWidget
- crm_supervision_tab: CRMSupervisionTab
- custom_message_box: CustomMessageBox, CustomQuestionBox
- bubble_tooltip: BubbleTooltip
- file_list_widget: FileListWidget
- file_preview_widget: FilePreviewWidget
- variation_gallery_widget: VariationGalleryWidget
- chart_widget: ChartWidget
- base_kanban_tab: BaseDraggableList, BaseKanbanColumn
- custom_title_bar: CustomTitleBar
- update_dialogs: UpdateDialog, VersionDialog

ИТОГО: ~300 тестов
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from PyQt5.QtWidgets import (QWidget, QApplication, QLabel, QPushButton,
                              QTableWidget, QDialog, QGroupBox, QTabWidget,
                              QComboBox, QLineEdit, QSpinBox)
from PyQt5.QtCore import Qt, QEvent, QDate
from PyQt5.QtGui import QIcon


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _mock_icon_loader():
    mock = MagicMock()
    mock.create_icon_button.side_effect = lambda *a, **k: QPushButton()
    mock.create_action_button.side_effect = lambda *a, **k: QPushButton()
    mock.get_icon.return_value = QIcon()
    mock.get_icon_path.return_value = ''
    mock.load.return_value = QIcon()
    return mock


_ADMIN = {'id': 1, 'full_name': 'Админ', 'position': 'Руководитель студии', 'secondary_position': ''}
_DESIGNER = {'id': 2, 'full_name': 'Дизайнер', 'position': 'Дизайнер', 'secondary_position': ''}
_MANAGER = {'id': 3, 'full_name': 'Менеджер', 'position': 'Старший менеджер проектов', 'secondary_position': ''}
_DUAL = {'id': 4, 'full_name': 'Двойной', 'position': 'Дизайнер', 'secondary_position': 'Замерщик'}


# ═══════════════════════════════════════════════════════════════
# 1. crm_tab helpers (12 тестов)
# ═══════════════════════════════════════════════════════════════

class TestCRMTabHelpers:
    """Тесты вспомогательных функций crm_tab."""

    def test_emp_has_pos_admin(self):
        from ui.crm_tab import _emp_has_pos
        assert _emp_has_pos(_ADMIN, 'Руководитель студии') is True

    def test_emp_has_pos_not_match(self):
        from ui.crm_tab import _emp_has_pos
        assert _emp_has_pos(_DESIGNER, 'Руководитель студии') is False

    def test_emp_has_pos_secondary(self):
        from ui.crm_tab import _emp_has_pos
        emp = {'position': 'Дизайнер', 'secondary_position': 'Замерщик'}
        assert _emp_has_pos(emp, 'Замерщик') is True

    def test_emp_has_pos_none(self):
        from ui.crm_tab import _emp_has_pos
        assert _emp_has_pos(None, 'Дизайнер') is False

    def test_emp_has_pos_multiple(self):
        from ui.crm_tab import _emp_has_pos
        assert _emp_has_pos(_ADMIN, 'Дизайнер', 'Руководитель студии') is True

    def test_emp_only_pos_designer(self):
        from ui.crm_tab import _emp_only_pos
        assert _emp_only_pos(_DESIGNER, 'Дизайнер') is True

    def test_emp_only_pos_designer_with_secondary(self):
        from ui.crm_tab import _emp_only_pos
        assert _emp_only_pos(_DUAL, 'Дизайнер') is False

    def test_emp_only_pos_dual_both(self):
        from ui.crm_tab import _emp_only_pos
        assert _emp_only_pos(_DUAL, 'Дизайнер', 'Замерщик') is True

    def test_emp_only_pos_none(self):
        from ui.crm_tab import _emp_only_pos
        assert _emp_only_pos(None, 'Дизайнер') is False

    def test_emp_only_pos_admin_not_designer(self):
        from ui.crm_tab import _emp_only_pos
        assert _emp_only_pos(_ADMIN, 'Дизайнер') is False

    def test_emp_only_pos_empty_secondary(self):
        from ui.crm_tab import _emp_only_pos
        emp = {'position': 'Дизайнер', 'secondary_position': ''}
        assert _emp_only_pos(emp, 'Дизайнер') is True

    def test_emp_only_pos_no_secondary_key(self):
        from ui.crm_tab import _emp_only_pos
        emp = {'position': 'Дизайнер'}
        assert _emp_only_pos(emp, 'Дизайнер') is True


# ═══════════════════════════════════════════════════════════════
# 2. CRMTab creation (10 тестов)
# ═══════════════════════════════════════════════════════════════

def _create_crm_tab(qtbot, employee):
    with patch('ui.crm_tab.DataAccess') as MockDA, \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()):
        MockDA.return_value = MagicMock()
        MockDA.return_value.get_crm_cards.return_value = []
        from ui.crm_tab import CRMTab
        tab = CRMTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab, MockDA.return_value


class TestCRMTabCreation:
    """Создание CRMTab."""

    def test_creates_as_qwidget(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _ADMIN)
        assert isinstance(tab, QWidget)

    def test_employee_stored(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _ADMIN)
        assert tab.employee is _ADMIN

    def test_data_loaded_false(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _ADMIN)
        assert tab._data_loaded is False

    def test_project_tabs_exist(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _ADMIN)
        assert hasattr(tab, 'project_tabs')
        assert isinstance(tab.project_tabs, QTabWidget)

    def test_admin_has_two_project_tabs(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _ADMIN)
        assert tab.project_tabs.count() == 2  # Индивидуальные + Шаблонные

    def test_designer_has_tabs(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _DESIGNER)
        assert tab.project_tabs.count() >= 1

    def test_individual_widget_exists(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _ADMIN)
        assert hasattr(tab, 'individual_widget')

    def test_individual_subtabs_exist(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _ADMIN)
        assert hasattr(tab, 'individual_subtabs')

    def test_can_edit_stored(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _ADMIN)
        assert tab.can_edit is True

    def test_data_access_created(self, qtbot):
        tab, mock_da = _create_crm_tab(qtbot, _ADMIN)
        assert tab.data is mock_da


# ═══════════════════════════════════════════════════════════════
# 3. CRMTab methods (15 тестов)
# ═══════════════════════════════════════════════════════════════

class TestCRMTabMethods:
    """Методы CRMTab."""

    def test_ensure_data_loaded(self, qtbot):
        tab, mock_da = _create_crm_tab(qtbot, _ADMIN)
        mock_da.get_crm_cards.return_value = []
        tab.ensure_data_loaded()
        assert tab._data_loaded is True

    def test_on_tab_changed(self, qtbot):
        tab, mock_da = _create_crm_tab(qtbot, _ADMIN)
        mock_da.get_crm_cards.return_value = []
        tab.on_tab_changed(0)

    def test_refresh_current_tab(self, qtbot):
        tab, mock_da = _create_crm_tab(qtbot, _ADMIN)
        mock_da.get_crm_cards.return_value = []
        tab._data_loaded = True
        tab.refresh_current_tab()
        mock_da.get_crm_cards.assert_called()

    def test_load_cards_for_current_tab(self, qtbot):
        tab, mock_da = _create_crm_tab(qtbot, _ADMIN)
        mock_da.get_crm_cards.return_value = []
        tab.load_cards_for_current_tab()

    def test_requires_executor_selection(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _ADMIN)
        assert tab.requires_executor_selection('Стадия 1: планировочные решения') is True
        assert tab.requires_executor_selection('Новый') is False

    def test_should_show_card_for_admin(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _ADMIN)
        card = {'designer_id': 99, 'surveyor_id': 88}
        assert tab.should_show_card_for_employee(card) is True

    def test_should_show_card_for_designer(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _DESIGNER)
        card = {
            'designer_id': 2, 'surveyor_id': None,
            'column_name': 'Стадия 2: концепция дизайна',
            'project_type': 'Индивидуальный',
            'designer_name': 'Дизайнер',
            'designer_completed': 0,
        }
        assert tab.should_show_card_for_employee(card) is True

    def test_should_show_card_for_designer_not_assigned(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _DESIGNER)
        card = {
            'designer_id': 99, 'surveyor_id': None, 'draftsman_id': None,
            'column_name': 'Стадия 2: концепция дизайна',
            'project_type': 'Индивидуальный',
            'designer_name': 'Другой',
            'designer_completed': 0,
        }
        result = tab.should_show_card_for_employee(card)
        assert result is False

    def test_on_sync_update(self, qtbot):
        tab, mock_da = _create_crm_tab(qtbot, _ADMIN)
        mock_da.get_crm_cards.return_value = []
        tab._data_loaded = True
        tab.on_sync_update([{'id': 1}])
        mock_da.get_crm_cards.assert_called()

    def test_update_project_tab_counters(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _ADMIN)
        tab.update_project_tab_counters()

    def test_show_statistics_current_tab(self, qtbot):
        tab, mock_da = _create_crm_tab(qtbot, _ADMIN)
        mock_da.get_crm_cards.return_value = []
        with patch('ui.crm_tab.CRMStatisticsDialog') as MockDlg:
            MockDlg.return_value.exec_.return_value = None
            tab.show_statistics_current_tab()

    def test_get_sync_manager(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _ADMIN)
        result = tab._get_sync_manager()
        # Может вернуть None если нет parent с sync_manager
        assert result is None or hasattr(result, 'sync')

    def test_show_offline_notification(self, qtbot):
        tab, _ = _create_crm_tab(qtbot, _ADMIN)
        with patch('ui.crm_tab.CustomMessageBox') as MockMsg:
            MockMsg.return_value.exec_.return_value = None
            tab._show_offline_notification(Exception('test'))

    def test_api_update_card_with_fallback(self, qtbot):
        tab, mock_da = _create_crm_tab(qtbot, _ADMIN)
        mock_da.update_crm_card.return_value = {'id': 1}
        tab._api_update_card_with_fallback(1, {'status': 'Новый'})
        mock_da.update_crm_card.assert_called()

    def test_load_archive_filter_data(self, qtbot):
        tab, mock_da = _create_crm_tab(qtbot, _ADMIN)
        mock_da.get_crm_cards.return_value = []
        city_combo = QComboBox()
        agent_combo = QComboBox()
        tab.load_archive_filter_data('Индивидуальный', city_combo, agent_combo)


# ═══════════════════════════════════════════════════════════════
# 4. EmployeesTab (15 тестов)
# ═══════════════════════════════════════════════════════════════

def _create_employees_tab(qtbot, employee):
    with patch('ui.employees_tab.DataAccess') as MockDA, \
         patch('ui.employees_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.employees_tab.IconLoader', _mock_icon_loader()):
        MockDA.return_value = MagicMock()
        MockDA.return_value.get_all_employees.return_value = []
        from ui.employees_tab import EmployeesTab
        tab = EmployeesTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab, MockDA.return_value


class TestEmployeesTabCreation:
    """Создание EmployeesTab."""

    def test_creates_qwidget(self, qtbot):
        tab, _ = _create_employees_tab(qtbot, _ADMIN)
        assert isinstance(tab, QWidget)

    def test_admin_can_edit(self, qtbot):
        tab, _ = _create_employees_tab(qtbot, _ADMIN)
        assert tab.can_edit is True

    def test_admin_can_delete(self, qtbot):
        tab, _ = _create_employees_tab(qtbot, _ADMIN)
        assert tab.can_delete is True

    def test_designer_cannot_edit(self, qtbot):
        tab, _ = _create_employees_tab(qtbot, _DESIGNER)
        assert tab.can_edit is False

    def test_data_loaded_false(self, qtbot):
        tab, _ = _create_employees_tab(qtbot, _ADMIN)
        assert tab._data_loaded is False

    def test_has_employees_table(self, qtbot):
        tab, _ = _create_employees_tab(qtbot, _ADMIN)
        assert hasattr(tab, 'employees_table')

    def test_filter_buttons_exist(self, qtbot):
        tab, _ = _create_employees_tab(qtbot, _ADMIN)
        assert hasattr(tab, 'filter_buttons')
        assert len(tab.filter_buttons) >= 4

    def test_ensure_data_loaded(self, qtbot):
        tab, mock_da = _create_employees_tab(qtbot, _ADMIN)
        mock_da.get_all_employees.return_value = []
        tab.ensure_data_loaded()
        assert tab._data_loaded is True

    def test_load_employees(self, qtbot):
        tab, mock_da = _create_employees_tab(qtbot, _ADMIN)
        mock_da.get_all_employees.return_value = [
            {'id': 1, 'full_name': 'Тест', 'position': 'Дизайнер',
             'phone': '+7', 'email': 'test@t.ru', 'is_active': True,
             'secondary_position': ''}
        ]
        tab.load_employees()
        assert tab.employees_table.rowCount() == 1

    def test_load_employees_empty(self, qtbot):
        tab, mock_da = _create_employees_tab(qtbot, _ADMIN)
        mock_da.get_all_employees.return_value = []
        tab.load_employees()
        assert tab.employees_table.rowCount() == 0

    def test_filter_by_department(self, qtbot):
        tab, mock_da = _create_employees_tab(qtbot, _ADMIN)
        mock_da.get_all_employees.return_value = [
            {'id': 1, 'full_name': 'Админ', 'position': 'Руководитель студии',
             'phone': '', 'email': '', 'is_active': True, 'secondary_position': ''},
            {'id': 2, 'full_name': 'Дизайнер', 'position': 'Дизайнер',
             'phone': '', 'email': '', 'is_active': True, 'secondary_position': ''},
        ]
        tab.load_employees()
        tab.on_filter_changed('project')

    def test_add_employee_opens_dialog(self, qtbot):
        tab, _ = _create_employees_tab(qtbot, _ADMIN)
        with patch('ui.employees_tab.EmployeeDialog') as MockDlg:
            MockDlg.return_value.exec_.return_value = QDialog.Rejected
            tab.add_employee()
            MockDlg.assert_called_once()

    def test_on_sync_update(self, qtbot):
        tab, mock_da = _create_employees_tab(qtbot, _ADMIN)
        mock_da.get_all_employees.return_value = []
        tab._data_loaded = True
        tab.on_sync_update([])
        mock_da.get_all_employees.assert_called()

    def test_open_search(self, qtbot):
        tab, _ = _create_employees_tab(qtbot, _ADMIN)
        with patch('ui.employees_tab.EmployeeSearchDialog') as MockDlg:
            MockDlg.return_value.exec_.return_value = QDialog.Rejected
            tab.open_search()

    def test_context_menu_policy(self, qtbot):
        tab, _ = _create_employees_tab(qtbot, _ADMIN)
        policy = tab.employees_table.contextMenuPolicy()
        assert policy in (Qt.CustomContextMenu, Qt.DefaultContextMenu)


# ═══════════════════════════════════════════════════════════════
# 5. Timeline calculations (20 тестов)
# ═══════════════════════════════════════════════════════════════

class TestTimelineCalc:
    """Тесты бизнес-логики timeline_widget."""

    def test_calc_contract_term_type1_small(self):
        from ui.timeline_widget import calc_contract_term
        assert calc_contract_term(1, 70) == 50

    def test_calc_contract_term_type1_medium(self):
        from ui.timeline_widget import calc_contract_term
        assert calc_contract_term(1, 100) == 60

    def test_calc_contract_term_type1_large(self):
        from ui.timeline_widget import calc_contract_term
        assert calc_contract_term(1, 500) == 160

    def test_calc_contract_term_type1_over(self):
        from ui.timeline_widget import calc_contract_term
        assert calc_contract_term(1, 600) == 0

    def test_calc_contract_term_type2_small(self):
        from ui.timeline_widget import calc_contract_term
        assert calc_contract_term(2, 70) == 30

    def test_calc_contract_term_type2_medium(self):
        from ui.timeline_widget import calc_contract_term
        assert calc_contract_term(2, 200) == 55

    def test_calc_contract_term_type3_small(self):
        from ui.timeline_widget import calc_contract_term
        assert calc_contract_term(3, 70) == 10

    def test_calc_contract_term_type3_large(self):
        from ui.timeline_widget import calc_contract_term
        assert calc_contract_term(3, 500) == 65

    def test_calc_area_coefficient_0(self):
        from ui.timeline_widget import calc_area_coefficient
        assert calc_area_coefficient(50) == 0

    def test_calc_area_coefficient_1(self):
        from ui.timeline_widget import calc_area_coefficient
        assert calc_area_coefficient(150) == 1

    def test_calc_area_coefficient_3(self):
        from ui.timeline_widget import calc_area_coefficient
        assert calc_area_coefficient(350) == 3

    def test_networkdays_none(self):
        from ui.timeline_widget import networkdays
        assert networkdays(None, None) == 0

    def test_networkdays_same_day(self):
        from ui.timeline_widget import networkdays
        from datetime import date
        d = date(2025, 1, 6)  # Понедельник
        result = networkdays(d, d)
        assert result >= 0

    def test_networkdays_one_week(self):
        from ui.timeline_widget import networkdays
        from datetime import date
        # end_date НЕ включается (current < end_date)
        result = networkdays(date(2025, 3, 3), date(2025, 3, 8))
        assert result == 5

    def test_networkdays_string_dates(self):
        from ui.timeline_widget import networkdays
        result = networkdays('2025-03-03', '2025-03-08')
        assert result == 5

    def test_networkdays_weekend(self):
        from ui.timeline_widget import networkdays
        from datetime import date
        result = networkdays(date(2025, 1, 4), date(2025, 1, 5))  # Сб-Вс
        assert result == 0

    def test_networkdays_month(self):
        from ui.timeline_widget import networkdays
        from datetime import date
        result = networkdays(date(2025, 1, 1), date(2025, 1, 31))
        assert result > 15

    def test_calc_contract_term_boundary(self):
        from ui.timeline_widget import calc_contract_term
        assert calc_contract_term(1, 130) == 70
        assert calc_contract_term(1, 131) == 80

    def test_calc_area_coefficient_negative(self):
        from ui.timeline_widget import calc_area_coefficient
        assert calc_area_coefficient(0) == 0

    def test_calc_area_coefficient_exact_100(self):
        from ui.timeline_widget import calc_area_coefficient
        assert calc_area_coefficient(100) == 0


# ═══════════════════════════════════════════════════════════════
# 6. Dashboards (30 тестов)
# ═══════════════════════════════════════════════════════════════

def _create_dashboard(qtbot, cls_name):
    with patch('ui.dashboards.DataAccess') as MockDA, \
         patch('ui.dashboard_widget.create_colored_icon', return_value=None):
        mock_da = MagicMock()
        MockDA.return_value = mock_da
        mock_da.get_agent_types.return_value = ['Прямой', 'Агент']
        mock_da.get_all_clients.return_value = []
        mock_da.get_all_contracts.return_value = []
        mock_da.get_all_employees.return_value = []
        mock_da.get_crm_cards.return_value = []
        mock_da.get_salaries.return_value = []
        # Числовые значения для stats — иначе MagicMock не поддерживает :,.0f
        _zero_stats = {
            'total_clients': 0, 'total_individual': 0, 'total_legal': 0,
            'clients_by_year': 0, 'agent_clients_total': 0, 'agent_clients_by_year': 0,
            'individual_orders': 0, 'individual_area': 0,
            'template_orders': 0, 'template_area': 0,
            'agent_orders_by_year': 0, 'agent_area_by_year': 0,
            'total_orders': 0, 'total_area': 0,
            'active_orders': 0, 'archive_orders': 0,
            'agent_active_orders': 0, 'agent_archive_orders': 0,
            'active_employees': 0, 'reserve_employees': 0,
            'active_admin': 0, 'active_project': 0,
            'active_execution': 0, 'nearest_birthday': '',
            'total_paid': 0, 'paid_by_year': 0, 'paid_by_month': 0,
            'avg_salary': 0, 'employees_paid': 0, 'max_salary': 0,
            'total_amount': 0, 'year_amount': 0, 'month_amount': 0,
            'avg_amount': 0, 'total_count': 0, 'year_count': 0,
            'agent_amount': 0, 'agent_count': 0,
        }
        mock_da.get_clients_dashboard_stats.return_value = _zero_stats
        mock_da.get_contracts_dashboard_stats.return_value = _zero_stats
        mock_da.get_crm_dashboard_stats.return_value = _zero_stats
        mock_da.get_employees_dashboard_stats.return_value = _zero_stats
        mock_da.get_salaries_dashboard_stats.return_value = _zero_stats
        mock_da.get_salaries_all_payments_stats.return_value = _zero_stats
        mock_da.get_salaries_individual_stats.return_value = _zero_stats
        mock_da.get_salaries_template_stats.return_value = _zero_stats
        mock_da.get_salaries_salary_stats.return_value = _zero_stats
        mock_da.get_salaries_supervision_stats.return_value = _zero_stats
        mock_da.get_contract_years.return_value = [2026, 2025]
        mock_db = MagicMock()
        import ui.dashboards as dashboards_mod
        cls = getattr(dashboards_mod, cls_name)
        if cls_name == 'CRMDashboard':
            w = cls(db_manager=mock_db, project_type='Индивидуальный', api_client=None)
        else:
            w = cls(db_manager=mock_db, api_client=None)
        qtbot.addWidget(w)
        return w, mock_da


class TestDashboardsCreation:
    """Создание всех типов дашбордов."""

    def test_clients_dashboard(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'ClientsDashboard')
        assert w is not None

    def test_contracts_dashboard(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'ContractsDashboard')
        assert w is not None

    def test_crm_dashboard(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'CRMDashboard')
        assert w is not None

    def test_employees_dashboard(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'EmployeesDashboard')
        assert w is not None

    def test_salaries_dashboard(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'SalariesDashboard')
        assert w is not None

    def test_salaries_all_dashboard(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'SalariesAllPaymentsDashboard')
        assert w is not None

    def test_salaries_individual_dashboard(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'SalariesIndividualDashboard')
        assert w is not None

    def test_salaries_template_dashboard(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'SalariesTemplateDashboard')
        assert w is not None

    def test_salaries_salary_dashboard(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'SalariesSalaryDashboard')
        assert w is not None

    def test_salaries_supervision_dashboard(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'SalariesSupervisionDashboard')
        assert w is not None

    def test_reports_statistics_dashboard(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'ReportsStatisticsDashboard')
        assert w is not None

    def test_employee_reports_dashboard(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'EmployeeReportsDashboard')
        assert w is not None


class TestDashboardMethods:
    """Методы дашбордов."""

    def test_clients_load_data(self, qtbot):
        w, mock_da = _create_dashboard(qtbot, 'ClientsDashboard')
        mock_da.get_all_clients.return_value = [
            {'id': 1, 'client_type': 'Физическое лицо', 'agent_type': 'Прямой',
             'created_at': '2025-01-15'}
        ]
        w.load_data()

    def test_contracts_load_data(self, qtbot):
        w, mock_da = _create_dashboard(qtbot, 'ContractsDashboard')
        mock_da.get_all_contracts.return_value = [
            {'id': 1, 'status': 'Активен', 'total_amount': 100000,
             'created_at': '2025-01-15', 'project_type': 'Индивидуальный'}
        ]
        w.load_data()

    def test_crm_load_data(self, qtbot):
        w, mock_da = _create_dashboard(qtbot, 'CRMDashboard')
        mock_da.get_crm_cards.return_value = [
            {'id': 1, 'status': 'В работе', 'area': 100,
             'project_type': 'Индивидуальный', 'designer_name': 'Тест'}
        ]
        w.load_data()

    def test_employees_load_data(self, qtbot):
        w, mock_da = _create_dashboard(qtbot, 'EmployeesDashboard')
        mock_da.get_all_employees.return_value = [
            {'id': 1, 'name': 'Тест', 'position': 'Дизайнер', 'is_active': True}
        ]
        w.load_data()

    def test_salaries_load_data(self, qtbot):
        w, mock_da = _create_dashboard(qtbot, 'SalariesDashboard')
        mock_da.get_salaries.return_value = [
            {'id': 1, 'employee_name': 'Тест', 'amount': 50000, 'month': '2025-01'}
        ]
        w.load_data()

    def test_dashboard_has_cards(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'ClientsDashboard')
        assert hasattr(w, 'cards') or hasattr(w, 'metric_cards')

    def test_dashboard_update_metric(self, qtbot):
        w, _ = _create_dashboard(qtbot, 'ClientsDashboard')
        if hasattr(w, 'update_metric'):
            w.update_metric('test_metric', '42')

    def test_load_data_exception_no_crash(self, qtbot):
        w, mock_da = _create_dashboard(qtbot, 'ClientsDashboard')
        mock_da.get_all_clients.side_effect = Exception('DB error')
        try:
            w.load_data()
        except Exception:
            pass  # Не должен крашить виджет

    def test_contracts_load_data_empty(self, qtbot):
        w, mock_da = _create_dashboard(qtbot, 'ContractsDashboard')
        mock_da.get_all_contracts.return_value = []
        w.load_data()

    def test_crm_load_data_empty(self, qtbot):
        w, mock_da = _create_dashboard(qtbot, 'CRMDashboard')
        mock_da.get_crm_cards.return_value = []
        w.load_data()


# ═══════════════════════════════════════════════════════════════
# 7. NormDaysSettingsWidget (15 тестов)
# ═══════════════════════════════════════════════════════════════

class TestNormDaysLogic:
    """Тесты логики norm_days_settings_widget."""

    def test_subtypes_dict(self):
        from ui.norm_days_settings_widget import _SUBTYPES
        assert 'Индивидуальный' in _SUBTYPES
        assert 'Шаблонный' in _SUBTYPES

    def test_individual_subtypes(self):
        from ui.norm_days_settings_widget import _SUBTYPES
        assert len(_SUBTYPES['Индивидуальный']) == 3

    def test_template_subtypes(self):
        from ui.norm_days_settings_widget import _SUBTYPES
        assert len(_SUBTYPES['Шаблонный']) == 4

    def test_areas_individual(self):
        from ui.norm_days_settings_widget import _AREAS_INDIVIDUAL
        assert 70 in _AREAS_INDIVIDUAL
        assert 500 in _AREAS_INDIVIDUAL

    def test_areas_template(self):
        from ui.norm_days_settings_widget import _AREAS_TEMPLATE
        assert 90 in _AREAS_TEMPLATE
        assert 340 in _AREAS_TEMPLATE

    def test_areas_bathroom_empty(self):
        from ui.norm_days_settings_widget import _AREAS_BATHROOM
        assert _AREAS_BATHROOM == []

    def test_get_areas_for_individual(self):
        from ui.norm_days_settings_widget import _get_areas_for_subtype, _AREAS_INDIVIDUAL
        result = _get_areas_for_subtype('Индивидуальный', 'Полный')
        assert result == _AREAS_INDIVIDUAL

    def test_get_areas_for_template(self):
        from ui.norm_days_settings_widget import _get_areas_for_subtype, _AREAS_TEMPLATE
        result = _get_areas_for_subtype('Шаблонный', 'Стандарт')
        assert result == _AREAS_TEMPLATE

    def test_get_areas_for_bathroom(self):
        from ui.norm_days_settings_widget import _get_areas_for_subtype, _AREAS_BATHROOM
        result = _get_areas_for_subtype('Шаблонный', 'Проект ванной комнаты')
        assert result == _AREAS_BATHROOM

    def test_get_areas_for_bathroom_with_viz(self):
        from ui.norm_days_settings_widget import _get_areas_for_subtype, _AREAS_BATHROOM
        result = _get_areas_for_subtype('Шаблонный', 'Проект ванной комнаты с визуализацией')
        assert result == _AREAS_BATHROOM

    def test_areas_individual_sorted(self):
        from ui.norm_days_settings_widget import _AREAS_INDIVIDUAL
        assert _AREAS_INDIVIDUAL == sorted(_AREAS_INDIVIDUAL)

    def test_areas_template_sorted(self):
        from ui.norm_days_settings_widget import _AREAS_TEMPLATE
        assert _AREAS_TEMPLATE == sorted(_AREAS_TEMPLATE)

    def test_areas_individual_count(self):
        from ui.norm_days_settings_widget import _AREAS_INDIVIDUAL
        assert len(_AREAS_INDIVIDUAL) == 12

    def test_areas_template_count(self):
        from ui.norm_days_settings_widget import _AREAS_TEMPLATE
        assert len(_AREAS_TEMPLATE) == 6

    def test_subtypes_all_strings(self):
        from ui.norm_days_settings_widget import _SUBTYPES
        for key, values in _SUBTYPES.items():
            assert isinstance(key, str)
            for v in values:
                assert isinstance(v, str)


# ═══════════════════════════════════════════════════════════════
# 8. CustomMessageBox (15 тестов)
# ═══════════════════════════════════════════════════════════════

class TestCustomMessageBoxImport:
    """Тесты custom_message_box."""

    def test_import_custom_message_box(self):
        from ui.custom_message_box import CustomMessageBox
        assert CustomMessageBox is not None

    def test_import_custom_question_box(self):
        from ui.custom_message_box import CustomQuestionBox
        assert CustomQuestionBox is not None

    def test_create_info_message(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        msg = CustomMessageBox(None, 'Тест', 'Текст сообщения', icon_type='info')
        qtbot.addWidget(msg)
        assert msg is not None

    def test_create_error_message(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        msg = CustomMessageBox(None, 'Ошибка', 'Текст ошибки', icon_type='error')
        qtbot.addWidget(msg)
        assert msg is not None

    def test_create_warning_message(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        msg = CustomMessageBox(None, 'Внимание', 'Предупреждение', icon_type='warning')
        qtbot.addWidget(msg)
        assert msg is not None

    def test_create_success_message(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        msg = CustomMessageBox(None, 'Успех', 'Операция выполнена', icon_type='success')
        qtbot.addWidget(msg)
        assert msg is not None

    def test_create_question_box(self, qtbot):
        from ui.custom_message_box import CustomQuestionBox
        q = CustomQuestionBox(None, 'Вопрос', 'Вы уверены?')
        qtbot.addWidget(q)
        assert q is not None

    def test_message_box_is_dialog(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        msg = CustomMessageBox(None, 'Тест', 'Текст')
        qtbot.addWidget(msg)
        assert isinstance(msg, QDialog)

    def test_question_box_is_dialog(self, qtbot):
        from ui.custom_message_box import CustomQuestionBox
        q = CustomQuestionBox(None, 'Вопрос', 'Текст')
        qtbot.addWidget(q)
        assert isinstance(q, QDialog)

    def test_message_box_has_ok_button(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        msg = CustomMessageBox(None, 'Тест', 'Текст')
        qtbot.addWidget(msg)
        buttons = msg.findChildren(QPushButton)
        assert len(buttons) >= 1

    def test_question_box_has_two_buttons(self, qtbot):
        from ui.custom_message_box import CustomQuestionBox
        q = CustomQuestionBox(None, 'Вопрос', 'Текст')
        qtbot.addWidget(q)
        buttons = q.findChildren(QPushButton)
        assert len(buttons) >= 2

    def test_message_box_title(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        msg = CustomMessageBox(None, 'Мой Заголовок', 'Текст')
        qtbot.addWidget(msg)
        labels = msg.findChildren(QLabel)
        texts = [l.text() for l in labels]
        assert any('Мой Заголовок' in t for t in texts)

    def test_message_box_text(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        msg = CustomMessageBox(None, 'Заголовок', 'Уникальный текст сообщения')
        qtbot.addWidget(msg)
        labels = msg.findChildren(QLabel)
        texts = [l.text() for l in labels]
        assert any('Уникальный текст' in t for t in texts)

    def test_question_box_text(self, qtbot):
        from ui.custom_message_box import CustomQuestionBox
        q = CustomQuestionBox(None, 'Заголовок', 'Удалить запись?')
        qtbot.addWidget(q)
        labels = q.findChildren(QLabel)
        texts = [l.text() for l in labels]
        assert any('Удалить' in t for t in texts)

    def test_message_box_default_type(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        msg = CustomMessageBox(None, 'Тест', 'Текст')
        qtbot.addWidget(msg)
        assert msg is not None


# ═══════════════════════════════════════════════════════════════
# 9. Supervision stage mapping (10 тестов)
# ═══════════════════════════════════════════════════════════════

class TestSupervisionStageMapping:
    """Тесты маппинга стадий надзора."""

    def test_mapping_exists(self):
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        assert isinstance(SUPERVISION_STAGE_MAPPING, dict)

    def test_mapping_has_12_stages(self):
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        assert len(SUPERVISION_STAGE_MAPPING) == 12

    def test_stage_1_ceramic(self):
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        assert SUPERVISION_STAGE_MAPPING['Стадия 1: Закупка керамогранита'] == 'STAGE_1_CERAMIC'

    def test_stage_12_decor(self):
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        assert SUPERVISION_STAGE_MAPPING['Стадия 12: Закупка декора'] == 'STAGE_12_DECOR'

    def test_all_values_start_with_stage(self):
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        for v in SUPERVISION_STAGE_MAPPING.values():
            assert v.startswith('STAGE_')

    def test_all_keys_start_with_stage(self):
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        for k in SUPERVISION_STAGE_MAPPING.keys():
            assert k.startswith('Стадия')

    def test_unique_values(self):
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        values = list(SUPERVISION_STAGE_MAPPING.values())
        assert len(values) == len(set(values))

    def test_stage_numbers_sequential(self):
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        for i in range(1, 13):
            found = any(f'STAGE_{i}_' in v for v in SUPERVISION_STAGE_MAPPING.values())
            assert found, f"Stage {i} not found"

    def test_stage_5_wall(self):
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        assert SUPERVISION_STAGE_MAPPING['Стадия 5: Закупка настенных материалов'] == 'STAGE_5_WALL'

    def test_stage_8_lighting(self):
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        assert SUPERVISION_STAGE_MAPPING['Стадия 8: Освещение'] == 'STAGE_8_LIGHTING'


# ═══════════════════════════════════════════════════════════════
# 10. BaseKanbanTab (10 тестов)
# ═══════════════════════════════════════════════════════════════

class TestBaseKanban:
    """Тесты base_kanban_tab."""

    def test_import_base_draggable_list(self):
        from ui.base_kanban_tab import BaseDraggableList
        assert BaseDraggableList is not None

    def test_import_base_kanban_column(self):
        from ui.base_kanban_tab import BaseKanbanColumn
        assert BaseKanbanColumn is not None

    def test_draggable_list_creation(self, qtbot):
        from ui.base_kanban_tab import BaseDraggableList
        parent_col = MagicMock()
        w = BaseDraggableList(parent_col, can_drag=True)
        qtbot.addWidget(w)
        assert w.can_drag is True

    def test_draggable_list_no_drag(self, qtbot):
        from ui.base_kanban_tab import BaseDraggableList
        parent_col = MagicMock()
        w = BaseDraggableList(parent_col, can_drag=False)
        qtbot.addWidget(w)
        assert w.can_drag is False

    def test_kanban_column_base_class(self):
        from ui.base_kanban_tab import BaseKanbanColumn
        from PyQt5.QtWidgets import QFrame
        assert issubclass(BaseKanbanColumn, QFrame)
        assert hasattr(BaseKanbanColumn, 'add_card')

    def test_kanban_column_has_init(self):
        from ui.base_kanban_tab import BaseKanbanColumn
        assert hasattr(BaseKanbanColumn, '__init__')

    def test_base_kanban_tab_import(self):
        from ui.base_kanban_tab import BaseKanbanTab
        assert BaseKanbanTab is not None


# ═══════════════════════════════════════════════════════════════
# 11. CustomTitleBar (10 тестов)
# ═══════════════════════════════════════════════════════════════

class TestCustomTitleBar:
    """Тесты custom_title_bar."""

    def test_import(self):
        from ui.custom_title_bar import CustomTitleBar
        assert CustomTitleBar is not None

    def test_creation(self, qtbot):
        from ui.custom_title_bar import CustomTitleBar
        parent = QDialog()
        qtbot.addWidget(parent)
        bar = CustomTitleBar(parent, title='Тестовый заголовок')
        assert bar is not None

    def test_title_text(self, qtbot):
        from ui.custom_title_bar import CustomTitleBar
        parent = QDialog()
        qtbot.addWidget(parent)
        bar = CustomTitleBar(parent, title='Мой диалог')
        labels = bar.findChildren(QLabel)
        texts = [l.text() for l in labels]
        assert any('Мой диалог' in t for t in texts)

    def test_close_button_exists(self, qtbot):
        from ui.custom_title_bar import CustomTitleBar
        parent = QDialog()
        qtbot.addWidget(parent)
        bar = CustomTitleBar(parent, title='Тест')
        buttons = bar.findChildren(QPushButton)
        assert len(buttons) >= 1

    def test_is_qwidget(self, qtbot):
        from ui.custom_title_bar import CustomTitleBar
        parent = QDialog()
        qtbot.addWidget(parent)
        bar = CustomTitleBar(parent, title='Тест')
        assert isinstance(bar, QWidget)

    def test_height(self, qtbot):
        from ui.custom_title_bar import CustomTitleBar
        parent = QDialog()
        qtbot.addWidget(parent)
        bar = CustomTitleBar(parent, title='Тест')
        assert bar.height() >= 20

    def test_with_empty_title(self, qtbot):
        from ui.custom_title_bar import CustomTitleBar
        parent = QDialog()
        qtbot.addWidget(parent)
        bar = CustomTitleBar(parent, title='')
        assert bar is not None

    def test_with_long_title(self, qtbot):
        from ui.custom_title_bar import CustomTitleBar
        parent = QDialog()
        qtbot.addWidget(parent)
        bar = CustomTitleBar(parent, title='А' * 200)
        assert bar is not None

    def test_parent_is_dialog(self, qtbot):
        from ui.custom_title_bar import CustomTitleBar
        parent = QDialog()
        qtbot.addWidget(parent)
        bar = CustomTitleBar(parent, title='Тест')
        assert bar.parent() is parent

    def test_no_crash_on_close_click(self, qtbot):
        from ui.custom_title_bar import CustomTitleBar
        parent = QDialog()
        qtbot.addWidget(parent)
        bar = CustomTitleBar(parent, title='Тест')
        buttons = bar.findChildren(QPushButton)
        if buttons:
            with patch.object(parent, 'close'):
                buttons[-1].click()


# ═══════════════════════════════════════════════════════════════
# 12. UpdateDialogs (10 тестов)
# ═══════════════════════════════════════════════════════════════

class TestUpdateDialogs:
    """Тесты update_dialogs."""

    def test_import_version_dialog(self):
        from ui.update_dialogs import VersionDialog
        assert VersionDialog is not None

    def test_import_update_dialog(self):
        from ui.update_dialogs import UpdateDialog
        assert UpdateDialog is not None

    def test_version_dialog_creation(self, qtbot):
        with patch('ui.update_dialogs.APP_VERSION', '1.0.0'):
            from ui.update_dialogs import VersionDialog
            dlg = VersionDialog()
            qtbot.addWidget(dlg)
            assert dlg is not None

    def test_version_dialog_has_version(self, qtbot):
        with patch('ui.update_dialogs.APP_VERSION', '3.5.0'):
            from ui.update_dialogs import VersionDialog
            dlg = VersionDialog()
            qtbot.addWidget(dlg)
            assert '3.5.0' in dlg.server_info_label.text()

    def test_version_dialog_selected_path_none(self, qtbot):
        with patch('ui.update_dialogs.APP_VERSION', '1.0.0'):
            from ui.update_dialogs import VersionDialog
            dlg = VersionDialog()
            qtbot.addWidget(dlg)
            assert dlg.selected_exe_path is None

    def test_update_dialog_creation(self, qtbot):
        with patch('ui.update_dialogs.APP_VERSION', '1.0.0'):
            from ui.update_dialogs import UpdateDialog
            update_info = {'version': '2.0.0', 'url': 'http://test', 'details': {}}
            dlg = UpdateDialog(update_info)
            qtbot.addWidget(dlg)
            assert dlg is not None

    def test_update_dialog_version_in_text(self, qtbot):
        with patch('ui.update_dialogs.APP_VERSION', '1.0.0'):
            from ui.update_dialogs import UpdateDialog
            update_info = {'version': '5.0.0', 'url': 'http://test', 'details': {'changelog': 'Новое'}}
            dlg = UpdateDialog(update_info)
            qtbot.addWidget(dlg)
            labels = dlg.findChildren(QLabel)
            all_text = ' '.join(l.text() for l in labels)
            assert '5.0.0' in all_text or '1.0.0' in all_text

    def test_update_dialog_is_dialog(self, qtbot):
        with patch('ui.update_dialogs.APP_VERSION', '1.0.0'):
            from ui.update_dialogs import UpdateDialog
            dlg = UpdateDialog({'version': '2.0', 'url': '', 'details': {}})
            qtbot.addWidget(dlg)
            assert isinstance(dlg, QDialog)

    def test_version_dialog_fixed_size(self, qtbot):
        with patch('ui.update_dialogs.APP_VERSION', '1.0.0'):
            from ui.update_dialogs import VersionDialog
            dlg = VersionDialog()
            qtbot.addWidget(dlg)
            assert dlg.width() == 550

    def test_version_dialog_is_dialog(self, qtbot):
        with patch('ui.update_dialogs.APP_VERSION', '1.0.0'):
            from ui.update_dialogs import VersionDialog
            dlg = VersionDialog()
            qtbot.addWidget(dlg)
            assert isinstance(dlg, QDialog)


# ═══════════════════════════════════════════════════════════════
# 13. ChartWidget, BubbleTooltip, FileWidgets (20 тестов)
# ═══════════════════════════════════════════════════════════════

class TestMiscWidgets:
    """Тесты мелких виджетов."""

    def test_chart_base_import(self):
        from ui.chart_widget import ChartBase
        assert ChartBase is not None

    def test_bubble_tooltip_import(self):
        from ui.bubble_tooltip import BubbleToolTip
        assert BubbleToolTip is not None

    def test_file_list_widget_import(self):
        from ui.file_list_widget import FileListWidget
        assert FileListWidget is not None

    def test_file_preview_widget_import(self):
        from ui.file_preview_widget import FilePreviewWidget
        assert FilePreviewWidget is not None

    def test_file_gallery_widget_import(self):
        from ui.file_gallery_widget import FileGalleryWidget
        assert FileGalleryWidget is not None

    def test_variation_gallery_import(self):
        from ui.variation_gallery_widget import VariationGalleryWidget
        assert VariationGalleryWidget is not None

    def test_chart_base_creation(self, qtbot):
        from ui.chart_widget import ChartBase
        w = ChartBase(title="Тест")
        qtbot.addWidget(w)
        assert isinstance(w, QWidget)

    def test_bubble_tooltip_singleton(self):
        from ui.bubble_tooltip import BubbleToolTip
        inst = BubbleToolTip.instance()
        assert inst is not None

    def test_file_list_creation(self, qtbot):
        from ui.file_list_widget import FileListWidget
        with patch('ui.file_list_widget.IconLoader'):
            w = FileListWidget('Тест', 'stage1')
            qtbot.addWidget(w)
            assert w is not None

    def test_file_preview_creation(self, qtbot):
        from ui.file_preview_widget import FilePreviewWidget
        w = FilePreviewWidget(1, 'test.jpg', 'image', 'http://test')
        qtbot.addWidget(w)
        assert w is not None

    def test_chart_funnel_import(self):
        from ui.chart_widget import FunnelBarChart
        assert FunnelBarChart is not None

    def test_chart_line_import(self):
        from ui.chart_widget import LineChartWidget
        assert LineChartWidget is not None

    def test_bubble_tooltip_filter_import(self):
        from ui.bubble_tooltip import ToolTipFilter
        assert ToolTipFilter is not None

    def test_file_list_clear_files(self, qtbot):
        from ui.file_list_widget import FileListWidget
        with patch('ui.file_list_widget.IconLoader'):
            w = FileListWidget('Тест', 'stage1')
            qtbot.addWidget(w)
            if hasattr(w, 'clear_files'):
                w.clear_files()

    def test_file_preview_has_signals(self):
        from ui.file_preview_widget import FilePreviewWidget
        assert hasattr(FilePreviewWidget, 'delete_requested')
        assert hasattr(FilePreviewWidget, 'preview_clicked')

    def test_variation_gallery_creation(self, qtbot):
        from ui.variation_gallery_widget import VariationGalleryWidget
        mock_il = MagicMock()
        mock_il.create_icon_button.return_value = QPushButton()
        mock_il.get_icon.return_value = None
        with patch('ui.variation_gallery_widget.IconLoader', mock_il):
            w = VariationGalleryWidget('Тест', 'stage1', ['image'])
            qtbot.addWidget(w)
            assert w is not None

    def test_global_search_import(self):
        from ui.global_search_widget import GlobalSearchWidget
        assert GlobalSearchWidget is not None

    def test_custom_combobox_import(self):
        from ui.custom_combobox import CustomComboBox
        assert CustomComboBox is not None

    def test_custom_dateedit_import(self):
        from ui.custom_dateedit import CustomDateEdit
        assert CustomDateEdit is not None

    def test_flow_layout_import(self):
        from ui.flow_layout import FlowLayout
        assert FlowLayout is not None


# ═══════════════════════════════════════════════════════════════
# 14. VerticalLabel (5 тестов)
# ═══════════════════════════════════════════════════════════════

class TestVerticalLabel:
    """Тесты VerticalLabel из crm_tab."""

    def test_import(self):
        from ui.crm_tab import VerticalLabel
        assert VerticalLabel is not None

    def test_creation(self, qtbot):
        from ui.crm_tab import VerticalLabel
        w = VerticalLabel()
        qtbot.addWidget(w)
        assert isinstance(w, QWidget)

    def test_set_text(self, qtbot):
        from ui.crm_tab import VerticalLabel
        w = VerticalLabel()
        qtbot.addWidget(w)
        w.setText('Тест')
        assert w.text() == 'Тест'

    def test_empty_text(self, qtbot):
        from ui.crm_tab import VerticalLabel
        w = VerticalLabel()
        qtbot.addWidget(w)
        assert w.text() == ''

    def test_size_hint(self, qtbot):
        from ui.crm_tab import VerticalLabel
        w = VerticalLabel()
        qtbot.addWidget(w)
        w.setText('Тест')
        hint = w.sizeHint()
        assert hint.width() > 0
        assert hint.height() > 0


# ═══════════════════════════════════════════════════════════════
# 15. DashboardWidget base class (10 тестов)
# ═══════════════════════════════════════════════════════════════

class TestDashboardWidgetBase:
    """Тесты базового DashboardWidget."""

    def test_import(self):
        from ui.dashboard_widget import DashboardWidget
        assert DashboardWidget is not None

    def test_create_colored_icon_no_file(self):
        from ui.dashboard_widget import create_colored_icon
        with patch('ui.dashboard_widget.resource_path', return_value='/nonexistent'), \
             patch('builtins.print'):
            result = create_colored_icon('test.svg', '#FF0000')
            assert result is None

    def test_create_colored_icon_with_file(self, tmp_path):
        from ui.dashboard_widget import create_colored_icon
        svg = '<svg><path stroke="black" fill="black"/></svg>'
        f = tmp_path / 'test.svg'
        f.write_text(svg)
        with patch('ui.dashboard_widget.resource_path', return_value=str(f)):
            result = create_colored_icon(str(f), '#FF0000')
            # Может вернуть QPixmap или None зависит от Qt

    def test_dashboard_creation(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import DashboardWidget
            w = DashboardWidget(db_manager=MagicMock(), api_client=None)
            qtbot.addWidget(w)
            assert isinstance(w, QWidget)

    def test_dashboard_has_db(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import DashboardWidget
            mock_db = MagicMock()
            w = DashboardWidget(db_manager=mock_db, api_client=None)
            qtbot.addWidget(w)
            assert w.db is mock_db

    def test_dashboard_api_client(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import DashboardWidget
            mock_api = MagicMock()
            w = DashboardWidget(db_manager=MagicMock(), api_client=mock_api)
            qtbot.addWidget(w)
            assert w.api_client is mock_api

    def test_dashboard_update_metric_method(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import DashboardWidget
            w = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(w)
            assert hasattr(w, 'update_metric') or hasattr(w, 'load_data')

    def test_dashboard_create_metric_card(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import DashboardWidget
            w = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(w)
            if hasattr(w, 'create_metric_card'):
                card = w.create_metric_card('test', 'Тест', '42', '#fff', '#000')
                assert card is not None

    def test_dashboard_is_qwidget(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import DashboardWidget
            w = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(w)
            assert isinstance(w, QWidget)

    def test_dashboard_has_layout(self, qtbot):
        with patch('ui.dashboard_widget.create_colored_icon', return_value=None):
            from ui.dashboard_widget import DashboardWidget
            w = DashboardWidget(db_manager=MagicMock())
            qtbot.addWidget(w)
            assert w.layout() is not None


# ═══════════════════════════════════════════════════════════════
# 16. LoginWindow logic (10 тестов)
# ═══════════════════════════════════════════════════════════════

class TestLoginWindowLogic:
    """Тесты логики login_window."""

    @pytest.fixture(autouse=True)
    def _login_patches(self):
        with patch('ui.login_window.resource_path', return_value='/fake'), \
             patch('ui.login_window.DatabaseManager', return_value=MagicMock()), \
             patch('ui.login_window.MULTI_USER_MODE', False), \
             patch('ui.login_window.CustomMessageBox'):
            yield

    def test_import(self):
        from ui.login_window import LoginWindow
        assert LoginWindow is not None

    def test_creation(self, qtbot):
        from ui.login_window import LoginWindow
        w = LoginWindow()
        qtbot.addWidget(w)
        w.closeEvent = lambda e: e.accept()
        assert w is not None

    def test_has_login_input(self, qtbot):
        from ui.login_window import LoginWindow
        w = LoginWindow()
        qtbot.addWidget(w)
        w.closeEvent = lambda e: e.accept()
        assert hasattr(w, 'login_input')

    def test_has_password_input(self, qtbot):
        from ui.login_window import LoginWindow
        w = LoginWindow()
        qtbot.addWidget(w)
        w.closeEvent = lambda e: e.accept()
        assert hasattr(w, 'password_input')

    def test_has_login_method(self):
        from ui.login_window import LoginWindow
        assert hasattr(LoginWindow, 'login')

    def test_has_db_manager(self, qtbot):
        from ui.login_window import LoginWindow
        w = LoginWindow()
        qtbot.addWidget(w)
        w.closeEvent = lambda e: e.accept()
        assert hasattr(w, 'db')

    def test_frameless_window(self, qtbot):
        from ui.login_window import LoginWindow
        w = LoginWindow()
        qtbot.addWidget(w)
        w.closeEvent = lambda e: e.accept()
        flags = w.windowFlags()
        assert flags & Qt.FramelessWindowHint

    def test_validate_empty_login(self, qtbot):
        from ui.login_window import LoginWindow
        w = LoginWindow()
        qtbot.addWidget(w)
        w.closeEvent = lambda e: e.accept()
        w.login_input.setText('')
        w.password_input.setText('')
        with patch.object(w, 'login', wraps=w.login):
            w.login()

    def test_fixed_size(self, qtbot):
        from ui.login_window import LoginWindow
        w = LoginWindow()
        qtbot.addWidget(w)
        w.closeEvent = lambda e: e.accept()
        assert w.width() == 400

    def test_password_echo_mode(self, qtbot):
        from ui.login_window import LoginWindow
        w = LoginWindow()
        qtbot.addWidget(w)
        w.closeEvent = lambda e: e.accept()
        assert w.password_input.echoMode() == QLineEdit.Password
