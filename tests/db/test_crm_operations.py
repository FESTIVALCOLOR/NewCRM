# -*- coding: utf-8 -*-
"""
DB Tests: CRM операции DatabaseManager
Проверяет работу CRM карточек, стадий, исполнителей, manager_acceptance.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ============================================================
# Вспомогательные функции для создания тестовых данных
# ============================================================

def _create_client(db):
    """Создание тестового клиента."""
    return db.add_client({
        'client_type': 'Физическое лицо',
        'full_name': '__TEST__CRM Клиент',
        'phone': '+79991234567',
    })


def _create_employee(db, position='Дизайнер', name='__TEST__Сотрудник', login='__test_crm_emp'):
    """Создание тестового сотрудника."""
    return db.add_employee({
        'full_name': name,
        'phone': '+79990000001',
        'position': position,
        'login': login,
        'password': 'test123',
    })


@patch('database.db_manager.YANDEX_DISK_TOKEN', '')
def _create_contract(db, client_id, project_type='Индивидуальный', status='Новый заказ',
                     contract_number=None, area=75.0, contract_period=90):
    """Создание тестового договора (mock YandexDisk)."""
    if not contract_number:
        import random
        contract_number = f'__TEST__CRM_{random.randint(10000, 99999)}'
    return db.add_contract({
        'client_id': client_id,
        'project_type': project_type,
        'agent_type': 'ФЕСТИВАЛЬ',
        'city': 'СПБ',
        'contract_number': contract_number,
        'address': 'Тестовый адрес',
        'area': area,
        'total_amount': 300000,
        'status': status,
        'contract_period': contract_period,
        'contract_date': '2026-01-15',
    })


# ============================================================
# Тесты CRM карточек
# ============================================================

class TestCRMCardCreation:
    """Создание CRM карточек."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_create_crm_card_auto(self, db):
        """Автоматическое создание CRM карточки при добавлении договора."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)

        card_id = db.get_crm_card_id_by_contract(contract_id)
        assert card_id is not None, "CRM карточка должна создаваться автоматически при добавлении договора"

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_create_crm_card_column_default(self, db):
        """CRM карточка создается в колонке 'Новый заказ'."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)

        card_id = db.get_crm_card_id_by_contract(contract_id)
        card = db.get_crm_card_data(card_id)
        assert card is not None
        assert card['column_name'] == 'Новый заказ'

    def test_add_crm_card_manual(self, db):
        """Ручное создание CRM карточки через add_crm_card."""
        # Создаем договор напрямую через SQL, чтобы _create_crm_card не вызывался дважды
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clients (client_type, full_name, phone)
            VALUES ('Физическое лицо', '__TEST__Manual CRM', '+79990000099')
        """)
        client_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO contracts (client_id, project_type, contract_number, address, area, status)
            VALUES (?, 'Индивидуальный', '__TEST__MANUAL_001', 'Адрес', 50.0, 'Новый заказ')
        """, (client_id,))
        contract_id = cursor.lastrowid
        conn.commit()
        db.close()

        card_id = db.add_crm_card({'contract_id': contract_id, 'project_type': 'Индивидуальный'})
        assert card_id is not None
        assert card_id > 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_crm_card_data(self, db):
        """Получение данных CRM карточки с подзапросами для исполнителей."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)

        card = db.get_crm_card_data(card_id)
        assert card is not None
        assert card['contract_id'] == contract_id
        assert 'designer_name' in card  # Подзапрос JOIN stage_executors
        assert 'draftsman_name' in card

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_crm_card_id_by_contract_nonexistent(self, db):
        """Получение card_id для несуществующего договора."""
        result = db.get_crm_card_id_by_contract(999999)
        assert result is None


class TestCRMCardUpdate:
    """Обновление CRM карточек."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_crm_card_basic(self, db):
        """Базовое обновление карточки."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)

        db.update_crm_card(card_id, {'tags': 'VIP,Срочно'})
        card = db.get_crm_card_data(card_id)
        assert card['tags'] == 'VIP,Срочно'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_crm_card_column(self, db):
        """Обновление колонки карточки (прогресс по Kanban)."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)

        db.update_crm_card_column(card_id, 'Замер')
        card = db.get_crm_card_data(card_id)
        assert card['column_name'] == 'Замер'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_crm_card_column_waiting_saves_previous(self, db):
        """Переход в 'В ожидании' сохраняет previous_column."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)

        # Перемещаем в "Замер"
        db.update_crm_card_column(card_id, 'Замер')
        # Перемещаем в "В ожидании"
        db.update_crm_card_column(card_id, 'В ожидании')

        card = db.get_crm_card_data(card_id)
        assert card['column_name'] == 'В ожидании'
        assert card.get('previous_column') == 'Замер'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_crm_card_column_return_from_waiting(self, db):
        """Возврат из 'В ожидании' очищает previous_column."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)

        db.update_crm_card_column(card_id, 'Замер')
        db.update_crm_card_column(card_id, 'В ожидании')
        db.update_crm_card_column(card_id, 'Дизайн')

        card = db.get_crm_card_data(card_id)
        assert card['column_name'] == 'Дизайн'
        assert card.get('previous_column') is None


