# -*- coding: utf-8 -*-
"""
DB Test Configuration - Temporary SQLite Database
Каждый тест получает чистую временную БД с примененными миграциями.
"""

import pytest
import os
import sys
import tempfile
import shutil

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture(scope="function")
def temp_db_path():
    """Путь к временной БД (удаляется после теста)"""
    tmp_dir = tempfile.mkdtemp(prefix="test_crm_db_")
    db_path = os.path.join(tmp_dir, "test_interior_studio.db")
    yield db_path
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def db(temp_db_path):
    """
    DatabaseManager с временной SQLite БД.
    Порядок: создаём таблицы → запускаем миграции (иначе миграции молча провалятся).
    """
    import database.db_manager as db_module

    # Шаг 1: Создаём DatabaseManager БЕЗ миграций (таблиц ещё нет)
    db_module._migrations_completed = True
    db_manager = db_module.DatabaseManager(temp_db_path)

    # Шаг 2: Создаём все базовые таблицы
    db_manager.initialize_database()

    # Шаг 3: Запускаем ВСЕ миграции (и gated, и standalone) — таблицы уже есть
    # Gated миграции (в production требуют database/migrations.py)
    try:
        db_manager.add_approval_deadline_field()
    except Exception:
        pass
    try:
        db_manager.add_approval_stages_field()
    except Exception:
        pass
    try:
        db_manager.create_approval_deadlines_table()
    except Exception:
        pass
    try:
        db_manager.add_project_data_link_field()
    except Exception:
        pass
    db_manager.add_third_payment_field()
    db_manager.add_birth_date_column()
    db_manager.add_address_column()
    db_manager.add_secondary_position_column()
    db_manager.add_status_changed_date_column()
    db_manager.add_tech_task_fields()
    db_manager.add_survey_date_column()

    # Standalone миграции
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
    db_manager.create_performance_indexes()

    yield db_manager

    try:
        db_manager.close()
    except Exception:
        pass

    db_module._migrations_completed = False


@pytest.fixture(scope="function")
def db_with_data(db):
    """
    DatabaseManager с предзаполненными тестовыми данными.
    Содержит: 1 клиент, 1 договор, 1 сотрудник.
    """
    conn = db.connect()
    cursor = conn.cursor()

    # Тестовый клиент
    cursor.execute("""
        INSERT INTO clients (client_type, full_name, phone, email)
        VALUES ('Физическое лицо', '__TEST__Клиент', '+79991234567', 'test@test.com')
    """)
    client_id = cursor.lastrowid

    # Тестовый сотрудник
    cursor.execute("""
        INSERT INTO employees (full_name, phone, position, department, login, password, role, status)
        VALUES ('__TEST__Сотрудник', '+79990000000', 'Дизайнер', 'Проектный', '__test_emp', 'hash', 'Дизайнер', 'активный')
    """)
    employee_id = cursor.lastrowid

    # Тестовый договор
    cursor.execute("""
        INSERT INTO contracts (client_id, project_type, agent_type, city,
                             contract_number, address, area, total_amount, status)
        VALUES (?, 'Индивидуальный', 'ФЕСТИВАЛЬ', 'СПБ',
                '__TEST__001', 'Тестовый адрес', 75.0, 300000, 'Новый заказ')
    """, (client_id,))
    contract_id = cursor.lastrowid

    conn.commit()
    db.close()

    db._test_data = {
        'client_id': client_id,
        'employee_id': employee_id,
        'contract_id': contract_id,
    }

    return db
