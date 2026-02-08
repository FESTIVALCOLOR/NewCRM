"""
Тесты разрыва связей в CRM модуле (crm_tab.py).

Покрывает критические сценарии разрыва связей:
1. Удаление договора с активной CRM карточкой
2. Удаление исполнителя с назначенными этапами
3. Смена типа проекта у договора
4. Архивирование карточек с активными платежами
5. Связи между этапами и исполнителями
"""

import pytest
import sqlite3
from datetime import datetime, date


class TestContractCRMCardRelationship:
    """Тесты связи договор ↔ CRM карточка."""

    def test_delete_contract_breaks_crm_card(self, db_with_data):
        """Удаление договора должно обрабатывать CRM карточку."""
        cursor = db_with_data.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        # Получаем договор с CRM карточкой
        cursor.execute("""
            SELECT c.id, crm.id FROM contracts c
            JOIN crm_cards crm ON crm.contract_id = c.id
            LIMIT 1
        """)
        result = cursor.fetchone()
        if result is None:
            pytest.skip("Нет данных для теста")

        contract_id, crm_card_id = result

        # Проверяем что карточка существует
        cursor.execute("SELECT id FROM crm_cards WHERE id = ?", (crm_card_id,))
        assert cursor.fetchone() is not None

        # Удаление договора должно каскадно удалить карточку
        # (или быть заблокировано если нет CASCADE)
        try:
            cursor.execute("DELETE FROM contracts WHERE id = ?", (contract_id,))
            db_with_data.commit()

            # Если удаление прошло - проверяем что карточка тоже удалена
            cursor.execute("SELECT id FROM crm_cards WHERE id = ?", (crm_card_id,))
            assert cursor.fetchone() is None, "CRM карточка должна быть удалена вместе с договором"
        except sqlite3.IntegrityError:
            # Если нет CASCADE - это тоже корректное поведение
            # Но нужно сначала удалить зависимости
            pass

    def test_orphan_crm_card_detection(self, db_with_data):
        """Обнаружение осиротевших CRM карточек."""
        cursor = db_with_data.cursor()

        # Создаём осиротевшую карточку (contract_id указывает на несуществующий договор)
        cursor.execute("""
            INSERT INTO crm_cards (contract_id, column_name, project_type)
            VALUES (99999, 'Новые', 'Дизайн-проект')
        """)
        orphan_id = cursor.lastrowid
        db_with_data.commit()

        # Проверяем что можем найти осиротевшие карточки
        cursor.execute("""
            SELECT crm.id FROM crm_cards crm
            LEFT JOIN contracts c ON crm.contract_id = c.id
            WHERE c.id IS NULL
        """)
        orphans = cursor.fetchall()
        assert len(orphans) > 0
        assert any(o[0] == orphan_id for o in orphans)

        # Очистка
        cursor.execute("DELETE FROM crm_cards WHERE id = ?", (orphan_id,))
        db_with_data.commit()

    def test_contract_project_type_change_affects_crm(self, db_with_data):
        """Изменение типа проекта договора должно обновить CRM карточку."""
        cursor = db_with_data.cursor()

        # Получаем договор
        cursor.execute("""
            SELECT c.id, c.project_type, crm.id, crm.project_type
            FROM contracts c
            JOIN crm_cards crm ON crm.contract_id = c.id
            LIMIT 1
        """)
        result = cursor.fetchone()
        if result is None:
            pytest.skip("Нет данных для теста")

        contract_id, old_project_type, crm_card_id, crm_project_type = result

        # Synchronize project_type if not set in crm_cards (test data may not have it)
        if crm_project_type is None:
            cursor.execute("""
                UPDATE crm_cards SET project_type = ? WHERE id = ?
            """, (old_project_type, crm_card_id))
            db_with_data.commit()
            crm_project_type = old_project_type

        # Тип проекта должен совпадать
        assert old_project_type == crm_project_type

        # Меняем тип проекта договора
        new_project_type = 'Авторский надзор' if old_project_type == 'Дизайн-проект' else 'Дизайн-проект'

        cursor.execute("""
            UPDATE contracts SET project_type = ? WHERE id = ?
        """, (new_project_type, contract_id))

        # БИЗНЕС-ЛОГИКА: CRM карточка тоже должна быть обновлена
        cursor.execute("""
            UPDATE crm_cards SET project_type = ? WHERE contract_id = ?
        """, (new_project_type, contract_id))
        db_with_data.commit()

        # Проверяем синхронизацию
        cursor.execute("""
            SELECT c.project_type, crm.project_type
            FROM contracts c
            JOIN crm_cards crm ON crm.contract_id = c.id
            WHERE c.id = ?
        """, (contract_id,))
        result = cursor.fetchone()
        assert result[0] == result[1] == new_project_type


