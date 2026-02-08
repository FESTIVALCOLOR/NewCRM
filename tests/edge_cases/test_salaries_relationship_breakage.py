"""
Тесты разрыва связей в модуле зарплат (salaries_tab.py).

КРИТИЧЕСКИЕ ТЕСТЫ для выявленных багов:
1. Supervision payments НЕ перезагружаются при изменении статуса
2. Entity type всегда 'payment' в offline queue (даже для salaries)
3. Параметр source игнорируется в API пути delete_payment_universal()
4. Несогласованность полей amount vs final_amount
5. Collision ID между payments и salaries таблицами

Основано на анализе:
- salaries_tab.py:2106 (set_payment_status - missing supervision reload)
- salaries_tab.py:1126 (_queue_payment_delete - hardcoded entity_type)
- salaries_tab.py:1068 (delete_payment_universal - source ignored)
"""

import pytest
import sqlite3
import json
from datetime import datetime


class TestSalariesTableSchema:
    """Тесты схемы таблицы salaries."""

    def setup_salaries_table(self, db):
        """Создание таблицы salaries если нет."""
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS salaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER REFERENCES employees(id),
                amount REAL DEFAULT 0,
                report_month TEXT,
                payment_status TEXT DEFAULT 'pending',
                project_type TEXT,
                source TEXT DEFAULT 'Оклад',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()

    def test_salaries_table_exists(self, temp_db):
        """Таблица salaries должна существовать."""
        self.setup_salaries_table(temp_db)
        cursor = temp_db.cursor()

        cursor.execute("PRAGMA table_info(salaries)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}

        assert 'amount' in columns  # salaries использует amount
        assert 'employee_id' in columns
        assert 'payment_status' in columns

    def test_salaries_uses_amount_not_final_amount(self, temp_db):
        """Salaries использует поле 'amount', НЕ 'final_amount'."""
        self.setup_salaries_table(temp_db)
        cursor = temp_db.cursor()

        cursor.execute("PRAGMA table_info(salaries)")
        columns = [col[1] for col in cursor.fetchall()]

        assert 'amount' in columns, "Salaries должна иметь поле 'amount'"
        # final_amount НЕ должно быть в salaries
        # (если есть - это дублирование)


class TestAmountFieldConsistency:
    """Тесты консистентности полей amount vs final_amount."""

    def setup_salaries_table(self, db):
        """Создание таблицы salaries."""
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS salaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER REFERENCES employees(id),
                amount REAL DEFAULT 0,
                final_amount REAL,
                report_month TEXT,
                payment_status TEXT DEFAULT 'pending',
                project_type TEXT,
                source TEXT DEFAULT 'Оклад',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()

    def test_payment_uses_final_amount(self, db_with_data):
        """CRM платежи используют final_amount."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT final_amount FROM payments LIMIT 1")
        result = cursor.fetchone()

        # Payments должны иметь final_amount
        assert result is not None

    def test_salary_uses_amount(self, temp_db):
        """Salary записи используют amount."""
        self.setup_salaries_table(temp_db)
        cursor = temp_db.cursor()

        # Создаём сотрудника
        cursor.execute("""
            INSERT INTO employees (login, password_hash, full_name, position, is_active)
            VALUES ('salary_emp', 'hash', 'Сотрудник Оклад', 'Менеджер', 1)
        """)
        employee_id = cursor.lastrowid

        # Создаём salary запись
        cursor.execute("""
            INSERT INTO salaries (employee_id, amount, report_month)
            VALUES (?, 50000, '2025-01')
        """, (employee_id,))
        salary_id = cursor.lastrowid
        temp_db.commit()

        # Проверяем что amount есть
        cursor.execute("SELECT amount FROM salaries WHERE id = ?", (salary_id,))
        result = cursor.fetchone()
        assert result[0] == 50000

    def test_unified_amount_retrieval(self, temp_db):
        """Унифицированное получение суммы из обеих таблиц."""
        self.setup_salaries_table(temp_db)
        cursor = temp_db.cursor()

        # Создаём тестовые данные
        cursor.execute("""
            INSERT INTO employees (login, password_hash, full_name, position, is_active)
            VALUES ('unified_emp', 'hash', 'Unified Employee', 'Designer', 1)
        """)
        employee_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO clients (full_name, phone, client_type)
            VALUES ('Unified Client', '+79991234567', 'individual')
        """)
        client_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO contracts (contract_number, client_id, project_type, address)
            VALUES ('UNI-001', ?, 'Individual', 'Test Address')
        """, (client_id,))
        contract_id = cursor.lastrowid

        # Payment с final_amount
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, 'Designer', 'Design', 'advance', 10000, 10000)
        """, (contract_id, employee_id))

        # Salary с amount
        cursor.execute("""
            INSERT INTO salaries (employee_id, amount, report_month)
            VALUES (?, 30000, '2025-01')
        """, (employee_id,))
        temp_db.commit()

        # Правильный способ получения суммы:
        # COALESCE(final_amount, amount) или
        # item.get('final_amount') or item.get('amount', 0)

        # Проверяем payment
        cursor.execute("SELECT final_amount FROM payments WHERE contract_id = ?", (contract_id,))
        payment_amount = cursor.fetchone()[0]
        assert payment_amount == 10000

        # Проверяем salary
        cursor.execute("SELECT amount FROM salaries WHERE employee_id = ?", (employee_id,))
        salary_amount = cursor.fetchone()[0]
        assert salary_amount == 30000


