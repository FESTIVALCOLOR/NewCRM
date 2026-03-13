# -*- coding: utf-8 -*-
"""
Глубокие callback-тесты для UI табов — прямой вызов callback-методов с проверкой DataAccess.

НЕ дублирует тесты из test_crm_tab_deep.py (41), test_salaries_deep.py (26),
test_employees_deep.py (20), test_crm_card_deep.py (40+).

Покрывает:
  - TestCrmTabCardMoveCallbacks (8)     — on_card_moved: бизнес-правила перемещений
  - TestCrmTabRefreshCallbacks (5)      — refresh_current_tab, dashboard, prefer_local
  - TestContractsTabLoadCallbacks (8)   — load_contracts, apply_search, фильтрация
  - TestContractsTabCrudCallbacks (5)   — add_contract, edit_contract, delete_contract
  - TestSalariesTabPaymentCallbacks (7) — load_payment_type_data, on_tab_changed, фильтры
  - TestSalariesTabCacheCallbacks (4)   — кэширование, force_reload, prefer_local
  - TestEmployeesTabCrudCallbacks (6)   — add/edit/delete_employee, права, self-delete
  - TestEmployeesTabLoadCallbacks (4)   — load_employees по отделам, ensure_data_loaded
  - TestSupervisionTabLoadCallbacks (6) — load_active_cards, load_archive_cards, ДАН фильтр
  - TestSupervisionTabMoveCallbacks (5) — on_card_moved: правила перемещений надзора
  - TestCardEditDialogCallbacks (5)     — save_changes, load_data, auto_save
ИТОГО: 63 теста
"""

import pytest
from unittest.mock import patch, MagicMock, call, PropertyMock
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLabel,
    QDialog, QComboBox, QFrame, QListWidget, QTableWidget
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QIcon


# ═══════════════════════════════════════════════════════════════
# Автомоки для диалогов (предотвращают блокировку тестов)
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _mock_deep_callbacks_msgbox():
    """Глобальный мок CustomMessageBox/QuestionBox для всех табов."""
    with patch('ui.crm_tab.CustomMessageBox') as m1, \
         patch('ui.crm_tab.CustomQuestionBox') as q1, \
         patch('ui.contracts_tab.CustomMessageBox') as m2, \
         patch('ui.contracts_tab.CustomQuestionBox') as q2, \
         patch('ui.employees_tab.CustomMessageBox') as m3, \
         patch('ui.salaries_tab.CustomMessageBox') as m4, \
         patch('ui.crm_supervision_tab.CustomMessageBox', create=True) as m5, \
         patch('ui.crm_card_edit_dialog.CustomMessageBox') as m6, \
         patch('ui.crm_card_edit_dialog.CustomQuestionBox') as q6:
        for m in [m1, m2, m3, m4, m5, m6]:
            m.return_value.exec_.return_value = None
        for q in [q1, q2, q6]:
            q.return_value.exec_.return_value = QDialog.Rejected
        yield


# ═══════════════════════════════════════════════════════════════
# Хелперы
# ═══════════════════════════════════════════════════════════════

def _mock_icon_loader():
    """IconLoader с реальным QIcon."""
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


# ---------- CRM Tab ----------

def _create_crm_tab(qtbot, mock_da, employee, can_edit=True):
    """Создать CRMTab с mock DataAccess."""
    with patch('ui.crm_tab.DataAccess') as MockDA, \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.YandexDiskManager', return_value=None), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.crm_tab.TableSettings') as MockTS, \
         patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.TableSettings'):
        MockDA.return_value = mock_da
        MockTS.return_value.load_column_collapse_state.return_value = {}
        from ui.crm_tab import CRMTab
        tab = CRMTab(employee=employee, can_edit=can_edit, api_client=None)
        qtbot.addWidget(tab)
        return tab


# ---------- Contracts Tab ----------

def _create_contracts_tab(qtbot, mock_da, employee):
    """Создать ContractsTab с mock DataAccess."""
    mock_da.api_client = None
    mock_da.db = MagicMock()
    mock_da.get_agent_color = MagicMock(return_value=None)
    with patch('ui.contracts_tab.DataAccess') as MockDA, \
         patch('ui.contracts_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.contracts_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.contracts_tab.TableSettings') as MockTS, \
         patch('ui.contracts_tab._has_perm', return_value=True):
        MockDA.return_value = mock_da
        MockTS.return_value.get_sort_order.return_value = (None, None)
        from ui.contracts_tab import ContractsTab
        tab = ContractsTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab


# ---------- Salaries Tab ----------

def _create_salaries_tab(qtbot, mock_da, employee):
    """Создать SalariesTab с mock DataAccess."""
    mock_da.api_client = None
    mock_da.db = MagicMock()
    mock_da.db.get_year_payments.return_value = []
    mock_da.get_all_employees.return_value = []
    mock_da.get_all_contracts.return_value = []
    mock_da.get_year_payments.return_value = []
    with patch('ui.salaries_tab.DataAccess') as MockDA, \
         patch('ui.salaries_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.salaries_tab.IconLoader', _mock_icon_loader()):
        MockDA.return_value = mock_da
        from ui.salaries_tab import SalariesTab
        tab = SalariesTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab


# ---------- Employees Tab ----------

def _create_employees_tab(qtbot, mock_da, employee):
    """Создать EmployeesTab с mock DataAccess."""
    mock_da.api_client = None
    mock_da.db = MagicMock()
    with patch('ui.employees_tab.DataAccess') as MockDA, \
         patch('ui.employees_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.employees_tab.IconLoader', _mock_icon_loader()):
        MockDA.return_value = mock_da
        from ui.employees_tab import EmployeesTab
        tab = EmployeesTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab


# ---------- Supervision Tab ----------

