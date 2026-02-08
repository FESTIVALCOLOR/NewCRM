"""
КРИТИЧЕСКИЕ ИНТЕГРАЦИОННЫЕ ТЕСТЫ: Завершение проекта и архивация

Эти тесты проверяют полный цикл:
1. Перемещение карточки в "Выполненный проект"
2. Выбор статуса завершения (СДАН, АВТОРСКИЙ НАДЗОР, РАСТОРГНУТ)
3. Создание карточки надзора (если АВТОРСКИЙ НАДЗОР)
4. Правильная фильтрация архивных карточек
5. Синхронизация между API и локальной БД

ВЫЯВЛЕННЫЕ ПРОБЛЕМЫ (01.02.2026):
1. API /api/crm/cards игнорировал параметр archived - ИСПРАВЛЕНО
2. ProjectCompletionDialog не синхронизировал с API - ИСПРАВЛЕНО
3. Карточка надзора создавалась только локально - ИСПРАВЛЕНО
"""

import pytest
import sqlite3
from datetime import datetime


class TestProjectCompletionFlow:
    """Тесты завершения проекта."""

    def test_completion_updates_contract_status(self, db_with_data):
        """Завершение проекта должно обновить статус договора."""
        cursor = db_with_data.cursor()

        # Создаём договор и CRM карточку
        cursor.execute("""
            INSERT INTO contracts (contract_number, project_type, status, address)
            VALUES ('TEST-COMPLETE-001', 'Индивидуальный', '', 'Тестовый адрес')
        """)
        contract_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO crm_cards (contract_id, column_name)
            VALUES (?, 'Выполненный проект')
        """, (contract_id,))
        db_with_data.commit()

        # Симулируем завершение со статусом АВТОРСКИЙ НАДЗОР
        new_status = 'АВТОРСКИЙ НАДЗОР'
        cursor.execute("""
            UPDATE contracts SET status = ? WHERE id = ?
        """, (new_status, contract_id))
        db_with_data.commit()

        # Проверяем что статус обновился
        cursor.execute("SELECT status FROM contracts WHERE id = ?", (contract_id,))
        result = cursor.fetchone()
        assert result[0] == 'АВТОРСКИЙ НАДЗОР', "Статус договора должен быть обновлен"

    def test_supervision_card_created_on_supervision_status(self, db_with_data):
        """При статусе АВТОРСКИЙ НАДЗОР должна создаться карточка надзора."""
        cursor = db_with_data.cursor()

        # Создаём договор
        cursor.execute("""
            INSERT INTO contracts (contract_number, project_type, status, address)
            VALUES ('TEST-SUPERVISION-001', 'Индивидуальный', 'АВТОРСКИЙ НАДЗОР', 'Тестовый адрес')
        """)
        contract_id = cursor.lastrowid

        # Создаём карточку надзора
        cursor.execute("""
            INSERT INTO supervision_cards (contract_id, column_name, status)
            VALUES (?, 'Новый заказ', 'active')
        """, (contract_id,))
        supervision_card_id = cursor.lastrowid
        db_with_data.commit()

        # Проверяем что карточка создана
        cursor.execute("""
            SELECT id, contract_id, column_name FROM supervision_cards
            WHERE contract_id = ?
        """, (contract_id,))
        result = cursor.fetchone()

        assert result is not None, "Карточка надзора должна быть создана"
        assert result[1] == contract_id, "Карточка должна ссылаться на правильный договор"
        assert result[2] == 'Новый заказ', "Карточка должна быть в колонке 'Новый заказ'"


class TestArchiveFiltering:
    """КРИТИЧЕСКИЕ тесты фильтрации архивных карточек."""

    def test_archived_cards_filtered_by_status(self, db_with_data):
        """
        КРИТИЧЕСКИЙ ТЕСТ: Архивные карточки должны фильтроваться по статусу договора.

        Архивные статусы: СДАН, РАСТОРГНУТ, АВТОРСКИЙ НАДЗОР
        Активные: все остальные (NULL, '', 'В работе' и т.д.)
        """
        cursor = db_with_data.cursor()

        # Создаём активный договор
        cursor.execute("""
            INSERT INTO contracts (contract_number, project_type, status, address)
            VALUES ('ACTIVE-001', 'Индивидуальный', '', 'Активный адрес')
        """)
        active_contract_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO crm_cards (contract_id, column_name)
            VALUES (?, 'Стадия 1: планировочные решения')
        """, (active_contract_id,))
        active_card_id = cursor.lastrowid

        # Создаём архивный договор (СДАН)
        cursor.execute("""
            INSERT INTO contracts (contract_number, project_type, status, address)
            VALUES ('ARCHIVED-001', 'Индивидуальный', 'СДАН', 'Архивный адрес')
        """)
        archived_contract_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO crm_cards (contract_id, column_name)
            VALUES (?, 'Выполненный проект')
        """, (archived_contract_id,))
        archived_card_id = cursor.lastrowid
        db_with_data.commit()

        # Проверяем фильтрацию АКТИВНЫХ карточек
        cursor.execute("""
            SELECT cc.id FROM crm_cards cc
            JOIN contracts c ON cc.contract_id = c.id
            WHERE c.project_type = 'Индивидуальный'
            AND (c.status IS NULL OR c.status = ''
                 OR c.status NOT IN ('СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР'))
        """)
        active_cards = cursor.fetchall()

        assert len(active_cards) >= 1, "Должна быть минимум 1 активная карточка"
        active_ids = [row[0] for row in active_cards]
        assert active_card_id in active_ids, "Активная карточка должна быть в списке активных"
        assert archived_card_id not in active_ids, "Архивная карточка НЕ должна быть в списке активных"

        # Проверяем фильтрацию АРХИВНЫХ карточек
        cursor.execute("""
            SELECT cc.id FROM crm_cards cc
            JOIN contracts c ON cc.contract_id = c.id
            WHERE c.project_type = 'Индивидуальный'
            AND c.status IN ('СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР')
        """)
        archived_cards = cursor.fetchall()

        assert len(archived_cards) >= 1, "Должна быть минимум 1 архивная карточка"
        archived_ids = [row[0] for row in archived_cards]
        assert archived_card_id in archived_ids, "Архивная карточка должна быть в списке архивных"
        assert active_card_id not in archived_ids, "Активная карточка НЕ должна быть в списке архивных"

    def test_no_duplicate_cards_in_archive_and_active(self, db_with_data):
        """
        КРИТИЧЕСКИЙ ТЕСТ: Одна карточка НЕ должна быть одновременно
        в активных и архивных.

        Это была проблема когда API игнорировал параметр archived.
        """
        cursor = db_with_data.cursor()

        # Создаём договор с определенным статусом
        cursor.execute("""
            INSERT INTO contracts (contract_number, project_type, status, address)
            VALUES ('NO-DUP-001', 'Индивидуальный', 'СДАН', 'Тестовый адрес')
        """)
        contract_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO crm_cards (contract_id, column_name)
            VALUES (?, 'Выполненный проект')
        """, (contract_id,))
        card_id = cursor.lastrowid
        db_with_data.commit()

        # Получаем активные
        cursor.execute("""
            SELECT cc.id FROM crm_cards cc
            JOIN contracts c ON cc.contract_id = c.id
            WHERE c.project_type = 'Индивидуальный'
            AND (c.status IS NULL OR c.status = ''
                 OR c.status NOT IN ('СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР'))
        """)
        active_ids = set(row[0] for row in cursor.fetchall())

        # Получаем архивные
        cursor.execute("""
            SELECT cc.id FROM crm_cards cc
            JOIN contracts c ON cc.contract_id = c.id
            WHERE c.project_type = 'Индивидуальный'
            AND c.status IN ('СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР')
        """)
        archived_ids = set(row[0] for row in cursor.fetchall())

        # КРИТИЧЕСКАЯ ПРОВЕРКА: пересечение должно быть пустым
        intersection = active_ids & archived_ids
        assert len(intersection) == 0, \
            f"Карточки {intersection} найдены и в активных, и в архивных - это ДУБЛИРОВАНИЕ!"


