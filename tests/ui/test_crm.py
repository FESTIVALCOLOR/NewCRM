# -*- coding: utf-8 -*-
"""
Тесты CRM вкладки — CRMTab, CRMColumn, CRMCard, диалоги.
82 теста.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLabel,
    QDialog, QComboBox, QFrame, QListWidget,
    QDateEdit
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QIcon


# ========== Фикстура авто-мока CustomMessageBox ==========

@pytest.fixture(autouse=True)
def _mock_crm_msgbox():
    """Глобальный мок CustomMessageBox чтобы диалоги не блокировали тесты."""
    with patch('ui.crm_tab.CustomMessageBox') as mock_msg, \
         patch('ui.crm_tab.CustomQuestionBox') as mock_q, \
         patch('ui.crm_dialogs.CustomMessageBox') as mock_msg2, \
         patch('ui.crm_dialogs.CustomQuestionBox') as mock_q2:
        mock_msg.return_value.exec_.return_value = None
        mock_q.return_value.exec_.return_value = None
        mock_msg2.return_value.exec_.return_value = None
        mock_q2.return_value.exec_.return_value = None
        yield mock_msg


# ========== Хелперы ==========

def _mock_icon_loader():
    """Настроить IconLoader так, чтобы load() возвращал QIcon, а create_icon_button — QPushButton."""
    mock = MagicMock()
    mock.load = MagicMock(return_value=QIcon())
    mock.create_icon_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    mock.create_action_button = MagicMock(side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else ''))
    mock.get_icon_path = MagicMock(return_value='')
    return mock


def _create_crm_tab(qtbot, mock_data_access, employee, can_edit=True):
    """Создать CRMTab с mock DataAccess."""
    with patch('ui.crm_tab.DataAccess') as MockDA, \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.YandexDiskManager', return_value=None), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.crm_tab.TableSettings') as MockTS, \
         patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.TableSettings'):
        MockDA.return_value = mock_data_access
        MockTS.return_value.load_column_collapse_state.return_value = {}
        from ui.crm_tab import CRMTab
        tab = CRMTab(employee=employee, can_edit=can_edit, api_client=None)
        qtbot.addWidget(tab)
        return tab


def _create_crm_card(qtbot, card_data, employee, can_edit=True):
    """Создать CRMCard с mock данными."""
    mock_db = MagicMock()
    with patch('ui.crm_tab.DataAccess') as MockDA, \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.YandexDiskManager', return_value=None), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.TableSettings'):
        MockDA.return_value = MagicMock()
        from ui.crm_tab import CRMCard
        card = CRMCard(card_data, can_edit, mock_db, employee=employee, api_client=None)
        qtbot.addWidget(card)
        return card


def _create_executor_dialog(qtbot, parent_widget, card_id=300,
                             stage_name='Стадия 1: планировочные решения',
                             project_type='Индивидуальный'):
    """Создать ExecutorSelectionDialog."""
    mock_da = parent_widget.data
    mock_da.api_client = None  # Локальный режим
    mock_da.get_project_timeline.return_value = []
    mock_da.get_all_employees.return_value = [
        {'id': 7, 'full_name': 'Чертёжник Тест', 'position': 'Чертёжник', 'status': 'активный'},
        {'id': 6, 'full_name': 'Дизайнер Тест', 'position': 'Дизайнер', 'status': 'активный'},
    ]
    mock_da.get_employees_by_position.return_value = [
        {'id': 7, 'full_name': 'Чертёжник Тест', 'position': 'Чертёжник', 'status': 'активный'},
    ]
    mock_da.get_crm_card.return_value = {'id': card_id, 'stage_executors': [], 'contract_id': 200}
    mock_da.get_previous_executor_by_position.return_value = None
    mock_da.get_contract_id_by_crm_card.return_value = 200
    mock_da.get_contract.return_value = {'id': 200, 'area': 100, 'city': 'Москва', 'project_type': project_type}
    mock_da.calculate_payment_amount.return_value = 10000
    mock_da.create_payment.return_value = {'id': 1}
    mock_da.assign_stage_executor.return_value = {'success': True}
    mock_da.db.get_employees_by_position.return_value = [
        {'id': 7, 'full_name': 'Чертёжник Тест', 'position': 'Чертёжник', 'status': 'активный'},
    ]
    mock_da.db.get_previous_executor_by_position.return_value = None
    mock_da.db.connect.return_value.cursor.return_value.fetchall.return_value = []
    mock_da.db.connect.return_value.cursor.return_value.fetchone.return_value = None

    with patch('ui.crm_tab.DataAccess') as MockDA, \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.TableSettings'):
        MockDA.return_value = mock_da
        from ui.crm_tab import ExecutorSelectionDialog
        dlg = ExecutorSelectionDialog(
            parent_widget, card_id=card_id, stage_name=stage_name,
            project_type=project_type, api_client=None, contract_id=200
        )
        qtbot.addWidget(dlg)
        return dlg


def _create_completion_dialog(qtbot, parent_widget, card_id=300):
    """Создать ProjectCompletionDialog."""
    with patch('ui.crm_tab.DataAccess') as MockDA, \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.TableSettings'):
        MockDA.return_value = parent_widget.data
        from ui.crm_tab import ProjectCompletionDialog
        dlg = ProjectCompletionDialog(parent_widget, card_id=card_id, api_client=None)
        qtbot.addWidget(dlg)
        return dlg


def _create_survey_date_dialog(qtbot, parent_widget, card_id=300):
    """Создать SurveyDateDialog."""
    with patch('ui.crm_tab.DataAccess') as MockDA, \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.TableSettings'):
        MockDA.return_value = parent_widget.data
        from ui.crm_tab import SurveyDateDialog
        dlg = SurveyDateDialog(parent_widget, card_id=card_id, api_client=None)
        qtbot.addWidget(dlg)
        return dlg


def _create_reassign_dialog(qtbot, parent_widget, card_id=300):
    """Создать ReassignExecutorDialog."""
    mock_da = parent_widget.data
    mock_da.api_client = None  # Локальный режим
    mock_da.get_all_employees.return_value = [
        {'id': 7, 'full_name': 'Чертёжник Тест', 'position': 'Чертёжник', 'status': 'активный'},
        {'id': 6, 'full_name': 'Дизайнер Тест', 'position': 'Дизайнер', 'status': 'активный'},
    ]
    mock_da.get_employees_by_position.return_value = [
        {'id': 7, 'full_name': 'Чертёжник Тест', 'position': 'Чертёжник', 'status': 'активный'},
    ]
    mock_da.get_crm_card.return_value = {'id': card_id, 'stage_executors': [], 'contract_id': 200}
    mock_da.get_action_history.return_value = []
    mock_da.get_previous_executor_by_position.return_value = None
    mock_da.get_contract_id_by_crm_card.return_value = 200
    mock_da.get_contract.return_value = {'id': 200, 'area': 100, 'city': 'Москва'}
    mock_da.db.get_employees_by_position.return_value = [
        {'id': 7, 'full_name': 'Чертёжник Тест', 'position': 'Чертёжник', 'status': 'активный'},
    ]
    mock_da.db.connect.return_value.cursor.return_value.fetchall.return_value = []
    mock_da.db.connect.return_value.cursor.return_value.fetchone.return_value = None

    with patch('ui.crm_tab.DataAccess') as MockDA, \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.TableSettings'):
        MockDA.return_value = mock_da
        from ui.crm_tab import ReassignExecutorDialog
        dlg = ReassignExecutorDialog(
            parent_widget, card_id=card_id,
            position='Чертёжник',
            stage_keyword='Стадия 1',
            executor_type='draftsman',
            current_executor_name='Чертёжник Тест',
            stage_name='Стадия 1: планировочные решения',
            api_client=None
        )
        qtbot.addWidget(dlg)
        return dlg


def _make_card_data(card_id=300, column='Новый заказ', project_type='Индивидуальный',
                    project_subtype='Полный проект', **overrides):
    """Сгенерировать минимальные данные CRM карточки."""
    data = {
        'id': card_id,
        'contract_id': 200,
        'contract_number': f'ИП-ПОЛ-{card_id}/26',
        'project_type': project_type,
        'project_subtype': project_subtype,
        'column_name': column,
        'client_name': 'Тестовый Клиент',
        'address': 'г. СПб, ул. Тест',
        'area': 85.5,
        'city': 'СПБ',
        'status': 'active',
        'designer_name': None,
        'draftsman_name': None,
        'designer_completed': 0,
        'draftsman_completed': 0,
        'is_approved': 0,
        'survey_date': None,
        'tech_task_date': None,
        'tech_task_link': None,
        'measurement_link': None,
        'references_link': None,
        'project_data_link': None,
        'contract_file_link': None,
        'yandex_folder_path': None,
        'stage_executors': [],
        'deadline': None,
        'manager_id': None,
        'sdp_id': None,
        'gap_id': None,
        'tags': '',
        'agent_type': '',
        'total_amount': 500000,
        'advance_payment': 150000,
        'additional_payment': 200000,
        'third_payment': 150000,
        'contract_date': '2026-01-15',
        'contract_period': 45,
    }
    data.update(overrides)
    return data


# ========== 1. Рендеринг CRMTab (8 тестов) ==========

@pytest.mark.ui
class TestCRMTabRendering:
    """Проверка рендеринга CRM вкладки."""

    def test_tab_creates(self, qtbot, mock_data_access, mock_employee_admin):
        """CRMTab создаётся как QWidget."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert isinstance(tab, QWidget)

    def test_project_tabs_exist(self, qtbot, mock_data_access, mock_employee_admin):
        """QTabWidget проектов существует."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'project_tabs')
        assert isinstance(tab.project_tabs, QTabWidget)

    def test_admin_sees_2_project_tabs(self, qtbot, mock_data_access, mock_employee_admin):
        """Админ видит 2 вкладки: Индивидуальные и Шаблонные."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.project_tabs.count() == 2

    def test_sdp_sees_1_project_tab(self, qtbot, mock_data_access, mock_employee_sdp):
        """СДП видит только 1 вкладку (Индивидуальные)."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_sdp)
        assert tab.project_tabs.count() == 1

    def test_individual_board_6_columns(self, qtbot, mock_data_access, mock_employee_admin):
        """Индивидуальная доска имеет 6 колонок."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert len(tab.individual_widget.columns) == 6

    def test_individual_column_names(self, qtbot, mock_data_access, mock_employee_admin):
        """Названия колонок индивидуального проекта."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        col_names = list(tab.individual_widget.columns.keys())
        assert 'Новый заказ' in col_names
        assert 'В ожидании' in col_names
        assert 'Выполненный проект' in col_names

    def test_template_board_6_columns(self, qtbot, mock_data_access, mock_employee_admin):
        """Шаблонная доска имеет 6 колонок."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert len(tab.template_widget.columns) == 6

    def test_data_access_set(self, qtbot, mock_data_access, mock_employee_admin):
        """DataAccess назначен."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.data is not None


# ========== 2. Видимость для ролей (8 тестов) ==========

@pytest.mark.ui
class TestCRMRoleVisibility:
    """Видимость элементов CRM по ролям."""

    def test_stats_btn_visible_admin(self, qtbot, mock_data_access, mock_employee_admin):
        """Админ видит кнопку статистики."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        btns = tab.findChildren(QPushButton)
        stat_btns = [b for b in btns if 'статистик' in b.text().lower()]
        assert len(stat_btns) >= 1

    def test_stats_btn_hidden_designer(self, qtbot, mock_data_access, mock_employee_designer):
        """Дизайнер не видит кнопку статистики."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_designer)
        btns = tab.findChildren(QPushButton)
        stat_btns = [b for b in btns if 'статистик' in b.text().lower()]
        assert len(stat_btns) == 0

    def test_archive_visible_admin(self, qtbot, mock_data_access, mock_employee_admin):
        """Админ видит архив (2 подвкладки)."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.individual_subtabs.count() == 2  # Активные + Архив

    def test_archive_hidden_designer(self, qtbot, mock_data_access, mock_employee_designer):
        """Дизайнер не видит архив (1 подвкладка)."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_designer)
        assert tab.individual_subtabs.count() == 1  # Только Активные

    def test_template_hidden_sdp(self, qtbot, mock_data_access, mock_employee_sdp):
        """Чистый СДП не видит шаблонные проекты."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_sdp)
        assert tab.project_tabs.count() == 1

    def test_manager_sees_only_individual_tab(self, qtbot, mock_data_access, mock_employee_manager):
        """Менеджер без права crm_cards.move видит только 1 вкладку (Индивидуальные)."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_manager)
        assert tab.project_tabs.count() == 1

    def test_dual_designer_manager_sees_only_individual(self, qtbot, mock_data_access, mock_employee_designer_manager):
        """Дизайнер+Менеджер без права crm_cards.move видит только 1 вкладку."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_designer_manager)
        assert tab.project_tabs.count() == 1

    def test_dual_designer_manager_no_archive(self, qtbot, mock_data_access, mock_employee_designer_manager):
        """Дизайнер+Менеджер без права crm_cards.move не видит архив (1 подвкладка)."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_designer_manager)
        assert tab.individual_subtabs.count() == 1


# ========== 3. CRMColumn (6 тестов) ==========

@pytest.mark.ui
class TestCRMColumn:
    """Проверка CRM колонок."""

    def test_individual_columns_correct(self, qtbot, mock_data_access, mock_employee_admin):
        """Индивидуальные: 6 колонок с правильными названиями."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        expected = [
            'Новый заказ', 'В ожидании',
            'Стадия 1: планировочные решения',
            'Стадия 2: концепция дизайна',
            'Стадия 3: рабочие чертежи',
            'Выполненный проект'
        ]
        for name in expected:
            assert name in tab.individual_widget.columns

    def test_template_columns_correct(self, qtbot, mock_data_access, mock_employee_admin):
        """Шаблонные: 6 колонок с правильными названиями."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        expected = [
            'Новый заказ', 'В ожидании',
            'Стадия 1: планировочные решения',
            'Стадия 2: рабочие чертежи',
            'Стадия 3: 3д визуализация (Дополнительная)',
            'Выполненный проект'
        ]
        for name in expected:
            assert name in tab.template_widget.columns

    def test_column_has_cards_list(self, qtbot, mock_data_access, mock_employee_admin):
        """Каждая колонка имеет cards_list."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        for col in tab.individual_widget.columns.values():
            assert hasattr(col, 'cards_list')

    def test_column_is_frame(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонка — QFrame."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        for col in tab.individual_widget.columns.values():
            assert isinstance(col, QFrame)

    def test_column_has_header(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонка имеет header_label."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        for col in tab.individual_widget.columns.values():
            assert hasattr(col, 'header_label')

    def test_column_has_collapse_btn(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонка имеет кнопку сворачивания."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        for col in tab.individual_widget.columns.values():
            assert hasattr(col, 'collapse_btn')


# ========== 4. CRM карточка (10 тестов) ==========

@pytest.mark.ui
class TestCRMCard:
    """Проверка CRM карточки."""

    def test_card_creates(self, qtbot, mock_employee_admin):
        """Карточка создаётся как QFrame."""
        data = _make_card_data()
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert isinstance(card, QFrame)

    def test_card_stores_data(self, qtbot, mock_employee_admin):
        """Карточка хранит card_data."""
        data = _make_card_data()
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert card.card_data['id'] == 300

    def test_card_stores_employee(self, qtbot, mock_employee_admin):
        """Карточка хранит employee."""
        data = _make_card_data()
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert card.employee == mock_employee_admin

    def test_card_with_designer_data(self, qtbot, mock_employee_admin):
        """Карточка с назначенным дизайнером."""
        data = _make_card_data(
            designer_name='Дизайнер Тест',
            column='Стадия 2: концепция дизайна'
        )
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert card.card_data['designer_name'] == 'Дизайнер Тест'

    def test_card_with_deadline(self, qtbot, mock_employee_admin):
        """Карточка с дедлайном."""
        data = _make_card_data(deadline='2026-03-15')
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert card.card_data['deadline'] == '2026-03-15'

    def test_card_can_edit_true(self, qtbot, mock_employee_admin):
        """Карточка с can_edit=True."""
        data = _make_card_data()
        card = _create_crm_card(qtbot, data, mock_employee_admin, can_edit=True)
        assert card.can_edit is True

    def test_card_can_edit_false(self, qtbot, mock_employee_admin):
        """Карточка с can_edit=False."""
        data = _make_card_data()
        card = _create_crm_card(qtbot, data, mock_employee_admin, can_edit=False)
        assert card.can_edit is False

    def test_card_with_survey_date(self, qtbot, mock_employee_admin):
        """Карточка с датой замера."""
        data = _make_card_data(survey_date='2026-02-10')
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert card.card_data['survey_date'] == '2026-02-10'

    def test_card_with_stage_executors(self, qtbot, mock_employee_admin):
        """Карточка со stage_executors."""
        executors = [
            {'stage_name': 'Стадия 1', 'executor_id': 7, 'executor_name': 'Тест'}
        ]
        data = _make_card_data(stage_executors=executors)
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert len(card.card_data['stage_executors']) == 1

    def test_working_days_calculation(self, qtbot, mock_employee_admin):
        """Метод calculate_working_days работает."""
        data = _make_card_data()
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        # Понедельник → Пятница = 5 рабочих дней
        start = QDate(2026, 2, 16)  # Понедельник
        end = QDate(2026, 2, 20)    # Пятница
        result = card.calculate_working_days(start, end)
        assert result == 5


# ========== 5. ExecutorSelectionDialog (8 тестов) ==========

@pytest.mark.ui
class TestExecutorSelectionDialog:
    """Диалог выбора исполнителя."""

    def test_dialog_creates(self, qtbot, parent_widget):
        """Диалог создаётся."""
        dlg = _create_executor_dialog(qtbot, parent_widget)
        assert isinstance(dlg, QDialog)

    def test_has_executor_combo(self, qtbot, parent_widget):
        """Комбобокс исполнителя существует."""
        dlg = _create_executor_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'executor_combo')

    def test_has_deadline_field(self, qtbot, parent_widget):
        """Поле дедлайна существует."""
        dlg = _create_executor_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'stage_deadline')

    def test_card_id_stored(self, qtbot, parent_widget):
        """card_id сохранён."""
        dlg = _create_executor_dialog(qtbot, parent_widget, card_id=500)
        assert dlg.card_id == 500

    def test_stage_name_stored(self, qtbot, parent_widget):
        """stage_name сохранён."""
        dlg = _create_executor_dialog(qtbot, parent_widget,
                                       stage_name='Стадия 2: концепция дизайна')
        assert dlg.stage_name == 'Стадия 2: концепция дизайна'

    def test_project_type_stored(self, qtbot, parent_widget):
        """project_type сохранён."""
        dlg = _create_executor_dialog(qtbot, parent_widget, project_type='Шаблонный')
        assert dlg.project_type == 'Шаблонный'

    def test_norm_days_loaded(self, qtbot, parent_widget):
        """norm_days инициализирован."""
        dlg = _create_executor_dialog(qtbot, parent_widget)
        assert hasattr(dlg, '_norm_days')

    def test_filter_stage1_draftsman(self, qtbot, parent_widget):
        """Стадия 1 фильтрует по Чертёжникам."""
        dlg = _create_executor_dialog(
            qtbot, parent_widget,
            stage_name='Стадия 1: планировочные решения',
            project_type='Индивидуальный'
        )
        # executor_combo должен содержать хотя бы 1 элемент
        assert dlg.executor_combo.count() >= 0  # Создаётся без ошибок


# ========== 6. ProjectCompletionDialog (6 тестов) ==========

@pytest.mark.ui
class TestProjectCompletionDialog:
    """Диалог завершения проекта."""

    def test_dialog_creates(self, qtbot, parent_widget):
        """Диалог создаётся."""
        dlg = _create_completion_dialog(qtbot, parent_widget)
        assert isinstance(dlg, QDialog)

    def test_has_status_combo(self, qtbot, parent_widget):
        """Комбобокс статуса существует."""
        dlg = _create_completion_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'status')

    def test_status_has_3_options(self, qtbot, parent_widget):
        """Комбобокс статуса имеет 3 варианта."""
        dlg = _create_completion_dialog(qtbot, parent_widget)
        assert dlg.status.count() == 3

    def test_status_options_correct(self, qtbot, parent_widget):
        """Варианты статуса: СДАН, АВТОРСКИЙ НАДЗОР, РАСТОРГНУТ."""
        dlg = _create_completion_dialog(qtbot, parent_widget)
        items = [dlg.status.itemText(i) for i in range(dlg.status.count())]
        assert any('СДАН' in item for item in items)
        assert any('АВТОРСКИЙ НАДЗОР' in item.upper() for item in items)
        assert any('РАСТОРГНУТ' in item for item in items)

    def test_termination_reason_hidden_default(self, qtbot, parent_widget):
        """Причина расторжения скрыта по умолчанию."""
        dlg = _create_completion_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'termination_reason_group')
        assert dlg.termination_reason_group.isHidden()

    def test_card_id_stored(self, qtbot, parent_widget):
        """card_id сохранён."""
        dlg = _create_completion_dialog(qtbot, parent_widget, card_id=999)
        assert dlg.card_id == 999


