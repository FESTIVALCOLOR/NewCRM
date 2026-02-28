# -*- coding: utf-8 -*-
"""
DB Tests: Операции с временными лентами (Timeline) DatabaseManager
Проверяет init_project_timeline, get_project_timeline, update_timeline_entry,
init_supervision_timeline, get_supervision_timeline, update_supervision_timeline_entry.
"""

import pytest
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ============================================================
# Вспомогательные функции для создания тестовых данных
# ============================================================

def _create_client(db):
    """Создание тестового клиента."""
    return db.add_client({
        'client_type': 'Физическое лицо',
        'full_name': '__TEST__Timeline Клиент',
        'phone': '+79991234567',
    })


@patch('database.db_manager.YANDEX_DISK_TOKEN', '')
def _create_contract(db, client_id):
    """Создание тестового договора."""
    import random
    return db.add_contract({
        'client_id': client_id,
        'project_type': 'Индивидуальный',
        'agent_type': 'ФЕСТИВАЛЬ',
        'city': 'СПБ',
        'contract_number': f'__TEST__TL_{random.randint(10000, 99999)}',
        'address': 'Тестовый адрес timeline',
        'area': 75.0,
        'total_amount': 300000,
        'status': 'Новый заказ',
        'contract_period': 90,
        'contract_date': '2026-01-15',
    })


def _ensure_timeline_tables(db):
    """Создание таблиц timeline, если они не были созданы в conftest."""
    try:
        db.create_timeline_tables()
    except Exception:
        pass


# ============================================================
# Тесты timeline проекта
# ============================================================

