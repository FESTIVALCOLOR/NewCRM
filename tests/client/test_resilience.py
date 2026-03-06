# -*- coding: utf-8 -*-
"""
RESILIENCE-ТЕСТЫ (Уровень 1): сетевая устойчивость клиента.

Проверяют поведение APIClientBase и SyncManager при сетевых сбоях:
  - SSL ошибки (SSLEOFError — как на скриншоте Docker rebuild)
  - ConnectionError (сервер недоступен)
  - Timeout (сервер тормозит)
  - Offline кеш (не долбим сервер сразу после сбоя)
  - Восстановление (force_online_check → reset_offline_cache)
  - Retry + exponential backoff
  - SyncManager пропускает heartbeat/sync при offline
"""

import sys
import os
import time
import ssl
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from requests.exceptions import (
    ConnectionError as ReqConnectionError,
    Timeout as ReqTimeout,
    SSLError as ReqSSLError,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.api_client.base import APIClientBase
from utils.api_client.exceptions import (
    APIConnectionError,
    APITimeoutError,
    APIError,
)


# ==================== Fixtures ====================

@pytest.fixture
def api():
    """APIClientBase с минимальными задержками для тестов."""
    client = APIClientBase("https://test.example.com", verify_ssl=False)
    # Ускоряем retry для тестов (не ждать реальные секунды)
    client.RETRY_DELAY = 0.01
    client.RETRY_MAX_DELAY = 0.05
    client.OFFLINE_CACHE_DURATION = 0.5  # 500ms кеш для тестов
    client.MAX_RETRIES = 2  # Минимум retry для скорости
    return client


# ==================== SSL ошибки (SSLEOFError) ====================

class TestSSLErrors:
    """SSL ошибки (как при Docker rebuild) корректно обрабатываются."""

    def test_ssl_eof_error_marks_offline(self, api):
        """SSLEOFError → клиент переходит в offline."""
        ssl_error = ReqSSLError(
            "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol"
        )
        api.session.request = MagicMock(side_effect=ReqConnectionError(ssl_error))

        with pytest.raises(APIConnectionError):
            api._request("GET", f"{api.base_url}/api/test")

        assert api.is_online is False

    def test_ssl_error_sets_offline_cache(self, api):
        """После SSL ошибки — кеш offline активен."""
        ssl_error = ReqSSLError("SSL handshake failed")
        api.session.request = MagicMock(side_effect=ReqConnectionError(ssl_error))

        with pytest.raises(APIConnectionError):
            api._request("GET", f"{api.base_url}/api/test")

        assert api._is_recently_offline() is True

    def test_ssl_error_subsequent_requests_cached(self, api):
        """После SSL ошибки — следующие запросы используют кеш (не долбят сервер)."""
        ssl_error = ReqSSLError("Connection reset")
        api.session.request = MagicMock(side_effect=ReqConnectionError(ssl_error))

        # Первый запрос — реальная ошибка
        with pytest.raises(APIConnectionError):
            api._request("GET", f"{api.base_url}/api/test")

        api.session.request.reset_mock()

        # Второй запрос — из кеша (session.request НЕ вызван)
        with pytest.raises(APIConnectionError, match="Offline режим.*кеш"):
            api._request("GET", f"{api.base_url}/api/another")

        api.session.request.assert_not_called()


# ==================== ConnectionError ====================

class TestConnectionErrors:
    """ConnectionError (сервер недоступен) → offline."""

    def test_connection_refused_marks_offline(self, api):
        """Connection refused → offline после всех retry."""
        api.session.request = MagicMock(
            side_effect=ReqConnectionError("Connection refused")
        )

        with pytest.raises(APIConnectionError):
            api._request("GET", f"{api.base_url}/api/test")

        assert api.is_online is False

    def test_connection_error_retries_before_offline(self, api):
        """При ConnectionError — пробует MAX_RETRIES раз перед offline."""
        api.session.request = MagicMock(
            side_effect=ReqConnectionError("refused")
        )

        with pytest.raises(APIConnectionError):
            api._request("GET", f"{api.base_url}/api/test")

        assert api.session.request.call_count == api.MAX_RETRIES

    def test_mark_offline_false_does_not_affect_status(self, api):
        """mark_offline=False → статус online не меняется (для heartbeat/sync)."""
        api.session.request = MagicMock(
            side_effect=ReqConnectionError("refused")
        )

        with pytest.raises(APIConnectionError):
            api._request("GET", f"{api.base_url}/api/test", mark_offline=False)

        assert api.is_online is True
        assert api._is_recently_offline() is False


# ==================== Timeout ====================

class TestTimeoutErrors:
    """Timeout → offline после исчерпания retry."""

    def test_timeout_marks_offline(self, api):
        """Timeout → клиент переходит в offline."""
        api.session.request = MagicMock(side_effect=ReqTimeout("read timed out"))

        with pytest.raises(APITimeoutError):
            api._request("GET", f"{api.base_url}/api/test")

        assert api.is_online is False

    def test_timeout_retries_with_backoff(self, api):
        """Timeout → retry с exponential backoff."""
        api.session.request = MagicMock(side_effect=ReqTimeout("timed out"))

        start = time.time()
        with pytest.raises(APITimeoutError):
            api._request("GET", f"{api.base_url}/api/test")
        elapsed = time.time() - start

        # Должно быть хотя бы 1 задержка между попытками
        assert elapsed > api.RETRY_DELAY * 0.5  # С учётом jitter

    def test_no_retry_when_disabled(self, api):
        """retry=False → одна попытка без повтора."""
        api.session.request = MagicMock(side_effect=ReqTimeout("timed out"))

        with pytest.raises(APITimeoutError):
            api._request("GET", f"{api.base_url}/api/test", retry=False)

        assert api.session.request.call_count == 1


# ==================== Offline кеш ====================

class TestOfflineCache:
    """Кеш offline статуса — не долбим сервер сразу после сбоя."""

    def test_recently_offline_skips_requests(self, api):
        """Запросы в пределах OFFLINE_CACHE_DURATION пропускаются."""
        api._mark_offline()

        with pytest.raises(APIConnectionError, match="Offline режим.*кеш"):
            api._request("GET", f"{api.base_url}/api/test")

    def test_offline_cache_expires(self, api):
        """После истечения OFFLINE_CACHE_DURATION — кеш сбрасывается."""
        api.OFFLINE_CACHE_DURATION = 0.1  # 100ms
        api._mark_offline()

        time.sleep(0.15)

        assert api._is_recently_offline() is False

    def test_login_bypasses_offline_cache(self, api):
        """Логин всегда пытается подключиться (не использует кеш)."""
        api._mark_offline()

        # Мокаем session.request для login endpoint
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test"}
        api.session.request = MagicMock(return_value=mock_response)

        # Login endpoint должен пройти через кеш
        result = api._request("POST", f"{api.base_url}/api/v1/auth/login")
        assert result.status_code == 200

    def test_set_offline_mode_prevents_all_requests(self, api):
        """set_offline_mode(True) → долгий offline кеш (24ч)."""
        api.set_offline_mode(True)

        assert api.is_online is False
        assert api._is_recently_offline() is True

        # Даже через секунду кеш активен (установлен на 24 часа)
        assert api._is_recently_offline() is True


# ==================== Восстановление соединения ====================

class TestConnectionRecovery:
    """Восстановление online после offline периода."""

    def test_successful_request_clears_offline(self, api):
        """Успешный запрос → online, кеш сброшен."""
        api._mark_offline()
        assert api.is_online is False

        # Мокаем успешный ответ
        mock_response = MagicMock()
        mock_response.status_code = 200
        api.session.request = MagicMock(return_value=mock_response)

        # Сбрасываем кеш чтобы запрос прошёл
        api.reset_offline_cache()
        result = api._request("GET", f"{api.base_url}/api/test")

        assert api.is_online is True
        assert api._is_recently_offline() is False

    def test_force_online_check_success(self, api):
        """force_online_check() → True при доступном сервере."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        api.session.get = MagicMock(return_value=mock_response)

        api._mark_offline()
        result = api.force_online_check()

        assert result is True
        assert api.is_online is True

    def test_force_online_check_failure(self, api):
        """force_online_check() → False при недоступном сервере."""
        api.session.get = MagicMock(side_effect=ReqConnectionError("refused"))

        result = api.force_online_check()

        assert result is False
        assert api.is_online is False

    def test_force_online_check_bypasses_cache(self, api):
        """force_online_check() игнорирует offline кеш."""
        api._mark_offline()
        assert api._is_recently_offline() is True

        mock_response = MagicMock()
        mock_response.status_code = 200
        api.session.get = MagicMock(return_value=mock_response)

        result = api.force_online_check()
        assert result is True

    def test_reset_offline_cache_allows_requests(self, api):
        """reset_offline_cache() → запросы снова проходят."""
        api._mark_offline()

        # Без reset — запросы блокированы
        assert api._is_recently_offline() is True

        api.reset_offline_cache()

        # После reset — кеш сброшен
        assert api._is_recently_offline() is False

    def test_recovery_cycle_offline_to_online(self, api):
        """Полный цикл: online → ошибка → offline → recovery → online."""
        # 1. Начальное состояние: online
        assert api.is_online is True

        # 2. Сетевая ошибка → offline
        api.session.request = MagicMock(
            side_effect=ReqConnectionError("refused")
        )
        with pytest.raises(APIConnectionError):
            api._request("GET", f"{api.base_url}/api/test")
        assert api.is_online is False

        # 3. Запросы блокированы кешем
        with pytest.raises(APIConnectionError, match="Offline режим.*кеш"):
            api._request("GET", f"{api.base_url}/api/other")

        # 4. force_online_check → сервер ожил
        mock_response = MagicMock()
        mock_response.status_code = 200
        api.session.get = MagicMock(return_value=mock_response)

        api.force_online_check()
        assert api.is_online is True

        # 5. reset_offline_cache → запросы снова проходят
        api.reset_offline_cache()

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        api.session.request = MagicMock(return_value=mock_response2)

        result = api._request("GET", f"{api.base_url}/api/test")
        assert result.status_code == 200


# ==================== Retry и backoff ====================

class TestRetryAndBackoff:
    """Retry логика с exponential backoff."""

    def test_retry_on_502(self, api):
        """502 Bad Gateway → retry."""
        responses = [MagicMock(status_code=502), MagicMock(status_code=200)]
        api.session.request = MagicMock(side_effect=responses)

        result = api._request("GET", f"{api.base_url}/api/test")
        assert result.status_code == 200
        assert api.session.request.call_count == 2

    def test_retry_on_503(self, api):
        """503 Service Unavailable → retry."""
        responses = [MagicMock(status_code=503), MagicMock(status_code=200)]
        api.session.request = MagicMock(side_effect=responses)

        result = api._request("GET", f"{api.base_url}/api/test")
        assert result.status_code == 200

    def test_retry_on_504(self, api):
        """504 Gateway Timeout → retry."""
        responses = [MagicMock(status_code=504), MagicMock(status_code=200)]
        api.session.request = MagicMock(side_effect=responses)

        result = api._request("GET", f"{api.base_url}/api/test")
        assert result.status_code == 200

    def test_429_respects_retry_after(self, api):
        """429 Too Many Requests → ждёт Retry-After."""
        response_429 = MagicMock(status_code=429)
        response_429.headers = {"Retry-After": "0.01"}  # 10ms
        response_200 = MagicMock(status_code=200)

        api.session.request = MagicMock(side_effect=[response_429, response_200])

        result = api._request("GET", f"{api.base_url}/api/test")
        assert result.status_code == 200

    def test_calc_backoff_exponential(self, api):
        """Backoff растёт экспоненциально."""
        b0 = api._calc_backoff(0)
        b1 = api._calc_backoff(1)
        b2 = api._calc_backoff(2)

        # С учётом jitter ±25%, но в среднем должно расти
        assert b1 > b0 * 0.5  # b1 ≈ 2*b0
        assert b2 > b1 * 0.5  # b2 ≈ 2*b1

    def test_backoff_capped_at_max(self, api):
        """Backoff не превышает RETRY_MAX_DELAY (+ min floor 0.1)."""
        # _calc_backoff имеет max(0.1, ...) — нижний предел 0.1с
        max_possible = max(api.RETRY_MAX_DELAY, 0.1) * 1.3  # С учётом jitter
        for attempt in range(10):
            delay = api._calc_backoff(attempt)
            assert delay <= max_possible

    def test_transient_error_then_success(self, api):
        """Одна ошибка → retry → успех (не переходит в offline)."""
        responses = [
            ReqConnectionError("temporary glitch"),
            MagicMock(status_code=200),
        ]

        call_count = [0]
        def side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if isinstance(responses[idx], Exception):
                raise responses[idx]
            return responses[idx]

        api.session.request = MagicMock(side_effect=side_effect)

        result = api._request("GET", f"{api.base_url}/api/test")
        assert result.status_code == 200
        assert api.is_online is True  # Не перешёл в offline


# ==================== Потокобезопасность ====================

class TestThreadSafety:
    """Потокобезопасность offline-статуса."""

    def test_mark_offline_is_thread_safe(self, api):
        """_mark_offline использует lock."""
        import threading

        errors = []

        def mark_offline():
            try:
                for _ in range(100):
                    api._mark_offline()
                    api.reset_offline_cache()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=mark_offline) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []

    def test_is_online_property_thread_safe(self, api):
        """is_online property использует lock."""
        import threading

        results = []

        def check_online():
            for _ in range(100):
                results.append(api.is_online)

        threads = [threading.Thread(target=check_online) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 400
        assert all(isinstance(r, bool) for r in results)


# ==================== SyncManager offline-поведение ====================

class TestSyncManagerResilience:
    """SyncManager корректно работает при offline."""

    @pytest.fixture
    def qapp(self):
        """QApplication для тестов с QTimer."""
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        yield app

    @pytest.fixture
    def mock_api_client(self):
        """Мок API клиента для SyncManager."""
        api = MagicMock()
        api.base_url = "https://test.example.com"
        api.is_online = True
        api._request = MagicMock()
        return api

    @pytest.fixture
    def sync_manager(self, qapp, mock_api_client):
        """SyncManager с мок API."""
        from utils.sync_manager import SyncManager
        sm = SyncManager(mock_api_client, employee_id=1)
        yield sm
        sm.stop()

    def test_heartbeat_skipped_when_offline(self, sync_manager, mock_api_client):
        """Heartbeat пропускается когда API offline."""
        mock_api_client.is_online = False

        sync_manager._send_heartbeat()

        mock_api_client._request.assert_not_called()

    def test_sync_skipped_when_offline(self, sync_manager, mock_api_client):
        """Sync пропускается когда API offline."""
        mock_api_client.is_online = False
        sync_manager.last_sync_timestamp = MagicMock()

        sync_manager._sync_data()

        mock_api_client.sync.assert_not_called()

    def test_sync_skipped_when_paused(self, sync_manager, mock_api_client):
        """Sync пропускается когда на паузе."""
        sync_manager.last_sync_timestamp = MagicMock()
        sync_manager.pause_sync()

        sync_manager._sync_data()

        mock_api_client.sync.assert_not_called()

    def test_connection_lost_emits_signal(self, sync_manager, mock_api_client):
        """Ошибка sync → connection_status_changed(False)."""
        sync_manager.is_connected = True

        # Вызываем обработчик ошибки синхронизации
        signals = []
        sync_manager.connection_status_changed.connect(lambda s: signals.append(s))

        sync_manager._on_sync_error()

        assert sync_manager.is_connected is False
        assert signals == [False]

    def test_heartbeat_no_api_client_no_crash(self, qapp):
        """Heartbeat без api_client → не падает."""
        from utils.sync_manager import SyncManager
        sm = SyncManager(None, employee_id=1)
        sm._send_heartbeat()  # Не должен упасть
        sm.stop()


# ==================== Offline → Online интеграция ====================

class TestOfflineOnlineIntegration:
    """Интеграционные тесты: APIClientBase + offline/online цикл."""

    def test_multiple_errors_then_recovery(self, api):
        """Множественные ошибки → offline → recovery → все запросы проходят."""
        # 1. Несколько разных сетевых ошибок
        errors = [
            ReqSSLError("SSL EOF"),
            ReqConnectionError("refused"),
            ReqTimeout("timed out"),
        ]
        for error_cls in errors:
            api.session.request = MagicMock(side_effect=error_cls)
            api.reset_offline_cache()
            try:
                api._request("GET", f"{api.base_url}/api/test")
            except (APIConnectionError, APITimeoutError):
                pass

        assert api.is_online is False

        # 2. Сервер вернулся
        mock_ok = MagicMock()
        mock_ok.status_code = 200
        api.session.get = MagicMock(return_value=mock_ok)
        api.force_online_check()

        assert api.is_online is True

        # 3. Запросы проходят
        api.reset_offline_cache()
        api.session.request = MagicMock(return_value=mock_ok)
        result = api._request("GET", f"{api.base_url}/api/test")
        assert result.status_code == 200

    def test_offline_message_shown_only_once(self, api, capsys):
        """Сообщение 'Переход в offline' показывается один раз."""
        api.session.request = MagicMock(
            side_effect=ReqConnectionError("refused")
        )

        # Первая ошибка
        with pytest.raises(APIConnectionError):
            api._request("GET", f"{api.base_url}/api/test")

        # Сбрасываем кеш для второй ошибки
        api._last_offline_time = None
        api._is_online = True  # Но не сбрасываем _offline_message_shown

        # Ещё раз пометить offline — сообщение не повторяется
        api._mark_offline()
        api._mark_offline()

        captured = capsys.readouterr()
        assert captured.out.count("Переход в offline") <= 1

    def test_write_timeout_longer_than_read(self, api):
        """POST/PUT/PATCH/DELETE используют увеличенный таймаут."""
        api._first_request = False  # Не первый запрос

        mock_response = MagicMock()
        mock_response.status_code = 200
        api.session.request = MagicMock(return_value=mock_response)

        # GET — DEFAULT_TIMEOUT
        api._request("GET", f"{api.base_url}/api/test")
        _, kwargs = api.session.request.call_args
        assert kwargs['timeout'] == api.DEFAULT_TIMEOUT

        # POST — WRITE_TIMEOUT
        api._request("POST", f"{api.base_url}/api/test")
        _, kwargs = api.session.request.call_args
        assert kwargs['timeout'] == api.WRITE_TIMEOUT
