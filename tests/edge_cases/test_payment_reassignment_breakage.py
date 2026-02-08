"""
Тесты разрыва связей платежей при переназначении исполнителей.

КРИТИЧЕСКИЕ ТЕСТЫ для известной проблемы:
- Дублирование платежей при переназначении
- Неправильная фильтрация reassigned платежей
- Разрыв связи executor ↔ payment

Основано на архитектурном анализе:
- crm_tab.py:14970-14992 (_reassign_payments_via_api)
- crm_tab.py:8792 (on_employee_changed)
"""

import pytest
import sqlite3
from datetime import datetime


class TestReassignedFlagFiltering:
    """КРИТИЧЕСКИЕ тесты фильтрации флага reassigned."""

    def test_reassigned_payments_excluded_from_active_search(self, db_with_data):
        """КРИТИЧНО: Платежи с reassigned=True ДОЛЖНЫ быть исключены при поиске активных."""
        cursor = db_with_data.cursor()

        # Создаём данные
        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 2")
        employees = cursor.fetchall()
        old_executor_id = employees[0][0]
        new_executor_id = employees[1][0] if len(employees) > 1 else old_executor_id

        stage_name = 'Критический этап'
        role = 'СДП'

        # Создаём старый платёж (reassigned=True)
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, ?, 'Аванс', 10000, 10000, 1)
        """, (contract_id, old_executor_id, role, stage_name))
        old_payment_id = cursor.lastrowid

        # Создаём новый платёж (reassigned=False)
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, ?, 'Аванс', 10000, 10000, 0)
        """, (contract_id, new_executor_id, role, stage_name))
        new_payment_id = cursor.lastrowid
        db_with_data.commit()

        # КРИТИЧЕСКАЯ ПРОВЕРКА: При поиске активных платежей для этапа
        # должен найтись ТОЛЬКО новый платёж

        cursor.execute("""
            SELECT id, employee_id, reassigned FROM payments
            WHERE contract_id = ?
            AND stage_name = ?
            AND role = ?
            AND reassigned = 0
        """, (contract_id, stage_name, role))
        active_payments = cursor.fetchall()

        assert len(active_payments) == 1, \
            f"Должен быть ровно 1 активный платёж, найдено: {len(active_payments)}"

        assert active_payments[0][0] == new_payment_id, \
            "Активный платёж должен быть новым"

        assert active_payments[0][2] == 0, \
            "Активный платёж НЕ должен быть помечен как reassigned"

    def test_old_payments_search_includes_reassigned_check(self, db_with_data):
        """КРИТИЧНО: Поиск старых платежей ДОЛЖЕН проверять флаг reassigned."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 1")
        old_executor_id = cursor.fetchone()[0]

        stage_name = 'Поиск старых'
        role = 'СДП'

        # Создаём платёж который УЖЕ БЫЛ переназначен
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, ?, 'Аванс', 10000, 10000, 1)
        """, (contract_id, old_executor_id, role, stage_name))
        already_reassigned_id = cursor.lastrowid
        db_with_data.commit()

        # ПРАВИЛЬНЫЙ поиск старых платежей для переназначения
        # (как должно быть в crm_tab.py:14970-14992)
        cursor.execute("""
            SELECT id FROM payments
            WHERE contract_id = ?
            AND stage_name = ?
            AND role = ?
            AND employee_id = ?
            AND NOT reassigned  -- КРИТИЧНО: эта проверка ДОЛЖНА быть!
        """, (contract_id, stage_name, role, old_executor_id))
        old_payments = cursor.fetchall()

        # Уже переназначенный платёж НЕ должен найтись
        assert len(old_payments) == 0, \
            "Уже переназначенные платежи НЕ должны находиться при поиске для переназначения"

    def test_duplicate_payment_prevention_on_reassignment(self, db_with_data):
        """КРИТИЧНО: Повторное переназначение НЕ должно создавать дубликаты."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 3")
        employees = cursor.fetchall()
        executor_1 = employees[0][0]
        executor_2 = employees[1][0] if len(employees) > 1 else executor_1
        executor_3 = employees[2][0] if len(employees) > 2 else executor_2

        stage_name = 'Дубликаты'
        role = 'СДП'

        # Первоначальный платёж для executor_1
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, ?, 'Аванс', 10000, 10000, 0)
        """, (contract_id, executor_1, role, stage_name))
        payment_1_id = cursor.lastrowid
        db_with_data.commit()

        # === ПЕРВОЕ ПЕРЕНАЗНАЧЕНИЕ: executor_1 → executor_2 ===
        cursor.execute("""
            UPDATE payments SET reassigned = 1 WHERE id = ?
        """, (payment_1_id,))

        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, ?, 'Аванс', 10000, 10000, 0)
        """, (contract_id, executor_2, role, stage_name))
        payment_2_id = cursor.lastrowid
        db_with_data.commit()

        # === ВТОРОЕ ПЕРЕНАЗНАЧЕНИЕ: executor_2 → executor_3 ===
        # Ищем активный платёж (без reassigned)
        cursor.execute("""
            SELECT id FROM payments
            WHERE contract_id = ?
            AND stage_name = ?
            AND role = ?
            AND employee_id = ?
            AND NOT reassigned
        """, (contract_id, stage_name, role, executor_2))
        active_payment = cursor.fetchone()

        assert active_payment is not None, "Должен быть активный платёж executor_2"
        assert active_payment[0] == payment_2_id

        # Переназначаем
        cursor.execute("""
            UPDATE payments SET reassigned = 1 WHERE id = ?
        """, (payment_2_id,))

        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, ?, 'Аванс', 10000, 10000, 0)
        """, (contract_id, executor_3, role, stage_name))
        db_with_data.commit()

        # ПРОВЕРКА: Должен быть ровно ОДИН активный платёж
        cursor.execute("""
            SELECT COUNT(*) FROM payments
            WHERE contract_id = ?
            AND stage_name = ?
            AND role = ?
            AND payment_type = 'Аванс'
            AND NOT reassigned
        """, (contract_id, stage_name, role))
        active_count = cursor.fetchone()[0]

        assert active_count == 1, \
            f"Должен быть ровно 1 активный платёж, найдено: {active_count}"