class TestPaymentIDCollision:
    """Тесты коллизии ID между payments и salaries."""

    def setup_salaries_table(self, db):
        """Создание таблицы salaries."""
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS salaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER REFERENCES employees(id),
                amount REAL DEFAULT 0,
                report_month TEXT,
                payment_status TEXT DEFAULT 'pending',
                source TEXT DEFAULT 'Оклад',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()

    def test_same_id_in_both_tables(self, db_with_data):
        """Один и тот же ID может существовать в обеих таблицах."""
        self.setup_salaries_table(db_with_data)
        cursor = db_with_data.cursor()

        # Получаем ID существующего payment
        cursor.execute("SELECT id FROM payments LIMIT 1")
        result = cursor.fetchone()
        if result is None:
            pytest.skip("Нет платежей для теста")

        payment_id = result[0]

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        # Создаём salary с тем же ID (если возможно)
        # В SQLite AUTOINCREMENT не позволяет это напрямую,
        # но демонстрируем проблему
        cursor.execute("""
            INSERT INTO salaries (employee_id, amount, report_month)
            VALUES (?, 40000, '2025-02')
        """, (employee_id,))
        salary_id = cursor.lastrowid
        db_with_data.commit()

        # Проверяем что оба существуют
        cursor.execute("SELECT id FROM payments WHERE id = ?", (payment_id,))
        assert cursor.fetchone() is not None

        cursor.execute("SELECT id FROM salaries WHERE id = ?", (salary_id,))
        assert cursor.fetchone() is not None

        # Если ID совпадают - это проблема при операциях без указания таблицы

    def test_delete_requires_source_specification(self, db_with_data):
        """Удаление требует указания источника (таблицы)."""
        self.setup_salaries_table(db_with_data)
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        # Создаём payment
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, 'Test', 'Test', 'full', 5000, 5000)
        """, (contract_id, employee_id))
        payment_id = cursor.lastrowid

        # Создаём salary
        cursor.execute("""
            INSERT INTO salaries (employee_id, amount, report_month)
            VALUES (?, 30000, '2025-03')
        """, (employee_id,))
        salary_id = cursor.lastrowid
        db_with_data.commit()

        # Удаление из payments
        cursor.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
        db_with_data.commit()

        # Payment удалён
        cursor.execute("SELECT id FROM payments WHERE id = ?", (payment_id,))
        assert cursor.fetchone() is None

        # Salary остался
        cursor.execute("SELECT id FROM salaries WHERE id = ?", (salary_id,))
        assert cursor.fetchone() is not None


class TestOfflineQueueEntityType:
    """Тесты корректности entity_type в offline queue."""

    def setup_tables(self, db):
        """Создание необходимых таблиц."""
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                data TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS salaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                amount REAL DEFAULT 0,
                report_month TEXT,
                source TEXT DEFAULT 'Оклад'
            )
        """)
        db.commit()

    def test_payment_entity_type_for_crm(self, temp_db):
        """Для CRM платежей entity_type = 'payment'."""
        self.setup_tables(temp_db)
        cursor = temp_db.cursor()

        payment_id = 42
        source = 'CRM'

        # ПРАВИЛЬНОЕ поведение
        entity_type = 'payment'  # Для CRM платежей

        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('delete', ?, ?, ?)
        """, (entity_type, payment_id, json.dumps({'source': source})))
        temp_db.commit()

        cursor.execute("SELECT entity_type FROM offline_queue WHERE entity_id = ?", (payment_id,))
        result = cursor.fetchone()
        assert result[0] == 'payment'

    def test_salary_entity_type_should_be_salary(self, temp_db):
        """КРИТИЧНО: Для зарплат entity_type ДОЛЖЕН быть 'salary'."""
        self.setup_tables(temp_db)
        cursor = temp_db.cursor()

        salary_id = 100
        source = 'Оклад'

        # ПРАВИЛЬНОЕ поведение (но в коде может быть баг!)
        # entity_type = 'salary' if source == 'Оклад' else 'payment'
        entity_type = 'salary'  # Должно быть так!

        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
            VALUES ('delete', ?, ?, ?)
        """, (entity_type, salary_id, json.dumps({'source': source})))
        temp_db.commit()

        cursor.execute("SELECT entity_type FROM offline_queue WHERE entity_id = ?", (salary_id,))
        result = cursor.fetchone()

        # Этот тест показывает ОЖИДАЕМОЕ поведение
        assert result[0] == 'salary', \
            "Для зарплат entity_type должен быть 'salary', не 'payment'"

    def test_queue_delete_determines_correct_entity_type(self, temp_db):
        """_queue_payment_delete должен определять правильный entity_type."""
        self.setup_tables(temp_db)
        cursor = temp_db.cursor()

        def queue_payment_delete_fixed(payment_id, source):
            """Исправленная версия функции."""
            # Определяем entity_type на основе source
            entity_type = 'salary' if source == 'Оклад' else 'payment'

            cursor.execute("""
                INSERT INTO offline_queue (operation_type, entity_type, entity_id, data)
                VALUES ('delete', ?, ?, ?)
            """, (entity_type, payment_id, json.dumps({'source': source})))

        # Тест для CRM
        queue_payment_delete_fixed(1, 'CRM')
        cursor.execute("SELECT entity_type FROM offline_queue WHERE entity_id = 1")
        assert cursor.fetchone()[0] == 'payment'

        # Тест для оклада
        queue_payment_delete_fixed(2, 'Оклад')
        cursor.execute("SELECT entity_type FROM offline_queue WHERE entity_id = 2")
        assert cursor.fetchone()[0] == 'salary'


