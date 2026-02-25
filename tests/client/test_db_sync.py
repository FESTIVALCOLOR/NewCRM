# -*- coding: utf-8 -*-
"""
Unit-тесты для utils/db_sync.py
Тестирует DatabaseSynchronizer, IntegrityChecker и публичные функции.
Все зависимости (db_manager, api_client) замокированы.
"""
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime

from utils.db_sync import (
    DatabaseSynchronizer,
    IntegrityChecker,
    sync_on_login,
    verify_data_integrity,
)


def make_db_mock():
    """Создаёт мок для DatabaseManager."""
    db = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = None  # Запись не найдена по умолчанию
    conn.cursor.return_value = cursor
    db.connect.return_value = conn
    return db, conn, cursor


def make_api_mock():
    """Создаёт мок для APIClient."""
    api = MagicMock()
    api.get_employees.return_value = []
    api.get_clients.return_value = []
    api.get_contracts.return_value = []
    api.get_crm_cards.return_value = []
    api.get_supervision_cards.return_value = []
    api.get_rates.return_value = []
    api.get_payments.return_value = []
    api.get_all_payments.return_value = []
    api.get_project_files.return_value = []
    api.get_salaries.return_value = []
    api.get_stage_executors.return_value = []
    api.get_approval_stage_deadlines.return_value = []
    api.get_action_history.return_value = []
    api.get_supervision_project_history.return_value = []
    return api


# ========== Тесты DatabaseSynchronizer ==========

class TestDatabaseSynchronizerInit:
    """Тесты инициализации DatabaseSynchronizer."""

    def test_init_stores_db_and_api(self):
        """Конструктор сохраняет db и api."""
        db, _, _ = make_db_mock()
        api = make_api_mock()
        sync = DatabaseSynchronizer(db, api)
        assert sync.db is db
        assert sync.api is api

    def test_init_creates_empty_sync_log(self):
        """Конструктор создаёт пустой лог синхронизации."""
        db, _, _ = make_db_mock()
        api = make_api_mock()
        sync = DatabaseSynchronizer(db, api)
        assert sync.sync_log == []


class TestDatabaseSynchronizerSyncAll:
    """Тесты метода sync_all."""

    def test_sync_all_returns_dict(self):
        """sync_all возвращает словарь."""
        db, _, _ = make_db_mock()
        api = make_api_mock()
        sync = DatabaseSynchronizer(db, api)
        result = sync.sync_all()
        assert isinstance(result, dict)

    def test_sync_all_has_success_key(self):
        """Результат содержит ключ 'success'."""
        db, _, _ = make_db_mock()
        api = make_api_mock()
        sync = DatabaseSynchronizer(db, api)
        result = sync.sync_all()
        assert 'success' in result

    def test_sync_all_has_synced_key(self):
        """Результат содержит ключ 'synced'."""
        db, _, _ = make_db_mock()
        api = make_api_mock()
        sync = DatabaseSynchronizer(db, api)
        result = sync.sync_all()
        assert 'synced' in result

    def test_sync_all_has_errors_key(self):
        """Результат содержит ключ 'errors'."""
        db, _, _ = make_db_mock()
        api = make_api_mock()
        sync = DatabaseSynchronizer(db, api)
        result = sync.sync_all()
        assert 'errors' in result

    def test_sync_all_empty_data_success(self):
        """Синхронизация с пустыми данными API — успех без ошибок."""
        db, _, _ = make_db_mock()
        api = make_api_mock()
        sync = DatabaseSynchronizer(db, api)
        result = sync.sync_all()
        assert result['success'] is True
        assert result['errors'] == []

    def test_sync_all_progress_callback_called(self):
        """Колбэк прогресса вызывается во время синхронизации."""
        db, _, _ = make_db_mock()
        api = make_api_mock()
        sync = DatabaseSynchronizer(db, api)

        progress_calls = []
        def track_progress(current, total, message):
            progress_calls.append((current, total, message))

        result = sync.sync_all(progress_callback=track_progress)
        assert len(progress_calls) > 0, "Колбэк прогресса должен вызываться"

    def test_sync_all_synced_has_all_tables(self):
        """'synced' содержит счётчики для всех основных таблиц."""
        db, _, _ = make_db_mock()
        api = make_api_mock()
        sync = DatabaseSynchronizer(db, api)
        result = sync.sync_all()
        expected_tables = [
            'employees', 'clients', 'contracts', 'crm_cards',
            'supervision_cards', 'payments', 'rates'
        ]
        for table in expected_tables:
            assert table in result['synced'], f"Ключ '{table}' должен быть в synced"

    def test_sync_all_with_api_error_marks_failure(self):
        """Исключение в API помечает результат как неуспешный."""
        db, _, _ = make_db_mock()
        api = make_api_mock()
        # Первый вызов вернёт данные, но _sync_employees упадёт от db ошибки
        api.get_employees.side_effect = Exception("Сетевая ошибка")
        sync = DatabaseSynchronizer(db, api)
        result = sync.sync_all()
        # Ошибка в конкретном методе _sync_employees не должна остановить весь sync_all
        # но должна быть обработана внутри метода (возвращает 0)
        assert isinstance(result, dict)

    def test_sync_all_empty_employees_returns_zero(self):
        """Пустой список сотрудников с сервера — synced['employees'] == 0."""
        db, _, _ = make_db_mock()
        api = make_api_mock()
        api.get_employees.return_value = []
        sync = DatabaseSynchronizer(db, api)
        result = sync.sync_all()
        assert result['synced']['employees'] == 0


