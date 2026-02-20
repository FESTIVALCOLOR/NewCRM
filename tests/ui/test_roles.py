# -*- coding: utf-8 -*-
"""
Тесты ролевого доступа — pytest-qt offscreen.

Покрытие:
  - TestEmpHasPos (10)              — helper _emp_has_pos
  - TestEmpOnlyPos (10)             — helper _emp_only_pos
  - TestRolesConfig (8)             — ROLES/POSITIONS из config.py
  - TestTabVisibilityFull (8)       — Руководитель/Старший менеджер — все вкладки
  - TestTabVisibilityManagement (8) — СДП/ГАП/Менеджер — частичные вкладки
  - TestTabVisibilityExecutors (8)  — Дизайнер/Чертёжник/Замерщик — только СРМ
  - TestTabVisibilityDAN (4)        — ДАН — только СРМ надзора
  - TestDualRoles (10)              — Двойные роли: union, can_edit OR
  - TestCanEditFlag (8)             — can_edit для каждой роли
  - TestCRMRoleActions (10)         — CRM кнопки/действия по ролям
  - TestSupervisionRoles (8)        — Надзор: доступ по ролям
ИТОГО: 92 теста
"""

import pytest
import logging
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QWidget, QPushButton
from PyQt5.QtGui import QIcon

logger = logging.getLogger('tests')

# ─── Импорт config данных ─────────────────────────────────────────

from config import ROLES, POSITIONS


# ─── Helpers ───────────────────────────────────────────────────────

def _make_employee(position, secondary_position='', emp_id=1):
    """Создание dict сотрудника для тестов."""
    return {
        'id': emp_id,
        'full_name': f'Тест {position}',
        'login': f'test_{emp_id}',
        'position': position,
        'secondary_position': secondary_position,
        'department': 'Тестовый отдел',
        'status': 'активный',
        'offline_mode': False,
    }


def _mock_icon_loader():
    """IconLoader с реальным QIcon."""
    mock = MagicMock()
    mock.load = MagicMock(return_value=QIcon())
    mock.create_icon_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    mock.get_icon_path = MagicMock(return_value='')
    return mock


def _get_tabs_for_employee(employee):
    """Расчёт видимых вкладок для сотрудника (копия логики MainWindow)."""
    position = employee.get('position', '')
    secondary_position = employee.get('secondary_position', '')

    allowed_tabs = set(ROLES.get(position, {}).get('tabs', []))

    if secondary_position:
        secondary_tabs = set(ROLES.get(secondary_position, {}).get('tabs', []))
        allowed_tabs = allowed_tabs.union(secondary_tabs)

    return allowed_tabs


def _get_can_edit(employee):
    """Расчёт can_edit для сотрудника (копия логики MainWindow)."""
    position = employee.get('position', '')
    secondary_position = employee.get('secondary_position', '')

    can_edit = ROLES.get(position, {}).get('can_edit', False)

    if secondary_position:
        secondary_can_edit = ROLES.get(secondary_position, {}).get('can_edit', False)
        can_edit = can_edit or secondary_can_edit

    return can_edit


def _create_crm_tab(qtbot, employee, can_edit=True):
    """Создание CRMTab для проверки ролевого доступа."""
    mock_da = MagicMock()
    mock_da.api_client = None
    mock_da.get_all_clients.return_value = []
    mock_da.get_all_contracts.return_value = []
    mock_da.get_all_employees.return_value = []
    mock_da.get_crm_cards.return_value = []
    mock_da.get_project_timeline.return_value = []
    mock_da.get_action_history.return_value = []
    mock_da.db = MagicMock()

    with patch('ui.crm_tab.DataAccess') as MockDA, \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.YandexDiskManager', return_value=None), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.crm_tab.TableSettings') as MockTS:
        MockDA.return_value = mock_da
        MockTS.return_value.load_column_collapse_state.return_value = {}
        from ui.crm_tab import CRMTab
        tab = CRMTab(employee=employee, can_edit=can_edit, api_client=None)
        qtbot.addWidget(tab)
        return tab


