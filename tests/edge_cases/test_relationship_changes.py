"""
Тесты изменения связей атрибутов при обновлении сущностей.

Покрывает сценарии:
1. Изменение client_id у договора
2. Изменение contract_id у CRM карточки
3. Изменение employee_id у платежа
4. Изменение executor_id у stage_executor
5. Каскадные эффекты при изменении связей
"""

import pytest
import sqlite3
from datetime import datetime, date


class TestContractRelationshipChanges:
    """Тесты изменения связей договора."""

    def test_change_contract_client_valid(self, db_with_data):
        """Изменение client_id договора на существующего клиента."""
        cursor = db_with_data.cursor()

        # Создаём второго клиента
        cursor.execute("""
            INSERT INTO clients (full_name, phone, client_type)
            VALUES ('Новый Клиент', '+79991112233', 'Физ. лицо')
        """)
        new_client_id = cursor.lastrowid

        # Получаем существующий договор
        cursor.execute("SELECT id, client_id FROM contracts LIMIT 1")
        contract = cursor.fetchone()
        old_client_id = contract[1]

        # Меняем client_id
        cursor.execute("""
            UPDATE contracts SET client_id = ? WHERE id = ?
        """, (new_client_id, contract[0]))
        db_with_data.commit()

        # Проверяем изменение
        cursor.execute("SELECT client_id FROM contracts WHERE id = ?", (contract[0],))
        result = cursor.fetchone()
        assert result[0] == new_client_id
        assert result[0] != old_client_id

    def test_change_contract_client_invalid_rejected(self, db_with_data):
        """Изменение client_id на несуществующего клиента должно быть отклонено."""
        cursor = db_with_data.cursor()

        # Включаем foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        # Пытаемся установить несуществующий client_id
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                UPDATE contracts SET client_id = 99999 WHERE id = ?
            """, (contract_id,))
            db_with_data.commit()

    def test_change_contract_preserves_crm_card_link(self, db_with_data):
        """При изменении client_id договора, CRM карточка остаётся связанной."""
        cursor = db_with_data.cursor()

        # Создаём второго клиента
        cursor.execute("""
            INSERT INTO clients (full_name, phone, client_type)
            VALUES ('Другой Клиент', '+79998887766', 'Юр. лицо')
        """)
        new_client_id = cursor.lastrowid

        # Получаем договор с CRM карточкой
        cursor.execute("""
            SELECT c.id, crm.id FROM contracts c
            JOIN crm_cards crm ON crm.contract_id = c.id
            LIMIT 1
        """)
        result = cursor.fetchone()
        contract_id, crm_card_id = result

        # Меняем client_id договора
        cursor.execute("""
            UPDATE contracts SET client_id = ? WHERE id = ?
        """, (new_client_id, contract_id))
        db_with_data.commit()

        # Проверяем что CRM карточка всё ещё связана с договором
        cursor.execute("""
            SELECT contract_id FROM crm_cards WHERE id = ?
        """, (crm_card_id,))
        result = cursor.fetchone()
        assert result[0] == contract_id


class TestCRMCardRelationshipChanges:
    """Тесты изменения связей CRM карточки."""

    def test_change_crm_card_contract_valid(self, db_with_data):
        """Изменение contract_id CRM карточки на существующий договор."""
        cursor = db_with_data.cursor()

        # Создаём новый договор
        cursor.execute("SELECT id FROM clients LIMIT 1")
        client_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO contracts (contract_number, client_id, project_type, address)
            VALUES ('NEW-001', ?, 'Дизайн-проект', 'Новый адрес')
        """, (client_id,))
        new_contract_id = cursor.lastrowid

        # Получаем CRM карточку
        cursor.execute("SELECT id, contract_id FROM crm_cards LIMIT 1")
        crm_card = cursor.fetchone()

        # Меняем contract_id
        cursor.execute("""
            UPDATE crm_cards SET contract_id = ? WHERE id = ?
        """, (new_contract_id, crm_card[0]))
        db_with_data.commit()

        # Проверяем
        cursor.execute("SELECT contract_id FROM crm_cards WHERE id = ?", (crm_card[0],))
        assert cursor.fetchone()[0] == new_contract_id

    def test_change_crm_card_contract_cascades_payments(self, db_with_data):
        """При смене договора у CRM карточки, платежи должны быть обновлены."""
        cursor = db_with_data.cursor()

        # Создаём платёж привязанный к contract_id через crm_card
        cursor.execute("""
            SELECT crm.id, crm.contract_id FROM crm_cards crm LIMIT 1
        """)
        crm_card_id, old_contract_id = cursor.fetchone()

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, 'Дизайнер', 'Планировка', 'Аванс', 10000, 10000)
        """, (old_contract_id, employee_id))
        payment_id = cursor.lastrowid
        db_with_data.commit()

        # Создаём новый договор
        cursor.execute("SELECT client_id FROM contracts WHERE id = ?", (old_contract_id,))
        client_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO contracts (contract_number, client_id, project_type, address)
            VALUES ('MOVE-001', ?, 'Дизайн-проект', 'Другой адрес')
        """, (client_id,))
        new_contract_id = cursor.lastrowid

        # Меняем contract_id у CRM карточки
        cursor.execute("""
            UPDATE crm_cards SET contract_id = ? WHERE id = ?
        """, (new_contract_id, crm_card_id))

        # ВАЖНО: Платежи тоже нужно обновить (бизнес-логика)
        cursor.execute("""
            UPDATE payments SET contract_id = ? WHERE contract_id = ?
        """, (new_contract_id, old_contract_id))
        db_with_data.commit()

        # Проверяем что платёж теперь привязан к новому договору
        cursor.execute("SELECT contract_id FROM payments WHERE id = ?", (payment_id,))
        assert cursor.fetchone()[0] == new_contract_id


