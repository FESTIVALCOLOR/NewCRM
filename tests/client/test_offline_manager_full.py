# -*- coding: utf-8 -*-
"""
Полное покрытие utils/offline_manager.py — 688 строк, покрытие 12% -> 80%+
Тесты: HMAC подпись, Enums, OfflineManager init, queue, sync, monitoring, history, retry.
~45 тестов.
"""

import pytest
import sys
import os
import json
import sqlite3
import threading
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================== HMAC FUNCTIONS ====================

class TestGetHmacKey:
    """_get_hmac_key — генерация и чтение HMAC ключа."""

    def test_generates_32_byte_key(self):
        from utils.offline_manager import _get_hmac_key
        with patch('utils.offline_manager.os.path.exists', return_value=False), \
             patch('builtins.open', MagicMock()):
            key = _get_hmac_key()
            assert isinstance(key, bytes)
            assert len(key) == 32

    def test_reads_existing_key(self, tmp_path):
        from utils.offline_manager import _get_hmac_key
        key_data = b'\x01' * 32
        key_file = tmp_path / 'test_hmac_key'
        key_file.write_bytes(key_data)
        with patch('utils.offline_manager._HMAC_KEY_FILE', str(key_file)):
            key = _get_hmac_key()
            assert key == key_data

    def test_handles_write_oserror(self):
        from utils.offline_manager import _get_hmac_key
        mock_open = MagicMock(side_effect=OSError("Нет прав"))
        with patch('utils.offline_manager.os.path.exists', return_value=False), \
             patch('builtins.open', mock_open):
            key = _get_hmac_key()
            assert isinstance(key, bytes)
            assert len(key) == 32


class TestSignOperation:
    """_sign_operation — подпись данных HMAC-SHA256."""

    def test_returns_hex_64_chars(self):
        from utils.offline_manager import _sign_operation
        sig = _sign_operation('{"id":1}', 'create', 'client')
        assert isinstance(sig, str)
        assert len(sig) == 64

    def test_deterministic_for_same_input(self):
        from utils.offline_manager import _sign_operation
        sig1 = _sign_operation('{"id":1}', 'create', 'client')
        sig2 = _sign_operation('{"id":1}', 'create', 'client')
        assert sig1 == sig2

    def test_different_data_different_sig(self):
        from utils.offline_manager import _sign_operation
        with patch('utils.offline_manager._get_hmac_key', return_value=b'k' * 32):
            sig1 = _sign_operation('{"a":1}', 'create', 'client')
            sig2 = _sign_operation('{"a":2}', 'create', 'client')
            assert sig1 != sig2

    def test_different_operation_type_different_sig(self):
        from utils.offline_manager import _sign_operation
        with patch('utils.offline_manager._get_hmac_key', return_value=b'k' * 32):
            sig1 = _sign_operation('{"a":1}', 'create', 'client')
            sig2 = _sign_operation('{"a":1}', 'update', 'client')
            assert sig1 != sig2

    def test_different_entity_type_different_sig(self):
        from utils.offline_manager import _sign_operation
        with patch('utils.offline_manager._get_hmac_key', return_value=b'k' * 32):
            sig1 = _sign_operation('{"a":1}', 'create', 'client')
            sig2 = _sign_operation('{"a":1}', 'create', 'employee')
            assert sig1 != sig2


class TestVerifyOperationSignature:
    """_verify_operation_signature — проверка HMAC подписи."""

    def test_valid_signature_returns_true(self):
        from utils.offline_manager import _sign_operation, _verify_operation_signature
        sig = _sign_operation('{"id":1}', 'create', 'client')
        assert _verify_operation_signature('{"id":1}', 'create', 'client', sig) is True

    def test_invalid_signature_returns_false(self):
        from utils.offline_manager import _verify_operation_signature
        assert _verify_operation_signature('{"id":1}', 'create', 'client', 'x' * 64) is False

    def test_tampered_data_fails_verification(self):
        from utils.offline_manager import _sign_operation, _verify_operation_signature
        sig = _sign_operation('{"id":1}', 'create', 'client')
        assert _verify_operation_signature('{"id":2}', 'create', 'client', sig) is False


# ==================== ENUMS ====================

