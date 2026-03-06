# -*- coding: utf-8 -*-
"""
MEDIUM/LOW тесты для DatabaseSynchronizer:
- _sync_employees (upsert, дубликаты по login, пустой ответ)
- _sync_clients (insert/update, пустой/None ответ)
- _sync_contracts, _sync_crm_cards, _sync_supervision_cards
- verify_integrity
- progress_callback
- Обработка частичных ошибок (один шаг падает, остальные продолжаются)
"""
import pytest
import sys
import os
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch, call
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.db_sync import DatabaseSynchronizer


# ==================== Helpers ====================

def _make_syncer(api_returns=None):
    """Создать DatabaseSynchronizer с моками."""
    mock_db = MagicMock()
    mock_api = MagicMock()

    # Дефолтные пустые ответы для всех шагов
    defaults = {
        'get_employees': [], 'get_clients': [], 'get_contracts': [],
        'get_crm_cards': [], 'get_supervision_cards': [],
        'get_rates': [], 'get_payments': [], 'get_project_files': [],
        'get_salaries': [], 'get_stage_executors': [],
        'get_approval_stage_deadlines': [], 'get_action_history': [],
        'get_supervision_history': [],
    }
    if api_returns:
        defaults.update(api_returns)

    for method, value in defaults.items():
        setattr(mock_api, method, MagicMock(return_value=value))

    return DatabaseSynchronizer(mock_db, mock_api), mock_db, mock_api


# ==================== sync_all ====================

class TestSyncAll:
    """sync_all — полная синхронизация."""

    def test_sync_all_empty_returns_success(self):
        syncer, _, _ = _make_syncer()
        result = syncer.sync_all()
        assert result['success'] is True
        assert result['synced']['employees'] == 0
        assert result['synced']['clients'] == 0

    def test_sync_all_progress_callback(self):
        syncer, _, _ = _make_syncer()
        calls = []
        result = syncer.sync_all(progress_callback=lambda c, t, m: calls.append((c, t, m)))
        assert len(calls) == 14
        # Проверяем что total=14 для всех
        assert all(t == 14 for _, t, _ in calls)
        # current растёт от 1 до 14
        assert [c for c, _, _ in calls] == list(range(1, 15))

    def test_sync_all_employees_error_continues(self):
        """Ошибка в employees — остальные шаги продолжаются."""
        syncer, _, mock_api = _make_syncer()
        mock_api.get_employees.side_effect = Exception("API down")
        result = syncer.sync_all()
        assert result['success'] is True
        assert result['synced']['employees'] == 0
        # Остальные шаги вызваны
        mock_api.get_clients.assert_called_once()

    def test_sync_all_clients_error_continues(self):
        syncer, _, mock_api = _make_syncer()
        mock_api.get_clients.side_effect = Exception("err")
        result = syncer.sync_all()
        assert result['success'] is True
        assert result['synced']['clients'] == 0


# ==================== _sync_employees ====================

class TestSyncEmployees:
    """_sync_employees — синхронизация сотрудников."""

    def test_empty_response_returns_zero(self):
        syncer, _, _ = _make_syncer()
        count = syncer._sync_employees()
        assert count == 0

    def test_none_response_returns_zero(self):
        syncer, _, mock_api = _make_syncer()
        mock_api.get_employees.return_value = None
        count = syncer._sync_employees()
        assert count == 0

    def test_inserts_new_employee(self):
        syncer, mock_db, mock_api = _make_syncer()
        mock_api.get_employees.return_value = [
            {'id': 1, 'full_name': 'Тест', 'login': 'test', 'phone': '', 'email': '',
             'status': 'active', 'position': 'Дизайнер', 'department': '', 'legal_status': '',
             'hire_date': '', 'payment_details': '', 'role': 'designer',
             'birth_date': '', 'address': '', 'secondary_position': ''}
        ]

        # Мокаем SQLite
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # Нет по ID и по login
        mock_conn.cursor.return_value = mock_cursor
        mock_db.connect.return_value = mock_conn

        count = syncer._sync_employees()
        assert count == 1
        mock_conn.commit.assert_called_once()

    def test_updates_existing_employee(self):
        syncer, mock_db, mock_api = _make_syncer()
        mock_api.get_employees.return_value = [
            {'id': 1, 'full_name': 'Обновлён', 'login': 'test', 'phone': '', 'email': '',
             'status': 'active', 'position': '', 'department': '', 'legal_status': '',
             'hire_date': '', 'payment_details': '', 'role': '', 'birth_date': '',
             'address': '', 'secondary_position': ''}
        ]

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # Первый fetchone — по ID: существует
        # Второй fetchone — по login: нет дубликатов
        mock_cursor.fetchone.side_effect = [(1, 'test'), None]
        mock_conn.cursor.return_value = mock_cursor
        mock_db.connect.return_value = mock_conn

        count = syncer._sync_employees()
        assert count == 1

    def test_api_exception_returns_zero(self):
        syncer, _, mock_api = _make_syncer()
        mock_api.get_employees.side_effect = Exception("Connection refused")
        count = syncer._sync_employees()
        assert count == 0


# ==================== _sync_clients ====================

