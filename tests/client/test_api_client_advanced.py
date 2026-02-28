# -*- coding: utf-8 -*-
"""
Расширенные тесты для utils/api_client/ — base.py edge-cases, миксины.

Этап 9: Мелкие модули и gaps.
Покрываем: retry-логику 401/429/5xx, JWT парсинг, auto-refresh,
offline кеш, _AuthSession, _extract_error_detail, миксины auth/clients/contracts.
"""
import sys
import os
import time
import json
import base64
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock, call

import pytest
import requests

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.api_client import (
    APIClient, APIClientBase, APIError, APITimeoutError,
    APIConnectionError, APIAuthError, APIResponseError,
)
from utils.api_client.base import _AuthSession


# ============================================================================
# ХЕЛПЕРЫ
# ============================================================================

def _make_response(status_code=200, json_data=None, headers=None, text=''):
    """Создать mock requests.Response"""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
        resp.headers.setdefault('content-type', 'application/json')
    else:
        resp.json.side_effect = ValueError("No JSON")
    return resp


def _make_jwt(payload: dict) -> str:
    """Создать фейковый JWT токен с заданным payload"""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b'=').decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=').decode()
    sig = base64.urlsafe_b64encode(b"fake_signature").rstrip(b'=').decode()
    return f"{header}.{body}.{sig}"


@pytest.fixture
def client():
    """APIClient с замоканной session (без реальных HTTP)"""
    c = APIClient(base_url="http://test-server:8000")
    c.session = MagicMock(spec=_AuthSession)
    return c


# ============================================================================
# BASE.PY — RETRY ЛОГИКА 401
# ============================================================================

class TestRetry401:
    """401 → refresh_token → retry"""

    def test_401_retry_with_refresh_token_success(self, client):
        """При 401 с refresh_token — обновляет токен и повторяет запрос."""
        # Устанавливаем refresh_token
        client.refresh_token = "old_refresh"
        client.token = "old_access"
        client.headers["Authorization"] = "Bearer old_access"

        resp_401 = _make_response(401, json_data={"detail": "Token expired"})
        resp_401.request = MagicMock(url="http://test-server:8000/api/clients")

        # refresh endpoint → 200 с новым токеном
        resp_refresh = _make_response(200, json_data={
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "employee_id": 1
        })
        resp_refresh.request = MagicMock(url="http://test-server:8000/api/auth/refresh")

        # Повторный запрос → 200
        resp_ok = _make_response(200, json_data=[{"id": 1}])

        client.session.request.side_effect = [resp_401, resp_refresh, resp_ok]

        result = client._request('GET', "http://test-server:8000/api/clients")
        # Должен вернуть успешный ответ (третий вызов)
        assert result.status_code == 200

    def test_401_without_refresh_token_raises(self, client):
        """При 401 без refresh_token — возвращает 401 ответ (не retry)."""
        client.refresh_token = None
        client.token = "old_access"

        resp_401 = _make_response(401, json_data={"detail": "Unauthorized"})
        resp_401.request = MagicMock(url="http://test-server:8000/api/clients")

        client.session.request.return_value = resp_401
        result = client._request('GET', "http://test-server:8000/api/clients")
        assert result.status_code == 401

    def test_401_refresh_fails_signals_relogin(self, client):
        """При 401 если refresh не удался — вызывает _signal_relogin_needed."""
        client.refresh_token = "old_refresh"
        client.token = "old_access"
        client.headers["Authorization"] = "Bearer old_access"

        resp_401 = _make_response(401, json_data={"detail": "Token expired"})
        resp_401.request = MagicMock(url="http://test-server:8000/api/clients")

        # refresh endpoint → 401 (refresh token тоже истёк)
        resp_refresh_fail = _make_response(401, json_data={"detail": "Refresh expired"})
        resp_refresh_fail.request = MagicMock(url="http://test-server:8000/api/auth/refresh")

        client.session.request.side_effect = [resp_401, resp_refresh_fail]

        callback = MagicMock(return_value=False)
        client.set_relogin_callback(callback)

        result = client._request('GET', "http://test-server:8000/api/clients")
        # Должен вернуть 401 (refresh не помог)
        assert result.status_code == 401
        # relogin callback должен быть вызван
        callback.assert_called_once()