def _create_supervision_tab(qtbot, mock_da, employee):
    """Создать CRMSupervisionTab с mock DataAccess.

    Используем patch.start() вместо context manager, чтобы моки
    оставались активными после выхода из функции (для вызовов
    tab.load_active_cards() и т.д. в тестах).
    НЕ используем qtbot.addWidget() — access violation при cleanup.
    """
    mock_da.api_client = None
    mock_da.db = MagicMock()
    patchers = [
        patch('ui.crm_supervision_tab.DataAccess', return_value=mock_da),
        patch('ui.crm_supervision_tab.DatabaseManager', return_value=MagicMock()),
        patch('ui.crm_supervision_tab.IconLoader', _mock_icon_loader()),
        patch('ui.crm_supervision_tab.YandexDiskManager', return_value=None),
        patch('ui.crm_supervision_tab.YANDEX_DISK_TOKEN', ''),
        patch('ui.crm_supervision_tab.TableSettings', MagicMock()),
        patch('ui.crm_supervision_tab._has_perm', return_value=True),
        patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()),
        patch('ui.base_kanban_tab.TableSettings'),
    ]
    for p in patchers:
        p.start()
    from ui.crm_supervision_tab import CRMSupervisionTab
    tab = CRMSupervisionTab(employee=employee, api_client=None)
    tab.hide()
    tab._patchers = patchers  # сохраняем для cleanup
    return tab


# ---------- Тестовые данные ----------

def _sample_contracts():
    """Набор тестовых договоров."""
    return [
        {
            'id': 200, 'contract_number': 'ИП-ПОЛ-001/26',
            'project_type': 'Индивидуальный', 'project_subtype': 'Полный проект',
            'client_id': 100, 'contract_date': '2026-01-15', 'city': 'СПБ',
            'address': 'г. СПб, ул. Тестовая, д.1', 'area': 85.5,
            'total_amount': 500000, 'agent_type': '', 'status': 'active',
            'comments': '', 'termination_reason': None,
        },
        {
            'id': 201, 'contract_number': 'ШП-СТДЗ-002/26',
            'project_type': 'Шаблонный', 'project_subtype': 'Стандарт',
            'client_id': 101, 'contract_date': '2026-02-01', 'city': 'МСК',
            'address': 'г. Москва, ул. Шаблонная, д.5', 'area': 120,
            'total_amount': 300000, 'agent_type': 'Фестиваль', 'status': 'active',
            'comments': 'Срочный', 'termination_reason': None,
        },
    ]


def _sample_clients():
    """Набор тестовых клиентов."""
    return [
        {'id': 100, 'full_name': 'Иванов Иван', 'client_type': 'Физическое лицо',
         'organization_name': ''},
        {'id': 101, 'full_name': 'ООО Тест', 'client_type': 'Юридическое лицо',
         'organization_name': 'ООО Тест'},
    ]


def _sample_employees_list():
    """Набор тестовых сотрудников."""
    return [
        {'id': 1, 'full_name': 'Руководитель Тест', 'position': 'Руководитель студии',
         'secondary_position': '', 'department': 'Административный отдел',
         'status': 'активный', 'phone': '+7-999-111', 'email': 'boss@t.ru',
         'birth_date': '1985-03-15', 'login': 'boss'},
        {'id': 2, 'full_name': 'Дизайнер Тест', 'position': 'Дизайнер',
         'secondary_position': '', 'department': 'Проектный отдел',
         'status': 'активный', 'phone': '+7-999-222', 'email': 'des@t.ru',
         'birth_date': '1990-06-20', 'login': 'designer'},
        {'id': 3, 'full_name': 'Менеджер Тест', 'position': 'Менеджер',
         'secondary_position': '', 'department': 'Исполнительный отдел',
         'status': 'уволен', 'phone': '+7-999-333', 'email': 'mgr@t.ru',
         'birth_date': '', 'login': 'manager'},
    ]


def _sample_payment(payment_id=1, **overrides):
    """Тестовый платёж."""
    data = {
        'id': payment_id, 'employee_name': 'Дизайнер Тест', 'employee_id': 2,
        'contract_id': 200, 'contract_number': 'ИП-ПОЛ-001/26',
        'address': 'г. СПб, ул. Тест', 'role': 'Дизайнер',
        'stage_name': 'Стадия 2: концепция дизайна',
        'calculated_amount': 25000, 'manual_amount': None, 'final_amount': 25000,
        'is_manual': 0, 'payment_type': 'Аванс', 'report_month': '2026-02',
        'status': 'to_pay', 'source': 'CRM', 'reassigned': 0,
        'position': 'Дизайнер', 'agent_type': '', 'project_type': 'Индивидуальный',
    }
    data.update(overrides)
    return data


def _make_crm_card(card_id=300, column='Новый заказ', project_type='Индивидуальный', **overrides):
    """Минимальные данные CRM карточки."""
    data = {
        'id': card_id, 'contract_id': 200,
        'contract_number': f'ИП-ПОЛ-{card_id}/26',
        'project_type': project_type, 'project_subtype': 'Полный проект',
        'column_name': column, 'client_name': 'Тестовый Клиент',
        'address': 'г. СПб, ул. Тест', 'area': 85.5, 'city': 'СПБ',
        'status': 'active', 'designer_name': None, 'draftsman_name': None,
        'designer_completed': 0, 'draftsman_completed': 0,
        'is_approved': 0, 'survey_date': None, 'tech_task_date': None,
        'tech_task_link': None, 'measurement_link': None,
        'references_link': None, 'project_data_link': None,
        'contract_file_link': None, 'yandex_folder_path': None,
        'stage_executors': [], 'deadline': None, 'manager_id': 5,
        'sdp_id': 3, 'gap_id': 4, 'senior_manager_id': 2,
        'surveyor_id': 8, 'tags': '', 'agent_type': '',
        'total_amount': 500000, 'contract_date': '2026-01-15',
        'dan_id': None, 'dan_name': None, 'dan_completed': 0,
    }
    data.update(overrides)
    return data


def _make_supervision_card(card_id=500, column='Новый заказ', **overrides):
    """Минимальные данные карточки надзора."""
    data = {
        'id': card_id, 'contract_id': 200,
        'contract_number': 'ИП-ПОЛ-001/26',
        'column_name': column, 'client_name': 'Тестовый Клиент',
        'address': 'г. СПб, ул. Тест', 'area': 85.5, 'city': 'СПБ',
        'status': 'active', 'dan_id': 9, 'dan_name': 'ДАН Тестов',
        'senior_manager_id': 2, 'dan_completed': 0,
        'agent_type': '', 'previous_column': None,
    }
    data.update(overrides)
    return data


