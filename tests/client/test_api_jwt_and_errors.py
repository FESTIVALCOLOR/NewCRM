# -*- coding: utf-8 -*-
"""
Тесты edge cases для API клиента:
- JWT lifecycle (set_token, clear_token, expiry parse, auto-refresh)
- Offline mode (mark_offline, reset, force_online_check, offline cache duration)
- Request retry logic (backoff, 429, 502/503/504)
- _handle_response (success, auth errors, response errors)
- _AuthSession (same-host redirect auth preservation)
- Relogin callback chain
- SyncManager edge cases (concurrent sync, process_sync_result, heartbeat)

HIGH criticality — покрывает разрывы логики в авторизации и сетевых ошибках.
"""
import pytest
import sys
import os
import time
import json
import base64
from unittest.mock import MagicMock, patch, PropertyMock, call
import requests.exceptions

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.api_client.base import APIClientBase, _AuthSession
from utils.api_client.exceptions import (
    APIError, APITimeoutError, APIConnectionError, APIAuthError, APIResponseError
)


# ==================== Helpers ====================

def _make_jwt(exp=None, sub="1"):
    """Создать JWT токен с заданным временем истечения."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b'=')
    payload_data = {"sub": sub}
    if exp is not None:
        payload_data["exp"] = exp
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b'=')
    signature = base64.urlsafe_b64encode(b"fake_signature").rstrip(b'=')
    return f"{header.decode()}.{payload.decode()}.{signature.decode()}"


def _make_response(status_code=200, json_data=None, headers=None, text=""):
    """Создать mock Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.headers = headers or {}
    if json_data is not None:
        resp.json.return_value = json_data
        resp.headers.setdefault('content-type', 'application/json')
    else:
        resp.json.side_effect = ValueError("No JSON")
    return resp


# ==================== JWT Token Parsing ====================

class TestJWTTokenParsing:
    """Парсинг JWT токенов — извлечение времени истечения."""

    def test_extract_token_expiry_valid(self):
        client = APIClientBase("https://test.example.com")
        exp_time = int(time.time()) + 3600
        token = _make_jwt(exp=exp_time)
        result = client._extract_token_expiry(token)
        assert result == exp_time

    def test_extract_token_expiry_no_exp(self):
        """Токен без exp — None."""
        client = APIClientBase("https://test.example.com")
        token = _make_jwt(exp=None)
        result = client._extract_token_expiry(token)
        assert result is None

    def test_extract_token_expiry_invalid_format(self):
        """Невалидный формат — None."""
        client = APIClientBase("https://test.example.com")
        assert client._extract_token_expiry("invalid.token") is None

    def test_extract_token_expiry_empty_string(self):
        client = APIClientBase("https://test.example.com")
        assert client._extract_token_expiry("") is None

    def test_extract_token_expiry_garbage(self):
        client = APIClientBase("https://test.example.com")
        assert client._extract_token_expiry("a.b.c") is None


# ==================== set_token / clear_token ====================

class TestTokenManagement:
    """Управление JWT токенами."""

    def test_set_token_sets_header(self):
        client = APIClientBase("https://test.example.com")
        client.set_token("my_token", "my_refresh")
        assert client.token == "my_token"
        assert client.refresh_token == "my_refresh"
        assert client.headers["Authorization"] == "Bearer my_token"

    def test_set_token_extracts_expiry(self):
        client = APIClientBase("https://test.example.com")
        exp = int(time.time()) + 3600
        token = _make_jwt(exp=exp)
        client.set_token(token)
        assert client._token_exp == exp

    def test_set_token_resets_relogin_flag(self):
        client = APIClientBase("https://test.example.com")
        client._relogin_signaled = True
        client.set_token("new_token")
        assert client._relogin_signaled is False

    def test_clear_token(self):
        client = APIClientBase("https://test.example.com")
        client.set_token("token123", "refresh123")
        client.clear_token()
        assert client.token is None
        assert client.refresh_token is None
        assert client._token_exp is None
        assert "Authorization" not in client.headers

    def test_clear_token_no_auth_header(self):
        """clear_token — когда Authorization уже нет."""
        client = APIClientBase("https://test.example.com")
        client.clear_token()  # Не должно упасть