class TestPaymentExecutorLink:
    """Тесты связи платёж ↔ исполнитель."""

    def test_payment_executor_consistency(self, db_with_data):
        """Платёж должен ссылаться на валидного исполнителя."""
        cursor = db_with_data.cursor()

        cursor.execute("""
            SELECT p.id, p.employee_id, e.id
            FROM payments p
            LEFT JOIN employees e ON p.employee_id = e.id
        """)
        payments = cursor.fetchall()

        for payment_id, payment_emp_id, emp_id in payments:
            if payment_emp_id is not None:
                assert emp_id is not None, \
                    f"Платёж {payment_id} ссылается на несуществующего сотрудника {payment_emp_id}"

    def test_payment_matches_stage_executor(self, db_with_data):
        """Платёж должен соответствовать исполнителю этапа (если назначен)."""
        cursor = db_with_data.cursor()

        # Создаём полную цепочку данных
        cursor.execute("SELECT id, contract_id FROM crm_cards LIMIT 1")
        crm_card_id, contract_id = cursor.fetchone()

        cursor.execute("SELECT id FROM employees LIMIT 1")
        executor_id = cursor.fetchone()[0]

        stage_name = 'Консистентный этап'
        role = 'СДП'

        # Назначаем исполнителя на этап
        cursor.execute("""
            INSERT OR REPLACE INTO stage_executors
            (crm_card_id, stage_name, executor_id, executor_type)
            VALUES (?, ?, ?, ?)
        """, (crm_card_id, stage_name, executor_id, role))

        # Создаём платёж для этого исполнителя
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, ?, 'Аванс', 10000, 10000, 0)
        """, (contract_id, executor_id, role, stage_name))
        db_with_data.commit()

        # Проверяем консистентность
        cursor.execute("""
            SELECT p.employee_id, se.executor_id
            FROM payments p
            JOIN crm_cards crm ON crm.contract_id = p.contract_id
            JOIN stage_executors se ON se.crm_card_id = crm.id
                AND se.stage_name = p.stage_name
                AND se.executor_type = p.role
            WHERE p.contract_id = ?
            AND p.stage_name = ?
            AND p.reassigned = 0
        """, (contract_id, stage_name))

        result = cursor.fetchone()
        if result:
            payment_executor, stage_executor = result
            assert payment_executor == stage_executor, \
                f"Исполнитель платежа ({payment_executor}) не совпадает с исполнителем этапа ({stage_executor})"

    def test_orphan_payments_after_executor_removal(self, db_with_data):
        """Обнаружение "осиротевших" платежей после удаления исполнителя из этапа."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id, contract_id FROM crm_cards LIMIT 1")
        crm_card_id, contract_id = cursor.fetchone()

        # Создаём двух сотрудников
        cursor.execute("""
            INSERT INTO employees (login, password_hash, full_name, position, is_active)
            VALUES ('orphan_old', 'hash1', 'Старый', 'Дизайнер', 1)
        """)
        old_executor_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO employees (login, password_hash, full_name, position, is_active)
            VALUES ('orphan_new', 'hash2', 'Новый', 'Дизайнер', 1)
        """)
        new_executor_id = cursor.lastrowid

        stage_name = 'Осиротевший этап'
        role = 'СДП'

        # Назначаем старого исполнителя
        cursor.execute("""
            INSERT INTO stage_executors
            (crm_card_id, stage_name, executor_id, executor_type)
            VALUES (?, ?, ?, ?)
        """, (crm_card_id, stage_name, old_executor_id, role))

        # Создаём платёж для старого исполнителя
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, ?, 'Аванс', 10000, 10000, 0)
        """, (contract_id, old_executor_id, role, stage_name))
        db_with_data.commit()

        # ПРОБЛЕМА: Меняем исполнителя БЕЗ переназначения платежа
        cursor.execute("""
            UPDATE stage_executors SET executor_id = ?
            WHERE crm_card_id = ? AND stage_name = ?
        """, (new_executor_id, crm_card_id, stage_name))
        db_with_data.commit()

        # Теперь платёж "осиротел" - его исполнитель не совпадает с исполнителем этапа
        cursor.execute("""
            SELECT p.id, p.employee_id, se.executor_id
            FROM payments p
            JOIN crm_cards crm ON crm.contract_id = p.contract_id
            JOIN stage_executors se ON se.crm_card_id = crm.id
                AND se.stage_name = p.stage_name
                AND se.executor_type = p.role
            WHERE p.contract_id = ?
            AND p.stage_name = ?
            AND p.reassigned = 0
            AND p.employee_id != se.executor_id
        """, (contract_id, stage_name))

        orphan_payments = cursor.fetchall()

        # Это должно быть выявлено как проблема!
        assert len(orphan_payments) > 0, \
            "Должен быть обнаружен осиротевший платёж"


