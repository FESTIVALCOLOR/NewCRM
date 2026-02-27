# -*- coding: utf-8 -*-
"""
Тесты для utils/table_settings.py — TableSettings, ProportionalResizeTable.

Этап 9: Мелкие модули и gaps.
PyQt5 замокан — тесты запускаются в CI без GUI.
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock, call

import pytest

# Мокаем PyQt5 ДО импорта
_qt_core_mock = MagicMock()
_qt_widgets_mock = MagicMock()
_qt_gui_mock = MagicMock()

# Сохраняем оригинальные модули PyQt5 перед мокированием
_pyqt5_keys = ['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui']
_saved_pyqt5 = {k: sys.modules[k] for k in _pyqt5_keys if k in sys.modules}

sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtCore'] = _qt_core_mock
sys.modules['PyQt5.QtWidgets'] = _qt_widgets_mock
sys.modules['PyQt5.QtGui'] = _qt_gui_mock

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.table_settings import TableSettings

# Восстанавливаем оригинальные модули — импорт уже закеширован,
# а остальные тесты в сессии получат настоящий PyQt5
for _k in _pyqt5_keys:
    if _k in _saved_pyqt5:
        sys.modules[_k] = _saved_pyqt5[_k]
    elif _k in sys.modules:
        del sys.modules[_k]


# ============================================================================
# ХЕЛПЕРЫ
# ============================================================================

@pytest.fixture
def mock_qsettings():
    """Mock QSettings с внутренним хранилищем"""
    store = {}
    group_prefix = ""

    qs = MagicMock()

    def set_value(key, value):
        full_key = f"{group_prefix}/{key}" if group_prefix else key
        store[full_key] = value

    def get_value(key, default=None):
        full_key = f"{group_prefix}/{key}" if group_prefix else key
        return store.get(full_key, default)

    def begin_group(group):
        nonlocal group_prefix
        group_prefix = group

    def end_group():
        nonlocal group_prefix
        group_prefix = ""

    def child_keys():
        prefix = group_prefix + "/"
        return [k.split(prefix, 1)[1] for k in store if k.startswith(prefix)]

    qs.setValue = MagicMock(side_effect=set_value)
    qs.value = MagicMock(side_effect=get_value)
    qs.beginGroup = MagicMock(side_effect=begin_group)
    qs.endGroup = MagicMock(side_effect=end_group)
    qs.childKeys = MagicMock(side_effect=child_keys)

    return qs, store


@pytest.fixture
def table_settings(mock_qsettings):
    """TableSettings с замоканным QSettings"""
    qs, store = mock_qsettings
    ts = TableSettings()
    ts.settings = qs
    return ts, store


# ============================================================================
# SAVE / GET SORT ORDER
# ============================================================================

class TestSortOrder:
    """save_sort_order / get_sort_order"""

    def test_save_sort_order(self, table_settings):
        """save_sort_order — сохраняет column и order."""
        ts, store = table_settings
        ts.save_sort_order('clients', 2, 1)
        assert store['clients/sort_column'] == 2
        assert store['clients/sort_order'] == 1

    def test_get_sort_order(self, table_settings):
        """get_sort_order — возвращает сохранённые значения."""
        ts, store = table_settings
        store['contracts/sort_column'] = 3
        store['contracts/sort_order'] = 0

        column, order = ts.get_sort_order('contracts')
        assert column == 3
        assert order == 0

    def test_get_sort_order_default(self, table_settings):
        """get_sort_order — (None, None) если нет настроек."""
        ts, store = table_settings
        column, order = ts.get_sort_order('nonexistent')
        assert column is None
        assert order is None

    def test_save_and_get_multiple_tables(self, table_settings):
        """save/get — разные таблицы не конфликтуют."""
        ts, store = table_settings
        ts.save_sort_order('clients', 1, 0)
        ts.save_sort_order('contracts', 3, 1)

        c1, o1 = ts.get_sort_order('clients')
        c2, o2 = ts.get_sort_order('contracts')
        assert (c1, o1) == (1, 0)
        assert (c2, o2) == (3, 1)

    def test_overwrite_sort_order(self, table_settings):
        """save_sort_order — перезаписывает предыдущие настройки."""
        ts, store = table_settings
        ts.save_sort_order('clients', 1, 0)
        ts.save_sort_order('clients', 5, 1)

        column, order = ts.get_sort_order('clients')
        assert column == 5
        assert order == 1


# ============================================================================
# COLUMN COLLAPSED STATE
# ============================================================================

class TestColumnCollapsedState:
    """save_column_collapsed_state / get_column_collapsed_state"""

    def test_save_collapsed_state(self, table_settings):
        """save_column_collapsed_state — сохраняет состояние."""
        ts, store = table_settings
        ts.save_column_collapsed_state('crm_individual', 'Новый заказ', True)
        key = 'columns/crm_individual/Новый_заказ'
        assert store[key] is True

    def test_get_collapsed_state_true(self, table_settings):
        """get_column_collapsed_state — True."""
        ts, store = table_settings
        store['columns/crm_individual/Новый_заказ'] = 'true'
        result = ts.get_column_collapsed_state('crm_individual', 'Новый заказ')
        assert result is True

    def test_get_collapsed_state_false(self, table_settings):
        """get_column_collapsed_state — False."""
        ts, store = table_settings
        store['columns/crm_individual/Новый_заказ'] = 'false'
        result = ts.get_column_collapsed_state('crm_individual', 'Новый заказ')
        assert result is False

    def test_get_collapsed_state_not_found(self, table_settings):
        """get_column_collapsed_state — не найдено → default."""
        ts, store = table_settings
        result = ts.get_column_collapsed_state('crm_individual', 'Несуществующая', default=None)
        assert result is None

    def test_get_collapsed_state_default_value(self, table_settings):
        """get_column_collapsed_state — не найдено → переданный default."""
        ts, store = table_settings
        result = ts.get_column_collapsed_state('board', 'col', default=True)
        assert result is True

    def test_special_chars_normalized(self, table_settings):
        """save_column_collapsed_state — спецсимволы нормализуются в ключе."""
        ts, store = table_settings
        # Колонка с двоеточием, пробелами и скобками
        ts.save_column_collapsed_state('crm_supervision', 'Замер: проведен (ожидание)', True)
        # Ключ должен быть нормализован
        expected_key = 'columns/crm_supervision/Замер__проведен_ожидание'
        assert expected_key in store


# ============================================================================
# GET ALL COLLAPSED COLUMNS
# ============================================================================

class TestGetAllCollapsedColumns:
    """get_all_collapsed_columns"""

    def test_get_all_collapsed_columns(self, table_settings):
        """get_all_collapsed_columns — возвращает dict."""
        ts, store = table_settings
        store['columns/crm_individual/col1'] = 'true'
        store['columns/crm_individual/col2'] = 'false'

        result = ts.get_all_collapsed_columns('crm_individual')
        assert isinstance(result, dict)
        assert result.get('col1') is True
        assert result.get('col2') is False

    def test_get_all_collapsed_columns_empty(self, table_settings):
        """get_all_collapsed_columns — пустой результат если нет настроек."""
        ts, store = table_settings
        result = ts.get_all_collapsed_columns('nonexistent_board')
        assert result == {}

    def test_get_all_collapsed_calls_begin_end_group(self, table_settings):
        """get_all_collapsed_columns — вызывает beginGroup/endGroup."""
        ts, store = table_settings
        ts.get_all_collapsed_columns('crm_template')
        ts.settings.beginGroup.assert_called_with('columns/crm_template')
        ts.settings.endGroup.assert_called()
