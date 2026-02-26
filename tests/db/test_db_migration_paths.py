# -*- coding: utf-8 -*-
"""
DB Tests: Пути миграции БД
Проверяет создание БД с нуля, типы колонок, идемпотентность миграций,
foreign keys, DEFAULT-значения, индексы, каскадные зависимости и offline-таблицы.
"""

import pytest
import sqlite3
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==============================================================
# Вспомогательные функции
# ==============================================================

def _table_exists(conn, table_name):
    """Проверяет, существует ли таблица"""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def _get_column_info(conn, table_name):
    """Возвращает словарь {имя_колонки: {cid, name, type, notnull, dflt_value, pk}}"""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = {}
    for row in cursor.fetchall():
        columns[row[1]] = {
            'cid': row[0],
            'name': row[1],
            'type': row[2],
            'notnull': row[3],
            'dflt_value': row[4],
            'pk': row[5],
        }
    return columns


def _get_index_names(conn):
    """Возвращает список имён всех индексов"""
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
    return [row[0] for row in cursor.fetchall()]


def _get_foreign_keys(conn, table_name):
    """Возвращает список foreign key constraint-ов для таблицы"""
    cursor = conn.execute(f"PRAGMA foreign_key_list({table_name})")
    return cursor.fetchall()


def _create_fresh_db(tmp_path):
    """Создаёт свежую БД через DatabaseManager.initialize_database() + все миграции.
    Возвращает (db_manager, sqlite3.Connection)."""
    import database.db_manager as db_module

    db_path = os.path.join(str(tmp_path), "migration_test.db")

    # Создаём DatabaseManager без авто-миграций
    db_module._migrations_completed = True
    db_manager = db_module.DatabaseManager(db_path)

    # Шаг 1: Создание базовых таблиц
    db_manager.initialize_database()

    # Шаг 2: Запуск всех миграций (gated)
    for method in [
        'add_approval_deadline_field',
        'add_approval_stages_field',
        'create_approval_deadlines_table',
        'add_project_data_link_field',
        'add_third_payment_field',
        'add_birth_date_column',
        'add_address_column',
        'add_secondary_position_column',
        'add_status_changed_date_column',
        'add_tech_task_fields',
        'add_survey_date_column',
        'add_payment_tracking_fields',
        'add_signed_acts_fields',
        'create_user_permissions_table',
        'create_role_default_permissions_table',
        'create_norm_days_templates_table',
        'add_agent_type_to_norm_days_templates',
        'add_custom_norm_days_column',
        'add_employee_multiuser_fields',
    ]:
        try:
            getattr(db_manager, method)()
        except Exception:
            pass

    # Шаг 3: Standalone миграции
    db_manager.create_supervision_table_migration()
    db_manager.fix_supervision_cards_column_name()
    db_manager.create_supervision_history_table()
    db_manager.create_manager_acceptance_table()
    db_manager.create_payments_system_tables()
    db_manager.add_reassigned_field_to_payments()
    db_manager.add_submitted_date_to_stage_executors()
    db_manager.add_stage_field_to_payments()
    db_manager.add_contract_file_columns()
    db_manager.create_project_files_table()
    db_manager.create_project_templates_table()
    db_manager.create_timeline_tables()
    db_manager.add_project_subtype_to_contracts()
    db_manager.add_floors_to_contracts()
    db_manager.create_stage_workflow_state_table()
    db_manager.create_messenger_tables()
    db_manager.create_performance_indexes()
    db_manager.add_missing_fields_rates_payments_salaries()
    try:
        db_manager.add_agents_status_field()
    except Exception:
        pass
    try:
        db_manager.migrate_add_cities_table()
    except Exception:
        pass

    # Получаем сырое соединение
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Сбрасываем флаг для следующих тестов
    db_module._migrations_completed = False

    return db_manager, conn


# ==============================================================
# 1. Создание БД с нуля — все таблицы создаются без ошибок
# ==============================================================

