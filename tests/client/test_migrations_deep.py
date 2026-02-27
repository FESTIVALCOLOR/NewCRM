# -*- coding: utf-8 -*-
"""
Глубокое покрытие database/migrations.py — каждая миграция, idempotent, upgrade path.
~90 тестов. Реальная SQLite через tmp_path.

Тестируемые миграции (НЕ дублируя test_migrations_full.py):
  1. add_contract_status_fields (standalone)
  2. run_migrations (полный pipeline)
  3. add_payment_tracking_fields
  4. add_signed_acts_fields
  5. create_user_permissions_table
  6. create_role_default_permissions_table
  7. create_norm_days_templates_table
  8. add_agent_type_to_norm_days_templates
  9. add_custom_norm_days_column
  10. add_employee_multiuser_fields
  11. add_agents_status_field
  12. migrate_add_cities_table
  13. add_third_payment_field (idempotent + data)
  14. initialize_database (полная инициализация + seed)
  15. add_approval_deadline_field / add_approval_stages_field
  16. create_approval_deadlines_table
  17. add_project_data_link_field
  18. add_birth_date_column / add_address_column / add_secondary_position_column
  19. add_status_changed_date_column
  20. add_tech_task_fields / add_survey_date_column
  21. create_supervision_table_migration / fix_supervision_cards_column_name
  22. create_supervision_history_table
  23. create_manager_acceptance_table / create_payments_system_tables
  24. add_reassigned_field_to_payments / add_submitted_date_to_stage_executors
  25. add_stage_field_to_payments / add_contract_file_columns
  26. create_project_files_table / create_project_templates_table
  27. create_timeline_tables / add_project_subtype_to_contracts
  28. add_floors_to_contracts / create_stage_workflow_state_table
  29. create_messenger_tables / create_performance_indexes
  30. add_missing_fields_rates_payments_salaries
  31. fix_payments_contract_id_nullable
  32. Upgrade path (sequential migrations)
"""

import pytest
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.migrations import DatabaseMigrations, add_contract_status_fields


# ============================================================================
# Базовый TestMigrator — обёртка для DatabaseMigrations mixin
# ============================================================================

class TestMigrator(DatabaseMigrations):
    """Минимальный класс для тестирования миграций."""

    def __init__(self, db_path):
        self.db_path = db_path
        self._conn = None
        self._shared_conn = False

    def connect(self):
        if self._shared_conn and self._conn:
            return self._conn
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        if self._shared_conn:
            return
        if self._conn:
            self._conn.close()
            self._conn = None


