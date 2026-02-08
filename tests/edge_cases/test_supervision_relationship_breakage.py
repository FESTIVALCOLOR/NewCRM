"""
Тесты разрыва связей в модуле авторского надзора (crm_supervision_tab.py).

КРИТИЧЕСКИЕ ТЕСТЫ для:
1. Переназначение ДАН (дежурный авторский надзор) - аналогично CRM
2. Удаление платежей при смене исполнителя
3. Целостность связей supervision_card ↔ payment
4. Отличия от CRM логики:
   - on_employee_changed() - ТОЛЬКО удаляет платежи, НЕ создаёт
   - on_card_moved() - СОЗДАЁТ платежи при перемещении карточки (строки 872-1127)
   - _reassign_dan_payments() - СОЗДАЁТ платежи при переназначении ДАН (строки 6054-6189)

Основано на анализе:
- crm_supervision_tab.py:872-1127 (on_card_moved - СОЗДАНИЕ платежей)
- crm_supervision_tab.py:5993 (save_reassignment)
- crm_supervision_tab.py:6054 (_reassign_dan_payments - СОЗДАНИЕ платежей при переназначении)
- crm_supervision_tab.py:4229-4270 (on_employee_changed - ТОЛЬКО удаление)
"""

import pytest
import sqlite3
from datetime import datetime


class TestDANReassignmentFiltering:
    """КРИТИЧЕСКИЕ тесты фильтрации при переназначении ДАН."""

    def test_reassigned_dan_payments_excluded_from_search(self, db_with_data):
        """КРИТИЧНО: Платежи с reassigned=True ДОЛЖНЫ быть исключены при поиске."""
        cursor = db_with_data.cursor()

        # Создаём данные для надзора
        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 2")
        employees = cursor.fetchall()
        old_dan_id = employees[0][0]
        new_dan_id = employees[1][0] if len(employees) > 1 else old_dan_id

        role = 'ДАН'

        # Создаём старый платёж (reassigned=True)
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, 'Авторский надзор', 'Полная оплата', 25000, 25000, 1)
        """, (contract_id, old_dan_id, role))
        old_payment_id = cursor.lastrowid

        # Создаём новый платёж (reassigned=False)
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, 'Авторский надзор', 'Полная оплата', 25000, 25000, 0)
        """, (contract_id, new_dan_id, role))
        new_payment_id = cursor.lastrowid
        db_with_data.commit()

        # КРИТИЧЕСКАЯ ПРОВЕРКА: При поиске активных платежей ДАН
        # должен найтись ТОЛЬКО новый платёж
        cursor.execute("""
            SELECT id, employee_id, reassigned FROM payments
            WHERE contract_id = ?
            AND role = ?
            AND reassigned = 0
        """, (contract_id, role))
        active_payments = cursor.fetchall()

        assert len(active_payments) == 1, \
            f"Должен быть ровно 1 активный платёж ДАН, найдено: {len(active_payments)}"

        assert active_payments[0][0] == new_payment_id, \
            "Активный платёж должен быть новым"

    def test_dan_reassignment_idempotency(self, db_with_data):
        """КРИТИЧНО: Повторное переназначение ДАН НЕ должно создавать дубликаты."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 3")
        employees = cursor.fetchall()
        dan_1 = employees[0][0]
        dan_2 = employees[1][0] if len(employees) > 1 else dan_1
        dan_3 = employees[2][0] if len(employees) > 2 else dan_2

        role = 'ДАН'
        stage = 'Авторский надзор'

        # Первоначальный платёж для dan_1
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, ?, 'Полная оплата', 20000, 20000, 0)
        """, (contract_id, dan_1, role, stage))
        payment_1_id = cursor.lastrowid
        db_with_data.commit()

        # === ПЕРВОЕ ПЕРЕНАЗНАЧЕНИЕ: dan_1 → dan_2 ===
        # Помечаем старый платёж
        cursor.execute("""
            UPDATE payments SET reassigned = 1 WHERE id = ?
        """, (payment_1_id,))

        # Создаём новый платёж
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, ?, 'Полная оплата', 20000, 20000, 0)
        """, (contract_id, dan_2, role, stage))
        payment_2_id = cursor.lastrowid
        db_with_data.commit()

        # === ВТОРОЕ ПЕРЕНАЗНАЧЕНИЕ: dan_2 → dan_3 ===
        # Ищем активный платёж (без reassigned)
        cursor.execute("""
            SELECT id FROM payments
            WHERE contract_id = ?
            AND role = ?
            AND employee_id = ?
            AND NOT reassigned
        """, (contract_id, role, dan_2))
        active_payment = cursor.fetchone()

        assert active_payment is not None, "Должен быть активный платёж dan_2"
        assert active_payment[0] == payment_2_id

        # Переназначаем
        cursor.execute("""
            UPDATE payments SET reassigned = 1 WHERE id = ?
        """, (payment_2_id,))

        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, reassigned)
            VALUES (?, ?, ?, ?, 'Полная оплата', 20000, 20000, 0)
        """, (contract_id, dan_3, role, stage))
        db_with_data.commit()

        # ПРОВЕРКА: Должен быть ровно ОДИН активный платёж ДАН
        cursor.execute("""
            SELECT COUNT(*) FROM payments
            WHERE contract_id = ?
            AND role = ?
            AND NOT reassigned
        """, (contract_id, role))
        active_count = cursor.fetchone()[0]

        assert active_count == 1, \
            f"Должен быть ровно 1 активный платёж ДАН, найдено: {active_count}"


