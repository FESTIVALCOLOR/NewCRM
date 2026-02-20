# -*- coding: utf-8 -*-
"""
Unit-тесты APIClient — retry, timeout, offline, session management
"""
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import requests

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.api_client import (
    APIClient, APIError, APITimeoutError,
    APIConnectionError, APIAuthError, APIResponseError
)


# ============================================================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================================================

class TestAPIClientInit:
    """Инициализация APIClient"""

    def test_base_url_stripped(self):
        client = APIClient("http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"

    def test_default_state(self):
        client = APIClient("http://localhost:8000")
        assert client.token is None
        assert client.employee_id is None
        assert client._is_online is True
        assert client._first_request is True
        assert client.verify_ssl is False

    def test_session_created(self):
        client = APIClient("http://localhost:8000")
        assert isinstance(client.session, requests.Session)
        assert client.session.trust_env is False

    def test_custom_verify_ssl(self):
        client = APIClient("http://localhost:8000", verify_ssl=True)
        assert client.verify_ssl is True


# ============================================================================
# TIMEOUT LOGIC
# ============================================================================

class TestTimeoutLogic:
    """Выбор таймаута в зависимости от типа запроса"""

    def test_first_request_timeout(self):
        client = APIClient("http://test:8000")
        client._first_request = True
        # Mock session.request to capture kwargs
        with patch.object(client.session, 'request') as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_req.return_value = mock_resp
            client._request('GET', 'http://test:8000/health')
            _, kwargs = mock_req.call_args
            assert kwargs['timeout'] == client.FIRST_REQUEST_TIMEOUT

    def test_read_timeout(self):
        client = APIClient("http://test:8000")
        client._first_request = False
        with patch.object(client.session, 'request') as mock_req:
            mock_resp = MagicMock()
            mock_req.return_value = mock_resp
            client._request('GET', 'http://test:8000/api/clients')
            _, kwargs = mock_req.call_args
            assert kwargs['timeout'] == client.DEFAULT_TIMEOUT

    def test_write_timeout_post(self):
        client = APIClient("http://test:8000")
        client._first_request = False
        with patch.object(client.session, 'request') as mock_req:
            mock_resp = MagicMock()
            mock_req.return_value = mock_resp
            client._request('POST', 'http://test:8000/api/clients')
            _, kwargs = mock_req.call_args
            assert kwargs['timeout'] == client.WRITE_TIMEOUT

    def test_write_timeout_put(self):
        client = APIClient("http://test:8000")
        client._first_request = False
        with patch.object(client.session, 'request') as mock_req:
            mock_resp = MagicMock()
            mock_req.return_value = mock_resp
            client._request('PUT', 'http://test:8000/api/clients/1')
            _, kwargs = mock_req.call_args
            assert kwargs['timeout'] == client.WRITE_TIMEOUT

    def test_write_timeout_delete(self):
        client = APIClient("http://test:8000")
        client._first_request = False
        with patch.object(client.session, 'request') as mock_req:
            mock_resp = MagicMock()
            mock_req.return_value = mock_resp
            client._request('DELETE', 'http://test:8000/api/clients/1')
            _, kwargs = mock_req.call_args
            assert kwargs['timeout'] == client.WRITE_TIMEOUT

    def test_custom_timeout_overrides(self):
        client = APIClient("http://test:8000")
        with patch.object(client.session, 'request') as mock_req:
            mock_resp = MagicMock()
            mock_req.return_value = mock_resp
            client._request('GET', 'http://test:8000/api/clients', timeout=30)
            _, kwargs = mock_req.call_args
            assert kwargs['timeout'] == 30


# ============================================================================
# RETRY LOGIC
# ============================================================================

class TestRetryLogic:
    """Retry при временных ошибках"""

    def test_retry_on_timeout(self):
        client = APIClient("http://test:8000")
        client.RETRY_DELAY = 0.01  # Быстрый retry для тестов
        with patch.object(client.session, 'request') as mock_req:
            mock_req.side_effect = requests.exceptions.Timeout("timeout")
            with pytest.raises(APITimeoutError):
                client._request('GET', 'http://test:8000/api/test')
            assert mock_req.call_count == client.MAX_RETRIES

    def test_retry_on_connection_error(self):
        client = APIClient("http://test:8000")
        client.RETRY_DELAY = 0.01
        with patch.object(client.session, 'request') as mock_req:
            mock_req.side_effect = requests.exceptions.ConnectionError("refused")
            with pytest.raises(APIConnectionError):
                client._request('GET', 'http://test:8000/api/test')
            assert mock_req.call_count == client.MAX_RETRIES

    def test_no_retry_when_disabled(self):
        client = APIClient("http://test:8000")
        with patch.object(client.session, 'request') as mock_req:
            mock_req.side_effect = requests.exceptions.Timeout("timeout")
            with pytest.raises(APITimeoutError):
                client._request('GET', 'http://test:8000/api/test', retry=False)
            assert mock_req.call_count == 1

    def test_retry_succeeds_on_second_attempt(self):
        client = APIClient("http://test:8000")
        client.RETRY_DELAY = 0.01
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(client.session, 'request') as mock_req:
            mock_req.side_effect = [
                requests.exceptions.Timeout("timeout"),
                mock_resp,
            ]
            result = client._request('GET', 'http://test:8000/api/test')
            assert result == mock_resp
            assert mock_req.call_count == 2


# ============================================================================
# OFFLINE LOGIC
# ============================================================================

class TestOfflineLogic:
    """Управление offline статусом"""

    def test_marks_offline_on_timeout(self):
        client = APIClient("http://test:8000")
        client.RETRY_DELAY = 0.01
        with patch.object(client.session, 'request') as mock_req:
            mock_req.side_effect = requests.exceptions.Timeout("timeout")
            with pytest.raises(APITimeoutError):
                client._request('GET', 'http://test:8000/api/test')
        assert client._is_online is False

    def test_marks_offline_on_connection_error(self):
        client = APIClient("http://test:8000")
        client.RETRY_DELAY = 0.01
        with patch.object(client.session, 'request') as mock_req:
            mock_req.side_effect = requests.exceptions.ConnectionError("refused")
            with pytest.raises(APIConnectionError):
                client._request('GET', 'http://test:8000/api/test')
        assert client._is_online is False

    def test_does_not_mark_offline_when_disabled(self):
        client = APIClient("http://test:8000")
        client.RETRY_DELAY = 0.01
        with patch.object(client.session, 'request') as mock_req:
            mock_req.side_effect = requests.exceptions.Timeout("timeout")
            with pytest.raises(APITimeoutError):
                client._request('GET', 'http://test:8000/api/test', mark_offline=False)
        # mark_offline=False still sets _is_online=False in the final fallthrough
        # but does NOT set _last_offline_time through _mark_offline()
        assert client._last_offline_time is None

    def test_recently_offline_skips_request(self):
        client = APIClient("http://test:8000")
        client._last_offline_time = time.time()  # Just went offline
        with patch.object(client.session, 'request') as mock_req:
            with pytest.raises(APIConnectionError, match="Offline"):
                client._request('GET', 'http://test:8000/api/test')
            mock_req.assert_not_called()  # No actual request made

    def test_offline_cache_expires(self):
        client = APIClient("http://test:8000")
        # Set offline time in the past, beyond cache duration
        client._last_offline_time = time.time() - client.OFFLINE_CACHE_DURATION - 1
        assert client._is_recently_offline() is False

    def test_reset_offline_cache(self):
        client = APIClient("http://test:8000")
        client._last_offline_time = time.time()
        client._offline_message_shown = True
        client.reset_offline_cache()
        assert client._last_offline_time is None
        assert client._offline_message_shown is False

    def test_set_offline_mode(self):
        client = APIClient("http://test:8000")
        client.set_offline_mode(True)
        assert client._is_online is False
        assert client._last_offline_time is not None

    def test_set_online_mode(self):
        client = APIClient("http://test:8000")
        client._is_online = False
        client._last_offline_time = time.time()
        client.set_offline_mode(False)
        assert client._is_online is True
        assert client._last_offline_time is None

    def test_successful_request_resets_offline(self):
        client = APIClient("http://test:8000")
        client._is_online = False
        client._last_offline_time = None  # Allow request through
        with patch.object(client.session, 'request') as mock_req:
            mock_resp = MagicMock()
            mock_req.return_value = mock_resp
            client._request('GET', 'http://test:8000/health')
        assert client._is_online is True
        assert client._first_request is False


# ============================================================================
# EXCEPTION CLASSES
# ============================================================================

class TestExceptions:
    """Проверка иерархии исключений"""

    def test_api_timeout_is_api_error(self):
        assert issubclass(APITimeoutError, APIError)

    def test_api_connection_is_api_error(self):
        assert issubclass(APIConnectionError, APIError)

    def test_api_auth_is_api_error(self):
        assert issubclass(APIAuthError, APIError)

    def test_api_response_error_has_status_code(self):
        err = APIResponseError("Not found", status_code=404)
        assert err.status_code == 404
        assert "Not found" in str(err)

    def test_api_response_error_default_status(self):
        err = APIResponseError("Error")
        assert err.status_code is None


# ============================================================================
# SESSION REUSE
# ============================================================================

class TestSessionReuse:
    """Переиспользование requests.Session"""

    def test_session_is_persistent(self):
        client = APIClient("http://test:8000")
        session1 = client.session
        # Same session object on second access
        assert client.session is session1

    def test_session_trust_env_disabled(self):
        """trust_env=False отключает прокси из env (VPN/Clash)"""
        client = APIClient("http://test:8000")
        assert client.session.trust_env is False

    def test_multiple_requests_use_same_session(self):
        client = APIClient("http://test:8000")
        with patch.object(client.session, 'request') as mock_req:
            mock_resp = MagicMock()
            mock_req.return_value = mock_resp
            client._request('GET', 'http://test:8000/api/a')
            client._request('GET', 'http://test:8000/api/b')
            assert mock_req.call_count == 2