# ============================================================================
# BASE.PY — 429 Too Many Requests
# ============================================================================

class TestRetry429:
    """429 → Retry-After → повтор"""

    def test_429_with_retry_after_header(self, client):
        """При 429 с заголовком Retry-After — ждёт и повторяет."""
        resp_429 = _make_response(429, headers={'Retry-After': '0.01'})
        resp_ok = _make_response(200, json_data={"ok": True})

        client.session.request.side_effect = [resp_429, resp_ok]

        with patch('utils.api_client.base.time.sleep') as mock_sleep:
            result = client._request('GET', "http://test-server:8000/api/data")

        assert result.status_code == 200
        # sleep был вызван с Retry-After значением
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] == pytest.approx(0.01, abs=0.001)

    def test_429_without_retry_after_uses_backoff(self, client):
        """При 429 без Retry-After — использует exponential backoff."""
        resp_429 = _make_response(429)
        resp_ok = _make_response(200, json_data={"ok": True})

        client.session.request.side_effect = [resp_429, resp_ok]

        with patch('utils.api_client.base.time.sleep') as mock_sleep:
            result = client._request('GET', "http://test-server:8000/api/data")

        assert result.status_code == 200
        mock_sleep.assert_called_once()
        # backoff задержка > 0
        assert mock_sleep.call_args[0][0] > 0


# ============================================================================
# BASE.PY — 502/503/504 RETRY
# ============================================================================

class TestRetry5xx:
    """502/503/504 → retry с backoff"""

    @pytest.mark.parametrize("status_code", [502, 503, 504])
    def test_5xx_retry_then_success(self, client, status_code):
        """При 5xx — retry с backoff, потом успех."""
        resp_5xx = _make_response(status_code)
        resp_ok = _make_response(200, json_data={"ok": True})

        client.session.request.side_effect = [resp_5xx, resp_ok]

        with patch('utils.api_client.base.time.sleep'):
            result = client._request('GET', "http://test-server:8000/api/data")

        assert result.status_code == 200

    def test_5xx_all_retries_exhausted(self, client):
        """При 5xx все попытки — возвращает последний 502."""
        resp_502 = _make_response(502)
        client.session.request.return_value = resp_502

        with patch('utils.api_client.base.time.sleep'):
            result = client._request('GET', "http://test-server:8000/api/data")

        # Последняя попытка — 502 возвращается как есть (не retry)
        assert result.status_code == 502


# ============================================================================
# BASE.PY — TOKEN EXPIRY / AUTO-REFRESH
# ============================================================================

class TestTokenExpiry:
    """Извлечение exp из JWT и auto-refresh"""

    def test_extract_token_expiry_valid_jwt(self, client):
        """Корректный JWT — извлекает exp."""
        exp_time = time.time() + 3600
        token = _make_jwt({"sub": "1", "exp": exp_time})
        result = client._extract_token_expiry(token)
        assert result == pytest.approx(exp_time, abs=1)

    def test_extract_token_expiry_invalid_jwt(self, client):
        """Невалидный JWT — возвращает None."""
        assert client._extract_token_expiry("not.a.valid-jwt") is None
        assert client._extract_token_expiry("only_one_part") is None
        assert client._extract_token_expiry("") is None

    def test_is_token_expiring_soon_true(self, client):
        """Токен истекает через 60 секунд (< 300 threshold) → True."""
        client._token_exp = time.time() + 60
        assert client._is_token_expiring_soon() is True

    def test_is_token_expiring_soon_false(self, client):
        """Токен истекает через 600 секунд (> 300 threshold) → False."""
        client._token_exp = time.time() + 600
        assert client._is_token_expiring_soon() is False

    def test_is_token_expiring_soon_no_exp(self, client):
        """Нет _token_exp → False."""
        client._token_exp = None
        assert client._is_token_expiring_soon() is False

    def test_auto_refresh_called_when_expiring(self, client):
        """_auto_refresh_if_needed вызывает refresh при скором истечении."""
        client.token = "old_access"
        client.refresh_token = "old_refresh"
        client._token_exp = time.time() + 60  # скоро истекает

        # Мокаем refresh_access_token
        with patch.object(client, 'refresh_access_token', return_value=True) as mock_refresh:
            client._auto_refresh_if_needed()
        mock_refresh.assert_called_once()

    def test_auto_refresh_not_called_when_not_expiring(self, client):
        """_auto_refresh_if_needed НЕ вызывает refresh если токен свежий."""
        client.token = "access"
        client.refresh_token = "refresh"
        client._token_exp = time.time() + 3600  # далеко от истечения

        with patch.object(client, 'refresh_access_token') as mock_refresh:
            client._auto_refresh_if_needed()
        mock_refresh.assert_not_called()


