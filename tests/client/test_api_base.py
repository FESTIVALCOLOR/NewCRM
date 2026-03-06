# -*- coding: utf-8 -*-
"""
Тесты для utils/api_client/base.py — APIClientBase + exceptions.

Покрытие:
- __init__ (инициализация, сессия, адаптеры)
- _request (retry, timeout, backoff, offline кеш, 401/429/5xx)
- _handle_response (success, ошибки)
- Token management (set_token, clear_token, JWT parse, auto-refresh)
- Offline mode (mark_offline, reset, force_online_check)
- _AuthSession (redirect auth preservation)
- Exceptions hierarchy
"""
import pytest
import sys
import os
import time
import json
import base64
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.api_client.base import APIClientBase, _AuthSession
from utils.api_client.exceptions import (
    APIError, APITimeoutError, APIConnectionError, APIAuthError, APIResponseError
)


# ==================== Exceptions ====================

class TestExceptions:
    """Иерархия исключений."""

    def test_api_error_is_exception(self):
        assert issubclass(APIError, Exception)

    def test_timeout_is_api_error(self):
        assert issubclass(APITimeoutError, APIError)

    def test_connection_is_api_error(self):
        assert issubclass(APIConnectionError, APIError)

    def test_auth_is_api_error(self):
        assert issubclass(APIAuthError, APIError)

    def test_response_is_api_error(self):
        assert issubclass(APIResponseError, APIError)

    def test_response_error_has_status_code(self):
        err = APIResponseError("test", status_code=404)
        assert err.status_code == 404

    def test_response_error_no_status_code(self):
        err = APIResponseError("test")
        assert err.status_code is None

    def test_api_error_message(self):
        err = APIError("test message")
        assert str(err) == "test message"


# ==================== __init__ ====================

class TestAPIClientInit:
    """Инициализация APIClientBase."""

    def test_base_url_stripped(self):
        client = APIClientBase("https://example.com/")
        assert client.base_url == "https://example.com"

    def test_default_timeout_values(self):
        client = APIClientBase("https://example.com")
        assert client.DEFAULT_TIMEOUT == 10
        assert client.WRITE_TIMEOUT == 15
        assert client.FIRST_REQUEST_TIMEOUT == 10

    def test_initial_state_online(self):
        client = APIClientBase("https://example.com")
        assert client.is_online is True

    def test_initial_token_none(self):
        client = APIClientBase("https://example.com")
        assert client.token is None
        assert client.refresh_token is None

    def test_content_type_header(self):
        client = APIClientBase("https://example.com")
        assert client.headers["Content-Type"] == "application/json"

    def test_session_created(self):
        client = APIClientBase("https://example.com")
        assert isinstance(client.session, _AuthSession)

    def test_verify_ssl_default_false(self):
        client = APIClientBase("https://example.com")
        assert client.verify_ssl is False

    def test_verify_ssl_custom(self):
        client = APIClientBase("https://example.com", verify_ssl=True)
        assert client.verify_ssl is True

    def test_first_request_flag(self):
        client = APIClientBase("https://example.com")
        assert client._first_request is True

    def test_max_retries(self):
        client = APIClientBase("https://example.com")
        assert client.MAX_RETRIES == 3


# ==================== Token Management ====================