class TestFreshDatabaseCreation:
    """Создание БД с нуля: проверяет, что все таблицы создаются без ошибок"""

    def test_fresh_db_creates_without_errors(self, tmp_path):
        """Создание БД с нуля не выбрасывает исключений"""
        db_manager, conn = _create_fresh_db(tmp_path)
        # Если дошли сюда — ошибок не было
        assert conn is not None
        conn.close()

    def test_all_core_tables_exist(self, tmp_path):
        """Все основные таблицы присутствуют после инициализации"""
        _, conn = _create_fresh_db(tmp_path)

        core_tables = [
            'employees', 'clients', 'contracts', 'crm_cards',
            'stage_executors', 'salaries', 'action_history',
            'agents', 'supervision_cards', 'payments', 'rates',
            'project_files', 'project_templates',
        ]

        for table in core_tables:
            assert _table_exists(conn, table), f"Отсутствует таблица: {table}"

        conn.close()

    def test_migration_tables_exist(self, tmp_path):
        """Таблицы, создаваемые миграциями, присутствуют"""
        _, conn = _create_fresh_db(tmp_path)

        migration_tables = [
            'approval_stage_deadlines',
            'supervision_project_history',
            'manager_stage_acceptance',
            'surveys',
            'crm_supervision',
            'project_timeline_entries',
            'supervision_timeline_entries',
            'stage_workflow_state',
            'user_permissions',
            'role_default_permissions',
            'norm_days_templates',
        ]

        for table in migration_tables:
            assert _table_exists(conn, table), f"Отсутствует таблица миграции: {table}"

        conn.close()


# ==============================================================
# 2. Типы колонок
# ==============================================================

class TestColumnTypes:
    """Проверка правильных типов колонок в ключевых таблицах"""

    def test_contracts_column_types(self, tmp_path):
        """Таблица contracts имеет правильные типы колонок"""
        _, conn = _create_fresh_db(tmp_path)
        columns = _get_column_info(conn, 'contracts')

        expected_types = {
            'id': 'INTEGER',
            'client_id': 'INTEGER',
            'project_type': 'TEXT',
            'contract_number': 'TEXT',
            'address': 'TEXT',
            'area': 'REAL',
            'total_amount': 'REAL',
            'advance_payment': 'REAL',
            'third_payment': 'REAL',
            'contract_period': 'INTEGER',
            'floors': 'INTEGER',
            'status': 'TEXT',
        }

        for col_name, expected_type in expected_types.items():
            assert col_name in columns, f"Отсутствует колонка {col_name} в contracts"
            actual_type = columns[col_name]['type'].upper()
            # SQLite допускает вариации вроде 'REAL DEFAULT 0', берём первое слово
            # Но PRAGMA table_info возвращает чистый тип
            assert expected_type in actual_type, (
                f"Колонка {col_name}: ожидался тип {expected_type}, получен {actual_type}"
            )

        conn.close()

    def test_employees_column_types(self, tmp_path):
        """Таблица employees имеет правильные типы колонок"""
        _, conn = _create_fresh_db(tmp_path)
        columns = _get_column_info(conn, 'employees')

        expected_types = {
            'id': 'INTEGER',
            'full_name': 'TEXT',
            'phone': 'TEXT',
            'login': 'TEXT',
            'role': 'TEXT',
            'position': 'TEXT',
        }

        for col_name, expected_type in expected_types.items():
            assert col_name in columns, f"Отсутствует колонка {col_name} в employees"
            assert expected_type in columns[col_name]['type'].upper(), (
                f"Колонка employees.{col_name}: ожидался {expected_type}, "
                f"получен {columns[col_name]['type']}"
            )

        conn.close()

    def test_payments_column_types(self, tmp_path):
        """Таблица payments имеет числовые колонки с типом REAL"""
        _, conn = _create_fresh_db(tmp_path)
        columns = _get_column_info(conn, 'payments')

        numeric_cols = ['calculated_amount', 'final_amount']
        for col_name in numeric_cols:
            assert col_name in columns, f"Отсутствует колонка {col_name} в payments"
            assert 'REAL' in columns[col_name]['type'].upper(), (
                f"Колонка payments.{col_name}: ожидался REAL, "
                f"получен {columns[col_name]['type']}"
            )

        conn.close()


