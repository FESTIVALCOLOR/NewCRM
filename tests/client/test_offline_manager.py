# -*- coding: utf-8 -*-
"""
Тесты OfflineManager — очередь offline-операций, синхронизация, HMAC подпись.
"""

import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

pytest.importorskip("PyQt5")

from utils.offline_manager import (
    OfflineManager,
    ConnectionStatus,
    OperationType,
    OperationStatus,
    _sign_operation,
    _verify_operation_signature,
)


@pytest.fixture
def tmp_db(tmp_path):
    """Временная SQLite БД для тестов"""
    return str(tmp_path / "test_offline.db")


@pytest.fixture
def qapp():
    """Offscreen QApplication"""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def mock_api():
    """Мок API клиента"""
    api = MagicMock()
    api.base_url = "http://test:8000"
    return api


@pytest.fixture
def manager(qapp, tmp_db, mock_api):
    """OfflineManager с мок-API"""
    mgr = OfflineManager(db_path=tmp_db, api_client=mock_api)
    yield mgr
    mgr.stop_monitoring()


# ============================================================
# Тесты HMAC подписи
# ============================================================

class TestHMACSignature:
    """Тесты подписи операций"""

    def test_sign_operation_returns_hex(self):
        """_sign_operation возвращает hex строку"""
        sig = _sign_operation('{"test": 1}', "create", "client")
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex = 64 символа

    def test_verify_valid_signature(self):
        """_verify_operation_signature проверяет валидную подпись"""
        data = '{"id": 1, "name": "test"}'
        sig = _sign_operation(data, "update", "employee")
        assert _verify_operation_signature(data, "update", "employee", sig) is True

    def test_verify_invalid_signature(self):
        """_verify_operation_signature отвергает невалидную подпись"""
        data = '{"id": 1}'
        assert _verify_operation_signature(data, "create", "client", "invalid_sig") is False

    def test_different_operations_different_signatures(self):
        """Разные операции дают разные подписи"""
        data = '{"id": 1}'
        sig_create = _sign_operation(data, "create", "client")
        sig_update = _sign_operation(data, "update", "client")
        assert sig_create != sig_update

    def test_different_entities_different_signatures(self):
        """Разные сущности дают разные подписи"""
        data = '{"id": 1}'
        sig_client = _sign_operation(data, "create", "client")
        sig_employee = _sign_operation(data, "create", "employee")
        assert sig_client != sig_employee


# ============================================================
# Тесты Enum'ов
# ============================================================

class TestEnums:
    """Тесты перечислений"""

    def test_connection_status_values(self):
        """ConnectionStatus имеет все необходимые значения"""
        assert ConnectionStatus.ONLINE.value == "online"
        assert ConnectionStatus.OFFLINE.value == "offline"
        assert ConnectionStatus.CONNECTING.value == "connecting"
        assert ConnectionStatus.SYNCING.value == "syncing"

    def test_operation_type_values(self):
        """OperationType имеет все CRUD операции"""
        assert OperationType.CREATE.value == "create"
        assert OperationType.UPDATE.value == "update"
        assert OperationType.DELETE.value == "delete"

    def test_operation_status_values(self):
        """OperationStatus имеет все статусы"""
        assert OperationStatus.PENDING.value == "pending"
        assert OperationStatus.SYNCED.value == "synced"
        assert OperationStatus.FAILED.value == "failed"
        assert OperationStatus.CONFLICT.value == "conflict"


# ============================================================
# Тесты инициализации
# ============================================================

class TestOfflineManagerInit:
    """Тесты инициализации OfflineManager"""

    def test_create_manager(self, qapp, tmp_db):
        """OfflineManager создаётся без ошибок"""
        mgr = OfflineManager(db_path=tmp_db)
        assert mgr is not None
        assert mgr.db_path == tmp_db
        mgr.stop_monitoring()

    def test_initial_status_offline(self, qapp, tmp_db):
        """Начальный статус — OFFLINE"""
        mgr = OfflineManager(db_path=tmp_db)
        assert mgr.status == ConnectionStatus.OFFLINE
        mgr.stop_monitoring()

    def test_is_online_initially_false(self, qapp, tmp_db):
        """is_online — False при инициализации"""
        mgr = OfflineManager(db_path=tmp_db)
        assert mgr.is_online() is False
        mgr.stop_monitoring()

    def test_operations_queue_table_created(self, qapp, tmp_db):
        """Таблица offline_operations_queue создаётся автоматически"""
        import sqlite3
        mgr = OfflineManager(db_path=tmp_db)
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='offline_operations_queue'"
        )
        assert cursor.fetchone() is not None
        conn.close()
        mgr.stop_monitoring()

    def test_set_api_client(self, manager, mock_api):
        """set_api_client устанавливает клиент"""
        new_api = MagicMock()
        manager.set_api_client(new_api)
        assert manager.api_client is new_api


# ============================================================
# Тесты очереди операций
# ============================================================

