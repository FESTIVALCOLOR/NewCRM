"""
API клиент для взаимодействия с сервером
Используется в PyQt5 клиенте
"""
import requests
import urllib3
import time
from typing import Optional, List, Dict, Any
from datetime import datetime

# Отключаем предупреждения о самоподписанных сертификатах (только для разработки!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# =========================
# КЛАССЫ ИСКЛЮЧЕНИЙ API
# =========================

class APIError(Exception):
    """Базовая ошибка API"""
    pass


class APITimeoutError(APIError):
    """Ошибка таймаута запроса"""
    pass


class APIConnectionError(APIError):
    """Ошибка соединения с сервером"""
    pass


class APIAuthError(APIError):
    """Ошибка аутентификации"""
    pass


class APIResponseError(APIError):
    """Ошибка ответа сервера"""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class APIClient:
    """
    Клиент для работы с REST API сервера
    С поддержкой timeout, retry и fallback логики
    """

    # Константы для настройки запросов
    DEFAULT_TIMEOUT = 10  # секунд для обычных запросов
    WRITE_TIMEOUT = 15  # секунд для операций записи (POST, PUT, PATCH, DELETE)
    FIRST_REQUEST_TIMEOUT = 20  # секунд для первого запроса (TCP cold start)
    MAX_RETRIES = 2  # 2 попытки для надежности
    RETRY_DELAY = 0.5  # секунд между попытками
    # ИСПРАВЛЕНИЕ 04.02.2026: Кеш offline 10 сек
    # При нестабильной сети первый запрос после паузы может быть медленным (TCP cold start)
    # 10 сек дает достаточно времени для восстановления без лишних сообщений
    OFFLINE_CACHE_DURATION = 10  # Секунд кешировать offline статус

    def __init__(self, base_url: str, verify_ssl: bool = False):
        """
        Args:
            base_url: Базовый URL API (например: https://your-app.railway.app)
            verify_ssl: Проверять SSL сертификат (False для самоподписанных)
        """
        self.base_url = base_url.rstrip('/')
        self.token: Optional[str] = None
        self.refresh_token: Optional[str] = None  # Refresh token для автоматического обновления
        self.employee_id: Optional[int] = None
        self.verify_ssl = verify_ssl  # Для самоподписанных сертификатов = False
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
        # Если недавно были offline - сразу выбрасываем исключение без запроса
        # НО: только если это не фоновый запрос (mark_offline=True)
        if mark_offline and self._is_recently_offline():
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
            raise APIAuthError("Доступ запрещён")
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

    def set_token(self, token: str, refresh_token: str = None):
        """Установить JWT токен для аутентификации"""
        self.token = token
        self.headers["Authorization"] = f"Bearer {token}"
        if refresh_token:
            self.refresh_token = refresh_token

    def clear_token(self):
        """Очистить токен"""
        self.token = None
        self.refresh_token = None
        if "Authorization" in self.headers:
            del self.headers["Authorization"]

    # =========================
    # АУТЕНТИФИКАЦИЯ
    # =========================

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Вход в систему

        Args:
            username: Логин
            password: Пароль

        Returns:
            dict с токеном и информацией о пользователе

        Raises:
            APIAuthError: При ошибке аутентификации
            APIConnectionError: При ошибке соединения
        """
        response = self._request(
            'POST',
            f"{self.base_url}/api/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        data = self._handle_response(response)
        # Сохраняем оба токена
        self.set_token(data["access_token"], data.get("refresh_token"))
        self.employee_id = data["employee_id"]
        return data

    def refresh_access_token(self) -> bool:
        """
        Обновить access_token с помощью refresh_token

        Returns:
            True если токен успешно обновлен, False если нужен повторный логин
        """
        if not self.refresh_token or self._is_refreshing:
            return False

        self._is_refreshing = True
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/auth/refresh",
                params={"refresh_token": self.refresh_token},
                mark_offline=False  # Не помечаем offline при ошибке refresh
            )

            if response.status_code == 200:
                data = response.json()
                self.set_token(data["access_token"], self.refresh_token)
                self.employee_id = data.get("employee_id", self.employee_id)
                print("[API] Токен успешно обновлен через refresh_token")
                return True
            else:
                print(f"[API] Ошибка обновления токена: {response.status_code}")
                return False
        except Exception as e:
            print(f"[API] Ошибка refresh_token: {e}")
            return False
        finally:
            self._is_refreshing = False

    def logout(self) -> bool:
        """
        Выход из системы

        Returns:
            True если успешно
        """
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/auth/logout",
                retry=False  # Не повторять при выходе
            )
            return response.status_code == 200
        except APIError as e:
            print(f"[API] Ошибка выхода: {e}")
            return False
        finally:
            self.clear_token()

    def get_current_user(self) -> Dict[str, Any]:
        """
        Получить информацию о текущем пользователе

        Returns:
            dict с данными пользователя
        """
        response = self._request('GET', f"{self.base_url}/api/auth/me")
        return self._handle_response(response)

    # =========================
    # КЛИЕНТЫ
    # =========================

    def get_clients(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить список клиентов"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/clients",
            params={"skip": skip, "limit": limit}
        )
        return self._handle_response(response)

    def get_client(self, client_id: int) -> Dict[str, Any]:
        """Получить клиента по ID"""
        response = self._request('GET', f"{self.base_url}/api/clients/{client_id}")
        return self._handle_response(response)

    def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать нового клиента"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/clients",
            json=client_data
        )
        return self._handle_response(response)

    def update_client(self, client_id: int, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить клиента"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/clients/{client_id}",
            json=client_data
        )
        return self._handle_response(response)

    def delete_client(self, client_id: int) -> bool:
        """Удалить клиента"""
        response = self._request('DELETE', f"{self.base_url}/api/clients/{client_id}")
        self._handle_response(response)
        return True

    # =========================
    # ДОГОВОРЫ
    # =========================

    def get_contracts(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить список договоров"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/contracts",
            params={"skip": skip, "limit": limit}
        )
        return self._handle_response(response)

    def get_contract(self, contract_id: int) -> Dict[str, Any]:
        """Получить договор по ID"""
        response = self._request('GET', f"{self.base_url}/api/contracts/{contract_id}")
        return self._handle_response(response)

    def create_contract(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать новый договор"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/contracts",
            json=contract_data
        )
        return self._handle_response(response)

    def update_contract(self, contract_id: int, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить договор"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/contracts/{contract_id}",
            json=contract_data
        )
        return self._handle_response(response)

    def update_contract_files(self, contract_id: int, files_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновить файлы договора (замер, референсы, фотофиксация)

        Args:
            contract_id: ID договора
            files_data: Словарь с данными файлов:
                - measurement_image_link: ссылка на изображение замера
                - measurement_file_name: имя файла замера
                - measurement_yandex_path: путь на Яндекс.Диске
                - measurement_date: дата замера
                - contract_file_link: ссылка на договор
                - tech_task_link: ссылка на ТЗ
        """
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/contracts/{contract_id}/files",
            json=files_data
        )
        return self._handle_response(response)

    def delete_contract(self, contract_id: int) -> bool:
        """Удалить договор"""
        response = self._request('DELETE', f"{self.base_url}/api/contracts/{contract_id}")
        self._handle_response(response)
        return True

    def check_contract_number_exists(self, contract_number: str, exclude_id: int = None) -> bool:
        """Проверить существование номера договора

        Args:
            contract_number: Номер договора для проверки
            exclude_id: ID договора, который нужно исключить из проверки (для редактирования)
        """
        try:
            contracts = self.get_contracts(skip=0, limit=10000)
            for contract in contracts:
                if contract.get('contract_number') == contract_number:
                    contract_id = contract.get('id')
                    # Если передан exclude_id, пропускаем этот договор
                    if exclude_id is not None and contract_id == exclude_id:
                        continue
                    return True
            return False
        except Exception as e:
            print(f"[API] Ошибка проверки номера договора: {e}")
            return False

    # =========================
    # СОТРУДНИКИ
    # =========================

    def get_employees(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить список сотрудников"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/employees",
            params={"skip": skip, "limit": limit}
        )
        return self._handle_response(response)

    def get_employees_by_position(self, position: str) -> List[Dict[str, Any]]:
        """Получить сотрудников по должности (фильтрация на клиенте)"""
        all_employees = self.get_employees(limit=500)
        return [
            emp for emp in all_employees
            if emp.get('position') == position or emp.get('secondary_position') == position
        ]

    def get_employee(self, employee_id: int) -> Dict[str, Any]:
        """Получить сотрудника по ID"""
        response = self._request('GET', f"{self.base_url}/api/employees/{employee_id}")
        return self._handle_response(response)

    def create_employee(self, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать нового сотрудника"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/employees",
            json=employee_data
        )
        return self._handle_response(response)

    def update_employee(self, employee_id: int, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить сотрудника"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/employees/{employee_id}",
            json=employee_data
        )
        return self._handle_response(response)

    def delete_employee(self, employee_id: int) -> bool:
        """Удалить сотрудника"""
        response = self._request('DELETE', f"{self.base_url}/api/employees/{employee_id}")
        self._handle_response(response)
        return True

    # =========================
    # CRM КАРТОЧКИ
    # =========================

    def get_crm_cards(self, project_type: str) -> List[Dict]:
        """
        Получить CRM карточки по типу проекта

        Args:
            project_type: Тип проекта ("Индивидуальный" или "Шаблонный")

        Returns:
            Список карточек с полной информацией
        """
        response = self._request(
            'GET',
            f"{self.base_url}/api/crm/cards",
            params={"project_type": project_type}
        )
        return self._handle_response(response)

    def get_crm_card(self, card_id: int) -> Dict:
        """
        Получить одну CRM карточку

        Args:
            card_id: ID карточки

        Returns:
            Данные карточки с исполнителями стадий
        """
        # Пробуем получить через специальный endpoint
        try:
            response = self._request('GET', f"{self.base_url}/api/crm/cards/{card_id}")
            if response.status_code == 200:
                return self._handle_response(response)
        except Exception as e:
            print(f"[API] get_crm_card endpoint error: {e}")

        # Fallback: получаем все карточки и фильтруем по ID
        print(f"[API] Fallback: поиск карточки {card_id} через get_crm_cards")
        for project_type in ['Индивидуальный', 'Шаблонный']:
            try:
                cards = self.get_crm_cards(project_type)
                for card in cards:
                    if card.get('id') == card_id:
                        print(f"[API] Карточка {card_id} найдена в {project_type}")
                        return card
            except Exception as e:
                print(f"[API] Ошибка поиска в {project_type}: {e}")

        raise APIError(f"CRM карточка с ID {card_id} не найдена")

    def create_crm_card(self, card_data: Dict[str, Any]) -> Dict:
        """
        Создать новую CRM карточку

        Args:
            card_data: Данные карточки (contract_id, column_name, и др.)

        Returns:
            Созданная карточка
        """
        response = self._request(
            'POST',
            f"{self.base_url}/api/crm/cards",
            json=card_data
        )
        return self._handle_response(response)

    def update_crm_card(self, card_id: int, updates: Dict[str, Any]) -> Dict:
        """
        Обновить CRM карточку (частичное обновление)

        Args:
            card_id: ID карточки
            updates: Словарь с обновляемыми полями

        Returns:
            Обновлённые данные карточки
        """
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/crm/cards/{card_id}",
            json=updates
        )
        return self._handle_response(response)

    def move_crm_card(self, card_id: int, column_name: str) -> Dict:
        """
        Переместить CRM карточку в другую колонку

        Args:
            card_id: ID карточки
            column_name: Название колонки ("Новый заказ", "В работе" и т.д.)

        Returns:
            Обновлённые данные карточки
        """
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/crm/cards/{card_id}/column",
            json={"column_name": column_name}
        )
        return self._handle_response(response)

    def assign_stage_executor(self, card_id: int, stage_data: Dict[str, Any]) -> Dict:
        """
        Назначить исполнителя на стадию

        Args:
            card_id: ID карточки
            stage_data: Данные назначения
                {
                    "stage_name": str,
                    "executor_id": int,
                    "deadline": str (optional, YYYY-MM-DD)
                }

        Returns:
            Данные созданного назначения
        """
        response = self._request(
            'POST',
            f"{self.base_url}/api/crm/cards/{card_id}/stage-executor",
            json=stage_data
        )
        return self._handle_response(response)

    def complete_stage(self, card_id: int, stage_name: str, completed: bool = True) -> Dict:
        """
        Отметить стадию как завершённую

        Args:
            card_id: ID карточки
            stage_name: Название стадии
            completed: True - завершена, False - отменить завершение

        Returns:
            Обновлённые данные назначения
        """
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/crm/cards/{card_id}/stage-executor/{stage_name}",
            json={"completed": completed}
        )
        return self._handle_response(response)

    # =========================
    # CRM SUPERVISION (Авторский надзор)
    # =========================

    def get_supervision_cards(self, status: str = "active") -> List[Dict]:
        """
        Получить карточки авторского надзора

        Args:
            status: "active" - активные (АВТОРСКИЙ НАДЗОР), "archived" - архивные

        Returns:
            Список карточек надзора
        """
        response = self._request(
            'GET',
            f"{self.base_url}/api/supervision/cards",
            params={"status": status}
        )
        return self._handle_response(response)

    def get_supervision_card(self, card_id: int) -> Dict:
        """Получить одну карточку надзора"""
        response = self._request('GET', f"{self.base_url}/api/supervision/cards/{card_id}")
        return self._handle_response(response)

    def create_supervision_card(self, card_data: Dict[str, Any]) -> Dict:
        """
        Создать новую карточку авторского надзора

        Args:
            card_data: Данные карточки (contract_id, column_name, и др.)

        Returns:
            Созданная карточка
        """
        response = self._request(
            'POST',
            f"{self.base_url}/api/supervision/cards",
            json=card_data
        )
        return self._handle_response(response)

    def update_supervision_card(self, card_id: int, updates: Dict[str, Any]) -> Dict:
        """Обновить карточку надзора"""
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/supervision/cards/{card_id}",
            json=updates
        )
        return self._handle_response(response)

    def move_supervision_card(self, card_id: int, column_name: str) -> Dict:
        """Переместить карточку надзора в другую колонку"""
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/supervision/cards/{card_id}/column",
            json={"column_name": column_name}
        )
        return self._handle_response(response)

    def pause_supervision_card(self, card_id: int, pause_reason: str) -> Dict:
        """Приостановить карточку надзора"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/supervision/cards/{card_id}/pause",
            json={"pause_reason": pause_reason}
        )
        return self._handle_response(response)

    def resume_supervision_card(self, card_id: int, employee_id: int = None) -> Dict:
        """Возобновить карточку надзора"""
        data = {}
        if employee_id:
            data['employee_id'] = employee_id
        response = self._request(
            'POST',
            f"{self.base_url}/api/supervision/cards/{card_id}/resume",
            json=data if data else None
        )
        return self._handle_response(response)

    # =========================
    # СИНХРОНИЗАЦИЯ
    # =========================

    def sync(self, last_sync_timestamp: datetime, entity_types: List[str],
             retry: bool = True, timeout: int = None, mark_offline: bool = False) -> Dict[str, Any]:
        """
        Получить обновления с сервера (фоновая синхронизация)

        Args:
            last_sync_timestamp: Время последней синхронизации
            entity_types: Типы сущностей ['clients', 'contracts', 'employees']
            retry: Включить retry логику (по умолчанию True)
            timeout: Таймаут в секундах (по умолчанию DEFAULT_TIMEOUT)
            mark_offline: Помечать клиент как offline при ошибке (по умолчанию False для sync)
                          Фоновая синхронизация НЕ должна блокировать пользовательские запросы

        Returns:
            dict с обновленными данными
        """
        response = self._request(
            'POST',
            f"{self.base_url}/api/sync",
            json={
                "last_sync_timestamp": last_sync_timestamp.isoformat(),
                "entity_types": entity_types
            },
            retry=retry,
            timeout=timeout,
            mark_offline=mark_offline
        )
        return self._handle_response(response)

    # =========================
    # УВЕДОМЛЕНИЯ
    # =========================

    def get_notifications(self, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Получить уведомления"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/notifications",
            params={"unread_only": unread_only}
        )
        return self._handle_response(response)

    def mark_notification_read(self, notification_id: int) -> bool:
        """Отметить уведомление как прочитанное"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/notifications/{notification_id}/read"
        )
        return response.status_code == 200

    # =========================
    # HEALTH CHECK
    # =========================

    def health_check(self) -> bool:
        """Проверка доступности сервера"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/health",
                timeout=5,
                retry=False  # Быстрая проверка без повторов
            )
            self._is_online = response.status_code == 200
            return self._is_online
        except APIError:
            self._is_online = False
            return False

    # =========================
    # PAYMENTS
    # =========================

    def get_payments_for_contract(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получить все оплаты для договора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments/contract/{contract_id}"
        )
        return self._handle_response(response)

    def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать запись оплаты"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/payments",
            json=payment_data
        )
        return self._handle_response(response)

    def get_payment(self, payment_id: int) -> Dict[str, Any]:
        """Получить данные платежа по ID"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments/{payment_id}"
        )
        return self._handle_response(response)

    def update_payment(self, payment_id: int, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить запись оплаты"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/payments/{payment_id}",
            json=payment_data
        )
        return self._handle_response(response)

    def delete_payment(self, payment_id: int) -> Dict[str, Any]:
        """Удалить запись оплаты"""
        response = self._request(
            'DELETE',
            f"{self.base_url}/api/payments/{payment_id}"
        )
        return self._handle_response(response)

    def set_payments_report_month(self, contract_id: int, report_month: str) -> Dict[str, Any]:
        """
        Установить отчетный месяц для всех платежей договора без месяца

        Args:
            contract_id: ID договора
            report_month: Отчетный месяц в формате 'YYYY-MM'

        Returns:
            Количество обновленных платежей
        """
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/payments/contract/{contract_id}/report-month",
            json={'report_month': report_month}
        )
        return self._handle_response(response)

    # =========================
    # ACTION HISTORY
    # =========================

    def get_action_history(self, entity_type: str, entity_id: int) -> List[Dict[str, Any]]:
        """Получить историю действий для сущности"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/action-history/{entity_type}/{entity_id}"
        )
        return self._handle_response(response)

    def create_action_history(self, history_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать запись истории действий"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/action-history",
            json=history_data
        )
        return self._handle_response(response)

    # =========================
    # RATES (Тарифы)
    # =========================

    def get_rates(self, project_type: str = None, role: str = None) -> List[Dict[str, Any]]:
        """Получить тарифы"""
        params = {}
        if project_type:
            params['project_type'] = project_type
        if role:
            params['role'] = role
        response = self._request(
            'GET',
            f"{self.base_url}/api/rates",
            params=params
        )
        return self._handle_response(response)

    def get_rate(self, rate_id: int) -> Dict[str, Any]:
        """Получить тариф по ID"""
        response = self._request('GET', f"{self.base_url}/api/rates/{rate_id}")
        return self._handle_response(response)

    def create_rate(self, rate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать тариф"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/rates",
            json=rate_data
        )
        return self._handle_response(response)

    def update_rate(self, rate_id: int, rate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить тариф"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/rates/{rate_id}",
            json=rate_data
        )
        return self._handle_response(response)

    def delete_rate(self, rate_id: int) -> bool:
        """Удалить тариф"""
        response = self._request('DELETE', f"{self.base_url}/api/rates/{rate_id}")
        self._handle_response(response)
        return True

    # =========================
    # SALARIES (Зарплаты)
    # =========================

    def get_salaries(self, report_month: str = None, employee_id: int = None) -> List[Dict[str, Any]]:
        """Получить зарплаты"""
        params = {}
        if report_month:
            params['report_month'] = report_month
        if employee_id:
            params['employee_id'] = employee_id
        response = self._request(
            'GET',
            f"{self.base_url}/api/salaries",
            params=params
        )
        return self._handle_response(response)

    def get_salary(self, salary_id: int) -> Dict[str, Any]:
        """Получить зарплату по ID"""
        response = self._request('GET', f"{self.base_url}/api/salaries/{salary_id}")
        return self._handle_response(response)

    def create_salary(self, salary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать запись о зарплате"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/salaries",
            json=salary_data
        )
        return self._handle_response(response)

    def update_salary(self, salary_id: int, salary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить запись о зарплате"""
        response = self._request(
            'PUT',
            f"{self.base_url}/api/salaries/{salary_id}",
            json=salary_data
        )
        return self._handle_response(response)

    def delete_salary(self, salary_id: int) -> bool:
        """Удалить запись о зарплате"""
        response = self._request('DELETE', f"{self.base_url}/api/salaries/{salary_id}")
        self._handle_response(response)
        return True

    def get_salary_report(self, report_month: str = None, employee_id: int = None, payment_type: str = None) -> Dict[str, Any]:
        """Получить отчет по зарплатам"""
        params = {}
        if report_month:
            params['report_month'] = report_month
        if employee_id:
            params['employee_id'] = employee_id
        if payment_type:
            params['payment_type'] = payment_type
        response = self._request(
            'GET',
            f"{self.base_url}/api/salaries/report",
            params=params
        )
        return self._handle_response(response)

    # =========================
    # FILES (Файлы проекта)
    # =========================

    def get_contract_files(self, contract_id: int, stage: str = None) -> List[Dict[str, Any]]:
        """Получить файлы договора"""
        params = {}
        if stage:
            params['stage'] = stage
        response = self._request(
            'GET',
            f"{self.base_url}/api/files/contract/{contract_id}",
            params=params
        )
        return self._handle_response(response)

    def create_file_record(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать запись о файле"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/files",
            json=file_data,
            mark_offline=False  # Не переходим в offline при ошибке синхронизации файлов
        )
        return self._handle_response(response)

    def delete_file_record(self, file_id: int) -> bool:
        """Удалить запись о файле"""
        response = self._request(
            'DELETE',
            f"{self.base_url}/api/files/{file_id}",
            mark_offline=False  # Не переходим в offline при ошибке синхронизации файлов
        )
        self._handle_response(response)
        return True

    # =========================
    # STAGE EXECUTORS
    # =========================

    def get_stage_executors(self, card_id: int) -> List[Dict[str, Any]]:
        """Получить исполнителей стадий для карточки"""
        response = self._request('GET', f"{self.base_url}/api/crm/cards/{card_id}")
        card_data = self._handle_response(response)
        return card_data.get('stage_executors', [])

    def update_stage_executor(self, card_id: int, stage_name: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить исполнителя стадии"""
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/crm/cards/{card_id}/stage-executor/{stage_name}",
            json=update_data
        )
        return self._handle_response(response)

    def delete_stage_executor(self, executor_id: int) -> bool:
        """Удалить назначение исполнителя"""
        response = self._request('DELETE', f"{self.base_url}/api/crm/stage-executors/{executor_id}")
        self._handle_response(response)
        return True

    # =========================
    # SUPERVISION HISTORY
    # =========================

    def get_supervision_history(self, card_id: int) -> List[Dict[str, Any]]:
        """Получить историю карточки надзора"""
        response = self._request('GET', f"{self.base_url}/api/supervision/cards/{card_id}/history")
        return self._handle_response(response)

    def add_supervision_history(self, card_id: int, entry_type: str, message: str, employee_id: int) -> Dict[str, Any]:
        """
        Добавить запись в историю надзора

        Args:
            card_id: ID карточки надзора
            entry_type: Тип записи ('moved', 'accepted', 'comment' и т.д.)
            message: Текст сообщения
            employee_id: ID сотрудника, выполнившего действие
        """
        history_data = {
            'entry_type': entry_type,
            'message': message,
            'created_by': employee_id
        }
        response = self._request(
            'POST',
            f"{self.base_url}/api/supervision/cards/{card_id}/history",
            json=history_data
        )
        return self._handle_response(response)

    # =========================
    # STATISTICS
    # =========================

    def get_dashboard_statistics(self, year: int = None, month: int = None, quarter: int = None,
                                  agent_type: str = None, city: str = None) -> Dict[str, Any]:
        """Получить статистику для дашборда"""
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if quarter:
            params['quarter'] = quarter
        if agent_type:
            params['agent_type'] = agent_type
        if city:
            params['city'] = city
        response = self._request(
            'GET',
            f"{self.base_url}/api/statistics/dashboard",
            params=params
        )
        return self._handle_response(response)

    def get_employee_statistics(self, year: int = None, month: int = None) -> List[Dict[str, Any]]:
        """Получить статистику по сотрудникам"""
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        response = self._request(
            'GET',
            f"{self.base_url}/api/statistics/employees",
            params=params
        )
        return self._handle_response(response)

    def get_contracts_by_period(self, year: int, group_by: str = "month", project_type: str = None) -> Dict[str, Any]:
        """Получить договоры сгруппированные по периоду"""
        params = {'year': year, 'group_by': group_by}
        if project_type:
            params['project_type'] = project_type
        response = self._request(
            'GET',
            f"{self.base_url}/api/statistics/contracts-by-period",
            params=params
        )
        return self._handle_response(response)

    def get_agent_types(self) -> List[str]:
        """Получить список типов агентов"""
        response = self._request('GET', f"{self.base_url}/api/statistics/agent-types")
        return self._handle_response(response)

    def get_cities(self) -> List[str]:
        """Получить список городов"""
        response = self._request('GET', f"{self.base_url}/api/statistics/cities")
        return self._handle_response(response)

    def get_payments_summary(self, year: int, month: int = None, quarter: int = None) -> Dict[str, Any]:
        """Получить сводку по платежам"""
        params = {'year': year}
        if month:
            params['month'] = month
        if quarter:
            params['quarter'] = quarter
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments/summary",
            params=params
        )
        return self._handle_response(response)

    # =========================
    # CRM CARD DELETION
    # =========================

    def delete_crm_card(self, card_id: int) -> bool:
        """Удалить CRM карточку"""
        response = self._request('DELETE', f"{self.base_url}/api/crm/cards/{card_id}")
        self._handle_response(response)
        return True

    # =========================
    # YANDEX DISK
    # =========================

    def upload_file_to_yandex(self, file_bytes: bytes, filename: str, yandex_path: str) -> Dict[str, Any]:
        """Загрузить файл на Яндекс.Диск через сервер"""
        import base64
        response = self._request(
            'POST',
            f"{self.base_url}/api/files/upload",
            json={
                'file_data': base64.b64encode(file_bytes).decode('utf-8'),
                'filename': filename,
                'yandex_path': yandex_path
            }
        )
        return self._handle_response(response)

    def create_yandex_folder(self, folder_path: str) -> Dict[str, Any]:
        """Создать папку на Яндекс.Диске"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/files/folder",
            params={'folder_path': folder_path}
        )
        return self._handle_response(response)

    def get_yandex_public_link(self, yandex_path: str) -> Dict[str, Any]:
        """Получить публичную ссылку на файл"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/files/public-link",
            params={'yandex_path': yandex_path}
        )
        return self._handle_response(response)

    def list_yandex_files(self, folder_path: str) -> Dict[str, Any]:
        """Получить список файлов в папке Яндекс.Диска"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/files/list",
            params={'folder_path': folder_path}
        )
        return self._handle_response(response)

    def delete_yandex_file(self, yandex_path: str) -> Dict[str, Any]:
        """Удалить файл с Яндекс.Диска"""
        response = self._request(
            'DELETE',
            f"{self.base_url}/api/files/yandex",
            params={'yandex_path': yandex_path}
        )
        return self._handle_response(response)

    # =========================
    # ARCHIVED CRM CARDS
    # =========================

    def get_archived_crm_cards(self, project_type: str = None) -> List[Dict]:
        """
        Получить архивные CRM карточки (статус СДАН)

        Args:
            project_type: Тип проекта ("Индивидуальный" или "Шаблонный"), если None - все

        Returns:
            Список архивных карточек
        """
        params = {}
        if project_type:
            params['project_type'] = project_type
        params['archived'] = True

        response = self._request(
            'GET',
            f"{self.base_url}/api/crm/cards",
            params=params
        )
        return self._handle_response(response)

    # =========================
    # AGENTS
    # =========================

    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Получить список всех агентов"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/agents"
            )
            return self._handle_response(response)
        except Exception:
            # Fallback: получаем через сотрудников с фильтром по должности
            employees = self.get_employees(limit=500)
            return [emp for emp in employees if emp.get('position') == 'Агент' or emp.get('secondary_position') == 'Агент']

    # =========================
    # PROJECT STATISTICS
    # =========================

    def get_project_statistics(self, project_type: str, year: int = None, quarter: int = None,
                               month: int = None, agent_type: str = None, city: str = None) -> Dict[str, Any]:
        """
        Получить статистику проектов

        Args:
            project_type: Тип проекта ("Индивидуальный" или "Шаблонный")
            year: Год
            quarter: Квартал (1-4)
            month: Месяц (1-12)
            agent_type: Тип агента
            city: Город

        Returns:
            Статистика проектов
        """
        params = {'project_type': project_type}
        if year:
            params['year'] = year
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type
        if city:
            params['city'] = city

        response = self._request(
            'GET',
            f"{self.base_url}/api/statistics/projects",
            params=params
        )
        return self._handle_response(response)

    def get_supervision_statistics(self, year: int = None, quarter: int = None,
                                   month: int = None, agent_type: str = None, city: str = None) -> Dict[str, Any]:
        """
        Получить статистику авторского надзора

        Args:
            year: Год
            quarter: Квартал (1-4)
            month: Месяц (1-12)
            agent_type: Тип агента
            city: Город

        Returns:
            Статистика надзора
        """
        params = {}
        if year:
            params['year'] = year
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type
        if city:
            params['city'] = city

        response = self._request(
            'GET',
            f"{self.base_url}/api/statistics/supervision",
            params=params
        )
        return self._handle_response(response)

    # =========================
    # PAYMENTS EXTENDED
    # =========================

    def get_all_payments(self, month: int = None, year: int = None) -> List[Dict[str, Any]]:
        """Получить все платежи с фильтрами по месяцу и году"""
        params = {}
        if month:
            params['month'] = month
        if year:
            params['year'] = year

        response = self._request(
            'GET',
            f"{self.base_url}/api/payments",
            params=params if params else None
        )
        return self._handle_response(response)

    def get_year_payments(self, year: int, include_null_month: bool = False) -> List[Dict[str, Any]]:
        """Получить платежи за год

        Args:
            year: Год
            include_null_month: Включить платежи с NULL report_month (В работе)
        """
        params = {'year': year}
        if include_null_month:
            params['include_null_month'] = 'true'
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments",
            params=params
        )
        return self._handle_response(response)

    def get_payments_by_type(self, payment_type: str, project_type_filter: str = None) -> List[Dict[str, Any]]:
        """
        Получить платежи по типу выплаты и фильтру типа проекта

        Сигнатура совпадает с вызовом в ui/salaries_tab.py:load_payment_type_data()

        Args:
            payment_type: Тип выплаты ('Индивидуальные проекты', 'Шаблонные проекты', 'Оклады', 'Авторский надзор')
            project_type_filter: Фильтр типа проекта ('Индивидуальный', 'Шаблонный', 'Авторский надзор', None)

        Returns:
            Список платежей с полями:
                - id, contract_id, employee_id, employee_name, position
                - role, stage_name, final_amount, payment_type
                - report_month, payment_status
                - contract_number, address, area, city, agent_type
                - source ('CRM' или 'Оклад')
        """
        params = {'payment_type': payment_type}
        if project_type_filter:
            params['project_type_filter'] = project_type_filter

        response = self._request(
            'GET',
            f"{self.base_url}/api/payments/by-type",
            params=params
        )
        return self._handle_response(response)

    # =========================
    # EMPLOYEE REPORTS
    # =========================

    def get_employee_report_data(self, project_type: str, period: str, year: int, quarter: int = None, month: int = None) -> Dict[str, Any]:
        """
        Получить данные для отчета по сотрудникам

        Сигнатура совпадает с database/db_manager.py:get_employee_report_data()

        Args:
            project_type: Тип проекта ('Индивидуальный' или 'Шаблонный')
            period: Период ('За год', 'За квартал', 'За месяц')
            year: Год
            quarter: Квартал (1-4), если period == 'За квартал'
            month: Месяц (1-12), если period == 'За месяц'

        Returns:
            Данные отчета с ключами:
                - completed: Список выполненных заказов
                - area: Список по площади
                - deadlines: Список просрочек
                - salaries: Список зарплат
        """
        params = {
            'project_type': project_type,
            'period': period,
            'year': int(year)  # Ensure year is int
        }
        if quarter:
            params['quarter'] = int(quarter)
        if month:
            params['month'] = int(month)

        response = self._request(
            'GET',
            f"{self.base_url}/api/reports/employee-report",
            params=params
        )
        return self._handle_response(response)

    # =========================
    # CRM CARD EXTENDED METHODS
    # =========================

    def reset_stage_completion(self, card_id: int) -> Dict[str, Any]:
        """Сбросить выполнение стадий карточки"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/crm/cards/{card_id}/reset-stages"
        )
        return self._handle_response(response)

    def reset_approval_stages(self, card_id: int) -> Dict[str, Any]:
        """Сбросить стадии согласования карточки"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/crm/cards/{card_id}/reset-approval"
        )
        return self._handle_response(response)

    # =========================
    # SUPERVISION EXTENDED METHODS
    # =========================

    def reset_supervision_stage_completion(self, card_id: int) -> Dict[str, Any]:
        """Сбросить выполнение стадий надзора"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/supervision/cards/{card_id}/reset-stages"
        )
        return self._handle_response(response)

    def complete_supervision_stage(self, card_id: int, stage_name: str = None) -> Dict[str, Any]:
        """Завершить стадию надзора"""
        data = {}
        if stage_name:
            data['stage_name'] = stage_name
        response = self._request(
            'POST',
            f"{self.base_url}/api/supervision/cards/{card_id}/complete-stage",
            json=data
        )
        return self._handle_response(response)

    def delete_supervision_order(self, contract_id: int, supervision_card_id: int) -> bool:
        """Удалить заказ надзора"""
        response = self._request(
            'DELETE',
            f"{self.base_url}/api/supervision/orders/{supervision_card_id}",
            params={'contract_id': contract_id}
        )
        self._handle_response(response)
        return True

    def get_payments_for_supervision(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получить платежи для надзора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments/supervision/{contract_id}"
        )
        return self._handle_response(response)

    def get_payments_by_supervision_card(self, supervision_card_id: int) -> List[Dict[str, Any]]:
        """ДОБАВЛЕНО 30.01.2026: Получить платежи по ID карточки надзора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments/by-supervision-card/{supervision_card_id}"
        )
        return self._handle_response(response)

    def update_payment_manual(self, payment_id: int, amount: float, report_month: str) -> Dict[str, Any]:
        """Обновить платеж вручную"""
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/payments/{payment_id}/manual",
            json={'amount': amount, 'report_month': report_month}
        )
        return self._handle_response(response)

    def get_submitted_stages(self, card_id: int) -> List[Dict[str, Any]]:
        """Получить отправленные стадии карточки"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/crm/cards/{card_id}/submitted-stages"
        )
        return self._handle_response(response)

    def get_stage_history(self, card_id: int) -> List[Dict[str, Any]]:
        """Получить историю стадий карточки"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/crm/cards/{card_id}/stage-history"
        )
        return self._handle_response(response)

    def get_supervision_addresses(self) -> List[str]:
        """Получить адреса надзора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/supervision/addresses"
        )
        return self._handle_response(response)

    def get_supervision_statistics_filtered(self, year: int = None, quarter: int = None,
                                            month: int = None, agent_type: str = None,
                                            city: str = None, address: str = None) -> Dict[str, Any]:
        """Получить отфильтрованную статистику надзора"""
        params = {}
        if year:
            params['year'] = year
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type
        if city:
            params['city'] = city
        if address:
            params['address'] = address

        response = self._request(
            'GET',
            f"{self.base_url}/api/statistics/supervision/filtered",
            params=params
        )
        return self._handle_response(response)

    def get_contract_id_by_supervision_card(self, card_id: int) -> int:
        """Получить ID договора по ID карточки надзора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/supervision/cards/{card_id}/contract"
        )
        result = self._handle_response(response)
        return result.get('contract_id')

    # =========================
    # RATES EXTENDED METHODS
    # =========================

    def get_template_rates(self, role: str = None) -> List[Dict[str, Any]]:
        """Получить шаблонные тарифы"""
        params = {}
        if role:
            params['role'] = role
        response = self._request(
            'GET',
            f"{self.base_url}/api/rates/template",
            params=params
        )
        return self._handle_response(response)

    def save_template_rate(self, role: str, area_from: float, area_to: float, price: float) -> Dict[str, Any]:
        """Сохранить шаблонный тариф"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/rates/template",
            json={
                'role': role,
                'area_from': area_from,
                'area_to': area_to,
                'price': price
            }
        )
        return self._handle_response(response)

    def save_individual_rate(self, role: str, rate_per_m2: float, stage_name: str = None) -> Dict[str, Any]:
        """Сохранить индивидуальный тариф"""
        data = {
            'role': role,
            'rate_per_m2': rate_per_m2
        }
        if stage_name:
            data['stage_name'] = stage_name
        response = self._request(
            'POST',
            f"{self.base_url}/api/rates/individual",
            json=data
        )
        return self._handle_response(response)

    def delete_individual_rate(self, role: str, stage_name: str = None) -> bool:
        """Удалить индивидуальный тариф"""
        params = {'role': role}
        if stage_name:
            params['stage_name'] = stage_name
        response = self._request(
            'DELETE',
            f"{self.base_url}/api/rates/individual",
            params=params
        )
        self._handle_response(response)
        return True

    def save_supervision_rate(self, stage_name: str, executor_rate: float, manager_rate: float) -> Dict[str, Any]:
        """Сохранить тариф надзора"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/rates/supervision",
            json={
                'stage_name': stage_name,
                'executor_rate': executor_rate,
                'manager_rate': manager_rate
            }
        )
        return self._handle_response(response)

    def save_surveyor_rate(self, city: str, price: float) -> Dict[str, Any]:
        """Сохранить тариф замерщика"""
        response = self._request(
            'POST',
            f"{self.base_url}/api/rates/surveyor",
            json={
                'city': city,
                'price': price
            }
        )
        return self._handle_response(response)

    # =========================
    # SALARY EXTENDED METHODS
    # =========================

    def add_salary(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Добавить запись о зарплате (alias для create_salary)"""
        return self.create_salary(payment_data)

    def mark_payment_as_paid(self, payment_id: int, employee_id: int) -> Dict[str, Any]:
        """Отметить платеж как выплаченный"""
        response = self._request(
            'PATCH',
            f"{self.base_url}/api/payments/{payment_id}/mark-paid",
            json={'employee_id': employee_id}
        )
        return self._handle_response(response)

    # =========================
    # ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ (совместимость с db_manager)
    # =========================

    def get_employees_by_department(self, department: str) -> List[Dict[str, Any]]:
        """Получить сотрудников по отделу"""
        all_employees = self.get_employees(limit=500)
        return [emp for emp in all_employees if emp.get('department') == department]

    def check_login_exists(self, login: str) -> bool:
        """Проверить существование логина"""
        try:
            employees = self.get_employees(limit=1000)
            for emp in employees:
                if emp.get('login') == login:
                    return True
            return False
        except Exception as e:
            print(f"[API] Ошибка проверки логина: {e}")
            return False

    def get_next_contract_number(self, year: int) -> int:
        """Получить следующий номер договора для года"""
        try:
            contracts = self.get_contracts(limit=10000)
            max_number = 0
            year_suffix = str(year)
            for contract in contracts:
                contract_number = contract.get('contract_number', '')
                if year_suffix in contract_number:
                    try:
                        number_part = contract_number.split('-')[0].replace('№', '').strip()
                        num = int(number_part)
                        if num > max_number:
                            max_number = num
                    except (ValueError, IndexError):
                        pass
            return max_number + 1
        except Exception as e:
            print(f"[API] Ошибка получения номера договора: {e}")
            return 1

    def get_crm_card_id_by_contract(self, contract_id: int) -> Optional[int]:
        """Получить ID CRM карточки по ID договора"""
        try:
            for project_type in ['Индивидуальный', 'Шаблонный']:
                cards = self.get_crm_cards(project_type)
                for card in cards:
                    if card.get('contract_id') == contract_id:
                        return card.get('id')
            return None
        except Exception as e:
            print(f"[API] Ошибка получения CRM карточки: {e}")
            return None

    def delete_order(self, contract_id: int, crm_card_id: int = None) -> bool:
        """Полное удаление заказа из системы"""
        try:
            if crm_card_id:
                self.delete_crm_card(crm_card_id)
            self.delete_contract(contract_id)
            return True
        except Exception as e:
            print(f"[API] Ошибка удаления заказа: {e}")
            return False

    def get_crm_statistics(self, project_type: str, period: str, year: int, month: int = None) -> List[Dict[str, Any]]:
        """Получить статистику CRM"""
        params = {
            'project_type': project_type,
            'period': period,
            'year': year
        }
        if month:
            params['month'] = month
        response = self._request(
            'GET',
            f"{self.base_url}/api/statistics/crm",
            params=params
        )
        return self._handle_response(response)

    def get_crm_statistics_filtered(self, project_type: str, period: str, year: int,
                                    quarter: int = None, month: int = None, project_id: int = None,
                                    executor_id: int = None, stage_name: str = None,
                                    status_filter: str = None) -> List[Dict[str, Any]]:
        """Получить статистику CRM с фильтрами"""
        params = {
            'project_type': project_type,
            'period': period,
            'year': year
        }
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        if project_id:
            params['project_id'] = project_id
        if executor_id:
            params['executor_id'] = executor_id
        if stage_name:
            params['stage_name'] = stage_name
        if status_filter:
            params['status_filter'] = status_filter

        response = self._request(
            'GET',
            f"{self.base_url}/api/statistics/crm/filtered",
            params=params
        )
        return self._handle_response(response)

    def get_projects_by_type(self, project_type: str) -> List[Dict[str, Any]]:
        """Получить список проектов по типу"""
        try:
            cards = self.get_crm_cards(project_type)
            projects = []
            seen_contracts = set()
            for card in cards:
                contract_id = card.get('contract_id')
                if contract_id and contract_id not in seen_contracts:
                    seen_contracts.add(contract_id)
                    projects.append({
                        'contract_id': contract_id,
                        'contract_number': card.get('contract_number'),
                        'address': card.get('address'),
                        'city': card.get('city')
                    })
            return projects
        except Exception as e:
            print(f"[API] Ошибка получения проектов: {e}")
            return []

    def complete_stage_for_executor(self, crm_card_id: int, stage_name: str, executor_id: int) -> bool:
        """Отметить стадию как выполненную для исполнителя"""
        try:
            response = self._request(
                'PATCH',
                f"{self.base_url}/api/crm/cards/{crm_card_id}/stage-executor/{stage_name}/complete",
                json={'executor_id': executor_id}
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка завершения стадии: {e}")
            return False

    def get_previous_executor_by_position(self, crm_card_id: int, position: str) -> Optional[int]:
        """Получить предыдущего исполнителя по должности"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/crm/cards/{crm_card_id}/previous-executor",
                params={'position': position}
            )
            result = self._handle_response(response)
            return result.get('executor_id')
        except Exception as e:
            print(f"[API] Ошибка получения предыдущего исполнителя: {e}")
            return None

    def update_stage_executor_deadline(self, crm_card_id: int, stage_keyword: str, deadline: str) -> bool:
        """Обновить дедлайн исполнителя стадии"""
        try:
            response = self._request(
                'PATCH',
                f"{self.base_url}/api/crm/cards/{crm_card_id}/stage-executor-deadline",
                json={'stage_keyword': stage_keyword, 'deadline': deadline}
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка обновления дедлайна: {e}")
            return False

    def get_approval_stage_deadlines(self, crm_card_id: int) -> List[Dict[str, Any]]:
        """Получить дедлайны стадий согласования"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/crm/cards/{crm_card_id}/approval-deadlines"
        )
        return self._handle_response(response)

    def complete_approval_stage(self, crm_card_id: int, stage_name: str) -> bool:
        """Завершить стадию согласования"""
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/crm/cards/{crm_card_id}/complete-approval-stage",
                json={'stage_name': stage_name}
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка завершения стадии согласования: {e}")
            return False

    def get_approval_statistics(self, project_type: str, period: str, year: int,
                                quarter: int = None, month: int = None,
                                project_id: int = None) -> List[Dict[str, Any]]:
        """Получить статистику согласований"""
        params = {
            'project_type': project_type,
            'period': period,
            'year': year
        }
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month
        if project_id:
            params['project_id'] = project_id

        response = self._request(
            'GET',
            f"{self.base_url}/api/statistics/approvals",
            params=params
        )
        return self._handle_response(response)

    def save_manager_acceptance(self, crm_card_id: int, stage_name: str,
                                executor_name: str, manager_id: int) -> bool:
        """Сохранить принятие работы менеджером"""
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/crm/cards/{crm_card_id}/manager-acceptance",
                json={
                    'stage_name': stage_name,
                    'executor_name': executor_name,
                    'manager_id': manager_id
                }
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка сохранения принятия: {e}")
            return False

    def get_accepted_stages(self, crm_card_id: int) -> List[Dict[str, Any]]:
        """Получить список принятых стадий"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/crm/cards/{crm_card_id}/accepted-stages"
        )
        return self._handle_response(response)

    def get_crm_card_data(self, card_id: int) -> Dict[str, Any]:
        """Получить данные карточки для проверок (alias для get_crm_card)"""
        return self.get_crm_card(card_id)

    def calculate_payment_amount(self, contract_id: int, employee_id: int, role: str,
                                  stage_name: str = None, supervision_card_id: int = None) -> float:
        """Рассчитать сумму оплаты на основе тарифов"""
        try:
            params = {
                'contract_id': contract_id,
                'employee_id': employee_id,
                'role': role
            }
            if stage_name:
                params['stage_name'] = stage_name
            if supervision_card_id:
                params['supervision_card_id'] = supervision_card_id

            response = self._request(
                'GET',
                f"{self.base_url}/api/payments/calculate",
                params=params
            )
            result = self._handle_response(response)
            return result.get('amount', 0)
        except Exception as e:
            print(f"[API] Ошибка расчета оплаты: {e}")
            return 0

    def create_payment_record(self, contract_id: int, employee_id: int, role: str,
                              stage_name: str = None, payment_type: str = 'Полная оплата',
                              report_month: str = None, crm_card_id: int = None,
                              supervision_card_id: int = None) -> Optional[int]:
        """Создать запись о выплате"""
        try:
            payment_data = {
                'contract_id': contract_id,
                'employee_id': employee_id,
                'role': role,
                'payment_type': payment_type
            }
            if stage_name:
                payment_data['stage_name'] = stage_name
            if report_month:
                payment_data['report_month'] = report_month
            if crm_card_id:
                payment_data['crm_card_id'] = crm_card_id
            if supervision_card_id:
                payment_data['supervision_card_id'] = supervision_card_id

            result = self.create_payment(payment_data)
            return result.get('id')
        except Exception as e:
            print(f"[API] Ошибка создания выплаты: {e}")
            return None

    def get_payments_for_crm(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получить выплаты для CRM (не надзор)"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments/crm/{contract_id}"
        )
        return self._handle_response(response)

    def get_all_payments_optimized(self, year: int = None, month: int = None, quarter: int = None) -> List[Dict[str, Any]]:
        """Оптимизированная загрузка всех выплат - один запрос вместо множества"""
        try:
            params = {}
            if year:
                params['year'] = year
            if month:
                params['month'] = month
            if quarter:
                params['quarter'] = quarter

            response = self._request(
                'GET',
                f"{self.base_url}/api/payments/all-optimized",
                params=params
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка загрузки оптимизированных выплат: {e}")
            return []

    def recalculate_payments(self, contract_id: int = None, role: str = None) -> Dict[str, Any]:
        """Пересчет выплат по текущим тарифам"""
        try:
            params = {}
            if contract_id:
                params['contract_id'] = contract_id
            if role:
                params['role'] = role

            response = self._request(
                'POST',
                f"{self.base_url}/api/payments/recalculate",
                params=params
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка пересчета выплат: {e}")
            return {'status': 'error', 'error': str(e)}

    def add_agent(self, name: str, color: str) -> bool:
        """Добавить нового агента"""
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/agents",
                json={'name': name, 'color': color}
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка добавления агента: {e}")
            return False

    def update_agent_color(self, name: str, color: str) -> bool:
        """Обновить цвет агента"""
        try:
            response = self._request(
                'PATCH',
                f"{self.base_url}/api/agents/{name}/color",
                json={'color': color}
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка обновления цвета агента: {e}")
            return False

    def get_agent_color(self, name: str) -> Optional[str]:
        """Получить цвет агента по имени"""
        try:
            agents = self.get_all_agents()
            for agent in agents:
                if agent.get('name') == name:
                    return agent.get('color')
            return None
        except Exception as e:
            print(f"[API] Ошибка получения цвета агента: {e}")
            return None

    def add_project_file(self, contract_id: int, stage: str, file_type: str,
                         public_link: str, yandex_path: str, file_name: str,
                         preview_cache_path: str = None, variation: int = 1) -> Optional[int]:
        """Добавить файл стадии проекта"""
        try:
            file_data = {
                'contract_id': contract_id,
                'stage': stage,
                'file_type': file_type,
                'public_link': public_link,
                'yandex_path': yandex_path,
                'file_name': file_name,
                'variation': variation
            }
            if preview_cache_path:
                file_data['preview_cache_path'] = preview_cache_path

            result = self.create_file_record(file_data)
            return result.get('id')
        except Exception as e:
            print(f"[API] Ошибка добавления файла: {e}")
            return None

    def get_project_files(self, contract_id: int, stage: str = None) -> List[Dict[str, Any]]:
        """Получить файлы стадии проекта (alias для get_contract_files)"""
        return self.get_contract_files(contract_id, stage)

    def get_all_project_files(self) -> List[Dict[str, Any]]:
        """Получить все файлы проектов для синхронизации"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/files/all"
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка получения всех файлов: {e}")
            return []

    def delete_project_file(self, file_id: int) -> Optional[Dict[str, Any]]:
        """Удалить файл стадии проекта"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/files/{file_id}",
                mark_offline=False  # Не переходим в offline при ошибке
            )
            file_info = self._handle_response(response)
            self.delete_file_record(file_id)
            return file_info
        except Exception as e:
            print(f"[API] Ошибка удаления файла: {e}")
            return None

    def update_project_file_order(self, file_id: int, new_order: int) -> bool:
        """Обновить порядок файла в галерее"""
        try:
            response = self._request(
                'PATCH',
                f"{self.base_url}/api/files/{file_id}/order",
                json={'file_order': new_order}
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка обновления порядка файла: {e}")
            return False

    def add_project_template(self, contract_id: int, template_url: str) -> Optional[int]:
        """Добавить ссылку на шаблон проекта"""
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/project-templates",
                json={'contract_id': contract_id, 'template_url': template_url}
            )
            result = self._handle_response(response)
            return result.get('id')
        except Exception as e:
            print(f"[API] Ошибка добавления шаблона: {e}")
            return None

    def get_project_templates(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получить все шаблоны для договора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/project-templates/{contract_id}"
        )
        return self._handle_response(response)

    def delete_project_template(self, template_id: int) -> bool:
        """Удалить шаблон проекта"""
        try:
            response = self._request(
                'DELETE',
                f"{self.base_url}/api/project-templates/{template_id}"
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка удаления шаблона: {e}")
            return False

    def reset_designer_completion(self, crm_card_id: int) -> bool:
        """Сбросить отметку о завершении дизайнером"""
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/crm/cards/{crm_card_id}/reset-designer"
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка сброса отметки дизайнера: {e}")
            return False

    def reset_draftsman_completion(self, crm_card_id: int) -> bool:
        """Сбросить отметку о завершении чертежником"""
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/crm/cards/{crm_card_id}/reset-draftsman"
            )
            self._handle_response(response)
            return True
        except Exception as e:
            print(f"[API] Ошибка сброса отметки чертежника: {e}")
            return False

    def add_action_history(self, user_id: int, action_type: str, entity_type: str,
                           entity_id: int, description: str) -> bool:
        """Добавить запись в историю действий"""
        try:
            history_data = {
                'user_id': user_id,
                'action_type': action_type,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'description': description
            }
            self.create_action_history(history_data)
            return True
        except Exception as e:
            print(f"[API] Ошибка добавления записи в историю: {e}")
            return False

    def get_general_statistics(self, year: int, quarter: int = None, month: int = None) -> Dict[str, Any]:
        """Получить общую статистику"""
        params = {'year': year}
        if quarter:
            params['quarter'] = quarter
        if month:
            params['month'] = month

        response = self._request(
            'GET',
            f"{self.base_url}/api/statistics/general",
            params=params
        )
        return self._handle_response(response)

    def assign_stage_executor_db(self, card_id: int, stage_name: str, executor_id: int,
                                  assigned_by: int, deadline: str = None) -> bool:
        """Назначить исполнителя на стадию (совместимость с db_manager)"""
        try:
            stage_data = {
                'stage_name': stage_name,
                'executor_id': executor_id,
                'assigned_by': assigned_by
            }
            if deadline:
                stage_data['deadline'] = deadline
            self.assign_stage_executor(card_id, stage_data)
            return True
        except Exception as e:
            print(f"[API] Ошибка назначения исполнителя: {e}")
            return False

    def get_contract_id_by_crm_card(self, crm_card_id: int) -> Optional[int]:
        """Получить ID договора по ID карточки CRM"""
        try:
            card = self.get_crm_card(crm_card_id)
            return card.get('contract_id')
        except Exception as e:
            print(f"[API] Ошибка получения contract_id: {e}")
            return None

    def update_crm_card_column(self, card_id: int, column_name: str) -> bool:
        """Обновить колонку карточки (alias для move_crm_card)"""
        try:
            self.move_crm_card(card_id, column_name)
            return True
        except Exception as e:
            print(f"[API] Ошибка обновления колонки: {e}")
            return False

    def update_supervision_card_column(self, card_id: int, column_name: str) -> bool:
        """Обновить колонку карточки надзора (alias для move_supervision_card)"""
        try:
            self.move_supervision_card(card_id, column_name)
            return True
        except Exception as e:
            print(f"[API] Ошибка обновления колонки надзора: {e}")
            return False

    def get_supervision_cards_active(self) -> List[Dict[str, Any]]:
        """Получить активные карточки надзора (alias)"""
        return self.get_supervision_cards(status="active")

    def get_supervision_cards_archived(self) -> List[Dict[str, Any]]:
        """Получить архивные карточки надзора (alias)"""
        return self.get_supervision_cards(status="archived")

    def get_supervision_statistics_report(self, year: int, quarter: int = None,
                                          month: int = None, agent_type: str = None,
                                          city: str = None) -> Dict[str, Any]:
        """Получить статистику надзора для отчета (alias)"""
        return self.get_supervision_statistics(year, quarter, month, agent_type, city)

    # =========================
    # ДОПОЛНИТЕЛЬНЫЕ АЛИАСЫ ДЛЯ СОВМЕСТИМОСТИ С db_manager
    # =========================

    def get_employee_by_id(self, employee_id: int) -> Dict[str, Any]:
        """Получить сотрудника по ID (alias для get_employee)"""
        return self.get_employee(employee_id)

    def get_client_by_id(self, client_id: int) -> Dict[str, Any]:
        """Получить клиента по ID (alias для get_client)"""
        return self.get_client(client_id)

    def get_employee_by_login(self, login: str, password: str) -> Optional[Dict[str, Any]]:
        """Проверить логин/пароль сотрудника через API login"""
        try:
            result = self.login(login, password)
            if result and result.get('access_token'):
                return self.get_current_user()
            return None
        except Exception:
            return None

    def add_crm_card(self, card_data: Dict[str, Any]) -> Optional[int]:
        """Добавить CRM карточку (alias для create_crm_card)"""
        result = self.create_crm_card(card_data)
        return result.get('id') if result else None

    def add_supervision_card(self, card_data: Dict[str, Any]) -> Optional[int]:
        """Добавить карточку надзора (alias для create_supervision_card)"""
        result = self.create_supervision_card(card_data)
        return result.get('id') if result else None

    def add_rate(self, rate_data: Dict[str, Any]) -> Optional[int]:
        """Добавить ставку (alias для create_rate)"""
        result = self.create_rate(rate_data)
        return result.get('id') if result else None

    def get_rate_by_id(self, rate_id: int) -> Dict[str, Any]:
        """Получить ставку по ID (alias для get_rate)"""
        return self.get_rate(rate_id)

    def get_salary_by_id(self, salary_id: int) -> Dict[str, Any]:
        """Получить запись о зарплате по ID (alias для get_salary)"""
        return self.get_salary(salary_id)

    def add_payment(self, payment_data: Dict[str, Any]) -> Optional[int]:
        """Добавить платёж (alias для create_payment)"""
        result = self.create_payment(payment_data)
        return result.get('id') if result else None

    def add_contract_file(self, file_data: Dict[str, Any]) -> Optional[int]:
        """Добавить файл договора (alias для create_file_record)"""
        result = self.create_file_record(file_data)
        return result.get('id') if result else None

    def delete_contract_file(self, file_id: int) -> bool:
        """Удалить файл договора (alias для delete_file_record)"""
        return self.delete_file_record(file_id)

    def get_supervision_card_data(self, card_id: int) -> Dict[str, Any]:
        """Получить данные карточки надзора (alias для get_supervision_card)"""
        return self.get_supervision_card(card_id)

    def sync_approval_stages_to_json(self, crm_card_id: int) -> bool:
        """Синхронизация стадий согласования (на сервере выполняется автоматически)"""
        # На сервере эта операция выполняется автоматически при обновлении
        return True

    # =========================
    # ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ (добавлены для совместимости с UI)
    # =========================

    def get_contracts_by_project_type(self, project_type: str) -> List[Dict[str, Any]]:
        """Получить договоры по типу проекта"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/contracts",
            params={'project_type': project_type}
        )
        return self._handle_response(response)

    def get_unique_cities(self) -> List[str]:
        """Получить уникальные города из договоров"""
        try:
            contracts = self.get_contracts()
            cities = set()
            for c in contracts:
                if c.get('city'):
                    cities.add(c['city'])
            return sorted(list(cities))
        except Exception:
            return []

    def get_unique_agent_types(self) -> List[str]:
        """Получить уникальные типы агентов из договоров"""
        try:
            contracts = self.get_contracts()
            agent_types = set()
            for c in contracts:
                if c.get('agent_type'):
                    agent_types.add(c['agent_type'])
            return sorted(list(agent_types))
        except Exception:
            return []

    def get_crm_card_by_contract_id(self, contract_id: int) -> Optional[Dict[str, Any]]:
        """Получить CRM карточку по ID договора"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/crm/cards/by-contract/{contract_id}"
            )
            return self._handle_response(response)
        except Exception:
            return None

    def get_payments(self) -> List[Dict[str, Any]]:
        """Получить все платежи"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments"
        )
        return self._handle_response(response)

    def get_payments_by_contract(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получить платежи по ID договора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments",
            params={'contract_id': contract_id}
        )
        return self._handle_response(response)

    def get_payments_by_employee(self, employee_id: int) -> List[Dict[str, Any]]:
        """Получить платежи по ID сотрудника"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments",
            params={'employee_id': employee_id}
        )
        return self._handle_response(response)

    def get_unpaid_payments(self) -> List[Dict[str, Any]]:
        """Получить неоплаченные платежи"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments",
            params={'is_paid': False}
        )
        return self._handle_response(response)

    def get_rates_by_project_type(self, project_type: str) -> List[Dict[str, Any]]:
        """Получить ставки по типу проекта"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/rates",
            params={'project_type': project_type}
        )
        return self._handle_response(response)

    def get_salaries_by_employee(self, employee_id: int) -> List[Dict[str, Any]]:
        """Получить зарплаты по ID сотрудника"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/salaries",
            params={'employee_id': employee_id}
        )
        return self._handle_response(response)

    def get_files_by_contract(self, contract_id: int) -> List[Dict[str, Any]]:
        """Получить файлы по ID договора"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/files/contract/{contract_id}"
        )
        return self._handle_response(response)

    def get_file_templates(self) -> List[Dict[str, Any]]:
        """Получить шаблоны файлов"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/file-templates"
            )
            return self._handle_response(response)
        except Exception:
            return []

    def get_agents(self) -> List[Dict[str, Any]]:
        """Получить список агентов"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/agents"
        )
        return self._handle_response(response)

    def get_agent(self, agent_id: int) -> Dict[str, Any]:
        """Получить агента по ID"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/agents/{agent_id}"
        )
        return self._handle_response(response)

    # ========== DASHBOARD METHODS ==========

    def get_clients_dashboard_stats(self, year: Optional[int] = None, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда страницы Клиенты"""
        params = {}
        if year:
            params['year'] = year
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/dashboard/clients",
            params=params
        )
        return self._handle_response(response)

    def get_contracts_dashboard_stats(self, year: Optional[int] = None, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда страницы Договора"""
        params = {}
        if year:
            params['year'] = year
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/dashboard/contracts",
            params=params
        )
        return self._handle_response(response)

    def get_crm_dashboard_stats(self, project_type: str, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда СРМ (Индивидуальные/Шаблонные/Надзор)"""
        params = {'project_type': project_type}
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/dashboard/crm",
            params=params
        )
        return self._handle_response(response)

    def get_employees_dashboard_stats(self) -> Dict[str, Any]:
        """Получить статистику для дашборда страницы Сотрудники"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/dashboard/employees"
        )
        return self._handle_response(response)

    def get_salaries_dashboard_stats(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда страницы Зарплаты"""
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month

        response = self._request(
            'GET',
            f"{self.base_url}/api/dashboard/salaries",
            params=params
        )
        return self._handle_response(response)

    def get_salaries_payment_type_stats(self, payment_type: str, year: Optional[int] = None,
                                         month: Optional[int] = None, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда вкладок зарплат по типу выплат

        Args:
            payment_type: Тип вкладки ('all', 'individual', 'template', 'salary', 'supervision')
            year: Год для фильтра
            month: Месяц для фильтра
            agent_type: Тип агента для фильтра

        Returns:
            Dict с ключами: total_paid, paid_by_year, paid_by_month, payments_count, to_pay_amount, by_agent
        """
        params = {'payment_type': payment_type}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/dashboard/salaries-by-type",
            params=params
        )
        return self._handle_response(response)

    def get_salaries_all_payments_stats(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда 'Все выплаты'
        Возвращает: total_paid, paid_by_year, paid_by_month, individual_by_year, template_by_year, supervision_by_year
        """
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month

        response = self._request(
            'GET',
            f"{self.base_url}/api/dashboard/salaries-all",
            params=params
        )
        return self._handle_response(response)

    def get_salaries_individual_stats(self, year: Optional[int] = None, month: Optional[int] = None,
                                       agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда 'Индивидуальные'
        Возвращает: total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count
        """
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/dashboard/salaries-individual",
            params=params
        )
        return self._handle_response(response)

    def get_salaries_template_stats(self, year: Optional[int] = None, month: Optional[int] = None,
                                     agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда 'Шаблонные'
        Возвращает: total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count
        """
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/dashboard/salaries-template",
            params=params
        )
        return self._handle_response(response)

    def get_salaries_salary_stats(self, year: Optional[int] = None, month: Optional[int] = None,
                                   project_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда 'Оклады'
        Возвращает: total_paid, paid_by_year, paid_by_month, by_project_type, avg_salary, employees_count
        """
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if project_type:
            params['project_type'] = project_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/dashboard/salaries-salary",
            params=params
        )
        return self._handle_response(response)

    def get_salaries_supervision_stats(self, year: Optional[int] = None, month: Optional[int] = None,
                                        agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Получить статистику для дашборда 'Авторский надзор'
        Возвращает: total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count
        """
        params = {}
        if year:
            params['year'] = year
        if month:
            params['month'] = month
        if agent_type:
            params['agent_type'] = agent_type

        response = self._request(
            'GET',
            f"{self.base_url}/api/dashboard/salaries-supervision",
            params=params
        )
        return self._handle_response(response)

    def get_agent_types(self) -> List[str]:
        """Получить список всех типов агентов"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/dashboard/agent-types"
        )
        return self._handle_response(response)

    def get_contract_years(self) -> List[int]:
        """Получить список всех годов из договоров (для фильтров дашборда)

        Returns:
            list: Список годов в обратном порядке (от нового к старому)
        """
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/dashboard/contract-years"
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка получения годов договоров: {e}")
            # Возвращаем fallback - 10 лет назад до следующего года
            from datetime import datetime
            current_year = datetime.now().year
            return list(range(current_year + 1, current_year - 10, -1))

    # =========================
    # SYNC DATA METHODS
    # =========================

    def get_all_stage_executors(self) -> List[Dict[str, Any]]:
        """Получить всех исполнителей стадий для синхронизации"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/sync/stage-executors"
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка получения исполнителей стадий: {e}")
            return []

    def get_all_approval_deadlines(self) -> List[Dict[str, Any]]:
        """Получить все дедлайны согласования для синхронизации"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/sync/approval-deadlines"
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка получения дедлайнов согласования: {e}")
            return []

    def get_all_action_history(self) -> List[Dict[str, Any]]:
        """Получить всю историю действий для синхронизации"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/sync/action-history"
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка получения истории действий: {e}")
            return []

    def get_all_supervision_history(self) -> List[Dict[str, Any]]:
        """Получить всю историю проектов надзора для синхронизации"""
        try:
            response = self._request(
                'GET',
                f"{self.base_url}/api/sync/supervision-history"
            )
            return self._handle_response(response)
        except Exception as e:
            print(f"[API] Ошибка получения истории надзора: {e}")
            return []