def _get_columns(db_path, table):
    """Получить список колонок таблицы."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [c[1] for c in cursor.fetchall()]
    conn.close()
    return columns


def _table_exists(db_path, table):
    """Проверить существование таблицы."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def _count_rows(db_path, table):
    """Подсчитать количество строк в таблице."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    conn.close()
    return count


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def empty_db(tmp_path):
    """Создать пустую SQLite БД (без таблиц)."""
    db_path = str(tmp_path / 'test_migrations.db')
    conn = sqlite3.connect(db_path)
    conn.close()
    return db_path


@pytest.fixture
def minimal_db(tmp_path):
    """Создать БД с минимальными таблицами (contracts, crm_cards, employees, clients)."""
    db_path = str(tmp_path / 'test_migrations.db')
    conn = sqlite3.connect(db_path)
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
        id INTEGER PRIMARY KEY, full_name TEXT, role TEXT, status TEXT,
        login TEXT, password TEXT, position TEXT, department TEXT, phone TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY, full_name TEXT, client_type TEXT, phone TEXT
    )''')
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def migrator(minimal_db):
    """Создать TestMigrator с минимальной БД."""
    return TestMigrator(minimal_db)


@pytest.fixture
def migrator_full(tmp_path):
    """Создать TestMigrator с полной инициализацией."""
    db_path = str(tmp_path / 'test_full.db')
    conn = sqlite3.connect(db_path)
    conn.close()
    m = TestMigrator(db_path)
    m.initialize_database()
    return m


# ============================================================================
# ТЕСТЫ: add_contract_status_fields (standalone функция)
# ============================================================================

class TestAddContractStatusFieldsStandalone:
    """Тесты standalone функции add_contract_status_fields."""

    def test_adds_status(self, minimal_db):
        """Добавляет колонку status."""
        # Удаляем status чтобы тестировать добавление
        conn = sqlite3.connect(minimal_db)
        conn.execute("CREATE TABLE contracts_new (id INTEGER PRIMARY KEY, contract_number TEXT)")
        conn.execute("DROP TABLE contracts")
        conn.execute("ALTER TABLE contracts_new RENAME TO contracts")
        conn.commit()
        conn.close()

        add_contract_status_fields(minimal_db)
        cols = _get_columns(minimal_db, 'contracts')
        assert 'status' in cols
        assert 'termination_reason' in cols

    def test_idempotent(self, minimal_db):
        """Повторный вызов не дублирует колонки."""
        add_contract_status_fields(minimal_db)
        add_contract_status_fields(minimal_db)
        cols = _get_columns(minimal_db, 'contracts')
        assert cols.count('status') == 1

    def test_invalid_path_no_crash(self):
        """Невалидный путь не вызывает crash."""
        add_contract_status_fields('/nonexistent/path/db.sqlite')

    def test_preserves_existing_data(self, minimal_db):
        """Существующие данные сохраняются."""
        conn = sqlite3.connect(minimal_db)
        conn.execute("INSERT INTO contracts (id, contract_number) VALUES (1, '001')")
        conn.commit()
        conn.close()

        add_contract_status_fields(minimal_db)

        conn = sqlite3.connect(minimal_db)
        cursor = conn.cursor()
        cursor.execute("SELECT contract_number FROM contracts WHERE id = 1")
        assert cursor.fetchone()[0] == '001'
        conn.close()


# ============================================================================
# ТЕСТЫ: add_payment_tracking_fields
# ============================================================================

class TestAddPaymentTrackingFields:
    """Миграция: поля отслеживания платежей."""

    def test_adds_payment_date_fields(self, migrator):
        """Добавляет поля дат оплат."""
        migrator.add_payment_tracking_fields()
        cols = _get_columns(migrator.db_path, 'contracts')
        for field in ['advance_payment_paid_date', 'additional_payment_paid_date', 'third_payment_paid_date']:
            assert field in cols, f"Поле {field} не добавлено"

    def test_adds_receipt_fields(self, migrator):
        """Добавляет поля чеков."""
        migrator.add_payment_tracking_fields()
        cols = _get_columns(migrator.db_path, 'contracts')
        for field in ['advance_receipt_link', 'advance_receipt_yandex_path',
                       'additional_receipt_link', 'third_receipt_link']:
            assert field in cols, f"Поле {field} не добавлено"

    def test_idempotent(self, migrator):
        """Повторный вызов не падает."""
        migrator.add_payment_tracking_fields()
        migrator.add_payment_tracking_fields()

    def test_twelve_new_columns(self, migrator):
        """Добавляет ровно 12 новых колонок."""
        cols_before = set(_get_columns(migrator.db_path, 'contracts'))
        migrator.add_payment_tracking_fields()
        cols_after = set(_get_columns(migrator.db_path, 'contracts'))
        new_cols = cols_after - cols_before
        assert len(new_cols) == 12


# ============================================================================
# ТЕСТЫ: add_signed_acts_fields
# ============================================================================

class TestAddSignedActsFields:
    """Миграция: поля подписанных актов."""

    def test_adds_act_fields(self, migrator):
        """Добавляет поля для подписанных актов."""
        migrator.add_signed_acts_fields()
        cols = _get_columns(migrator.db_path, 'contracts')
        for field in ['act_planning_signed_link', 'act_concept_signed_link',
                       'info_letter_signed_link', 'act_final_signed_link']:
            assert field in cols, f"Поле {field} не добавлено"

    def test_twelve_new_columns(self, migrator):
        """Добавляет 12 колонок (4 акта * 3 поля)."""
        cols_before = set(_get_columns(migrator.db_path, 'contracts'))
        migrator.add_signed_acts_fields()
        cols_after = set(_get_columns(migrator.db_path, 'contracts'))
        new_cols = cols_after - cols_before
        assert len(new_cols) == 12

    def test_idempotent(self, migrator):
        """Повторный вызов не падает."""
        migrator.add_signed_acts_fields()
        migrator.add_signed_acts_fields()


# ============================================================================
# ТЕСТЫ: create_user_permissions_table
# ============================================================================

class TestCreateUserPermissionsTable:
    """Миграция: таблица user_permissions."""

    def test_creates_table(self, migrator):
        """Таблица user_permissions создаётся."""
        migrator.create_user_permissions_table()
        assert _table_exists(migrator.db_path, 'user_permissions')

    def test_has_required_columns(self, migrator):
        """Таблица имеет необходимые колонки."""
        migrator.create_user_permissions_table()
        cols = _get_columns(migrator.db_path, 'user_permissions')
        assert 'employee_id' in cols
        assert 'permission_name' in cols
        assert 'granted_by' in cols

    def test_idempotent(self, migrator):
        """Повторный вызов (CREATE IF NOT EXISTS) не падает."""
        migrator.create_user_permissions_table()
        migrator.create_user_permissions_table()

    def test_unique_constraint(self, migrator):
        """UNIQUE(employee_id, permission_name) предотвращает дубликаты."""
        migrator.create_user_permissions_table()
        conn = sqlite3.connect(migrator.db_path)
        conn.execute("INSERT INTO user_permissions (employee_id, permission_name) VALUES (1, 'test')")
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO user_permissions (employee_id, permission_name) VALUES (1, 'test')")
        conn.close()


# ============================================================================
# ТЕСТЫ: create_role_default_permissions_table
# ============================================================================

class TestCreateRoleDefaultPermissionsTable:
    """Миграция: таблица role_default_permissions."""

    def test_creates_table(self, migrator):
        """Таблица создаётся."""
        migrator.create_role_default_permissions_table()
        assert _table_exists(migrator.db_path, 'role_default_permissions')

    def test_has_required_columns(self, migrator):
        """Необходимые колонки."""
        migrator.create_role_default_permissions_table()
        cols = _get_columns(migrator.db_path, 'role_default_permissions')
        assert 'role' in cols
        assert 'permission_name' in cols

    def test_idempotent(self, migrator):
        """Повторный вызов не падает."""
        migrator.create_role_default_permissions_table()
        migrator.create_role_default_permissions_table()


# ============================================================================
# ТЕСТЫ: create_norm_days_templates_table
# ============================================================================

class TestCreateNormDaysTemplatesTable:
    """Миграция: таблица norm_days_templates."""

    def test_creates_table(self, migrator):
        """Таблица создаётся."""
        migrator.create_norm_days_templates_table()
        assert _table_exists(migrator.db_path, 'norm_days_templates')

    def test_has_required_columns(self, migrator):
        """Все необходимые колонки."""
        migrator.create_norm_days_templates_table()
        cols = _get_columns(migrator.db_path, 'norm_days_templates')
        for col in ['project_type', 'project_subtype', 'stage_code', 'stage_name',
                     'stage_group', 'base_norm_days', 'executor_role', 'sort_order']:
            assert col in cols, f"Колонка {col} не найдена"

    def test_has_agent_type_column(self, migrator):
        """Колонка agent_type с дефолтом 'Все агенты'."""
        migrator.create_norm_days_templates_table()
        cols = _get_columns(migrator.db_path, 'norm_days_templates')
        assert 'agent_type' in cols

    def test_unique_constraint(self, migrator):
        """UNIQUE(project_type, project_subtype, stage_code, agent_type)."""
        migrator.create_norm_days_templates_table()
        conn = sqlite3.connect(migrator.db_path)
        conn.execute("""INSERT INTO norm_days_templates
            (project_type, project_subtype, stage_code, stage_name, stage_group,
             base_norm_days, executor_role, sort_order)
            VALUES ('Инд', 'Стандарт', 'S1', 'Замер', 'Подготовка', 3, 'Замерщик', 1)""")
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""INSERT INTO norm_days_templates
                (project_type, project_subtype, stage_code, stage_name, stage_group,
                 base_norm_days, executor_role, sort_order)
                VALUES ('Инд', 'Стандарт', 'S1', 'Замер2', 'Подготовка', 5, 'Замерщик', 2)""")
        conn.close()

    def test_idempotent(self, migrator):
        """Повторный вызов не падает."""
        migrator.create_norm_days_templates_table()
        migrator.create_norm_days_templates_table()


