# -*- coding: utf-8 -*-
"""
Полное покрытие utils/db_security.py — ~20 тестов.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.db_security import (
    ALLOWED_FIELDS, validate_update_data, build_update_query,
    build_insert_query, sanitize_table_name
)


class TestAllowedFields:
    def test_clients_table_exists(self):
        assert 'clients' in ALLOWED_FIELDS

    def test_contracts_table_exists(self):
        assert 'contracts' in ALLOWED_FIELDS

    def test_employees_table_exists(self):
        assert 'employees' in ALLOWED_FIELDS

    def test_crm_cards_table_exists(self):
        assert 'crm_cards' in ALLOWED_FIELDS

    def test_supervision_cards_table_exists(self):
        assert 'supervision_cards' in ALLOWED_FIELDS


class TestValidateUpdateData:
    def test_filters_allowed_fields(self):
        data = {'full_name': 'Иван', 'phone': '+7...', 'hacker_field': 'DROP'}
        result = validate_update_data('clients', data)
        assert 'full_name' in result
        assert 'phone' in result
        assert 'hacker_field' not in result

    def test_unknown_table_raises(self):
        with pytest.raises(ValueError, match="не найдена"):
            validate_update_data('unknown_table', {'field': 'value'})

    def test_all_valid_fields_kept(self):
        data = {'client_type': 'Физическое лицо', 'full_name': 'Тест'}
        result = validate_update_data('clients', data)
        assert len(result) == 2

    def test_empty_data_returns_empty(self):
        result = validate_update_data('clients', {})
        assert result == {}

    def test_all_invalid_fields_filtered(self):
        data = {'evil1': 'a', 'evil2': 'b'}
        result = validate_update_data('clients', data)
        assert result == {}


class TestBuildUpdateQuery:
    def test_basic_update(self):
        query, values = build_update_query('clients', {'full_name': 'Иван'})
        assert 'UPDATE clients SET' in query
        assert 'full_name = ?' in query
        assert values == ['Иван']

    def test_multiple_fields(self):
        query, values = build_update_query('clients', {'full_name': 'Иван', 'phone': '+7...'})
        assert query.count('?') >= 2
        assert len(values) == 2

    def test_custom_where(self):
        query, values = build_update_query('clients', {'full_name': 'Тест'}, 'client_type = ?')
        assert 'WHERE client_type = ?' in query

    def test_empty_after_validation_raises(self):
        with pytest.raises(ValueError, match="Нет данных"):
            build_update_query('clients', {'evil_field': 'DROP'})


class TestBuildInsertQuery:
    def test_basic_insert(self):
        query, values = build_insert_query('clients', {'full_name': 'Тест', 'phone': '+7...'})
        assert 'INSERT INTO clients' in query
        assert 'VALUES' in query
        assert len(values) == 2

    def test_empty_after_validation_raises(self):
        with pytest.raises(ValueError, match="Нет данных"):
            build_insert_query('clients', {'evil_field': 'DROP'})


class TestSanitizeTableName:
    def test_valid_name(self):
        assert sanitize_table_name('clients') == 'clients'

    def test_sql_injection_blocked(self):
        with pytest.raises(ValueError, match="Недопустимое"):
            sanitize_table_name('clients; DROP TABLE employees')

    def test_unknown_table_blocked(self):
        with pytest.raises(ValueError, match="не разрешена"):
            sanitize_table_name('unknown_valid_name')

    def test_special_chars_blocked(self):
        with pytest.raises(ValueError):
            sanitize_table_name('table-name')