# ==============================================================
# 3-4. Миграция: ADD COLUMN + идемпотентность
# ==============================================================

class TestMigrationIdempotency:
    """Миграция добавляет колонку если её нет, повторная миграция не падает"""

    def test_add_third_payment_idempotent(self, tmp_path):
        """add_third_payment_field: повторный вызов не вызывает ошибку"""
        db_manager, conn = _create_fresh_db(tmp_path)
        conn.close()

        # Вызываем миграцию повторно — не должна упасть
        db_manager.add_third_payment_field()
        db_manager.add_third_payment_field()

        # Проверяем что колонка существует
        conn2 = db_manager.connect()
        cols = _get_column_info(conn2, 'contracts')
        assert 'third_payment' in cols
        db_manager.close()

    def test_add_birth_date_idempotent(self, tmp_path):
        """add_birth_date_column: повторный вызов не вызывает ошибку"""
        db_manager, conn = _create_fresh_db(tmp_path)
        conn.close()

        db_manager.add_birth_date_column()
        db_manager.add_birth_date_column()

        conn2 = db_manager.connect()
        cols = _get_column_info(conn2, 'employees')
        assert 'birth_date' in cols
        db_manager.close()

    def test_add_approval_deadline_idempotent(self, tmp_path):
        """add_approval_deadline_field: повторный вызов не вызывает ошибку"""
        db_manager, conn = _create_fresh_db(tmp_path)
        conn.close()

        db_manager.add_approval_deadline_field()
        db_manager.add_approval_deadline_field()

        conn2 = db_manager.connect()
        cols = _get_column_info(conn2, 'crm_cards')
        assert 'approval_deadline' in cols
        db_manager.close()

    def test_create_project_files_table_idempotent(self, tmp_path):
        """create_project_files_table: повторный вызов не падает"""
        db_manager, conn = _create_fresh_db(tmp_path)
        conn.close()

        db_manager.create_project_files_table()
        db_manager.create_project_files_table()

        conn2 = db_manager.connect()
        assert _table_exists(conn2, 'project_files')
        db_manager.close()

    def test_create_supervision_table_idempotent(self, tmp_path):
        """create_supervision_table_migration: повторный вызов не падает"""
        db_manager, conn = _create_fresh_db(tmp_path)
        conn.close()

        db_manager.create_supervision_table_migration()
        db_manager.create_supervision_table_migration()

        conn2 = db_manager.connect()
        assert _table_exists(conn2, 'supervision_cards')
        db_manager.close()

    def test_full_migration_chain_idempotent(self, tmp_path):
        """Полная цепочка миграций идемпотентна: двойной прогон не падает"""
        db_manager, conn = _create_fresh_db(tmp_path)
        conn.close()

        # Прогоняем ВСЮ цепочку миграций повторно
        migration_methods = [
            'add_approval_deadline_field',
            'add_approval_stages_field',
            'create_approval_deadlines_table',
            'add_project_data_link_field',
            'add_third_payment_field',
            'add_birth_date_column',
            'add_address_column',
            'add_secondary_position_column',
            'add_status_changed_date_column',
            'add_tech_task_fields',
            'add_survey_date_column',
            'add_payment_tracking_fields',
            'add_signed_acts_fields',
            'create_user_permissions_table',
            'create_role_default_permissions_table',
            'create_norm_days_templates_table',
            'add_employee_multiuser_fields',
            'create_supervision_table_migration',
            'fix_supervision_cards_column_name',
            'create_supervision_history_table',
            'create_manager_acceptance_table',
            'create_payments_system_tables',
            'add_reassigned_field_to_payments',
            'add_submitted_date_to_stage_executors',
            'add_stage_field_to_payments',
            'add_contract_file_columns',
            'create_project_files_table',
            'create_project_templates_table',
            'create_timeline_tables',
            'add_project_subtype_to_contracts',
            'add_floors_to_contracts',
            'create_stage_workflow_state_table',
            'create_messenger_tables',
            'create_performance_indexes',
            'add_missing_fields_rates_payments_salaries',
        ]

        for method_name in migration_methods:
            getattr(db_manager, method_name)()

        # Должны дойти сюда без исключений
        conn2 = db_manager.connect()
        assert _table_exists(conn2, 'contracts')
        db_manager.close()