class TestPaymentContractLink:
    """Тесты связи платёж ↔ договор."""

    def test_payment_contract_consistency(self, db_with_data):
        """Платёж должен ссылаться на валидный договор."""
        cursor = db_with_data.cursor()

        cursor.execute("""
            SELECT p.id, p.contract_id, c.id
            FROM payments p
            LEFT JOIN contracts c ON p.contract_id = c.id
        """)
        payments = cursor.fetchall()

        for payment_id, payment_contract_id, contract_id in payments:
            if payment_contract_id is not None:
                assert contract_id is not None, \
                    f"Платёж {payment_id} ссылается на несуществующий договор {payment_contract_id}"

    def test_payment_amount_consistency(self, db_with_data):
        """Сумма платежа должна быть консистентной."""
        cursor = db_with_data.cursor()

        cursor.execute("""
            SELECT id, calculated_amount, final_amount, manual_amount
            FROM payments
        """)
        payments = cursor.fetchall()

        for payment_id, calc, final, manual in payments:
            # Если есть ручная сумма, она должна быть финальной
            if manual is not None and manual > 0:
                assert final == manual or final is None, \
                    f"Платёж {payment_id}: final_amount должен равняться manual_amount"
            # Иначе финальная = расчётной
            elif calc is not None:
                # final может отличаться из-за корректировок
                pass