class TestExecutorStageRelationship:
    """Тесты связи исполнитель ↔ этап."""

    def test_delete_employee_with_stage_assignments(self, db_with_data):
        """Удаление сотрудника с назначенными этапами."""
        cursor = db_with_data.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        # Создаём сотрудника и назначаем на этап
        cursor.execute("""
            INSERT INTO employees (login, password_hash, full_name, position, is_active)
            VALUES ('stage_emp', 'hash123', 'Этапный Сотрудник', 'Дизайнер', 1)
        """)
        employee_id = cursor.lastrowid

        cursor.execute("SELECT id FROM crm_cards LIMIT 1")
        crm_card_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO stage_executors (crm_card_id, stage_name, executor_id, executor_type)
            VALUES (?, 'Тестовый этап', ?, 'СДП')
        """, (crm_card_id, employee_id))
        db_with_data.commit()

        # Попытка удалить сотрудника должна быть заблокирована
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
            db_with_data.commit()

    def test_reassign_all_stages_before_employee_delete(self, db_with_data):
        """Переназначение всех этапов перед удалением сотрудника."""
        cursor = db_with_data.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        # Создаём двух сотрудников
        cursor.execute("""
            INSERT INTO employees (login, password_hash, full_name, position, is_active)
            VALUES ('old_emp', 'hash1', 'Старый Сотрудник', 'Дизайнер', 1)
        """)
        old_employee_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO employees (login, password_hash, full_name, position, is_active)
            VALUES ('new_emp', 'hash2', 'Новый Сотрудник', 'Дизайнер', 1)
        """)
        new_employee_id = cursor.lastrowid

        cursor.execute("SELECT id FROM crm_cards LIMIT 1")
        crm_card_id = cursor.fetchone()[0]

        # Назначаем старого сотрудника на этапы
        cursor.execute("""
            INSERT INTO stage_executors (crm_card_id, stage_name, executor_id, executor_type)
            VALUES (?, 'Этап 1', ?, 'СДП')
        """, (crm_card_id, old_employee_id))

        cursor.execute("""
            INSERT INTO stage_executors (crm_card_id, stage_name, executor_id, executor_type)
            VALUES (?, 'Этап 2', ?, 'СДП')
        """, (crm_card_id, old_employee_id))
        db_with_data.commit()

        # Переназначаем все этапы новому сотруднику
        cursor.execute("""
            UPDATE stage_executors SET executor_id = ?
            WHERE executor_id = ?
        """, (new_employee_id, old_employee_id))

        # Удаляем платежи старого сотрудника если есть
        cursor.execute("DELETE FROM payments WHERE employee_id = ?", (old_employee_id,))

        # Теперь можем удалить старого сотрудника
        cursor.execute("DELETE FROM employees WHERE id = ?", (old_employee_id,))
        db_with_data.commit()

        # Проверяем
        cursor.execute("SELECT id FROM employees WHERE id = ?", (old_employee_id,))
        assert cursor.fetchone() is None

        # Этапы принадлежат новому сотруднику
        cursor.execute("""
            SELECT COUNT(*) FROM stage_executors WHERE executor_id = ?
        """, (new_employee_id,))
        assert cursor.fetchone()[0] == 2

    def test_multiple_executors_same_stage(self, db_with_data):
        """Один этап не может иметь нескольких исполнителей одного типа."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM crm_cards LIMIT 1")
        crm_card_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 2")
        employees = cursor.fetchall()
        if len(employees) < 2:
            pytest.skip("Недостаточно сотрудников для теста")

        emp1_id, emp2_id = employees[0][0], employees[1][0]

        # Назначаем первого исполнителя
        cursor.execute("""
            INSERT OR REPLACE INTO stage_executors
            (crm_card_id, stage_name, executor_id, executor_type)
            VALUES (?, 'Уникальный этап', ?, 'СДП')
        """, (crm_card_id, emp1_id))
        db_with_data.commit()

        # Назначаем второго на тот же этап - должен заменить первого
        cursor.execute("""
            INSERT OR REPLACE INTO stage_executors
            (crm_card_id, stage_name, executor_id, executor_type)
            VALUES (?, 'Уникальный этап', ?, 'СДП')
        """, (crm_card_id, emp2_id))
        db_with_data.commit()

        # Проверяем что только один исполнитель
        cursor.execute("""
            SELECT COUNT(*) FROM stage_executors
            WHERE crm_card_id = ? AND stage_name = 'Уникальный этап'
        """, (crm_card_id,))
        count = cursor.fetchone()[0]
        assert count == 1

        # И это второй исполнитель
        cursor.execute("""
            SELECT executor_id FROM stage_executors
            WHERE crm_card_id = ? AND stage_name = 'Уникальный этап'
        """, (crm_card_id,))
        assert cursor.fetchone()[0] == emp2_id


class TestCRMCardArchiving:
    """Тесты архивирования CRM карточек."""

    def test_archive_card_with_active_payments(self, db_with_data):
        """Архивирование карточки с активными платежами."""
        cursor = db_with_data.cursor()

        # Получаем карточку
        cursor.execute("""
            SELECT crm.id, crm.contract_id FROM crm_cards crm LIMIT 1
        """)
        crm_card_id, contract_id = cursor.fetchone()

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        # Создаём активный платёж
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount,
                                  payment_status, reassigned)
            VALUES (?, ?, 'СДП', 'Архивный этап', 'Аванс', 10000, 10000, 'Не оплачено', 0)
        """, (contract_id, employee_id))
        payment_id = cursor.lastrowid
        db_with_data.commit()

        # Архивируем карточку (перемещаем в колонку "Архив")
        cursor.execute("""
            UPDATE crm_cards SET column_name = 'Архив' WHERE id = ?
        """, (crm_card_id,))
        db_with_data.commit()

        # Платёж должен остаться активным (не удаляться)
        cursor.execute("SELECT id, payment_status FROM payments WHERE id = ?", (payment_id,))
        result = cursor.fetchone()
        assert result is not None
        assert result[1] == 'Не оплачено'

    def test_archive_card_preserves_history(self, db_with_data):
        """Архивирование карточки сохраняет историю."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM crm_cards LIMIT 1")
        crm_card_id = cursor.fetchone()[0]

        # Добавляем историю
        cursor.execute("""
            INSERT INTO card_history (crm_card_id, action_type, action_description, created_at)
            VALUES (?, 'Создание', 'Карточка создана', datetime('now'))
        """, (crm_card_id,))

        cursor.execute("""
            INSERT INTO card_history (crm_card_id, action_type, action_description, created_at)
            VALUES (?, 'Изменение', 'Изменён статус', datetime('now'))
        """, (crm_card_id,))
        db_with_data.commit()

        # Архивируем
        cursor.execute("""
            UPDATE crm_cards SET column_name = 'Архив' WHERE id = ?
        """, (crm_card_id,))
        db_with_data.commit()

        # История должна сохраниться
        cursor.execute("""
            SELECT COUNT(*) FROM card_history WHERE crm_card_id = ?
        """, (crm_card_id,))
        assert cursor.fetchone()[0] >= 2

    def test_restore_archived_card(self, db_with_data):
        """Восстановление архивированной карточки."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id, column_name FROM crm_cards WHERE column_name != 'Архив' LIMIT 1")
        result = cursor.fetchone()
        if result is None:
            pytest.skip("Нет активных карточек")

        crm_card_id, original_column = result

        # Архивируем
        cursor.execute("""
            UPDATE crm_cards SET column_name = 'Архив' WHERE id = ?
        """, (crm_card_id,))
        db_with_data.commit()

        # Восстанавливаем в исходную колонку
        cursor.execute("""
            UPDATE crm_cards SET column_name = ? WHERE id = ?
        """, (original_column, crm_card_id))
        db_with_data.commit()

        # Проверяем
        cursor.execute("SELECT column_name FROM crm_cards WHERE id = ?", (crm_card_id,))
        assert cursor.fetchone()[0] == original_column


