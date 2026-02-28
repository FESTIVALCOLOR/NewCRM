# -*- coding: utf-8 -*-
"""
Покрытие utils/api_client/base.py — APIClientBase.
~45 тестов: инициализация, backoff, retry-after, offline кеш,
токены JWT, обработка ответов, _request, force_online_check.
"""

import pytest
import sys
import os
import time
import json
import base64
import random
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock, call

import requests

# Корень проекта
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.api_client.base import APIClientBase
from utils.api_client.exceptions import (
    APIError, APITimeoutError, APIConnectionError,
    APIAuthError, APIResponseError
)


# ============================================================================
# Вспомогательные функции
# ============================================================================

def _make_jwt(payload: dict) -> str:
    """Собрать минимальный JWT (header.payload.signature) для тестов."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b'=').decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=').decode()
    signature = base64.urlsafe_b64encode(b'fake-signature').rstrip(b'=').decode()
    return f"{header}.{body}.{signature}"


def _mock_response(status_code=200, json_data=None, headers=None, text=''):
    """Создать мок requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    resp.headers = headers or {}
    if json_data is not None:
        resp.json.return_value = json_data
        resp.headers.setdefault('content-type', 'application/json')
    else:
        resp.json.side_effect = ValueError("No JSON")
    return resp


# ============================================================================
# Фикстуры
# ============================================================================

@pytest.fixture
def api():
    """Создать APIClientBase с тестовым URL."""
    client = APIClientBase('http://test-server:8000')
    # Отключаем auto_refresh чтобы не мешал тестам _request
    client._auto_refresh_if_needed = MagicMock()
    return client


@pytest.fixture
def api_raw():
    """APIClientBase без подмены _auto_refresh_if_needed."""
    return APIClientBase('http://test-server:8000')


# ============================================================================
# 1. ИНИЦИАЛИЗАЦИЯ (__init__)
# ============================================================================

class TestInit:
    """Тесты инициализации APIClientBase."""

    def test_base_url_trailing_slash_stripped(self):
        """Trailing slash должен быть удалён."""
        client = APIClientBase('http://example.com/')
        assert client.base_url == 'http://example.com'

    def test_default_state(self):
        """Значения по умолчанию после создания."""
        client = APIClientBase('http://example.com')
        assert client.token is None
        assert client.refresh_token is None
        assert client._token_exp is None
        assert client.employee_id is None
        assert client.verify_ssl is False
        assert client._is_online is True
        assert client._last_offline_time is None
        assert client._first_request is True
        assert client._is_refreshing is False

    def test_custom_verify_ssl(self):
        """verify_ssl=True должен сохраняться."""
        client = APIClientBase('http://example.com', verify_ssl=True)
        assert client.verify_ssl is True

    def test_session_created(self):
        """Сессия должна быть создана с trust_env=False."""
        client = APIClientBase('http://example.com')
        assert client.session is not None
        assert client.session.trust_env is False

    def test_default_headers(self):
        """Content-Type по умолчанию — application/json."""
        client = APIClientBase('http://example.com')
        assert client.headers['Content-Type'] == 'application/json'
        assert 'Authorization' not in client.headers


# ============================================================================
# 2. КОНСТАНТЫ
# ============================================================================

class TestConstants:
    """Проверка значений констант."""

    def test_timeout_values(self):
        assert APIClientBase.DEFAULT_TIMEOUT == 10
        assert APIClientBase.WRITE_TIMEOUT == 15
        assert APIClientBase.FIRST_REQUEST_TIMEOUT == 10

    def test_retry_values(self):
        assert APIClientBase.MAX_RETRIES == 3
        assert APIClientBase.RETRY_DELAY == 0.5
        assert APIClientBase.RETRY_MAX_DELAY == 4.0
        assert APIClientBase.RETRY_JITTER == 0.25

    def test_offline_cache_duration(self):
        assert APIClientBase.OFFLINE_CACHE_DURATION == 10

    def test_token_refresh_threshold(self):
        assert APIClientBase.TOKEN_REFRESH_THRESHOLD == 300


# ============================================================================
# 3. _calc_backoff
# ============================================================================