# ==============================================================
# 5. Foreign key constraints
# ==============================================================

class TestForeignKeys:
    """Foreign key constraints работают корректно"""

    def test_contracts_references_clients(self, tmp_path):
        """Таблица contracts имеет FK на clients"""
        _, conn = _create_fresh_db(tmp_path)
        fks = _get_foreign_keys(conn, 'contracts')
        fk_tables = [fk[2] for fk in fks]
        assert 'clients' in fk_tables, (
            f"contracts не ссылается на clients. FK: {fk_tables}"
        )
        conn.close()

    def test_crm_cards_references_contracts(self, tmp_path):
        """Таблица crm_cards имеет FK на contracts"""
        _, conn = _create_fresh_db(tmp_path)
        fks = _get_foreign_keys(conn, 'crm_cards')
        fk_tables = [fk[2] for fk in fks]
        assert 'contracts' in fk_tables, (
            f"crm_cards не ссылается на contracts. FK: {fk_tables}"
        )
        conn.close()

    def test_stage_executors_references_crm_cards_and_employees(self, tmp_path):
        """Таблица stage_executors имеет FK на crm_cards и employees"""
        _, conn = _create_fresh_db(tmp_path)
        fks = _get_foreign_keys(conn, 'stage_executors')
        fk_tables = [fk[2] for fk in fks]
        assert 'crm_cards' in fk_tables, (
            f"stage_executors не ссылается на crm_cards. FK: {fk_tables}"
        )
        assert 'employees' in fk_tables, (
            f"stage_executors не ссылается на employees. FK: {fk_tables}"
        )
        conn.close()

    def test_payments_references_contracts_and_employees(self, tmp_path):
        """Таблица payments имеет FK на contracts и employees"""
        _, conn = _create_fresh_db(tmp_path)
        fks = _get_foreign_keys(conn, 'payments')
        fk_tables = [fk[2] for fk in fks]
        assert 'contracts' in fk_tables, (
            f"payments не ссылается на contracts. FK: {fk_tables}"
        )
        assert 'employees' in fk_tables, (
            f"payments не ссылается на employees. FK: {fk_tables}"
        )
        conn.close()

    def test_project_files_references_contracts_with_cascade(self, tmp_path):
        """project_files имеет FK на contracts с ON DELETE CASCADE"""
        _, conn = _create_fresh_db(tmp_path)
        fks = _get_foreign_keys(conn, 'project_files')
        # PRAGMA foreign_key_list: (id, seq, table, from, to, on_update, on_delete, match)
        for fk in fks:
            if fk[2] == 'contracts':
                # on_delete = fk[6]
                assert fk[6] == 'CASCADE', (
                    f"project_files FK на contracts: ожидался ON DELETE CASCADE, "
                    f"получен {fk[6]}"
                )
                break
        else:
            pytest.fail("project_files не имеет FK на contracts")
        conn.close()

    def test_fk_enforcement_with_pragma(self, tmp_path):
        """FK enforcement работает при включённом PRAGMA foreign_keys"""
        _, conn = _create_fresh_db(tmp_path)
        conn.execute("PRAGMA foreign_keys = ON")

        # Попытка вставить договор с несуществующим client_id
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO contracts (client_id, project_type, contract_number) "
                "VALUES (99999, 'Тест', 'FK-TEST-001')"
            )
        conn.close()


# ==============================================================
# 6. DEFAULT-значения
# ==============================================================