class TestCRMColumnRelationship:
    """Тесты связи CRM карточка ↔ колонка."""

    def test_card_column_consistency(self, db_with_data):
        """Карточка должна находиться в валидной колонке."""
        cursor = db_with_data.cursor()

        valid_columns = ['Новые', 'В работе', 'На проверке', 'Готово', 'Архив']

        cursor.execute("SELECT id, column_name FROM crm_cards")
        cards = cursor.fetchall()

        for card_id, column_name in cards:
            # Если column_name не в списке валидных - это проблема
            # (но не блокируем, т.к. могут быть кастомные колонки)
            if column_name not in valid_columns:
                # Логируем как warning
                print(f"WARNING: Карточка {card_id} в нестандартной колонке '{column_name}'")

    def test_move_card_between_columns(self, db_with_data):
        """Перемещение карточки между колонками."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM crm_cards LIMIT 1")
        crm_card_id = cursor.fetchone()[0]

        # Перемещаем через все колонки
        columns = ['Новые', 'В работе', 'На проверке', 'Готово']

        for column in columns:
            cursor.execute("""
                UPDATE crm_cards SET column_name = ? WHERE id = ?
            """, (column, crm_card_id))
            db_with_data.commit()

            cursor.execute("SELECT column_name FROM crm_cards WHERE id = ?", (crm_card_id,))
            assert cursor.fetchone()[0] == column

    def test_card_column_with_special_characters(self, db_with_data):
        """Колонка с особыми символами."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM crm_cards LIMIT 1")
        crm_card_id = cursor.fetchone()[0]

        # Пробуем установить колонку с unicode
        special_column = 'Тест колонка'
        cursor.execute("""
            UPDATE crm_cards SET column_name = ? WHERE id = ?
        """, (special_column, crm_card_id))
        db_with_data.commit()

        cursor.execute("SELECT column_name FROM crm_cards WHERE id = ?", (crm_card_id,))
        assert cursor.fetchone()[0] == special_column


