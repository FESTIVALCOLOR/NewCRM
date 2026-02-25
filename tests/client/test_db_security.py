# -*- coding: utf-8 -*-
"""
Unit-тесты для utils/db_security.py
Проверяет функции валидации и построения SQL-запросов.
"""
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from utils.db_security import (
    validate_update_data,
    build_update_query,
    build_insert_query,
    sanitize_table_name,
    ALLOWED_FIELDS,
)


# ========== Тесты validate_update_data ==========

class TestValidateUpdateData:
    """Тесты функции валидации данных для UPDATE."""

    def test_valid_fields_pass_through(self):
        """Разрешённые поля проходят валидацию без изменений."""
        data = {'full_name': 'Иван Иванов', 'phone': '+7 (999) 123-45-67'}
        result = validate_update_data('clients', data)
        assert 'full_name' in result
        assert 'phone' in result

    def test_malicious_field_is_filtered(self):
        """Неразрешённые поля (инъекции) фильтруются."""
        data = {
            'full_name': 'Иван',
            'DROP TABLE clients': 'evil',
            'malicious_field': 'danger'
        }
        result = validate_update_data('clients', data)
        assert 'full_name' in result
        assert 'DROP TABLE clients' not in result
        assert 'malicious_field' not in result

    def test_unknown_table_raises_value_error(self):
        """Неизвестная таблица вызывает ValueError."""
        with pytest.raises(ValueError, match="не найдена в whitelist"):
            validate_update_data('unknown_table', {'field': 'value'})

    def test_empty_data_returns_empty_dict(self):
        """Пустой словарь данных возвращает пустой словарь."""
        result = validate_update_data('clients', {})
        assert result == {}

    def test_all_tables_in_whitelist(self):
        """Все таблицы из ALLOWED_FIELDS доступны."""
        for table in ALLOWED_FIELDS:
            # Не должно вызывать ValueError
            result = validate_update_data(table, {})
            assert isinstance(result, dict)

    def test_partial_valid_fields(self):
        """Только допустимые поля проходят, остальные отфильтрованы."""
        data = {'full_name': 'Test', 'evil': 'DROP'}
        result = validate_update_data('employees', data)
        assert result == {'full_name': 'Test'}

    def test_employees_allowed_fields(self):
        """Поля таблицы employees доступны."""
        data = {'full_name': 'Тест', 'email': 'test@test.com', 'role': 'admin'}
        result = validate_update_data('employees', data)
        assert len(result) == 3

    def test_contracts_allowed_fields(self):
        """Поля таблицы contracts доступны."""
        data = {'city': 'СПБ', 'area': 50.0, 'status': 'active'}
        result = validate_update_data('contracts', data)
        assert len(result) == 3


# ========== Тесты build_update_query ==========

class TestBuildUpdateQuery:
    """Тесты функции построения UPDATE запроса."""

    def test_basic_update_query_structure(self):
        """Базовая структура UPDATE запроса корректна."""
        query, values = build_update_query('clients', {'full_name': 'Иван', 'phone': '+7...'})
        assert 'UPDATE clients SET' in query
        assert 'WHERE id = ?' in query
        assert '?' in query

    def test_values_match_data(self):
        """Значения соответствуют переданным данным."""
        query, values = build_update_query('clients', {'full_name': 'Иван'})
        assert 'Иван' in values

    def test_empty_data_raises_value_error(self):
        """Пустые данные (нет допустимых полей) вызывают ValueError."""
        with pytest.raises(ValueError):
            build_update_query('clients', {})

    def test_malicious_fields_filtered_from_query(self):
        """Вредоносные поля не попадают в запрос."""
        with pytest.raises(ValueError):
            # Все поля вредоносные — ни одного не осталось после фильтрации
            build_update_query('clients', {'evil_field': 'DROP TABLE'})

    def test_custom_where_clause(self):
        """Кастомный WHERE clause используется."""
        query, values = build_update_query(
            'clients', {'full_name': 'Тест'}, where_clause="client_id = ?"
        )
        assert 'WHERE client_id = ?' in query

    def test_multiple_fields_in_set(self):
        """Несколько полей корректно включаются в SET."""
        query, values = build_update_query(
            'employees', {'full_name': 'Тест', 'email': 'test@test.com'}
        )
        assert 'full_name = ?' in query
        assert 'email = ?' in query
        assert len(values) == 2


# ========== Тесты build_insert_query ==========

class TestBuildInsertQuery:
    """Тесты функции построения INSERT запроса."""

    def test_basic_insert_query_structure(self):
        """Базовая структура INSERT запроса корректна."""
        query, values = build_insert_query('clients', {
            'client_type': 'Физическое лицо',
            'full_name': 'Иван'
        })
        assert 'INSERT INTO clients' in query
        assert 'VALUES' in query
        assert '?' in query

    def test_columns_in_query(self):
        """Столбцы присутствуют в запросе."""
        query, values = build_insert_query('clients', {'full_name': 'Тест'})
        assert 'full_name' in query

    def test_values_count_matches_columns(self):
        """Количество значений соответствует количеству столбцов."""
        data = {'full_name': 'Тест', 'phone': '+7...', 'email': 'a@b.com'}
        query, values = build_insert_query('clients', data)
        # Подсчитываем плейсхолдеры
        assert query.count('?') == len(values)

    def test_empty_data_raises_value_error(self):
        """Пустые данные вызывают ValueError."""
        with pytest.raises(ValueError):
            build_insert_query('clients', {})

    def test_malicious_fields_filtered(self):
        """Вредоносные поля не попадают в INSERT запрос."""
        with pytest.raises(ValueError):
            build_insert_query('clients', {'; DROP TABLE': 'evil'})


# ========== Тесты sanitize_table_name ==========

class TestSanitizeTableName:
    """Тесты функции санитизации имени таблицы."""

    def test_valid_table_name_passes(self):
        """Допустимое имя таблицы из whitelist проходит."""
        result = sanitize_table_name('clients')
        assert result == 'clients'

    def test_sql_injection_raises(self):
        """SQL-инъекция в имени таблицы блокируется."""
        with pytest.raises(ValueError):
            sanitize_table_name("clients; DROP TABLE employees")

    def test_space_in_name_raises(self):
        """Пробел в имени таблицы блокируется."""
        with pytest.raises(ValueError):
            sanitize_table_name("my table")

    def test_unknown_table_raises(self):
        """Неизвестная таблица (не в whitelist) блокируется."""
        with pytest.raises(ValueError):
            sanitize_table_name('unknown_valid_name')

    def test_all_whitelisted_tables_pass(self):
        """Все таблицы из whitelist проходят санитизацию."""
        for table in ALLOWED_FIELDS:
            result = sanitize_table_name(table)
            assert result == table

    def test_semicolon_injection_raises(self):
        """Точка с запятой в имени таблицы блокируется."""
        with pytest.raises(ValueError):
            sanitize_table_name("employees;")

    def test_dash_in_name_raises(self):
        """Дефис в имени таблицы блокируется (не допустимый символ)."""
        with pytest.raises(ValueError):
            sanitize_table_name("my-table")