class TestDefaultValues:
    """DEFAULT значения применяются корректно"""

    def test_contracts_status_default(self, tmp_path):
        """Договор получает DEFAULT статус при создании"""
        _, conn = _create_fresh_db(tmp_path)

        # Вставляем клиента, потом договор без указания status
        conn.execute(
            "INSERT INTO clients (client_type, full_name, phone) "
            "VALUES ('Физ. лицо', 'Тест', '+70000000000')"
        )
        client_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.execute(
            "INSERT INTO contracts (client_id, project_type, contract_number) "
            "VALUES (?, 'Индивидуальный', 'DEF-TEST-001')",
            (client_id,)
        )
        conn.commit()

        row = conn.execute(
            "SELECT status FROM contracts WHERE contract_number = 'DEF-TEST-001'"
        ).fetchone()
        assert row is not None
        assert row[0] == 'Новый заказ', f"Ожидался DEFAULT 'Новый заказ', получен '{row[0]}'"
        conn.close()

    def test_crm_cards_is_approved_default(self, tmp_path):
        """crm_cards.is_approved имеет DEFAULT 0"""
        _, conn = _create_fresh_db(tmp_path)
        columns = _get_column_info(conn, 'crm_cards')
        assert 'is_approved' in columns
        assert columns['is_approved']['dflt_value'] in ('0', '0.0', None, 'FALSE'), (
            f"Ожидался DEFAULT 0 для is_approved, получен {columns['is_approved']['dflt_value']}"
        )
        conn.close()

    def test_employees_status_default(self, tmp_path):
        """employees.status имеет DEFAULT 'активный'"""
        _, conn = _create_fresh_db(tmp_path)
        columns = _get_column_info(conn, 'employees')
        assert 'status' in columns
        dflt = columns['status']['dflt_value']
        assert dflt is not None and 'активный' in dflt, (
            f"Ожидался DEFAULT 'активный' для employees.status, получен {dflt}"
        )
        conn.close()

    def test_floors_default_value(self, tmp_path):
        """contracts.floors имеет DEFAULT 1"""
        _, conn = _create_fresh_db(tmp_path)
        columns = _get_column_info(conn, 'contracts')
        assert 'floors' in columns
        dflt = columns['floors']['dflt_value']
        assert dflt is not None and '1' in str(dflt), (
            f"Ожидался DEFAULT 1 для contracts.floors, получен {dflt}"
        )
        conn.close()


# ==============================================================
# 7. Индексы
# ==============================================================

class TestIndexCreation:
    """Индексы создаются корректно"""

    def test_performance_indexes_created(self, tmp_path):
        """Индексы производительности создаются при миграции"""
        _, conn = _create_fresh_db(tmp_path)
        indexes = _get_index_names(conn)

        expected_indexes = [
            'idx_contracts_client_id',
            'idx_crm_cards_contract_id',
            'idx_crm_cards_column_name',
            'idx_stage_executors_crm_card_id',
            'idx_payments_contract_id',
            'idx_payments_employee_id',
            'idx_supervision_cards_contract_id',
        ]

        for expected in expected_indexes:
            found = any(expected in idx for idx in indexes)
            assert found, f"Не найден индекс {expected}. Имеющиеся: {indexes}"

        conn.close()

    def test_project_files_indexes(self, tmp_path):
        """Таблица project_files имеет индексы по contract_id и stage"""
        _, conn = _create_fresh_db(tmp_path)
        indexes = _get_index_names(conn)

        assert any('project_files_contract' in idx for idx in indexes), (
            f"Не найден индекс project_files по contract. Индексы: {indexes}"
        )
        conn.close()

    def test_messenger_indexes(self, tmp_path):
        """Таблицы мессенджера имеют необходимые индексы"""
        _, conn = _create_fresh_db(tmp_path)
        indexes = _get_index_names(conn)

        expected = [
            'idx_messenger_chats_crm_card',
            'idx_messenger_chats_contract',
            'idx_messenger_members_chat',
            'idx_messenger_log_chat',
        ]

        for idx_name in expected:
            assert any(idx_name in idx for idx in indexes), (
                f"Не найден индекс мессенджера: {idx_name}"
            )
        conn.close()

    def test_timeline_indexes(self, tmp_path):
        """Таблицы timeline имеют индексы"""
        _, conn = _create_fresh_db(tmp_path)
        indexes = _get_index_names(conn)

        assert any('timeline_contract' in idx for idx in indexes), (
            f"Не найден индекс timeline_contract"
        )
        assert any('supervision_timeline_card' in idx for idx in indexes), (
            f"Не найден индекс supervision_timeline_card"
        )
        conn.close()