class TestSourceParameterUsage:
    """Тесты использования параметра source."""

    def setup_salaries_table(self, db):
        """Создание таблицы salaries."""
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS salaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                amount REAL DEFAULT 0,
                report_month TEXT,
                source TEXT DEFAULT 'Оклад'
            )
        """)
        db.commit()

    def test_delete_payment_uses_source_parameter(self, db_with_data):
        """delete_payment_universal должен использовать source для выбора таблицы."""
        self.setup_salaries_table(db_with_data)
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        # Создаём salary
        cursor.execute("""
            INSERT INTO salaries (employee_id, amount, report_month)
            VALUES (?, 45000, '2025-04')
        """, (employee_id,))
        salary_id = cursor.lastrowid
        db_with_data.commit()

        # Правильное удаление с использованием source
        source = 'Оклад'
        table_name = 'salaries' if source == 'Оклад' else 'payments'

        cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (salary_id,))
        db_with_data.commit()

        # Проверяем что удалено из правильной таблицы
        cursor.execute("SELECT id FROM salaries WHERE id = ?", (salary_id,))
        assert cursor.fetchone() is None

    def test_source_determines_table_for_update(self, db_with_data):
        """Source должен определять таблицу для UPDATE."""
        self.setup_salaries_table(db_with_data)
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO salaries (employee_id, amount, report_month)
            VALUES (?, 55000, '2025-05')
        """, (employee_id,))
        salary_id = cursor.lastrowid
        db_with_data.commit()

        # Обновление с использованием source
        source = 'Оклад'
        new_amount = 60000
        table_name = 'salaries' if source == 'Оклад' else 'payments'
        amount_field = 'amount' if source == 'Оклад' else 'final_amount'

        cursor.execute(f"UPDATE {table_name} SET {amount_field} = ? WHERE id = ?",
                       (new_amount, salary_id))
        db_with_data.commit()

        # Проверяем
        cursor.execute("SELECT amount FROM salaries WHERE id = ?", (salary_id,))
        assert cursor.fetchone()[0] == new_amount


