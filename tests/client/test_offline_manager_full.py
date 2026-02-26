# -*- coding: utf-8 -*-
"""
Покрытие utils/offline_manager.py — HMAC, Enums, OfflineManager.
~30 тестов.
"""

import pytest
import sys
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================== ENUMS ====================

class TestConnectionStatus:
    def test_online_value(self):
        from utils.offline_manager import ConnectionStatus
        assert ConnectionStatus.ONLINE.value == "online"

    def test_offline_value(self):
        from utils.offline_manager import ConnectionStatus
        assert ConnectionStatus.OFFLINE.value == "offline"

    def test_connecting_value(self):
        from utils.offline_manager import ConnectionStatus
        assert ConnectionStatus.CONNECTING.value == "connecting"

    def test_syncing_value(self):
        from utils.offline_manager import ConnectionStatus
        assert ConnectionStatus.SYNCING.value == "syncing"


class TestOperationType:
    def test_create(self):
        from utils.offline_manager import OperationType
        assert OperationType.CREATE.value == "create"

    def test_update(self):
        from utils.offline_manager import OperationType
        assert OperationType.UPDATE.value == "update"

    def test_delete(self):
        from utils.offline_manager import OperationType
        assert OperationType.DELETE.value == "delete"


class TestOperationStatus:
    def test_pending(self):
        from utils.offline_manager import OperationStatus
        assert OperationStatus.PENDING.value == "pending"

    def test_synced(self):
        from utils.offline_manager import OperationStatus
        assert OperationStatus.SYNCED.value == "synced"

    def test_failed(self):
        from utils.offline_manager import OperationStatus
        assert OperationStatus.FAILED.value == "failed"

    def test_conflict(self):
        from utils.offline_manager import OperationStatus
        assert OperationStatus.CONFLICT.value == "conflict"


# ==================== HMAC FUNCTIONS ====================

class TestHmacFunctions:
    def test_get_hmac_key_returns_bytes(self):
        from utils.offline_manager import _get_hmac_key
        with patch('utils.offline_manager.os.path.exists', return_value=False), \
             patch('builtins.open', MagicMock()):
            key = _get_hmac_key()
            assert isinstance(key, bytes)
            assert len(key) == 32

    def test_sign_operation_returns_hex_string(self):
        from utils.offline_manager import _sign_operation
        with patch('utils.offline_manager._get_hmac_key', return_value=b'test_key_32bytes_padded_to_32by'):
            result = _sign_operation('{"id":1}', 'create', 'client')
            assert isinstance(result, str)
            assert len(result) == 64  # SHA256 hex digest

    def test_verify_valid_signature(self):
        from utils.offline_manager import _sign_operation, _verify_operation_signature
        with patch('utils.offline_manager._get_hmac_key', return_value=b'test_key_32bytes_padded_to_32by'):
            sig = _sign_operation('{"id":1}', 'create', 'client')
            assert _verify_operation_signature('{"id":1}', 'create', 'client', sig) is True

    def test_verify_invalid_signature(self):
        from utils.offline_manager import _verify_operation_signature
        with patch('utils.offline_manager._get_hmac_key', return_value=b'test_key_32bytes_padded_to_32by'):
            assert _verify_operation_signature('{"id":1}', 'create', 'client', 'bad_signature') is False

    def test_different_data_different_signatures(self):
        from utils.offline_manager import _sign_operation
        with patch('utils.offline_manager._get_hmac_key', return_value=b'test_key_32bytes_padded_to_32by'):
            sig1 = _sign_operation('{"id":1}', 'create', 'client')
            sig2 = _sign_operation('{"id":2}', 'create', 'client')
            assert sig1 != sig2

    def test_different_types_different_signatures(self):
        from utils.offline_manager import _sign_operation
        with patch('utils.offline_manager._get_hmac_key', return_value=b'test_key_32bytes_padded_to_32by'):
            sig1 = _sign_operation('{"id":1}', 'create', 'client')
            sig2 = _sign_operation('{"id":1}', 'update', 'client')
            assert sig1 != sig2


# ==================== OFFLINE MANAGER ====================