# ==============================================================
# 8. Каскадное создание зависимых таблиц
# ==============================================================

class TestCascadeDependencies:
    """Каскадное создание зависимых таблиц"""

    def test_contracts_depends_on_clients(self, tmp_path):
        """Нельзя создать договор без клиента при включённых FK"""
        _, conn = _create_fresh_db(tmp_path)
        conn.execute("PRAGMA foreign_keys = ON")

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO contracts (client_id, project_type, contract_number) "
                "VALUES (99999, 'Тест', 'CASCADE-001')"
            )
        conn.close()

    def test_cascade_delete_project_files(self, tmp_path):
        """Удаление договора каскадно удаляет project_files (ON DELETE CASCADE)"""
        _, conn = _create_fresh_db(tmp_path)
        conn.execute("PRAGMA foreign_keys = ON")

        # Создаём клиента → договор → файл
        conn.execute(
            "INSERT INTO clients (client_type, full_name, phone) "
            "VALUES ('Физ. лицо', 'Тест каскада', '+70001112233')"
        )
        client_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.execute(
            "INSERT INTO contracts (client_id, project_type, contract_number) "
            "VALUES (?, 'Индивидуальный', 'CASCADE-DEL-001')",
            (client_id,)
        )
        contract_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.execute(
            "INSERT INTO project_files (contract_id, stage, file_type, yandex_path, file_name) "
            "VALUES (?, 'Планировки', 'image', '/path/test.png', 'test.png')",
            (contract_id,)
        )
        conn.commit()

        # Проверяем что файл есть
        count = conn.execute(
            "SELECT COUNT(*) FROM project_files WHERE contract_id = ?",
            (contract_id,)
        ).fetchone()[0]
        assert count == 1

        # Удаляем договор
        conn.execute("DELETE FROM contracts WHERE id = ?", (contract_id,))
        conn.commit()

        # Файлы должны быть удалены каскадно
        count_after = conn.execute(
            "SELECT COUNT(*) FROM project_files WHERE contract_id = ?",
            (contract_id,)
        ).fetchone()[0]
        assert count_after == 0, "project_files не удалены каскадно при удалении contracts"

        conn.close()

    def test_cascade_delete_crm_cards_timeline(self, tmp_path):
        """Удаление договора каскадно удаляет project_timeline_entries"""
        _, conn = _create_fresh_db(tmp_path)
        conn.execute("PRAGMA foreign_keys = ON")

        conn.execute(
            "INSERT INTO clients (client_type, full_name, phone) "
            "VALUES ('Физ. лицо', 'Тест timeline', '+70001112244')"
        )
        client_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.execute(
            "INSERT INTO contracts (client_id, project_type, contract_number) "
            "VALUES (?, 'Индивидуальный', 'CASCADE-TL-001')",
            (client_id,)
        )
        contract_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.execute(
            "INSERT INTO project_timeline_entries "
            "(contract_id, stage_code, stage_name, stage_group, executor_role, sort_order) "
            "VALUES (?, 'S1', 'Стадия 1', 'Группа 1', 'Дизайнер', 1)",
            (contract_id,)
        )
        conn.commit()

        count = conn.execute(
            "SELECT COUNT(*) FROM project_timeline_entries WHERE contract_id = ?",
            (contract_id,)
        ).fetchone()[0]
        assert count == 1

        conn.execute("DELETE FROM contracts WHERE id = ?", (contract_id,))
        conn.commit()

        count_after = conn.execute(
            "SELECT COUNT(*) FROM project_timeline_entries WHERE contract_id = ?",
            (contract_id,)
        ).fetchone()[0]
        assert count_after == 0, "project_timeline_entries не удалены каскадно"
        conn.close()


