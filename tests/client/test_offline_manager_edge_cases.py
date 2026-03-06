# -*- coding: utf-8 -*-
"""
MEDIUM/LOW тесты для OfflineManager:
- HMAC подпись операций (sign/verify)
- Очередь операций (queue/get_pending/count)
- ConnectionStatus enum
- OperationType / OperationStatus enums
- _execute_server_operation маппинг
- _start_sync guard (race condition)
- _check_connection логика

Без реального Qt (мокирование PyQt5).
"""
import pytest
import sys
import os
import json
import tempfile
import sqlite3
import threading
from unittest.mock import MagicMock, patch
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Мокаем PyQt5 перед импортом
_pyqt5_keys = ['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui']
_saved_pyqt5 = {k: sys.modules[k] for k in _pyqt5_keys if k in sys.modules}

_mock_qtcore = MagicMock()
_mock_qtcore.pyqtSignal = MagicMock(return_value=MagicMock())
_mock_qtcore.QObject = type('MockQObject', (), {'__init__': lambda self, *a, **kw: None})


class MockQTimer:
    def __init__(self, *args, **kwargs):
        self.timeout = MagicMock()
        self.timeout.connect = MagicMock()
    def start(self, interval=0): pass
    def stop(self): pass
    @staticmethod
    def singleShot(ms, callback):
        # В тестах выполняем callback сразу
        if callable(callback):
            callback()


_mock_qtcore.QTimer = MockQTimer

sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtCore'] = _mock_qtcore
sys.modules['PyQt5.QtWidgets'] = MagicMock()
sys.modules['PyQt5.QtGui'] = MagicMock()

from utils.offline_manager import (
    OfflineManager, ConnectionStatus, OperationType, OperationStatus,
    _sign_operation, _verify_operation_signature
)

# Восстанавливаем
for _k in _pyqt5_keys:
    if _k in _saved_pyqt5:
        sys.modules[_k] = _saved_pyqt5[_k]
    elif _k in sys.modules:
        del sys.modules[_k]
if 'utils.offline_manager' in sys.modules:
    del sys.modules['utils.offline_manager']


# ==================== Enums ====================

class TestEnums:
    """Enum-ы для offline-менеджера."""

    def test_connection_status_values(self):
        assert ConnectionStatus.ONLINE.value == "online"
        assert ConnectionStatus.OFFLINE.value == "offline"
        assert ConnectionStatus.CONNECTING.value == "connecting"
        assert ConnectionStatus.SYNCING.value == "syncing"

    def test_operation_type_values(self):
        assert OperationType.CREATE.value == "create"
        assert OperationType.UPDATE.value == "update"
        assert OperationType.DELETE.value == "delete"

    def test_operation_status_values(self):
        assert OperationStatus.PENDING.value == "pending"
        assert OperationStatus.SYNCING.value == "syncing"
        assert OperationStatus.SYNCED.value == "synced"
        assert OperationStatus.FAILED.value == "failed"
        assert OperationStatus.CONFLICT.value == "conflict"


# ==================== HMAC ====================

class TestHMAC:
    """HMAC подпись для защиты offline-операций."""

    def test_sign_returns_string(self):
        sig = _sign_operation('{"name":"test"}', 'create', 'client')
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA256 hex digest

    def test_verify_valid_signature(self):
        data = '{"id": 1}'
        sig = _sign_operation(data, 'update', 'contract')
        assert _verify_operation_signature(data, 'update', 'contract', sig) is True

    def test_verify_invalid_signature(self):
        data = '{"id": 1}'
        assert _verify_operation_signature(data, 'update', 'contract', 'invalid_sig') is False

    def test_verify_tampered_data(self):
        """Изменённые данные не проходят проверку."""
        original = '{"id": 1}'
        sig = _sign_operation(original, 'create', 'client')
        tampered = '{"id": 999}'
        assert _verify_operation_signature(tampered, 'create', 'client', sig) is False

    def test_verify_wrong_operation_type(self):
        data = '{"id": 1}'
        sig = _sign_operation(data, 'create', 'client')
        assert _verify_operation_signature(data, 'delete', 'client', sig) is False

    def test_verify_wrong_entity_type(self):
        data = '{"id": 1}'
        sig = _sign_operation(data, 'create', 'client')
        assert _verify_operation_signature(data, 'create', 'contract', sig) is False


# ==================== OfflineManager — init ====================

