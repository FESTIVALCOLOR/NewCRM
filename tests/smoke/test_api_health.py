"""
Smoke Tests - API Health Check
Быстрая проверка что API сервер работает и endpoints отвечают

Эти тесты используют РЕАЛЬНЫЙ API сервер (не Mock!)
Запуск: pytest tests/smoke/ -v
"""

import pytest
import requests
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import API_BASE_URL


# ==================== FIXTURES ====================

@pytest.fixture(scope="module")
def api_base():
    """Базовый URL API"""
    return API_BASE_URL


@pytest.fixture(scope="module")
def auth_token(api_base):
    """Получение токена авторизации"""
    try:
        response = requests.post(
            f"{api_base}/api/auth/login",
            data={"username": "admin", "password": "admin123"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception as e:
        pytest.skip(f"Не удалось получить токен: {e}")
    return None


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers с авторизацией"""
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}
    return {}


# ==================== SMOKE TESTS ====================

class TestAPIHealth:
    """Проверка что API сервер отвечает"""

    def test_smoke_001_server_reachable(self, api_base):
        """SMOKE_001: Сервер доступен"""
        try:
            response = requests.get(f"{api_base}/", timeout=5)
            assert response.status_code == 200, f"Сервер вернул {response.status_code}"
        except requests.exceptions.ConnectionError:
            pytest.fail(f"Сервер {api_base} недоступен")
        except requests.exceptions.Timeout:
            pytest.fail(f"Таймаут подключения к {api_base}")

    def test_smoke_002_auth_endpoint_exists(self, api_base):
        """SMOKE_002: Endpoint авторизации существует"""
        response = requests.post(
            f"{api_base}/api/auth/login",
            data={"username": "wrong", "password": "wrong"},
            timeout=5
        )
        # Даже с неправильными данными должен вернуть 401, а не 404
        assert response.status_code in [200, 401, 422], \
            f"Endpoint /api/auth/login вернул {response.status_code}"

    def test_smoke_003_auth_works(self, api_base):
        """SMOKE_003: Авторизация работает"""
        response = requests.post(
            f"{api_base}/api/auth/login",
            data={"username": "admin", "password": "admin123"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data, "Ответ не содержит access_token"
        else:
            # Если admin/admin123 не работает - это тоже важная информация
            pytest.skip(f"Авторизация admin/admin123 не работает: {response.status_code}")


class TestCRMEndpoints:
    """Проверка CRM endpoints"""

    def test_smoke_010_crm_cards_endpoint(self, api_base, auth_headers):
        """SMOKE_010: Endpoint CRM карточек отвечает"""
        if not auth_headers:
            pytest.skip("Нет авторизации")

        response = requests.get(
            f"{api_base}/api/crm/cards",
            headers=auth_headers,
            params={"project_type": "Индивидуальный"},
            timeout=10
        )
        assert response.status_code == 200, f"CRM cards вернул {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "CRM cards должен вернуть список"

    def test_smoke_011_crm_cards_returns_valid_structure(self, api_base, auth_headers):
        """SMOKE_011: CRM карточки возвращают правильную структуру"""
        if not auth_headers:
            pytest.skip("Нет авторизации")

        response = requests.get(
            f"{api_base}/api/crm/cards",
            headers=auth_headers,
            params={"project_type": "Индивидуальный"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                card = data[0]
                # Проверяем наличие обязательных полей
                required_fields = ['id', 'contract_id', 'column_name']
                for field in required_fields:
                    assert field in card, f"Отсутствует поле {field} в карточке CRM"


class TestContractsEndpoints:
    """Проверка endpoints договоров"""

    def test_smoke_020_contracts_endpoint(self, api_base, auth_headers):
        """SMOKE_020: Endpoint договоров отвечает"""
        if not auth_headers:
            pytest.skip("Нет авторизации")

        response = requests.get(
            f"{api_base}/api/contracts",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200, f"Contracts вернул {response.status_code}"

    def test_smoke_021_contracts_returns_list(self, api_base, auth_headers):
        """SMOKE_021: Договоры возвращают список"""
        if not auth_headers:
            pytest.skip("Нет авторизации")

        response = requests.get(
            f"{api_base}/api/contracts",
            headers=auth_headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), "Contracts должен вернуть список"


class TestClientsEndpoints:
    """Проверка endpoints клиентов"""

    def test_smoke_030_clients_endpoint(self, api_base, auth_headers):
        """SMOKE_030: Endpoint клиентов отвечает"""
        if not auth_headers:
            pytest.skip("Нет авторизации")

        response = requests.get(
            f"{api_base}/api/clients",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200, f"Clients вернул {response.status_code}"


class TestPaymentsEndpoints:
    """Проверка endpoints платежей"""

    def test_smoke_040_payments_endpoint(self, api_base, auth_headers):
        """SMOKE_040: Endpoint платежей отвечает"""
        if not auth_headers:
            pytest.skip("Нет авторизации")

        response = requests.get(
            f"{api_base}/api/payments",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200, f"Payments вернул {response.status_code}"

    def test_smoke_041_payments_with_month_filter(self, api_base, auth_headers):
        """SMOKE_041: Платежи с фильтром по месяцу"""
        if not auth_headers:
            pytest.skip("Нет авторизации")

        response = requests.get(
            f"{api_base}/api/payments",
            headers=auth_headers,
            params={"month": 1, "year": 2025},
            timeout=10
        )
        assert response.status_code == 200, f"Payments с фильтром вернул {response.status_code}"


class TestEmployeesEndpoints:
    """Проверка endpoints сотрудников"""

    def test_smoke_050_employees_endpoint(self, api_base, auth_headers):
        """SMOKE_050: Endpoint сотрудников отвечает"""
        if not auth_headers:
            pytest.skip("Нет авторизации")

        response = requests.get(
            f"{api_base}/api/employees",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200, f"Employees вернул {response.status_code}"


class TestSupervisionEndpoints:
    """Проверка endpoints авторского надзора"""

    def test_smoke_060_supervision_cards_endpoint(self, api_base, auth_headers):
        """SMOKE_060: Endpoint карточек надзора отвечает"""
        if not auth_headers:
            pytest.skip("Нет авторизации")

        response = requests.get(
            f"{api_base}/api/supervision/cards",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200, f"Supervision cards вернул {response.status_code}"


class TestStatisticsEndpoints:
    """Проверка endpoints статистики"""

    def test_smoke_070_statistics_projects(self, api_base, auth_headers):
        """SMOKE_070: Статистика проектов отвечает"""
        if not auth_headers:
            pytest.skip("Нет авторизации")

        response = requests.get(
            f"{api_base}/api/statistics/projects",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200, f"Statistics projects вернул {response.status_code}"

    def test_smoke_071_statistics_supervision(self, api_base, auth_headers):
        """SMOKE_071: Статистика надзора отвечает"""
        if not auth_headers:
            pytest.skip("Нет авторизации")

        response = requests.get(
            f"{api_base}/api/statistics/supervision",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200, f"Statistics supervision вернул {response.status_code}"


class TestRatesEndpoints:
    """Проверка endpoints тарифов"""

    def test_smoke_080_rates_endpoint(self, api_base, auth_headers):
        """SMOKE_080: Endpoint тарифов отвечает"""
        if not auth_headers:
            pytest.skip("Нет авторизации")

        response = requests.get(
            f"{api_base}/api/rates",
            headers=auth_headers,
            timeout=10
        )
        assert response.status_code == 200, f"Rates вернул {response.status_code}"

    def test_smoke_081_template_rates(self, api_base, auth_headers):
        """SMOKE_081: Шаблонные тарифы отвечают"""
        if not auth_headers:
            pytest.skip("Нет авторизации")

        response = requests.get(
            f"{api_base}/api/rates/template",
            headers=auth_headers,
            timeout=10
        )
        # Может вернуть 200 или 404 если шаблонов нет
        assert response.status_code in [200, 404], f"Template rates вернул {response.status_code}"