# ==============================================================
# 9. Cities таблица (справочник)
# ==============================================================

class TestCitiesTable:
    """Таблица городов и seed-данные"""

    def test_cities_table_exists(self, tmp_path):
        """Таблица cities создаётся миграцией"""
        _, conn = _create_fresh_db(tmp_path)
        assert _table_exists(conn, 'cities'), "Таблица cities не создана"
        conn.close()

    def test_cities_has_correct_columns(self, tmp_path):
        """Таблица cities имеет колонки id, name, status, created_at"""
        _, conn = _create_fresh_db(tmp_path)
        columns = _get_column_info(conn, 'cities')
        for col in ['id', 'name', 'status', 'created_at']:
            assert col in columns, f"Отсутствует колонка {col} в cities"
        conn.close()

    def test_cities_seed_data(self, tmp_path):
        """Миграция cities засевает дефолтные города (СПБ, МСК, ВН)"""
        _, conn = _create_fresh_db(tmp_path)
        rows = conn.execute("SELECT name FROM cities ORDER BY name").fetchall()
        city_names = [r[0] for r in rows]

        for expected_city in ['СПБ', 'МСК', 'ВН']:
            assert expected_city in city_names, (
                f"Город {expected_city} не найден в seed-данных cities. Имеющиеся: {city_names}"
            )
        conn.close()

    def test_cities_status_default(self, tmp_path):
        """Город получает DEFAULT статус 'активный'"""
        _, conn = _create_fresh_db(tmp_path)
        columns = _get_column_info(conn, 'cities')
        dflt = columns['status']['dflt_value']
        assert dflt is not None and 'активный' in dflt, (
            f"Ожидался DEFAULT 'активный' для cities.status, получен {dflt}"
        )
        conn.close()


# ==============================================================
# 10. Offline-таблицы (offline_queue / sync)
# ==============================================================

class TestOfflineTables:
    """Проверка таблиц для offline-режима"""

    def test_messenger_settings_table_exists(self, tmp_path):
        """Таблица messenger_settings для offline-конфига существует"""
        _, conn = _create_fresh_db(tmp_path)
        assert _table_exists(conn, 'messenger_settings')
        conn.close()

    def test_action_history_for_audit_trail(self, tmp_path):
        """Таблица action_history для аудита offline-операций существует с правильными колонками"""
        _, conn = _create_fresh_db(tmp_path)
        assert _table_exists(conn, 'action_history')
        columns = _get_column_info(conn, 'action_history')

        required = ['id', 'user_id', 'action_type', 'entity_type', 'entity_id']
        for col in required:
            assert col in columns, f"Отсутствует колонка {col} в action_history"
        conn.close()


# ==============================================================
# Дополнительные тесты — миграции конкретных колонок
# ==============================================================