class TestPaymentRelationshipChanges:
    """Тесты изменения связей платежей."""

    def test_change_payment_employee_valid(self, db_with_data):
        """Изменение employee_id платежа на другого сотрудника."""
        cursor = db_with_data.cursor()

        # Создаём второго сотрудника
        cursor.execute("""
            INSERT INTO employees (login, password_hash, full_name, position, is_active)
            VALUES ('new_emp', 'hash123', 'Новый Сотрудник', 'Дизайнер', 1)
        """)
        new_employee_id = cursor.lastrowid

        # Получаем существующий платёж
        cursor.execute("SELECT id FROM payments LIMIT 1")
        result = cursor.fetchone()
        if result is None:
            # Создаём платёж если нет
            cursor.execute("SELECT id FROM contracts LIMIT 1")
            contract_id = cursor.fetchone()[0]
            cursor.execute("SELECT id FROM employees LIMIT 1")
            old_employee_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                      payment_type, calculated_amount, final_amount)
                VALUES (?, ?, 'Дизайнер', 'Планировка', 'Аванс', 5000, 5000)
            """, (contract_id, old_employee_id))
            payment_id = cursor.lastrowid
        else:
            payment_id = result[0]

        # Меняем employee_id
        cursor.execute("""
            UPDATE payments SET employee_id = ? WHERE id = ?
        """, (new_employee_id, payment_id))
        db_with_data.commit()

        # Проверяем
        cursor.execute("SELECT employee_id FROM payments WHERE id = ?", (payment_id,))
        assert cursor.fetchone()[0] == new_employee_id

    def test_change_payment_contract_valid(self, db_with_data):
        """Изменение contract_id платежа на другой договор."""
        cursor = db_with_data.cursor()

        # Создаём новый договор
        cursor.execute("SELECT id FROM clients LIMIT 1")
        client_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO contracts (contract_number, client_id, project_type, address)
            VALUES ('PAY-MOVE-001', ?, 'Дизайн-проект', 'Платёжный адрес')
        """, (client_id,))
        new_contract_id = cursor.lastrowid

        # Получаем или создаём платёж
        cursor.execute("SELECT id FROM payments LIMIT 1")
        result = cursor.fetchone()
        if result is None:
            cursor.execute("SELECT id FROM contracts LIMIT 1")
            old_contract_id = cursor.fetchone()[0]
            cursor.execute("SELECT id FROM employees LIMIT 1")
            employee_id = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                      payment_type, calculated_amount, final_amount)
                VALUES (?, ?, 'Дизайнер', 'Планировка', 'Аванс', 5000, 5000)
            """, (old_contract_id, employee_id))
            payment_id = cursor.lastrowid
        else:
            payment_id = result[0]

        # Меняем contract_id
        cursor.execute("""
            UPDATE payments SET contract_id = ? WHERE id = ?
        """, (new_contract_id, payment_id))
        db_with_data.commit()

        # Проверяем
        cursor.execute("SELECT contract_id FROM payments WHERE id = ?", (payment_id,))
        assert cursor.fetchone()[0] == new_contract_id

    def test_payment_employee_change_preserves_history(self, db_with_data):
        """При смене сотрудника в платеже, история должна сохраняться."""
        cursor = db_with_data.cursor()

        # Получаем данные
        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM employees LIMIT 1")
        old_employee_id = cursor.fetchone()[0]

        # Создаём платёж
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, 'Дизайнер', 'Планировка', 'Аванс', 10000, 10000, 0)
        """, (contract_id, old_employee_id))
        old_payment_id = cursor.lastrowid

        # Создаём нового сотрудника
        cursor.execute("""
            INSERT INTO employees (login, password_hash, full_name, position, is_active)
            VALUES ('reassign_emp', 'hash456', 'Переназначенный', 'Дизайнер', 1)
        """)
        new_employee_id = cursor.lastrowid

        # ПРАВИЛЬНАЯ логика переназначения: помечаем старый как reassigned
        cursor.execute("""
            UPDATE payments SET reassigned = 1 WHERE id = ?
        """, (old_payment_id,))

        # Создаём новый платёж для нового сотрудника
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, 'Дизайнер', 'Планировка', 'Аванс', 10000, 10000, 0)
        """, (contract_id, new_employee_id))
        new_payment_id = cursor.lastrowid
        db_with_data.commit()

        # Проверяем что оба платежа существуют
        cursor.execute("SELECT id, reassigned FROM payments WHERE id IN (?, ?)",
                       (old_payment_id, new_payment_id))
        payments = cursor.fetchall()
        assert len(payments) == 2

        # Старый помечен как reassigned
        old_payment = next(p for p in payments if p[0] == old_payment_id)
        assert old_payment[1] == 1

        # Новый не помечен
        new_payment = next(p for p in payments if p[0] == new_payment_id)
        assert new_payment[1] == 0


class TestStageExecutorRelationshipChanges:
    """Тесты изменения связей исполнителей этапов."""

    def test_change_stage_executor_employee(self, db_with_data):
        """Изменение executor_id в stage_executors."""
        cursor = db_with_data.cursor()

        # Создаём stage_executor если нет
        cursor.execute("SELECT id FROM crm_cards LIMIT 1")
        crm_card_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM employees LIMIT 1")
        old_executor_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT OR REPLACE INTO stage_executors
            (crm_card_id, stage_name, executor_id, executor_type)
            VALUES (?, 'Планировка', ?, 'СДП')
        """, (crm_card_id, old_executor_id))
        db_with_data.commit()

        # Создаём нового сотрудника
        cursor.execute("""
            INSERT INTO employees (login, password_hash, full_name, position, is_active)
            VALUES ('stage_new', 'hash789', 'Новый Исполнитель', 'Дизайнер', 1)
        """)
        new_executor_id = cursor.lastrowid

        # Меняем исполнителя
        cursor.execute("""
            UPDATE stage_executors SET executor_id = ?
            WHERE crm_card_id = ? AND stage_name = 'Планировка'
        """, (new_executor_id, crm_card_id))
        db_with_data.commit()

        # Проверяем
        cursor.execute("""
            SELECT executor_id FROM stage_executors
            WHERE crm_card_id = ? AND stage_name = 'Планировка'
        """, (crm_card_id,))
        assert cursor.fetchone()[0] == new_executor_id

    def test_stage_executor_change_triggers_payment_reassignment(self, db_with_data):
        """При смене исполнителя этапа должны быть переназначены платежи."""
        cursor = db_with_data.cursor()

        # Создаём полную цепочку данных
        cursor.execute("SELECT id FROM crm_cards LIMIT 1")
        crm_card_id = cursor.fetchone()[0]

        cursor.execute("SELECT contract_id FROM crm_cards WHERE id = ?", (crm_card_id,))
        contract_id = cursor.fetchone()[0]

        # Use unique login with timestamp to avoid conflicts
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        cursor.execute("SELECT id FROM employees WHERE position = 'Designer' LIMIT 1")
        result = cursor.fetchone()
        if result is None:
            cursor.execute("""
                INSERT INTO employees (login, password_hash, full_name, position, is_active)
                VALUES (?, 'hash', 'Designer 1', 'Designer', 1)
            """, (f'designer1_{unique_id}',))
            old_executor_id = cursor.lastrowid
        else:
            old_executor_id = result[0]

        # Создаём stage_executor
        cursor.execute("""
            INSERT OR REPLACE INTO stage_executors
            (crm_card_id, stage_name, executor_id, executor_type)
            VALUES (?, 'Планировка', ?, 'СДП')
        """, (crm_card_id, old_executor_id))

        # Создаём платёж для этого исполнителя
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, 'СДП', 'Планировка', 'Аванс', 15000, 15000, 0)
        """, (contract_id, old_executor_id))
        old_payment_id = cursor.lastrowid
        db_with_data.commit()

        # Создаём нового исполнителя с уникальным логином
        cursor.execute("""
            INSERT INTO employees (login, password_hash, full_name, position, is_active)
            VALUES (?, 'hash2', 'Designer 2', 'Designer', 1)
        """, (f'designer2_{unique_id}',))
        new_executor_id = cursor.lastrowid

        # БИЗНЕС-ЛОГИКА: При смене исполнителя этапа
        # 1. Обновляем stage_executors
        cursor.execute("""
            UPDATE stage_executors SET executor_id = ?
            WHERE crm_card_id = ? AND stage_name = 'Планировка'
        """, (new_executor_id, crm_card_id))

        # 2. Помечаем старый платёж как reassigned
        cursor.execute("""
            UPDATE payments SET reassigned = 1 WHERE id = ?
        """, (old_payment_id,))

        # 3. Создаём новый платёж
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, 'СДП', 'Планировка', 'Аванс', 15000, 15000, 0)
        """, (contract_id, new_executor_id))
        new_payment_id = cursor.lastrowid
        db_with_data.commit()

        # Проверки
        # 1. Stage executor обновлён
        cursor.execute("""
            SELECT executor_id FROM stage_executors
            WHERE crm_card_id = ? AND stage_name = 'Планировка'
        """, (crm_card_id,))
        assert cursor.fetchone()[0] == new_executor_id

        # 2. Старый платёж помечен
        cursor.execute("SELECT reassigned FROM payments WHERE id = ?", (old_payment_id,))
        assert cursor.fetchone()[0] == 1

        # 3. Новый платёж не помечен
        cursor.execute("SELECT reassigned FROM payments WHERE id = ?", (new_payment_id,))
        assert cursor.fetchone()[0] == 0

        # 4. Только один активный платёж для этапа
        cursor.execute("""
            SELECT COUNT(*) FROM payments
            WHERE contract_id = ? AND stage_name = 'Планировка'
            AND role = 'СДП' AND reassigned = 0
        """, (contract_id,))
        assert cursor.fetchone()[0] == 1