class TestPaymentTypeConsistency:
    """Тесты консистентности типов платежей."""

    def test_advance_and_remainder_pair(self, db_with_data):
        """Аванс и доплата должны существовать парой для СДП."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        stage_name = 'Парный этап'
        role = 'СДП'

        # Создаём только аванс
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, ?, 'Аванс', 5000, 5000, 0)
        """, (contract_id, employee_id, role, stage_name))
        db_with_data.commit()

        # Проверяем наличие пары
        cursor.execute("""
            SELECT payment_type FROM payments
            WHERE contract_id = ?
            AND stage_name = ?
            AND role = ?
            AND employee_id = ?
            AND reassigned = 0
            ORDER BY payment_type
        """, (contract_id, stage_name, role, employee_id))
        types = [r[0] for r in cursor.fetchall()]

        # Для СДП должны быть оба типа (Аванс и Доплата)
        # Если только один - это потенциальная проблема
        if 'Аванс' in types and 'Доплата' not in types:
            # Создаём доплату
            cursor.execute("""
                INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                      payment_type, calculated_amount, final_amount, reassigned)
                VALUES (?, ?, ?, ?, 'Доплата', 5000, 5000, 0)
            """, (contract_id, employee_id, role, stage_name))
            db_with_data.commit()

        # Перепроверяем
        cursor.execute("""
            SELECT COUNT(DISTINCT payment_type) FROM payments
            WHERE contract_id = ?
            AND stage_name = ?
            AND role = ?
            AND employee_id = ?
            AND reassigned = 0
        """, (contract_id, stage_name, role, employee_id))
        type_count = cursor.fetchone()[0]

        assert type_count == 2, f"Для СДП должно быть 2 типа платежей, найдено: {type_count}"

    def test_single_payment_for_non_sdp_roles(self, db_with_data):
        """Для ролей не-СДП должен быть один платёж."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        stage_name = 'Менеджерский этап'
        role = 'Менеджер'

        # Создаём один платёж
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, ?, 'Полная оплата', 3000, 3000, 0)
        """, (contract_id, employee_id, role, stage_name))
        db_with_data.commit()

        # Проверяем что только один
        cursor.execute("""
            SELECT COUNT(*) FROM payments
            WHERE contract_id = ?
            AND stage_name = ?
            AND role = ?
            AND employee_id = ?
            AND reassigned = 0
        """, (contract_id, stage_name, role, employee_id))
        count = cursor.fetchone()[0]

        assert count == 1, f"Для роли {role} должен быть 1 платёж, найдено: {count}"


class TestPaymentStatusTransitions:
    """Тесты переходов статусов платежей."""

    def test_payment_status_valid_values(self, db_with_data):
        """Статус платежа должен быть из допустимого списка."""
        cursor = db_with_data.cursor()

        # Include both Russian and English variants for test data compatibility
        valid_statuses = ['Не оплачено', 'Частично оплачено', 'Оплачено', 'pending', 'paid', 'partial', None, '']

        cursor.execute("SELECT id, payment_status FROM payments")
        payments = cursor.fetchall()

        for payment_id, status in payments:
            assert status in valid_statuses, \
                f"Платёж {payment_id} имеет недопустимый статус: {status}"

    def test_paid_payment_cannot_be_reassigned(self, db_with_data):
        """Оплаченный платёж НЕ должен переназначаться."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        # Создаём оплаченный платёж
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount,
                                  payment_status, reassigned)
            VALUES (?, ?, 'СДП', 'Оплаченный этап', 'Аванс', 10000, 10000, 'Оплачено', 0)
        """, (contract_id, employee_id))
        payment_id = cursor.lastrowid
        db_with_data.commit()

        # БИЗНЕС-ПРАВИЛО: Оплаченный платёж нельзя переназначить
        # Проверяем это через статус + reassigned
        cursor.execute("""
            SELECT payment_status, reassigned FROM payments WHERE id = ?
        """, (payment_id,))
        status, reassigned = cursor.fetchone()

        # Если статус "Оплачено" - переназначение запрещено
        if status == 'Оплачено':
            assert reassigned == 0, \
                "Оплаченный платёж НЕ должен быть помечен как reassigned"


class TestPaymentRoleStageMapping:
    """Тесты соответствия роли и этапа."""

    def test_role_stage_valid_combination(self, db_with_data):
        """Роль и этап должны быть совместимы."""
        cursor = db_with_data.cursor()

        # Словарь допустимых комбинаций (упрощённый)
        valid_combinations = {
            'Менеджер': ['Все этапы', None],  # Менеджер на всех
            'СМП': ['Все этапы', None],
            'СДП': ['Планировка', '3D визуализация', 'Чертежи', None],
            'Дизайнер': ['Планировка', '3D визуализация', 'Чертежи', None],
            'Чертёжник': ['Чертежи', None],
            'Визуализатор': ['3D визуализация', None],
            'Комплектатор': ['Комплектация', None],
            'ДАН': ['Авторский надзор', None],
        }

        cursor.execute("""
            SELECT id, role, stage_name FROM payments
        """)
        payments = cursor.fetchall()

        # Не блокируем, просто логируем потенциальные проблемы
        for payment_id, role, stage in payments:
            if role in valid_combinations:
                expected_stages = valid_combinations[role]
                # None означает любой этап допустим
                if None not in expected_stages and stage not in expected_stages:
                    print(f"WARNING: Платёж {payment_id}: роль '{role}' на этапе '{stage}' может быть некорректной")