# ==================== Token Expiry Check ====================

class TestTokenExpiryCheck:
    """Проверка истечения токена и auto-refresh."""

    def test_token_not_expiring_soon(self):
        client = APIClientBase("https://test.example.com")
        client._token_exp = time.time() + 3600  # Через 1 час
        assert client._is_token_expiring_soon() is False

    def test_token_expiring_soon(self):
        client = APIClientBase("https://test.example.com")
        client._token_exp = time.time() + 60  # Через 1 минуту (<5 мин)
        assert client._is_token_expiring_soon() is True

    def test_token_already_expired(self):
        client = APIClientBase("https://test.example.com")
        client._token_exp = time.time() - 100  # Истёк
        assert client._is_token_expiring_soon() is True

    def test_no_token_exp_not_expiring(self):
        """Без _token_exp — False (не нужен refresh)."""
        client = APIClientBase("https://test.example.com")
        client._token_exp = None
        assert client._is_token_expiring_soon() is False

    def test_auto_refresh_no_token(self):
        """auto_refresh — без токена не делает ничего."""
        client = APIClientBase("https://test.example.com")
        client.token = None
        client._auto_refresh_if_needed()  # Не должно упасть

    def test_auto_refresh_no_refresh_token(self):
        """auto_refresh — без refresh_token не делает ничего."""
        client = APIClientBase("https://test.example.com")
        client.token = "access"
        client.refresh_token = None
        client._auto_refresh_if_needed()  # Не должно упасть


# ==================== Offline Mode ====================

class TestOfflineMode:
    """Управление offline-статусом."""

    def test_mark_offline(self):
        client = APIClientBase("https://test.example.com")
        assert client.is_online is True
        client._mark_offline()
        assert client.is_online is False
        assert client._last_offline_time is not None

    def test_mark_offline_only_messages_once(self):
        """_mark_offline — сообщение выводится только при первом переходе."""
        client = APIClientBase("https://test.example.com")
        client._mark_offline()
        assert client._offline_message_shown is True
        # Повторный вызов — флаг остаётся True
        client._mark_offline()
        assert client._offline_message_shown is True

    def test_is_recently_offline_true(self):
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = time.time()  # Только что
        assert client._is_recently_offline() is True

    def test_is_recently_offline_false_expired(self):
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = time.time() - 100  # 100 сек назад (>10)
        assert client._is_recently_offline() is False

    def test_is_recently_offline_no_time(self):
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = None
        assert client._is_recently_offline() is False

    def test_reset_offline_cache(self):
        client = APIClientBase("https://test.example.com")
        client._mark_offline()
        client.reset_offline_cache()
        assert client._last_offline_time is None
        assert client._offline_message_shown is False

    def test_set_offline_mode_on(self):
        client = APIClientBase("https://test.example.com")
        client.set_offline_mode(offline=True)
        assert client.is_online is False
        # Время должно быть далеко в будущем (24+ часа)
        assert client._last_offline_time > time.time() + 80000

    def test_set_offline_mode_off(self):
        client = APIClientBase("https://test.example.com")
        client.set_offline_mode(offline=True)
        client.set_offline_mode(offline=False)
        assert client.is_online is True
        assert client._last_offline_time is None

    def test_offline_cache_duration_constant(self):
        assert APIClientBase.OFFLINE_CACHE_DURATION == 10


# ==================== force_online_check ====================

class TestForceOnlineCheck:
    """force_online_check — принудительная проверка соединения."""

    def test_success(self):
        client = APIClientBase("https://test.example.com")
        client._mark_offline()
        resp = MagicMock()
        resp.status_code = 200
        client.session.get = MagicMock(return_value=resp)
        result = client.force_online_check()
        assert result is True
        assert client.is_online is True

    def test_server_error(self):
        client = APIClientBase("https://test.example.com")
        resp = MagicMock()
        resp.status_code = 500
        client.session.get = MagicMock(return_value=resp)
        result = client.force_online_check()
        assert result is False
        assert client.is_online is False

    def test_connection_error(self):
        client = APIClientBase("https://test.example.com")
        client.session.get = MagicMock(side_effect=ConnectionError("refused"))
        result = client.force_online_check()
        assert result is False
        assert client.is_online is False