# ============================================================================
# ТЕСТЫ: add_agent_type_to_norm_days_templates
# ============================================================================

class TestAddAgentTypeToNormDaysTemplates:
    """Миграция: добавление agent_type в norm_days_templates."""

    def test_adds_column_if_missing(self, migrator):
        """Добавляет колонку agent_type если её нет."""
        # Создаём таблицу без agent_type
        conn = sqlite3.connect(migrator.db_path)
        conn.execute("""CREATE TABLE norm_days_templates (
            id INTEGER PRIMARY KEY,
            project_type TEXT NOT NULL,
            project_subtype TEXT NOT NULL,
            stage_code TEXT NOT NULL,
            stage_name TEXT NOT NULL,
            stage_group TEXT NOT NULL,
            base_norm_days REAL NOT NULL,
            executor_role TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            k_multiplier REAL DEFAULT 0,
            substage_group TEXT,
            is_in_contract_scope BOOLEAN DEFAULT 1,
            updated_at TIMESTAMP,
            updated_by INTEGER,
            UNIQUE(project_type, project_subtype, stage_code)
        )""")
        conn.commit()
        conn.close()

        migrator.add_agent_type_to_norm_days_templates()
        cols = _get_columns(migrator.db_path, 'norm_days_templates')
        assert 'agent_type' in cols

    def test_idempotent_when_already_exists(self, migrator):
        """Не падает если agent_type уже существует."""
        migrator.create_norm_days_templates_table()
        migrator.add_agent_type_to_norm_days_templates()  # колонка уже есть


# ============================================================================
# ТЕСТЫ: add_custom_norm_days_column
# ============================================================================

class TestAddCustomNormDaysColumn:
    """Миграция: custom_norm_days в project_timeline_entries."""

    def test_adds_column(self, migrator_full):
        """Добавляет колонку custom_norm_days."""
        migrator_full.create_timeline_tables()
        migrator_full.add_custom_norm_days_column()
        cols = _get_columns(migrator_full.db_path, 'project_timeline_entries')
        assert 'custom_norm_days' in cols

    def test_idempotent(self, migrator_full):
        """Повторный вызов не падает."""
        migrator_full.create_timeline_tables()
        migrator_full.add_custom_norm_days_column()
        migrator_full.add_custom_norm_days_column()


# ============================================================================
# ТЕСТЫ: add_employee_multiuser_fields
# ============================================================================

class TestAddEmployeeMultiuserFields:
    """Миграция: multiuser поля для employees."""

    def test_adds_is_online(self, migrator):
        """Добавляет поле is_online."""
        migrator.add_employee_multiuser_fields()
        cols = _get_columns(migrator.db_path, 'employees')
        assert 'is_online' in cols

    def test_adds_last_login(self, migrator):
        """Добавляет поле last_login."""
        migrator.add_employee_multiuser_fields()
        cols = _get_columns(migrator.db_path, 'employees')
        assert 'last_login' in cols

    def test_adds_last_activity(self, migrator):
        """Добавляет поле last_activity."""
        migrator.add_employee_multiuser_fields()
        cols = _get_columns(migrator.db_path, 'employees')
        assert 'last_activity' in cols

    def test_adds_session_token(self, migrator):
        """Добавляет поле current_session_token."""
        migrator.add_employee_multiuser_fields()
        cols = _get_columns(migrator.db_path, 'employees')
        assert 'current_session_token' in cols

    def test_adds_agent_color(self, migrator):
        """Добавляет поле agent_color."""
        migrator.add_employee_multiuser_fields()
        cols = _get_columns(migrator.db_path, 'employees')
        assert 'agent_color' in cols

    def test_idempotent(self, migrator):
        """Повторный вызов не падает."""
        migrator.add_employee_multiuser_fields()
        migrator.add_employee_multiuser_fields()

    def test_five_new_columns(self, migrator):
        """Добавляет 5 новых колонок."""
        cols_before = set(_get_columns(migrator.db_path, 'employees'))
        migrator.add_employee_multiuser_fields()
        cols_after = set(_get_columns(migrator.db_path, 'employees'))
        new_cols = cols_after - cols_before
        assert len(new_cols) == 5