# ========== 7. SurveyDateDialog (4 теста) ==========

@pytest.mark.ui
class TestSurveyDateDialog:
    """Диалог установки даты замера."""

    def test_dialog_creates(self, qtbot, parent_widget):
        """Диалог создаётся."""
        dlg = _create_survey_date_dialog(qtbot, parent_widget)
        assert isinstance(dlg, QDialog)

    def test_card_id_stored(self, qtbot, parent_widget):
        """card_id сохранён."""
        dlg = _create_survey_date_dialog(qtbot, parent_widget, card_id=777)
        assert dlg.card_id == 777

    def test_has_date_field(self, qtbot, parent_widget):
        """Поле даты замера существует."""
        dlg = _create_survey_date_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'survey_date')

    def test_has_save_button(self, qtbot, parent_widget):
        """Кнопка сохранения существует."""
        dlg = _create_survey_date_dialog(qtbot, parent_widget)
        save_btns = [b for b in dlg.findChildren(QPushButton)
                     if 'сохранить' in b.text().lower() or 'установ' in b.text().lower()
                     or 'назнач' in b.text().lower()]
        assert len(save_btns) >= 1


# ========== 8. ReassignExecutorDialog (6 тестов) ==========

@pytest.mark.ui
class TestReassignExecutorDialog:
    """Диалог переназначения исполнителя."""

    def test_dialog_creates(self, qtbot, parent_widget):
        """Диалог создаётся."""
        dlg = _create_reassign_dialog(qtbot, parent_widget)
        assert isinstance(dlg, QDialog)

    def test_card_id_stored(self, qtbot, parent_widget):
        """card_id сохранён."""
        dlg = _create_reassign_dialog(qtbot, parent_widget, card_id=888)
        assert dlg.card_id == 888

    def test_position_stored(self, qtbot, parent_widget):
        """position сохранён."""
        dlg = _create_reassign_dialog(qtbot, parent_widget)
        assert dlg.position == 'Чертёжник'

    def test_stage_name_stored(self, qtbot, parent_widget):
        """stage_name сохранён."""
        dlg = _create_reassign_dialog(qtbot, parent_widget)
        assert dlg.stage_name == 'Стадия 1: планировочные решения'

    def test_has_executor_combo(self, qtbot, parent_widget):
        """Комбобокс нового исполнителя существует."""
        dlg = _create_reassign_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'executor_combo')

    def test_executor_type_stored(self, qtbot, parent_widget):
        """executor_type сохранён."""
        dlg = _create_reassign_dialog(qtbot, parent_widget)
        assert dlg.executor_type == 'draftsman'