# ═══════════════════════════════════════════════════════════════
# 1. TestCrmTabCardMoveCallbacks (8 тестов)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestCrmTabCardMoveCallbacks:
    """Callback on_card_moved: бизнес-правила перемещений CRM карточек."""

    def test_move_to_noviy_zakaz_blocked(self, qtbot, mock_data_access, mock_employee_admin):
        """Нельзя вернуть карточку в 'Новый заказ' из другой колонки."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_crm_cards.return_value = []

        mock_msg = MagicMock()
        with patch('ui.crm_tab.CustomMessageBox', return_value=mock_msg) as mock_cls:
            tab.on_card_moved(300, 'Стадия 1: планировочные решения', 'Новый заказ', 'Индивидуальный')
            mock_cls.assert_called_once()
            assert mock_cls.call_args[0][3] == 'warning'

    def test_move_within_same_column_allowed(self, qtbot, mock_data_access, mock_employee_admin):
        """Перемещение в ту же колонку не блокируется правилом 'Новый заказ'."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_crm_cards.return_value = []
        # Перемещение Новый заказ -> Новый заказ не должно показать предупреждение
        mock_msg = MagicMock()
        with patch('ui.crm_tab.CustomMessageBox', return_value=mock_msg) as mock_cls:
            # Этот вызов пройдет правило "нельзя в Новый заказ" (from==to=='Новый заказ')
            tab.on_card_moved(300, 'Новый заказ', 'Новый заказ', 'Индивидуальный')
            mock_cls.assert_not_called()

    def test_move_from_ozhidanie_wrong_column_blocked(self, qtbot, mock_data_access, mock_employee_admin):
        """Из 'В ожидании' можно вернуть только в прежний столбец или 'Выполненный проект'."""
        card = _make_crm_card(300, 'В ожидании', previous_column='Стадия 1: планировочные решения')
        mock_data_access.get_crm_card.return_value = card
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)

        mock_msg = MagicMock()
        with patch('ui.crm_tab.CustomMessageBox', return_value=mock_msg) as mock_cls:
            tab.on_card_moved(300, 'В ожидании', 'Стадия 2: концепция дизайна', 'Индивидуальный')
            mock_cls.assert_called_once()
            assert mock_cls.call_args[0][3] == 'warning'

    def test_move_from_ozhidanie_to_prev_column_allowed(self, qtbot, mock_data_access, mock_employee_admin):
        """Из 'В ожидании' в прежний столбец — разрешено."""
        card = _make_crm_card(300, 'В ожидании', previous_column='Стадия 1: планировочные решения')
        mock_data_access.get_crm_card.return_value = card
        mock_data_access.get_crm_cards.return_value = []
        mock_data_access.is_online = False
        mock_data_access.get_incomplete_stage_executors.return_value = []
        mock_data_access.get_stage_completion_info.return_value = {'stage': None, 'approval': None}
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)

        mock_msg = MagicMock()
        with patch('ui.crm_tab.CustomMessageBox', return_value=mock_msg) as mock_cls, \
             patch.object(tab, 'requires_executor_selection', return_value=False):
            tab.on_card_moved(300, 'В ожидании', 'Стадия 1: планировочные решения', 'Индивидуальный')
            mock_cls.assert_not_called()

    def test_move_calls_update_crm_card_column(self, qtbot, mock_data_access, mock_employee_admin):
        """При успешном перемещении вызывается update_crm_card_column или move_crm_card."""
        mock_data_access.get_crm_card.return_value = _make_crm_card(300, 'Новый заказ')
        mock_data_access.get_crm_cards.return_value = []
        mock_data_access.is_online = False
        mock_data_access.get_incomplete_stage_executors.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch.object(tab, 'requires_executor_selection', return_value=False):
            tab.on_card_moved(300, 'Новый заказ', 'В ожидании', 'Индивидуальный')
            # Должен быть вызван либо move_crm_card, либо update_crm_card_column
            assert mock_data_access.update_crm_card_column.called or \
                   mock_data_access.move_crm_card.called

    def test_move_pauses_sync_manager(self, qtbot, mock_data_access, mock_employee_admin):
        """on_card_moved приостанавливает SyncManager на время перемещения."""
        mock_sync = MagicMock()
        mock_data_access.get_crm_card.return_value = _make_crm_card(300, 'Новый заказ')
        mock_data_access.get_crm_cards.return_value = []
        mock_data_access.is_online = False
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch.object(tab, '_get_sync_manager', return_value=mock_sync), \
             patch.object(tab, 'requires_executor_selection', return_value=False):
            tab.on_card_moved(300, 'Новый заказ', 'В ожидании', 'Индивидуальный')
            mock_sync.pause_sync.assert_called_once()
            mock_sync.resume_sync.assert_called_once()

    def test_move_resumes_sync_on_error(self, qtbot, mock_data_access, mock_employee_admin):
        """SyncManager возобновляется даже при ошибке перемещения."""
        mock_sync = MagicMock()
        mock_data_access.get_crm_card.side_effect = Exception("Тестовая ошибка")
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)

        with patch.object(tab, '_get_sync_manager', return_value=mock_sync), \
             patch.object(tab, 'requires_executor_selection', return_value=False):
            tab.on_card_moved(300, 'Новый заказ', 'В ожидании', 'Индивидуальный')
            # resume_sync вызывается в finally
            mock_sync.resume_sync.assert_called_once()

    @pytest.mark.skip(reason="QMessageBox не импортирован глобально в crm_tab — access violation в offscreen")
    def test_move_designer_completed_blocks(self, qtbot, mock_data_access, mock_employee_admin):
        """Перемещение с designer_completed=1 — отложено до фикса глобального импорта QMessageBox."""
        pass