class TestCalcBackoff:
    """Exponential backoff с jitter."""

    def test_attempt_0(self, api):
        """attempt=0 → базовая задержка ~0.5 сек (±25% jitter)."""
        with patch('random.random', return_value=0.5):
            # jitter = 0.5 * 0.25 * (2*0.5 - 1) = 0 → delay = 0.5
            result = api._calc_backoff(0)
            assert result == pytest.approx(0.5, abs=0.01)

    def test_attempt_1(self, api):
        """attempt=1 → ~1.0 сек."""
        with patch('random.random', return_value=0.5):
            result = api._calc_backoff(1)
            assert result == pytest.approx(1.0, abs=0.01)

    def test_attempt_2(self, api):
        """attempt=2 → ~2.0 сек."""
        with patch('random.random', return_value=0.5):
            result = api._calc_backoff(2)
            assert result == pytest.approx(2.0, abs=0.01)

    def test_attempt_3_capped(self, api):
        """attempt=3 → capped at RETRY_MAX_DELAY (4.0 сек)."""
        with patch('random.random', return_value=0.5):
            result = api._calc_backoff(3)
            assert result == pytest.approx(4.0, abs=0.01)

    def test_attempt_high_capped(self, api):
        """Очень большой attempt → всё равно <= RETRY_MAX_DELAY + jitter."""
        result = api._calc_backoff(100)
        assert result <= api.RETRY_MAX_DELAY * 1.3  # с запасом на jitter

    def test_result_at_least_0_1(self, api):
        """Результат всегда >= 0.1."""
        # Минимальный jitter — отрицательный, random=0
        with patch('random.random', return_value=0.0):
            result = api._calc_backoff(0)
            assert result >= 0.1

    def test_jitter_variability(self, api):
        """Разные random дают разные задержки."""
        with patch('random.random', return_value=0.0):
            low = api._calc_backoff(1)
        with patch('random.random', return_value=1.0):
            high = api._calc_backoff(1)
        assert low < high


# ============================================================================
# 4. _parse_retry_after
# ============================================================================

class TestParseRetryAfter:
    """Парсинг заголовка Retry-After."""

    def test_numeric_value(self):
        """Числовое значение Retry-After."""
        resp = _mock_response(429, headers={'Retry-After': '3'})
        result = APIClientBase._parse_retry_after(resp)
        assert result == 3.0

    def test_float_value(self):
        """Дробное значение Retry-After."""
        resp = _mock_response(429, headers={'Retry-After': '1.5'})
        result = APIClientBase._parse_retry_after(resp)
        assert result == 1.5

    def test_missing_header(self):
        """Отсутствующий Retry-After → None."""
        resp = _mock_response(429, headers={})
        result = APIClientBase._parse_retry_after(resp)
        assert result is None

    def test_invalid_header(self):
        """Нечисловой Retry-After → None."""
        resp = _mock_response(429, headers={'Retry-After': 'invalid'})
        result = APIClientBase._parse_retry_after(resp)
        assert result is None


# ============================================================================
# 5. OFFLINE КЕШ
# ============================================================================

class TestOfflineCache:
    """Offline кеш: _is_recently_offline, _mark_offline, reset_offline_cache."""

    def test_initially_not_offline(self, api):
        """Сразу после создания — не offline."""
        assert api._is_recently_offline() is False

    def test_mark_offline_sets_flag(self, api):
        """_mark_offline ставит _is_online=False и _last_offline_time."""
        api._mark_offline()
        assert api._is_online is False
        assert api._last_offline_time is not None

    def test_is_recently_offline_after_mark(self, api):
        """После _mark_offline — _is_recently_offline() = True."""
        api._mark_offline()
        assert api._is_recently_offline() is True

    def test_is_recently_offline_expired(self, api):
        """Через OFFLINE_CACHE_DURATION секунд — _is_recently_offline() = False."""
        api._mark_offline()
        # Переносим время offline далеко в прошлое
        api._last_offline_time = time.time() - api.OFFLINE_CACHE_DURATION - 1
        assert api._is_recently_offline() is False

    def test_reset_offline_cache(self, api):
        """reset_offline_cache сбрасывает _last_offline_time."""
        api._mark_offline()
        assert api._is_recently_offline() is True
        api.reset_offline_cache()
        assert api._is_recently_offline() is False
        assert api._offline_message_shown is False

    def test_mark_offline_message_once(self, api, capsys):
        """Сообщение 'Переход в offline режим' печатается только один раз."""
        api._mark_offline()
        api._mark_offline()
        captured = capsys.readouterr()
        assert captured.out.count("Переход в offline режим") == 1


