"""
Базовый класс API клиента.
Содержит: настройку соединения, retry/timeout логику, offline кеш,
обработку ответов и управление JWT токенами.
"""
import requests
import urllib3
import time
import json
import base64
from typing import Optional, List, Dict, Any
from datetime import datetime

from .exceptions import APIError, APITimeoutError, APIConnectionError, APIAuthError, APIResponseError

# Подавление предупреждений для самоподписанных сертификатов
# SECURITY NOTE: В production с валидным SSL сертификатом установить API_VERIFY_SSL=true
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class APIClientBase:
    """
    Базовый класс API клиента.
    Обеспечивает: HTTP-сессию, retry/timeout, offline-кеш,
    обработку ответов, управление JWT токенами.
    """

    # Константы для настройки запросов
    DEFAULT_TIMEOUT = 10  # секунд для обычных запросов
    WRITE_TIMEOUT = 15  # секунд для операций записи (POST, PUT, PATCH, DELETE)
    FIRST_REQUEST_TIMEOUT = 10  # секунд для первого запроса (TCP cold start)
    MAX_RETRIES = 2  # 2 попытки для надежности
    RETRY_DELAY = 0.5  # секунд между попытками
    # ИСПРАВЛЕНИЕ 04.02.2026: Кеш offline 10 сек
    # При нестабильной сети первый запрос после паузы может быть медленным (TCP cold start)
    # 10 сек дает достаточно времени для восстановления без лишних сообщений
    OFFLINE_CACHE_DURATION = 10  # Секунд кешировать offline статус

    # Порог для автоматического обновления токена (за 5 минут до истечения)
    TOKEN_REFRESH_THRESHOLD = 300  # секунд

    def __init__(self, base_url: str, verify_ssl: bool = False):
        """
        Args:
            base_url: Базовый URL API (например: https://your-app.railway.app)
            verify_ssl: Проверять SSL сертификат
                        False для self-signed сертификатов (текущий сервер)
                        True при наличии валидного SSL от CA
        """
        self.base_url = base_url.rstrip('/')
        self.token: Optional[str] = None
        self.refresh_token: Optional[str] = None  # Refresh token для автоматического обновления
        self._token_exp: Optional[float] = None  # Время истечения access token (unix timestamp)
        self.employee_id: Optional[int] = None
        self.verify_ssl = verify_ssl
        self.headers = {
            "Content-Type": "application/json"
        }
        self._is_online = True  # Флаг статуса соединения
        self._last_offline_time = None  # Время последнего перехода в offline
        self._is_refreshing = False  # Флаг для предотвращения рекурсивного refresh
        self._offline_message_shown = False  # Флаг для подавления повторных сообщений об offline
        self._first_request = True  # Флаг для первого запроса (увеличенный таймаут)
        self.session = requests.Session()  # Переиспользуемая сессия
        # Отключаем прокси для API запросов (избегаем задержек через VPN/Clash)
        self.session.trust_env = False

    def _request(
        self,
        method: str,
        url: str,
        timeout: int = None,
        retry: bool = True,
        mark_offline: bool = True,
        **kwargs
    ) -> requests.Response:
        """
        Унифицированный метод запроса с timeout и retry логикой

        Args:
            method: HTTP метод (GET, POST, PUT, PATCH, DELETE)
            url: Полный URL запроса
            timeout: Таймаут в секундах (по умолчанию DEFAULT_TIMEOUT)
            retry: Включить retry логику
            mark_offline: Помечать клиент как offline при ошибке (по умолчанию True)
                          Для фоновых запросов (sync) передавать False, чтобы не блокировать
                          пользовательские запросы
            **kwargs: Дополнительные параметры для requests

        Returns:
            requests.Response объект

        Raises:
            APITimeoutError: При таймауте
            APIConnectionError: При ошибке соединения
            APIError: При других ошибках
        """
        # Автоматическое обновление токена перед запросом (если скоро истечёт)
        if not url.endswith('/api/auth/refresh') and not url.endswith('/api/auth/login'):
            self._auto_refresh_if_needed()

        # Если недавно были offline - сразу выбрасываем исключение без запроса
        # НО: логин всегда должен пытаться подключиться к серверу
        if mark_offline and self._is_recently_offline() and not url.endswith('/api/auth/login'):
            # Подавляем повторные сообщения об offline в консоли
            raise APIConnectionError(f"Offline режим (кеш): {url}")

        # Выбираем таймаут в зависимости от типа запроса
        if timeout is None:
            if self._first_request:
                # Первый запрос - увеличенный таймаут для TCP cold start
                timeout = self.FIRST_REQUEST_TIMEOUT
            elif method.upper() in ('POST', 'PUT', 'PATCH', 'DELETE'):
                timeout = self.WRITE_TIMEOUT
            else:
                timeout = self.DEFAULT_TIMEOUT

        kwargs.setdefault('verify', self.verify_ssl)
        kwargs.setdefault('headers', self.headers)
        kwargs['timeout'] = timeout

        last_error = None
        max_attempts = self.MAX_RETRIES if retry else 1

        for attempt in range(max_attempts):
            try:
                response = self.session.request(method, url, **kwargs)
                # Успешный запрос - сбрасываем offline статус и флаг первого запроса
                if not self._is_online:
                    print("[API] Соединение восстановлено")
                self._is_online = True
                self._first_request = False  # Первый запрос успешен, дальше обычные таймауты
                self._last_offline_time = None  # Сбрасываем время offline
                self._offline_message_shown = False  # Разрешаем показ следующего offline сообщения

                # Авторетрай на 401: обновляем токен и повторяем запрос однократно
                if (response.status_code == 401
                        and self.refresh_token
                        and not self._is_refreshing
                        and not url.endswith('/api/auth/refresh')
                        and not url.endswith('/api/auth/login')):
                    if self.refresh_access_token():
                        # Обновляем заголовки для повторного запроса
                        kwargs['headers'] = self.headers
                        retry_response = self.session.request(method, url, **kwargs)
                        return retry_response

                return response

            except requests.exceptions.Timeout as e:
                last_error = APITimeoutError(
                    f"Таймаут запроса после {timeout} сек: {url}"
                )
                if attempt < max_attempts - 1:
                    # Не выводим сообщение при каждой попытке - слишком много шума
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue  # Повторяем попытку
                else:
                    if mark_offline:
                        self._mark_offline()
                        # Сообщение выводится в _mark_offline() только при первом переходе

            except requests.exceptions.ConnectionError as e:
                last_error = APIConnectionError(
                    f"Не удалось подключиться к серверу: {self.base_url}"
                )
                if attempt < max_attempts - 1:
                    # Не выводим сообщение при каждой попытке
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue  # Повторяем попытку
                else:
                    if mark_offline:
                        self._mark_offline()
                        # Сообщение выводится в _mark_offline() только при первом переходе

            except requests.exceptions.RequestException as e:
                last_error = APIError(f"Ошибка запроса: {e}")
                # Не выводим сообщение - слишком много шума
                if attempt < max_attempts - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))

        # Все попытки исчерпаны
        if mark_offline:
            self._is_online = False
        raise last_error

    def _is_recently_offline(self) -> bool:
        """Проверить, были ли мы недавно offline (в пределах OFFLINE_CACHE_DURATION)"""
        if self._last_offline_time is None:
            return False
        elapsed = time.time() - self._last_offline_time
        return elapsed < self.OFFLINE_CACHE_DURATION

    def _mark_offline(self):
        """Отметить переход в offline режим"""
        was_online = self._is_online
        self._is_online = False
        self._last_offline_time = time.time()
        # Выводим сообщение только при первом переходе в offline
        if was_online and not self._offline_message_shown:
            print("[API] Переход в offline режим")
            self._offline_message_shown = True

    def reset_offline_cache(self):
        """
        ИСПРАВЛЕНИЕ 30.01.2026: Сбросить кеш offline статуса
        Используется OfflineManager после успешного ping для координации
        """
        self._last_offline_time = None
        self._offline_message_shown = False

    def set_offline_mode(self, offline: bool = True):
        """
        Принудительная установка offline режима.
        Используется после offline логина чтобы предотвратить ненужные API запросы.
        """
        self._is_online = not offline
        if offline:
            # Устанавливаем время offline далеко в будущее чтобы кеш не истекал
            self._last_offline_time = time.time() + 86400  # +24 часа
            print("[API] Принудительно установлен OFFLINE режим")
        else:
            self._last_offline_time = None
            print("[API] Принудительно установлен ONLINE режим")

    def force_online_check(self) -> bool:
        """
        ИСПРАВЛЕНИЕ 30.01.2026: Принудительная проверка соединения
        Игнорирует кеш и делает реальный запрос к серверу

        Returns:
            True если сервер доступен, False если нет
        """
        try:
            # Сбрасываем кеш перед проверкой
            old_offline_time = self._last_offline_time
            self._last_offline_time = None

            # Делаем быстрый запрос к health endpoint
            response = self.session.get(
                f"{self.base_url}/",
                timeout=5,
                verify=self.verify_ssl
            )

            if response.status_code == 200:
                self._is_online = True
                print("[API] Принудительная проверка: сервер доступен")
                return True
            else:
                self._is_online = False
                self._last_offline_time = old_offline_time or time.time()
                print(f"[API] Принудительная проверка: сервер вернул {response.status_code}")
                return False

        except Exception as e:
            self._is_online = False
            self._last_offline_time = old_offline_time or time.time()
            print(f"[API] Принудительная проверка: ошибка - {e}")
            return False

    def _handle_response(self, response: requests.Response, success_codes: list = None) -> Any:
        """
        Обработка ответа сервера

        Args:
            response: Ответ сервера
            success_codes: Список успешных кодов (по умолчанию [200])

        Returns:
            JSON данные ответа

        Raises:
            APIAuthError: При ошибке аутентификации (401, 403)
            APIResponseError: При других ошибках
        """
        success_codes = success_codes or [200]

        if response.status_code in success_codes:
            try:
                return response.json()
            except ValueError:
                return True  # Для ответов без JSON

        # Обработка ошибок
        error_detail = self._extract_error_detail(response)

        if response.status_code == 401:
            # Пробуем обновить токен через refresh_token
            if self.refresh_token and not self._is_refreshing:
                if self.refresh_access_token():
                    # Токен обновлен, но нужно повторить запрос в вызывающем коде
                    raise APIAuthError("Токен обновлен, повторите запрос")
            raise APIAuthError("Требуется авторизация")
        elif response.status_code == 403:
            raise APIAuthError(error_detail or "Доступ запрещён")
        elif response.status_code == 429:
            raise APIResponseError(
                f"Слишком много попыток. {error_detail}",
                status_code=response.status_code
            )
        else:
            raise APIResponseError(
                f"Ошибка сервера (HTTP {response.status_code}): {error_detail}",
                status_code=response.status_code
            )

    def _extract_error_detail(self, response: requests.Response) -> str:
        """Извлечь детали ошибки из ответа"""
        try:
            if 'application/json' in response.headers.get('content-type', ''):
                return response.json().get('detail', 'Неизвестная ошибка')
        except (ValueError, AttributeError):
            pass
        return response.text or 'Неизвестная ошибка'

    @property
    def is_online(self) -> bool:
        """Статус соединения с сервером"""
        return self._is_online

    def _extract_token_expiry(self, token: str) -> Optional[float]:
        """Извлечь время истечения из JWT токена (без проверки подписи)"""
        try:
            # JWT = header.payload.signature — декодируем payload
            parts = token.split('.')
            if len(parts) != 3:
                return None
            # Добавляем padding для base64
            payload_b64 = parts[1] + '=' * (4 - len(parts[1]) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return payload.get('exp')
        except Exception:
            return None

    def _is_token_expiring_soon(self) -> bool:
        """Проверить, истекает ли access token в ближайшее время"""
        if self._token_exp is None:
            return False
        remaining = self._token_exp - time.time()
        return remaining < self.TOKEN_REFRESH_THRESHOLD

    def _auto_refresh_if_needed(self):
        """Автоматически обновить access token если он скоро истечёт"""
        if not self.token or not self.refresh_token:
            return
        if self._is_token_expiring_soon() and not self._is_refreshing:
            self.refresh_access_token()

    def set_token(self, token: str, refresh_token: str = None):
        """Установить JWT токен для аутентификации"""
        self.token = token
        self._token_exp = self._extract_token_expiry(token)
        self.headers["Authorization"] = f"Bearer {token}"
        if refresh_token:
            self.refresh_token = refresh_token

    def clear_token(self):
        """Очистить токен"""
        self.token = None
        self.refresh_token = None
        self._token_exp = None
        if "Authorization" in self.headers:
            del self.headers["Authorization"]