class TestStageExecutors:
    """Назначение и завершение стадий."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_assign_stage_executor(self, db):
        """Назначение исполнителя на этап CRM карточки."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер', '__test_designer_1')
        manager_id = _create_employee(db, 'Менеджер', '__TEST__Менеджер', '__test_mgr_1')

        db.assign_stage_executor(card_id, 'Дизайн-концепция', emp_id, assigned_by=manager_id, deadline='2026-03-01')

        executors = db.get_incomplete_stage_executors(card_id, 'Дизайн-концепция')
        assert len(executors) >= 1
        assert any(e['executor_id'] == emp_id for e in executors)

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_assign_multiple_executors(self, db):
        """Назначение нескольких исполнителей на один этап."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)
        emp1 = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер1', '__test_des_m1')
        emp2 = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер2', '__test_des_m2')
        manager = _create_employee(db, 'Менеджер', '__TEST__Менеджер Assign', '__test_mgr_m')

        db.assign_stage_executor(card_id, 'Дизайн-концепция', emp1, assigned_by=manager, deadline='2026-03-01')
        db.assign_stage_executor(card_id, 'Дизайн-концепция', emp2, assigned_by=manager, deadline='2026-03-15')

        executors = db.get_incomplete_stage_executors(card_id, 'Дизайн-концепция')
        assert len(executors) == 2

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_complete_stage_for_executor(self, db):
        """Отметка завершения стадии исполнителем."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер Complete', '__test_des_c')
        manager = _create_employee(db, 'Менеджер', '__TEST__Менеджер Complete', '__test_mgr_c')

        db.assign_stage_executor(card_id, 'Дизайн-концепция', emp_id, assigned_by=manager, deadline='2026-03-01')
        db.complete_stage_for_executor(card_id, 'Дизайн-концепция', emp_id)

        # После завершения — исполнитель НЕ должен быть в списке незавершённых
        executors = db.get_incomplete_stage_executors(card_id, 'Дизайн-концепция')
        assert len(executors) == 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_stage_completion_info(self, db):
        """Получение информации о статусе стадии."""
        # Создать таблицу approval_stages (не во всех миграциях)
        conn = db.connect()
        conn.execute('''CREATE TABLE IF NOT EXISTS approval_stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crm_card_id INTEGER,
            stage_name TEXT,
            is_approved INTEGER DEFAULT 0
        )''')
        conn.commit()
        db.close()

        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер Info', '__test_des_i')
        manager = _create_employee(db, 'Менеджер', '__TEST__Менеджер Info', '__test_mgr_i')

        db.assign_stage_executor(card_id, 'Дизайн-концепция', emp_id, assigned_by=manager, deadline='2026-03-01')

        info = db.get_stage_completion_info(card_id, 'Дизайн-концепция')
        assert info is not None
        assert 'stage' in info
        assert info['stage']['completed'] == 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_incomplete_stage_executors_empty(self, db):
        """Пустой список незавершённых исполнителей."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)

        executors = db.get_incomplete_stage_executors(card_id, 'Несуществующая стадия')
        assert executors == []

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_reset_stage_completion(self, db):
        """Сброс всех отметок о завершении."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер Reset', '__test_des_r')
        manager = _create_employee(db, 'Менеджер', '__TEST__Менеджер Reset', '__test_mgr_r')

        db.assign_stage_executor(card_id, 'Дизайн-концепция', emp_id, assigned_by=manager, deadline='2026-03-01')
        db.complete_stage_for_executor(card_id, 'Дизайн-концепция', emp_id)

        # Сбрасываем
        db.reset_stage_completion(card_id)

        executors = db.get_incomplete_stage_executors(card_id, 'Дизайн-концепция')
        assert len(executors) == 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_reset_designer_completion(self, db):
        """Сброс отметки о завершении дизайнером (stage_name LIKE '%концепция%')."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)
        designer = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер ResetD', '__test_des_rd')
        draftsman = _create_employee(db, 'Чертёжник', '__TEST__Чертёжник ResetD', '__test_dft_rd')
        manager = _create_employee(db, 'Менеджер', '__TEST__Менеджер ResetD', '__test_mgr_rd')

        db.assign_stage_executor(card_id, 'Дизайн-концепция', designer, assigned_by=manager, deadline='2026-03-01')
        db.assign_stage_executor(card_id, 'Рабочие чертежи', draftsman, assigned_by=manager, deadline='2026-04-01')
        db.complete_stage_for_executor(card_id, 'Дизайн-концепция', designer)
        db.complete_stage_for_executor(card_id, 'Рабочие чертежи', draftsman)

        # Сбрасываем ТОЛЬКО дизайнера
        db.reset_designer_completion(card_id)

        # Дизайнер — незавершён
        designers = db.get_incomplete_stage_executors(card_id, 'Дизайн-концепция')
        assert len(designers) == 1

        # Чертёжник — остаётся завершён
        draftsmen = db.get_incomplete_stage_executors(card_id, 'Рабочие чертежи')
        assert len(draftsmen) == 0


class TestCRMCardQueries:
    """Запросы CRM карточек с JOIN."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_crm_cards_by_project_type(self, db):
        """Получение карточек по типу проекта (ТОЛЬКО активные)."""
        client_id = _create_client(db)
        _create_contract(db, client_id, 'Индивидуальный', 'Новый заказ', '__TEST__IND_001')

        cards = db.get_crm_cards_by_project_type('Индивидуальный')
        assert isinstance(cards, list)
        assert len(cards) >= 1
        # Каждая карточка содержит join-поля
        for card in cards:
            assert 'contract_number' in card
            assert 'address' in card

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_crm_cards_excludes_archived(self, db):
        """Архивные карточки (СДАН/РАСТОРГНУТ) исключаются."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, 'Индивидуальный', 'Новый заказ', '__TEST__ARC_001')

        # Обновляем статус договора на СДАН
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE contracts SET status = 'СДАН' WHERE id = ?", (contract_id,))
        conn.commit()
        db.close()

        cards = db.get_crm_cards_by_project_type('Индивидуальный')
        card_contracts = [c['contract_id'] for c in cards]
        assert contract_id not in card_contracts

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_archived_crm_cards(self, db):
        """Получение архивных карточек (СДАН, РАСТОРГНУТ)."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, 'Индивидуальный', 'Новый заказ', '__TEST__ARCH_002')

        # Обновляем на СДАН
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE contracts SET status = 'СДАН' WHERE id = ?", (contract_id,))
        conn.commit()
        db.close()

        archived = db.get_archived_crm_cards('Индивидуальный')
        assert isinstance(archived, list)
        contract_ids = [c['contract_id'] for c in archived]
        assert contract_id in contract_ids

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_stage_history(self, db):
        """Получение истории стадий проекта."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)
        emp_id = _create_employee(db, 'Дизайнер', '__TEST__Дизайнер History', '__test_des_h')
        manager = _create_employee(db, 'Менеджер', '__TEST__Менеджер History', '__test_mgr_h')

        db.assign_stage_executor(card_id, 'Дизайн-концепция', emp_id, assigned_by=manager, deadline='2026-03-01')

        history = db.get_stage_history(card_id)
        assert isinstance(history, list)
        assert len(history) >= 1
        assert history[0]['stage_name'] == 'Дизайн-концепция'
        assert 'executor_name' in history[0]
        assert 'assigned_by_name' in history[0]

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_stage_history_empty(self, db):
        """Пустая история стадий."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)

        history = db.get_stage_history(card_id)
        assert history == []