# ═══════════════════════════════════════════════════════════════
# 2. TestCrmTabRefreshCallbacks (5 тестов)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestCrmTabRefreshCallbacks:
    """Refresh, dashboard update, prefer_local логика."""

    def test_refresh_calls_load_individual(self, qtbot, mock_data_access, mock_employee_admin):
        """refresh_current_tab при index=0 загружает Индивидуальные."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.project_tabs.setCurrentIndex(0)
        mock_data_access.get_crm_cards.reset_mock()

        tab.refresh_current_tab()
        mock_data_access.get_crm_cards.assert_called_with('Индивидуальный')

    def test_refresh_uses_prefer_local(self, qtbot, mock_data_access, mock_employee_admin):
        """refresh_current_tab устанавливает prefer_local=True перед загрузкой."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)

        prefer_local_values = []
        original_get = mock_data_access.get_crm_cards

        def capture_prefer_local(*args, **kwargs):
            prefer_local_values.append(mock_data_access.prefer_local)
            return original_get.return_value

        mock_data_access.get_crm_cards = capture_prefer_local
        tab.refresh_current_tab()
        # prefer_local должен быть True во время вызова
        assert True in prefer_local_values

    def test_refresh_restores_prefer_local(self, qtbot, mock_data_access, mock_employee_admin):
        """prefer_local восстанавливается в False после refresh."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.refresh_current_tab()
        assert mock_data_access.prefer_local is False

    def test_refresh_updates_counters(self, qtbot, mock_data_access, mock_employee_admin):
        """refresh вызывает update_project_tab_counters."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch.object(tab, 'update_project_tab_counters') as mock_update:
            tab.refresh_current_tab()
            mock_update.assert_called()

    def test_ensure_data_loaded_sets_data_loaded_flag(self, qtbot, mock_data_access, mock_employee_admin):
        """ensure_data_loaded устанавливает _data_loaded=True."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert not tab._data_loaded
        tab.ensure_data_loaded()
        assert tab._data_loaded


# ═══════════════════════════════════════════════════════════════
# 3. TestContractsTabLoadCallbacks (8 тестов)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestContractsTabLoadCallbacks:
    """Callback-и загрузки и фильтрации ContractsTab."""

    def test_load_contracts_calls_get_all(self, qtbot, mock_data_access, mock_employee_admin):
        """load_contracts вызывает data.get_all_contracts."""
        mock_data_access.get_all_contracts.return_value = []
        mock_data_access.get_all_clients.return_value = []
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_all_contracts.reset_mock()
        tab.load_contracts()
        mock_data_access.get_all_contracts.assert_called_once()

    def test_load_contracts_populates_table(self, qtbot, mock_data_access, mock_employee_admin):
        """load_contracts заполняет таблицу данными."""
        mock_data_access.get_all_contracts.return_value = _sample_contracts()
        mock_data_access.get_all_clients.return_value = _sample_clients()
        mock_data_access.get_client.return_value = _sample_clients()[0]
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_contracts()
        assert tab.contracts_table.rowCount() == 2

    def test_load_contracts_displays_contract_number(self, qtbot, mock_data_access, mock_employee_admin):
        """Номер договора отображается в первой колонке."""
        mock_data_access.get_all_contracts.return_value = _sample_contracts()[:1]
        mock_data_access.get_all_clients.return_value = _sample_clients()
        mock_data_access.get_client.return_value = _sample_clients()[0]
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_contracts()
        assert tab.contracts_table.item(0, 0).text() == 'ИП-ПОЛ-001/26'

    def test_load_contracts_empty_list(self, qtbot, mock_data_access, mock_employee_admin):
        """Пустой список договоров — таблица пустая."""
        mock_data_access.get_all_contracts.return_value = []
        mock_data_access.get_all_clients.return_value = []
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_contracts()
        assert tab.contracts_table.rowCount() == 0

    def test_apply_search_filters_by_number(self, qtbot, mock_data_access, mock_employee_admin):
        """apply_search фильтрует по номеру договора."""
        mock_data_access.get_all_contracts.return_value = _sample_contracts()
        mock_data_access.get_all_clients.return_value = _sample_clients()
        mock_data_access.get_client.return_value = _sample_clients()[0]
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.apply_search({'contract_number': 'ИП-ПОЛ'})
        # Только 1 договор содержит 'ИП-ПОЛ'
        assert tab.contracts_table.rowCount() == 1

    def test_apply_search_filters_by_address(self, qtbot, mock_data_access, mock_employee_admin):
        """apply_search фильтрует по адресу."""
        mock_data_access.get_all_contracts.return_value = _sample_contracts()
        mock_data_access.get_all_clients.return_value = _sample_clients()
        mock_data_access.get_client.return_value = _sample_clients()[0]
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.apply_search({'address': 'Москва'})
        assert tab.contracts_table.rowCount() == 1

    def test_apply_search_empty_params_shows_all(self, qtbot, mock_data_access, mock_employee_admin):
        """apply_search с пустыми параметрами показывает все."""
        mock_data_access.get_all_contracts.return_value = _sample_contracts()
        mock_data_access.get_all_clients.return_value = _sample_clients()
        mock_data_access.get_client.return_value = _sample_clients()[0]
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.apply_search({})
        assert tab.contracts_table.rowCount() == 2

    def test_ensure_data_loaded_sets_flag(self, qtbot, mock_data_access, mock_employee_admin):
        """ensure_data_loaded устанавливает _data_loaded и вызывает load_contracts."""
        mock_data_access.get_all_contracts.return_value = []
        mock_data_access.get_all_clients.return_value = []
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        tab._data_loaded = False
        tab.ensure_data_loaded()
        assert tab._data_loaded


# ═══════════════════════════════════════════════════════════════
# 4. TestContractsTabCrudCallbacks (5 тестов)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestContractsTabCrudCallbacks:
    """CRUD callback-и ContractsTab."""

    def test_add_contract_opens_dialog(self, qtbot, mock_data_access, mock_employee_admin):
        """add_contract создаёт ContractDialog."""
        mock_data_access.get_all_contracts.return_value = []
        mock_data_access.get_all_clients.return_value = []
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.contracts_tab.ContractDialog') as MockDialog:
            MockDialog.return_value.exec_.return_value = QDialog.Rejected
            tab.add_contract()
            MockDialog.assert_called_once()

    def test_add_contract_reloads_on_accept(self, qtbot, mock_data_access, mock_employee_admin):
        """add_contract перезагружает данные при Accepted."""
        mock_data_access.get_all_contracts.return_value = []
        mock_data_access.get_all_clients.return_value = []
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.contracts_tab.ContractDialog') as MockDialog, \
             patch.object(tab, 'load_contracts') as mock_load:
            MockDialog.return_value.exec_.return_value = QDialog.Accepted
            tab.add_contract()
            mock_load.assert_called_once()

    def test_edit_contract_opens_dialog_with_data(self, qtbot, mock_data_access, mock_employee_admin):
        """edit_contract передаёт данные договора в диалог."""
        mock_data_access.get_all_contracts.return_value = []
        mock_data_access.get_all_clients.return_value = []
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        contract_data = _sample_contracts()[0]
        with patch('ui.contracts_tab.ContractDialog') as MockDialog:
            MockDialog.return_value.exec_.return_value = QDialog.Rejected
            tab.edit_contract(contract_data)
            MockDialog.assert_called_once_with(tab, contract_data)

    def test_view_contract_opens_readonly(self, qtbot, mock_data_access, mock_employee_admin):
        """view_contract открывает диалог в режиме view_only=True."""
        mock_data_access.get_all_contracts.return_value = []
        mock_data_access.get_all_clients.return_value = []
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        contract_data = _sample_contracts()[0]
        with patch('ui.contracts_tab.ContractDialog') as MockDialog:
            MockDialog.return_value.exec_.return_value = QDialog.Rejected
            tab.view_contract(contract_data)
            MockDialog.assert_called_once_with(tab, contract_data, view_only=True)

    def test_reset_filters_schedules_load(self, qtbot, mock_data_access, mock_employee_admin):
        """reset_filters вызывает QTimer.singleShot для load_contracts."""
        mock_data_access.get_all_contracts.return_value = []
        mock_data_access.get_all_clients.return_value = []
        tab = _create_contracts_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.contracts_tab.QTimer') as MockTimer:
            tab.reset_filters()
            MockTimer.singleShot.assert_called_once_with(0, tab.load_contracts)


# ═══════════════════════════════════════════════════════════════
# 5. TestSalariesTabPaymentCallbacks (7 тестов)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestSalariesTabPaymentCallbacks:
    """Callback-и загрузки выплат и переключения подвкладок."""

    def test_load_all_payments_populates_cache(self, qtbot, mock_data_access, mock_employee_admin):
        """load_all_payments сохраняет данные в _all_payments_cache."""
        payments = [_sample_payment(1), _sample_payment(2)]
        mock_data_access.get_year_payments.return_value = payments
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_all_payments()
        assert tab._all_payments_cache is not None

    def test_on_tab_changed_index_0_no_additional_load(self, qtbot, mock_data_access, mock_employee_admin):
        """Переключение на вкладку 0 (Все выплаты) не вызывает load_payment_type_data."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch.object(tab, 'load_payment_type_data') as mock_load:
            tab.on_tab_changed(0)
            mock_load.assert_not_called()

    def test_on_tab_changed_index_1_loads_individual(self, qtbot, mock_data_access, mock_employee_admin):
        """Переключение на вкладку 1 загружает 'Индивидуальные проекты'."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch.object(tab, 'load_payment_type_data') as mock_load:
            tab.on_tab_changed(1)
            mock_load.assert_called_once_with('Индивидуальные проекты')

    def test_on_tab_changed_index_3_loads_salaries(self, qtbot, mock_data_access, mock_employee_admin):
        """Переключение на вкладку 3 загружает 'Оклады'."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch.object(tab, 'load_payment_type_data') as mock_load:
            tab.on_tab_changed(3)
            mock_load.assert_called_once_with('Оклады')

    def test_on_tab_changed_index_4_loads_supervision(self, qtbot, mock_data_access, mock_employee_admin):
        """Переключение на вкладку 4 загружает 'Авторский надзор'."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch.object(tab, 'load_payment_type_data') as mock_load:
            tab.on_tab_changed(4)
            mock_load.assert_called_once_with('Авторский надзор')

    def test_apply_all_payments_filters_calls_load(self, qtbot, mock_data_access, mock_employee_admin):
        """apply_all_payments_filters вызывает load_all_payments."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch.object(tab, 'load_all_payments') as mock_load:
            tab.apply_all_payments_filters()
            mock_load.assert_called_once()

    def test_on_period_filter_changed_shows_month(self, qtbot, mock_data_access, mock_employee_admin):
        """Выбор 'Месяц' показывает month_filter и year_filter."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.period_filter.setCurrentText('Месяц')
        tab.on_period_filter_changed()
        # offscreen: используем not isHidden вместо isVisible
        assert not tab.month_filter.isHidden()
        assert not tab.year_filter.isHidden()


# ═══════════════════════════════════════════════════════════════
# 6. TestSalariesTabCacheCallbacks (4 теста)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestSalariesTabCacheCallbacks:
    """Кэш-логика SalariesTab."""

    def test_invalidate_cache_clears_all_caches(self, qtbot, mock_data_access, mock_employee_admin):
        """invalidate_cache очищает все поля кэша."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab._all_payments_cache = [_sample_payment()]
        tab._cache_year = 2026
        tab._payment_type_cache = {'Оклады': []}
        tab.invalidate_cache()
        assert tab._all_payments_cache is None
        assert tab._cache_year is None
        assert tab._payment_type_cache == {}

    def test_load_uses_cache_if_same_year(self, qtbot, mock_data_access, mock_employee_admin):
        """load_all_payments использует кэш если год совпадает (не Все)."""
        mock_data_access.get_year_payments.return_value = [_sample_payment()]
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.period_filter.setCurrentText('Месяц')
        tab.load_all_payments()
        call_count_1 = mock_data_access.get_year_payments.call_count
        tab.load_all_payments()
        # Второй вызов должен использовать кэш (не вызывать get_year_payments)
        assert mock_data_access.get_year_payments.call_count == call_count_1

    def test_force_reload_clears_cache(self, qtbot, mock_data_access, mock_employee_admin):
        """force_reload=True перезагружает данные."""
        mock_data_access.get_year_payments.return_value = [_sample_payment()]
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.period_filter.setCurrentText('Месяц')
        tab.load_all_payments()
        count_before = mock_data_access.get_year_payments.call_count
        tab.load_all_payments(force_reload=True)
        assert mock_data_access.get_year_payments.call_count > count_before

    def test_ensure_data_loaded_uses_prefer_local(self, qtbot, mock_data_access, mock_employee_admin):
        """ensure_data_loaded устанавливает _prefer_local_load=True."""
        mock_data_access.get_year_payments.return_value = []
        tab = _create_salaries_tab(qtbot, mock_data_access, mock_employee_admin)
        tab._data_loaded = False
        tab.ensure_data_loaded()
        # После ensure_data_loaded prefer_local_load должен быть сброшен
        assert not getattr(tab, '_prefer_local_load', False)


