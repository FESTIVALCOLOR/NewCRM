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
    DEFAULT_TIMEOUT = 10  # секунд
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # секунд между попытками

    def __init__(self, base_url: str, verify_ssl: bool = False):
        """
        Args:
            base_url: Базовый URL API (например: https://your-app.railway.app)
            verify_ssl: Проверять SSL сертификат (False для самоподписанных)
        """
        self.base_url = base_url.rstrip('/')
        self.token: Optional[str] = None
        self.employee_id: Optional[int] = None
        self.verify_ssl = verify_ssl  # Для самоподписанных сертификатов = False
        self.headers = {
            "Content-Type": "application/json"
        }
        self._is_online = True  # Флаг статуса соединения
        self.session = requests.Session()  # Переиспользуемая сессия

    def _request(
        self,
        method: str,
        url: str,
        timeout: int = None,
        retry: bool = True,
        **kwargs
    ) -> requests.Response:
        """
        Унифицированный метод запроса с timeout и retry логикой

        Args:
            method: HTTP метод (GET, POST, PUT, PATCH, DELETE)
            url: Полный URL запроса
            timeout: Таймаут в секундах (по умолчанию DEFAULT_TIMEOUT)
            retry: Включить retry логику
            **kwargs: Дополнительные параметры для requests

        Returns:
            requests.Response объект

        Raises:
            APITimeoutError: При таймауте
            APIConnectionError: При ошибке соединения
            APIError: При других ошибках
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        kwargs.setdefault('verify', self.verify_ssl)
        kwargs.setdefault('headers', self.headers)
        kwargs['timeout'] = timeout

        last_error = None
        max_attempts = self.MAX_RETRIES if retry else 1

        for attempt in range(max_attempts):
            try:
                response = self.session.request(method, url, **kwargs)
                self._is_online = True
                return response

            except requests.exceptions.Timeout as e:
                last_error = APITimeoutError(
                    f"Таймаут запроса после {timeout} сек: {url}"
                )
                print(f"[API] Таймаут (попытка {attempt + 1}/{max_attempts}): {url}")

            except requests.exceptions.ConnectionError as e:
                self._is_online = False
                last_error = APIConnectionError(
                    f"Не удалось подключиться к серверу: {self.base_url}"
                )
                print(f"[API] Ошибка соединения (попытка {attempt + 1}/{max_attempts}): {e}")

            except requests.exceptions.RequestException as e:
                last_error = APIError(f"Ошибка запроса: {e}")
                print(f"[API] Ошибка (попытка {attempt + 1}/{max_attempts}): {e}")

            # Задержка перед повторной попыткой
            if attempt < max_attempts - 1:
                delay = self.RETRY_DELAY * (attempt + 1)  # Exponential backoff
                print(f"[API] Повтор через {delay} сек...")
                time.sleep(delay)

        # Все попытки исчерпаны
        self._is_online = False
        raise last_error

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

    def set_token(self, token: str):
        """Установить JWT токен для аутентификации"""
        self.token = token
        self.headers["Authorization"] = f"Bearer {token}"

    def clear_token(self):
        """Очистить токен"""
        self.token = None
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
        self.set_token(data["access_token"])
        self.employee_id = data["employee_id"]
        return data

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

    def sync(self, last_sync_timestamp: datetime, entity_types: List[str]) -> Dict[str, Any]:
        """
        Получить обновления с сервера

        Args:
            last_sync_timestamp: Время последней синхронизации
            entity_types: Типы сущностей ['clients', 'contracts', 'employees']

        Returns:
            dict с обновленными данными
        """
        response = self._request(
            'POST',
            f"{self.base_url}/api/sync",
            json={
                "last_sync_timestamp": last_sync_timestamp.isoformat(),
                "entity_types": entity_types
            }
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
            json=file_data
        )
        return self._handle_response(response)

    def delete_file_record(self, file_id: int) -> bool:
        """Удалить запись о файле"""
        response = self._request('DELETE', f"{self.base_url}/api/files/{file_id}")
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

    def add_supervision_history(self, card_id: int, history_data: Dict[str, Any]) -> Dict[str, Any]:
        """Добавить запись в историю надзора"""
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

    def get_all_payments(self) -> List[Dict[str, Any]]:
        """Получить все платежи"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments"
        )
        return self._handle_response(response)

    def get_year_payments(self, year: int) -> List[Dict[str, Any]]:
        """Получить платежи за год"""
        response = self._request(
            'GET',
            f"{self.base_url}/api/payments",
            params={'year': year}
        )
        return self._handle_response(response)

    def get_payments_by_type(self, payment_type: str, year: int = None, month: int = None) -> List[Dict[str, Any]]:
        """
        Получить платежи по типу

        Args:
            payment_type: Тип платежа ('first', 'second', 'third', 'supervision')
            year: Год
            month: Месяц

        Returns:
            Список платежей
        """
        params = {'payment_type': payment_type}
        if year:
            params['year'] = year
        if month:
            params['month'] = month

        response = self._request(
            'GET',
            f"{self.base_url}/api/payments",
            params=params
        )
        return self._handle_response(response)

    # =========================
    # EMPLOYEE REPORTS
    # =========================

    def get_employee_report_data(self, employee_id: int, year: int = None, month: int = None) -> Dict[str, Any]:
        """
        Получить данные для отчета сотрудника

        Args:
            employee_id: ID сотрудника
            year: Год
            month: Месяц

        Returns:
            Данные отчета
        """
        params = {'employee_id': employee_id}
        if year:
            params['year'] = year
        if month:
            params['month'] = month

        response = self._request(
            'GET',
            f"{self.base_url}/api/reports/employee",
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