class TestTokenManagement:
    """set_token, clear_token, JWT extraction."""

    def test_set_token(self):
        client = APIClientBase("https://example.com")
        client.set_token("test_token")
        assert client.token == "test_token"
        assert client.headers["Authorization"] == "Bearer test_token"

    def test_set_token_with_refresh(self):
        client = APIClientBase("https://example.com")
        client.set_token("access", "refresh")
        assert client.token == "access"
        assert client.refresh_token == "refresh"

    def test_clear_token(self):
        client = APIClientBase("https://example.com")
        client.set_token("test_token", "refresh")
        client.clear_token()
        assert client.token is None
        assert client.refresh_token is None
        assert "Authorization" not in client.headers

    def test_clear_token_when_no_token(self):
        """clear_token без токена — не падает."""
        client = APIClientBase("https://example.com")
        client.clear_token()  # Не должно упасть

    def test_extract_token_expiry_valid_jwt(self):
        """Извлечение exp из валидного JWT."""
        client = APIClientBase("https://example.com")
        # Создаём минимальный JWT: header.payload.signature
        payload = {"sub": "1", "exp": 9999999999}
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b'=').decode()
        header_b64 = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256"}).encode()
        ).rstrip(b'=').decode()
        token = f"{header_b64}.{payload_b64}.fake_signature"
        exp = client._extract_token_expiry(token)
        assert exp == 9999999999

    def test_extract_token_expiry_invalid(self):
        client = APIClientBase("https://example.com")
        assert client._extract_token_expiry("invalid") is None

    def test_extract_token_expiry_no_exp(self):
        client = APIClientBase("https://example.com")
        payload = {"sub": "1"}
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b'=').decode()
        header_b64 = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256"}).encode()
        ).rstrip(b'=').decode()
        token = f"{header_b64}.{payload_b64}.sig"
        exp = client._extract_token_expiry(token)
        assert exp is None

    def test_is_token_expiring_soon_no_exp(self):
        client = APIClientBase("https://example.com")
        client._token_exp = None
        assert client._is_token_expiring_soon() is False

    def test_is_token_expiring_soon_far(self):
        client = APIClientBase("https://example.com")
        client._token_exp = time.time() + 3600  # через час
        assert client._is_token_expiring_soon() is False

    def test_is_token_expiring_soon_close(self):
        client = APIClientBase("https://example.com")
        client._token_exp = time.time() + 60  # через минуту (< 300 threshold)
        assert client._is_token_expiring_soon() is True

    def test_set_relogin_callback(self):
        client = APIClientBase("https://example.com")
        cb = MagicMock()
        client.set_relogin_callback(cb)
        assert client._relogin_callback == cb

    def test_signal_relogin_needed_calls_callback(self):
        client = APIClientBase("https://example.com")
        cb = MagicMock(return_value=True)
        client._relogin_callback = cb
        client._signal_relogin_needed()
        cb.assert_called_once()

    def test_signal_relogin_not_repeated(self):
        """Повторный вызов — callback не вызывается."""
        client = APIClientBase("https://example.com")
        cb = MagicMock(return_value=False)
        client._relogin_callback = cb
        client._signal_relogin_needed()
        client._signal_relogin_needed()
        cb.assert_called_once()


# ==================== Offline Mode ====================

class TestOfflineMode:
    """Offline mode management."""

    def test_mark_offline(self):
        client = APIClientBase("https://example.com")
        client._mark_offline()
        assert client.is_online is False
        assert client._last_offline_time is not None

    def test_is_recently_offline_false_initially(self):
        client = APIClientBase("https://example.com")
        assert client._is_recently_offline() is False

    def test_is_recently_offline_after_mark(self):
        client = APIClientBase("https://example.com")
        client._mark_offline()
        assert client._is_recently_offline() is True

    def test_reset_offline_cache(self):
        client = APIClientBase("https://example.com")
        client._mark_offline()
        client.reset_offline_cache()
        assert client._is_recently_offline() is False

    def test_set_offline_mode_true(self):
        client = APIClientBase("https://example.com")
        client.set_offline_mode(True)
        assert client.is_online is False

    def test_set_offline_mode_false(self):
        client = APIClientBase("https://example.com")
        client.set_offline_mode(True)
        client.set_offline_mode(False)
        assert client.is_online is True

    def test_force_online_check_success(self):
        client = APIClientBase("https://example.com")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(client.session, 'get', return_value=mock_resp):
            result = client.force_online_check()
        assert result is True
        assert client.is_online is True

    def test_force_online_check_failure(self):
        client = APIClientBase("https://example.com")
        with patch.object(client.session, 'get', side_effect=Exception("conn error")):
            result = client.force_online_check()
        assert result is False
        assert client.is_online is False

    def test_force_online_check_non_200(self):
        client = APIClientBase("https://example.com")
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        with patch.object(client.session, 'get', return_value=mock_resp):
            result = client.force_online_check()
        assert result is False


# ==================== _calc_backoff ====================

class TestCalcBackoff:
    """Exponential backoff с jitter."""

    def test_backoff_increases(self):
        client = APIClientBase("https://example.com")
        delays = [client._calc_backoff(i) for i in range(3)]
        # Средние: 0.5, 1.0, 2.0 — с jitter каждый >= 0.1
        assert all(d >= 0.1 for d in delays)

    def test_backoff_has_jitter(self):
        """Два вызова с тем же attempt дают разные значения (jitter)."""
        client = APIClientBase("https://example.com")
        values = set()
        for _ in range(10):
            values.add(round(client._calc_backoff(0), 6))
        # С jitter ±25% маловероятно 10 одинаковых
        assert len(values) > 1

    def test_backoff_max_cap(self):
        """Backoff не превышает RETRY_MAX_DELAY."""
        client = APIClientBase("https://example.com")
        delay = client._calc_backoff(100)
        assert delay <= client.RETRY_MAX_DELAY * (1 + client.RETRY_JITTER) + 0.1