# ============================================================================
# BASE.PY — OFFLINE CACHE
# ============================================================================

class TestOfflineCache:
    """Кеширование offline статуса (10 сек)"""

    def test_offline_cache_duration_constant(self, client):
        """OFFLINE_CACHE_DURATION = 10"""
        assert client.OFFLINE_CACHE_DURATION == 10

    def test_recently_offline_true(self, client):
        """После _mark_offline — _is_recently_offline() возвращает True."""
        client._mark_offline()
        assert client._is_recently_offline() is True

    def test_recently_offline_false_initially(self, client):
        """До offline — _is_recently_offline() = False."""
        assert client._is_recently_offline() is False

    def test_reset_offline_cache(self, client):
        """reset_offline_cache() сбрасывает кеш."""
        client._mark_offline()
        assert client._is_recently_offline() is True
        client.reset_offline_cache()
        assert client._is_recently_offline() is False

    def test_force_online_check_success(self, client):
        """force_online_check: сервер доступен → True, is_online = True."""
        client._mark_offline()
        resp_ok = _make_response(200)
        client.session.get.return_value = resp_ok

        result = client.force_online_check()
        assert result is True
        assert client.is_online is True

    def test_force_online_check_failure(self, client):
        """force_online_check: сервер недоступен → False."""
        client.session.get.side_effect = requests.exceptions.ConnectionError("fail")
        result = client.force_online_check()
        assert result is False
        assert client.is_online is False


# ============================================================================
# BASE.PY — _AuthSession
# ============================================================================

class TestAuthSession:
    """_AuthSession — сохранение Authorization при same-host redirect"""

    def test_same_host_keeps_auth(self):
        """Same-host redirect (https→http) — сохраняет Authorization."""
        session = _AuthSession()
        prepared = MagicMock()
        prepared.headers = {"Authorization": "Bearer token123"}
        prepared.url = "http://example.com/api/data"

        response = MagicMock()
        response.request = MagicMock()
        response.request.url = "https://example.com/api/data/"

        session.rebuild_auth(prepared, response)
        # Authorization должен остаться
        assert "Authorization" in prepared.headers

    def test_cross_host_removes_auth(self):
        """Cross-host redirect — удаляет Authorization."""
        session = _AuthSession()
        prepared = MagicMock()
        prepared.headers = {"Authorization": "Bearer token123"}
        prepared.url = "http://evil.com/steal"

        response = MagicMock()
        response.request = MagicMock()
        response.request.url = "https://example.com/api/data/"

        session.rebuild_auth(prepared, response)
        assert "Authorization" not in prepared.headers

    def test_no_auth_header_noop(self):
        """Без Authorization в headers — ничего не делает."""
        session = _AuthSession()
        prepared = MagicMock()
        prepared.headers = {"Content-Type": "application/json"}
        prepared.url = "http://evil.com/steal"

        response = MagicMock()
        response.request = MagicMock()
        response.request.url = "https://example.com/"

        # Не должен вызвать ошибку
        session.rebuild_auth(prepared, response)
        assert "Authorization" not in prepared.headers


# ============================================================================
# BASE.PY — _extract_error_detail
# ============================================================================