# ============================================================================
# ТЕСТЫ: add_agents_status_field
# ============================================================================

class TestAddAgentsStatusField:
    """Миграция: поле status в таблице agents."""

    def test_adds_status_field(self, migrator_full):
        """Добавляет поле status в agents."""
        # initialize_database создаёт agents, теперь добавляем status
        migrator_full.add_agents_status_field()
        cols = _get_columns(migrator_full.db_path, 'agents')
        assert 'status' in cols

    def test_idempotent(self, migrator_full):
        """Повторный вызов не падает."""
        migrator_full.add_agents_status_field()
        migrator_full.add_agents_status_field()


# ============================================================================
# ТЕСТЫ: migrate_add_cities_table
# ============================================================================

class TestMigrateAddCitiesTable:
    """Миграция: таблица городов."""

    def test_creates_table(self, migrator_full):
        """Таблица cities создаётся."""
        migrator_full.migrate_add_cities_table()
        assert _table_exists(migrator_full.db_path, 'cities')

    def test_has_required_columns(self, migrator_full):
        """Таблица имеет name, status, created_at."""
        migrator_full.migrate_add_cities_table()
        cols = _get_columns(migrator_full.db_path, 'cities')
        assert 'name' in cols
        assert 'status' in cols
        assert 'created_at' in cols

    def test_seeds_default_cities(self, migrator_full):
        """Добавляет seed-города: СПБ, МСК, ВН."""
        migrator_full.migrate_add_cities_table()
        conn = sqlite3.connect(migrator_full.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM cities ORDER BY name")
        names = [r[0] for r in cursor.fetchall()]
        conn.close()
        assert 'СПБ' in names
        assert 'МСК' in names
        assert 'ВН' in names

    def test_idempotent(self, migrator_full):
        """Повторный вызов не дублирует города."""
        migrator_full.migrate_add_cities_table()
        migrator_full.migrate_add_cities_table()
        count = _count_rows(migrator_full.db_path, 'cities')
        assert count == 3

    def test_unique_name_constraint(self, migrator_full):
        """UNIQUE на name не позволяет дубликаты."""
        migrator_full.migrate_add_cities_table()
        conn = sqlite3.connect(migrator_full.db_path)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO cities (name) VALUES ('СПБ')")
        conn.close()


# ============================================================================
# ТЕСТЫ: initialize_database
# ============================================================================

class TestInitializeDatabase:
    """Полная инициализация БД."""

    def test_creates_employees_table(self, empty_db):
        """Создаёт таблицу employees."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        assert _table_exists(empty_db, 'employees')

    def test_creates_clients_table(self, empty_db):
        """Создаёт таблицу clients."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        assert _table_exists(empty_db, 'clients')

    def test_creates_contracts_table(self, empty_db):
        """Создаёт таблицу contracts."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        assert _table_exists(empty_db, 'contracts')

    def test_creates_crm_cards_table(self, empty_db):
        """Создаёт таблицу crm_cards."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        assert _table_exists(empty_db, 'crm_cards')

    def test_creates_stage_executors_table(self, empty_db):
        """Создаёт таблицу stage_executors."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        assert _table_exists(empty_db, 'stage_executors')

    def test_creates_salaries_table(self, empty_db):
        """Создаёт таблицу salaries."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        assert _table_exists(empty_db, 'salaries')

    def test_creates_action_history_table(self, empty_db):
        """Создаёт таблицу action_history."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        assert _table_exists(empty_db, 'action_history')

    def test_creates_agents_table(self, empty_db):
        """Создаёт таблицу agents."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        assert _table_exists(empty_db, 'agents')

    def test_creates_crm_supervision_table(self, empty_db):
        """Создаёт таблицу crm_supervision."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        assert _table_exists(empty_db, 'crm_supervision')

    def test_seeds_admin(self, empty_db):
        """Создаёт администратора по умолчанию."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        conn = sqlite3.connect(empty_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE login = 'admin'")
        admin = cursor.fetchone()
        conn.close()
        assert admin is not None
        assert admin['full_name'] == 'Администратор'

    def test_seeds_agents(self, empty_db):
        """Создаёт агентов по умолчанию (ПЕТРОВИЧ, ФЕСТИВАЛЬ)."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        conn = sqlite3.connect(empty_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM agents ORDER BY name")
        names = [r[0] for r in cursor.fetchall()]
        conn.close()
        assert 'ПЕТРОВИЧ' in names
        assert 'ФЕСТИВАЛЬ' in names

    def test_idempotent(self, empty_db):
        """Повторная инициализация не дублирует данные."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        m.initialize_database()
        count = _count_rows(empty_db, 'agents')
        assert count == 2  # Только ПЕТРОВИЧ и ФЕСТИВАЛЬ

    def test_admin_password_hashed(self, empty_db):
        """Пароль администратора хэширован."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        conn = sqlite3.connect(empty_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM employees WHERE login = 'admin'")
        admin = cursor.fetchone()
        conn.close()
        assert admin['password'] != 'admin'
        assert len(admin['password']) > 10

    def test_contracts_table_has_all_columns(self, empty_db):
        """Contracts имеет все современные колонки."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        cols = _get_columns(empty_db, 'contracts')
        for col in ['project_type', 'project_subtype', 'floors', 'agent_type',
                     'city', 'area', 'total_amount', 'yandex_folder_path']:
            assert col in cols, f"Колонка {col} не найдена в contracts"

    def test_crm_cards_table_has_all_columns(self, empty_db):
        """CRM cards имеет все современные колонки."""
        m = TestMigrator(empty_db)
        m.initialize_database()
        cols = _get_columns(empty_db, 'crm_cards')
        for col in ['column_name', 'deadline', 'tags', 'is_approved',
                     'previous_column', 'senior_manager_id', 'gap_id']:
            assert col in cols, f"Колонка {col} не найдена в crm_cards"