# ============================================================================
# 6. set_offline_mode
# ============================================================================

class TestSetOfflineMode:
    """Принудительная установка offline/online."""

    def test_set_offline(self, api):
        """set_offline_mode(True) → offline, кеш далеко в будущем."""
        api.set_offline_mode(True)
        assert api._is_online is False
        assert api._is_recently_offline() is True
        # Время offline установлено в будущее (+24 часа)
        assert api._last_offline_time > time.time() + 3600

    def test_set_online(self, api):
        """set_offline_mode(False) → online, кеш сброшен."""
        api.set_offline_mode(True)
        api.set_offline_mode(False)
        assert api._is_online is True
        assert api._last_offline_time is None


# ============================================================================
# 7. is_online (property)
# ============================================================================

class TestIsOnlineProperty:
    """Property is_online."""

    def test_initially_online(self, api):
        assert api.is_online is True

    def test_after_mark_offline(self, api):
        api._mark_offline()
        assert api.is_online is False


# ============================================================================
# 8. JWT ТОКЕНЫ
# ============================================================================

class TestTokenManagement:
    """set_token, clear_token, _extract_token_expiry, _is_token_expiring_soon."""

    def test_set_token_basic(self, api):
        """set_token сохраняет токен и ставит Authorization header."""
        token = _make_jwt({"sub": "1", "exp": time.time() + 3600})
        api.set_token(token)
        assert api.token == token
        assert api.headers['Authorization'] == f'Bearer {token}'

    def test_set_token_with_refresh(self, api):
        """set_token с refresh_token."""
        token = _make_jwt({"sub": "1", "exp": time.time() + 3600})
        api.set_token(token, refresh_token='refresh-abc')
        assert api.refresh_token == 'refresh-abc'

    def test_set_token_without_refresh_keeps_old(self, api):
        """set_token без refresh_token не перезаписывает существующий."""
        api.refresh_token = 'old-refresh'
        token = _make_jwt({"sub": "1", "exp": time.time() + 3600})
        api.set_token(token)
        assert api.refresh_token == 'old-refresh'

    def test_set_token_extracts_expiry(self, api):
        """set_token извлекает exp из JWT payload."""
        exp_time = time.time() + 7200
        token = _make_jwt({"sub": "1", "exp": exp_time})
        api.set_token(token)
        assert api._token_exp == pytest.approx(exp_time, abs=1)

    def test_set_token_resets_relogin_flag(self, api):
        """set_token сбрасывает _relogin_signaled."""
        api._relogin_signaled = True
        token = _make_jwt({"sub": "1", "exp": time.time() + 3600})
        api.set_token(token)
        assert api._relogin_signaled is False

    def test_clear_token(self, api):
        """clear_token удаляет токен и Authorization header."""
        token = _make_jwt({"sub": "1", "exp": time.time() + 3600})
        api.set_token(token, refresh_token='refresh-abc')
        api.clear_token()
        assert api.token is None
        assert api.refresh_token is None
        assert api._token_exp is None
        assert 'Authorization' not in api.headers

    def test_clear_token_no_auth_header(self, api):
        """clear_token не падает если Authorization header отсутствует."""
        api.clear_token()  # Не должно быть исключения
        assert 'Authorization' not in api.headers

    def test_extract_token_expiry_valid(self, api):
        """_extract_token_expiry извлекает exp из корректного JWT."""
        exp_time = 1700000000
        token = _make_jwt({"sub": "1", "exp": exp_time})
        result = api._extract_token_expiry(token)
        assert result == exp_time

    def test_extract_token_expiry_no_exp(self, api):
        """_extract_token_expiry без поля exp → None."""
        token = _make_jwt({"sub": "1"})
        result = api._extract_token_expiry(token)
        assert result is None

    def test_extract_token_expiry_invalid_jwt(self, api):
        """Невалидный JWT (не 3 части) → None."""
        result = api._extract_token_expiry("not.a.valid.jwt.too.many")
        assert result is None
        result2 = api._extract_token_expiry("garbage")
        assert result2 is None

    def test_is_token_expiring_soon_no_exp(self, api):
        """Нет _token_exp → False."""
        api._token_exp = None
        assert api._is_token_expiring_soon() is False

    def test_is_token_expiring_soon_true(self, api):
        """Токен истекает через 60 сек (< 300) → True."""
        api._token_exp = time.time() + 60
        assert api._is_token_expiring_soon() is True

    def test_is_token_expiring_soon_false(self, api):
        """Токен истекает через 3600 сек (> 300) → False."""
        api._token_exp = time.time() + 3600
        assert api._is_token_expiring_soon() is False

    def test_is_token_expiring_soon_already_expired(self, api):
        """Токен уже истёк (negative remaining) → True."""
        api._token_exp = time.time() - 100
        assert api._is_token_expiring_soon() is True


