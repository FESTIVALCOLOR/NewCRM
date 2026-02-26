# -*- coding: utf-8 -*-
"""
Тесты utils/migrate_passwords.py — миграция паролей plain text -> PBKDF2.

Покрытие:
  - TestMigratePasswords (8) — основная логика миграции
  - TestCreateBackup (4) — создание резервных копий
ИТОГО: 12 тестов
"""

import os
import sqlite3
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def temp_db(tmp_path):
    """Создаёт временную SQLite БД с таблицей employees и тестовыми данными."""
    db_path = str(tmp_path / 'test_migrate.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            login TEXT,
            password TEXT,
            full_name TEXT
        )
    ''')
    # Добавляем тестовых сотрудников с plain text паролями
    cursor.executemany(
        'INSERT INTO employees (login, password, full_name) VALUES (?, ?, ?)',
        [
            ('admin', 'admin123', 'Администратор'),
            ('designer', 'design456', 'Дизайнер Иванов'),
            ('manager', 'manage789', 'Менеджер Петрова'),
        ]
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def temp_db_with_hashed(tmp_path):
    """БД с уже хэшированными паролями (содержат $)."""
    db_path = str(tmp_path / 'test_migrate_hashed.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            login TEXT,
            password TEXT,
            full_name TEXT
        )
    ''')
    cursor.executemany(
        'INSERT INTO employees (login, password, full_name) VALUES (?, ?, ?)',
        [
            ('admin', 'salt_base64$hash_base64', 'Администратор'),
            ('designer', 'another_salt$another_hash', 'Дизайнер'),
        ]
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def temp_db_mixed(tmp_path):
    """БД со смешанными паролями: часть plain text, часть хэшированных."""
    db_path = str(tmp_path / 'test_migrate_mixed.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            login TEXT,
            password TEXT,
            full_name TEXT
        )
    ''')
    cursor.executemany(
        'INSERT INTO employees (login, password, full_name) VALUES (?, ?, ?)',
        [
            ('admin', 'salt$hash', 'Администратор'),
            ('designer', 'plaintext_password', 'Дизайнер'),
        ]
    )
    conn.commit()
    conn.close()
    return db_path


class TestMigratePasswords:
    """Тесты миграции паролей из plain text в хэшированный формат."""

    def test_migrate_plain_passwords(self, temp_db):
        """Все plain text пароли мигрируются в формат salt$hash."""
        from utils.migrate_passwords import migrate_passwords
        result = migrate_passwords(temp_db)
        assert result is True

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM employees')
        passwords = [row[0] for row in cursor.fetchall()]
        conn.close()

        for pwd in passwords:
            assert '$' in pwd, f"Пароль не хэширован: {pwd}"

    def test_migrate_returns_true_on_success(self, temp_db):
        """Успешная миграция возвращает True."""
        from utils.migrate_passwords import migrate_passwords
        assert migrate_passwords(temp_db) is True

    def test_migrate_nonexistent_db_returns_false(self):
        """Несуществующая БД — возвращает False."""
        from utils.migrate_passwords import migrate_passwords
        result = migrate_passwords('/nonexistent/path/database.db')
        assert result is False

    def test_already_hashed_skipped(self, temp_db_with_hashed):
        """Уже хэшированные пароли (с $) пропускаются."""
        from utils.migrate_passwords import migrate_passwords
        result = migrate_passwords(temp_db_with_hashed)
        assert result is True

        conn = sqlite3.connect(temp_db_with_hashed)
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM employees WHERE login = ?', ('admin',))
        password = cursor.fetchone()[0]
        conn.close()

        # Пароль должен остаться прежним
        assert password == 'salt_base64$hash_base64'

    def test_mixed_passwords_migrate_only_plain(self, temp_db_mixed):
        """В смешанной БД мигрируются только plain text пароли."""
        from utils.migrate_passwords import migrate_passwords
        result = migrate_passwords(temp_db_mixed)
        assert result is True

        conn = sqlite3.connect(temp_db_mixed)
        cursor = conn.cursor()
        cursor.execute('SELECT login, password FROM employees ORDER BY id')
        rows = cursor.fetchall()
        conn.close()

        # admin — уже хэширован, должен остаться как есть
        assert rows[0][1] == 'salt$hash'
        # designer — был plain text, теперь хэширован
        assert '$' in rows[1][1]
        assert rows[1][1] != 'plaintext_password'

    def test_empty_db_returns_true(self, tmp_path):
        """БД без сотрудников — возвращает True."""
        db_path = str(tmp_path / 'empty.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                login TEXT,
                password TEXT,
                full_name TEXT
            )
        ''')
        conn.commit()
        conn.close()

        from utils.migrate_passwords import migrate_passwords
        assert migrate_passwords(db_path) is True

    def test_null_passwords_ignored(self, tmp_path):
        """Записи с NULL или пустыми паролями не обрабатываются."""
        db_path = str(tmp_path / 'null_pwd.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                login TEXT,
                password TEXT,
                full_name TEXT
            )
        ''')
        cursor.executemany(
            'INSERT INTO employees (login, password, full_name) VALUES (?, ?, ?)',
            [
                ('user1', None, 'Пользователь 1'),
                ('user2', '', 'Пользователь 2'),
            ]
        )
        conn.commit()
        conn.close()

        from utils.migrate_passwords import migrate_passwords
        result = migrate_passwords(db_path)
        assert result is True

    def test_hashed_passwords_are_verifiable(self, temp_db):
        """После миграции пароли проверяются через verify_password."""
        from utils.migrate_passwords import migrate_passwords
        from utils.password_utils import verify_password

        migrate_passwords(temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute('SELECT login, password FROM employees WHERE login = ?', ('admin',))
        _, hashed = cursor.fetchone()
        conn.close()

        assert verify_password('admin123', hashed) is True
        assert verify_password('wrong_password', hashed) is False


class TestCreateBackup:
    """Тесты создания резервных копий."""

    def test_creates_backup_file(self, temp_db):
        """Создаётся файл резервной копии."""
        from utils.migrate_passwords import create_backup
        backup_path = create_backup(temp_db)
        assert backup_path is not None
        assert os.path.exists(backup_path)
        # Очистка
        os.remove(backup_path)

    def test_backup_contains_timestamp(self, temp_db):
        """Имя бэкапа содержит временную метку."""
        from utils.migrate_passwords import create_backup
        backup_path = create_backup(temp_db)
        assert 'backup_' in backup_path
        # Очистка
        os.remove(backup_path)

    def test_backup_nonexistent_returns_none(self):
        """Бэкап несуществующего файла возвращает None."""
        from utils.migrate_passwords import create_backup
        result = create_backup('/nonexistent/database.db')
        assert result is None

    def test_backup_is_valid_copy(self, temp_db):
        """Бэкап — полноценная копия БД с теми же данными."""
        from utils.migrate_passwords import create_backup
        backup_path = create_backup(temp_db)

        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM employees')
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 3  # 3 сотрудника в temp_db
        # Очистка
        os.remove(backup_path)