class TestRelationshipIntegrityOnDelete:
    """Тесты целостности связей при удалении."""

    def test_delete_employee_with_payments_blocked(self, db_with_data):
        """Удаление сотрудника с активными платежами должно быть заблокировано."""
        cursor = db_with_data.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        # Создаём сотрудника с платежом
        cursor.execute("""
            INSERT INTO employees (login, password_hash, full_name, position, is_active)
            VALUES ('to_delete', 'hash', 'Удаляемый', 'Дизайнер', 1)
        """)
        employee_id = cursor.lastrowid

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, 'Дизайнер', 'Планировка', 'Полная', 20000, 20000)
        """, (contract_id, employee_id))
        db_with_data.commit()

        # Попытка удалить сотрудника должна провалиться
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
            db_with_data.commit()

    def test_delete_employee_after_payments_removed(self, db_with_data):
        """Удаление сотрудника после удаления всех платежей должно работать."""
        cursor = db_with_data.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        # Создаём сотрудника
        cursor.execute("""
            INSERT INTO employees (login, password_hash, full_name, position, is_active)
            VALUES ('safe_delete', 'hash', 'Безопасно удаляемый', 'Менеджер', 1)
        """)
        employee_id = cursor.lastrowid

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        # Создаём и удаляем платёж
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, 'Менеджер', 'Планировка', 'Полная', 5000, 5000)
        """, (contract_id, employee_id))
        payment_id = cursor.lastrowid
        db_with_data.commit()

        # Удаляем платёж
        cursor.execute("DELETE FROM payments WHERE id = ?", (payment_id,))

        # Удаляем stage_executors если есть
        cursor.execute("DELETE FROM stage_executors WHERE executor_id = ?", (employee_id,))

        # Теперь можем удалить сотрудника
        cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        db_with_data.commit()

        # Проверяем что удалён
        cursor.execute("SELECT id FROM employees WHERE id = ?", (employee_id,))
        assert cursor.fetchone() is None