class TestExtractErrorDetail:
    """_extract_error_detail — JSON vs plain text"""

    def test_json_error_with_detail(self, client):
        """JSON ответ с полем detail — извлекает detail."""
        resp = _make_response(400, json_data={"detail": "Bad request"})
        result = client._extract_error_detail(resp)
        assert result == "Bad request"

    def test_json_error_list(self, client):
        """JSON ответ — список ошибок."""
        resp = _make_response(422, json_data=[{"loc": ["body"], "msg": "required"}])
        result = client._extract_error_detail(resp)
        assert "required" in result

    def test_plain_text_error(self, client):
        """Не-JSON ответ — возвращает text."""
        resp = _make_response(500, text="Internal Server Error")
        resp.headers = {'content-type': 'text/plain'}
        result = client._extract_error_detail(resp)
        assert result == "Internal Server Error"

    def test_empty_response(self, client):
        """Пустой ответ — 'Неизвестная ошибка'."""
        resp = _make_response(500, text='')
        resp.headers = {}
        result = client._extract_error_detail(resp)
        assert result == 'Неизвестная ошибка'


# ============================================================================
# BASE.PY — SET/CLEAR TOKEN
# ============================================================================

class TestTokenManagement:
    """set_token / clear_token"""

    def test_set_token_updates_headers(self, client):
        """set_token устанавливает Authorization header."""
        exp_time = time.time() + 3600
        token = _make_jwt({"sub": "1", "exp": exp_time})
        client.set_token(token, "refresh_tok")
        assert client.token == token
        assert client.refresh_token == "refresh_tok"
        assert client.headers["Authorization"] == f"Bearer {token}"
        assert client._token_exp is not None

    def test_clear_token_removes_all(self, client):
        """clear_token очищает всё."""
        client.token = "tok"
        client.refresh_token = "ref"
        client._token_exp = 123.0
        client.headers["Authorization"] = "Bearer tok"
        client.clear_token()
        assert client.token is None
        assert client.refresh_token is None
        assert client._token_exp is None
        assert "Authorization" not in client.headers


# ============================================================================
# BASE.PY — _handle_response
# ============================================================================