class TestOfflineManagerInit:
    """Инициализация OfflineManager."""

    def _make_om(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        om = OfflineManager(db_path=db_path, api_client=None)
        return om, db_path

    def test_init_creates_table(self):
        om, db_path = self._make_om()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='offline_operations_queue'")
        assert cursor.fetchone() is not None
        conn.close()
        os.unlink(db_path)

    def test_init_status_offline(self):
        om, db_path = self._make_om()
        assert om.status == ConnectionStatus.OFFLINE
        os.unlink(db_path)

    def test_set_api_client(self):
        om, db_path = self._make_om()
        mock_api = MagicMock()
        om.set_api_client(mock_api)
        assert om.api_client is mock_api
        os.unlink(db_path)

    def test_is_online_false_initial(self):
        om, db_path = self._make_om()
        assert om.is_online() is False
        os.unlink(db_path)


# ==================== OfflineManager — queue operations ====================

class TestOfflineManagerQueue:
    """Очередь offline-операций."""

    def _make_om(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        om = OfflineManager(db_path=db_path, api_client=None)
        return om, db_path

    def test_queue_operation(self):
        om, db_path = self._make_om()
        op_id = om.queue_operation(OperationType.CREATE, 'client', 1, {"name": "Тест"})
        assert op_id > 0
        assert om.get_pending_operations_count() == 1
        os.unlink(db_path)

    def test_queue_multiple_operations(self):
        om, db_path = self._make_om()
        om.queue_operation(OperationType.CREATE, 'client', 1, {"name": "A"})
        om.queue_operation(OperationType.UPDATE, 'client', 1, {"name": "B"})
        om.queue_operation(OperationType.DELETE, 'contract', 5, {})
        assert om.get_pending_operations_count() == 3
        os.unlink(db_path)

    def test_get_pending_operations(self):
        om, db_path = self._make_om()
        om.queue_operation(OperationType.CREATE, 'client', 10, {"name": "Тест"})
        ops = om.get_pending_operations()
        assert len(ops) == 1
        assert ops[0]['entity_type'] == 'client'
        assert ops[0]['entity_id'] == 10
        assert ops[0]['data'] == {"name": "Тест"}
        os.unlink(db_path)

    def test_pending_operations_ordered_by_time(self):
        om, db_path = self._make_om()
        om.queue_operation(OperationType.CREATE, 'client', 1, {"order": 1})
        om.queue_operation(OperationType.CREATE, 'client', 2, {"order": 2})
        ops = om.get_pending_operations()
        assert ops[0]['data']['order'] == 1
        assert ops[1]['data']['order'] == 2
        os.unlink(db_path)

    def test_hmac_signature_stored(self):
        om, db_path = self._make_om()
        om.queue_operation(OperationType.CREATE, 'client', 1, {"name": "Signed"})

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT signature FROM offline_operations_queue WHERE id = 1")
        row = cursor.fetchone()
        assert row['signature'] is not None
        assert len(row['signature']) == 64
        conn.close()
        os.unlink(db_path)

    def test_tampered_operation_skipped(self):
        """Операция с подменённой подписью пропускается при get_pending."""
        om, db_path = self._make_om()
        om.queue_operation(OperationType.CREATE, 'client', 1, {"name": "Original"})

        # Подменяем подпись в БД
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE offline_operations_queue SET signature = 'tampered_sig' WHERE id = 1")
        conn.commit()
        conn.close()

        ops = om.get_pending_operations()
        assert len(ops) == 0  # Подменённая операция пропущена
        os.unlink(db_path)

    def test_empty_queue_count_zero(self):
        om, db_path = self._make_om()
        assert om.get_pending_operations_count() == 0
        os.unlink(db_path)


# ==================== OfflineManager — _check_connection ====================

class TestOfflineManagerCheckConnection:
    """_check_connection — логика проверки подключения."""

    def _make_om(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        om = OfflineManager(db_path=db_path, api_client=None)
        return om, db_path

    def test_check_no_api_stays_offline(self):
        om, db_path = self._make_om()
        om._check_connection()
        assert om.status == ConnectionStatus.OFFLINE
        os.unlink(db_path)

    def test_check_api_online(self):
        om, db_path = self._make_om()
        mock_api = MagicMock()
        mock_api.force_online_check.return_value = True
        mock_api.reset_offline_cache = MagicMock()
        om.set_api_client(mock_api)
        om._check_connection()
        assert om.status == ConnectionStatus.ONLINE
        os.unlink(db_path)

    def test_check_api_offline(self):
        om, db_path = self._make_om()
        mock_api = MagicMock()
        mock_api.force_online_check.return_value = False
        om.set_api_client(mock_api)
        om._check_connection()
        assert om.status == ConnectionStatus.OFFLINE
        os.unlink(db_path)

    def test_check_skipped_during_sync(self):
        om, db_path = self._make_om()
        mock_api = MagicMock()
        om.set_api_client(mock_api)
        om._is_syncing = True
        om._check_connection()
        mock_api.force_online_check.assert_not_called()
        os.unlink(db_path)


# ==================== OfflineManager — _start_sync guard ====================

class TestOfflineManagerStartSync:
    """_start_sync — защита от одновременного запуска."""

    def _make_om(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        om = OfflineManager(db_path=db_path, api_client=MagicMock())
        return om, db_path

    def test_start_sync_sets_flag(self):
        om, db_path = self._make_om()
        om._sync_pending_operations = MagicMock()  # Не запускать реальную sync
        om._start_sync()
        assert om._is_syncing is True
        os.unlink(db_path)

    def test_start_sync_idempotent(self):
        """Повторный _start_sync — не запускает вторую синхронизацию."""
        om, db_path = self._make_om()
        om._is_syncing = True
        om._sync_pending_operations = MagicMock()
        om._start_sync()  # Не должно начать новую
        om._sync_pending_operations.assert_not_called()
        os.unlink(db_path)


# ==================== OfflineManager — _execute_server_operation ====================

class TestExecuteServerOperation:
    """_execute_server_operation — маппинг entity_type на методы API."""

    def _make_om(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        mock_api = MagicMock()
        om = OfflineManager(db_path=db_path, api_client=mock_api)
        return om, db_path

    def test_no_api_client_returns_failure(self):
        om, db_path = self._make_om()
        om.api_client = None
        result = om._execute_server_operation('create', 'client', 1, {})
        assert result['success'] is False
        os.unlink(db_path)

    def test_client_operation_routes(self):
        om, db_path = self._make_om()
        om._sync_client_operation = MagicMock(return_value={'success': True})
        result = om._execute_server_operation('create', 'client', 1, {"name": "T"})
        om._sync_client_operation.assert_called_once_with('create', 1, {"name": "T"})
        assert result['success'] is True
        os.unlink(db_path)

    def test_contract_operation_routes(self):
        om, db_path = self._make_om()
        om._sync_contract_operation = MagicMock(return_value={'success': True})
        om._execute_server_operation('update', 'contract', 5, {"status": "active"})
        om._sync_contract_operation.assert_called_once()
        os.unlink(db_path)

    def test_crm_card_operation_routes(self):
        om, db_path = self._make_om()
        om._sync_crm_card_operation = MagicMock(return_value={'success': True})
        om._execute_server_operation('create', 'crm_card', 1, {})
        om._sync_crm_card_operation.assert_called_once()
        os.unlink(db_path)

    def test_supervision_card_operation_routes(self):
        om, db_path = self._make_om()
        om._sync_supervision_card_operation = MagicMock(return_value={'success': True})
        om._execute_server_operation('update', 'supervision_card', 1, {})
        om._sync_supervision_card_operation.assert_called_once()
        os.unlink(db_path)

    def test_timeout_temporarily_increased(self):
        """Таймаут API временно увеличивается на время sync."""
        om, db_path = self._make_om()
        om.api_client.DEFAULT_TIMEOUT = 10
        om._sync_client_operation = MagicMock(return_value={'success': True})
        om._execute_server_operation('create', 'client', 1, {})
        # Таймаут должен быть восстановлен
        assert om.api_client.DEFAULT_TIMEOUT == 10
        os.unlink(db_path)


# ==================== OfflineManager — status property ====================

class TestOfflineManagerStatus:
    """status property — отслеживание изменений."""

    def _make_om(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        om = OfflineManager(db_path=db_path, api_client=None)
        return om, db_path

    def test_status_change_tracked(self):
        om, db_path = self._make_om()
        assert om.status == ConnectionStatus.OFFLINE
        om.status = ConnectionStatus.ONLINE
        assert om.status == ConnectionStatus.ONLINE
        os.unlink(db_path)

    def test_same_status_no_emit(self):
        """Установка того же статуса — connection_status_changed не вызывается."""
        om, db_path = self._make_om()
        om.connection_status_changed = MagicMock()
        om.status = ConnectionStatus.OFFLINE  # Тот же что и сейчас
        om.connection_status_changed.emit.assert_not_called()
        os.unlink(db_path)


# ==================== OfflineManager — monitoring ====================

class TestOfflineManagerMonitoring:
    """start_monitoring / stop_monitoring."""

    def _make_om(self):
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        om = OfflineManager(db_path=db_path, api_client=None)
        return om, db_path

    def test_start_monitoring(self):
        om, db_path = self._make_om()
        om.start_monitoring()
        # Не падает
        os.unlink(db_path)

    def test_stop_monitoring(self):
        om, db_path = self._make_om()
        om.start_monitoring()
        om.stop_monitoring()
        # Не падает
        os.unlink(db_path)

    def test_stop_monitoring_without_start(self):
        om, db_path = self._make_om()
        om.stop_monitoring()  # Не должно упасть
        os.unlink(db_path)