# ==================== _parse_retry_after ====================

class TestParseRetryAfter:
    """Парсинг Retry-After заголовка."""

    def test_numeric_value(self):
        resp = MagicMock()
        resp.headers = {'Retry-After': '5'}
        assert APIClientBase._parse_retry_after(resp) == 5.0

    def test_float_value(self):
        resp = MagicMock()
        resp.headers = {'Retry-After': '1.5'}
        assert APIClientBase._parse_retry_after(resp) == 1.5

    def test_missing_header(self):
        resp = MagicMock()
        resp.headers = {}
        assert APIClientBase._parse_retry_after(resp) is None

    def test_invalid_value(self):
        resp = MagicMock()
        resp.headers = {'Retry-After': 'invalid'}
        assert APIClientBase._parse_retry_after(resp) is None


# ==================== _handle_response ====================

class TestHandleResponse:
    """Обработка ответов сервера."""

    def test_success_200_json(self):
        client = APIClientBase("https://example.com")
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"id": 1, "name": "test"}
        result = client._handle_response(resp)
        assert result == {"id": 1, "name": "test"}

    def test_success_custom_code(self):
        client = APIClientBase("https://example.com")
        resp = MagicMock()
        resp.status_code = 201
        resp.json.return_value = {"id": 2}
        result = client._handle_response(resp, success_codes=[200, 201])
        assert result == {"id": 2}

    def test_success_no_json(self):
        """Ответ без JSON → True."""
        client = APIClientBase("https://example.com")
        resp = MagicMock()
        resp.status_code = 200
        resp.json.side_effect = ValueError("No JSON")
        result = client._handle_response(resp)
        assert result is True

    def test_error_401(self):
        client = APIClientBase("https://example.com")
        resp = MagicMock()
        resp.status_code = 401
        resp.headers = {'content-type': 'application/json'}
        resp.json.return_value = {'detail': 'Unauthorized'}
        with pytest.raises(APIAuthError):
            client._handle_response(resp)

    def test_error_403(self):
        client = APIClientBase("https://example.com")
        resp = MagicMock()
        resp.status_code = 403
        resp.headers = {'content-type': 'application/json'}
        resp.json.return_value = {'detail': 'Forbidden'}
        with pytest.raises(APIAuthError, match="Forbidden"):
            client._handle_response(resp)

    def test_error_429(self):
        client = APIClientBase("https://example.com")
        resp = MagicMock()
        resp.status_code = 429
        resp.headers = {'content-type': 'application/json'}
        resp.json.return_value = {'detail': 'Too many requests'}
        with pytest.raises(APIResponseError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.status_code == 429

    def test_error_500(self):
        client = APIClientBase("https://example.com")
        resp = MagicMock()
        resp.status_code = 500
        resp.headers = {'content-type': 'text/plain'}
        resp.text = 'Internal Server Error'
        with pytest.raises(APIResponseError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.status_code == 500


# ==================== _extract_error_detail ====================

class TestExtractErrorDetail:
    """Извлечение деталей ошибки."""

    def test_json_dict_detail(self):
        client = APIClientBase("https://example.com")
        resp = MagicMock()
        resp.headers = {'content-type': 'application/json'}
        resp.json.return_value = {'detail': 'Not found'}
        assert client._extract_error_detail(resp) == 'Not found'

    def test_json_list(self):
        client = APIClientBase("https://example.com")
        resp = MagicMock()
        resp.headers = {'content-type': 'application/json'}
        resp.json.return_value = [{'error': 'msg'}]
        result = client._extract_error_detail(resp)
        assert 'error' in result

    def test_text_fallback(self):
        client = APIClientBase("https://example.com")
        resp = MagicMock()
        resp.headers = {'content-type': 'text/plain'}
        resp.text = 'Error text'
        assert client._extract_error_detail(resp) == 'Error text'

    def test_empty_text(self):
        client = APIClientBase("https://example.com")
        resp = MagicMock()
        resp.headers = {'content-type': 'text/plain'}
        resp.text = ''
        assert client._extract_error_detail(resp) == 'Неизвестная ошибка'


# ==================== _request ====================

class TestRequest:
    """_request — HTTP запросы с retry и обработкой ошибок."""

    def test_successful_get(self):
        client = APIClientBase("https://example.com")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(client.session, 'request', return_value=mock_resp):
            result = client._request('GET', 'https://example.com/api/test')
        assert result == mock_resp
        assert client.is_online is True

    def test_timeout_raises(self):
        import requests
        client = APIClientBase("https://example.com")
        with patch.object(client.session, 'request',
                          side_effect=requests.exceptions.Timeout("timeout")):
            with pytest.raises(APITimeoutError):
                client._request('GET', 'https://example.com/api/test', retry=False)

    def test_connection_error_raises(self):
        import requests
        client = APIClientBase("https://example.com")
        with patch.object(client.session, 'request',
                          side_effect=requests.exceptions.ConnectionError("conn")):
            with pytest.raises(APIConnectionError):
                client._request('GET', 'https://example.com/api/test', retry=False)

    def test_offline_cache_skips_request(self):
        """Если недавно были offline — сразу APIConnectionError."""
        client = APIClientBase("https://example.com")
        client._mark_offline()
        with pytest.raises(APIConnectionError, match="Offline"):
            client._request('GET', 'https://example.com/api/test')

    def test_login_bypasses_offline_cache(self):
        """Login запрос проходит даже в offline режиме."""
        client = APIClientBase("https://example.com")
        client._mark_offline()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(client.session, 'request', return_value=mock_resp):
            result = client._request('GET', 'https://example.com/api/v1/auth/login')
        assert result == mock_resp

    def test_write_timeout_for_post(self):
        """POST использует WRITE_TIMEOUT."""
        client = APIClientBase("https://example.com")
        client._first_request = False
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(client.session, 'request', return_value=mock_resp) as mock_req:
            client._request('POST', 'https://example.com/api/test')
        _, kwargs = mock_req.call_args
        assert kwargs['timeout'] == client.WRITE_TIMEOUT

    def test_first_request_timeout(self):
        """Первый запрос использует FIRST_REQUEST_TIMEOUT."""
        client = APIClientBase("https://example.com")
        assert client._first_request is True
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(client.session, 'request', return_value=mock_resp) as mock_req:
            client._request('GET', 'https://example.com/api/test')
        _, kwargs = mock_req.call_args
        assert kwargs['timeout'] == client.FIRST_REQUEST_TIMEOUT
        # После первого запроса флаг сбрасывается
        assert client._first_request is False

    def test_retry_on_502(self):
        """502 → retry с backoff."""
        import requests as req_lib
        client = APIClientBase("https://example.com")
        resp_502 = MagicMock()
        resp_502.status_code = 502
        resp_200 = MagicMock()
        resp_200.status_code = 200
        with patch.object(client.session, 'request',
                          side_effect=[resp_502, resp_200]), \
             patch.object(client, '_calc_backoff', return_value=0.001):
            result = client._request('GET', 'https://example.com/api/test')
        assert result.status_code == 200

    def test_retry_on_429_with_header(self):
        """429 + Retry-After → ожидание и retry."""
        client = APIClientBase("https://example.com")
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.headers = {'Retry-After': '0.001'}
        resp_200 = MagicMock()
        resp_200.status_code = 200
        with patch.object(client.session, 'request',
                          side_effect=[resp_429, resp_200]):
            result = client._request('GET', 'https://example.com/api/test')
        assert result.status_code == 200

    def test_mark_offline_false_skips(self):
        """mark_offline=False — не помечает как offline."""
        import requests
        client = APIClientBase("https://example.com")
        with patch.object(client.session, 'request',
                          side_effect=requests.exceptions.ConnectionError("conn")):
            with pytest.raises(APIConnectionError):
                client._request('GET', 'https://example.com/api/test',
                                retry=False, mark_offline=False)
        # Не помечен offline (last_offline_time не установлен)
        assert client._last_offline_time is None


# ==================== _AuthSession ====================

class TestAuthSession:
    """_AuthSession — сохранение auth при redirect."""

    def test_same_host_preserves_auth(self):
        session = _AuthSession()
        prepared = MagicMock()
        prepared.headers = {'Authorization': 'Bearer token'}
        prepared.url = 'http://example.com/api/test'
        response = MagicMock()
        response.request.url = 'https://example.com/api/test'
        session.rebuild_auth(prepared, response)
        assert 'Authorization' in prepared.headers

    def test_different_host_removes_auth(self):
        session = _AuthSession()
        prepared = MagicMock()
        prepared.headers = {'Authorization': 'Bearer token'}
        prepared.url = 'https://evil.com/steal'
        response = MagicMock()
        response.request.url = 'https://example.com/api'
        session.rebuild_auth(prepared, response)
        assert 'Authorization' not in prepared.headers

    def test_no_auth_header_noop(self):
        """Без Authorization — ничего не делает."""
        session = _AuthSession()
        prepared = MagicMock()
        prepared.headers = {}
        response = MagicMock()
        response.request.url = 'https://example.com'
        session.rebuild_auth(prepared, response)