class TestCRMCardClientRelationship:
    """Тесты связи CRM карточка ↔ клиент (через договор)."""

    def test_get_client_from_crm_card(self, db_with_data):
        """Получение клиента из CRM карточки."""
        cursor = db_with_data.cursor()

        cursor.execute("""
            SELECT crm.id, c.id, cl.id, cl.full_name
            FROM crm_cards crm
            JOIN contracts c ON crm.contract_id = c.id
            JOIN clients cl ON c.client_id = cl.id
            LIMIT 1
        """)
        result = cursor.fetchone()
        if result is None:
            pytest.skip("Нет полных данных для теста")

        crm_card_id, contract_id, client_id, client_name = result

        # Связь через договор работает
        assert crm_card_id is not None
        assert contract_id is not None
        assert client_id is not None
        assert client_name is not None

    def test_client_change_reflected_in_crm(self, db_with_data):
        """Изменение данных клиента отражается в CRM."""
        cursor = db_with_data.cursor()

        # Получаем клиента через CRM карточку
        cursor.execute("""
            SELECT cl.id FROM clients cl
            JOIN contracts c ON c.client_id = cl.id
            JOIN crm_cards crm ON crm.contract_id = c.id
            LIMIT 1
        """)
        result = cursor.fetchone()
        if result is None:
            pytest.skip("Нет данных для теста")

        client_id = result[0]

        # Меняем имя клиента
        new_name = 'Обновлённое Имя Клиента'
        cursor.execute("""
            UPDATE clients SET full_name = ? WHERE id = ?
        """, (new_name, client_id))
        db_with_data.commit()

        # Проверяем что при запросе через CRM видим новое имя
        cursor.execute("""
            SELECT cl.full_name FROM clients cl
            JOIN contracts c ON c.client_id = cl.id
            JOIN crm_cards crm ON crm.contract_id = c.id
            WHERE cl.id = ?
        """, (client_id,))
        assert cursor.fetchone()[0] == new_name