class TestSpecificMigrations:
    """Тесты конкретных миграций"""

    def test_employee_multiuser_fields(self, tmp_path):
        """Миграция добавляет multiuser-поля в employees"""
        _, conn = _create_fresh_db(tmp_path)
        columns = _get_column_info(conn, 'employees')

        multiuser_fields = ['is_online', 'last_login', 'last_activity',
                            'current_session_token', 'agent_color']
        for field in multiuser_fields:
            assert field in columns, (
                f"Отсутствует multiuser-поле {field} в employees"
            )
        conn.close()

    def test_contracts_file_columns(self, tmp_path):
        """Миграция добавляет файловые колонки в contracts"""
        _, conn = _create_fresh_db(tmp_path)
        columns = _get_column_info(conn, 'contracts')

        file_columns = [
            'contract_file_yandex_path', 'contract_file_name',
            'template_contract_file_yandex_path', 'template_contract_file_name',
            'references_yandex_path', 'photo_documentation_yandex_path',
        ]
        for col in file_columns:
            assert col in columns, f"Отсутствует файловая колонка {col} в contracts"
        conn.close()

    def test_payment_tracking_fields(self, tmp_path):
        """Миграция добавляет поля отслеживания платежей в contracts"""
        _, conn = _create_fresh_db(tmp_path)
        columns = _get_column_info(conn, 'contracts')

        tracking_cols = [
            'advance_payment_paid_date',
            'additional_payment_paid_date',
            'third_payment_paid_date',
            'advance_receipt_link',
        ]
        for col in tracking_cols:
            assert col in columns, f"Отсутствует колонка отслеживания платежа {col}"
        conn.close()

    def test_admin_user_created(self, tmp_path):
        """При инициализации создаётся администратор"""
        _, conn = _create_fresh_db(tmp_path)
        admin = conn.execute(
            "SELECT * FROM employees WHERE login = 'admin'"
        ).fetchone()
        assert admin is not None, "Администратор не создан при инициализации"
        conn.close()

    def test_agents_table_with_default_agents(self, tmp_path):
        """Таблица agents содержит дефолтных агентов (ПЕТРОВИЧ, ФЕСТИВАЛЬ)"""
        _, conn = _create_fresh_db(tmp_path)
        agents = conn.execute("SELECT name, color FROM agents ORDER BY name").fetchall()
        agent_names = [a[0] for a in agents]

        assert 'ПЕТРОВИЧ' in agent_names, "Агент ПЕТРОВИЧ не найден"
        assert 'ФЕСТИВАЛЬ' in agent_names, "Агент ФЕСТИВАЛЬ не найден"
        conn.close()

    def test_norm_days_templates_unique_constraint(self, tmp_path):
        """norm_days_templates имеет UNIQUE constraint (project_type, project_subtype, stage_code, agent_type)"""
        _, conn = _create_fresh_db(tmp_path)

        # Вставляем запись
        conn.execute(
            "INSERT INTO norm_days_templates "
            "(project_type, project_subtype, stage_code, stage_name, stage_group, "
            "base_norm_days, executor_role, sort_order, agent_type) "
            "VALUES ('Индивидуальный', 'Квартира', 'S1', 'Стадия 1', 'Группа 1', "
            "5.0, 'Дизайнер', 1, 'Все агенты')"
        )
        conn.commit()

        # Попытка вставить дубликат
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO norm_days_templates "
                "(project_type, project_subtype, stage_code, stage_name, stage_group, "
                "base_norm_days, executor_role, sort_order, agent_type) "
                "VALUES ('Индивидуальный', 'Квартира', 'S1', 'Стадия 1', 'Группа 1', "
                "10.0, 'Дизайнер', 2, 'Все агенты')"
            )
        conn.close()

    def test_stage_workflow_state_table(self, tmp_path):
        """Таблица stage_workflow_state создаётся с правильной структурой"""
        _, conn = _create_fresh_db(tmp_path)
        columns = _get_column_info(conn, 'stage_workflow_state')

        required = [
            'id', 'crm_card_id', 'stage_name', 'current_substep_code',
            'status', 'revision_count',
        ]
        for col in required:
            assert col in columns, f"Отсутствует колонка {col} в stage_workflow_state"
        conn.close()

    def test_supervision_timeline_entries_columns(self, tmp_path):
        """supervision_timeline_entries имеет все необходимые колонки"""
        _, conn = _create_fresh_db(tmp_path)
        columns = _get_column_info(conn, 'supervision_timeline_entries')

        required = [
            'id', 'supervision_card_id', 'stage_code', 'stage_name',
            'sort_order', 'budget_planned', 'budget_actual', 'commission',
        ]
        for col in required:
            assert col in columns, (
                f"Отсутствует колонка {col} в supervision_timeline_entries"
            )
        conn.close()