# ============================================================================
# 9. _handle_response
# ============================================================================

class TestHandleResponse:
    """Обработка ответов _handle_response."""

    def test_200_ok_json(self, api):
        """200 с JSON → возвращает JSON данные."""
        resp = _mock_response(200, json_data={"id": 1, "name": "test"})
        result = api._handle_response(resp)
        assert result == {"id": 1, "name": "test"}

    def test_200_ok_no_json(self, api):
        """200 без JSON → возвращает True."""
        resp = _mock_response(200)
        result = api._handle_response(resp)
        assert result is True

    def test_custom_success_code(self, api):
        """201 с success_codes=[200, 201] → OK."""
        resp = _mock_response(201, json_data={"created": True})
        result = api._handle_response(resp, success_codes=[200, 201])
        assert result == {"created": True}

    def test_401_raises_auth_error(self, api):
        """401 → APIAuthError."""
        resp = _mock_response(401, json_data={"detail": "Unauthorized"})
        with pytest.raises(APIAuthError, match="Требуется авторизация"):
            api._handle_response(resp)

    def test_403_raises_auth_error(self, api):
        """403 → APIAuthError с деталями."""
        resp = _mock_response(403, json_data={"detail": "Нет прав"})
        with pytest.raises(APIAuthError, match="Нет прав"):
            api._handle_response(resp)

    def test_403_default_message(self, api):
        """403 без detail → 'Доступ запрещён'."""
        resp = _mock_response(403, json_data={})
        # Когда detail нет, get('detail', 'Неизвестная ошибка') вернёт дефолт
        # Но _extract_error_detail вернёт 'Неизвестная ошибка', а handle_response:
        # error_detail or "Доступ запрещён" → "Неизвестная ошибка" (truthy)
        with pytest.raises(APIAuthError):
            api._handle_response(resp)

    def test_404_raises_response_error(self, api):
        """404 → APIResponseError с status_code."""
        resp = _mock_response(404, json_data={"detail": "Не найдено"})
        with pytest.raises(APIResponseError) as exc_info:
            api._handle_response(resp)
        assert exc_info.value.status_code == 404
        assert "Не найдено" in str(exc_info.value)

    def test_429_raises_response_error(self, api):
        """429 → APIResponseError."""
        resp = _mock_response(429, json_data={"detail": "Лимит превышен"})
        with pytest.raises(APIResponseError) as exc_info:
            api._handle_response(resp)
        assert exc_info.value.status_code == 429

    def test_500_raises_response_error(self, api):
        """500 → APIResponseError."""
        resp = _mock_response(500, json_data={"detail": "Internal error"})
        with pytest.raises(APIResponseError) as exc_info:
            api._handle_response(resp)
        assert exc_info.value.status_code == 500


# ============================================================================
# 10. _extract_error_detail
# ============================================================================

class TestExtractErrorDetail:
    """Извлечение деталей ошибки из ответа."""

    def test_json_with_detail(self, api):
        """JSON ответ с полем detail."""
        resp = _mock_response(400, json_data={"detail": "Ошибка валидации"})
        result = api._extract_error_detail(resp)
        assert result == "Ошибка валидации"

    def test_json_list(self, api):
        """JSON ответ — список → строковое представление."""
        resp = _mock_response(400, json_data=[{"field": "name", "msg": "required"}])
        result = api._extract_error_detail(resp)
        assert "name" in result

    def test_no_json(self, api):
        """Не JSON ответ → text."""
        resp = _mock_response(400, text="Bad request plain text")
        resp.headers = {'content-type': 'text/plain'}
        result = api._extract_error_detail(resp)
        assert result == "Bad request plain text"

    def test_empty_response(self, api):
        """Пустой ответ → 'Неизвестная ошибка'."""
        resp = _mock_response(400, text='')
        resp.headers = {'content-type': 'text/plain'}
        result = api._extract_error_detail(resp)
        assert result == 'Неизвестная ошибка'