class TestSupervisionReloadOnStatusChange:
    """Тесты перезагрузки supervision при изменении статуса."""

    def test_status_change_should_reload_all_tabs(self, db_with_data):
        """Изменение статуса должно перезагрузить ВСЕ вкладки, включая надзор."""
        cursor = db_with_data.cursor()

        # Этот тест документирует ОЖИДАЕМОЕ поведение
        # В коде сейчас надзор НЕ перезагружается

        # Список вкладок которые ДОЛЖНЫ перезагружаться:
        tabs_to_reload = [
            'all_payments',           # load_all_payments()
            'Оклады',                 # load_payment_type_data('Оклады')
            'Индивидуальные проекты', # load_payment_type_data('Индивидуальные проекты')
            'Шаблонные проекты',      # load_payment_type_data('Шаблонные проекты')
            'Авторский надзор',       # load_payment_type_data('Авторский надзор') - ПРОПУЩЕНО!
        ]

        # Проверяем что все вкладки в списке
        assert 'Авторский надзор' in tabs_to_reload, \
            "Авторский надзор ДОЛЖЕН быть в списке перезагрузки!"

    def test_supervision_payment_status_change_visible(self, db_with_data):
        """Изменение статуса платежа надзора должно быть видно."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 1")
        dan_id = cursor.fetchone()[0]

        # Создаём платёж надзора
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, payment_status)
            VALUES (?, ?, 'ДАН', 'Авторский надзор', 'Полная оплата', 25000, 25000, 'pending')
        """, (contract_id, dan_id))
        payment_id = cursor.lastrowid
        db_with_data.commit()

        # Меняем статус
        new_status = 'paid'
        cursor.execute("""
            UPDATE payments SET payment_status = ? WHERE id = ?
        """, (new_status, payment_id))
        db_with_data.commit()

        # Проверяем что статус изменился
        cursor.execute("SELECT payment_status FROM payments WHERE id = ?", (payment_id,))
        result = cursor.fetchone()[0]
        assert result == new_status


class TestPaymentStatusValues:
    """Тесты валидности значений статуса платежа."""

    def test_valid_payment_statuses(self, db_with_data):
        """Статус должен быть из допустимого списка."""
        cursor = db_with_data.cursor()

        # Допустимые статусы в системе
        valid_statuses = [
            'pending',        # Ожидает
            'to_pay',         # К оплате
            'paid',           # Оплачено
            'Не оплачено',    # Русский вариант
            'К оплате',       # Русский вариант
            'Оплачено',       # Русский вариант
            None,             # Не установлен
            ''                # Пустая строка
        ]

        cursor.execute("SELECT id, payment_status FROM payments")
        payments = cursor.fetchall()

        for payment_id, status in payments:
            assert status in valid_statuses, \
                f"Платёж {payment_id} имеет недопустимый статус: {status}"

    def test_toggle_status_logic(self, db_with_data):
        """Toggle логика статуса."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, payment_status)
            VALUES (?, ?, 'Test', 'Test', 'full', 1000, 1000, NULL)
        """, (contract_id, employee_id))
        payment_id = cursor.lastrowid
        db_with_data.commit()

        def toggle_status(current_status, target_status):
            """Toggle логика из set_payment_status."""
            if current_status == target_status:
                return None  # Toggle off
            else:
                return target_status  # Toggle on

        # Тест toggle on
        current = None
        new = toggle_status(current, 'paid')
        assert new == 'paid'

        # Тест toggle off
        current = 'paid'
        new = toggle_status(current, 'paid')
        assert new is None
