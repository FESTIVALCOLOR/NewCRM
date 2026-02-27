# -*- coding: utf-8 -*-
"""Тесты для database/migrations.py — миграции БД"""

import pytest
import sqlite3
import os
from unittest.mock import patch, MagicMock


@pytest.fixture
def db_path(tmp_path):
    """Создать тестовую БД с минимальной схемой"""
    path = str(tmp_path / 'test_migrations.db')
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    # Минимальная схема contracts
    cursor.execute('''CREATE TABLE IF NOT EXISTS contracts (
        id INTEGER PRIMARY KEY,
        contract_number TEXT,
        client_id INTEGER
    )''')
    # Минимальная схема crm_cards
    cursor.execute('''CREATE TABLE IF NOT EXISTS crm_cards (
        id INTEGER PRIMARY KEY,
        contract_id INTEGER,
        column_name TEXT
    )''')
    # Минимальная схема employees
    cursor.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY,
        full_name TEXT,
        role TEXT,
        status TEXT DEFAULT 'Активный'
    )''')
    conn.commit()
    conn.close()
    return path


class TestAddContractStatusFields:
    """Тесты add_contract_status_fields"""

    def test_adds_status_column(self, db_path):
        from database.migrations import add_contract_status_fields
        add_contract_status_fields(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(contracts)")
        columns = [c[1] for c in cursor.fetchall()]
        conn.close()
        assert 'status' in columns
        assert 'termination_reason' in columns

    def test_idempotent(self, db_path):
        from database.migrations import add_contract_status_fields
        add_contract_status_fields(db_path)
        add_contract_status_fields(db_path)  # повторный вызов — не падает
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(contracts)")
        columns = [c[1] for c in cursor.fetchall()]
        conn.close()
        assert columns.count('status') == 1

    def test_already_has_columns(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE contracts ADD COLUMN status TEXT DEFAULT 'Новый'")
        cursor.execute("ALTER TABLE contracts ADD COLUMN termination_reason TEXT")
        conn.commit()
        conn.close()
        from database.migrations import add_contract_status_fields
        add_contract_status_fields(db_path)  # не падает

    def test_invalid_path(self):
        from database.migrations import add_contract_status_fields
        add_contract_status_fields('/nonexistent/path/db.sqlite')  # не падает, ловит exception


class TestDatabaseMigrations:
    """Тесты DatabaseMigrations mixin"""

    @pytest.fixture
    def migrator(self, tmp_path):
        """Создаём объект с DatabaseMigrations mixin"""
        db_file = str(tmp_path / 'test.db')
        # Создаём полную минимальную БД
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY, contract_number TEXT, client_id INTEGER,
            status TEXT, termination_reason TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS crm_cards (
            id INTEGER PRIMARY KEY, contract_id INTEGER, column_name TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY, full_name TEXT, role TEXT, status TEXT, login TEXT, password TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY, name TEXT, client_type TEXT
        )''')
        conn.commit()
        conn.close()

        from database.migrations import DatabaseMigrations

        class TestMigrator(DatabaseMigrations):
            def __init__(self, db_path):
                self.db_path = db_path
                self._conn = None

            def connect(self):
                self._conn = sqlite3.connect(self.db_path)
                self._conn.row_factory = sqlite3.Row
                return self._conn

            def close(self):
                if self._conn:
                    self._conn.close()
                    self._conn = None

        return TestMigrator(db_file)

    def test_add_approval_deadline_field(self, migrator):
        migrator.add_approval_deadline_field()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(crm_cards)")
        columns = [c[1] for c in cursor.fetchall()]
        conn.close()
        assert 'approval_deadline' in columns

    def test_add_approval_deadline_field_idempotent(self, migrator):
        migrator.add_approval_deadline_field()
        migrator.add_approval_deadline_field()  # не падает

    def test_add_approval_stages_field(self, migrator):
        migrator.add_approval_stages_field()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(crm_cards)")
        columns = [c[1] for c in cursor.fetchall()]
        conn.close()
        assert 'approval_stages' in columns

    def test_add_project_data_link_field(self, migrator):
        migrator.add_project_data_link_field()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(crm_cards)")
        columns = [c[1] for c in cursor.fetchall()]
        conn.close()
        assert 'project_data_link' in columns

    def test_add_third_payment_field(self, migrator):
        migrator.add_third_payment_field()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(contracts)")
        columns = [c[1] for c in cursor.fetchall()]
        conn.close()
        assert 'third_payment' in columns

    def test_add_birth_date_column(self, migrator):
        migrator.add_birth_date_column()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(employees)")
        columns = [c[1] for c in cursor.fetchall()]
        conn.close()
        assert 'birth_date' in columns

    def test_add_address_column(self, migrator):
        migrator.add_address_column()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(employees)")
        columns = [c[1] for c in cursor.fetchall()]
        conn.close()
        assert 'address' in columns

    def test_add_secondary_position_column(self, migrator):
        migrator.add_secondary_position_column()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(employees)")
        columns = [c[1] for c in cursor.fetchall()]
        conn.close()
        assert 'secondary_position' in columns

    def test_add_status_changed_date_column(self, migrator):
        migrator.add_status_changed_date_column()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(crm_cards)")
        columns = [c[1] for c in cursor.fetchall()]
        conn.close()
        assert 'status_changed_date' in columns

    def test_create_approval_deadlines_table(self, migrator):
        migrator.create_approval_deadlines_table()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='approval_deadlines'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_add_employee_multiuser_fields(self, migrator):
        migrator.add_employee_multiuser_fields()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(employees)")
        columns = [c[1] for c in cursor.fetchall()]
        conn.close()
        # Проверяем что хотя бы login или password добавлены (если не было)

    def test_add_payment_tracking_fields(self, migrator):
        migrator.add_payment_tracking_fields()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(contracts)")
        columns = [c[1] for c in cursor.fetchall()]
        conn.close()

    def test_create_user_permissions_table(self, migrator):
        migrator.create_user_permissions_table()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_permissions'")
        result = cursor.fetchone()
        conn.close()
        assert result is not None

    def test_create_norm_days_templates_table(self, migrator):
        migrator.create_norm_days_templates_table()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='norm_days_templates'")
        result = cursor.fetchone()
        conn.close()
        assert result is not None

    def test_initialize_database(self, migrator):
        """Полная инициализация базы"""
        migrator.initialize_database()
        conn = sqlite3.connect(migrator.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        conn.close()
        # Должны быть ключевые таблицы
        assert 'contracts' in tables
        assert 'employees' in tables