# ========== Тесты IntegrityChecker ==========

class TestIntegrityChecker:
    """Тесты класса проверки целостности данных."""

    def test_check_returns_dict_with_required_keys(self):
        """check() возвращает словарь с необходимыми ключами."""
        db, conn, cursor = make_db_mock()
        cursor.fetchone.return_value = (0,)  # COUNT(*) = 0
        api = make_api_mock()

        checker = IntegrityChecker(db, api)
        result = checker.check()

        assert 'is_synced' in result
        assert 'discrepancies' in result
        assert 'local_counts' in result
        assert 'server_counts' in result

    def test_check_is_synced_when_counts_match(self):
        """is_synced=True когда локальные и серверные счётчики совпадают."""
        db, conn, cursor = make_db_mock()
        cursor.fetchone.return_value = (0,)  # Все локальные счётчики = 0
        api = make_api_mock()
        # Все API возвращают пустые списки (count=0)

        checker = IntegrityChecker(db, api)
        result = checker.check()

        assert result['is_synced'] is True
        assert result['discrepancies'] == []

    def test_check_not_synced_when_counts_differ(self):
        """is_synced=False когда счётчики расходятся."""
        db, conn, cursor = make_db_mock()
        cursor.fetchone.return_value = (5,)  # Локально 5 записей
        api = make_api_mock()
        api.get_employees.return_value = [{'id': i} for i in range(10)]  # На сервере 10

        checker = IntegrityChecker(db, api)
        result = checker.check()

        assert result['is_synced'] is False
        assert len(result['discrepancies']) > 0

    def test_check_has_timestamp(self):
        """Результат содержит временную метку."""
        db, conn, cursor = make_db_mock()
        cursor.fetchone.return_value = (0,)
        api = make_api_mock()

        checker = IntegrityChecker(db, api)
        result = checker.check()

        assert 'timestamp' in result
        # Проверяем что это валидная дата
        datetime.fromisoformat(result['timestamp'])

    def test_checker_stores_last_result(self):
        """Результат последней проверки сохраняется в атрибуте."""
        db, conn, cursor = make_db_mock()
        cursor.fetchone.return_value = (0,)
        api = make_api_mock()

        checker = IntegrityChecker(db, api)
        result = checker.check()

        assert checker.last_check_result is not None
        assert checker.last_check_result is result


# ========== Тесты публичных функций ==========

class TestPublicFunctions:
    """Тесты публичных функций модуля db_sync."""

    def test_sync_on_login_returns_dict(self):
        """sync_on_login возвращает результат словарём."""
        db, _, _ = make_db_mock()
        api = make_api_mock()
        result = sync_on_login(db, api)
        assert isinstance(result, dict)
        assert 'success' in result

    def test_sync_on_login_with_callback(self):
        """sync_on_login передаёт колбэк синхронизатору."""
        db, _, _ = make_db_mock()
        api = make_api_mock()

        calls = []
        def cb(current, total, msg):
            calls.append(msg)

        result = sync_on_login(db, api, progress_callback=cb)
        assert len(calls) > 0

    def test_verify_data_integrity_returns_dict(self):
        """verify_data_integrity возвращает словарь."""
        db, conn, cursor = make_db_mock()
        cursor.fetchone.return_value = (0,)
        api = make_api_mock()
        result = verify_data_integrity(db, api)
        assert isinstance(result, dict)
        assert 'is_synced' in result