# ==================== _handle_response ====================

class TestHandleResponse:
    """_handle_response — обработка HTTP ответов."""

    def test_success_200_json(self):
        client = APIClientBase("https://test.example.com")
        resp = _make_response(200, json_data={"id": 1})
        result = client._handle_response(resp)
        assert result == {"id": 1}

    def test_success_no_json(self):
        """Ответ без JSON — возвращает True."""
        client = APIClientBase("https://test.example.com")
        resp = _make_response(200)
        resp.json.side_effect = ValueError("No JSON")
        result = client._handle_response(resp)
        assert result is True

    def test_custom_success_codes(self):
        """Кастомные success codes."""
        client = APIClientBase("https://test.example.com")
        resp = _make_response(201, json_data={"created": True})
        result = client._handle_response(resp, success_codes=[200, 201])
        assert result == {"created": True}

    def test_401_raises_auth_error(self):
        client = APIClientBase("https://test.example.com")
        resp = _make_response(401, json_data={"detail": "Not authenticated"})
        with pytest.raises(APIAuthError):
            client._handle_response(resp)

    def test_403_raises_auth_error(self):
        client = APIClientBase("https://test.example.com")
        resp = _make_response(403, json_data={"detail": "Forbidden"})
        with pytest.raises(APIAuthError, match="Forbidden"):
            client._handle_response(resp)

    def test_429_raises_response_error(self):
        client = APIClientBase("https://test.example.com")
        resp = _make_response(429, json_data={"detail": "Rate limited"})
        with pytest.raises(APIResponseError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.status_code == 429

    def test_500_raises_response_error(self):
        client = APIClientBase("https://test.example.com")
        resp = _make_response(500, json_data={"detail": "Internal error"})
        with pytest.raises(APIResponseError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.status_code == 500

    def test_error_detail_extraction(self):
        client = APIClientBase("https://test.example.com")
        resp = _make_response(500, json_data={"detail": "DB connection failed"})
        assert client._extract_error_detail(resp) == "DB connection failed"

    def test_error_detail_list(self):
        client = APIClientBase("https://test.example.com")
        resp = _make_response(422, json_data=[{"msg": "validation error"}])
        detail = client._extract_error_detail(resp)
        assert "validation error" in detail

    def test_error_detail_no_json(self):
        client = APIClientBase("https://test.example.com")
        resp = _make_response(500, text="Server Error")
        resp.headers = {}  # Нет content-type
        detail = client._extract_error_detail(resp)
        assert detail == "Server Error"


# ==================== _calc_backoff ====================

class TestCalcBackoff:
    """Exponential backoff с jitter."""

    def test_first_attempt_around_half_second(self):
        client = APIClientBase("https://test.example.com")
        delay = client._calc_backoff(0)
        # 0.5 ± 25% → [0.375, 0.625]
        assert 0.1 <= delay <= 1.0

    def test_second_attempt_around_one_second(self):
        client = APIClientBase("https://test.example.com")
        delay = client._calc_backoff(1)
        # 1.0 ± 25% → [0.75, 1.25]
        assert 0.5 <= delay <= 2.0

    def test_max_delay_capped(self):
        client = APIClientBase("https://test.example.com")
        delay = client._calc_backoff(10)
        assert delay <= client.RETRY_MAX_DELAY * 1.5  # С jitter


# ==================== _parse_retry_after ====================

class TestParseRetryAfter:
    """Парсинг заголовка Retry-After."""

    def test_numeric_value(self):
        resp = MagicMock()
        resp.headers = {'Retry-After': '30'}
        assert APIClientBase._parse_retry_after(resp) == 30.0

    def test_no_header(self):
        resp = MagicMock()
        resp.headers = {}
        assert APIClientBase._parse_retry_after(resp) is None

    def test_invalid_value(self):
        resp = MagicMock()
        resp.headers = {'Retry-After': 'invalid'}
        assert APIClientBase._parse_retry_after(resp) is None


# ==================== _AuthSession ====================

class TestAuthSession:
    """_AuthSession — сохранение Authorization при same-host redirect."""

    def test_same_host_keeps_auth(self):
        session = _AuthSession()
        # Мок original request
        original_request = MagicMock()
        original_request.url = "https://example.com/api/v1/test"

        # Мок redirect response
        response = MagicMock()
        response.request = original_request

        # Мок prepared request (redirect target)
        prepared = MagicMock()
        prepared.url = "http://example.com/api/v1/test/"  # Same host, different scheme
        prepared.headers = {"Authorization": "Bearer token123"}

        session.rebuild_auth(prepared, response)
        # Auth должен остаться
        assert "Authorization" in prepared.headers

    def test_different_host_removes_auth(self):
        session = _AuthSession()
        original_request = MagicMock()
        original_request.url = "https://example.com/api/test"

        response = MagicMock()
        response.request = original_request

        prepared = MagicMock()
        prepared.url = "https://other-host.com/api/test"
        prepared.headers = {"Authorization": "Bearer token123"}

        session.rebuild_auth(prepared, response)
        # Auth должен быть удалён (cross-origin)
        assert "Authorization" not in prepared.headers

    def test_no_auth_header_noop(self):
        session = _AuthSession()
        response = MagicMock()
        response.request = MagicMock(url="https://a.com/x")
        prepared = MagicMock()
        prepared.url = "https://b.com/x"
        prepared.headers = {"Content-Type": "application/json"}
        session.rebuild_auth(prepared, response)
        # Ничего не упало, Content-Type на месте
        assert "Content-Type" in prepared.headers


# ==================== Relogin callback ====================

class TestReloginCallback:
    """Relogin callback chain при истечении refresh token."""

    def test_set_relogin_callback(self):
        client = APIClientBase("https://test.example.com")
        callback = MagicMock()
        client.set_relogin_callback(callback)
        assert client._relogin_callback is callback

    def test_signal_relogin_calls_callback(self):
        client = APIClientBase("https://test.example.com")
        callback = MagicMock(return_value=True)
        client.set_relogin_callback(callback)
        client._signal_relogin_needed()
        callback.assert_called_once()
        assert client._relogin_signaled is False  # Сброшен при успехе

    def test_signal_relogin_failed(self):
        client = APIClientBase("https://test.example.com")
        callback = MagicMock(return_value=False)
        client.set_relogin_callback(callback)
        client._signal_relogin_needed()
        callback.assert_called_once()
        assert client._relogin_signaled is True  # Остаётся True

    def test_signal_relogin_no_duplicate(self):
        """Повторный вызов — callback не вызывается повторно."""
        client = APIClientBase("https://test.example.com")
        callback = MagicMock(return_value=False)
        client.set_relogin_callback(callback)
        client._signal_relogin_needed()
        client._signal_relogin_needed()
        assert callback.call_count == 1

    def test_signal_relogin_no_callback(self):
        """Без callback — просто устанавливает флаг."""
        client = APIClientBase("https://test.example.com")
        client._signal_relogin_needed()
        assert client._relogin_signaled is True

    def test_signal_relogin_callback_raises(self):
        """Callback выбрасывает ошибку — не падает."""
        client = APIClientBase("https://test.example.com")
        callback = MagicMock(side_effect=RuntimeError("fail"))
        client.set_relogin_callback(callback)
        client._signal_relogin_needed()
        assert client._relogin_signaled is True


# ==================== Request — offline cache skip ====================

class TestRequestOfflineCache:
    """_request — пропуск запросов при недавнем offline."""

    def test_recently_offline_raises_connection_error(self):
        """При недавнем offline — сразу APIConnectionError без реального запроса."""
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = time.time()  # Только что
        with pytest.raises(APIConnectionError, match="Offline"):
            client._request('GET', 'https://test.example.com/api/test')

    def test_login_bypasses_offline_cache(self):
        """Login-запрос — всегда выполняется, даже при offline."""
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = time.time()
        resp = _make_response(200, json_data={"token": "abc"})
        client.session.request = MagicMock(return_value=resp)
        # Login endpoint не блокируется offline кешем
        result = client._request('POST', 'https://test.example.com/api/v1/auth/login')
        assert result.status_code == 200

    def test_mark_offline_false_no_offline_cache(self):
        """mark_offline=False — не блокируется offline кешем."""
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = time.time()
        resp = _make_response(200, json_data={})
        client.session.request = MagicMock(return_value=resp)
        result = client._request(
            'POST', 'https://test.example.com/api/heartbeat',
            mark_offline=False
        )
        assert result.status_code == 200


# ==================== Request — success restores online ====================

class TestRequestOnlineRestoration:
    """Успешный запрос — восстановление online статуса."""

    def test_successful_request_restores_online(self):
        client = APIClientBase("https://test.example.com")
        client._is_online = False
        client._last_offline_time = None  # Не recently offline
        client._offline_message_shown = True
        resp = _make_response(200, json_data={"ok": True})
        client.session.request = MagicMock(return_value=resp)
        client._request('GET', 'https://test.example.com/api/test', retry=False)
        assert client.is_online is True
        assert client._first_request is False
        assert client._offline_message_shown is False


# ==================== Request — timeout / connection errors ====================

class TestRequestErrors:
    """_request — обработка сетевых ошибок."""

    def test_timeout_raises_api_timeout(self):
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = None
        client.session.request = MagicMock(
            side_effect=requests.exceptions.Timeout("timeout")
        )
        with pytest.raises(APITimeoutError):
            client._request('GET', 'https://test.example.com/api/test', retry=False)

    def test_connection_error_raises_api_connection(self):
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = None
        client.session.request = MagicMock(
            side_effect=requests.exceptions.ConnectionError("refused")
        )
        with pytest.raises(APIConnectionError):
            client._request('GET', 'https://test.example.com/api/test', retry=False)

    def test_timeout_marks_offline(self):
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = None
        client.session.request = MagicMock(
            side_effect=requests.exceptions.Timeout("timeout")
        )
        try:
            client._request('GET', 'https://test.example.com/api/test', retry=False)
        except APITimeoutError:
            pass
        assert client.is_online is False

    def test_connection_error_marks_offline(self):
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = None
        client.session.request = MagicMock(
            side_effect=requests.exceptions.ConnectionError("refused")
        )
        try:
            client._request('GET', 'https://test.example.com/api/test', retry=False)
        except APIConnectionError:
            pass
        assert client.is_online is False

    def test_mark_offline_false_no_offline_status(self):
        """mark_offline=False — статус не меняется при ошибке."""
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = None
        client.session.request = MagicMock(
            side_effect=requests.exceptions.Timeout("timeout")
        )
        try:
            client._request(
                'GET', 'https://test.example.com/api/test',
                retry=False, mark_offline=False
            )
        except APITimeoutError:
            pass
        # is_online всё ещё True (mark_offline=False)
        assert client.is_online is True


# ==================== Request — retry on 502/503/504 ====================

class TestRequestRetry:
    """_request — retry при серверных ошибках."""

    def test_502_retries(self):
        """502 — retry, потом успех."""
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = None
        client.RETRY_DELAY = 0.01  # Ускоряем для тестов
        resp_502 = _make_response(502)
        resp_200 = _make_response(200, json_data={"ok": True})
        client.session.request = MagicMock(side_effect=[resp_502, resp_200])
        result = client._request('GET', 'https://test.example.com/api/test')
        assert result.status_code == 200
        assert client.session.request.call_count == 2

    def test_429_retries_with_retry_after(self):
        """429 с Retry-After — ждёт и повторяет."""
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = None
        client.RETRY_DELAY = 0.01
        resp_429 = _make_response(429, headers={'Retry-After': '0.01'})
        resp_200 = _make_response(200, json_data={"ok": True})
        client.session.request = MagicMock(side_effect=[resp_429, resp_200])
        result = client._request('GET', 'https://test.example.com/api/test')
        assert result.status_code == 200

    def test_no_retry_when_disabled(self):
        """retry=False — одна попытка."""
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = None
        resp_502 = _make_response(502)
        client.session.request = MagicMock(return_value=resp_502)
        result = client._request('GET', 'https://test.example.com/api/test', retry=False)
        assert result.status_code == 502
        assert client.session.request.call_count == 1


# ==================== Request — write timeout ====================

class TestRequestTimeout:
    """_request — выбор таймаута."""

    def test_write_operations_use_write_timeout(self):
        """POST/PUT/PATCH/DELETE — WRITE_TIMEOUT."""
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = None
        client._first_request = False
        resp = _make_response(200, json_data={})
        client.session.request = MagicMock(return_value=resp)
        for method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            client.session.request.reset_mock()
            client._request(method, 'https://test.example.com/api/test', retry=False)
            call_kwargs = client.session.request.call_args
            assert call_kwargs[1].get('timeout') == client.WRITE_TIMEOUT or \
                   call_kwargs.kwargs.get('timeout') == client.WRITE_TIMEOUT

    def test_first_request_uses_first_timeout(self):
        """Первый запрос — FIRST_REQUEST_TIMEOUT."""
        client = APIClientBase("https://test.example.com")
        client._last_offline_time = None
        client._first_request = True
        resp = _make_response(200, json_data={})
        client.session.request = MagicMock(return_value=resp)
        client._request('GET', 'https://test.example.com/api/test', retry=False)
        call_kwargs = client.session.request.call_args
        assert call_kwargs[1].get('timeout') == client.FIRST_REQUEST_TIMEOUT or \
               call_kwargs.kwargs.get('timeout') == client.FIRST_REQUEST_TIMEOUT


# ==================== DatabaseSynchronizer — basic ====================

class TestDatabaseSynchronizer:
    """DatabaseSynchronizer — синхронизация серверных данных."""

    def test_sync_all_success(self):
        from utils.db_sync import DatabaseSynchronizer
        mock_db = MagicMock()
        mock_api = MagicMock()

        # Мокаем все API методы
        mock_api.get_employees.return_value = []
        mock_api.get_clients.return_value = []
        mock_api.get_contracts.return_value = []
        mock_api.get_crm_cards.return_value = []
        mock_api.get_supervision_cards.return_value = []
        mock_api.get_rates.return_value = []
        mock_api.get_payments.return_value = []
        mock_api.get_project_files.return_value = []
        mock_api.get_salaries.return_value = []
        mock_api.get_stage_executors.return_value = []
        mock_api.get_approval_stage_deadlines.return_value = []
        mock_api.get_action_history.return_value = []
        mock_api.get_supervision_history.return_value = []

        syncer = DatabaseSynchronizer(mock_db, mock_api)
        result = syncer.sync_all()
        assert result['success'] is True
        assert isinstance(result['synced'], dict)

    def test_sync_all_with_progress_callback(self):
        from utils.db_sync import DatabaseSynchronizer
        mock_db = MagicMock()
        mock_api = MagicMock()
        mock_api.get_employees.return_value = []
        mock_api.get_clients.return_value = []
        mock_api.get_contracts.return_value = []
        mock_api.get_crm_cards.return_value = []
        mock_api.get_supervision_cards.return_value = []
        mock_api.get_rates.return_value = []
        mock_api.get_payments.return_value = []
        mock_api.get_project_files.return_value = []
        mock_api.get_salaries.return_value = []
        mock_api.get_stage_executors.return_value = []
        mock_api.get_approval_stage_deadlines.return_value = []
        mock_api.get_action_history.return_value = []
        mock_api.get_supervision_history.return_value = []

        syncer = DatabaseSynchronizer(mock_db, mock_api)
        progress_calls = []
        result = syncer.sync_all(
            progress_callback=lambda cur, total, msg: progress_calls.append((cur, total, msg))
        )
        assert result['success'] is True
        assert len(progress_calls) == 14

    def test_sync_all_partial_failure(self):
        """Ошибка в одном шаге — sync продолжается, synced count = 0 для сбойного шага."""
        from utils.db_sync import DatabaseSynchronizer
        mock_db = MagicMock()
        mock_api = MagicMock()
        # Сотрудники — ошибка (внутри _sync_employees ловится, возвращает 0)
        mock_api.get_employees.side_effect = Exception("API down")
        # Остальные — пустые
        mock_api.get_clients.return_value = []
        mock_api.get_contracts.return_value = []
        mock_api.get_crm_cards.return_value = []
        mock_api.get_supervision_cards.return_value = []
        mock_api.get_rates.return_value = []
        mock_api.get_payments.return_value = []
        mock_api.get_project_files.return_value = []
        mock_api.get_salaries.return_value = []
        mock_api.get_stage_executors.return_value = []
        mock_api.get_approval_stage_deadlines.return_value = []
        mock_api.get_action_history.return_value = []
        mock_api.get_supervision_history.return_value = []

        syncer = DatabaseSynchronizer(mock_db, mock_api)
        result = syncer.sync_all()
        # Отдельные шаги ловят ошибки сами, sync_all продолжается
        assert result['success'] is True
        assert result['synced']['employees'] == 0


# ==================== SyncManager — process_sync_result edge cases ====================

class TestSyncManagerProcessResult:
    """SyncManager._process_sync_result — edge cases (дополнение к test_sync_manager.py)."""

    def _make_sm(self):
        """Создать SyncManager с моками (без реального PyQt5)."""
        # Используем тот же подход мокирования что в test_sync_manager.py
        import importlib
        saved = {}
        for k in ['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui']:
            if k in sys.modules:
                saved[k] = sys.modules[k]

        mock_qtcore = MagicMock()
        mock_qtcore.pyqtSignal = MagicMock(return_value=MagicMock())
        mock_qtcore.QObject = type('MockQObject', (), {'__init__': lambda s, *a, **kw: None})

        class MockQTimer:
            def __init__(self, *args, **kwargs):
                self.timeout = MagicMock()
                self.timeout.connect = MagicMock()
            def start(self, interval=0): pass
            def stop(self): pass
            @staticmethod
            def singleShot(ms, callback): pass

        mock_qtcore.QTimer = MockQTimer
        sys.modules['PyQt5'] = MagicMock()
        sys.modules['PyQt5.QtCore'] = mock_qtcore
        sys.modules['PyQt5.QtWidgets'] = MagicMock()
        sys.modules['PyQt5.QtGui'] = MagicMock()

        # Очищаем кеш для перезагрузки с моками
        if 'utils.sync_manager' in sys.modules:
            del sys.modules['utils.sync_manager']

        from utils.sync_manager import SyncManager
        api = MagicMock()
        api.is_online = True
        api.base_url = "http://test:8000"
        sm = SyncManager(api_client=api, employee_id=1)

        # Восстанавливаем
        for k in ['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui']:
            if k in saved:
                sys.modules[k] = saved[k]
            elif k in sys.modules:
                del sys.modules[k]
        if 'utils.sync_manager' in sys.modules:
            del sys.modules['utils.sync_manager']

        return sm

    def test_sync_in_progress_cleared_on_error(self):
        """_on_sync_error — _sync_in_progress сбрасывается."""
        sm = self._make_sm()
        sm._sync_in_progress = True
        sm._on_sync_error()
        assert sm._sync_in_progress is False

    def test_sync_data_already_in_progress_skipped(self):
        """_sync_data — пропускается при _sync_in_progress=True."""
        sm = self._make_sm()
        sm.last_sync_timestamp = MagicMock()
        sm._sync_in_progress = True
        sm._sync_data()
        # Не должно начинать новую синхронизацию
        assert sm._sync_in_progress is True

    def test_start_stop_idempotent(self):
        sm = self._make_sm()
        sm.start()
        sm.start()  # Повторный — ничего не делает
        assert sm.is_running is True
        sm.stop()
        sm.stop()  # Повторный — ничего не делает
        assert sm.is_running is False

    def test_pause_blocks_sync(self):
        sm = self._make_sm()
        sm.start()
        sm.pause_sync()
        assert sm._sync_paused is True
        sm.last_sync_timestamp = MagicMock()
        sm._sync_data()
        assert sm._sync_in_progress is False  # Не начата