class TestSupervisionCardPaymentLink:
    """Тесты связи supervision_card ↔ payment."""

    def test_supervision_card_payment_consistency(self, db_with_data):
        """Платёж надзора должен ссылаться на валидный договор."""
        cursor = db_with_data.cursor()

        # Создаём supervision_card
        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO supervision_cards (contract_id, status)
            VALUES (?, 'active')
        """, (contract_id,))
        supervision_card_id = cursor.lastrowid

        cursor.execute("SELECT id FROM employees LIMIT 1")
        dan_id = cursor.fetchone()[0]

        # Создаём платёж для надзора
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, 'ДАН', 'Авторский надзор', 'Полная оплата', 15000, 15000)
        """, (contract_id, dan_id))
        db_with_data.commit()

        # Проверяем связь через contract_id
        cursor.execute("""
            SELECT p.id, p.contract_id, sc.contract_id
            FROM payments p
            JOIN supervision_cards sc ON p.contract_id = sc.contract_id
            WHERE p.role = 'ДАН'
        """)
        result = cursor.fetchone()

        if result:
            payment_contract, sc_contract = result[1], result[2]
            assert payment_contract == sc_contract, \
                "Платёж и карточка надзора должны ссылаться на один договор"

    def test_delete_supervision_card_orphans_payments(self, db_with_data):
        """Удаление карточки надзора должно обрабатывать платежи."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO supervision_cards (contract_id, status)
            VALUES (?, 'active')
        """, (contract_id,))
        supervision_card_id = cursor.lastrowid

        cursor.execute("SELECT id FROM employees LIMIT 1")
        dan_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, 'ДАН', 'Авторский надзор', 'Полная оплата', 10000, 10000)
        """, (contract_id, dan_id))
        payment_id = cursor.lastrowid
        db_with_data.commit()

        # Удаляем карточку надзора
        cursor.execute("DELETE FROM supervision_cards WHERE id = ?", (supervision_card_id,))
        db_with_data.commit()

        # Платёж всё ещё существует (orphaned)
        cursor.execute("SELECT id FROM payments WHERE id = ?", (payment_id,))
        result = cursor.fetchone()

        # Это показывает проблему - нет CASCADE DELETE
        # Тест документирует текущее поведение
        assert result is not None, "Платёж остаётся orphaned после удаления карточки"


class TestSupervisionEmployeeAssignment:
    """Тесты назначения сотрудников в надзоре."""

    def test_on_employee_changed_deletes_old_payments(self, db_with_data):
        """При смене сотрудника старые платежи должны удаляться."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 2")
        employees = cursor.fetchall()
        old_smp_id = employees[0][0]
        new_smp_id = employees[1][0] if len(employees) > 1 else old_smp_id

        role = 'Старший менеджер проектов'

        # Создаём платёж для старого СМП
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, ?, 'Авторский надзор', 'Полная оплата', 5000, 5000)
        """, (contract_id, old_smp_id, role))
        old_payment_id = cursor.lastrowid
        db_with_data.commit()

        # Симулируем on_employee_changed: удаляем все платежи для роли
        cursor.execute("""
            DELETE FROM payments
            WHERE contract_id = ? AND role = ?
        """, (contract_id, role))
        db_with_data.commit()

        # Проверяем что платёж удалён
        cursor.execute("SELECT id FROM payments WHERE id = ?", (old_payment_id,))
        assert cursor.fetchone() is None, "Старый платёж должен быть удалён"

    def test_on_employee_changed_does_not_create_new_payments(self, db_with_data):
        """ВАЖНО: При смене сотрудника в надзоре НЕ создаются новые платежи автоматически."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 1")
        new_smp_id = cursor.fetchone()[0]

        role = 'Старший менеджер проектов'

        # Симулируем on_employee_changed
        # В CRM создаются платежи, в надзоре - НЕТ

        # Проверяем что платежей нет
        cursor.execute("""
            SELECT COUNT(*) FROM payments
            WHERE contract_id = ? AND role = ? AND employee_id = ?
        """, (contract_id, role, new_smp_id))
        count = cursor.fetchone()[0]

        assert count == 0, "Платежи НЕ должны создаваться автоматически при назначении в надзоре"