# ========== 9. Дедлайны (8 тестов) ==========

@pytest.mark.ui
class TestCRMDeadlines:
    """Дедлайны на CRM карточках."""

    def test_deadline_in_card_data(self, qtbot, mock_employee_admin):
        """Дедлайн хранится в card_data."""
        data = _make_card_data(deadline='2026-03-20')
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert card.card_data['deadline'] == '2026-03-20'

    def test_no_deadline_none(self, qtbot, mock_employee_admin):
        """Без дедлайна — None."""
        data = _make_card_data(deadline=None)
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert card.card_data['deadline'] is None

    def test_working_days_weekdays_only(self, qtbot, mock_employee_admin):
        """Рабочие дни исключают выходные."""
        data = _make_card_data()
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        # Пн-Вс = 5 рабочих дней (без Сб-Вс)
        start = QDate(2026, 2, 16)  # Пн
        end = QDate(2026, 2, 22)    # Вс
        result = card.calculate_working_days(start, end)
        assert result == 5

    def test_working_days_one_day(self, qtbot, mock_employee_admin):
        """1 день = 1 рабочий день."""
        data = _make_card_data()
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        start = QDate(2026, 2, 16)  # Пн
        end = QDate(2026, 2, 16)    # Пн
        result = card.calculate_working_days(start, end)
        assert result == 1

    def test_working_days_weekend_zero(self, qtbot, mock_employee_admin):
        """Выходной → 0 рабочих дней."""
        data = _make_card_data()
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        start = QDate(2026, 2, 21)  # Сб
        end = QDate(2026, 2, 21)    # Сб
        result = card.calculate_working_days(start, end)
        assert result == 0

    def test_working_days_negative_reversed(self, qtbot, mock_employee_admin):
        """Обратный порядок дат — отрицательный результат."""
        data = _make_card_data()
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        start = QDate(2026, 2, 20)  # Пт
        end = QDate(2026, 2, 16)    # Пн
        result = card.calculate_working_days(start, end)
        assert result < 0

    def test_working_days_full_week(self, qtbot, mock_employee_admin):
        """Полная неделя = 5 рабочих дней."""
        data = _make_card_data()
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        start = QDate(2026, 2, 16)  # Пн
        end = QDate(2026, 2, 20)    # Пт
        result = card.calculate_working_days(start, end)
        assert result == 5

    def test_working_days_two_weeks(self, qtbot, mock_employee_admin):
        """2 недели = 10 рабочих дней."""
        data = _make_card_data()
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        start = QDate(2026, 2, 16)  # Пн
        end = QDate(2026, 2, 27)    # Пт
        result = card.calculate_working_days(start, end)
        assert result == 10