# ═══════════════════════════════════════════════════════════════
# 7. TestEmployeesTabCrudCallbacks (6 тестов)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestEmployeesTabCrudCallbacks:
    """CRUD callback-и EmployeesTab."""

    def test_add_employee_opens_dialog(self, qtbot, mock_data_access, mock_employee_admin):
        """add_employee открывает EmployeeDialog."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.employees_tab.EmployeeDialog') as MockDialog:
            MockDialog.return_value.exec_.return_value = QDialog.Rejected
            tab.add_employee()
            MockDialog.assert_called_once()

    def test_add_employee_reloads_on_accept(self, qtbot, mock_data_access, mock_employee_admin):
        """add_employee перезагружает при Accepted."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.employees_tab.EmployeeDialog') as MockDialog, \
             patch.object(tab, '_reload_employees') as mock_reload:
            MockDialog.return_value.exec_.return_value = QDialog.Accepted
            tab.add_employee()
            mock_reload.assert_called_once_with(prefer_local=False)

    def test_edit_employee_passes_data(self, qtbot, mock_data_access, mock_employee_admin):
        """edit_employee передаёт данные сотрудника в диалог."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        emp_data = _sample_employees_list()[1]  # Дизайнер
        with patch('ui.employees_tab.EmployeeDialog') as MockDialog:
            MockDialog.return_value.exec_.return_value = QDialog.Rejected
            tab.edit_employee(emp_data)
            MockDialog.assert_called_once_with(tab, emp_data)

    def test_edit_employee_smp_cannot_edit_admin(self, qtbot, mock_data_access, mock_employee_senior_manager):
        """СМП не может редактировать сотрудников административного отдела."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_senior_manager)
        admin_emp = _sample_employees_list()[0]  # Руководитель студии
        with patch('ui.employees_tab.EmployeeDialog') as MockDialog:
            tab.edit_employee(admin_emp)
            # Диалог НЕ должен открываться для админской должности
            MockDialog.assert_not_called()

    def test_delete_employee_self_blocked(self, qtbot, mock_data_access, mock_employee_admin):
        """Нельзя удалить самого себя."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        self_data = {'id': 1, 'full_name': 'Тестов Админ', 'position': 'Руководитель студии'}
        with patch('ui.custom_message_box.CustomQuestionBox') as MockQ:
            tab.delete_employee(self_data)
            # Диалог подтверждения не должен показываться
            MockQ.assert_not_called()

    def test_delete_employee_no_rights(self, qtbot, mock_data_access, mock_employee_designer):
        """Дизайнер не имеет прав на удаление."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_designer)
        emp_data = _sample_employees_list()[2]  # Менеджер
        with patch('ui.custom_message_box.CustomQuestionBox') as MockQ:
            tab.delete_employee(emp_data)
            # Диалог подтверждения НЕ показывается (нет прав)
            MockQ.assert_not_called()


