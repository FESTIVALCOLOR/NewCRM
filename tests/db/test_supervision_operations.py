# -*- coding: utf-8 -*-
"""
DB Tests: Операции надзора DatabaseManager
Проверяет создание, обновление, паузирование, историю карточек надзора.
"""

import pytest
import sys
import os
from unittest.mock import patch
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ============================================================
# Вспомогательные функции для создания тестовых данных
# ============================================================

def _create_client(db):
    """Создание тестового клиента."""
    return db.add_client({
        'client_type': 'Физическое лицо',
        'full_name': '__TEST__Supv Клиент',
        'phone': '+79991234567',
    })


def _create_employee(db, position='ДАН', name='__TEST__Supv Сотрудник', login=None):
    """Создание тестового сотрудника."""
    if not login:
        import random
        login = f'__test_supv_{random.randint(10000, 99999)}'
    return db.add_employee({
        'full_name': name,
        'phone': '+79990000003',
        'position': position,
        'login': login,
        'password': 'test123',
    })


@patch('database.db_manager.YANDEX_DISK_TOKEN', '')
def _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР'):
    """Создание тестового договора для надзора."""
    import random
    return db.add_contract({
        'client_id': client_id,
        'project_type': 'Индивидуальный',
        'agent_type': 'ФЕСТИВАЛЬ',
        'city': 'СПБ',
        'contract_number': f'__TEST__SUPV_{random.randint(10000, 99999)}',
        'address': 'Тестовый адрес надзора',
        'area': 90.0,
        'total_amount': 200000,
        'status': status,
        'contract_period': 60,
        'contract_date': '2026-01-10',
    })


# ============================================================
# Тесты карточек надзора
# ============================================================

class TestSupervisionCardCreation:
    """Создание карточек надзора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_create_supervision_card(self, db):
        """Создание карточки надзора."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')

        card_id = db.create_supervision_card(contract_id)
        assert card_id is not None
        assert card_id > 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_create_supervision_card_idempotent(self, db):
        """Повторное создание не дублирует карточку."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')

        card_id1 = db.create_supervision_card(contract_id)
        card_id2 = db.create_supervision_card(contract_id)
        assert card_id1 == card_id2

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_create_supervision_card_default_column(self, db):
        """Карточка создаётся в колонке 'Новый заказ'."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)

        # Проверяем через SQL
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT column_name FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()

        assert row['column_name'] == 'Новый заказ'


class TestSupervisionCardQueries:
    """Запросы карточек надзора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_supervision_cards_active(self, db):
        """Получение активных карточек надзора."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        db.create_supervision_card(contract_id)

        cards = db.get_supervision_cards_active()
        assert isinstance(cards, list)
        assert len(cards) >= 1
        # JOIN-поля
        assert 'contract_number' in cards[0]
        assert 'address' in cards[0]

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_supervision_cards_archived(self, db):
        """Получение архивных карточек надзора (СДАН, РАСТОРГНУТ)."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        db.create_supervision_card(contract_id)

        # Меняем статус на СДАН
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE contracts SET status = 'СДАН' WHERE id = ?", (contract_id,))
        conn.commit()
        db.close()

        archived = db.get_supervision_cards_archived()
        assert isinstance(archived, list)
        assert len(archived) >= 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_supervision_cards_active_excludes_archived(self, db):
        """Активные карточки не включают СДАН."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)

        # Меняем на СДАН
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE contracts SET status = 'СДАН' WHERE id = ?", (contract_id,))
        conn.commit()
        db.close()

        active = db.get_supervision_cards_active()
        active_ids = [c['id'] for c in active]
        assert card_id not in active_ids


