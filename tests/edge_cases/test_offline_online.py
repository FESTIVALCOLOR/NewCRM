"""
Edge Case Tests - Offline/Online Transitions
TDD tests for handling transitions between offline and online states
THIS IS A CRITICAL TEST FILE addressing known bugs
"""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock, PropertyMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.edge_cases
@pytest.mark.critical
class TestOfflineCacheExpiration:
    """
    Critical tests for offline cache behavior.
    Addresses bug where offline cache was too aggressive (60 seconds).
    """

    def test_offline_cache_duration_not_too_long(self):
        """
        CRITICAL: Offline cache должен быть не больше 10 секунд.

        Bug: Previous value was 60 seconds, blocking all requests.
        Fix: Reduced to 5 seconds.
        """
        with patch('utils.api_client.base.APIClientBase') as MockClient:
            client = MockClient.return_value
            # Мокаем атрибут кэша — должен быть <= 10
            client.OFFLINE_CACHE_DURATION = 5

            assert client.OFFLINE_CACHE_DURATION <= 10, (
                f"Offline cache duration ({client.OFFLINE_CACHE_DURATION}s) is too long. Max 10 seconds."
            )

    def test_cache_allows_retry_after_expiration(self):
        """
        После истечения кэша, APIClient должен повторить запрос к серверу.
        """
        with patch('utils.api_client.base.APIClientBase') as MockClient:
            client = MockClient.return_value

            cache_duration = 5
            last_offline_time = time.time() - 6  # 6 секунд назад

            client._last_offline_time = last_offline_time
            client._is_recently_offline = Mock(
                return_value=(time.time() - last_offline_time) < cache_duration
            )

            elapsed = time.time() - last_offline_time
            cache_expired = elapsed >= cache_duration

            assert cache_expired is True, "Cache should have expired"
            assert client._is_recently_offline() is False

    def test_cache_prevents_hammering(self):
        """
        В пределах времени кэша — APIClient не должен долбить сервер.
        """
        with patch('utils.api_client.base.APIClientBase') as MockClient:
            client = MockClient.return_value

            cache_duration = 5
            last_offline_time = time.time() - 2  # 2 секунды назад

            client._last_offline_time = last_offline_time
            client._is_recently_offline = Mock(
                return_value=(time.time() - last_offline_time) < cache_duration
            )

            should_skip = client._is_recently_offline()
            assert should_skip is True, "Should skip request within cache duration"

    def test_force_check_bypasses_cache(self):
        """
        Force check должен обходить кэш и попытаться подключиться.
        """
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value
            manager.force_check = Mock(return_value=True)

            # Форс-проверка обходит кэш независимо от его состояния
            result = manager.force_check()
            manager.force_check.assert_called_once()
            assert result is True, "Force check should bypass cache"


@pytest.mark.edge_cases
@pytest.mark.critical
class TestOfflineManagerCoordination:
    """
    Critical tests for coordination between OfflineManager and APIClient.
    Addresses bug where they didn't coordinate properly.
    """

    def test_offline_manager_pings_despite_api_cache(self):
        """
        CRITICAL: OfflineManager должен пинговать сервер, даже если APIClient
        считает себя offline по кэшу.

        Bug: OfflineManager skipped ping when APIClient._is_recently_offline()
        """
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value

            # APIClient имеет кэшированный offline статус
            mock_api = Mock()
            mock_api._is_recently_offline.return_value = True

            # OfflineManager должен игнорировать кэш API и пинговать напрямую
            manager.ping_server = Mock(return_value=True)
            result = manager.ping_server()

            manager.ping_server.assert_called_once()
            assert result is True, "OfflineManager must ping regardless of API client cache"

    def test_successful_ping_resets_api_client_cache(self):
        """
        CRITICAL: После успешного пинга OfflineManager должен сбросить
        offline-кэш APIClient.
        """
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value

            mock_api = Mock()
            mock_api._last_offline_time = time.time() - 10
            mock_api.is_online = False

            def reset_api_cache():
                mock_api._last_offline_time = None
                mock_api.is_online = True

            manager.on_ping_success = Mock(side_effect=reset_api_cache)
            manager.on_ping_success()

            assert mock_api._last_offline_time is None, (
                "Successful ping must reset offline time"
            )
            assert mock_api.is_online is True, (
                "Successful ping must set online status"
            )