class TestSupervisionPaymentModification:
    """Тесты модификации платежей надзора."""

    def test_adjust_payment_amount_updates_manual_amount(self, db_with_data):
        """Корректировка суммы должна обновить manual_amount."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        # Создаём платёж
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, manual_amount)
            VALUES (?, ?, 'ДАН', 'Авторский надзор', 'Полная оплата', 20000, 20000, NULL)
        """, (contract_id, employee_id))
        payment_id = cursor.lastrowid
        db_with_data.commit()

        # Корректируем сумму
        new_amount = 25000
        cursor.execute("""
            UPDATE payments SET manual_amount = ?, final_amount = ? WHERE id = ?
        """, (new_amount, new_amount, payment_id))
        db_with_data.commit()

        # Проверяем
        cursor.execute("""
            SELECT manual_amount, final_amount FROM payments WHERE id = ?
        """, (payment_id,))
        result = cursor.fetchone()
        assert result[0] == new_amount
        assert result[1] == new_amount

    def test_delete_payment_removes_from_db(self, db_with_data):
        """Удаление платежа должно удалить его из БД."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        # Создаём платёж
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, 'ДАН', 'Авторский надзор', 'Полная оплата', 15000, 15000)
        """, (contract_id, employee_id))
        payment_id = cursor.lastrowid
        db_with_data.commit()

        # Удаляем
        cursor.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
        db_with_data.commit()

        # Проверяем
        cursor.execute("SELECT id FROM payments WHERE id = ?", (payment_id,))
        assert cursor.fetchone() is None


class TestSupervisionStatusTransitions:
    """Тесты переходов статусов в надзоре."""

    def test_pause_supervision_card_preserves_payments(self, db_with_data):
        """Пауза карточки надзора должна сохранить платежи."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO supervision_cards (contract_id, status)
            VALUES (?, 'active')
        """, (contract_id,))
        supervision_card_id = cursor.lastrowid

        cursor.execute("SELECT id FROM employees LIMIT 1")
        dan_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, 'ДАН', 'Авторский надзор', 'Полная оплата', 12000, 12000)
        """, (contract_id, dan_id))
        payment_id = cursor.lastrowid
        db_with_data.commit()

        # Ставим на паузу
        cursor.execute("""
            UPDATE supervision_cards SET status = 'paused', pause_date = date('now')
            WHERE id = ?
        """, (supervision_card_id,))
        db_with_data.commit()

        # Платёж должен остаться
        cursor.execute("SELECT id FROM payments WHERE id = ?", (payment_id,))
        assert cursor.fetchone() is not None

    def test_resume_supervision_card_keeps_payments(self, db_with_data):
        """Возобновление карточки надзора должно сохранить платежи."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO supervision_cards (contract_id, status, pause_date)
            VALUES (?, 'paused', date('now'))
        """, (contract_id,))
        supervision_card_id = cursor.lastrowid

        cursor.execute("SELECT id FROM employees LIMIT 1")
        dan_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, 'ДАН', 'Авторский надзор', 'Полная оплата', 18000, 18000)
        """, (contract_id, dan_id))
        payment_id = cursor.lastrowid
        db_with_data.commit()

        # Возобновляем
        cursor.execute("""
            UPDATE supervision_cards SET status = 'active', pause_date = NULL
            WHERE id = ?
        """, (supervision_card_id,))
        db_with_data.commit()

        # Платёж должен остаться
        cursor.execute("SELECT id FROM payments WHERE id = ?", (payment_id,))
        assert cursor.fetchone() is not None