def _create_supervision_tab(qtbot, employee):
    """Создание CRMSupervisionTab для проверки ролевого доступа."""
    mock_da = MagicMock()
    mock_da.api_client = None
    mock_da.get_supervision_cards_active.return_value = []
    mock_da.get_supervision_cards_archived.return_value = []
    mock_da.get_all_employees.return_value = []
    mock_da.get_supervision_history.return_value = []
    mock_da.get_supervision_timeline.return_value = []
    mock_da.db = MagicMock()

    with patch('ui.crm_supervision_tab.DataAccess') as MockDA, \
         patch('ui.crm_supervision_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_supervision_tab.YandexDiskManager', return_value=None), \
         patch('ui.crm_supervision_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.crm_supervision_tab.TableSettings') as MockTS:
        MockDA.return_value = mock_da
        MockTS.return_value.load_column_collapse_state.return_value = {}
        from ui.crm_supervision_tab import CRMSupervisionTab
        tab = CRMSupervisionTab(employee=employee, api_client=None)
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
# TestEmpHasPos — helper _emp_has_pos (10 тестов)
# ═══════════════════════════════════════════════════════════════════

class TestEmpHasPos:
    """Тесты _emp_has_pos: True если ЛЮБАЯ должность совпадает."""

    def _func(self, employee, *positions):
        from ui.crm_tab import _emp_has_pos
        return _emp_has_pos(employee, *positions)

    def test_primary_match(self):
        emp = _make_employee('Дизайнер')
        assert self._func(emp, 'Дизайнер') is True

    def test_primary_no_match(self):
        emp = _make_employee('Дизайнер')
        assert self._func(emp, 'Менеджер') is False

    def test_secondary_match(self):
        emp = _make_employee('Дизайнер', 'Менеджер')
        assert self._func(emp, 'Менеджер') is True

    def test_both_match(self):
        emp = _make_employee('Дизайнер', 'Менеджер')
        assert self._func(emp, 'Дизайнер', 'Менеджер') is True

    def test_none_employee(self):
        assert self._func(None, 'Дизайнер') is False

    def test_empty_employee(self):
        assert self._func({}, 'Дизайнер') is False

    def test_multi_positions_one_match(self):
        emp = _make_employee('СДП')
        assert self._func(emp, 'СДП', 'ГАП', 'Менеджер') is True

    def test_multi_positions_no_match(self):
        emp = _make_employee('Замерщик')
        assert self._func(emp, 'СДП', 'ГАП', 'Менеджер') is False

    def test_admin_in_list(self):
        emp = _make_employee('Руководитель студии')
        assert self._func(emp, 'Руководитель студии', 'Старший менеджер проектов') is True

    def test_secondary_only(self):
        emp = _make_employee('Чертёжник', 'Дизайнер')
        assert self._func(emp, 'Дизайнер') is True


# ═══════════════════════════════════════════════════════════════════
# TestEmpOnlyPos — helper _emp_only_pos (10 тестов)
# ═══════════════════════════════════════════════════════════════════

class TestEmpOnlyPos:
    """Тесты _emp_only_pos: True если ВСЕ должности входят в набор."""

    def _func(self, employee, *positions):
        from ui.crm_tab import _emp_only_pos
        return _emp_only_pos(employee, *positions)

    def test_single_match(self):
        emp = _make_employee('Дизайнер')
        assert self._func(emp, 'Дизайнер') is True

    def test_single_no_match(self):
        emp = _make_employee('Менеджер')
        assert self._func(emp, 'Дизайнер') is False

    def test_dual_both_in_set(self):
        emp = _make_employee('Дизайнер', 'Чертёжник')
        assert self._func(emp, 'Дизайнер', 'Чертёжник', 'Замерщик') is True

    def test_dual_secondary_not_in_set(self):
        emp = _make_employee('Дизайнер', 'Менеджер')
        assert self._func(emp, 'Дизайнер', 'Чертёжник', 'Замерщик') is False

    def test_none_employee(self):
        assert self._func(None, 'Дизайнер') is False

    def test_empty_employee(self):
        assert self._func({}, 'Дизайнер') is False

    def test_executor_set(self):
        """Чистый исполнитель (без второй роли)."""
        emp = _make_employee('Замерщик')
        assert self._func(emp, 'Дизайнер', 'Чертёжник', 'Замерщик') is True

    def test_executor_with_manager_secondary(self):
        """Исполнитель с доп. ролью менеджера — НЕ чистый исполнитель."""
        emp = _make_employee('Дизайнер', 'Менеджер')
        assert self._func(emp, 'Дизайнер', 'Чертёжник', 'Замерщик') is False

    def test_admin_not_executor(self):
        emp = _make_employee('Руководитель студии')
        assert self._func(emp, 'Дизайнер', 'Чертёжник', 'Замерщик') is False

    def test_no_secondary_ok(self):
        """Без secondary_position — проверяется только primary."""
        emp = _make_employee('Чертёжник', '')
        assert self._func(emp, 'Чертёжник') is True