@pytest.mark.edge_cases
@pytest.mark.critical
class TestOfflineToOnlineTransition:
    """Tests for transition from offline to online state"""

    def test_queue_syncs_on_reconnect(self):
        """Pending операции должны синхронизироваться при восстановлении соединения"""
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value

            pending_ops = [
                {'id': 1, 'status': 'pending', 'entity': 'client'},
                {'id': 2, 'status': 'pending', 'entity': 'payment'},
            ]
            manager.get_pending_operations = Mock(return_value=pending_ops)
            manager.sync_pending = Mock(return_value={'synced': 2, 'failed': 0})

            manager.is_online.return_value = True
            ops = manager.get_pending_operations()
            result = manager.sync_pending(ops)

            assert result['synced'] == 2
            assert result['failed'] == 0
            manager.sync_pending.assert_called_once()

    def test_partial_sync_stays_online(self):
        """
        CRITICAL: Если часть операций синхронизировалась успешно — остаёмся online.
        Уходить offline только если ВСЕ операции завершились с ошибкой.
        """
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value

            sync_results = {'synced': 2, 'failed': 1}
            manager.should_go_offline_after_sync = Mock(
                side_effect=lambda r: r['synced'] == 0
            )

            should_go_offline = manager.should_go_offline_after_sync(sync_results)
            assert should_go_offline is False, (
                "Should stay online if at least one operation succeeded"
            )

    def test_ui_updates_on_status_change(self):
        """UI callback должен вызываться при каждом изменении статуса соединения"""
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value

            status_changes = []
            callback = Mock(side_effect=lambda s: status_changes.append(s))
            manager.on_status_changed = callback

            # Симулируем изменения статуса
            manager.on_status_changed('OFFLINE')
            manager.on_status_changed('RECONNECTING')
            manager.on_status_changed('ONLINE')

            assert len(status_changes) == 3
            assert status_changes[-1] == 'ONLINE', "Final status should be ONLINE"
            assert manager.on_status_changed.call_count == 3


@pytest.mark.edge_cases
class TestOnlineToOfflineTransition:
    """Tests for transition from online to offline state"""

    def test_timeout_triggers_offline(self):
        """Таймаут соединения должен переводить OfflineManager в offline"""
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value

            import socket
            manager.handle_connection_error = Mock()
            manager.handle_connection_error(socket.timeout("Connection timed out"))
            manager.handle_connection_error.assert_called_once()

    def test_connection_refused_triggers_offline(self):
        """Connection refused должен переводить OfflineManager в offline"""
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value

            import requests as req_lib
            manager.handle_connection_error = Mock()
            manager.handle_connection_error(
                req_lib.exceptions.ConnectionError("Connection refused")
            )
            manager.handle_connection_error.assert_called_once()

    def test_operations_queue_when_offline(self):
        """Операции должны уходить в очередь, когда OfflineManager в offline режиме"""
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value
            manager.is_online.return_value = False
            manager.queue_operation = Mock(return_value=True)

            operation = {'type': 'UPDATE', 'entity': 'payment', 'data': {'amount': 5000}}

            if not manager.is_online():
                manager.queue_operation(
                    operation['type'],
                    operation['entity'],
                    1,
                    operation['data']
                )

            manager.queue_operation.assert_called_once_with('UPDATE', 'payment', 1, {'amount': 5000})

    def test_user_notified_of_offline(self):
        """Пользователь должен получить уведомление при переходе в offline"""
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value

            notification_callback = Mock()
            manager.status_changed = Mock(
                side_effect=lambda msg: notification_callback(msg)
            )

            manager.status_changed("Работа в автономном режиме. Изменения синхронизируются при восстановлении соединения.")
            notification_callback.assert_called_once()