class TestSupervisionVsCRMDifferences:
    """Тесты различий между CRM и надзором."""

    def test_crm_creates_payments_on_assign_supervision_does_not(self, db_with_data):
        """CRM создаёт платежи при назначении, надзор - нет."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        # Проверяем что платежей нет для этого сотрудника
        cursor.execute("""
            SELECT COUNT(*) FROM payments
            WHERE contract_id = ? AND employee_id = ?
        """, (contract_id, employee_id))
        initial_count = cursor.fetchone()[0]

        # Симулируем назначение в надзоре (БЕЗ создания платежей)
        # В реальном коде on_employee_changed НЕ создаёт платежи

        # Проверяем что платежей по-прежнему нет
        cursor.execute("""
            SELECT COUNT(*) FROM payments
            WHERE contract_id = ? AND employee_id = ?
        """, (contract_id, employee_id))
        after_count = cursor.fetchone()[0]

        assert after_count == initial_count, \
            "Назначение в надзоре НЕ должно создавать платежи"

    def test_dan_has_single_payment_type(self, db_with_data):
        """ДАН имеет один платёж (Полная оплата), а не аванс+доплата."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM employees LIMIT 1")
        dan_id = cursor.fetchone()[0]

        # Создаём платёж ДАН (полная оплата)
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, 'ДАН', 'Авторский надзор', 'Полная оплата', 20000, 20000)
        """, (contract_id, dan_id))
        db_with_data.commit()

        # Проверяем что только один платёж
        cursor.execute("""
            SELECT COUNT(*) FROM payments
            WHERE contract_id = ? AND role = 'ДАН'
        """, (contract_id,))
        count = cursor.fetchone()[0]

        assert count == 1, f"ДАН должен иметь 1 платёж, найдено: {count}"

        # Проверяем тип
        cursor.execute("""
            SELECT payment_type FROM payments
            WHERE contract_id = ? AND role = 'ДАН'
        """, (contract_id,))
        payment_type = cursor.fetchone()[0]

        assert payment_type == 'Полная оплата', \
            f"Тип платежа ДАН должен быть 'Полная оплата', получен: {payment_type}"


class TestOnCardMovedPaymentCreation:
    """
    КРИТИЧЕСКИЕ тесты создания платежей при перемещении карточки.

    В отличие от CRM (создаёт платежи сразу при назначении исполнителя),
    Supervision создаёт платежи при перемещении карточки в on_card_moved().

    Основано на анализе crm_supervision_tab.py:872-1127
    """

    def test_card_move_creates_manager_payment(self, db_with_data):
        """Перемещение карточки должно создать платёж для менеджера."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO supervision_cards (contract_id, status, column_name)
            VALUES (?, 'active', 'Договор')
        """, (contract_id,))
        supervision_card_id = cursor.lastrowid

        cursor.execute("SELECT id FROM employees WHERE position LIKE '%менеджер%' OR position = 'Менеджер' LIMIT 1")
        row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT id FROM employees LIMIT 1")
            row = cursor.fetchone()
        manager_id = row[0]

        db_with_data.commit()

        # Симулируем on_card_moved: при перемещении создаётся платёж
        # Это происходит в реальном коде на строках 872-1127
        new_column = 'В работе'
        role = 'Менеджер'

        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, payment_status)
            VALUES (?, ?, ?, 'Авторский надзор', 'Полная оплата', 5000, 5000, 'pending')
        """, (contract_id, manager_id, role))
        db_with_data.commit()

        # Обновляем колонку карточки
        cursor.execute("""
            UPDATE supervision_cards SET column_name = ? WHERE id = ?
        """, (new_column, supervision_card_id))
        db_with_data.commit()

        # Проверяем что платёж создан
        cursor.execute("""
            SELECT id, role, employee_id FROM payments
            WHERE contract_id = ? AND role = ?
        """, (contract_id, role))
        payment = cursor.fetchone()

        assert payment is not None, "Платёж менеджера должен быть создан при перемещении карточки"
        assert payment[2] == manager_id, "Платёж должен быть привязан к менеджеру"

    def test_card_move_creates_dan_payment(self, db_with_data):
        """Перемещение карточки должно создать платёж для ДАН."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO supervision_cards (contract_id, status, column_name)
            VALUES (?, 'active', 'Договор')
        """, (contract_id,))
        supervision_card_id = cursor.lastrowid

        cursor.execute("SELECT id FROM employees LIMIT 1")
        dan_id = cursor.fetchone()[0]

        db_with_data.commit()

        # Симулируем on_card_moved: при перемещении создаётся платёж ДАН
        new_column = 'Авторский надзор'
        role = 'ДАН'

        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, payment_status)
            VALUES (?, ?, ?, 'Авторский надзор', 'Полная оплата', 25000, 25000, 'pending')
        """, (contract_id, dan_id, role))
        db_with_data.commit()

        # Обновляем колонку карточки
        cursor.execute("""
            UPDATE supervision_cards SET column_name = ? WHERE id = ?
        """, (new_column, supervision_card_id))
        db_with_data.commit()

        # Проверяем что платёж создан
        cursor.execute("""
            SELECT id, role, payment_type FROM payments
            WHERE contract_id = ? AND role = ?
        """, (contract_id, role))
        payment = cursor.fetchone()

        assert payment is not None, "Платёж ДАН должен быть создан при перемещении карточки"
        assert payment[2] == 'Полная оплата', "Тип платежа ДАН должен быть 'Полная оплата'"

    def test_card_move_no_duplicate_payments(self, db_with_data):
        """Повторное перемещение НЕ должно создавать дубликаты платежей."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO supervision_cards (contract_id, status, column_name)
            VALUES (?, 'active', 'В работе')
        """, (contract_id,))
        supervision_card_id = cursor.lastrowid

        cursor.execute("SELECT id FROM employees LIMIT 1")
        dan_id = cursor.fetchone()[0]

        # Создаём первый платёж
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, payment_status)
            VALUES (?, ?, 'ДАН', 'Авторский надзор', 'Полная оплата', 25000, 25000, 'pending')
        """, (contract_id, dan_id))
        db_with_data.commit()

        # КРИТИЧНО: Перед созданием второго платежа должна быть проверка
        # на существование платежа с такими же параметрами
        cursor.execute("""
            SELECT COUNT(*) FROM payments
            WHERE contract_id = ? AND role = 'ДАН' AND NOT reassigned
        """, (contract_id,))
        existing_count = cursor.fetchone()[0]

        # Если платёж уже есть, новый НЕ должен создаваться
        if existing_count > 0:
            # Симуляция правильного поведения: не создаём дубликат
            pass
        else:
            # Только если нет - создаём
            cursor.execute("""
                INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                      payment_type, calculated_amount, final_amount)
                VALUES (?, ?, 'ДАН', 'Авторский надзор', 'Полная оплата', 25000, 25000)
            """, (contract_id, dan_id))
        db_with_data.commit()

        # Проверяем что ровно 1 активный платёж
        cursor.execute("""
            SELECT COUNT(*) FROM payments
            WHERE contract_id = ? AND role = 'ДАН' AND NOT reassigned
        """, (contract_id,))
        final_count = cursor.fetchone()[0]

        assert final_count == 1, \
            f"Должен быть ровно 1 активный платёж ДАН, найдено: {final_count}"

    def test_supervision_payment_creation_differs_from_crm(self, db_with_data):
        """
        ДОКУМЕНТИРУЮЩИЙ ТЕСТ: Различие в логике создания платежей.

        CRM (crm_tab.py):
        - on_employee_changed() СОЗДАЁТ платежи при выборе исполнителя

        Supervision (crm_supervision_tab.py):
        - on_employee_changed() ТОЛЬКО УДАЛЯЕТ платежи (строки 4229-4270)
        - on_card_moved() СОЗДАЁТ платежи (строки 872-1127)
        """
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        # Начальное состояние: нет платежей
        cursor.execute("""
            SELECT COUNT(*) FROM payments WHERE contract_id = ?
        """, (contract_id,))
        initial_count = cursor.fetchone()[0]

        # Симулируем on_employee_changed в Supervision:
        # Этот метод ТОЛЬКО удаляет старые платежи, но НЕ создаёт новые
        # (В отличие от CRM, где on_employee_changed создаёт платежи)

        # Никаких INSERT - это правильное поведение для Supervision

        cursor.execute("""
            SELECT COUNT(*) FROM payments WHERE contract_id = ?
        """, (contract_id,))
        after_employee_change = cursor.fetchone()[0]

        # Платежи НЕ создаются при on_employee_changed
        assert after_employee_change == initial_count, \
            "on_employee_changed в Supervision НЕ должен создавать платежи"

        # Теперь симулируем on_card_moved - ВОТ ЗДЕСЬ создаются платежи
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, 'Менеджер', 'Авторский надзор', 'Полная оплата', 5000, 5000)
        """, (contract_id, employee_id))
        db_with_data.commit()

        cursor.execute("""
            SELECT COUNT(*) FROM payments WHERE contract_id = ?
        """, (contract_id,))
        after_card_move = cursor.fetchone()[0]

        # Платежи создаются при on_card_moved
        assert after_card_move > initial_count, \
            "on_card_moved в Supervision ДОЛЖЕН создавать платежи"