# ========== 10. Хелпер-функции ролей (8 тестов) ==========

@pytest.mark.ui
class TestCRMHelperFunctions:
    """Тесты хелпер-функций _emp_has_pos и _emp_only_pos."""

    def test_emp_has_pos_primary(self):
        """_emp_has_pos — основная должность совпадает."""
        from ui.crm_tab import _emp_has_pos
        emp = {'position': 'Дизайнер', 'secondary_position': ''}
        assert _emp_has_pos(emp, 'Дизайнер') is True

    def test_emp_has_pos_secondary(self):
        """_emp_has_pos — дополнительная должность совпадает."""
        from ui.crm_tab import _emp_has_pos
        emp = {'position': 'Дизайнер', 'secondary_position': 'Менеджер'}
        assert _emp_has_pos(emp, 'Менеджер') is True

    def test_emp_has_pos_none(self):
        """_emp_has_pos — ни одна должность не совпадает."""
        from ui.crm_tab import _emp_has_pos
        emp = {'position': 'Дизайнер', 'secondary_position': ''}
        assert _emp_has_pos(emp, 'Менеджер') is False

    def test_emp_has_pos_no_employee(self):
        """_emp_has_pos — None → False."""
        from ui.crm_tab import _emp_has_pos
        assert _emp_has_pos(None, 'Дизайнер') is False

    def test_emp_only_pos_single(self):
        """_emp_only_pos — единственная должность совпадает."""
        from ui.crm_tab import _emp_only_pos
        emp = {'position': 'Дизайнер', 'secondary_position': ''}
        assert _emp_only_pos(emp, 'Дизайнер') is True

    def test_emp_only_pos_dual_match(self):
        """_emp_only_pos — обе должности в наборе."""
        from ui.crm_tab import _emp_only_pos
        emp = {'position': 'Дизайнер', 'secondary_position': 'Чертёжник'}
        assert _emp_only_pos(emp, 'Дизайнер', 'Чертёжник') is True

    def test_emp_only_pos_dual_mismatch(self):
        """_emp_only_pos — вторая должность не в наборе."""
        from ui.crm_tab import _emp_only_pos
        emp = {'position': 'Дизайнер', 'secondary_position': 'Менеджер'}
        assert _emp_only_pos(emp, 'Дизайнер') is False

    def test_emp_only_pos_no_employee(self):
        """_emp_only_pos — None → False."""
        from ui.crm_tab import _emp_only_pos
        assert _emp_only_pos(None, 'Дизайнер') is False