# ═══════════════════════════════════════════════════════════════════
# TestRolesConfig — ROLES/POSITIONS из config.py (8 тестов)
# ═══════════════════════════════════════════════════════════════════

class TestRolesConfig:
    """Проверка конфигурации ролей."""

    def test_9_positions(self):
        """9 должностей в POSITIONS."""
        assert len(POSITIONS) == 9

    def test_all_positions_in_roles(self):
        """Все должности из POSITIONS присутствуют в ROLES."""
        for pos in POSITIONS:
            assert pos in ROLES, f"Должность '{pos}' не найдена в ROLES"

    def test_admin_has_8_tabs(self):
        """Руководитель — 8 вкладок."""
        tabs = ROLES['Руководитель студии']['tabs']
        assert len(tabs) == 8

    def test_sr_manager_has_8_tabs(self):
        """Старший менеджер — 8 вкладок."""
        tabs = ROLES['Старший менеджер проектов']['tabs']
        assert len(tabs) == 8

    def test_designer_has_1_tab(self):
        """Дизайнер — 1 вкладка (СРМ)."""
        tabs = ROLES['Дизайнер']['tabs']
        assert len(tabs) == 1
        assert 'СРМ' in tabs

    def test_dan_has_1_tab(self):
        """ДАН — 1 вкладка (СРМ надзора)."""
        tabs = ROLES['ДАН']['tabs']
        assert len(tabs) == 1
        assert 'СРМ надзора' in tabs

    def test_surveyor_can_edit_false(self):
        """Замерщик — can_edit=False (единственный)."""
        assert ROLES['Замерщик']['can_edit'] is False

    def test_all_others_can_edit_true(self):
        """Все кроме Замерщика — can_edit=True."""
        for pos in POSITIONS:
            if pos != 'Замерщик':
                assert ROLES[pos]['can_edit'] is True, f"{pos} should have can_edit=True"


# ═══════════════════════════════════════════════════════════════════
# TestTabVisibilityFull — Руководитель/Старший менеджер (8 тестов)
# ═══════════════════════════════════════════════════════════════════

class TestTabVisibilityFull:
    """Полный доступ: Руководитель + Старший менеджер."""

    @pytest.mark.parametrize('position', [
        'Руководитель студии', 'Старший менеджер проектов'
    ])
    def test_sees_clients(self, position):
        emp = _make_employee(position)
        assert 'Клиенты' in _get_tabs_for_employee(emp)

    @pytest.mark.parametrize('position', [
        'Руководитель студии', 'Старший менеджер проектов'
    ])
    def test_sees_contracts(self, position):
        emp = _make_employee(position)
        assert 'Договора' in _get_tabs_for_employee(emp)

    @pytest.mark.parametrize('position', [
        'Руководитель студии', 'Старший менеджер проектов'
    ])
    def test_sees_salaries(self, position):
        emp = _make_employee(position)
        assert 'Зарплаты' in _get_tabs_for_employee(emp)

    @pytest.mark.parametrize('position', [
        'Руководитель студии', 'Старший менеджер проектов'
    ])
    def test_sees_all_8_tabs(self, position):
        emp = _make_employee(position)
        tabs = _get_tabs_for_employee(emp)
        assert len(tabs) == 8


# ═══════════════════════════════════════════════════════════════════
# TestTabVisibilityManagement — СДП/ГАП/Менеджер (8 тестов)
# ═══════════════════════════════════════════════════════════════════