# ============================================================================
# ТЕСТЫ: add_tech_task_fields / add_survey_date_column
# ============================================================================

class TestTechTaskAndSurveyFields:
    """Миграции для полей ТЗ и замера."""

    def test_add_tech_task_fields(self, migrator):
        """Добавляет поля tech_task."""
        migrator.add_tech_task_fields()
        cols = _get_columns(migrator.db_path, 'crm_cards')
        assert 'tech_task_file' in cols
        assert 'tech_task_date' in cols

    def test_add_survey_date_column(self, migrator):
        """Добавляет survey_date в crm_cards."""
        migrator.add_survey_date_column()
        cols = _get_columns(migrator.db_path, 'crm_cards')
        assert 'survey_date' in cols

    def test_tech_task_idempotent(self, migrator):
        """Повторный вызов не падает."""
        migrator.add_tech_task_fields()
        migrator.add_tech_task_fields()

    def test_survey_date_idempotent(self, migrator):
        """Повторный вызов не падает."""
        migrator.add_survey_date_column()
        migrator.add_survey_date_column()


# ============================================================================
# ТЕСТЫ: create_supervision_table_migration / fix_supervision_cards_column_name
# ============================================================================

class TestSupervisionMigrations:
    """Миграции надзора."""

    def test_create_supervision_table(self, migrator_full):
        """Создаёт таблицу supervision_cards."""
        migrator_full.create_supervision_table_migration()
        assert _table_exists(migrator_full.db_path, 'supervision_cards')

    def test_supervision_has_required_columns(self, migrator_full):
        """supervision_cards имеет необходимые колонки."""
        migrator_full.create_supervision_table_migration()
        cols = _get_columns(migrator_full.db_path, 'supervision_cards')
        assert 'contract_id' in cols
        assert 'column_name' in cols

    def test_fix_supervision_column_name_idempotent(self, migrator_full):
        """fix_supervision_cards_column_name не падает при повторном вызове."""
        migrator_full.create_supervision_table_migration()
        migrator_full.fix_supervision_cards_column_name()
        migrator_full.fix_supervision_cards_column_name()

    def test_double_create_adds_more_columns(self, migrator_full):
        """Повторный вызов create_supervision_table_migration добавляет доп. колонки."""
        migrator_full.create_supervision_table_migration()
        migrator_full.create_supervision_table_migration()
        cols = _get_columns(migrator_full.db_path, 'supervision_cards')
        # Второй вызов должен добавить previous_column и другие ALTER
        assert 'previous_column' in cols or 'deadline' in cols


# ============================================================================
# ТЕСТЫ: create_supervision_history_table
# ============================================================================

class TestCreateSupervisionHistoryTable:
    """Миграция: таблица supervision_project_history."""

    def test_creates_table(self, migrator_full):
        """Таблица создаётся."""
        migrator_full.create_supervision_table_migration()
        migrator_full.create_supervision_history_table()
        assert _table_exists(migrator_full.db_path, 'supervision_project_history')

    def test_has_required_columns(self, migrator_full):
        """Необходимые колонки."""
        migrator_full.create_supervision_table_migration()
        migrator_full.create_supervision_history_table()
        cols = _get_columns(migrator_full.db_path, 'supervision_project_history')
        assert 'supervision_card_id' in cols
        assert 'entry_type' in cols
        assert 'message' in cols

    def test_idempotent(self, migrator_full):
        """Повторный вызов не падает."""
        migrator_full.create_supervision_table_migration()
        migrator_full.create_supervision_history_table()
        migrator_full.create_supervision_history_table()


# ============================================================================
# ТЕСТЫ: create_manager_acceptance_table
# ============================================================================

class TestCreateManagerAcceptanceTable:
    """Миграция: таблица manager_stage_acceptance."""

    def test_creates_table(self, migrator_full):
        """Таблица создаётся."""
        migrator_full.create_manager_acceptance_table()
        assert _table_exists(migrator_full.db_path, 'manager_stage_acceptance')

    def test_idempotent(self, migrator_full):
        """Повторный вызов не падает."""
        migrator_full.create_manager_acceptance_table()
        migrator_full.create_manager_acceptance_table()


# ============================================================================
# ТЕСТЫ: create_payments_system_tables
# ============================================================================

class TestCreatePaymentsSystemTables:
    """Миграция: платёжные таблицы."""

    def test_creates_payments_table(self, migrator_full):
        """Создаёт таблицу payments."""
        migrator_full.create_payments_system_tables()
        assert _table_exists(migrator_full.db_path, 'payments')

    def test_creates_rates_table(self, migrator_full):
        """Создаёт таблицу rates."""
        migrator_full.create_payments_system_tables()
        assert _table_exists(migrator_full.db_path, 'rates')

    def test_payments_has_required_columns(self, migrator_full):
        """payments имеет ключевые колонки."""
        migrator_full.create_payments_system_tables()
        cols = _get_columns(migrator_full.db_path, 'payments')
        for col in ['contract_id', 'employee_id', 'role', 'calculated_amount',
                     'final_amount', 'payment_type']:
            assert col in cols, f"Колонка {col} не найдена"

    def test_idempotent(self, migrator_full):
        """Повторный вызов не падает."""
        migrator_full.create_payments_system_tables()
        migrator_full.create_payments_system_tables()