class TestProjectTimeline:
    """Таблица сроков проекта."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_init_project_timeline(self, db):
        """Инициализация таблицы сроков проекта."""
        _ensure_timeline_tables(db)
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)

        entries = [
            {
                'stage_code': 'SURVEY',
                'stage_name': 'Замер',
                'stage_group': 'Подготовка',
                'executor_role': 'Замерщик',
                'sort_order': 1,
                'raw_norm_days': 3,
                'cumulative_days': 3,
                'norm_days': 3,
            },
            {
                'stage_code': 'CONCEPT',
                'stage_name': 'Дизайн-концепция',
                'stage_group': 'Проектирование',
                'executor_role': 'Дизайнер',
                'sort_order': 2,
                'raw_norm_days': 14,
                'cumulative_days': 17,
                'norm_days': 14,
            },
        ]

        result = db.init_project_timeline(contract_id, entries)
        assert result is True

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_project_timeline(self, db):
        """Получение таблицы сроков проекта."""
        _ensure_timeline_tables(db)
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)

        entries = [
            {
                'stage_code': 'SURVEY',
                'stage_name': 'Замер',
                'stage_group': 'Подготовка',
                'executor_role': 'Замерщик',
                'sort_order': 1,
                'raw_norm_days': 3,
                'cumulative_days': 3,
                'norm_days': 3,
            },
            {
                'stage_code': 'CONCEPT',
                'stage_name': 'Дизайн-концепция',
                'stage_group': 'Проектирование',
                'executor_role': 'Дизайнер',
                'sort_order': 2,
                'raw_norm_days': 14,
                'cumulative_days': 17,
                'norm_days': 14,
            },
        ]

        db.init_project_timeline(contract_id, entries)
        timeline = db.get_project_timeline(contract_id)

        assert isinstance(timeline, list)
        assert len(timeline) == 2
        # Порядок сортировки
        assert timeline[0]['stage_code'] == 'SURVEY'
        assert timeline[1]['stage_code'] == 'CONCEPT'
        assert timeline[0]['sort_order'] < timeline[1]['sort_order']

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_project_timeline_empty(self, db):
        """Пустая таблица сроков."""
        _ensure_timeline_tables(db)
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)

        timeline = db.get_project_timeline(contract_id)
        assert timeline == []

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_timeline_entry(self, db):
        """Обновление записи таблицы сроков."""
        _ensure_timeline_tables(db)
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)

        entries = [{
            'stage_code': 'SURVEY',
            'stage_name': 'Замер',
            'stage_group': 'Подготовка',
            'executor_role': 'Замерщик',
            'sort_order': 1,
            'raw_norm_days': 3,
            'cumulative_days': 3,
            'norm_days': 3,
        }]

        db.init_project_timeline(contract_id, entries)
        result = db.update_timeline_entry(contract_id, 'SURVEY', {
            'actual_date': '2026-02-01',
            'actual_days': 2,
            'status': 'Завершено',
        })

        assert result is True

        timeline = db.get_project_timeline(contract_id)
        assert timeline[0]['actual_date'] == '2026-02-01'
        assert timeline[0]['actual_days'] == 2
        assert timeline[0]['status'] == 'Завершено'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_init_project_timeline_idempotent(self, db):
        """Повторная инициализация не дублирует записи (INSERT OR IGNORE)."""
        _ensure_timeline_tables(db)
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)

        entries = [{
            'stage_code': 'SURVEY',
            'stage_name': 'Замер',
            'stage_group': 'Подготовка',
            'executor_role': 'Замерщик',
            'sort_order': 1,
            'raw_norm_days': 3,
            'cumulative_days': 3,
            'norm_days': 3,
        }]

        db.init_project_timeline(contract_id, entries)
        db.init_project_timeline(contract_id, entries)

        timeline = db.get_project_timeline(contract_id)
        assert len(timeline) == 1  # Не дублируется


# ============================================================
# Тесты timeline надзора
# ============================================================

class TestSupervisionTimeline:
    """Таблица сроков надзора."""

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_init_supervision_timeline(self, db):
        """Инициализация таблицы сроков надзора."""
        _ensure_timeline_tables(db)
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        sv_card_id = db.create_supervision_card(contract_id)

        entries = [
            {
                'stage_code': 'FOUNDATION',
                'stage_name': 'Фундамент',
                'sort_order': 1,
                'status': 'Не начато',
                'executor': '',
            },
            {
                'stage_code': 'WALLS',
                'stage_name': 'Стены',
                'sort_order': 2,
                'status': 'Не начато',
                'executor': '',
            },
        ]

        result = db.init_supervision_timeline(sv_card_id, entries)
        assert result is True

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_supervision_timeline(self, db):
        """Получение таблицы сроков надзора."""
        _ensure_timeline_tables(db)
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        sv_card_id = db.create_supervision_card(contract_id)

        entries = [
            {
                'stage_code': 'FOUNDATION',
                'stage_name': 'Фундамент',
                'sort_order': 1,
            },
            {
                'stage_code': 'WALLS',
                'stage_name': 'Стены',
                'sort_order': 2,
            },
        ]

        db.init_supervision_timeline(sv_card_id, entries)
        timeline = db.get_supervision_timeline(sv_card_id)

        assert isinstance(timeline, list)
        assert len(timeline) == 2
        assert timeline[0]['stage_code'] == 'FOUNDATION'
        assert timeline[1]['stage_code'] == 'WALLS'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_get_supervision_timeline_empty(self, db):
        """Пустая таблица сроков надзора."""
        _ensure_timeline_tables(db)
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        sv_card_id = db.create_supervision_card(contract_id)

        timeline = db.get_supervision_timeline(sv_card_id)
        assert timeline == []

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_update_supervision_timeline_entry(self, db):
        """Обновление записи таблицы сроков надзора."""
        _ensure_timeline_tables(db)
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        sv_card_id = db.create_supervision_card(contract_id)

        entries = [{
            'stage_code': 'FOUNDATION',
            'stage_name': 'Фундамент',
            'sort_order': 1,
        }]

        db.init_supervision_timeline(sv_card_id, entries)
        result = db.update_supervision_timeline_entry(sv_card_id, 'FOUNDATION', {
            'status': 'В работе',
            'executor': 'Подрядчик А',
            'actual_date': '2026-03-01',
        })

        assert result is True

        timeline = db.get_supervision_timeline(sv_card_id)
        assert timeline[0]['status'] == 'В работе'
        assert timeline[0]['executor'] == 'Подрядчик А'
        assert timeline[0]['actual_date'] == '2026-03-01'

    @patch('database.db_manager.YANDEX_DISK_TOKEN', '')
    def test_init_supervision_timeline_idempotent(self, db):
        """Повторная инициализация не дублирует записи."""
        _ensure_timeline_tables(db)
        client_id = _create_client(db)
        contract_id = _create_contract(db, client_id)
        sv_card_id = db.create_supervision_card(contract_id)

        entries = [{
            'stage_code': 'FOUNDATION',
            'stage_name': 'Фундамент',
            'sort_order': 1,
        }]

        db.init_supervision_timeline(sv_card_id, entries)
        db.init_supervision_timeline(sv_card_id, entries)

        timeline = db.get_supervision_timeline(sv_card_id)
        assert len(timeline) == 1