class TestOperationsQueue:
    """Тесты очереди offline-операций"""

    def test_queue_create_operation(self, manager):
        """queue_operation добавляет CREATE операцию"""
        result = manager.queue_operation(
            OperationType.CREATE, "client", None,
            {"full_name": "Тест Клиент", "phone": "+71234567890"}
        )
        assert result

    def test_queue_update_operation(self, manager):
        """queue_operation добавляет UPDATE операцию"""
        result = manager.queue_operation(
            OperationType.UPDATE, "employee", 42,
            {"full_name": "Новое Имя"}
        )
        assert result

    def test_queue_delete_operation(self, manager):
        """queue_operation добавляет DELETE операцию"""
        result = manager.queue_operation(
            OperationType.DELETE, "contract", 100, {}
        )
        assert result

    def test_pending_count_increases(self, manager):
        """Счётчик pending операций увеличивается"""
        initial = manager.get_pending_operations_count()
        manager.queue_operation(OperationType.CREATE, "client", None, {"name": "test1"})
        manager.queue_operation(OperationType.CREATE, "client", None, {"name": "test2"})
        assert manager.get_pending_operations_count() == initial + 2

    def test_get_pending_operations(self, manager):
        """get_pending_operations возвращает список операций"""
        manager.queue_operation(OperationType.CREATE, "client", None, {"name": "test"})
        ops = manager.get_pending_operations()
        assert isinstance(ops, list)
        assert len(ops) >= 1

    def test_pending_operation_structure(self, manager):
        """Структура операции содержит обязательные ключи"""
        manager.queue_operation(OperationType.UPDATE, "employee", 1, {"name": "test"})
        ops = manager.get_pending_operations()
        op = ops[-1]  # последняя добавленная
        assert "id" in op
        assert "operation_type" in op
        assert "entity_type" in op
        assert "status" in op
        assert op["operation_type"] == "update"
        assert op["entity_type"] == "employee"
        assert op["status"] == "pending"

    def test_operation_data_preserved(self, manager):
        """Данные операции сохраняются корректно"""
        manager.queue_operation(OperationType.CREATE, "client", None, {"name": "test_preserved"})
        ops = manager.get_pending_operations()
        op = ops[-1]
        # data может быть dict или строка JSON
        data = op.get("data", {})
        if isinstance(data, str):
            data = json.loads(data)
        assert data.get("name") == "test_preserved"

    def test_queue_operation_with_none_entity_id(self, manager):
        """CREATE операция с entity_id=None"""
        result = manager.queue_operation(OperationType.CREATE, "payment", None, {"amount": 100})
        assert result
        ops = manager.get_pending_operations()
        assert len(ops) >= 1


# ============================================================
# Тесты статуса подключения
# ============================================================

class TestConnectionStatus:
    """Тесты управления статусом подключения"""

    def test_status_setter(self, manager):
        """Установка статуса через setter"""
        manager.status = ConnectionStatus.ONLINE
        assert manager.status == ConnectionStatus.ONLINE

    def test_is_online_when_online(self, manager):
        """is_online возвращает True при ONLINE"""
        manager.status = ConnectionStatus.ONLINE
        assert manager.is_online() is True

    def test_is_online_when_offline(self, manager):
        """is_online возвращает False при OFFLINE"""
        manager.status = ConnectionStatus.OFFLINE
        assert manager.is_online() is False


# ============================================================
# Тесты истории операций
# ============================================================

class TestOperationHistory:
    """Тесты истории операций"""

    def test_get_operation_history(self, manager):
        """get_operation_history возвращает list"""
        history = manager.get_operation_history()
        assert isinstance(history, list)

    def test_history_includes_queued(self, manager):
        """История включает добавленные операции"""
        manager.queue_operation(OperationType.CREATE, "client", None, {"name": "hist_test"})
        history = manager.get_operation_history(limit=100)
        assert len(history) >= 1

    def test_history_limit(self, manager):
        """Лимит ограничивает количество записей"""
        for i in range(5):
            manager.queue_operation(OperationType.CREATE, "client", None, {"name": f"test_{i}"})
        history = manager.get_operation_history(limit=3)
        assert len(history) <= 3


# ============================================================
# Тесты очистки и повтора
# ============================================================

class TestClearAndRetry:
    """Тесты очистки и повтора операций"""

    def test_clear_synced_operations(self, manager):
        """clear_synced_operations не падает"""
        manager.clear_synced_operations()
        # Просто не должно упасть

    def test_retry_failed_operations(self, manager):
        """retry_failed_operations не падает"""
        manager.retry_failed_operations()


# ============================================================
# Тесты синхронизации (мок)
# ============================================================

class TestSync:
    """Тесты синхронизации через mock API"""

    def test_force_sync_when_offline(self, manager):
        """force_sync при offline — ничего не делает"""
        manager.status = ConnectionStatus.OFFLINE
        manager.force_sync()
        # Не должно упасть

    def test_sync_single_create_client(self, manager, mock_api):
        """Синхронизация CREATE client через API"""
        mock_api.create_client.return_value = {"id": 999, "full_name": "Тест"}
        manager.status = ConnectionStatus.ONLINE

        # Добавляем операцию
        manager.queue_operation(OperationType.CREATE, "client", None,
                                {"full_name": "Тест", "phone": "+7123"})
        ops = manager.get_pending_operations()
        assert len(ops) >= 1

    def test_sync_does_not_crash_on_api_error(self, manager, mock_api):
        """Синхронизация не падает при ошибке API"""
        mock_api.create_client.side_effect = Exception("API Error")
        manager.status = ConnectionStatus.ONLINE
        manager.queue_operation(OperationType.CREATE, "client", None, {"name": "err"})
        # force_sync не должен упасть
        manager.force_sync()