class TestManagerAcceptance:
    """Принятие работы менеджером."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_save_manager_acceptance(self, db):
        """Сохранение принятия работы менеджером."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)
        manager = _create_employee(db, 'Менеджер', '__TEST__Менеджер Accept', '__test_mgr_acc')

        # Не должно выбрасывать исключение
        db.save_manager_acceptance(card_id, 'Дизайн-концепция', '__TEST__Дизайнер', manager)

        # Проверяем через get_accepted_stages
        accepted = db.get_accepted_stages(card_id)
        assert len(accepted) >= 1
        assert accepted[0]['stage_name'] == 'Дизайн-концепция'
        assert accepted[0]['executor_name'] == '__TEST__Дизайнер'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_save_multiple_acceptances(self, db):
        """Сохранение нескольких принятий для одной карточки."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        card_id = db.get_crm_card_id_by_contract(contract_id)
        manager = _create_employee(db, 'Менеджер', '__TEST__Менеджер Multi', '__test_mgr_multi')

        db.save_manager_acceptance(card_id, 'Дизайн-концепция', '__TEST__Дизайнер1', manager)
        db.save_manager_acceptance(card_id, 'Рабочие чертежи', '__TEST__Чертёжник1', manager)

        accepted = db.get_accepted_stages(card_id)
        assert len(accepted) == 2
        stage_names = [a['stage_name'] for a in accepted]
        assert 'Дизайн-концепция' in stage_names
        assert 'Рабочие чертежи' in stage_names