class TestSupervisionCardUpdate:
    """Обновление карточек надзора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_supervision_card(self, db):
        """Обновление полей карточки надзора."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)

        emp_id = _create_employee(db, 'ДАН', '__TEST__ДАН upd', '__test_dan_upd')
        db.update_supervision_card(card_id, {'dan_id': emp_id})

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT dan_id FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()

        assert row['dan_id'] == emp_id

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_pause_supervision_card(self, db):
        """Приостановка карточки надзора."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)
        emp_id = _create_employee(db, 'Менеджер', '__TEST__Менеджер pause', '__test_mgr_pause')

        db.pause_supervision_card(card_id, 'Клиент не отвечает', emp_id)

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT is_paused, pause_reason FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()

        assert row['is_paused'] == 1
        assert row['pause_reason'] == 'Клиент не отвечает'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_resume_supervision_card(self, db):
        """Возобновление карточки надзора."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)
        emp_id = _create_employee(db, 'Менеджер', '__TEST__Менеджер resume', '__test_mgr_resume')

        db.pause_supervision_card(card_id, 'Ожидание', emp_id)
        db.resume_supervision_card(card_id, emp_id)

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT is_paused FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()

        assert row['is_paused'] == 0

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_complete_supervision_stage(self, db):
        """Отметка стадии надзора как сданной."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)

        db.complete_supervision_stage(card_id)

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT dan_completed FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()

        assert row['dan_completed'] == 1

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_reset_supervision_stage_completion(self, db):
        """Сброс отметки о сдаче надзора."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)

        db.complete_supervision_stage(card_id)
        db.reset_supervision_stage_completion(card_id)

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT dan_completed FROM supervision_cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        db.close()

        assert row['dan_completed'] == 0


class TestSupervisionHistory:
    """История проекта надзора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_add_supervision_history(self, db):
        """Добавление записи в историю проекта надзора."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)
        emp_id = _create_employee(db, 'Менеджер', '__TEST__Менеджер hist', '__test_mgr_hist')

        db.add_supervision_history(card_id, 'note', 'Визит на объект', emp_id)

        history = db.get_supervision_history(card_id)
        assert len(history) >= 1
        assert history[0]['entry_type'] == 'note'
        assert history[0]['message'] == 'Визит на объект'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_supervision_history_with_employee_name(self, db):
        """История содержит имя сотрудника через JOIN."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)
        emp_id = _create_employee(db, 'ДАН', '__TEST__ДАН histname', '__test_dan_histn')

        db.add_supervision_history(card_id, 'stage_complete', 'Этап завершён', emp_id)

        history = db.get_supervision_history(card_id)
        assert 'created_by_name' in history[0]
        assert history[0]['created_by_name'] == '__TEST__ДАН histname'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_supervision_history_empty(self, db):
        """Пустая история."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)

        history = db.get_supervision_history(card_id)
        assert history == []

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_pause_creates_history_entry(self, db):
        """Приостановка создаёт запись в истории."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)
        emp_id = _create_employee(db, 'Менеджер', '__TEST__Менеджер pausehist', '__test_mgr_ph')

        db.pause_supervision_card(card_id, 'Ожидание материалов', emp_id)

        history = db.get_supervision_history(card_id)
        assert len(history) >= 1
        pause_entries = [h for h in history if h['entry_type'] == 'pause']
        assert len(pause_entries) == 1
        assert 'Ожидание материалов' in pause_entries[0]['message']

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_resume_creates_history_entry(self, db):
        """Возобновление создаёт запись в истории."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)
        emp_id = _create_employee(db, 'Менеджер', '__TEST__Менеджер resumehist', '__test_mgr_rh')

        db.pause_supervision_card(card_id, 'Причина', emp_id)
        db.resume_supervision_card(card_id, emp_id)

        history = db.get_supervision_history(card_id)
        resume_entries = [h for h in history if h['entry_type'] == 'resume']
        assert len(resume_entries) == 1


class TestDeleteSupervisionOrder:
    """Удаление заказа надзора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_delete_supervision_order(self, db):
        """Полное удаление заказа надзора + зависимостей."""
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id, status='АВТОРСКИЙ НАДЗОР')
        card_id = db.create_supervision_card(contract_id)
        emp_id = _create_employee(db, 'Менеджер', '__TEST__Менеджер delsupv', '__test_mgr_delsupv')

        # Добавляем историю
        db.add_supervision_history(card_id, 'note', 'Тест', emp_id)

        # Удаляем
        db.delete_supervision_order(contract_id, card_id)

        # Проверяем — договор удалён
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM contracts WHERE id = ?', (contract_id,))
        assert cursor.fetchone() is None

        # Карточка удалена
        cursor.execute('SELECT id FROM supervision_cards WHERE id = ?', (card_id,))
        assert cursor.fetchone() is None
        db.close()