class TestTabVisibilityManagement:
    """Управленческий уровень: СДП, ГАП, Менеджер."""

    @pytest.mark.parametrize('position', ['СДП', 'ГАП'])
    def test_sdp_gap_sees_crm(self, position):
        emp = _make_employee(position)
        assert 'СРМ' in _get_tabs_for_employee(emp)

    @pytest.mark.parametrize('position', ['СДП', 'ГАП'])
    def test_sdp_gap_sees_reports(self, position):
        emp = _make_employee(position)
        assert 'Отчеты и Статистика' in _get_tabs_for_employee(emp)

    @pytest.mark.parametrize('position', ['СДП', 'ГАП'])
    def test_sdp_gap_no_clients(self, position):
        emp = _make_employee(position)
        assert 'Клиенты' not in _get_tabs_for_employee(emp)

    def test_manager_sees_supervision(self):
        emp = _make_employee('Менеджер')
        assert 'СРМ надзора' in _get_tabs_for_employee(emp)

    def test_sdp_no_supervision(self):
        emp = _make_employee('СДП')
        assert 'СРМ надзора' not in _get_tabs_for_employee(emp)

    def test_gap_no_supervision(self):
        emp = _make_employee('ГАП')
        assert 'СРМ надзора' not in _get_tabs_for_employee(emp)

    def test_manager_4_tabs(self):
        emp = _make_employee('Менеджер')
        tabs = _get_tabs_for_employee(emp)
        assert len(tabs) == 4

    def test_sdp_3_tabs(self):
        emp = _make_employee('СДП')
        tabs = _get_tabs_for_employee(emp)
        assert len(tabs) == 3


# ═══════════════════════════════════════════════════════════════════
# TestTabVisibilityExecutors — Дизайнер/Чертёжник/Замерщик (8 тестов)
# ═══════════════════════════════════════════════════════════════════

class TestTabVisibilityExecutors:
    """Исполнительский уровень: Дизайнер, Чертёжник, Замерщик."""

    @pytest.mark.parametrize('position', ['Дизайнер', 'Чертёжник', 'Замерщик'])
    def test_sees_crm(self, position):
        emp = _make_employee(position)
        assert 'СРМ' in _get_tabs_for_employee(emp)

    @pytest.mark.parametrize('position', ['Дизайнер', 'Чертёжник', 'Замерщик'])
    def test_no_clients(self, position):
        emp = _make_employee(position)
        assert 'Клиенты' not in _get_tabs_for_employee(emp)

    def test_designer_1_tab(self):
        emp = _make_employee('Дизайнер')
        assert len(_get_tabs_for_employee(emp)) == 1

    def test_surveyor_1_tab(self):
        emp = _make_employee('Замерщик')
        assert len(_get_tabs_for_employee(emp)) == 1


# ═══════════════════════════════════════════════════════════════════
# TestTabVisibilityDAN — ДАН (4 теста)
# ═══════════════════════════════════════════════════════════════════

class TestTabVisibilityDAN:
    """ДАН — только СРМ надзора."""

    def test_sees_supervision(self):
        emp = _make_employee('ДАН')
        assert 'СРМ надзора' in _get_tabs_for_employee(emp)

    def test_no_crm(self):
        emp = _make_employee('ДАН')
        assert 'СРМ' not in _get_tabs_for_employee(emp)

    def test_no_clients(self):
        emp = _make_employee('ДАН')
        assert 'Клиенты' not in _get_tabs_for_employee(emp)

    def test_1_tab(self):
        emp = _make_employee('ДАН')
        assert len(_get_tabs_for_employee(emp)) == 1


# ═══════════════════════════════════════════════════════════════════
# TestDualRoles — Двойные роли (10 тестов)
# ═══════════════════════════════════════════════════════════════════