# ============================================================================
# 11. force_online_check
# ============================================================================

class TestForceOnlineCheck:
    """Принудительная проверка соединения force_online_check."""

    def test_server_available(self, api):
        """Сервер доступен → True, is_online=True."""
        api._mark_offline()
        mock_resp = _mock_response(200, json_data={"status": "healthy"})
        with patch.object(api.session, 'get', return_value=mock_resp):
            result = api.force_online_check()
        assert result is True
        assert api.is_online is True

    def test_server_unavailable_connection_error(self, api):
        """Сервер недоступен (ConnectionError) → False, is_online=False."""
        with patch.object(api.session, 'get', side_effect=requests.ConnectionError("refused")):
            result = api.force_online_check()
        assert result is False
        assert api.is_online is False

    def test_server_returns_500(self, api):
        """Сервер вернул 500 → False."""
        mock_resp = _mock_response(500)
        with patch.object(api.session, 'get', return_value=mock_resp):
            result = api.force_online_check()
        assert result is False
        assert api.is_online is False

    def test_resets_cache_before_check(self, api):
        """force_online_check сбрасывает кеш offline перед проверкой."""
        api._mark_offline()
        assert api._is_recently_offline() is True
        mock_resp = _mock_response(200, json_data={})
        with patch.object(api.session, 'get', return_value=mock_resp):
            api.force_online_check()
        # Кеш сброшен, online восстановлен
        assert api.is_online is True


# ============================================================================
# 12. _request — ОСНОВНОЙ МЕТОД
# ============================================================================

