# -*- coding: utf-8 -*-
"""
Тесты для CRMSupervisionTab — Kanban доска авторского надзора.

Проверяется создание виджета, наличие колонок Kanban, вкладки активные/архив,
карточки надзора, фильтры, права ДАН-роли, переключение вкладок.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import (QApplication, QTabWidget, QLabel, QPushButton,
                              QScrollArea, QFrame)
from PyQt5.QtCore import Qt
from unittest.mock import patch, MagicMock


# ========== Список колонок Kanban ==========

SUPERVISION_COLUMNS = [
    'Новый заказ',
    'В ожидании',
    'Стадия 1: Закупка керамогранита',
    'Стадия 2: Закупка сантехники',
    'Стадия 3: Закупка оборудования',
    'Стадия 4: Закупка дверей и окон',
    'Стадия 5: Закупка настенных материалов',
    'Стадия 6: Закупка напольных материалов',
    'Стадия 7: Лепной декор',
    'Стадия 8: Освещение',
    'Стадия 9: Бытовая техника',
    'Стадия 10: Закупка заказной мебели',
    'Стадия 11: Закупка фабричной мебели',
    'Стадия 12: Закупка декора',
    'Выполненный проект'
]


# ========== Вспомогательные функции ==========

def _make_mock_data_access(active_cards=None, archived_cards=None):
    """Создать MagicMock DataAccess для CRMSupervisionTab."""
    mock_da = MagicMock()
    mock_da.get_supervision_cards_active.return_value = active_cards or []
    mock_da.get_supervision_cards_archived.return_value = archived_cards or []
    mock_da.get_supervision_history.return_value = []
    mock_da.get_supervision_timeline.return_value = []
    mock_da.get_all_employees.return_value = []
    mock_da.get_all_contracts.return_value = []
    mock_da.db = MagicMock()
    mock_da.is_online = False
    mock_da.prefer_local = False
    return mock_da


def _create_supervision_tab(qtbot, employee, active_cards=None, archived_cards=None):
    """Создать CRMSupervisionTab с замоканными зависимостями."""
    mock_da = _make_mock_data_access(
        active_cards=active_cards,
        archived_cards=archived_cards
    )
    with patch('ui.crm_supervision_tab.DataAccess', return_value=mock_da), \
         patch('ui.crm_supervision_tab.IconLoader') as mock_icon, \
         patch('ui.crm_supervision_tab.YandexDiskManager'), \
         patch('ui.crm_supervision_tab._has_perm', return_value=True), \
         patch('ui.crm_supervision_tab.debounce_click', side_effect=lambda fn: fn):
        mock_icon.load.return_value = MagicMock()
        mock_icon.create_action_button.return_value = QPushButton()
        mock_icon.create_icon_button.return_value = QPushButton()
        from ui.crm_supervision_tab import CRMSupervisionTab
        tab = CRMSupervisionTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab, mock_da


# ========== Тестовые данные ==========

SAMPLE_SUPERVISION_CARD = {
    'id': 1, 'contract_id': 100,
    'contract_number': 'АН-12345/26',
    'client_name': 'Иванов И.И.',
    'address': 'ул. Тестовая, д.1',
    'city': 'СПБ', 'area': 85.5,
    'column_name': 'Новый заказ',
    'dan_id': 9, 'dan_name': 'ДАН Тестов',
    'agent_type': '', 'status': 'active',
    'created_at': '2026-01-15'
}

SAMPLE_SUPERVISION_CARDS = [
    SAMPLE_SUPERVISION_CARD,
    {
        'id': 2, 'contract_id': 101,
        'contract_number': 'АН-12346/26',
        'client_name': 'Петров П.П.',
        'address': 'ул. Другая, д.5',
        'city': 'МСК', 'area': 120,
        'column_name': 'Стадия 1: Закупка керамогранита',
        'dan_id': 9, 'dan_name': 'ДАН Тестов',
        'agent_type': 'Петрович', 'status': 'active',
        'created_at': '2026-02-01'
    },
    {
        'id': 3, 'contract_id': 102,
        'contract_number': 'АН-12347/26',
        'client_name': 'Сидоров С.С.',
        'address': 'пр. Невский, д.10',
        'city': 'СПБ', 'area': 200,
        'column_name': 'Выполненный проект',
        'dan_id': 1, 'dan_name': 'Тестов Админ',
        'agent_type': '', 'status': 'active',
        'created_at': '2025-12-20'
    },
]


class TestSupervisionTabCreation:
    """Тесты создания и инициализации CRMSupervisionTab."""

    def test_create_widget(self, qtbot, mock_employee_admin):
        """CRMSupervisionTab создаётся без ошибок."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert tab is not None

    def test_widget_is_visible(self, qtbot, mock_employee_admin):
        """CRMSupervisionTab видим после show()."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        tab.show()
        assert tab.isVisible()

    def test_employee_stored(self, qtbot, mock_employee_admin):
        """Атрибут employee сохраняет данные текущего пользователя."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert tab.employee == mock_employee_admin

    def test_data_access_initialized(self, qtbot, mock_employee_admin):
        """DataAccess инициализирован."""
        tab, mock_da = _create_supervision_tab(qtbot, mock_employee_admin)
        assert tab.data is mock_da

    def test_admin_not_dan_role(self, qtbot, mock_employee_admin):
        """Руководитель студии НЕ является ДАН-ролью."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert tab.is_dan_role is False

    def test_dan_role_detected(self, qtbot, mock_employee_dan):
        """Сотрудник с должностью ДАН определяется как is_dan_role."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_dan)
        assert tab.is_dan_role is True