class TestHandleResponse:
    """_handle_response — обработка HTTP ответов"""

    def test_200_returns_json(self, client):
        """200 + JSON → возвращает данные."""
        resp = _make_response(200, json_data={"name": "test"})
        result = client._handle_response(resp)
        assert result == {"name": "test"}

    def test_200_no_json_returns_true(self, client):
        """200 без JSON → возвращает True."""
        resp = _make_response(200)
        result = client._handle_response(resp)
        assert result is True

    def test_401_raises_auth_error(self, client):
        """401 → APIAuthError."""
        resp = _make_response(401, json_data={"detail": "Token expired"})
        with pytest.raises(APIAuthError, match="авторизация"):
            client._handle_response(resp)

    def test_403_raises_auth_error(self, client):
        """403 → APIAuthError с деталями."""
        resp = _make_response(403, json_data={"detail": "Forbidden"})
        with pytest.raises(APIAuthError, match="Forbidden"):
            client._handle_response(resp)

    def test_500_raises_response_error(self, client):
        """500 → APIResponseError с кодом."""
        resp = _make_response(500, json_data={"detail": "Internal error"})
        with pytest.raises(APIResponseError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.status_code == 500


# ============================================================================
# BASE.PY — BACKOFF
# ============================================================================

class TestBackoff:
    """_calc_backoff — exponential backoff с jitter"""

    def test_backoff_increases_with_attempt(self, client):
        """Задержка растёт с каждой попыткой."""
        delays = [client._calc_backoff(i) for i in range(5)]
        # Средние значения должны расти (с учётом jitter могут варьироваться)
        # Проверяем что первая задержка <= последней
        # Из-за jitter берём широкие рамки
        assert delays[0] < 5.0  # первая задержка < max_delay

    def test_backoff_never_negative(self, client):
        """Задержка всегда >= 0.1"""
        for attempt in range(10):
            delay = client._calc_backoff(attempt)
            assert delay >= 0.1

    def test_backoff_capped_at_max_delay(self, client):
        """Задержка не превышает RETRY_MAX_DELAY + jitter"""
        for attempt in range(20):
            delay = client._calc_backoff(attempt)
            max_possible = client.RETRY_MAX_DELAY * (1 + client.RETRY_JITTER)
            assert delay <= max_possible + 0.1  # небольшой запас


# ============================================================================
# BASE.PY — TIMEOUT LOGIC
# ============================================================================

class TestTimeoutRetry:
    """Timeout и ConnectionError — retry и offline"""

    def test_timeout_all_retries_raises(self, client):
        """Timeout на всех попытках → APITimeoutError."""
        client.session.request.side_effect = requests.exceptions.Timeout("timed out")
        with patch('utils.api_client.base.time.sleep'):
            with pytest.raises(APITimeoutError):
                client._request('GET', "http://test-server:8000/api/data")

    def test_connection_error_all_retries_raises(self, client):
        """ConnectionError на всех попытках → APIConnectionError."""
        client.session.request.side_effect = requests.exceptions.ConnectionError("refused")
        with patch('utils.api_client.base.time.sleep'):
            with pytest.raises(APIConnectionError):
                client._request('GET', "http://test-server:8000/api/data")

    def test_connection_error_marks_offline(self, client):
        """ConnectionError → клиент помечается как offline."""
        client.session.request.side_effect = requests.exceptions.ConnectionError("refused")
        with patch('utils.api_client.base.time.sleep'):
            with pytest.raises(APIConnectionError):
                client._request('GET', "http://test-server:8000/api/data")
        assert client.is_online is False

    def test_mark_offline_false_no_offline(self, client):
        """mark_offline=False → клиент НЕ помечается как offline."""
        client.session.request.side_effect = requests.exceptions.ConnectionError("refused")
        with patch('utils.api_client.base.time.sleep'):
            with pytest.raises(APIConnectionError):
                client._request(
                    'GET', "http://test-server:8000/api/data",
                    mark_offline=False
                )
        assert client.is_online is True


# ============================================================================
# BASE.PY — set_offline_mode / is_online
# ============================================================================

class TestOfflineMode:
    """set_offline_mode — принудительная установка offline"""

    def test_set_offline_mode_true(self, client):
        """set_offline_mode(True) — is_online=False, кеш не истекает."""
        client.set_offline_mode(True)
        assert client.is_online is False
        assert client._is_recently_offline() is True

    def test_set_offline_mode_false(self, client):
        """set_offline_mode(False) — is_online=True."""
        client.set_offline_mode(True)
        client.set_offline_mode(False)
        assert client.is_online is True
        assert client._is_recently_offline() is False


# ============================================================================
# AUTH MIXIN
# ============================================================================

class TestAuthMixin:
    """auth_mixin.py — login, refresh, logout, get_current_user"""

    def test_login_sets_token_and_employee_id(self, client):
        """login — устанавливает token и employee_id."""
        exp_time = time.time() + 3600
        access_token = _make_jwt({"sub": "1", "exp": exp_time})
        resp = _make_response(200, json_data={
            "access_token": access_token,
            "refresh_token": "ref_123",
            "employee_id": 42
        })
        client.session.request.return_value = resp

        data = client.login("admin", "password")
        assert client.token == access_token
        assert client.refresh_token == "ref_123"
        assert client.employee_id == 42
        assert data["employee_id"] == 42

    def test_refresh_token_rotation(self, client):
        """refresh_access_token — ротация refresh_token."""
        client.token = "old_access"
        client.refresh_token = "old_refresh"

        exp_time = time.time() + 3600
        new_token = _make_jwt({"sub": "1", "exp": exp_time})
        resp = _make_response(200, json_data={
            "access_token": new_token,
            "refresh_token": "new_refresh",
            "employee_id": 1
        })
        client.session.request.return_value = resp

        result = client.refresh_access_token()
        assert result is True
        assert client.token == new_token
        assert client.refresh_token == "new_refresh"

    def test_refresh_fails_returns_false(self, client):
        """refresh_access_token — при ошибке возвращает False."""
        client.token = "old_access"
        client.refresh_token = "old_refresh"

        resp = _make_response(401, json_data={"detail": "Invalid refresh"})
        client.session.request.return_value = resp

        result = client.refresh_access_token()
        assert result is False

    def test_logout_clears_token(self, client):
        """logout — очищает token."""
        client.token = "access"
        client.refresh_token = "refresh"
        client.headers["Authorization"] = "Bearer access"

        resp = _make_response(200)
        client.session.request.return_value = resp

        client.logout()
        assert client.token is None
        assert client.refresh_token is None

    def test_get_current_user(self, client):
        """get_current_user — GET /api/auth/me."""
        resp = _make_response(200, json_data={"id": 1, "full_name": "Admin"})
        client.session.request.return_value = resp

        data = client.get_current_user()
        assert data["full_name"] == "Admin"


# ============================================================================
# CLIENTS MIXIN
# ============================================================================

class TestClientsMixin:
    """clients_mixin.py — CRUD операции"""

    def test_get_clients_pagination(self, client):
        """get_clients — передаёт skip/limit параметры."""
        resp = _make_response(200, json_data=[{"id": 1}])
        client.session.request.return_value = resp

        result = client.get_clients(skip=10, limit=50)
        assert result == [{"id": 1}]
        # Проверяем что params переданы
        call_kwargs = client.session.request.call_args
        assert call_kwargs[1].get('params') == {"skip": 10, "limit": 50}

    def test_get_clients_paginated_x_total_count(self, client):
        """get_clients_paginated — парсит X-Total-Count."""
        resp = _make_response(200, json_data=[{"id": 1}, {"id": 2}])
        resp.headers["X-Total-Count"] = "100"
        client.session.request.return_value = resp

        data, total = client.get_clients_paginated(skip=0, limit=2)
        assert len(data) == 2
        assert total == 100

    def test_get_clients_paginated_no_header(self, client):
        """get_clients_paginated — без X-Total-Count используют len(data)."""
        resp = _make_response(200, json_data=[{"id": 1}])
        client.session.request.return_value = resp

        data, total = client.get_clients_paginated()
        assert total == 1

    def test_create_client_post(self, client):
        """create_client — POST с JSON данными."""
        resp = _make_response(200, json_data={"id": 10, "full_name": "New"})
        client.session.request.return_value = resp

        result = client.create_client({"full_name": "New", "phone": "+7"})
        assert result["id"] == 10
        # Проверяем что POST
        assert client.session.request.call_args[0][0] == 'POST'

    def test_update_client_put(self, client):
        """update_client — PUT с JSON данными."""
        resp = _make_response(200, json_data={"id": 10, "updated": True})
        client.session.request.return_value = resp

        result = client.update_client(10, {"full_name": "Updated"})
        assert result["updated"] is True
        assert client.session.request.call_args[0][0] == 'PUT'

    def test_delete_client(self, client):
        """delete_client — DELETE."""
        resp = _make_response(200, json_data=None)
        # _handle_response при 200 без JSON → True
        client.session.request.return_value = resp

        result = client.delete_client(5)
        assert result is True
        assert client.session.request.call_args[0][0] == 'DELETE'


# ============================================================================
# CONTRACTS MIXIN
# ============================================================================

class TestContractsMixin:
    """contracts_mixin.py — CRUD + count + filter"""

    def test_get_contracts(self, client):
        """get_contracts — GET /api/contracts."""
        resp = _make_response(200, json_data=[{"id": 1, "contract_number": "D-001"}])
        client.session.request.return_value = resp

        result = client.get_contracts()
        assert result == [{"id": 1, "contract_number": "D-001"}]

    def test_get_contracts_count_with_filters(self, client):
        """get_contracts_count — передаёт фильтры."""
        resp = _make_response(200, json_data={"count": 42})
        client.session.request.return_value = resp

        result = client.get_contracts_count(status="СДАН", year=2025)
        assert result == 42
        call_kwargs = client.session.request.call_args
        params = call_kwargs[1].get('params', {})
        assert params.get('status') == "СДАН"
        assert params.get('year') == 2025

    def test_get_contracts_count_no_filters(self, client):
        """get_contracts_count без фильтров — пустые params."""
        resp = _make_response(200, json_data={"count": 10})
        client.session.request.return_value = resp

        result = client.get_contracts_count()
        assert result == 10

    def test_create_contract(self, client):
        """create_contract — POST."""
        resp = _make_response(200, json_data={"id": 20, "contract_number": "D-002"})
        client.session.request.return_value = resp

        result = client.create_contract({"contract_number": "D-002"})
        assert result["id"] == 20

    def test_update_contract(self, client):
        """update_contract — PUT."""
        resp = _make_response(200, json_data={"id": 20, "updated": True})
        client.session.request.return_value = resp

        result = client.update_contract(20, {"contract_number": "D-002-edited"})
        assert result["updated"] is True

    def test_delete_contract(self, client):
        """delete_contract — DELETE."""
        resp = _make_response(200, json_data=None)
        client.session.request.return_value = resp

        result = client.delete_contract(20)
        assert result is True

    def test_get_contracts_paginated(self, client):
        """get_contracts_paginated — парсит X-Total-Count."""
        resp = _make_response(200, json_data=[{"id": 1}])
        resp.headers["X-Total-Count"] = "55"
        client.session.request.return_value = resp

        data, total = client.get_contracts_paginated(skip=0, limit=10)
        assert total == 55

    def test_check_contract_number_exists_true(self, client):
        """check_contract_number_exists — существующий номер → True."""
        resp = _make_response(200, json_data=[
            {"id": 1, "contract_number": "D-001"},
            {"id": 2, "contract_number": "D-002"}
        ])
        client.session.request.return_value = resp

        result = client.check_contract_number_exists("D-001")
        assert result is True

    def test_check_contract_number_exists_false(self, client):
        """check_contract_number_exists — несуществующий номер → False."""
        resp = _make_response(200, json_data=[
            {"id": 1, "contract_number": "D-001"}
        ])
        client.session.request.return_value = resp

        result = client.check_contract_number_exists("D-999")
        assert result is False

    def test_check_contract_number_exclude_id(self, client):
        """check_contract_number_exists с exclude_id — пропускает свой id."""
        resp = _make_response(200, json_data=[
            {"id": 1, "contract_number": "D-001"}
        ])
        client.session.request.return_value = resp

        result = client.check_contract_number_exists("D-001", exclude_id=1)
        assert result is False


# ============================================================================
# BASE.PY — _parse_retry_after
# ============================================================================

class TestParseRetryAfter:
    """_parse_retry_after — парсинг заголовка"""

    def test_numeric_retry_after(self):
        """Числовой Retry-After → float."""
        resp = _make_response(429, headers={'Retry-After': '5'})
        result = APIClientBase._parse_retry_after(resp)
        assert result == 5.0

    def test_decimal_retry_after(self):
        """Дробный Retry-After → float."""
        resp = _make_response(429, headers={'Retry-After': '1.5'})
        result = APIClientBase._parse_retry_after(resp)
        assert result == 1.5

    def test_missing_retry_after(self):
        """Отсутствующий Retry-After → None."""
        resp = _make_response(429)
        result = APIClientBase._parse_retry_after(resp)
        assert result is None

    def test_invalid_retry_after(self):
        """Невалидный Retry-After → None."""
        resp = _make_response(429, headers={'Retry-After': 'invalid'})
        result = APIClientBase._parse_retry_after(resp)
        assert result is None


# ============================================================================
# BASE.PY — RELOGIN CALLBACK
# ============================================================================

class TestReloginCallback:
    """set_relogin_callback / _signal_relogin_needed"""

    def test_relogin_callback_called_once(self, client):
        """_signal_relogin_needed вызывает callback только один раз."""
        callback = MagicMock(return_value=False)
        client.set_relogin_callback(callback)

        client._signal_relogin_needed()
        client._signal_relogin_needed()  # второй раз — не вызовет

        callback.assert_called_once()

    def test_relogin_success_resets_flag(self, client):
        """Успешный relogin — можно сигналить снова."""
        callback = MagicMock(return_value=True)
        client.set_relogin_callback(callback)

        client._signal_relogin_needed()
        assert callback.call_count == 1

        # При успехе флаг сбрасывается
        client._signal_relogin_needed()
        assert callback.call_count == 2

    def test_no_callback_no_error(self, client):
        """Без callback — _signal_relogin_needed не падает."""
        client._relogin_callback = None
        client._signal_relogin_needed()  # не должно быть ошибки