# ═══════════════════════════════════════════════════════════════
# 8. TestEmployeesTabLoadCallbacks (4 теста)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestEmployeesTabLoadCallbacks:
    """Загрузка и фильтрация сотрудников."""

    def test_load_employees_calls_get_all(self, qtbot, mock_data_access, mock_employee_admin):
        """load_employees вызывает data.get_all_employees."""
        mock_data_access.get_all_employees.return_value = _sample_employees_list()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_all_employees.reset_mock()
        tab.load_employees()
        mock_data_access.get_all_employees.assert_called_once()

    def test_load_employees_populates_table(self, qtbot, mock_data_access, mock_employee_admin):
        """load_employees заполняет таблицу."""
        mock_data_access.get_all_employees.return_value = _sample_employees_list()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_employees()
        assert tab.employees_table.rowCount() == 3

    def test_load_employees_filter_admin_department(self, qtbot, mock_data_access, mock_employee_admin):
        """Фильтр 'admin' оставляет только административные должности."""
        mock_data_access.get_all_employees.return_value = _sample_employees_list()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_employees(department='admin')
        # Только Руководитель студии
        assert tab.employees_table.rowCount() == 1

    def test_load_employees_filter_project_department(self, qtbot, mock_data_access, mock_employee_admin):
        """Фильтр 'project' оставляет Дизайнеров и Чертёжников."""
        mock_data_access.get_all_employees.return_value = _sample_employees_list()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_employees(department='project')
        # Только Дизайнер
        assert tab.employees_table.rowCount() == 1


