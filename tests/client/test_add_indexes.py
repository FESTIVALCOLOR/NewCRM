# -*- coding: utf-8 -*-
"""
Тесты utils/add_indexes.py — добавление индексов в SQLite БД.

Покрытие:
  - TestAddDatabaseIndexes (8) — создание индексов
  - TestAnalyzeQueryPerformance (2) — анализ производительности
ИТОГО: 10 тестов
"""

import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def full_schema_db(tmp_path):
    """Создаёт SQLite БД с полной схемой таблиц для тестирования индексов."""
    db_path = str(tmp_path / 'test_indexes.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Создаём все таблицы, на которые ссылаются индексы
    cursor.execute('''
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            login TEXT,
            status TEXT,
            position TEXT,
            department TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY,
            phone TEXT,
            email TEXT,
            inn TEXT,
            client_type TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE contracts (
            id INTEGER PRIMARY KEY,
            client_id INTEGER,
            contract_number TEXT,
            status TEXT,
            contract_date TEXT,
            project_type TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE crm_cards (
            id INTEGER PRIMARY KEY,
            contract_id INTEGER,
            column_name TEXT,
            deadline TEXT,
            senior_manager_id INTEGER,
            sdp_id INTEGER,
            gap_id INTEGER,
            manager_id INTEGER,
            surveyor_id INTEGER,
            is_approved INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE supervision_cards (
            id INTEGER PRIMARY KEY,
            contract_id INTEGER,
            column_name TEXT,
            dan_id INTEGER,
            senior_manager_id INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE salaries (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER,
            contract_id INTEGER,
            report_month TEXT,
            payment_type TEXT
        )
    ''')

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def empty_db(tmp_path):
    """Пустая БД без таблиц."""
    db_path = str(tmp_path / 'empty.db')
    conn = sqlite3.connect(db_path)
    conn.close()
    return db_path


class TestAddDatabaseIndexes:
    """Тесты добавления индексов в базу данных."""

    def test_adds_indexes_successfully(self, full_schema_db):
        """Индексы создаются успешно, функция возвращает True."""
        from utils.add_indexes import add_database_indexes
        result = add_database_indexes(full_schema_db)
        assert result is True

    def test_indexes_exist_after_creation(self, full_schema_db):
        """После выполнения индексы видны в sqlite_master."""
        from utils.add_indexes import add_database_indexes
        add_database_indexes(full_schema_db)

        conn = sqlite3.connect(full_schema_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type = 'index' AND name LIKE 'idx_%'
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Проверяем ключевые индексы
        assert 'idx_employees_login' in indexes
        assert 'idx_clients_phone' in indexes
        assert 'idx_contracts_client_id' in indexes
        assert 'idx_crm_cards_contract_id' in indexes
        assert 'idx_salaries_employee_id' in indexes

    def test_composite_indexes_created(self, full_schema_db):
        """Составные индексы создаются."""
        from utils.add_indexes import add_database_indexes
        add_database_indexes(full_schema_db)

        conn = sqlite3.connect(full_schema_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type = 'index' AND name LIKE 'idx_%'
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert 'idx_crm_cards_contract_column' in indexes
        assert 'idx_salaries_employee_month' in indexes

    def test_idempotent_execution(self, full_schema_db):
        """Повторный вызов не вызывает ошибок (IF NOT EXISTS)."""
        from utils.add_indexes import add_database_indexes
        result1 = add_database_indexes(full_schema_db)
        result2 = add_database_indexes(full_schema_db)
        assert result1 is True
        assert result2 is True

    def test_nonexistent_db_returns_false(self):
        """Несуществующая БД — возвращает False."""
        from utils.add_indexes import add_database_indexes
        result = add_database_indexes('/nonexistent/path/db.sqlite')
        assert result is False

    def test_index_count(self, full_schema_db):
        """Создаётся ожидаемое количество индексов (32)."""
        from utils.add_indexes import add_database_indexes
        add_database_indexes(full_schema_db)

        conn = sqlite3.connect(full_schema_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'index' AND name LIKE 'idx_%'
        """)
        count = cursor.fetchone()[0]
        conn.close()

        # В коде определено 32 индекса
        assert count == 32

    def test_analyze_runs_after_indexes(self, full_schema_db):
        """ANALYZE выполняется после создания индексов."""
        from utils.add_indexes import add_database_indexes

        # Проверяем что вызов не падает и функция завершается успешно
        result = add_database_indexes(full_schema_db)
        assert result is True

    def test_handles_missing_tables_gracefully(self, empty_db):
        """БД без таблиц — индексы не создаются, но ошибки обрабатываются."""
        from utils.add_indexes import add_database_indexes
        # Индексы ссылаются на несуществующие таблицы — каждый выведет ошибку,
        # но функция всё равно вернёт True (ошибки обрабатываются в цикле)
        result = add_database_indexes(empty_db)
        assert result is True


class TestAnalyzeQueryPerformance:
    """Тесты анализа производительности запросов."""

    def test_analyze_existing_db(self, full_schema_db):
        """Анализ производительности на существующей БД не вызывает ошибок."""
        from utils.add_indexes import analyze_query_performance
        # Не должно бросить исключений
        analyze_query_performance(full_schema_db)

    def test_analyze_nonexistent_db(self):
        """Анализ несуществующей БД — корректное завершение."""
        from utils.add_indexes import analyze_query_performance
        # Не должно бросить исключений
        analyze_query_performance('/nonexistent/db.sqlite')