# ============================================================================
# ТЕСТЫ: add_reassigned_field_to_payments
# ============================================================================

class TestAddReassignedFieldToPayments:
    """Миграция: поле reassigned в payments."""

    def test_adds_field(self, migrator_full):
        """Добавляет поле reassigned."""
        migrator_full.create_payments_system_tables()
        migrator_full.add_reassigned_field_to_payments()
        cols = _get_columns(migrator_full.db_path, 'payments')
        assert 'reassigned' in cols

    def test_idempotent(self, migrator_full):
        """Повторный вызов не падает."""
        migrator_full.create_payments_system_tables()
        migrator_full.add_reassigned_field_to_payments()
        migrator_full.add_reassigned_field_to_payments()


# ============================================================================
# ТЕСТЫ: add_submitted_date_to_stage_executors
# ============================================================================

class TestAddSubmittedDateToStageExecutors:
    """Миграция: submitted_date в stage_executors."""

    def test_adds_field(self, migrator_full):
        """Добавляет поле submitted_date."""
        migrator_full.add_submitted_date_to_stage_executors()
        cols = _get_columns(migrator_full.db_path, 'stage_executors')
        assert 'submitted_date' in cols

    def test_idempotent(self, migrator_full):
        migrator_full.add_submitted_date_to_stage_executors()
        migrator_full.add_submitted_date_to_stage_executors()


# ============================================================================
# ТЕСТЫ: add_stage_field_to_payments
# ============================================================================

class TestAddStageFieldToPayments:
    """Миграция: stage_name в payments."""

    def test_adds_field(self, migrator_full):
        """Добавляет stage_name."""
        migrator_full.create_payments_system_tables()
        migrator_full.add_stage_field_to_payments()
        cols = _get_columns(migrator_full.db_path, 'payments')
        assert 'stage_name' in cols

    def test_idempotent(self, migrator_full):
        migrator_full.create_payments_system_tables()
        migrator_full.add_stage_field_to_payments()
        migrator_full.add_stage_field_to_payments()


# ============================================================================
# ТЕСТЫ: add_contract_file_columns
# ============================================================================

class TestAddContractFileColumns:
    """Миграция: колонки файлов в contracts."""

    def test_adds_file_columns(self, migrator_full):
        """Добавляет колонки для файлов."""
        migrator_full.add_contract_file_columns()
        cols = _get_columns(migrator_full.db_path, 'contracts')
        assert 'contract_file_name' in cols

    def test_idempotent(self, migrator_full):
        migrator_full.add_contract_file_columns()
        migrator_full.add_contract_file_columns()


# ============================================================================
# ТЕСТЫ: create_project_files_table
# ============================================================================

class TestCreateProjectFilesTable:
    """Миграция: таблица project_files."""

    def test_creates_table(self, migrator_full):
        """Таблица project_files создаётся."""
        migrator_full.create_project_files_table()
        assert _table_exists(migrator_full.db_path, 'project_files')

    def test_has_columns(self, migrator_full):
        """Необходимые колонки."""
        migrator_full.create_project_files_table()
        cols = _get_columns(migrator_full.db_path, 'project_files')
        for col in ['contract_id', 'stage', 'file_type', 'public_link', 'yandex_path', 'file_name']:
            assert col in cols, f"Колонка {col} не найдена"

    def test_idempotent(self, migrator_full):
        migrator_full.create_project_files_table()
        migrator_full.create_project_files_table()


# ============================================================================
# ТЕСТЫ: create_project_templates_table
# ============================================================================

class TestCreateProjectTemplatesTable:
    """Миграция: таблица contract_templates."""

    def test_creates_table(self, migrator_full):
        """Таблица contract_templates создаётся."""
        migrator_full.create_project_templates_table()
        assert _table_exists(migrator_full.db_path, 'contract_templates')

    def test_idempotent(self, migrator_full):
        migrator_full.create_project_templates_table()
        migrator_full.create_project_templates_table()


# ============================================================================
# ТЕСТЫ: create_timeline_tables
# ============================================================================

class TestCreateTimelineTables:
    """Миграция: таблицы timeline."""

    def test_creates_timeline_entries(self, migrator_full):
        """Создаёт project_timeline_entries."""
        migrator_full.create_timeline_tables()
        assert _table_exists(migrator_full.db_path, 'project_timeline_entries')

    def test_timeline_has_columns(self, migrator_full):
        """project_timeline_entries имеет ключевые колонки."""
        migrator_full.create_timeline_tables()
        cols = _get_columns(migrator_full.db_path, 'project_timeline_entries')
        for col in ['contract_id', 'stage_code', 'stage_name', 'norm_days']:
            assert col in cols, f"Колонка {col} не найдена"

    def test_idempotent(self, migrator_full):
        migrator_full.create_timeline_tables()
        migrator_full.create_timeline_tables()


# ============================================================================
# ТЕСТЫ: add_project_subtype_to_contracts / add_floors_to_contracts
# ============================================================================