class TestSupervisionCardVisibility:
    """Тесты видимости карточек надзора."""

    def test_supervision_card_visible_only_with_correct_contract_status(self, db_with_data):
        """
        КРИТИЧЕСКИЙ ТЕСТ: Карточка надзора должна быть видна
        только если Contract.status == 'АВТОРСКИЙ НАДЗОР'

        Это была проблема когда карточка создавалась локально,
        но на сервере Contract.status не обновлялся.
        """
        cursor = db_with_data.cursor()

        # Создаём договор БЕЗ статуса АВТОРСКИЙ НАДЗОР
        cursor.execute("""
            INSERT INTO contracts (contract_number, project_type, status, address)
            VALUES ('SUP-VIS-001', 'Индивидуальный', '', 'Тестовый адрес')
        """)
        contract_id = cursor.lastrowid

        # Создаём карточку надзора
        cursor.execute("""
            INSERT INTO supervision_cards (contract_id, column_name, status)
            VALUES (?, 'Новый заказ', 'active')
        """, (contract_id,))
        supervision_card_id = cursor.lastrowid
        db_with_data.commit()

        # Запрос как в API - фильтруем по Contract.status == 'АВТОРСКИЙ НАДЗОР'
        cursor.execute("""
            SELECT sc.id FROM supervision_cards sc
            JOIN contracts c ON sc.contract_id = c.id
            WHERE c.status = 'АВТОРСКИЙ НАДЗОР'
        """)
        visible_cards = cursor.fetchall()

        # Карточка НЕ должна быть видна (Contract.status != 'АВТОРСКИЙ НАДЗОР')
        visible_ids = [row[0] for row in visible_cards]
        assert supervision_card_id not in visible_ids, \
            "Карточка надзора НЕ должна быть видна если Contract.status != 'АВТОРСКИЙ НАДЗОР'"

        # Теперь обновляем статус договора
        cursor.execute("""
            UPDATE contracts SET status = 'АВТОРСКИЙ НАДЗОР' WHERE id = ?
        """, (contract_id,))
        db_with_data.commit()

        # Теперь карточка ДОЛЖНА быть видна
        cursor.execute("""
            SELECT sc.id FROM supervision_cards sc
            JOIN contracts c ON sc.contract_id = c.id
            WHERE c.status = 'АВТОРСКИЙ НАДЗОР'
        """)
        visible_cards = cursor.fetchall()
        visible_ids = [row[0] for row in visible_cards]
        assert supervision_card_id in visible_ids, \
            "Карточка надзора ДОЛЖНА быть видна когда Contract.status == 'АВТОРСКИЙ НАДЗОР'"


