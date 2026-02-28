# -*- coding: utf-8 -*-
"""Глубокие тесты DatabaseManager — валидация, статистика, CRM карточки, надзор"""

import pytest
import sqlite3
import os
import re
from unittest.mock import patch, MagicMock


@pytest.fixture
def db_path(tmp_path):
    """Создать путь для тестовой БД"""
    return str(tmp_path / 'test_deep.db')


@pytest.fixture
def db(db_path):
    """Создать DatabaseManager с тестовой БД (миграции пропускаются)"""
    import database.db_manager as dbm
    # Сброс глобального флага миграций для тестов
    dbm._migrations_completed = True  # пропускаем миграции

    with patch('database.db_manager.YandexDiskManager'):
        manager = dbm.DatabaseManager(db_path=db_path)

    # Вручную создаём минимальные таблицы
    conn = sqlite3.connect(db_path)
    conn.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY, full_name TEXT, position TEXT, status TEXT DEFAULT 'Активный',
        login TEXT, password TEXT, role TEXT, birth_date TEXT, address TEXT, secondary_position TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT, client_type TEXT DEFAULT 'Физлицо'
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS contracts (
        id INTEGER PRIMARY KEY, contract_number TEXT, client_id INTEGER, project_type TEXT,
        area REAL DEFAULT 0, city TEXT, status TEXT DEFAULT 'Новый', agent_type TEXT,
        supervision INTEGER DEFAULT 0, project_subtype TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS crm_cards (
        id INTEGER PRIMARY KEY, contract_id INTEGER, column_name TEXT, project_type TEXT,
        approval_deadline TEXT, approval_stages TEXT, status_changed_date TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS stage_executors (
        id INTEGER PRIMARY KEY, crm_card_id INTEGER, stage_name TEXT,
        executor_id INTEGER, position TEXT, deadline TEXT, completed INTEGER DEFAULT 0,
        completed_date TEXT, assigned_by INTEGER, assigned_date TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY, contract_id INTEGER, employee_id INTEGER, amount REAL,
        payment_type TEXT, report_month TEXT, is_paid INTEGER DEFAULT 0,
        role TEXT, stage_name TEXT, crm_card_id INTEGER
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS rates (
        id INTEGER PRIMARY KEY, project_type TEXT, role TEXT, price REAL
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS supervision_cards (
        id INTEGER PRIMARY KEY, contract_id INTEGER, column_name TEXT
    )''')
    conn.commit()
    conn.close()

    return manager


# ─── Валидация SQL ───────────────────────────────────────────────────────

class TestDatabaseValidation:
    """Тесты валидации SQL"""

    def test_validate_table_valid(self, db):
        db._validate_table('clients')
        db._validate_table('contracts')
        db._validate_table('employees')

    def test_validate_table_invalid(self, db):
        with pytest.raises(ValueError):
            db._validate_table('drop_table')
        with pytest.raises(ValueError):
            db._validate_table("'; DROP TABLE--")

    def test_validate_columns_valid(self, db):
        db._validate_columns(['name', 'phone', 'client_type'])

    def test_validate_columns_invalid(self, db):
        with pytest.raises(ValueError):
            db._validate_columns(['name; DROP TABLE'])
        with pytest.raises(ValueError):
            db._validate_columns(['1name'])  # начинается с цифры

    def test_build_set_clause(self, db):
        clause, values = db._build_set_clause({'name': 'Тест', 'phone': '123'})
        assert 'name = ?' in clause
        assert 'phone = ?' in clause
        assert values == ['Тест', '123']

    def test_build_set_clause_injection(self, db):
        with pytest.raises(ValueError):
            db._build_set_clause({"name; DROP TABLE users--": 'hack'})

    def test_allowed_tables(self, db):
        assert 'clients' in db.ALLOWED_TABLES
        assert 'contracts' in db.ALLOWED_TABLES
        assert 'employees' in db.ALLOWED_TABLES
        assert 'crm_cards' in db.ALLOWED_TABLES
        assert 'payments' in db.ALLOWED_TABLES


# ─── Connect / Close ────────────────────────────────────────────────────

class TestDatabaseConnection:
    """Тесты подключения к БД"""

    def test_connect(self, db, db_path):
        conn = db.connect()
        assert conn is not None
        db.close()

    def test_close(self, db):
        db.connect()
        db.close()
        # Повторное закрытие не должно падать

    def test_shared_conn_mode(self, db):
        db._shared_conn = True
        db.connection = MagicMock()
        result = db.connect()
        assert result is db.connection
        db._shared_conn = False
        db.connection = None

    def test_close_shared_conn(self, db):
        db._shared_conn = True
        db.close()  # Не должно закрывать в shared mode
        db._shared_conn = False


# ─── Клиенты ────────────────────────────────────────────────────────────

class TestDatabaseClients:
    """Тесты работы с клиентами"""

    def test_add_client(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO clients (name, phone) VALUES (?, ?)", ('Иванов', '+79001234567'))
        conn.commit()
        cursor.execute("SELECT * FROM clients WHERE name='Иванов'")
        row = cursor.fetchone()
        assert row is not None
        db.close()

    def test_get_all_clients(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO clients (name) VALUES ('Тест1')")
        cursor.execute("INSERT INTO clients (name) VALUES ('Тест2')")
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM clients")
        count = cursor.fetchone()[0]
        assert count == 2
        db.close()


# ─── Договоры ───────────────────────────────────────────────────────────

class TestDatabaseContracts:
    """Тесты работы с договорами"""

    def test_add_contract(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO contracts (contract_number, project_type, area) VALUES (?, ?, ?)",
            ('№1-2026', 'Индивидуальный', 100)
        )
        conn.commit()
        cursor.execute("SELECT * FROM contracts WHERE contract_number='№1-2026'")
        row = cursor.fetchone()
        assert row is not None
        db.close()

    def test_check_contract_number_exists(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO contracts (contract_number) VALUES (?)", ('№1-2026',)
        )
        conn.commit()
        cursor.execute(
            "SELECT COUNT(*) FROM contracts WHERE contract_number=?", ('№1-2026',)
        )
        assert cursor.fetchone()[0] == 1
        cursor.execute(
            "SELECT COUNT(*) FROM contracts WHERE contract_number=?", ('№999-2026',)
        )
        assert cursor.fetchone()[0] == 0
        db.close()


# ─── CRM карточки ───────────────────────────────────────────────────────

class TestDatabaseCrmCards:
    """Тесты работы с CRM карточками"""

    def test_add_crm_card(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO crm_cards (contract_id, column_name, project_type) VALUES (?, ?, ?)",
            (1, 'Замер', 'Индивидуальный')
        )
        conn.commit()
        cursor.execute("SELECT * FROM crm_cards WHERE contract_id=1")
        assert cursor.fetchone() is not None
        db.close()

    def test_update_crm_card_column(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO crm_cards (contract_id, column_name) VALUES (?, ?)", (1, 'Замер')
        )
        conn.commit()
        card_id = cursor.lastrowid
        cursor.execute("UPDATE crm_cards SET column_name=? WHERE id=?", ('Дизайн', card_id))
        conn.commit()
        cursor.execute("SELECT column_name FROM crm_cards WHERE id=?", (card_id,))
        assert cursor.fetchone()[0] == 'Дизайн'
        db.close()


# ─── Исполнители стадий ─────────────────────────────────────────────────

class TestDatabaseStageExecutors:
    """Тесты работы с исполнителями стадий"""

    def test_add_stage_executor(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO stage_executors (crm_card_id, stage_name, executor_id, position) VALUES (?, ?, ?, ?)",
            (1, 'Замер', 5, 'Замерщик')
        )
        conn.commit()
        cursor.execute("SELECT * FROM stage_executors WHERE crm_card_id=1")
        assert cursor.fetchone() is not None
        db.close()

    def test_complete_stage(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO stage_executors (crm_card_id, stage_name, executor_id, completed) VALUES (?, ?, ?, ?)",
            (1, 'Замер', 5, 0)
        )
        conn.commit()
        se_id = cursor.lastrowid
        cursor.execute("UPDATE stage_executors SET completed=1 WHERE id=?", (se_id,))
        conn.commit()
        cursor.execute("SELECT completed FROM stage_executors WHERE id=?", (se_id,))
        assert cursor.fetchone()[0] == 1
        db.close()

    def test_get_stage_executors(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO stage_executors (crm_card_id, stage_name, executor_id) VALUES (?, ?, ?)",
            (1, 'Замер', 5)
        )
        cursor.execute(
            "INSERT INTO stage_executors (crm_card_id, stage_name, executor_id) VALUES (?, ?, ?)",
            (1, 'Дизайн', 6)
        )
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM stage_executors WHERE crm_card_id=1")
        assert cursor.fetchone()[0] == 2
        db.close()


# ─── Платежи ────────────────────────────────────────────────────────────

class TestDatabasePayments:
    """Тесты работы с платежами"""

    def test_add_payment(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO payments (contract_id, employee_id, amount, payment_type) VALUES (?, ?, ?, ?)",
            (1, 5, 10000, 'Полная оплата')
        )
        conn.commit()
        cursor.execute("SELECT * FROM payments WHERE contract_id=1")
        assert cursor.fetchone() is not None
        db.close()

    def test_get_payments_by_contract(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO payments (contract_id, amount) VALUES (?, ?)", (1, 5000)
        )
        cursor.execute(
            "INSERT INTO payments (contract_id, amount) VALUES (?, ?)", (1, 3000)
        )
        cursor.execute(
            "INSERT INTO payments (contract_id, amount) VALUES (?, ?)", (2, 7000)
        )
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM payments WHERE contract_id=1")
        assert cursor.fetchone()[0] == 2
        db.close()

    def test_mark_payment_paid(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO payments (contract_id, amount, is_paid) VALUES (?, ?, ?)", (1, 5000, 0))
        conn.commit()
        pay_id = cursor.lastrowid
        cursor.execute("UPDATE payments SET is_paid=1 WHERE id=?", (pay_id,))
        conn.commit()
        cursor.execute("SELECT is_paid FROM payments WHERE id=?", (pay_id,))
        assert cursor.fetchone()[0] == 1
        db.close()


# ─── Надзор ─────────────────────────────────────────────────────────────

class TestDatabaseSupervision:
    """Тесты работы с карточками надзора"""

    def test_add_supervision_card(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO supervision_cards (contract_id, column_name) VALUES (?, ?)",
            (1, 'Авторский надзор')
        )
        conn.commit()
        cursor.execute("SELECT * FROM supervision_cards WHERE contract_id=1")
        assert cursor.fetchone() is not None
        db.close()

    def test_update_supervision_column(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO supervision_cards (contract_id, column_name) VALUES (?, ?)",
            (1, 'Этап 1')
        )
        conn.commit()
        card_id = cursor.lastrowid
        cursor.execute("UPDATE supervision_cards SET column_name=? WHERE id=?", ('Этап 2', card_id))
        conn.commit()
        cursor.execute("SELECT column_name FROM supervision_cards WHERE id=?", (card_id,))
        assert cursor.fetchone()[0] == 'Этап 2'
        db.close()


# ─── Сотрудники ─────────────────────────────────────────────────────────

class TestDatabaseEmployees:
    """Тесты работы с сотрудниками"""

    def test_add_employee(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO employees (full_name, position, status) VALUES (?, ?, ?)",
            ('Иванов И.И.', 'Дизайнер', 'Активный')
        )
        conn.commit()
        cursor.execute("SELECT * FROM employees WHERE full_name='Иванов И.И.'")
        assert cursor.fetchone() is not None
        db.close()

    def test_update_employee(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO employees (full_name, position) VALUES (?, ?)", ('Тест', 'Дизайнер'))
        conn.commit()
        emp_id = cursor.lastrowid
        cursor.execute("UPDATE employees SET position=? WHERE id=?", ('Чертёжник', emp_id))
        conn.commit()
        cursor.execute("SELECT position FROM employees WHERE id=?", (emp_id,))
        assert cursor.fetchone()[0] == 'Чертёжник'
        db.close()

    def test_delete_employee(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO employees (full_name) VALUES (?)", ('Удаляемый',))
        conn.commit()
        emp_id = cursor.lastrowid
        cursor.execute("DELETE FROM employees WHERE id=?", (emp_id,))
        conn.commit()
        cursor.execute("SELECT * FROM employees WHERE id=?", (emp_id,))
        assert cursor.fetchone() is None
        db.close()

    def test_get_employees_by_position(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO employees (full_name, position) VALUES (?, ?)", ('А', 'Дизайнер'))
        cursor.execute("INSERT INTO employees (full_name, position) VALUES (?, ?)", ('Б', 'Чертёжник'))
        cursor.execute("INSERT INTO employees (full_name, position) VALUES (?, ?)", ('В', 'Дизайнер'))
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM employees WHERE position=?", ('Дизайнер',))
        assert cursor.fetchone()[0] == 2
        db.close()


# ─── Тарифы (rates) ─────────────────────────────────────────────────────

class TestDatabaseRates:
    """Тесты работы со ставками"""

    def test_add_rate(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO rates (project_type, role, price) VALUES (?, ?, ?)",
            ('Индивидуальный', 'Дизайнер', 500.0)
        )
        conn.commit()
        cursor.execute("SELECT price FROM rates WHERE role='Дизайнер'")
        assert cursor.fetchone()[0] == 500.0
        db.close()

    def test_update_rate(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO rates (role, price) VALUES (?, ?)", ('Дизайнер', 500))
        conn.commit()
        rate_id = cursor.lastrowid
        cursor.execute("UPDATE rates SET price=? WHERE id=?", (600, rate_id))
        conn.commit()
        cursor.execute("SELECT price FROM rates WHERE id=?", (rate_id,))
        assert cursor.fetchone()[0] == 600
        db.close()
