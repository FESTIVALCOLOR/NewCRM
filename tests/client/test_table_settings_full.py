# -*- coding: utf-8 -*-
"""
Покрытие utils/table_settings.py — TableSettings класс.
~20 тестов.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture
def mock_qsettings():
    """Мок QSettings с хранилищем в памяти."""
    storage = {}

    class FakeQSettings:
        def __init__(self, *args):
            self._group_prefix = ''

        def setValue(self, key, value):
            full_key = f"{self._group_prefix}{key}" if self._group_prefix else key
            storage[full_key] = value

        def value(self, key, default=None):
            full_key = f"{self._group_prefix}{key}" if self._group_prefix else key
            return storage.get(full_key, default)

        def beginGroup(self, group):
            self._group_prefix = f"{group}/"

        def endGroup(self):
            self._group_prefix = ''

        def childKeys(self):
            prefix = self._group_prefix
            return [k[len(prefix):] for k in storage if k.startswith(prefix) and '/' not in k[len(prefix):]]

    return FakeQSettings, storage


@pytest.fixture
def ts(mock_qsettings):
    """Создать TableSettings с мок QSettings."""
    fake_class, _ = mock_qsettings
    with patch('utils.table_settings.QSettings', fake_class):
        from utils.table_settings import TableSettings
        return TableSettings()


# ==================== SORT ORDER ====================

class TestSaveSortOrder:
    def test_saves_column_and_order(self, ts, mock_qsettings):
        _, storage = mock_qsettings
        ts.save_sort_order('clients', 2, 1)
        assert storage['clients/sort_column'] == 2
        assert storage['clients/sort_order'] == 1

    def test_different_tables(self, ts, mock_qsettings):
        _, storage = mock_qsettings
        ts.save_sort_order('clients', 0, 0)
        ts.save_sort_order('contracts', 3, 1)
        assert storage['clients/sort_column'] == 0
        assert storage['contracts/sort_column'] == 3


class TestGetSortOrder:
    def test_returns_saved_values(self, ts):
        ts.save_sort_order('employees', 1, 0)
        col, order = ts.get_sort_order('employees')
        assert col == 1
        assert order == 0

    def test_returns_none_for_missing(self, ts):
        col, order = ts.get_sort_order('nonexistent_table')
        assert col is None
        assert order is None

    def test_converts_to_int(self, ts, mock_qsettings):
        _, storage = mock_qsettings
        # QSettings часто возвращает строки
        storage['salaries/sort_column'] = '5'
        storage['salaries/sort_order'] = '1'
        col, order = ts.get_sort_order('salaries')
        assert col == 5
        assert order == 1
        assert isinstance(col, int)
        assert isinstance(order, int)


# ==================== COLUMN COLLAPSED STATE ====================

class TestSaveColumnCollapsedState:
    def test_saves_collapsed_true(self, ts, mock_qsettings):
        _, storage = mock_qsettings
        ts.save_column_collapsed_state('crm_individual', 'Замер', True)
        assert storage['columns/crm_individual/Замер'] is True

    def test_saves_collapsed_false(self, ts, mock_qsettings):
        _, storage = mock_qsettings
        ts.save_column_collapsed_state('crm_template', 'Эскиз', False)
        assert storage['columns/crm_template/Эскиз'] is False

    def test_normalizes_key_with_special_chars(self, ts, mock_qsettings):
        _, storage = mock_qsettings
        ts.save_column_collapsed_state('crm', 'Стадия: Замер (этап 1)', True)
        assert storage['columns/crm/Стадия__Замер_этап_1'] is True


class TestGetColumnCollapsedState:
    def test_returns_saved_value(self, ts):
        ts.save_column_collapsed_state('crm', 'Замер', True)
        result = ts.get_column_collapsed_state('crm', 'Замер')
        assert result is True

    def test_returns_default_when_missing(self, ts):
        result = ts.get_column_collapsed_state('crm', 'NonExistent', default=None)
        assert result is None

    def test_returns_explicit_default(self, ts):
        result = ts.get_column_collapsed_state('crm', 'Missing', default=False)
        assert result is False

    def test_converts_string_true(self, ts, mock_qsettings):
        _, storage = mock_qsettings
        storage['columns/crm/Test'] = 'true'
        result = ts.get_column_collapsed_state('crm', 'Test')
        assert result is True

    def test_converts_string_false(self, ts, mock_qsettings):
        _, storage = mock_qsettings
        storage['columns/crm/Test'] = 'false'
        result = ts.get_column_collapsed_state('crm', 'Test')
        assert result is False


class TestGetAllCollapsedColumns:
    def test_returns_all_saved(self, ts):
        ts.save_column_collapsed_state('board1', 'ColA', True)
        ts.save_column_collapsed_state('board1', 'ColB', False)
        result = ts.get_all_collapsed_columns('board1')
        assert 'ColA' in result
        assert 'ColB' in result
        assert result['ColA'] is True
        assert result['ColB'] is False

    def test_empty_board_returns_empty(self, ts):
        result = ts.get_all_collapsed_columns('empty_board')
        assert result == {}

    def test_different_boards_isolated(self, ts):
        ts.save_column_collapsed_state('board1', 'Col1', True)
        ts.save_column_collapsed_state('board2', 'Col2', False)
        r1 = ts.get_all_collapsed_columns('board1')
        r2 = ts.get_all_collapsed_columns('board2')
        assert 'Col1' in r1
        assert 'Col2' not in r1
        assert 'Col2' in r2
        assert 'Col1' not in r2

    def test_handles_string_values(self, ts, mock_qsettings):
        _, storage = mock_qsettings
        storage['columns/myboard/Тест'] = 'true'
        result = ts.get_all_collapsed_columns('myboard')
        assert result.get('Тест') is True