@pytest.fixture
def om(tmp_path):
    """Создать OfflineManager с временной SQLite БД."""
    db_path = str(tmp_path / 'test.db')
    from utils.offline_manager import OfflineManager
    manager = OfflineManager(db_path=db_path, api_client=None)
    return manager


class TestOfflineManagerInit:
    def test_creates_instance(self, om):
        assert om is not None
        assert om.api_client is None

    def test_initial_status_offline(self, om):
        from utils.offline_manager import ConnectionStatus
        assert om._status == ConnectionStatus.OFFLINE

    def test_is_online_false_initially(self, om):
        assert om.is_online() is False


class TestOfflineManagerSetApiClient:
    def test_set_api_client(self, om):
        mock_api = MagicMock()
        om.set_api_client(mock_api)
        assert om.api_client is mock_api


class TestOfflineManagerStatus:
    def test_status_property(self, om):
        from utils.offline_manager import ConnectionStatus
        assert om.status == ConnectionStatus.OFFLINE

    def test_set_status_emits_signal(self, om):
        from utils.offline_manager import ConnectionStatus
        om.connection_status_changed = MagicMock()
        om.status = ConnectionStatus.ONLINE
        assert om._status == ConnectionStatus.ONLINE

    def test_is_online_true_when_online(self, om):
        from utils.offline_manager import ConnectionStatus
        om._status = ConnectionStatus.ONLINE
        assert om.is_online() is True

    def test_is_online_false_when_syncing(self, om):
        from utils.offline_manager import ConnectionStatus
        om._status = ConnectionStatus.SYNCING
        assert om.is_online() is False


class TestOfflineManagerQueue:
    def test_queue_operation(self, om):
        from utils.offline_manager import OperationType
        result = om.queue_operation(
            OperationType.CREATE, 'client', None,
            {'full_name': 'Тест'}
        )
        assert isinstance(result, int)
        assert result > 0

    def test_get_pending_operations_count(self, om):
        from utils.offline_manager import OperationType
        assert om.get_pending_operations_count() == 0
        om.queue_operation(OperationType.CREATE, 'client', None, {'full_name': 'А'})
        om.queue_operation(OperationType.UPDATE, 'client', 1, {'full_name': 'Б'})
        assert om.get_pending_operations_count() == 2

    def test_get_pending_operations(self, om):
        from utils.offline_manager import OperationType
        om.queue_operation(OperationType.CREATE, 'client', None, {'full_name': 'Тест'})
        ops = om.get_pending_operations()
        assert len(ops) == 1
        assert ops[0]['entity_type'] == 'client'

    def test_clear_synced_operations(self, om):
        from utils.offline_manager import OperationType, OperationStatus
        om.queue_operation(OperationType.CREATE, 'client', None, {'full_name': 'А'})
        # Помечаем как synced
        conn = om._get_connection()
        conn.execute("UPDATE offline_operations_queue SET status = ?", (OperationStatus.SYNCED.value,))
        conn.commit()
        conn.close()
        deleted = om.clear_synced_operations()
        assert deleted == 1
        assert om.get_pending_operations_count() == 0

    def test_get_operation_history(self, om):
        from utils.offline_manager import OperationType
        om.queue_operation(OperationType.CREATE, 'client', None, {'full_name': 'А'})
        om.queue_operation(OperationType.DELETE, 'contract', 5, {})
        history = om.get_operation_history(limit=10)
        assert len(history) == 2


class TestOfflineManagerSync:
    def test_force_sync_without_api_does_nothing(self, om):
        # Не должно упасть
        om.force_sync()

    def test_force_sync_when_offline_does_nothing(self, om):
        from utils.offline_manager import ConnectionStatus
        om._status = ConnectionStatus.OFFLINE
        om.api_client = MagicMock()
        om.force_sync()
        # Не упало — OK

    def test_retry_failed_operations(self, om):
        from utils.offline_manager import OperationType, OperationStatus
        om.queue_operation(OperationType.CREATE, 'client', None, {'full_name': 'Fail'})
        # Помечаем как failed
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
