# -*- coding: utf-8 -*-
"""
ПРОЦЕССНЫЕ ТЕСТЫ: Offline → Online цикл.

Проверяют ПОЛНУЮ цепочку:
  DataAccess (offline) → OfflineManager (реальная SQLite очередь) → синхронизация → API

Ключевые бизнес-правила:
  - Сетевые ошибки (APIConnectionError/APITimeoutError) → в очередь
  - Бизнес-ошибки (409/400/401) → НЕ в очередь (бесконечный retry)
  - HMAC подпись на каждой операции → защита от tampering
  - FIFO порядок синхронизации
  - Таймаут увеличивается при синхронизации
"""
import pytest
import sys
import os
import sqlite3
import tempfile
import json
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================== Fixtures ====================

@pytest.fixture
def offline_db():
    """Реальная SQLite БД для OfflineManager."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def mock_api():
    """Мок API клиента."""
    api = MagicMock()
    api.base_url = "https://test.example.com"
    api.is_online = True
    api.DEFAULT_TIMEOUT = 5
    api.force_online_check = MagicMock(return_value=True)
    api.reset_offline_cache = MagicMock()
    return api


@pytest.fixture
def offline_manager(offline_db, mock_api):
    """Реальный OfflineManager с реальной SQLite (pytest-qt предоставляет QApplication)."""
    from utils.offline_manager import OfflineManager
    om = OfflineManager(offline_db, mock_api)
    return om


@pytest.fixture
def data_access(mock_api, offline_manager):
    """DataAccess с реальным OfflineManager (очередь в SQLite)."""
    mock_db = MagicMock()
    mock_db.add_client = MagicMock(return_value=1)
    mock_db.add_contract = MagicMock(return_value=1)
    mock_db.update_client = MagicMock()
    mock_db.delete_client = MagicMock()
    mock_db.update_contract = MagicMock()
    mock_db.update_crm_card_column = MagicMock()
    mock_db.update_supervision_card_column = MagicMock()
    mock_db.get_crm_card_id_by_contract = MagicMock(return_value=10)

    with patch('utils.data_access._global_cache') as mock_cache, \
         patch('utils.data_access.get_offline_manager', return_value=offline_manager):
        mock_cache.get.return_value = None
        mock_cache.set = MagicMock()
        mock_cache.invalidate = MagicMock()

        from utils.data_access import DataAccess
        da = DataAccess.__new__(DataAccess)
        da.api_client = mock_api
        da.db = mock_db
        da._is_online = True
        da.prefer_local = False
        da._prev_api_mode = True
        # Мокаем сигналы
        da.connection_status_changed = MagicMock()
        da.operation_queued = MagicMock()
        da.pending_operations_changed = MagicMock()
        yield da


# ==================== Offline→Online полный цикл ====================

class TestOfflineOnlineCycle:
    """Полный цикл: работа offline → данные в очереди → восстановление → синхронизация."""

    def test_create_client_offline_queues_operation(self, data_access, offline_manager, mock_api):
        """Создание клиента при offline → операция сохраняется в реальной SQLite очереди."""
        from utils.api_client.exceptions import APIConnectionError

        mock_api.create_client.side_effect = APIConnectionError("Connection refused")

        # Создаём клиента — API упадёт, должна попасть в очередь
        with patch('utils.data_access.get_offline_manager', return_value=offline_manager):
            result = data_access.create_client({'full_name': 'Тест Клиент', 'phone': '+79001234567'})

        assert result is not None
        # Операция должна быть в реальной SQLite очереди
        pending = offline_manager.get_pending_operations()
        assert len(pending) == 1
        assert pending[0]['entity_type'] == 'client'
        assert pending[0]['operation_type'] == 'create'
        assert pending[0]['data']['full_name'] == 'Тест Клиент'

    def test_create_client_offline_has_hmac(self, data_access, offline_manager, mock_api):
        """Операция в очереди подписана HMAC."""
        from utils.api_client.exceptions import APITimeoutError

        mock_api.create_client.side_effect = APITimeoutError("Timeout")

        with patch('utils.data_access.get_offline_manager', return_value=offline_manager):
            data_access.create_client({'full_name': 'HMAC Клиент'})

        # Проверяем в сырой БД что signature не пустая
        conn = sqlite3.connect(offline_manager.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT signature FROM offline_operations_queue WHERE status = 'pending'")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row['signature'] is not None
        assert len(row['signature']) == 64  # SHA256 hex

    def test_multiple_operations_fifo_order(self, data_access, offline_manager, mock_api):
        """Несколько операций в очереди → порядок FIFO."""
        from utils.api_client.exceptions import APIConnectionError

        mock_api.create_client.side_effect = APIConnectionError("down")
        mock_api.update_client.side_effect = APIConnectionError("down")

        with patch('utils.data_access.get_offline_manager', return_value=offline_manager):
            data_access.create_client({'full_name': 'Первый'})
            data_access.update_client(1, {'full_name': 'Обновлённый'})

        pending = offline_manager.get_pending_operations()
        assert len(pending) == 2
        assert pending[0]['operation_type'] == 'create'
        assert pending[0]['data']['full_name'] == 'Первый'
        assert pending[1]['operation_type'] == 'update'
        assert pending[1]['data']['full_name'] == 'Обновлённый'

    def test_sync_sends_operations_to_api(self, offline_manager, mock_api):
        """При синхронизации операции отправляются на API."""
        from utils.offline_manager import OperationType

        # Добавляем операцию в очередь
        offline_manager.queue_operation(
            OperationType.CREATE, 'client', 1,
            {'full_name': 'Sync Test', 'phone': '+7900'}
        )

        # Мокаем API чтобы создание клиента прошло
        mock_api.create_client.return_value = {'id': 100, 'full_name': 'Sync Test'}

        # Синхронизируем одну операцию напрямую
        pending = offline_manager.get_pending_operations()
        result = offline_manager._sync_single_operation(pending[0])

        assert result is True
        mock_api.create_client.assert_called_once()
        # После синхронизации операция помечена как synced
        assert offline_manager.get_pending_operations_count() == 0

    def test_sync_timeout_increased(self, offline_manager, mock_api):
        """Таймаут API увеличивается при синхронизации."""
        from utils.offline_manager import OperationType

        original_timeout = mock_api.DEFAULT_TIMEOUT
        offline_manager.queue_operation(
            OperationType.UPDATE, 'client', 1, {'full_name': 'Timeout Test'}
        )

        mock_api.update_client.return_value = {'id': 1}

        pending = offline_manager.get_pending_operations()
        offline_manager._sync_single_operation(pending[0])

        # Таймаут должен быть восстановлен после операции
        assert mock_api.DEFAULT_TIMEOUT == original_timeout

    def test_sync_failed_operation_marked_failed(self, offline_manager, mock_api):
        """Неуспешная синхронизация → операция помечается как failed."""
        from utils.offline_manager import OperationType

        offline_manager.queue_operation(
            OperationType.CREATE, 'client', 1, {'full_name': 'Fail Test'}
        )

        mock_api.create_client.side_effect = Exception("Server Error 500")

        pending = offline_manager.get_pending_operations()
        result = offline_manager._sync_single_operation(pending[0])

        assert result is False
        # Операция помечена как failed, не pending
        assert offline_manager.get_pending_operations_count() == 0
        # Но в БД она есть со статусом failed
        conn = sqlite3.connect(offline_manager.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM offline_operations_queue")
        row = cursor.fetchone()
        conn.close()
        assert row['status'] == 'failed'


# ==================== Бизнес-ошибки НЕ в очередь ====================

class TestBusinessErrorsNotQueued:
    """Критическое правило: бизнес-ошибки (409/400/401) НЕ попадают в очередь.

    ВАЖНО: OfflineManager должен быть ONLINE, иначе DataAccess идёт в ветку
    `elif self.api_client:` (offline) где _queue_operation вызывается БЕЗ except-контекста,
    и sys.exc_info() = (None,None,None) → проверка типа ошибки не срабатывает.
    """

    def _set_online(self, offline_manager):
        """Перевести OfflineManager в online-режим."""
        from utils.offline_manager import ConnectionStatus
        offline_manager._status = ConnectionStatus.ONLINE

    def test_api_response_error_not_queued(self, data_access, offline_manager, mock_api):
        """APIResponseError (409) НЕ попадает в очередь."""
        from utils.api_client.exceptions import APIResponseError
        self._set_online(offline_manager)

        mock_api.create_client.side_effect = APIResponseError("Duplicate", status_code=409)

        with patch('utils.data_access.get_offline_manager', return_value=offline_manager):
            data_access.create_client({'full_name': 'Дубликат'})

        # Очередь ПУСТА — бизнес-ошибка не поставлена
        assert offline_manager.get_pending_operations_count() == 0

    def test_api_auth_error_not_queued(self, data_access, offline_manager, mock_api):
        """APIAuthError (401) НЕ попадает в очередь."""
        from utils.api_client.exceptions import APIAuthError
        self._set_online(offline_manager)

        mock_api.create_client.side_effect = APIAuthError("Token expired")

        with patch('utils.data_access.get_offline_manager', return_value=offline_manager):
            data_access.create_client({'full_name': 'Auth Fail'})

        assert offline_manager.get_pending_operations_count() == 0

    def test_value_error_not_queued(self, data_access, offline_manager, mock_api):
        """ValueError (бизнес-логика) НЕ попадает в очередь."""
        self._set_online(offline_manager)

        mock_api.update_client.side_effect = ValueError("Invalid phone format")

        with patch('utils.data_access.get_offline_manager', return_value=offline_manager):
            data_access.update_client(1, {'phone': 'bad'})

        assert offline_manager.get_pending_operations_count() == 0

    def test_connection_error_IS_queued(self, data_access, offline_manager, mock_api):
        """APIConnectionError ПОПАДАЕТ в очередь (сетевая ошибка)."""
        from utils.api_client.exceptions import APIConnectionError
        self._set_online(offline_manager)

        mock_api.update_client.side_effect = APIConnectionError("refused")

        with patch('utils.data_access.get_offline_manager', return_value=offline_manager):
            data_access.update_client(1, {'full_name': 'Network fail'})

        assert offline_manager.get_pending_operations_count() == 1

    def test_timeout_error_IS_queued(self, data_access, offline_manager, mock_api):
        """APITimeoutError ПОПАДАЕТ в очередь (сетевая ошибка)."""
        from utils.api_client.exceptions import APITimeoutError
        self._set_online(offline_manager)

        mock_api.delete_client.side_effect = APITimeoutError("Timed out")

        with patch('utils.data_access.get_offline_manager', return_value=offline_manager):
            data_access.delete_client(1)

        assert offline_manager.get_pending_operations_count() == 1
        pending = offline_manager.get_pending_operations()
        assert pending[0]['operation_type'] == 'delete'

    def test_api_400_bad_request_not_queued(self, data_access, offline_manager, mock_api):
        """APIResponseError(400) — Bad Request — НЕ в очередь."""
        from utils.api_client.exceptions import APIResponseError
        self._set_online(offline_manager)

        mock_api.update_client.side_effect = APIResponseError("Bad Request", status_code=400)

        with patch('utils.data_access.get_offline_manager', return_value=offline_manager):
            data_access.update_client(1, {'full_name': ''})

        assert offline_manager.get_pending_operations_count() == 0


# ==================== HMAC защита очереди ====================

class TestHMACQueueProtection:
    """HMAC подпись предотвращает tampering операций в очереди."""

    def test_tampered_data_skipped_during_sync(self, offline_manager, mock_api):
        """Изменённые данные в очереди → операция пропускается при синхронизации."""
        from utils.offline_manager import OperationType

        # Добавляем валидную операцию
        op_id = offline_manager.queue_operation(
            OperationType.CREATE, 'client', 1,
            {'full_name': 'Original'}
        )

        # Подменяем данные в БД (tampering!)
        conn = sqlite3.connect(offline_manager.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE offline_operations_queue SET data = ? WHERE id = ?",
            (json.dumps({'full_name': 'HACKED'}), op_id)
        )
        conn.commit()
        conn.close()

        # get_pending_operations проверяет HMAC — подменённая операция пропускается
        pending = offline_manager.get_pending_operations()
        assert len(pending) == 0  # Операция с невалидной подписью пропущена

    def test_valid_operation_passes_hmac(self, offline_manager):
        """Неподменённые операции проходят HMAC-проверку."""
        from utils.offline_manager import OperationType

        offline_manager.queue_operation(
            OperationType.UPDATE, 'contract', 5,
            {'status': 'СДАН', 'total': 100000}
        )

        pending = offline_manager.get_pending_operations()
        assert len(pending) == 1
        assert pending[0]['data']['status'] == 'СДАН'


# ==================== Offline sync entity routing ====================

class TestSyncEntityRouting:
    """При синхронизации операции маршрутизируются к правильным API методам."""

    def test_client_create_routes_to_create_client(self, offline_manager, mock_api):
        """create client → api.create_client()."""
        from utils.offline_manager import OperationType

        mock_api.create_client.return_value = {'id': 100}

        offline_manager.queue_operation(OperationType.CREATE, 'client', 1, {'full_name': 'Test'})
        pending = offline_manager.get_pending_operations()
        result = offline_manager._sync_single_operation(pending[0])

        assert result is True
        mock_api.create_client.assert_called_once_with({'full_name': 'Test'})

    def test_contract_update_routes_to_update_contract(self, offline_manager, mock_api):
        """update contract → api.update_contract()."""
        from utils.offline_manager import OperationType

        mock_api.update_contract.return_value = {'id': 5}

        offline_manager.queue_operation(OperationType.UPDATE, 'contract', 5, {'status': 'СДАН'})
        pending = offline_manager.get_pending_operations()
        result = offline_manager._sync_single_operation(pending[0])

        assert result is True
        mock_api.update_contract.assert_called_once_with(5, {'status': 'СДАН'})

    def test_crm_card_delete_routes_correctly(self, offline_manager, mock_api):
        """delete crm_card → api.delete_crm_card()."""
        from utils.offline_manager import OperationType

        mock_api.delete_crm_card.return_value = True

        offline_manager.queue_operation(OperationType.DELETE, 'crm_card', 10, {})
        pending = offline_manager.get_pending_operations()
        result = offline_manager._sync_single_operation(pending[0])

        assert result is True
        mock_api.delete_crm_card.assert_called_once_with(10)

    def test_supervision_card_update_routes_correctly(self, offline_manager, mock_api):
        """update supervision_card → api.update_supervision_card()."""
        from utils.offline_manager import OperationType

        mock_api.update_supervision_card.return_value = {'id': 7}

        offline_manager.queue_operation(
            OperationType.UPDATE, 'supervision_card', 7,
            {'column_name': 'Стадия 2'}
        )
        pending = offline_manager.get_pending_operations()
        result = offline_manager._sync_single_operation(pending[0])

        assert result is True
        mock_api.update_supervision_card.assert_called_once_with(7, {'column_name': 'Стадия 2'})

    def test_unknown_entity_type_fails(self, offline_manager, mock_api):
        """Неизвестный entity_type → операция failed."""
        from utils.offline_manager import OperationType

        offline_manager.queue_operation(OperationType.CREATE, 'unknown_entity', 1, {'x': 1})
        pending = offline_manager.get_pending_operations()
        result = offline_manager._sync_single_operation(pending[0])

        assert result is False  # Unknown entity type


# ==================== Connection check and sync trigger ====================

class TestConnectionCheckAndSync:
    """Проверка подключения и автоматический запуск синхронизации."""

    def test_offline_to_online_triggers_sync(self, offline_manager, mock_api):
        """Переход offline → online с операциями → запускается синхронизация."""
        from utils.offline_manager import OperationType, ConnectionStatus

        # Начальное состояние: offline с операцией в очереди
        offline_manager._status = ConnectionStatus.OFFLINE
        offline_manager.queue_operation(OperationType.CREATE, 'client', 1, {'full_name': 'Test'})

        # Мокаем _start_sync чтобы он не запускал поток
        offline_manager._start_sync = MagicMock()

        # Проверяем подключение — сервер доступен
        mock_api.force_online_check.return_value = True

        offline_manager._check_connection()

        # _start_sync должен быть вызван (была очередь + перешли из offline)
        offline_manager._start_sync.assert_called_once()

    def test_online_no_pending_no_sync(self, offline_manager, mock_api):
        """online без операций → синхронизация НЕ запускается."""
        from utils.offline_manager import ConnectionStatus

        offline_manager._status = ConnectionStatus.OFFLINE
        offline_manager._start_sync = MagicMock()
        mock_api.force_online_check.return_value = True

        offline_manager._check_connection()

        # Нет операций → _start_sync НЕ вызван
        offline_manager._start_sync.assert_not_called()

    def test_check_connection_skipped_during_sync(self, offline_manager, mock_api):
        """Во время синхронизации check_connection пропускается."""
        from utils.offline_manager import ConnectionStatus

        offline_manager._is_syncing = True
        old_status = offline_manager._status

        offline_manager._check_connection()

        # Статус не изменился, API не вызвано
        assert offline_manager._status == old_status
        mock_api.force_online_check.assert_not_called()

    def test_start_sync_race_condition_guard(self, offline_manager):
        """Двойной вызов _start_sync → только один запуск."""
        import threading

        # Первый вызов: устанавливает _is_syncing = True
        offline_manager._is_syncing = False

        # Имитируем что синхронизация уже идёт
        with offline_manager._sync_lock:
            offline_manager._is_syncing = True

        # Второй вызов не должен создать поток
        with patch('threading.Thread') as MockThread:
            offline_manager._start_sync()
            MockThread.assert_not_called()


# ==================== DataAccess local-first writes ====================

class TestDataAccessLocalFirst:
    """DataAccess: запись сначала локально, потом API."""

    def test_create_client_saves_locally_first(self, data_access, mock_api):
        """create_client → db.add_client вызывается ПЕРЕД api.create_client."""
        call_order = []
        data_access.db.add_client = lambda data: (call_order.append('db'), 1)[1]
        mock_api.create_client = lambda data: (call_order.append('api'), {'id': 100})[1]

        with patch('utils.data_access.get_offline_manager', return_value=None):
            data_access.create_client({'full_name': 'Order Test'})

        assert call_order == ['db', 'api']

    def test_update_client_saves_locally_first(self, data_access, mock_api):
        """update_client → db.update_client вызывается ПЕРЕД api.update_client."""
        call_order = []
        data_access.db.update_client = lambda cid, data: call_order.append('db')
        mock_api.update_client = lambda cid, data: (call_order.append('api'), {'id': 1})[1]

        with patch('utils.data_access.get_offline_manager', return_value=None):
            data_access.update_client(1, {'full_name': 'Updated'})

        assert call_order == ['db', 'api']

    def test_api_returns_list_protection(self, data_access, mock_api):
        """API возвращает list вместо dict → DataAccess обрабатывает корректно."""
        # Известный баг: API иногда возвращает [{}] вместо {}
        mock_api.create_client.return_value = [{'id': 100, 'full_name': 'List Bug'}]

        with patch('utils.data_access.get_offline_manager', return_value=None):
            result = data_access.create_client({'full_name': 'List Bug'})

        # Должен вернуть dict, не list
        assert isinstance(result, dict)
        assert result.get('id') == 100

    def test_server_id_updates_local_id(self, data_access, mock_api):
        """Сервер возвращает другой ID → локальный обновляется."""
        data_access.db.add_client.return_value = 1  # Локальный ID
        mock_api.create_client.return_value = {'id': 500}  # Серверный ID

        data_access._update_local_id = MagicMock()

        with patch('utils.data_access.get_offline_manager', return_value=None):
            data_access.create_client({'full_name': 'ID Sync'})

        data_access._update_local_id.assert_called_once_with('clients', 1, 500)


# ==================== DataAccess cache behavior ====================

class TestDataAccessCacheBehavior:
    """Кеш инвалидируется при записи, используется при чтении."""

    def test_create_invalidates_cache(self, data_access, mock_api):
        """create_client → кеш clients инвалидирован."""
        with patch('utils.data_access._global_cache') as mock_cache, \
             patch('utils.data_access.get_offline_manager', return_value=None):
            mock_api.create_client.return_value = {'id': 1}
            data_access.create_client({'full_name': 'Cache Test'})
            mock_cache.invalidate.assert_called_with("clients")

    def test_create_contract_invalidates_both_caches(self, data_access, mock_api):
        """create_contract → инвалидирует и contracts, и crm_cards кеш."""
        invalidated = []
        with patch('utils.data_access._global_cache') as mock_cache, \
             patch('utils.data_access.get_offline_manager', return_value=None):
            mock_cache.invalidate.side_effect = lambda prefix: invalidated.append(prefix)
            mock_api.create_contract.return_value = {'id': 1, 'project_type': 'Дизайн'}
            data_access.create_contract({'project_type': 'Дизайн'})

        assert "contracts" in invalidated
        assert "crm_cards" in invalidated

    def test_delete_contract_also_deletes_crm_card_locally(self, data_access, mock_api):
        """delete_contract → удаляет и CRM карточку локально."""
        mock_api.delete_contract.return_value = True
        data_access.db.get_crm_card_id_by_contract.return_value = 10
        data_access.db.delete_order = MagicMock(return_value=True)

        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=MagicMock(return_value=True))):
            result = data_access.delete_contract(5)

        assert result is True
        data_access.db.delete_order.assert_called_once_with(5, 10)
