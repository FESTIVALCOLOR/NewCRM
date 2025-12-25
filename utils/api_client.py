"""
API клиент для взаимодействия с сервером
Используется в PyQt5 клиенте
"""
import requests
import urllib3
from typing import Optional, List, Dict, Any
from datetime import datetime

# Отключаем предупреждения о самоподписанных сертификатах (только для разработки!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class APIClient:
    """
    Клиент для работы с REST API сервера
    """

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
            Exception: При ошибке аутентификации
        """
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            data={
                "username": username,
                "password": password
            },
            verify=self.verify_ssl
        )

        if response.status_code != 200:
            raise Exception(f"Не удалось войти: {response.json().get('detail', 'Неизвестная ошибка')}")

        data = response.json()
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
            response = requests.post(
                f"{self.base_url}/api/auth/logout",
                headers=self.headers
            , verify=self.verify_ssl)
            self.clear_token()
            return response.status_code == 200
        except Exception as e:
            print(f"Ошибка выхода: {e}")
            self.clear_token()
            return False

    def get_current_user(self) -> Dict[str, Any]:
        """
        Получить информацию о текущем пользователе

        Returns:
            dict с данными пользователя
        """
        response = requests.get(
            f"{self.base_url}/api/auth/me",
            headers=self.headers
        , verify=self.verify_ssl)

        if response.status_code != 200:
            raise Exception("Не удалось получить данные пользователя")

        return response.json()

    # =========================
    # КЛИЕНТЫ
    # =========================

    def get_clients(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить список клиентов"""
        response = requests.get(
            f"{self.base_url}/api/clients",
            headers=self.headers,
            params={"skip": skip, "limit": limit}
        , verify=self.verify_ssl)

        if response.status_code != 200:
            raise Exception("Ошибка получения клиентов")

        return response.json()

    def get_client(self, client_id: int) -> Dict[str, Any]:
        """Получить клиента по ID"""
        response = requests.get(
            f"{self.base_url}/api/clients/{client_id}",
            headers=self.headers
        , verify=self.verify_ssl)

        if response.status_code != 200:
            raise Exception(f"Клиент {client_id} не найден")

        return response.json()

    def create_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать нового клиента"""
        response = requests.post(
            f"{self.base_url}/api/clients",
            headers=self.headers,
            json=client_data
        , verify=self.verify_ssl)

        if response.status_code != 200:
            raise Exception(f"Ошибка создания клиента: {response.json().get('detail')}")

        return response.json()

    def update_client(self, client_id: int, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить клиента"""
        response = requests.put(
            f"{self.base_url}/api/clients/{client_id}",
            headers=self.headers,
            json=client_data
        , verify=self.verify_ssl)

        if response.status_code != 200:
            raise Exception(f"Ошибка обновления клиента: {response.json().get('detail')}")

        return response.json()

    # =========================
    # ДОГОВОРЫ
    # =========================

    def get_contracts(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить список договоров"""
        response = requests.get(
            f"{self.base_url}/api/contracts",
            headers=self.headers,
            params={"skip": skip, "limit": limit}
        , verify=self.verify_ssl)

        if response.status_code != 200:
            raise Exception("Ошибка получения договоров")

        return response.json()

    def get_contract(self, contract_id: int) -> Dict[str, Any]:
        """Получить договор по ID"""
        response = requests.get(
            f"{self.base_url}/api/contracts/{contract_id}",
            headers=self.headers
        , verify=self.verify_ssl)

        if response.status_code != 200:
            raise Exception(f"Договор {contract_id} не найден")

        return response.json()

    def create_contract(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать новый договор"""
        response = requests.post(
            f"{self.base_url}/api/contracts",
            headers=self.headers,
            json=contract_data
        , verify=self.verify_ssl)

        if response.status_code != 200:
            raise Exception(f"Ошибка создания договора: {response.json().get('detail')}")

        return response.json()

    def update_contract(self, contract_id: int, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить договор"""
        response = requests.put(
            f"{self.base_url}/api/contracts/{contract_id}",
            headers=self.headers,
            json=contract_data
        , verify=self.verify_ssl)

        if response.status_code != 200:
            raise Exception(f"Ошибка обновления договора: {response.json().get('detail')}")

        return response.json()

    # =========================
    # СОТРУДНИКИ
    # =========================

    def get_employees(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить список сотрудников"""
        response = requests.get(
            f"{self.base_url}/api/employees",
            headers=self.headers,
            params={"skip": skip, "limit": limit}
        , verify=self.verify_ssl)

        if response.status_code != 200:
            raise Exception("Ошибка получения сотрудников")

        return response.json()

    def get_employee(self, employee_id: int) -> Dict[str, Any]:
        """Получить сотрудника по ID"""
        response = requests.get(
            f"{self.base_url}/api/employees/{employee_id}",
            headers=self.headers
        , verify=self.verify_ssl)

        if response.status_code != 200:
            raise Exception(f"Сотрудник {employee_id} не найден")

        return response.json()

    def create_employee(self, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать нового сотрудника"""
        response = requests.post(
            f"{self.base_url}/api/employees",
            headers=self.headers,
            json=employee_data
        , verify=self.verify_ssl)

        if response.status_code != 200:
            error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
            raise Exception(f"Ошибка создания сотрудника (HTTP {response.status_code}): {error_detail}")

        return response.json()

    def update_employee(self, employee_id: int, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить сотрудника"""
        response = requests.put(
            f"{self.base_url}/api/employees/{employee_id}",
            headers=self.headers,
            json=employee_data,
            verify=self.verify_ssl
        )

        if response.status_code != 200:
            error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
            raise Exception(f"Ошибка обновления сотрудника (HTTP {response.status_code}): {error_detail}")

        return response.json()

    def delete_employee(self, employee_id: int) -> bool:
        """Удалить сотрудника"""
        response = requests.delete(
            f"{self.base_url}/api/employees/{employee_id}",
            headers=self.headers,
            verify=self.verify_ssl
        )

        if response.status_code != 200:
            error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
            raise Exception(f"Ошибка удаления сотрудника (HTTP {response.status_code}): {error_detail}")

        return True

    def delete_client(self, client_id: int) -> bool:
        """Удалить клиента"""
        response = requests.delete(
            f"{self.base_url}/api/clients/{client_id}",
            headers=self.headers,
            verify=self.verify_ssl
        )

        if response.status_code != 200:
            error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
            raise Exception(f"Ошибка удаления клиента (HTTP {response.status_code}): {error_detail}")

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
        response = requests.get(
            f"{self.base_url}/api/crm/cards",
            headers=self.headers,
            params={"project_type": project_type},
            verify=self.verify_ssl
        )

        if response.status_code != 200:
            error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
            raise Exception(f"Ошибка получения CRM карточек (HTTP {response.status_code}): {error_detail}")

        return response.json()

    def get_crm_card(self, card_id: int) -> Dict:
        """
        Получить одну CRM карточку

        Args:
            card_id: ID карточки

        Returns:
            Данные карточки с исполнителями стадий
        """
        response = requests.get(
            f"{self.base_url}/api/crm/cards/{card_id}",
            headers=self.headers,
            verify=self.verify_ssl
        )

        if response.status_code != 200:
            error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
            raise Exception(f"Ошибка получения CRM карточки (HTTP {response.status_code}): {error_detail}")

        return response.json()

    def update_crm_card(self, card_id: int, updates: Dict[str, Any]) -> Dict:
        """
        Обновить CRM карточку (частичное обновление)

        Args:
            card_id: ID карточки
            updates: Словарь с обновляемыми полями

        Returns:
            Обновлённые данные карточки
        """
        response = requests.patch(
            f"{self.base_url}/api/crm/cards/{card_id}",
            headers=self.headers,
            json=updates,
            verify=self.verify_ssl
        )

        if response.status_code != 200:
            error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
            raise Exception(f"Ошибка обновления CRM карточки (HTTP {response.status_code}): {error_detail}")

        return response.json()

    def move_crm_card(self, card_id: int, column_name: str) -> Dict:
        """
        Переместить CRM карточку в другую колонку

        Args:
            card_id: ID карточки
            column_name: Название колонки ("Новый заказ", "В работе" и т.д.)

        Returns:
            Обновлённые данные карточки
        """
        response = requests.patch(
            f"{self.base_url}/api/crm/cards/{card_id}/column",
            headers=self.headers,
            json={"column_name": column_name},
            verify=self.verify_ssl
        )

        if response.status_code != 200:
            error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
            raise Exception(f"Ошибка перемещения CRM карточки (HTTP {response.status_code}): {error_detail}")

        return response.json()

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
        response = requests.post(
            f"{self.base_url}/api/crm/cards/{card_id}/stage-executor",
            headers=self.headers,
            json=stage_data,
            verify=self.verify_ssl
        )

        if response.status_code != 200:
            error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
            raise Exception(f"Ошибка назначения исполнителя (HTTP {response.status_code}): {error_detail}")

        return response.json()

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
        response = requests.patch(
            f"{self.base_url}/api/crm/cards/{card_id}/stage-executor/{stage_name}",
            headers=self.headers,
            json={"completed": completed},
            verify=self.verify_ssl
        )

        if response.status_code != 200:
            error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
            raise Exception(f"Ошибка обновления стадии (HTTP {response.status_code}): {error_detail}")

        return response.json()

    def delete_contract(self, contract_id: int) -> bool:
        """Удалить договор"""
        response = requests.delete(
            f"{self.base_url}/api/contracts/{contract_id}",
            headers=self.headers,
            verify=self.verify_ssl
        )

        if response.status_code != 200:
            error_detail = response.json().get('detail', 'Unknown error') if response.headers.get('content-type') == 'application/json' else response.text
            raise Exception(f"Ошибка удаления договора (HTTP {response.status_code}): {error_detail}")

        return True

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
        response = requests.post(
            f"{self.base_url}/api/sync",
            headers=self.headers,
            json={
                "last_sync_timestamp": last_sync_timestamp.isoformat(),
                "entity_types": entity_types
            },
            verify=self.verify_ssl
        )

        if response.status_code != 200:
            raise Exception("Ошибка синхронизации")

        return response.json()

    # =========================
    # УВЕДОМЛЕНИЯ
    # =========================

    def get_notifications(self, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Получить уведомления"""
        response = requests.get(
            f"{self.base_url}/api/notifications",
            headers=self.headers,
            params={"unread_only": unread_only}
        , verify=self.verify_ssl)

        if response.status_code != 200:
            raise Exception("Ошибка получения уведомлений")

        return response.json()

    def mark_notification_read(self, notification_id: int) -> bool:
        """Отметить уведомление как прочитанное"""
        response = requests.put(
            f"{self.base_url}/api/notifications/{notification_id}/read",
            headers=self.headers
        , verify=self.verify_ssl)

        return response.status_code == 200

    # =========================
    # HEALTH CHECK
    # =========================

    def health_check(self) -> bool:
        """Проверка доступности сервера"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5, verify=self.verify_ssl)
            return response.status_code == 200
        except Exception:
            return False