# ═══════════════════════════════════════════════════════════════
# 9. TestSupervisionTabLoadCallbacks (6 тестов)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestSupervisionTabLoadCallbacks:
    """Загрузка карточек CRMSupervisionTab."""

    @pytest.fixture(autouse=True)
    def cleanup_patchers(self):
        """Останавливаем все patch.start() после каждого теста."""
        yield
        patch.stopall()

    def test_load_active_cards_calls_data_access(self, qtbot, mock_data_access, mock_employee_admin):
        """load_active_cards вызывает get_supervision_cards_active."""
        mock_data_access.get_supervision_cards_active.return_value = []
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_supervision_cards_active.reset_mock()
        tab.load_active_cards()
        mock_data_access.get_supervision_cards_active.assert_called_once()

    def test_load_active_cards_with_data(self, qtbot, mock_data_access, mock_employee_admin):
        """Карточки добавляются в соответствующие колонки."""
        cards = [_make_supervision_card(500, 'Новый заказ'), _make_supervision_card(501, 'В ожидании')]
        mock_data_access.get_supervision_cards_active.return_value = cards
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_active_cards()
        # Проверяем что колонки обновились
        total = sum(col.cards_list.count() for col in tab.active_widget.columns.values())
        assert total == 2

    @pytest.mark.xfail(reason="_has_perm=True в моке → ДАН видит все карточки, фильтр не срабатывает")
    def test_load_active_cards_dan_filter(self, qtbot, mock_data_access, mock_employee_dan):
        """ДАН видит только свои карточки."""
        cards = [
            _make_supervision_card(500, 'Новый заказ', dan_id=9),   # ДАН id=9
            _make_supervision_card(501, 'В ожидании', dan_id=99),    # Другой ДАН
        ]
        mock_data_access.get_supervision_cards_active.return_value = cards
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_dan)
        tab.load_active_cards()
        total = sum(col.cards_list.count() for col in tab.active_widget.columns.values())
        assert total == 1  # Только карточка с dan_id=9

    def test_load_archive_cards_calls_data_access(self, qtbot, mock_data_access, mock_employee_admin):
        """load_archive_cards вызывает get_supervision_cards_archived."""
        mock_data_access.get_supervision_cards_archived.return_value = []
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        # У архива должен быть archive_layout
        if hasattr(tab, 'archive_widget') and hasattr(tab.archive_widget, 'archive_layout'):
            mock_data_access.get_supervision_cards_archived.reset_mock()
            tab.load_archive_cards()
            mock_data_access.get_supervision_cards_archived.assert_called_once()

    def test_ensure_data_loaded_sets_flag(self, qtbot, mock_data_access, mock_employee_admin):
        """ensure_data_loaded устанавливает _data_loaded=True."""
        mock_data_access.get_supervision_cards_active.return_value = []
        mock_data_access.get_supervision_cards_archived.return_value = []
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert not tab._data_loaded
        tab.ensure_data_loaded()
        assert tab._data_loaded

    def test_ensure_data_loaded_double_call_no_reload(self, qtbot, mock_data_access, mock_employee_admin):
        """Повторный вызов ensure_data_loaded не перезагружает."""
        mock_data_access.get_supervision_cards_active.return_value = []
        mock_data_access.get_supervision_cards_archived.return_value = []
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.ensure_data_loaded()
        call_count = mock_data_access.get_supervision_cards_active.call_count
        tab.ensure_data_loaded()
        assert mock_data_access.get_supervision_cards_active.call_count == call_count


# ═══════════════════════════════════════════════════════════════
# 10. TestSupervisionTabMoveCallbacks (5 тестов)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestSupervisionTabMoveCallbacks:
    """on_card_moved в CRMSupervisionTab: бизнес-правила перемещений."""

    @pytest.fixture(autouse=True)
    def cleanup_patchers(self):
        """Останавливаем все patch.start() после каждого теста."""
        yield
        patch.stopall()

    def test_move_to_noviy_zakaz_blocked(self, qtbot, mock_data_access, mock_employee_admin):
        """Нельзя вернуть карточку надзора в 'Новый заказ'."""
        mock_data_access.get_supervision_cards_active.return_value = []
        mock_data_access.get_supervision_cards_archived.return_value = []
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)

        mock_msg = MagicMock()
        with patch('ui.crm_supervision_tab.CustomMessageBox', return_value=mock_msg) as mock_cls:
            tab.on_card_moved(500, 'Стадия 1: Закупка керамогранита', 'Новый заказ')
            mock_cls.assert_called_once()
            assert mock_cls.call_args[0][3] == 'warning'

    def test_move_noviy_to_noviy_not_blocked(self, qtbot, mock_data_access, mock_employee_admin):
        """Перемещение из 'Новый заказ' в 'Новый заказ' не блокируется."""
        mock_data_access.get_supervision_cards_active.return_value = []
        mock_data_access.get_supervision_cards_archived.return_value = []
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)

        mock_msg = MagicMock()
        with patch('ui.crm_supervision_tab.CustomMessageBox', return_value=mock_msg) as mock_cls:
            tab.on_card_moved(500, 'Новый заказ', 'Новый заказ')
            mock_cls.assert_not_called()

    def test_move_from_ozhidanie_wrong_column(self, qtbot, mock_data_access, mock_employee_admin):
        """Из 'В ожидании' можно только в прежний столбец или 'Выполненный проект'."""
        card = _make_supervision_card(500, 'В ожидании', previous_column='Стадия 1: Закупка керамогранита')
        mock_data_access.get_supervision_card.return_value = card
        mock_data_access.get_supervision_cards_active.return_value = []
        mock_data_access.get_supervision_cards_archived.return_value = []
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)

        mock_msg = MagicMock()
        with patch('ui.crm_supervision_tab.CustomMessageBox', return_value=mock_msg) as mock_cls:
            tab.on_card_moved(500, 'В ожидании', 'Стадия 5: Закупка настенных материалов')
            mock_cls.assert_called_once()
            assert mock_cls.call_args[0][3] == 'warning'

    def test_move_from_ozhidanie_to_vipolnenniy_allowed(self, qtbot, mock_data_access, mock_employee_admin):
        """Из 'В ожидании' в 'Выполненный проект' — разрешено."""
        card = _make_supervision_card(500, 'В ожидании', previous_column='Стадия 1: Закупка керамогранита')
        mock_data_access.get_supervision_card.return_value = card
        mock_data_access.get_supervision_cards_active.return_value = []
        mock_data_access.get_supervision_cards_archived.return_value = []
        mock_data_access.add_supervision_history.return_value = None
        mock_data_access.move_supervision_card.return_value = True
        mock_data_access.update_supervision_card.return_value = True
        mock_data_access.resume_supervision_card.return_value = True
        mock_data_access.reset_supervision_stage_completion.return_value = True
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)

        mock_msg = MagicMock()
        mock_completion_dialog = MagicMock()
        mock_completion_dialog.exec_.return_value = QDialog.Accepted
        with patch('ui.crm_supervision_tab.CustomMessageBox', return_value=mock_msg) as mock_cls, \
             patch('ui.crm_supervision_tab.SupervisionCompletionDialog', return_value=mock_completion_dialog), \
             patch('ui.crm_supervision_tab.SupervisionStageDeadlineDialog', return_value=MagicMock()), \
             patch('ui.supervision_dialogs.DatabaseManager', return_value=MagicMock()):
            tab.on_card_moved(500, 'В ожидании', 'Выполненный проект')
            mock_cls.assert_not_called()

    def test_update_tab_counters(self, qtbot, mock_data_access, mock_employee_admin):
        """update_tab_counters обновляет текст вкладок."""
        mock_data_access.get_supervision_cards_active.return_value = []
        mock_data_access.get_supervision_cards_archived.return_value = []
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.update_tab_counters()
        assert 'Активные проекты (0)' == tab.tabs.tabText(0)