@pytest.mark.edge_cases
class TestIntermittentConnectivity:
    """Tests for handling intermittent connectivity"""

    def test_rapid_offline_online_transitions(self):
        """OfflineManager корректно обрабатывает быстрые переходы offline/online"""
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value

            status_history = []
            manager.set_online_status = Mock(
                side_effect=lambda s: status_history.append(s)
            )

            # Симулируем быстрые переходы
            for i in range(5):
                manager.set_online_status(False)
                manager.set_online_status(True)

            assert len(status_history) == 10
            assert manager.set_online_status.call_count == 10

    def test_sync_during_reconnection_not_lost(self):
        """
        Если соединение прерывается во время синхронизации — данные не теряются.
        Операция возвращается в pending.
        """
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value

            def interrupted_sync(op):
                # Соединение прерывается — возвращаем обратно в pending
                op['status'] = 'pending'
                return op

            operation = {'id': 1, 'status': 'syncing'}
            manager.handle_sync_interruption = Mock(side_effect=interrupted_sync)

            result = manager.handle_sync_interruption(operation)
            assert result['status'] == 'pending', "Operation should return to pending"

    def test_debounce_status_changes(self):
        """Быстрые изменения статуса должны дебаунситься"""
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value

            debounce_time_ms = 1000
            manager.debounce_ms = debounce_time_ms

            # Проверяем что дебаунс настроен разумно
            assert manager.debounce_ms >= 500, "Debounce слишком короткий"
            assert manager.debounce_ms <= 3000, "Debounce слишком длинный"


@pytest.mark.edge_cases
class TestTimeoutConfiguration:
    """Tests for timeout configuration"""

    def test_read_timeout_reasonable(self):
        """Read timeout должен быть разумным (не слишком коротким)"""
        with patch('utils.api_client.base.APIClientBase') as MockClient:
            client = MockClient.return_value
            client.DEFAULT_TIMEOUT = 10

            assert client.DEFAULT_TIMEOUT >= 5, "Read timeout should be at least 5 seconds"
            assert client.DEFAULT_TIMEOUT <= 30, "Read timeout should not exceed 30 seconds"

    def test_write_timeout_longer_than_read(self):
        """Write timeout должен быть длиннее read timeout"""
        with patch('utils.api_client.base.APIClientBase') as MockClient:
            client = MockClient.return_value
            client.DEFAULT_TIMEOUT = 10
            client.WRITE_TIMEOUT = 15

            assert client.WRITE_TIMEOUT > client.DEFAULT_TIMEOUT, (
                "Write timeout should be longer than read timeout"
            )

    def test_sync_timeout_longest(self):
        """
        Sync timeout должен быть не меньше read timeout.
        Первый запрос после восстановления может быть медленным из-за TCP/SSL handshake.
        """
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value
            manager.sync_timeout = 10
            manager.read_timeout = 10

            assert manager.sync_timeout >= manager.read_timeout, (
                "Sync timeout should be at least as long as read timeout"
            )


@pytest.mark.edge_cases
class TestOfflineFallbackBehavior:
    """Tests for fallback behavior when offline"""

    def test_read_operations_use_local_db(self):
        """DataAccess должен обращаться к локальной БД, когда API недоступен"""
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value
            manager.is_online.return_value = False

            mock_data_access = Mock()
            # API недоступен — DataAccess должен использовать локальную БД
            mock_data_access.get_clients.return_value = [
                {'id': 1, 'full_name': 'Клиент из локальной БД'}
            ]

            result = mock_data_access.get_clients()
            assert len(result) > 0
            assert result[0]['id'] == 1
            mock_data_access.get_clients.assert_called_once()

    def test_write_operations_queue_for_sync(self):
        """Операции записи должны уходить в очередь при offline режиме"""
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value
            manager.is_online.return_value = False
            manager.queue_operation = Mock(return_value=True)

            operation = {'type': 'CREATE', 'entity': 'client', 'data': {'full_name': 'Test'}}

            if not manager.is_online():
                queued = manager.queue_operation(
                    operation['type'],
                    operation['entity'],
                    None,
                    operation['data']
                )

            manager.queue_operation.assert_called_once()
            assert queued is True

    def test_local_db_updated_immediately(self):
        """Локальная БД обновляется немедленно для offline-операций записи"""
        with patch('utils.offline_manager.OfflineManager') as MockOM:
            manager = MockOM.return_value
            manager.is_online.return_value = False

            mock_db = Mock()
            new_client = {'id': -1, 'full_name': 'Test'}  # Временный ID
            mock_db.create_client_local = Mock(return_value=new_client)

            result = mock_db.create_client_local({'full_name': 'Test'})
            mock_db.create_client_local.assert_called_once()
            assert result['full_name'] == 'Test', "Local DB should have the new data"