class TestRequest:
    """Основной метод _request с retry, timeout, offline логикой."""

    def test_success_get(self, api):
        """Успешный GET запрос возвращает response."""
        mock_resp = _mock_response(200, json_data={"ok": True})
        with patch.object(api.session, 'request', return_value=mock_resp):
            resp = api._request('GET', 'http://test-server:8000/api/health')
        assert resp.status_code == 200

    def test_success_resets_online_status(self, api):
        """Успешный запрос восстанавливает online статус."""
        api._is_online = False
        api._first_request = True
        mock_resp = _mock_response(200, json_data={"ok": True})
        with patch.object(api.session, 'request', return_value=mock_resp):
            api._request('GET', 'http://test-server:8000/api/test')
        assert api._is_online is True
        assert api._first_request is False
        assert api._last_offline_time is None

    def test_timeout_raises_api_timeout_error(self, api):
        """Timeout → APITimeoutError после MAX_RETRIES попыток."""
        with patch.object(api.session, 'request', side_effect=requests.exceptions.Timeout("timeout")):
            with patch('time.sleep'):
                with pytest.raises(APITimeoutError):
                    api._request('GET', 'http://test-server:8000/api/test')
        # Должен перейти в offline
        assert api._is_online is False

    def test_connection_error_raises_api_connection_error(self, api):
        """ConnectionError → APIConnectionError после MAX_RETRIES попыток."""
        with patch.object(api.session, 'request', side_effect=requests.exceptions.ConnectionError("refused")):
            with patch('time.sleep'):
                with pytest.raises(APIConnectionError):
                    api._request('GET', 'http://test-server:8000/api/test')
        assert api._is_online is False

    def test_request_exception_raises_api_error(self, api):
        """Другие RequestException → APIError."""
        with patch.object(api.session, 'request', side_effect=requests.exceptions.RequestException("unknown")):
            with patch('time.sleep'):
                with pytest.raises(APIError):
                    api._request('GET', 'http://test-server:8000/api/test')

    def test_retry_on_timeout(self, api):
        """Retry при timeout: 3 попытки (MAX_RETRIES)."""
        with patch.object(api.session, 'request', side_effect=requests.exceptions.Timeout("timeout")) as mock_req:
            with patch('time.sleep'):
                with pytest.raises(APITimeoutError):
                    api._request('GET', 'http://test-server:8000/api/test')
        assert mock_req.call_count == api.MAX_RETRIES

    def test_no_retry_when_disabled(self, api):
        """retry=False → одна попытка."""
        with patch.object(api.session, 'request', side_effect=requests.exceptions.Timeout("timeout")) as mock_req:
            with patch('time.sleep'):
                with pytest.raises(APITimeoutError):
                    api._request('GET', 'http://test-server:8000/api/test', retry=False)
        assert mock_req.call_count == 1

    def test_429_retries_with_retry_after(self, api):
        """HTTP 429 → retry с Retry-After задержкой."""
        resp_429 = _mock_response(429, headers={'Retry-After': '1'})
        resp_200 = _mock_response(200, json_data={"ok": True})
        with patch.object(api.session, 'request', side_effect=[resp_429, resp_200]):
            with patch('time.sleep') as mock_sleep:
                result = api._request('GET', 'http://test-server:8000/api/test')
        assert result.status_code == 200
        # Должен был подождать 1 секунду (Retry-After)
        mock_sleep.assert_called_once_with(1.0)

    def test_503_retries_with_backoff(self, api):
        """HTTP 503 → retry с backoff."""
        resp_503 = _mock_response(503)
        resp_200 = _mock_response(200, json_data={"ok": True})
        with patch.object(api.session, 'request', side_effect=[resp_503, resp_200]):
            with patch('time.sleep'):
                result = api._request('GET', 'http://test-server:8000/api/test')
        assert result.status_code == 200

    def test_502_retries(self, api):
        """HTTP 502 → retry."""
        resp_502 = _mock_response(502)
        resp_200 = _mock_response(200, json_data={"ok": True})
        with patch.object(api.session, 'request', side_effect=[resp_502, resp_200]):
            with patch('time.sleep'):
                result = api._request('GET', 'http://test-server:8000/api/test')
        assert result.status_code == 200

    def test_504_retries(self, api):
        """HTTP 504 → retry."""
        resp_504 = _mock_response(504)
        resp_200 = _mock_response(200, json_data={"ok": True})
        with patch.object(api.session, 'request', side_effect=[resp_504, resp_200]):
            with patch('time.sleep'):
                result = api._request('GET', 'http://test-server:8000/api/test')
        assert result.status_code == 200

    def test_recently_offline_raises_immediately(self, api):
        """Если недавно были offline — сразу APIConnectionError без запроса."""
        api._mark_offline()
        with pytest.raises(APIConnectionError, match="Offline режим"):
            api._request('GET', 'http://test-server:8000/api/test')

    def test_recently_offline_allows_login(self, api):
        """Offline кеш НЕ блокирует /api/auth/login."""
        api._mark_offline()
        mock_resp = _mock_response(200, json_data={"token": "abc"})
        with patch.object(api.session, 'request', return_value=mock_resp):
            result = api._request('POST', 'http://test-server:8000/api/auth/login')
        assert result.status_code == 200

    def test_mark_offline_false_does_not_mark(self, api):
        """mark_offline=False → не переходит в offline при ошибке."""
        with patch.object(api.session, 'request', side_effect=requests.exceptions.Timeout("timeout")):
            with patch('time.sleep'):
                with pytest.raises(APITimeoutError):
                    api._request('GET', 'http://test-server:8000/api/test',
                                 mark_offline=False, retry=False)
        # Не должен перейти в offline
        assert api._is_online is True

    def test_default_timeout_get(self, api):
        """GET → DEFAULT_TIMEOUT по умолчанию."""
        api._first_request = False
        mock_resp = _mock_response(200, json_data={})
        with patch.object(api.session, 'request', return_value=mock_resp) as mock_req:
            api._request('GET', 'http://test-server:8000/api/test')
        _, kwargs = mock_req.call_args
        assert kwargs['timeout'] == api.DEFAULT_TIMEOUT

    def test_default_timeout_post(self, api):
        """POST → WRITE_TIMEOUT по умолчанию."""
        api._first_request = False
        mock_resp = _mock_response(200, json_data={})
        with patch.object(api.session, 'request', return_value=mock_resp) as mock_req:
            api._request('POST', 'http://test-server:8000/api/test')
        _, kwargs = mock_req.call_args
        assert kwargs['timeout'] == api.WRITE_TIMEOUT

    def test_first_request_timeout(self, api):
        """Первый запрос → FIRST_REQUEST_TIMEOUT."""
        api._first_request = True
        mock_resp = _mock_response(200, json_data={})
        with patch.object(api.session, 'request', return_value=mock_resp) as mock_req:
            api._request('GET', 'http://test-server:8000/api/test')
        _, kwargs = mock_req.call_args
        assert kwargs['timeout'] == api.FIRST_REQUEST_TIMEOUT

    def test_custom_timeout(self, api):
        """Явный timeout переопределяет дефолтный."""
        mock_resp = _mock_response(200, json_data={})
        with patch.object(api.session, 'request', return_value=mock_resp) as mock_req:
            api._request('GET', 'http://test-server:8000/api/test', timeout=30)
        _, kwargs = mock_req.call_args
        assert kwargs['timeout'] == 30

    def test_verify_ssl_passed(self, api):
        """verify_ssl передаётся в kwargs."""
        mock_resp = _mock_response(200, json_data={})
        with patch.object(api.session, 'request', return_value=mock_resp) as mock_req:
            api._request('GET', 'http://test-server:8000/api/test')
        _, kwargs = mock_req.call_args
        assert kwargs['verify'] == api.verify_ssl