class TestProjectSubtypeAndFloors:
    """Миграции для project_subtype и floors."""

    def test_add_project_subtype(self, migrator_full):
        """Добавляет project_subtype."""
        migrator_full.add_project_subtype_to_contracts()
        cols = _get_columns(migrator_full.db_path, 'contracts')
        assert 'project_subtype' in cols

    def test_add_floors(self, migrator_full):
        """Добавляет floors."""
        migrator_full.add_floors_to_contracts()
        cols = _get_columns(migrator_full.db_path, 'contracts')
        assert 'floors' in cols

    def test_subtype_idempotent(self, migrator_full):
        migrator_full.add_project_subtype_to_contracts()
        migrator_full.add_project_subtype_to_contracts()

    def test_floors_idempotent(self, migrator_full):
        migrator_full.add_floors_to_contracts()
        migrator_full.add_floors_to_contracts()


# ============================================================================
# ТЕСТЫ: create_stage_workflow_state_table
# ============================================================================

class TestCreateStageWorkflowStateTable:
    """Миграция: stage_workflow_state."""

    def test_creates_table(self, migrator_full):
        migrator_full.create_stage_workflow_state_table()
        assert _table_exists(migrator_full.db_path, 'stage_workflow_state')

    def test_idempotent(self, migrator_full):
        migrator_full.create_stage_workflow_state_table()
        migrator_full.create_stage_workflow_state_table()


# ============================================================================
# ТЕСТЫ: create_messenger_tables
# ============================================================================

class TestCreateMessengerTables:
    """Миграция: таблицы мессенджера."""

    def test_creates_messenger_settings(self, migrator_full):
        """Создаёт messenger_settings."""
        migrator_full.create_messenger_tables()
        assert _table_exists(migrator_full.db_path, 'messenger_settings')

    def test_creates_messenger_scripts(self, migrator_full):
        """Создаёт messenger_scripts."""
        migrator_full.create_messenger_tables()
        assert _table_exists(migrator_full.db_path, 'messenger_scripts')

    def test_idempotent(self, migrator_full):
        migrator_full.create_messenger_tables()
        migrator_full.create_messenger_tables()


# ============================================================================
# ТЕСТЫ: create_performance_indexes
# ============================================================================