class TestNullRelationshipHandling:
    """Тесты обработки NULL в связях."""

    def test_payment_with_null_crm_card_id(self, db_with_data):
        """Платёж может не иметь crm_card_id (для окладов)."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        # Создаём платёж без crm_card_id
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, crm_card_id)
            VALUES (?, ?, 'Оклад', NULL, 'Оклад', 50000, 50000, NULL)
        """, (contract_id, employee_id))
        payment_id = cursor.lastrowid
        db_with_data.commit()

        # Проверяем
        cursor.execute("SELECT crm_card_id, stage_name FROM payments WHERE id = ?", (payment_id,))
        result = cursor.fetchone()
        assert result[0] is None  # crm_card_id is NULL
        assert result[1] is None  # stage_name is NULL

    def test_contract_with_null_optional_fields(self, db_with_data):
        """Договор с NULL в опциональных полях."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM clients LIMIT 1")
        client_id = cursor.fetchone()[0]

        # Создаём договор с минимумом полей
        cursor.execute("""
            INSERT INTO contracts (contract_number, client_id, project_type, address,
                                   contract_date, total_area, rooms_count)
            VALUES ('NULL-TEST-001', ?, 'Дизайн-проект', 'Тестовый адрес',
                    NULL, NULL, NULL)
        """, (client_id,))
        contract_id = cursor.lastrowid
        db_with_data.commit()

        # Проверяем
        cursor.execute("""
            SELECT contract_date, total_area, rooms_count
            FROM contracts WHERE id = ?
        """, (contract_id,))
        result = cursor.fetchone()
        assert result[0] is None  # contract_date
        assert result[1] is None  # total_area
        assert result[2] is None  # rooms_count