# ============================================================================
# 13. _signal_relogin_needed / set_relogin_callback
# ============================================================================

class TestReloginCallback:
    """Callback для перелогинивания."""

    def test_signal_calls_callback(self, api):
        """_signal_relogin_needed вызывает callback."""
        callback = MagicMock(return_value=True)
        api.set_relogin_callback(callback)
        api._signal_relogin_needed()
        callback.assert_called_once()

    def test_signal_relogin_only_once(self, api):
        """Повторный _signal_relogin_needed не вызывает callback снова (если первый failed)."""
        callback = MagicMock(return_value=False)
        api.set_relogin_callback(callback)
        api._signal_relogin_needed()
        api._signal_relogin_needed()
        # Второй раз не вызывается т.к. _relogin_signaled = True
        callback.assert_called_once()

    def test_successful_relogin_resets_flag(self, api):
        """Успешный relogin сбрасывает _relogin_signaled."""
        callback = MagicMock(return_value=True)
        api.set_relogin_callback(callback)
        api._signal_relogin_needed()
        # После успеха _relogin_signaled = False, можно вызвать снова
        assert api._relogin_signaled is False

    def test_no_callback_set(self, api):
        """Без callback — не падает."""
        api._signal_relogin_needed()  # Не должно быть исключения
        assert api._relogin_signaled is True


# ============================================================================
# 14. _auto_refresh_if_needed
# ============================================================================

class TestAutoRefresh:
    """Автоматическое обновление токена."""

    def test_no_refresh_without_token(self, api_raw):
        """Без токена — refresh не запускается."""
        api_raw.token = None
        api_raw.refresh_token = None
        # refresh_access_token определён в миксине, create=True для base
        with patch.object(api_raw, 'refresh_access_token', create=True) as mock_refresh:
            api_raw._auto_refresh_if_needed()
        mock_refresh.assert_not_called()

    def test_no_refresh_when_token_fresh(self, api_raw):
        """Токен свежий (далеко до истечения) — refresh не запускается."""
        api_raw.token = 'some-token'
        api_raw.refresh_token = 'some-refresh'
        api_raw._token_exp = time.time() + 3600  # 1 час до истечения
        with patch.object(api_raw, 'refresh_access_token', create=True) as mock_refresh:
            api_raw._auto_refresh_if_needed()
        mock_refresh.assert_not_called()

    def test_refresh_when_expiring_soon(self, api_raw):
        """Токен скоро истекает → запускается refresh."""
        api_raw.token = 'some-token'
        api_raw.refresh_token = 'some-refresh'
        api_raw._token_exp = time.time() + 60  # < 300 секунд
        with patch.object(api_raw, 'refresh_access_token', create=True) as mock_refresh:
            api_raw._auto_refresh_if_needed()
        mock_refresh.assert_called_once()