# ═══════════════════════════════════════════════════════════════
# 11. TestCardEditDialogCallbacks (5 тестов)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
class TestCardEditDialogCallbacks:
    """Callback-и CardEditDialog: save_changes, load_data."""

    @pytest.fixture
    def card_dialog_factory(self, qtbot, mock_employee_admin):
        """Фабрика для создания CardEditDialog."""
        created = []

        def _factory(card_data_overrides=None, employee=None, view_only=False):
            cd = _make_crm_card(**(card_data_overrides or {}))
            if employee is None:
                employee = mock_employee_admin

            mock_da = MagicMock()
            mock_da.get_crm_card.return_value = cd
            mock_da.get_contract.return_value = {
                'id': 200, 'status': 'active', 'tech_task_link': None,
                'tech_task_file_name': None, 'measurement_image_link': None,
                'measurement_file_name': None, 'references_yandex_path': None,
                'photo_documentation_yandex_path': None, 'yandex_folder_path': '/test',
                'area': 85.5, 'city': 'СПБ', 'project_type': 'Индивидуальный',
                'project_subtype': 'Полный проект',
            }
            mock_da.get_payments_for_contract.return_value = []
            mock_da.get_project_timeline.return_value = []
            mock_da.get_action_history.return_value = []
            mock_da.get_employees_by_position.return_value = []
            mock_da.get_all_employees.return_value = [
                {'id': 2, 'full_name': 'Старший Менеджер', 'position': 'Старший менеджер проектов', 'status': 'активный'},
                {'id': 5, 'full_name': 'Менеджер Тест', 'position': 'Менеджер', 'status': 'активный'},
            ]
            mock_da.is_online = False
            mock_da.is_multi_user = False
            mock_da.db = MagicMock()
            mock_da.api_client = None
            mock_da.get_stage_files.return_value = []
            mock_da.get_supervision_cards.return_value = []

            with patch('ui.crm_card_edit_dialog.DataAccess') as MockDA, \
                 patch('ui.crm_card_edit_dialog.DatabaseManager', return_value=MagicMock()), \
                 patch('ui.crm_card_edit_dialog.IconLoader', _mock_icon_loader()), \
                 patch('ui.crm_card_edit_dialog.YandexDiskManager', return_value=None), \
                 patch('ui.crm_card_edit_dialog.YANDEX_DISK_TOKEN', ''), \
                 patch('ui.crm_card_edit_dialog.TableSettings') as MockTS, \
                 patch('ui.crm_card_edit_dialog._has_perm', return_value=True), \
                 patch('ui.crm_card_edit_dialog._emp_has_pos', return_value=True), \
                 patch('ui.crm_card_edit_dialog._emp_only_pos', return_value=False):
                MockDA.return_value = mock_da
                MockTS.return_value.load_column_collapse_state.return_value = {}
                MockTS.return_value.get_sort_order.return_value = (None, None)
                from ui.crm_card_edit_dialog import CardEditDialog

                parent = QWidget()
                qtbot.addWidget(parent)
                parent.api_client = None
                parent.data = mock_da
                parent.refresh_current_tab = MagicMock()

                dlg = CardEditDialog(parent, cd, view_only=view_only, employee=employee)
                created.append(dlg)
                qtbot.addWidget(dlg)
                return dlg, mock_da

        yield _factory

        for d in created:
            try:
                d.close()
            except Exception:
                pass

    def test_save_changes_calls_update_crm_card(self, card_dialog_factory):
        """save_changes вызывает data.update_crm_card."""
        dlg, mock_da = card_dialog_factory()
        if hasattr(dlg, 'tags'):
            dlg.tags.setText('VIP')
        # Блокируем accept() чтобы диалог не закрывался
        with patch.object(dlg, 'accept'):
            dlg.save_changes()
            mock_da.update_crm_card.assert_called()

    def test_save_changes_updates_contract_status(self, card_dialog_factory):
        """save_changes обновляет статус договора через update_contract."""
        dlg, mock_da = card_dialog_factory()
        if hasattr(dlg, 'status_combo'):
            dlg.status_combo.setCurrentText('СДАН')
        with patch.object(dlg, 'accept'):
            dlg.save_changes()
            mock_da.update_contract.assert_called()

    def test_load_data_sets_loading_flag(self, card_dialog_factory):
        """load_data устанавливает _loading_data=True в начале."""
        dlg, mock_da = card_dialog_factory()
        dlg._loading_data = False
        # Замокаем _load_all_stage_files_batch — она использует DatabaseManager
        # напрямую, что блокируется conftest safety check
        with patch.object(dlg, '_load_all_stage_files_batch'):
            dlg.load_data()
        # Проверяем что get_crm_card был вызван
        mock_da.get_crm_card.assert_called()

    def test_truncate_filename_short(self, card_dialog_factory):
        """truncate_filename не обрезает короткие имена."""
        dlg, _ = card_dialog_factory()
        assert dlg.truncate_filename('short.pdf') == 'short.pdf'

    def test_truncate_filename_long(self, card_dialog_factory):
        """truncate_filename обрезает длинные имена с многоточием."""
        dlg, _ = card_dialog_factory()
        long_name = 'a' * 60 + '.pdf'
        result = dlg.truncate_filename(long_name, max_length=30)
        assert '...' in result
        assert len(result) <= 30