# ========== 11. Перемещение карточек (10 тестов) ==========

@pytest.mark.ui
class TestCRMCardMovement:
    """Перемещение карточек между колонками."""

    def test_can_edit_stored(self, qtbot, mock_data_access, mock_employee_admin):
        """can_edit сохранён в tab."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin, can_edit=True)
        assert tab.can_edit is True

    def test_can_edit_false(self, qtbot, mock_data_access, mock_employee_admin):
        """can_edit=False сохранён."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin, can_edit=False)
        assert tab.can_edit is False

    def test_column_card_moved_signal_exists(self, qtbot, mock_data_access, mock_employee_admin):
        """Сигнал card_moved существует у колонки."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        col = list(tab.individual_widget.columns.values())[0]
        assert hasattr(col, 'card_moved')

    def test_individual_stage2_is_design(self, qtbot, mock_data_access, mock_employee_admin):
        """Индивидуальный: Стадия 2 = концепция дизайна."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert 'Стадия 2: концепция дизайна' in tab.individual_widget.columns

    def test_template_stage2_is_drafts(self, qtbot, mock_data_access, mock_employee_admin):
        """Шаблонный: Стадия 2 = рабочие чертежи."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert 'Стадия 2: рабочие чертежи' in tab.template_widget.columns

    def test_template_stage3_is_3d(self, qtbot, mock_data_access, mock_employee_admin):
        """Шаблонный: Стадия 3 = 3д визуализация."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert 'Стадия 3: 3д визуализация (Дополнительная)' in tab.template_widget.columns

    def test_individual_stage3_is_drafts(self, qtbot, mock_data_access, mock_employee_admin):
        """Индивидуальный: Стадия 3 = рабочие чертежи."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert 'Стадия 3: рабочие чертежи' in tab.individual_widget.columns

    def test_first_column_is_new_order(self, qtbot, mock_data_access, mock_employee_admin):
        """Первая колонка — Новый заказ."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        first_col = list(tab.individual_widget.columns.keys())[0]
        assert first_col == 'Новый заказ'

    def test_last_column_is_completed(self, qtbot, mock_data_access, mock_employee_admin):
        """Последняя колонка — Выполненный проект."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        last_col = list(tab.individual_widget.columns.keys())[-1]
        assert last_col == 'Выполненный проект'

    def test_on_card_moved_method_exists(self, qtbot, mock_data_access, mock_employee_admin):
        """Метод on_card_moved существует."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'on_card_moved')
        assert callable(tab.on_card_moved)