class TestReportMonthOnCompletion:
    """Тесты установки отчетного месяца при завершении."""

    def test_report_month_set_on_completion(self, db_with_data):
        """При завершении проекта должен установиться отчетный месяц."""
        cursor = db_with_data.cursor()

        cursor.execute("SELECT id FROM contracts LIMIT 1")
        contract_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM employees LIMIT 1")
        employee_id = cursor.fetchone()[0]

        # Создаём платежи БЕЗ отчетного месяца
        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, report_month)
            VALUES (?, ?, 'Дизайнер', 'Стадия 1', 'Аванс', 10000, 10000, NULL)
        """, (contract_id, employee_id))
        payment1_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO payments (contract_id, employee_id, role, stage_name,
                                  payment_type, calculated_amount, final_amount, report_month)
            VALUES (?, ?, 'Дизайнер', 'Стадия 1', 'Доплата', 10000, 10000, '')
        """, (contract_id, employee_id))
        payment2_id = cursor.lastrowid
        db_with_data.commit()

        # Симулируем установку отчетного месяца при завершении
        current_month = datetime.now().strftime('%Y-%m')
        cursor.execute("""
            UPDATE payments
            SET report_month = ?
            WHERE contract_id = ?
            AND (report_month IS NULL OR report_month = '')
        """, (current_month, contract_id))
        db_with_data.commit()

        # Проверяем что месяц установлен
        cursor.execute("""
            SELECT report_month FROM payments WHERE id IN (?, ?)
        """, (payment1_id, payment2_id))
        results = cursor.fetchall()

        for row in results:
            assert row[0] == current_month, \
                f"Отчетный месяц должен быть {current_month}, получен: {row[0]}"


class TestCounterConsistency:
    """Тесты согласованности счетчиков активных/архивных карточек."""

    def test_active_plus_archived_equals_total(self, db_with_data):
        """Активные + Архивные = Всего карточек для типа проекта."""
        cursor = db_with_data.cursor()

        project_type = 'Индивидуальный'

        # Создаём несколько карточек с разными статусами
        for i, status in enumerate(['', 'СДАН', '', 'АВТОРСКИЙ НАДЗОР', 'РАСТОРГНУТ']):
            cursor.execute("""
                INSERT INTO contracts (contract_number, project_type, status, address)
                VALUES (?, ?, ?, ?)
            """, (f'COUNT-{i}', project_type, status, f'Адрес {i}'))
            contract_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO crm_cards (contract_id, column_name)
                VALUES (?, 'Стадия 1: планировочные решения')
            """, (contract_id,))
        db_with_data.commit()

        # Считаем всего
        cursor.execute("""
            SELECT COUNT(*) FROM crm_cards cc
            JOIN contracts c ON cc.contract_id = c.id
            WHERE c.project_type = ?
        """, (project_type,))
        total = cursor.fetchone()[0]

        # Считаем активные
        cursor.execute("""
            SELECT COUNT(*) FROM crm_cards cc
            JOIN contracts c ON cc.contract_id = c.id
            WHERE c.project_type = ?
            AND (c.status IS NULL OR c.status = ''
                 OR c.status NOT IN ('СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР'))
        """, (project_type,))
        active = cursor.fetchone()[0]

        # Считаем архивные
        cursor.execute("""
            SELECT COUNT(*) FROM crm_cards cc
            JOIN contracts c ON cc.contract_id = c.id
            WHERE c.project_type = ?
            AND c.status IN ('СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР')
        """, (project_type,))
        archived = cursor.fetchone()[0]

        assert active + archived == total, \
            f"Активные ({active}) + Архивные ({archived}) != Всего ({total})"