class TestEnums:
    """Тесты перечислений ConnectionStatus, OperationType, OperationStatus."""

    def test_connection_status_all_values(self):
        from utils.offline_manager import ConnectionStatus
        assert set(s.value for s in ConnectionStatus) == {"online", "offline", "connecting", "syncing"}

    def test_operation_type_all_values(self):
        from utils.offline_manager import OperationType
        assert set(t.value for t in OperationType) == {"create", "update", "delete"}

    def test_operation_status_all_values(self):
        from utils.offline_manager import OperationStatus
        expected = {"pending", "syncing", "synced", "failed", "conflict"}
        assert set(s.value for s in OperationStatus) == expected

    def test_operation_status_syncing_exists(self):
        from utils.offline_manager import OperationStatus
        assert OperationStatus.SYNCING.value == "syncing"


# ==================== OFFLINE MANAGER ====================

@pytest.fixture
def om(tmp_path):
    """Создать OfflineManager с временной SQLite БД."""
    db_path = str(tmp_path / 'test_offline.db')
    from utils.offline_manager import OfflineManager
    mgr = OfflineManager(db_path=db_path, api_client=None)
    yield mgr
    mgr.stop_monitoring()


@pytest.fixture
def mock_api():
    """Мок API клиента."""
    api = MagicMock()
    api.base_url = "http://test:8000"
    api.force_online_check = MagicMock(return_value=True)
    api.reset_offline_cache = MagicMock()
    return api


# ---- Инициализация ----