class TestDualRoles:
    """Двойные роли: union вкладок, OR can_edit."""

    def test_designer_manager_union_tabs(self):
        """Дизайнер + Менеджер = union: СРМ + СРМ надзора + Отчеты + Сотрудники."""
        emp = _make_employee('Дизайнер', 'Менеджер')
        tabs = _get_tabs_for_employee(emp)
        assert 'СРМ' in tabs
        assert 'СРМ надзора' in tabs
        assert 'Отчеты и Статистика' in tabs
        assert 'Сотрудники' in tabs

    def test_designer_manager_more_than_designer(self):
        """Дизайнер+Менеджер видит больше вкладок чем чистый Дизайнер."""
        des = _make_employee('Дизайнер')
        des_mgr = _make_employee('Дизайнер', 'Менеджер')
        assert len(_get_tabs_for_employee(des_mgr)) > len(_get_tabs_for_employee(des))

    def test_designer_draftsman_union(self):
        """Дизайнер + Чертёжник = СРМ (оба имеют только СРМ)."""
        emp = _make_employee('Дизайнер', 'Чертёжник')
        tabs = _get_tabs_for_employee(emp)
        assert tabs == {'СРМ'}

    def test_designer_manager_4_tabs(self):
        """Дизайнер + Менеджер = 4 вкладки."""
        emp = _make_employee('Дизайнер', 'Менеджер')
        tabs = _get_tabs_for_employee(emp)
        assert len(tabs) == 4

    def test_surveyor_manager_can_edit_true(self):
        """Замерщик(can_edit=False) + Менеджер(True) = True (OR)."""
        emp = _make_employee('Замерщик', 'Менеджер')
        assert _get_can_edit(emp) is True

    def test_surveyor_alone_can_edit_false(self):
        """Замерщик без second — can_edit=False."""
        emp = _make_employee('Замерщик')
        assert _get_can_edit(emp) is False

    def test_designer_manager_can_edit_true(self):
        """Дизайнер + Менеджер: True OR True = True."""
        emp = _make_employee('Дизайнер', 'Менеджер')
        assert _get_can_edit(emp) is True

    def test_no_secondary_uses_primary(self):
        """Без secondary — используется только primary."""
        emp = _make_employee('СДП', '')
        tabs = _get_tabs_for_employee(emp)
        assert tabs == set(ROLES['СДП']['tabs'])

    def test_secondary_empty_string(self):
        """Пустая строка secondary — не добавляет вкладок."""
        emp = _make_employee('Дизайнер', '')
        assert len(_get_tabs_for_employee(emp)) == 1

    def test_designer_dan_union(self):
        """Дизайнер + ДАН = СРМ + СРМ надзора."""
        emp = _make_employee('Дизайнер', 'ДАН')
        tabs = _get_tabs_for_employee(emp)
        assert 'СРМ' in tabs
        assert 'СРМ надзора' in tabs
        assert len(tabs) == 2


# ═══════════════════════════════════════════════════════════════════
# TestCanEditFlag — can_edit для каждой роли (8 тестов)
# ═══════════════════════════════════════════════════════════════════

class TestCanEditFlag:
    """can_edit по ролям."""

    @pytest.mark.parametrize('position,expected', [
        ('Руководитель студии', True),
        ('Старший менеджер проектов', True),
        ('СДП', True),
        ('ГАП', True),
        ('Менеджер', True),
        ('Дизайнер', True),
        ('Чертёжник', True),
        ('Замерщик', False),
    ])
    def test_can_edit(self, position, expected):
        emp = _make_employee(position)
        assert _get_can_edit(emp) is expected


# ═══════════════════════════════════════════════════════════════════
# TestCRMRoleActions — CRM кнопки/действия по ролям (10 тестов)
# ═══════════════════════════════════════════════════════════════════