class TestCreatePerformanceIndexes:
    """Миграция: производительные индексы."""

    def test_creates_indexes(self, migrator_full):
        """Создаёт индексы без ошибок."""
        migrator_full.create_performance_indexes()
        # Проверяем что хотя бы один индекс создан
        conn = sqlite3.connect(migrator_full.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [r[0] for r in cursor.fetchall()]
        conn.close()
        # Должен быть хотя бы один пользовательский индекс
        user_indexes = [i for i in indexes if not i.startswith('sqlite_')]
        assert len(user_indexes) > 0

    def test_idempotent(self, migrator_full):
        migrator_full.create_performance_indexes()
        migrator_full.create_performance_indexes()


# ============================================================================
# ТЕСТЫ: add_missing_fields_rates_payments_salaries
# ============================================================================

class TestAddMissingFieldsRatesPaymentsSalaries:
    """Миграция: недостающие поля в rates, payments, salaries."""

    def test_runs_without_error(self, migrator_full):
        """Миграция выполняется без ошибок."""
        migrator_full.create_payments_system_tables()
        migrator_full.add_missing_fields_rates_payments_salaries()

    def test_idempotent(self, migrator_full):
        migrator_full.create_payments_system_tables()
        migrator_full.add_missing_fields_rates_payments_salaries()
        migrator_full.add_missing_fields_rates_payments_salaries()


# ============================================================================
# ТЕСТЫ: fix_payments_contract_id_nullable
# ============================================================================

class TestFixPaymentsContractIdNullable:
    """Миграция: contract_id nullable в payments."""

    def test_runs_without_error(self, migrator_full):
        """Миграция выполняется без ошибок."""
        migrator_full.create_payments_system_tables()
        migrator_full.fix_payments_contract_id_nullable()

    def test_idempotent(self, migrator_full):
        migrator_full.create_payments_system_tables()
        migrator_full.fix_payments_contract_id_nullable()
        migrator_full.fix_payments_contract_id_nullable()


# ============================================================================
# ТЕСТЫ: run_migrations (полный pipeline)
# ============================================================================

class TestRunMigrations:
    """Полный pipeline миграций."""

    def test_run_on_initialized_db(self, migrator_full):
        """run_migrations на инициализированной БД не падает."""
        migrator_full.run_migrations()

    def test_run_migrations_idempotent(self, migrator_full):
        """Повторный вызов не вызывает ошибок."""
        migrator_full.run_migrations()
        migrator_full.run_migrations()

    def test_run_migrations_creates_approval_columns(self, migrator_full):
        """run_migrations добавляет approval_deadline и approval_stages."""
        migrator_full.run_migrations()
        cols = _get_columns(migrator_full.db_path, 'crm_cards')
        assert 'approval_deadline' in cols
        assert 'approval_stages' in cols

    def test_run_migrations_creates_cities(self, migrator_full):
        """run_migrations создаёт таблицу cities."""
        migrator_full.run_migrations()
        assert _table_exists(migrator_full.db_path, 'cities')


# ============================================================================
# ТЕСТЫ: Upgrade path (sequential migrations на реальном DatabaseManager)
# ============================================================================

class TestUpgradePath:
    """Тест последовательного применения всех миграций."""

    def test_full_upgrade_path(self, empty_db):
        """Полный upgrade path: initialize -> run_migrations -> all individual migrations."""
        m = TestMigrator(empty_db)

        # 1. Инициализация
        m.initialize_database()
        assert _table_exists(empty_db, 'employees')
        assert _table_exists(empty_db, 'contracts')

        # 2. Полный pipeline миграций
        m.run_migrations()

        # 3. Дополнительные миграции (из db_manager.__init__)
        m.create_supervision_table_migration()
        m.fix_supervision_cards_column_name()
        m.create_supervision_history_table()
        m.create_manager_acceptance_table()
        m.create_payments_system_tables()
        m.add_reassigned_field_to_payments()
        m.add_submitted_date_to_stage_executors()
        m.add_stage_field_to_payments()
        m.add_contract_file_columns()
        m.create_project_files_table()
        m.create_project_templates_table()
        m.create_timeline_tables()
        m.add_project_subtype_to_contracts()
        m.add_floors_to_contracts()
        m.create_stage_workflow_state_table()
        m.create_messenger_tables()
        m.create_performance_indexes()
        m.add_missing_fields_rates_payments_salaries()
        m.fix_payments_contract_id_nullable()

        # 4. Проверяем что всё создано
        expected_tables = [
            'employees', 'clients', 'contracts', 'crm_cards',
            'stage_executors', 'salaries', 'action_history', 'agents',
            'supervision_cards', 'supervision_project_history',
            'manager_stage_acceptance', 'payments', 'rates',
            'project_files', 'contract_templates',
            'project_timeline_entries', 'stage_workflow_state',
            'messenger_settings', 'messenger_scripts',
            'user_permissions', 'cities',
        ]
        for table in expected_tables:
            assert _table_exists(empty_db, table), f"Таблица {table} не создана"

    def test_migrations_from_scratch_dont_crash(self, empty_db):
        """Миграции на пустой БД (до initialize) не крашатся."""
        m = TestMigrator(empty_db)
        # run_migrations на пустой БД (без таблиц) — должен ловить ошибки
        m.run_migrations()  # Не должно бросить исключение


# ============================================================================
# ТЕСТЫ: add_birth_date / add_address / add_secondary_position — data preservation
# ============================================================================

class TestDataPreservationMigrations:
    """Проверка что ALTER TABLE миграции сохраняют данные."""

    def test_birth_date_preserves_data(self, migrator):
        """add_birth_date_column сохраняет существующие данные."""
        conn = sqlite3.connect(migrator.db_path)
        conn.execute("INSERT INTO employees (id, full_name, status) VALUES (1, 'Тест', 'активный')")
        conn.commit()
        conn.close()

        migrator.add_birth_date_column()

        conn = sqlite3.connect(migrator.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT full_name, birth_date FROM employees WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        assert row['full_name'] == 'Тест'
        assert row['birth_date'] is None  # Новая колонка — NULL

    def test_address_preserves_data(self, migrator):
        """add_address_column сохраняет существующие данные."""
        conn = sqlite3.connect(migrator.db_path)
        conn.execute("INSERT INTO employees (id, full_name) VALUES (1, 'Тест Адрес')")
        conn.commit()
        conn.close()

        migrator.add_address_column()

        conn = sqlite3.connect(migrator.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT full_name FROM employees WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        assert row['full_name'] == 'Тест Адрес'

    def test_secondary_position_preserves_data(self, migrator):
        """add_secondary_position_column сохраняет существующие данные."""
        conn = sqlite3.connect(migrator.db_path)
        conn.execute("INSERT INTO employees (id, full_name, position) VALUES (1, 'Тест', 'Дизайнер')")
        conn.commit()
        conn.close()

        migrator.add_secondary_position_column()

        conn = sqlite3.connect(migrator.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT full_name, position FROM employees WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        assert row['full_name'] == 'Тест'
        assert row['position'] == 'Дизайнер'


# ============================================================================
# ТЕСТЫ: add_status_changed_date_column
# ============================================================================

class TestAddStatusChangedDateColumn:
    """Миграция status_changed_date (расширенные)."""

    def test_adds_to_contracts(self, migrator):
        """Добавляет status_changed_date в contracts."""
        migrator.add_status_changed_date_column()
        cols = _get_columns(migrator.db_path, 'contracts')
        assert 'status_changed_date' in cols

    def test_idempotent(self, migrator):
        migrator.add_status_changed_date_column()
        migrator.add_status_changed_date_column()

    def test_default_null(self, migrator):
        """Новая колонка имеет NULL по умолчанию."""
        conn = sqlite3.connect(migrator.db_path)
        conn.execute("INSERT INTO contracts (id, contract_number) VALUES (1, 'T1')")
        conn.commit()
        conn.close()

        migrator.add_status_changed_date_column()

        conn = sqlite3.connect(migrator.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT status_changed_date FROM contracts WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        assert row['status_changed_date'] is None


# ============================================================================
# ТЕСТЫ: add_third_payment_field — расширенные
# ============================================================================

class TestAddThirdPaymentFieldExtended:
    """Расширенные тесты для third_payment."""

    def test_default_value_zero(self, migrator):
        """third_payment имеет DEFAULT 0."""
        conn = sqlite3.connect(migrator.db_path)
        conn.execute("INSERT INTO contracts (id, contract_number) VALUES (1, 'TP1')")
        conn.commit()
        conn.close()

        migrator.add_third_payment_field()

        conn = sqlite3.connect(migrator.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT third_payment FROM contracts WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        assert row['third_payment'] == 0

    def test_preserves_data(self, migrator):
        """Существующие данные не теряются."""
        conn = sqlite3.connect(migrator.db_path)
        conn.execute("INSERT INTO contracts (id, contract_number, status) VALUES (1, 'TP2', 'Новый')")
        conn.commit()
        conn.close()

        migrator.add_third_payment_field()

        conn = sqlite3.connect(migrator.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT contract_number, status FROM contracts WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        assert row['contract_number'] == 'TP2'
        assert row['status'] == 'Новый'