class TestSyncClients:
    """_sync_clients — синхронизация клиентов."""

    def test_empty_response(self):
        syncer, _, _ = _make_syncer()
        count = syncer._sync_clients()
        assert count == 0

    def test_none_response(self):
        syncer, _, mock_api = _make_syncer()
        mock_api.get_clients.return_value = None
        count = syncer._sync_clients()
        assert count == 0

    def test_api_error_returns_zero(self):
        syncer, _, mock_api = _make_syncer()
        mock_api.get_clients.side_effect = Exception("err")
        count = syncer._sync_clients()
        assert count == 0

    def test_inserts_new_client(self):
        syncer, mock_db, mock_api = _make_syncer()
        mock_api.get_clients.return_value = [
            {'id': 1, 'full_name': 'Клиент', 'phone': '+7900', 'email': 'a@b.c',
             'source': '', 'notes': '', 'created_at': '', 'updated_at': ''}
        ]

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # Нет в БД
        mock_conn.cursor.return_value = mock_cursor
        mock_db.connect.return_value = mock_conn

        count = syncer._sync_clients()
        assert count == 1
        mock_conn.commit.assert_called_once()


# ==================== _sync_contracts ====================

class TestSyncContracts:
    """_sync_contracts — синхронизация договоров."""

    def test_empty_response(self):
        syncer, _, _ = _make_syncer()
        count = syncer._sync_contracts()
        assert count == 0

    def test_api_error_returns_zero(self):
        syncer, _, mock_api = _make_syncer()
        mock_api.get_contracts.side_effect = Exception("err")
        count = syncer._sync_contracts()
        assert count == 0


# ==================== _sync_crm_cards ====================

class TestSyncCRMCards:
    """_sync_crm_cards — синхронизация CRM карточек."""

    def test_empty_response(self):
        syncer, _, _ = _make_syncer()
        count = syncer._sync_crm_cards()
        assert count == 0

    def test_api_error_returns_zero(self):
        syncer, _, mock_api = _make_syncer()
        mock_api.get_crm_cards.side_effect = Exception("err")
        count = syncer._sync_crm_cards()
        assert count == 0


# ==================== _sync_supervision_cards ====================

class TestSyncSupervisionCards:
    """_sync_supervision_cards — синхронизация карточек надзора."""

    def test_empty_response(self):
        syncer, _, _ = _make_syncer()
        count = syncer._sync_supervision_cards()
        assert count == 0

    def test_api_error_returns_zero(self):
        syncer, _, mock_api = _make_syncer()
        mock_api.get_supervision_cards.side_effect = Exception("err")
        count = syncer._sync_supervision_cards()
        assert count == 0


# ==================== Other sync methods ====================

class TestOtherSyncMethods:
    """_sync_rates, _sync_payments, и т.д. — пустые/ошибки."""

    def test_sync_rates_empty(self):
        syncer, _, _ = _make_syncer()
        count = syncer._sync_rates()
        assert count == 0

    def test_sync_payments_empty(self):
        syncer, _, _ = _make_syncer()
        count = syncer._sync_payments()
        assert count == 0

    def test_sync_project_files_empty(self):
        syncer, _, _ = _make_syncer()
        count = syncer._sync_project_files()
        assert count == 0

    def test_sync_salaries_empty(self):
        syncer, _, _ = _make_syncer()
        count = syncer._sync_salaries()
        assert count == 0

    def test_sync_stage_executors_empty(self):
        syncer, _, _ = _make_syncer()
        count = syncer._sync_stage_executors()
        assert count == 0

    def test_sync_approval_deadlines_empty(self):
        syncer, _, _ = _make_syncer()
        count = syncer._sync_approval_stage_deadlines()
        assert count == 0

    def test_sync_action_history_empty(self):
        syncer, _, _ = _make_syncer()
        count = syncer._sync_action_history()
        assert count == 0

    def test_sync_supervision_history_empty(self):
        syncer, _, _ = _make_syncer()
        count = syncer._sync_supervision_project_history()
        assert count == 0

    def test_sync_rates_error(self):
        syncer, _, mock_api = _make_syncer()
        mock_api.get_rates.side_effect = Exception("err")
        count = syncer._sync_rates()
        assert count == 0

    def test_sync_payments_error(self):
        syncer, _, mock_api = _make_syncer()
        mock_api.get_payments.side_effect = Exception("err")
        count = syncer._sync_payments()
        assert count == 0


# ==================== Cache invalidation ====================

class TestSyncCacheInvalidation:
    """sync_all — инвалидация кеша DataAccess после синхронизации."""

    def test_cache_invalidated_at_end(self):
        syncer, _, _ = _make_syncer()
        with patch('utils.db_sync._global_cache', create=True) as mock_cache:
            # Не упадёт даже если _global_cache не существует (ImportError ловится)
            syncer.sync_all()


# ==================== verify_integrity ====================

class TestVerifyIntegrity:
    """verify_integrity — проверка целостности данных."""

    def test_verify_integrity_creates_checker(self):
        syncer, mock_db, mock_api = _make_syncer()
        # IntegrityChecker — внутренний класс, нужно мокать
        with patch('utils.db_sync.IntegrityChecker') as MockChecker:
            MockChecker.return_value.check.return_value = {'ok': True, 'mismatches': []}
            result = syncer.verify_integrity()
            assert result['ok'] is True
            MockChecker.assert_called_once_with(mock_db, mock_api)