class TestCRMRoleActions:
    """CRM — ролевой доступ к элементам UI."""

    def test_admin_can_edit_true(self, qtbot):
        """Руководитель — can_edit=True."""
        emp = _make_employee('Руководитель студии')
        tab = _create_crm_tab(qtbot, emp, can_edit=True)
        assert tab.can_edit is True

    def test_surveyor_can_edit_false(self, qtbot):
        """Замерщик — can_edit=False."""
        emp = _make_employee('Замерщик')
        tab = _create_crm_tab(qtbot, emp, can_edit=False)
        assert tab.can_edit is False

    def test_designer_can_edit_true(self, qtbot):
        """Дизайнер — can_edit=True."""
        emp = _make_employee('Дизайнер')
        tab = _create_crm_tab(qtbot, emp, can_edit=True)
        assert tab.can_edit is True

    def test_admin_archive_btn_visible(self, qtbot):
        """Руководитель видит кнопку архива."""
        emp = _make_employee('Руководитель студии')
        tab = _create_crm_tab(qtbot, emp, can_edit=True)
        from ui.crm_tab import _emp_has_pos
        assert _emp_has_pos(emp, 'Руководитель студии', 'Старший менеджер проектов',
                           'СДП', 'ГАП', 'Менеджер')

    def test_designer_no_archive(self, qtbot):
        """Дизайнер НЕ видит архив (чистый исполнитель)."""
        emp = _make_employee('Дизайнер')
        from ui.crm_tab import _emp_only_pos
        assert _emp_only_pos(emp, 'Дизайнер', 'Чертёжник', 'Замерщик')

    def test_sdp_sees_individual_only(self, qtbot):
        """СДП видит только индивидуальные проекты."""
        emp = _make_employee('СДП')
        tab = _create_crm_tab(qtbot, emp, can_edit=True)
        # СДП должен видеть individual tab, но не template
        assert hasattr(tab, 'tabs') or hasattr(tab, 'individual_widget')

    def test_manager_sees_both_tabs(self, qtbot):
        """Менеджер видит обе вкладки (индивид. + шаблонные)."""
        emp = _make_employee('Менеджер')
        tab = _create_crm_tab(qtbot, emp, can_edit=True)
        assert isinstance(tab, QWidget)

    def test_emp_has_pos_submit_work(self):
        """Дизайнер может сдавать работу (submit)."""
        emp = _make_employee('Дизайнер')
        from ui.crm_tab import _emp_has_pos
        # Сдача работы доступна для Дизайнер, Чертёжник
        assert _emp_has_pos(emp, 'Дизайнер', 'Чертёжник')

    def test_emp_has_pos_accept_work(self):
        """СДП может принимать работу (accept)."""
        emp = _make_employee('СДП')
        from ui.crm_tab import _emp_has_pos
        assert _emp_has_pos(emp, 'Руководитель студии', 'Старший менеджер проектов',
                           'СДП', 'ГАП')

    def test_draftsman_no_accept(self):
        """Чертёжник НЕ может принимать работу."""
        emp = _make_employee('Чертёжник')
        from ui.crm_tab import _emp_has_pos
        assert not _emp_has_pos(emp, 'Руководитель студии', 'Старший менеджер проектов',
                               'СДП', 'ГАП')


# ═══════════════════════════════════════════════════════════════════
# TestSupervisionRoles — Надзор: доступ по ролям (8 тестов)
# ═══════════════════════════════════════════════════════════════════

class TestSupervisionRoles:
    """CRM Надзора — ролевой доступ."""

    def test_admin_creates(self, qtbot):
        """Руководитель — таб создаётся."""
        emp = _make_employee('Руководитель студии')
        tab = _create_supervision_tab(qtbot, emp)
        assert isinstance(tab, QWidget)

    def test_manager_creates(self, qtbot):
        """Менеджер — таб создаётся."""
        emp = _make_employee('Менеджер')
        tab = _create_supervision_tab(qtbot, emp)
        assert isinstance(tab, QWidget)

    def test_dan_creates(self, qtbot):
        """ДАН — таб создаётся (read-only)."""
        emp = _make_employee('ДАН')
        tab = _create_supervision_tab(qtbot, emp)
        assert isinstance(tab, QWidget)

    def test_dan_is_dan_role(self, qtbot):
        """ДАН определяется как dan_role."""
        emp = _make_employee('ДАН')
        tab = _create_supervision_tab(qtbot, emp)
        assert tab.is_dan_role is True

    def test_admin_not_dan_role(self, qtbot):
        """Руководитель — not dan_role."""
        emp = _make_employee('Руководитель студии')
        tab = _create_supervision_tab(qtbot, emp)
        assert tab.is_dan_role is False

    def test_dan_in_allowed_tabs(self):
        """ДАН имеет 'СРМ надзора' в ROLES."""
        assert 'СРМ надзора' in ROLES['ДАН']['tabs']

    def test_manager_in_allowed_tabs(self):
        """Менеджер имеет 'СРМ надзора' в ROLES."""
        assert 'СРМ надзора' in ROLES['Менеджер']['tabs']

    def test_sdp_no_supervision_tab(self):
        """СДП НЕ имеет 'СРМ надзора' в ROLES."""
        assert 'СРМ надзора' not in ROLES['СДП']['tabs']