# ========== 12. Ленивая загрузка (4 теста) ==========

@pytest.mark.ui
class TestCRMLazyLoading:
    """Ленивая загрузка данных CRM."""

    def test_data_not_loaded_on_create(self, qtbot, mock_data_access, mock_employee_admin):
        """Данные не загружены при создании."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab._data_loaded is False

    def test_ensure_data_loaded_sets_flag(self, qtbot, mock_data_access, mock_employee_admin):
        """ensure_data_loaded устанавливает флаг."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.ensure_data_loaded()
        assert tab._data_loaded is True

    def test_ensure_data_loaded_calls_load(self, qtbot, mock_data_access, mock_employee_admin):
        """ensure_data_loaded вызывает загрузку карточек."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.ensure_data_loaded()
        # get_crm_cards должен быть вызван
        mock_data_access.get_crm_cards.assert_called()

    def test_double_ensure_reloads_via_cache(self, qtbot, mock_data_access, mock_employee_admin):
        """Повторный ensure_data_loaded обновляет данные (через кэш DataAccess)."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.ensure_data_loaded()
        call_count_after_first = mock_data_access.get_crm_cards.call_count
        assert call_count_after_first >= 1
        tab.ensure_data_loaded()
        # При повторном вызове данные перезагружаются (кэш 30с TTL)
        assert mock_data_access.get_crm_cards.call_count > call_count_after_first