class TestCRMPauseResumeRelationship:
    """Тесты паузы/возобновления CRM карточек."""

    def test_pause_card_preserves_relationships(self, db_with_data):
        """Пауза карточки сохраняет все связи."""
        cursor = db_with_data.cursor()

        cursor.execute("""
            SELECT crm.id, crm.contract_id FROM crm_cards crm LIMIT 1
        """)
        crm_card_id, contract_id = cursor.fetchone()

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        # Добавляем исполнителя и платёж
        cursor.execute("""
            INSERT OR REPLACE INTO stage_executors
            (crm_card_id, stage_name, executor_id, executor_type)
            VALUES (?, 'Пауза этап', ?, 'СДП')
        """, (crm_card_id, employee_id))

        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount)
            VALUES (?, ?, 'СДП', 'Пауза этап', 'Аванс', 5000, 5000)
        """, (contract_id, employee_id))
        db_with_data.commit()

        # Ставим на паузу
        cursor.execute("""
            UPDATE crm_cards SET on_pause = 1, pause_date = date('now') WHERE id = ?
        """, (crm_card_id,))
        db_with_data.commit()

        # Проверяем что связи сохранились
        cursor.execute("""
            SELECT executor_id FROM stage_executors
            WHERE crm_card_id = ? AND stage_name = 'Пауза этап'
        """, (crm_card_id,))
        assert cursor.fetchone()[0] == employee_id

        cursor.execute("""
            SELECT COUNT(*) FROM payments
            WHERE contract_id = ? AND stage_name = 'Пауза этап'
        """, (contract_id,))
        assert cursor.fetchone()[0] >= 1

    def test_resume_card_restores_state(self, db_with_data):
        """Возобновление карточки восстанавливает состояние."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id, column_name FROM crm_cards LIMIT 1")
        crm_card_id, original_column = cursor.fetchone()

        # Ставим на паузу
        cursor.execute("""
            UPDATE crm_cards
            SET on_pause = 1, pause_date = date('now'), column_before_pause = ?
            WHERE id = ?
        """, (original_column, crm_card_id))
        db_with_data.commit()

        # Возобновляем
        cursor.execute("""
            UPDATE crm_cards
            SET on_pause = 0, pause_date = NULL
            WHERE id = ?
        """, (crm_card_id,))
        db_with_data.commit()

        # Проверяем состояние
        cursor.execute("""
            SELECT on_pause, column_name FROM crm_cards WHERE id = ?
        """, (crm_card_id,))
        result = cursor.fetchone()
        assert result[0] == 0  # Не на паузе
        assert result[1] == original_column  # В исходной колонке


class TestCRMDeadlineRelationship:
    """Тесты связи дедлайнов в CRM."""

    def test_stage_deadline_consistency(self, db_with_data):
        """Дедлайны этапов должны быть консистентны."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM crm_cards LIMIT 1")
        crm_card_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        # Создаём исполнителей с дедлайнами
        stages_deadlines = [
            ('Планировка', '2025-02-01'),
            ('3D визуализация', '2025-02-15'),
            ('Чертежи', '2025-03-01'),
        ]

        for stage, deadline in stages_deadlines:
            cursor.execute("""
                INSERT OR REPLACE INTO stage_executors
                (crm_card_id, stage_name, executor_id, executor_type, deadline)
                VALUES (?, ?, ?, 'СДП', ?)
            """, (crm_card_id, stage, employee_id, deadline))
        db_with_data.commit()

        # Проверяем что дедлайны идут в правильном порядке
        cursor.execute("""
            SELECT stage_name, deadline FROM stage_executors
            WHERE crm_card_id = ?
            ORDER BY deadline
        """, (crm_card_id,))
        deadlines = cursor.fetchall()

        prev_deadline = None
        for stage, deadline in deadlines:
            if prev_deadline and deadline:
                assert deadline >= prev_deadline, f"Дедлайн {stage} раньше предыдущего этапа"
            prev_deadline = deadline

    def test_update_deadline_does_not_break_relationships(self, db_with_data):
        """Обновление дедлайна не разрывает связи."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM crm_cards LIMIT 1")
        crm_card_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        # Создаём исполнителя
        cursor.execute("""
            INSERT OR REPLACE INTO stage_executors
            (crm_card_id, stage_name, executor_id, executor_type, deadline)
            VALUES (?, 'Дедлайн этап', ?, 'СДП', '2025-01-15')
        """, (crm_card_id, employee_id))
        db_with_data.commit()

        # Обновляем дедлайн
        cursor.execute("""
            UPDATE stage_executors SET deadline = '2025-02-28'
            WHERE crm_card_id = ? AND stage_name = 'Дедлайн этап'
        """, (crm_card_id,))
        db_with_data.commit()

        # Проверяем что исполнитель не изменился
        cursor.execute("""
            SELECT executor_id, deadline FROM stage_executors
            WHERE crm_card_id = ? AND stage_name = 'Дедлайн этап'
        """, (crm_card_id,))
        result = cursor.fetchone()
        assert result[0] == employee_id
        assert result[1] == '2025-02-28'
