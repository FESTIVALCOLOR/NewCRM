# -*- coding: utf-8 -*-
"""
O-11: CI-тест сравнения колонок SQLite vs PostgreSQL
Проверяет что общие таблицы имеют одинаковые колонки (кроме известных расхождений).
"""
import sqlite3
import tempfile
import os
import sys
import pytest

# Добавляем корень проекта в PATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# Известные расхождения (whitelist) — не считаются ошибками
KNOWN_DIVERGENCES = {
    # Таблицы, которые есть ТОЛЬКО на сервере (PostgreSQL)
    'server_only_tables': {
        'user_sessions', 'activity_log', 'concurrent_edits',
        'notifications', 'file_storage',
    },
    # Таблицы, которые есть ТОЛЬКО в SQLite (legacy)
    'sqlite_only_tables': {
        'crm_supervision', 'agents', 'manager_stage_acceptance',
        'surveys', 'project_templates',
    },
    # Колонки с разными именами
    'column_renames': {
        ('employees', 'password', 'password_hash'),  # (table, sqlite_name, pg_name)
    },
    # Колонки, которые есть ТОЛЬКО в SQLite (legacy)
    'sqlite_only_columns': {
        ('employees', 'legal_status'),
        ('employees', 'hire_date'),
        ('employees', 'payment_details'),
        ('payments', 'stage'),
        ('payments', 'base_amount'),
        ('payments', 'bonus_amount'),
        ('payments', 'penalty_amount'),
        ('payments', 'payment_date'),
        ('payments', 'status'),
    },
    # Колонки, которые есть ТОЛЬКО в PostgreSQL (серверные)
    'pg_only_columns': {
        ('employees', 'last_login'),
        ('employees', 'is_online'),
        ('employees', 'last_activity'),
        ('employees', 'current_session_token'),
        ('employees', 'agent_color'),
    },
}


def get_sqlite_tables_and_columns():
    """Создаёт временную SQLite БД с миграциями и возвращает схему."""
    import database.db_manager as dbm

    # Сбрасываем глобальный флаг миграций для чистого запуска
    dbm._migrations_completed = False

    db_path = os.path.join(tempfile.gettempdir(), 'test_schema_sync.db')
    # Удаляем старый файл если есть
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except OSError:
            pass

    try:
        db = dbm.DatabaseManager(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Получаем список таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = {row[0] for row in cursor.fetchall()}

        # Получаем колонки каждой таблицы
        schema = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = {row[1] for row in cursor.fetchall()}
            schema[table] = columns

        conn.close()
        return schema
    finally:
        # Сбрасываем флаг обратно
        dbm._migrations_completed = False
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except OSError:
            pass  # Windows может держать файл — не критично


def get_pg_tables_and_columns():
    """Парсит SQLAlchemy модели из server/database.py и возвращает схему."""
    server_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'server')
    sys.path.insert(0, server_dir)

    try:
        from database import Base
        schema = {}
        for table_name, table in Base.metadata.tables.items():
            columns = {col.name for col in table.columns}
            schema[table_name] = columns
        return schema
    except ImportError:
        pytest.skip("Не удалось импортировать серверные модели (нужны серверные зависимости)")
    finally:
        if server_dir in sys.path:
            sys.path.remove(server_dir)


class TestSchemaSync:
    """Тесты синхронизации SQLite и PostgreSQL схемы."""

    def test_sqlite_schema_loads(self):
        """SQLite схема загружается без ошибок."""
        schema = get_sqlite_tables_and_columns()
        assert len(schema) > 10, f"Ожидалось >10 таблиц, получено {len(schema)}"

    def test_common_tables_have_matching_columns(self):
        """Общие таблицы имеют одинаковые колонки (кроме whitelisted)."""
        sqlite_schema = get_sqlite_tables_and_columns()

        try:
            pg_schema = get_pg_tables_and_columns()
        except Exception:
            pytest.skip("Серверные зависимости недоступны")
            return

        # Общие таблицы (за вычётом known-only)
        sqlite_tables = set(sqlite_schema.keys()) - KNOWN_DIVERGENCES['sqlite_only_tables']
        pg_tables = set(pg_schema.keys()) - KNOWN_DIVERGENCES['server_only_tables']
        common_tables = sqlite_tables & pg_tables

        assert len(common_tables) > 5, f"Ожидалось >5 общих таблиц, найдено {len(common_tables)}"

        # Строим whitelist колонок
        sqlite_only_cols = KNOWN_DIVERGENCES['sqlite_only_columns']
        pg_only_cols = KNOWN_DIVERGENCES['pg_only_columns']
        col_renames = KNOWN_DIVERGENCES['column_renames']

        # Собираем rename маппинг
        sqlite_rename = {(t, sqlite_name) for t, sqlite_name, _ in col_renames}
        pg_rename = {(t, pg_name) for t, _, pg_name in col_renames}

        errors = []
        for table in sorted(common_tables):
            sqlite_cols = sqlite_schema.get(table, set())
            pg_cols = pg_schema.get(table, set())

            # Убираем whitelisted колонки
            effective_sqlite = sqlite_cols - {c for t, c in sqlite_only_cols if t == table}
            effective_sqlite = effective_sqlite - {c for t, c in sqlite_rename if t == table}

            effective_pg = pg_cols - {c for t, c in pg_only_cols if t == table}
            effective_pg = effective_pg - {c for t, c in pg_rename if t == table}

            # Колонки в SQLite, но не в PostgreSQL (неизвестные)
            only_sqlite = effective_sqlite - effective_pg
            if only_sqlite:
                errors.append(f"{table}: только в SQLite: {only_sqlite}")

            # Колонки в PostgreSQL, но не в SQLite (неизвестные)
            only_pg = effective_pg - effective_sqlite
            if only_pg:
                errors.append(f"{table}: только в PostgreSQL: {only_pg}")

        if errors:
            msg = "Обнаружены НОВЫЕ расхождения схемы (не в whitelist):\n"
            msg += "\n".join(f"  - {e}" for e in errors)
            msg += "\n\nЕсли расхождения ожидаемые, добавьте их в KNOWN_DIVERGENCES в test_schema_sync.py"
            pytest.fail(msg)