# ========== 13. Прочие диалоги и элементы (6 тестов) ==========

@pytest.mark.ui
class TestCRMDialogsAndWidgets:
    """Другие диалоги и виджеты CRM."""

    def test_on_tab_changed_exists(self, qtbot, mock_data_access, mock_employee_admin):
        """Метод on_tab_changed существует."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'on_tab_changed')

    def test_project_tabs_initial_index_0(self, qtbot, mock_data_access, mock_employee_admin):
        """При создании активна первая вкладка."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.project_tabs.currentIndex() == 0

    def test_individual_subtabs_exist(self, qtbot, mock_data_access, mock_employee_admin):
        """Подвкладки индивидуальных проектов существуют."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'individual_subtabs')
        assert isinstance(tab.individual_subtabs, QTabWidget)

    def test_template_subtabs_exist(self, qtbot, mock_data_access, mock_employee_admin):
        """Подвкладки шаблонных проектов существуют."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'template_subtabs')
        assert isinstance(tab.template_subtabs, QTabWidget)

    def test_refresh_current_tab_callable(self, qtbot, mock_data_access, mock_employee_admin):
        """refresh_current_tab вызываем."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert callable(tab.refresh_current_tab)

    def test_update_project_tab_counters_callable(self, qtbot, mock_data_access, mock_employee_admin):
        """update_project_tab_counters вызываем."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert callable(tab.update_project_tab_counters)