class TestSupervisionTabTabs:
    """Тесты вкладок Активные / Архив."""

    def test_has_tabs_widget(self, qtbot, mock_employee_admin):
        """CRMSupervisionTab содержит QTabWidget."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'tabs')
        assert isinstance(tab.tabs, QTabWidget)

    def test_admin_has_two_tabs(self, qtbot, mock_employee_admin):
        """Руководитель видит 2 вкладки: Активные и Архив."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert tab.tabs.count() == 2

    def test_dan_has_one_tab(self, qtbot, mock_employee_dan):
        """ДАН видит только 1 вкладку (без Архива)."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_dan)
        assert tab.tabs.count() == 1

    def test_active_tab_name(self, qtbot, mock_employee_admin):
        """Первая вкладка содержит 'Активные проекты'."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert 'Активные проекты' in tab.tabs.tabText(0)

    def test_archive_tab_name(self, qtbot, mock_employee_admin):
        """Вторая вкладка содержит 'Архив'."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert 'Архив' in tab.tabs.tabText(1)

    def test_default_tab_is_active(self, qtbot, mock_employee_admin):
        """По умолчанию выбрана вкладка 'Активные проекты'."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert tab.tabs.currentIndex() == 0


class TestSupervisionTabKanbanColumns:
    """Тесты Kanban-колонок доски надзора."""

    def test_has_active_widget(self, qtbot, mock_employee_admin):
        """Наличие виджета активной доски."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'active_widget')

    def test_active_widget_has_columns(self, qtbot, mock_employee_admin):
        """Активная доска содержит словарь колонок."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert hasattr(tab.active_widget, 'columns')
        assert isinstance(tab.active_widget.columns, dict)

    def test_columns_count(self, qtbot, mock_employee_admin):
        """Должно быть 15 колонок (Новый заказ + В ожидании + 12 стадий + Выполненный проект)."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert len(tab.active_widget.columns) == 15

    def test_all_column_names_present(self, qtbot, mock_employee_admin):
        """Все ожидаемые названия колонок присутствуют."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        columns = tab.active_widget.columns
        for col_name in SUPERVISION_COLUMNS:
            assert col_name in columns, f"Колонка '{col_name}' не найдена"

    def test_column_new_order_exists(self, qtbot, mock_employee_admin):
        """Колонка 'Новый заказ' существует."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert 'Новый заказ' in tab.active_widget.columns

    def test_column_completed_exists(self, qtbot, mock_employee_admin):
        """Колонка 'Выполненный проект' существует."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert 'Выполненный проект' in tab.active_widget.columns

    def test_columns_are_qframe(self, qtbot, mock_employee_admin):
        """Каждая колонка является наследником QFrame."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        for col_name, column in tab.active_widget.columns.items():
            assert isinstance(column, QFrame), \
                f"Колонка '{col_name}' не является QFrame"

    def test_columns_have_header_label(self, qtbot, mock_employee_admin):
        """Каждая колонка имеет header_label."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        for col_name, column in tab.active_widget.columns.items():
            assert hasattr(column, 'header_label'), \
                f"Колонка '{col_name}' не имеет header_label"

    def test_columns_have_cards_list(self, qtbot, mock_employee_admin):
        """Каждая колонка имеет cards_list (QListWidget)."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        for col_name, column in tab.active_widget.columns.items():
            assert hasattr(column, 'cards_list'), \
                f"Колонка '{col_name}' не имеет cards_list"

    def test_empty_columns_on_init(self, qtbot, mock_employee_admin):
        """При пустых данных все колонки содержат 0 карточек."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        for col_name, column in tab.active_widget.columns.items():
            assert column.cards_list.count() == 0, \
                f"Колонка '{col_name}' не пуста при инициализации"


class TestSupervisionTabArchive:
    """Тесты архивной доски."""

    def test_admin_has_archive_widget(self, qtbot, mock_employee_admin):
        """У администратора есть виджет архива."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'archive_widget')

    def test_dan_no_archive_widget(self, qtbot, mock_employee_dan):
        """У ДАН нет виджета архива."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_dan)
        assert not hasattr(tab, 'archive_widget')

    def test_switch_to_archive_tab(self, qtbot, mock_employee_admin):
        """Переключение на вкладку Архив."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        tab.tabs.setCurrentIndex(1)
        assert tab.tabs.currentIndex() == 1


class TestSupervisionTabCounters:
    """Тесты обновления счётчиков вкладок."""

    def test_update_tab_counters(self, qtbot, mock_employee_admin):
        """update_tab_counters обновляет текст вкладок."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        tab.update_tab_counters()
        # После обновления текст должен содержать число
        assert '(0)' in tab.tabs.tabText(0)

    def test_active_tab_counter_text(self, qtbot, mock_employee_admin):
        """Вкладка активных проектов содержит счётчик."""
        tab, _ = _create_supervision_tab(qtbot, mock_employee_admin)
        tab_text = tab.tabs.tabText(0)
        assert 'Активные проекты' in tab_text
        assert '(' in tab_text and ')' in tab_text