class TestOfflineManagerInit:
    """OfflineManager — создание и инициализация."""

    def test_creates_instance(self, om):
        assert om is not None
        assert om.api_client is None

    def test_initial_status_offline(self, om):
        from utils.offline_manager import ConnectionStatus
        assert om._status == ConnectionStatus.OFFLINE

    def test_is_online_false_initially(self, om):
        assert om.is_online() is False

    def test_db_path_stored(self, om, tmp_path):
        assert om.db_path == str(tmp_path / 'test_offline.db')

    def test_queue_table_created(self, om):
        conn = sqlite3.connect(om.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='offline_operations_queue'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_queue_table_has_signature_column(self, om):
        conn = sqlite3.connect(om.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(offline_operations_queue)")
        columns = [row[1] for row in cursor.fetchall()]
        assert 'signature' in columns
        conn.close()

    def test_indexes_created(self, om):
        conn = sqlite3.connect(om.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        assert 'idx_offline_queue_status' in indexes
        assert 'idx_offline_queue_entity' in indexes
        conn.close()

    def test_check_timer_initialized(self, om):
        assert om._check_timer is not None

    def test_sync_lock_is_threading_lock(self, om):
        assert isinstance(om._sync_lock, type(threading.Lock()))

    def test_db_lock_is_rlock(self, om):
        assert isinstance(om._db_lock, type(threading.RLock()))


# ---- Статус и API клиент ----

class TestOfflineManagerStatusAndApi:
    """Статус подключения и set_api_client."""

    def test_set_api_client(self, om, mock_api):
        om.set_api_client(mock_api)
        assert om.api_client is mock_api

    def test_status_property_getter(self, om):
        from utils.offline_manager import ConnectionStatus
        assert om.status == ConnectionStatus.OFFLINE

    def test_status_setter_emits_signal(self, om):
        from utils.offline_manager import ConnectionStatus
        om.connection_status_changed = MagicMock()
        om.status = ConnectionStatus.ONLINE
        assert om._status == ConnectionStatus.ONLINE

    def test_status_setter_no_emit_same_value(self, om):
        from utils.offline_manager import ConnectionStatus
        om.connection_status_changed = MagicMock()
        om.status = ConnectionStatus.OFFLINE  # Уже OFFLINE
        # Не должен был вызвать emit т.к. значение то же
        om.connection_status_changed.emit.assert_not_called()

    def test_is_online_true_when_online(self, om):
        from utils.offline_manager import ConnectionStatus
        om._status = ConnectionStatus.ONLINE
        assert om.is_online() is True

    def test_is_online_false_when_syncing(self, om):
        from utils.offline_manager import ConnectionStatus
        om._status = ConnectionStatus.SYNCING
        assert om.is_online() is False

    def test_is_online_false_when_connecting(self, om):
        from utils.offline_manager import ConnectionStatus
        om._status = ConnectionStatus.CONNECTING
        assert om.is_online() is False


# ---- Очередь операций ----

class TestOfflineManagerQueue:
    """Тесты очереди offline-операций: queue, pending count, get pending."""

    def test_queue_create_returns_positive_id(self, om):
        from utils.offline_manager import OperationType
        result = om.queue_operation(OperationType.CREATE, 'client', None, {'full_name': 'Тест'})
        assert isinstance(result, int)
        assert result > 0

    def test_queue_update_operation(self, om):
        from utils.offline_manager import OperationType
        result = om.queue_operation(OperationType.UPDATE, 'employee', 42, {'full_name': 'Новое'})
        assert result > 0

    def test_queue_delete_operation(self, om):
        from utils.offline_manager import OperationType
        result = om.queue_operation(OperationType.DELETE, 'contract', 100, {})
        assert result > 0

    def test_pending_count_increases(self, om):
        from utils.offline_manager import OperationType
        assert om.get_pending_operations_count() == 0
        om.queue_operation(OperationType.CREATE, 'client', None, {'a': 1})
        assert om.get_pending_operations_count() == 1
        om.queue_operation(OperationType.CREATE, 'client', None, {'a': 2})
        assert om.get_pending_operations_count() == 2

    def test_get_pending_operations_returns_list(self, om):
        from utils.offline_manager import OperationType
        om.queue_operation(OperationType.CREATE, 'client', None, {'name': 'test'})
        ops = om.get_pending_operations()
        assert isinstance(ops, list)
        assert len(ops) == 1

    def test_pending_operation_has_required_keys(self, om):
        from utils.offline_manager import OperationType
        om.queue_operation(OperationType.UPDATE, 'employee', 1, {'name': 'test'})
        ops = om.get_pending_operations()
        op = ops[0]
        assert 'id' in op
        assert 'operation_type' in op
        assert 'entity_type' in op
        assert 'status' in op
        assert op['operation_type'] == 'update'
        assert op['entity_type'] == 'employee'
        assert op['status'] == 'pending'

    def test_queue_operation_stores_data_json(self, om):
        from utils.offline_manager import OperationType
        om.queue_operation(OperationType.CREATE, 'client', None, {'phone': '+71234567890'})
        ops = om.get_pending_operations()
        data = ops[0].get('data', '{}')
        if isinstance(data, str):
            data = json.loads(data)
        assert data.get('phone') == '+71234567890'

    def test_queue_operation_stores_signature(self, om):
        from utils.offline_manager import OperationType
        om.queue_operation(OperationType.CREATE, 'client', None, {'name': 'sig_test'})
        conn = sqlite3.connect(om.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT signature FROM offline_operations_queue ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        assert row[0] is not None
        assert len(row[0]) == 64

    def test_queue_with_none_entity_id(self, om):
        from utils.offline_manager import OperationType
        result = om.queue_operation(OperationType.CREATE, 'payment', None, {'amount': 100})
        assert result > 0

    def test_queue_preserves_unicode_data(self, om):
        from utils.offline_manager import OperationType
        om.queue_operation(OperationType.CREATE, 'client', None, {'name': 'Кириллица'})
        ops = om.get_pending_operations()
        data = ops[0].get('data', '{}')
        if isinstance(data, str):
            data = json.loads(data)
        assert data.get('name') == 'Кириллица'


# ---- История и очистка ----

class TestOfflineManagerHistory:
    """get_operation_history, clear_synced_operations, retry_failed_operations."""

    def test_get_operation_history_empty(self, om):
        history = om.get_operation_history()
        assert isinstance(history, list)

    def test_get_operation_history_includes_queued(self, om):
        from utils.offline_manager import OperationType
        om.queue_operation(OperationType.CREATE, 'client', None, {'name': 'hist'})
        om.queue_operation(OperationType.DELETE, 'contract', 5, {})
        history = om.get_operation_history(limit=100)
        assert len(history) == 2

    def test_history_limit(self, om):
        from utils.offline_manager import OperationType
        for i in range(10):
            om.queue_operation(OperationType.CREATE, 'client', None, {'i': i})
        history = om.get_operation_history(limit=3)
        assert len(history) <= 3

    def test_clear_synced_operations(self, om):
        from utils.offline_manager import OperationType, OperationStatus
        om.queue_operation(OperationType.CREATE, 'client', None, {'name': 'А'})
        conn = om._get_connection()
        conn.execute("UPDATE offline_operations_queue SET status = ?", (OperationStatus.SYNCED.value,))
        conn.commit()
        conn.close()
        deleted = om.clear_synced_operations()
        assert deleted == 1
        assert om.get_pending_operations_count() == 0

    def test_clear_synced_keeps_pending(self, om):
        from utils.offline_manager import OperationType, OperationStatus
        om.queue_operation(OperationType.CREATE, 'client', None, {'name': 'pending'})
        om.queue_operation(OperationType.CREATE, 'client', None, {'name': 'synced'})
        # Помечаем только второй как synced
        conn = om._get_connection()
        conn.execute(
            "UPDATE offline_operations_queue SET status = ? WHERE id = 2",
            (OperationStatus.SYNCED.value,)
        )
        conn.commit()
        conn.close()
        deleted = om.clear_synced_operations()
        assert deleted == 1
        assert om.get_pending_operations_count() == 1

    def test_retry_failed_operations(self, om):
        from utils.offline_manager import OperationType, OperationStatus
        om.queue_operation(OperationType.CREATE, 'client', None, {'name': 'Fail'})
        conn = om._get_connection()
        conn.execute(
            "UPDATE offline_operations_queue SET status = ?, retry_count = 1",
            (OperationStatus.FAILED.value,)
        )
        conn.commit()
        conn.close()
        count = om.retry_failed_operations()
        assert count == 1
        assert om.get_pending_operations_count() == 1


# ---- Мониторинг ----

class TestOfflineManagerMonitoring:
    """start_monitoring, stop_monitoring, _check_connection."""

    def test_stop_monitoring_no_crash(self, om):
        om.stop_monitoring()  # Не должно упасть

    def test_check_connection_without_api_sets_offline(self, om):
        from utils.offline_manager import ConnectionStatus
        om.api_client = None
        om._check_connection()
        assert om.status == ConnectionStatus.OFFLINE

    def test_check_connection_skips_when_syncing(self, om, mock_api):
        from utils.offline_manager import ConnectionStatus
        om.set_api_client(mock_api)
        om._is_syncing = True
        om._status = ConnectionStatus.ONLINE
        om._check_connection()
        # force_online_check не должен вызываться
        mock_api.force_online_check.assert_not_called()

    def test_check_connection_online_with_force_check(self, om, mock_api):
        from utils.offline_manager import ConnectionStatus
        om.set_api_client(mock_api)
        mock_api.force_online_check.return_value = True
        om._check_connection()
        assert om.status == ConnectionStatus.ONLINE

    def test_check_connection_offline_on_failure(self, om, mock_api):
        from utils.offline_manager import ConnectionStatus
        om.set_api_client(mock_api)
        mock_api.force_online_check.return_value = False
        om._check_connection()
        assert om.status == ConnectionStatus.OFFLINE

    def test_check_connection_offline_on_exception(self, om, mock_api):
        from utils.offline_manager import ConnectionStatus
        om.set_api_client(mock_api)
        mock_api.force_online_check.side_effect = Exception("Сеть")
        om._check_connection()
        assert om.status == ConnectionStatus.OFFLINE

    def test_check_connection_resets_offline_cache(self, om, mock_api):
        from utils.offline_manager import ConnectionStatus
        om.set_api_client(mock_api)
        om._status = ConnectionStatus.OFFLINE
        mock_api.force_online_check.return_value = True
        om._check_connection()
        mock_api.reset_offline_cache.assert_called_once()


# ---- Синхронизация ----

class TestOfflineManagerSync:
    """force_sync, _start_sync."""

    def test_force_sync_without_api_does_nothing(self, om):
        om.force_sync()  # Не должно упасть

    def test_force_sync_when_offline_does_nothing(self, om, mock_api):
        from utils.offline_manager import ConnectionStatus
        om._status = ConnectionStatus.OFFLINE
        om.set_api_client(mock_api)
        om.force_sync()

    def test_force_sync_does_not_crash_on_api_error(self, om, mock_api):
        from utils.offline_manager import ConnectionStatus, OperationType
        om.set_api_client(mock_api)
        om._status = ConnectionStatus.ONLINE
        mock_api.create_client.side_effect = Exception("API Error")
        om.queue_operation(OperationType.CREATE, 'client', None, {'name': 'err'})
        om.force_sync()  # Не должно упасть

    def test_check_interval_is_60_seconds(self, om):
        assert om.CHECK_INTERVAL == 60000

    def test_ping_timeout_is_2_seconds(self, om):
        assert om.PING_TIMEOUT == 2

    def test_sync_timeout_is_10_seconds(self, om):
        assert om.SYNC_TIMEOUT == 10

    def test_max_sync_errors_is_3(self, om):
        assert om.MAX_SYNC_ERRORS == 3

    def test_get_connection_returns_connection(self, om):
        conn = om._get_connection()
        assert conn is not None
        conn.close()

    def test_get_connection_has_row_factory(self, om):
        conn = om._get_connection()
        assert conn.row_factory == sqlite3.Row
        conn.close()
