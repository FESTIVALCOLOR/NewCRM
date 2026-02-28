# -*- coding: utf-8 -*-
"""
E2E Test Configuration - Fixtures and Data Factory
Реальные HTTP запросы к API серверу, реальные сотрудники и данные.
Все тестовые данные с префиксом __TEST__ для изоляции.
"""

import pytest
import requests
import time
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import API_BASE_URL
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


# ==============================================================
# AUTO-SKIP: пропуск E2E тестов если сервер недоступен
# ==============================================================

def _check_server_available():
    """Проверка доступности API сервера."""
    try:
        resp = requests.get(f"{API_BASE_URL}/health", timeout=3, verify=False)
        return resp.status_code == 200
    except Exception:
        return False


_server_available = _check_server_available()


def pytest_collection_modifyitems(config, items):
    """Пропустить все E2E тесты если сервер недоступен."""
    if _server_available:
        return
    skip_marker = pytest.mark.skip(reason="API сервер недоступен — E2E тесты пропущены")
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(skip_marker)


# ==============================================================
# КОНСТАНТЫ
# ==============================================================

TEST_PREFIX = "__TEST__"
API_BASE = API_BASE_URL
ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin123"
TEST_PASSWORD = "test123456"
REQUEST_TIMEOUT = 15

# ==============================================================
# ГЛОБАЛЬНАЯ HTTP SESSION (переиспользование TCP соединений)
# ==============================================================

_http_session = requests.Session()
_http_session.verify = False  # Self-signed certificate на сервере
_retry_strategy = Retry(
    total=2,
    backoff_factor=1,
    status_forcelist=[502, 503],
)
_adapter = HTTPAdapter(
    max_retries=_retry_strategy,
    pool_connections=20,
    pool_maxsize=20,
)
_http_session.mount("http://", _adapter)
_http_session.mount("https://", _adapter)


# ==============================================================
# БАЗОВЫЕ ФИКСТУРЫ
# ==============================================================

@pytest.fixture(scope="session")
def api_base():
    """Базовый URL API сервера"""
    return API_BASE


@pytest.fixture(scope="session")
def session_requests():
    """Общая requests.Session для переиспользования соединений"""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    yield s
    s.close()


@pytest.fixture(scope="session")
def admin_token(api_base):
    """Авторизация admin -> Bearer token"""
    response = _http_session.post(
        f"{api_base}/api/auth/login",
        data={"username": ADMIN_LOGIN, "password": ADMIN_PASSWORD},
        timeout=REQUEST_TIMEOUT
    )
    assert response.status_code == 200, (
        f"Не удалось авторизоваться как admin: {response.status_code} {response.text}"
    )
    data = response.json()
    assert "access_token" in data, "Ответ не содержит access_token"
    return data["access_token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    """HTTP headers с Bearer token администратора"""
    return {"Authorization": f"Bearer {admin_token}"}


# ==============================================================
# ТЕСТОВЫЕ СОТРУДНИКИ (8 ролей)
# ==============================================================

ROLE_DEFINITIONS = {
    'sdp': {
        'full_name': f'{TEST_PREFIX}СДП Тестовый',
        'login': f'{TEST_PREFIX}sdp',
        'position': 'СДП',
        'department': 'Административный',
        'role': 'СДП',
        'phone': '+79990000001',
    },
    'gap': {
        'full_name': f'{TEST_PREFIX}ГАП Тестовый',
        'login': f'{TEST_PREFIX}gap',
        'position': 'ГАП',
        'department': 'Административный',
        'role': 'ГАП',
        'phone': '+79990000002',
    },
    'designer': {
        'full_name': f'{TEST_PREFIX}Дизайнер Тестовый',
        'login': f'{TEST_PREFIX}designer',
        'position': 'Дизайнер',
        'department': 'Проектный',
        'role': 'Дизайнер',
        'phone': '+79990000003',
    },
    'draftsman': {
        'full_name': f'{TEST_PREFIX}Чертёжник Тестовый',
        'login': f'{TEST_PREFIX}draftsman',
        'position': 'Чертёжник',
        'department': 'Проектный',
        'role': 'Чертёжник',
        'phone': '+79990000004',
    },
    'manager': {
        'full_name': f'{TEST_PREFIX}Менеджер Тестовый',
        'login': f'{TEST_PREFIX}manager',
        'position': 'Менеджер',
        'department': 'Исполнительный',
        'role': 'Менеджер',
        'phone': '+79990000005',
    },
    'dan': {
        'full_name': f'{TEST_PREFIX}ДАН Тестовый',
        'login': f'{TEST_PREFIX}dan',
        'position': 'ДАН',
        'department': 'Исполнительный',
        'role': 'ДАН',
        'phone': '+79990000006',
    },
    'senior_manager': {
        'full_name': f'{TEST_PREFIX}Старший Менеджер Тестовый',
        'login': f'{TEST_PREFIX}smp',
        'position': 'Старший менеджер проектов',
        'department': 'Административный',
        'role': 'Старший менеджер проектов',
        'phone': '+79990000007',
    },
    'surveyor': {
        'full_name': f'{TEST_PREFIX}Замерщик Тестовый',
        'login': f'{TEST_PREFIX}surveyor',
        'position': 'Замерщик',
        'department': 'Исполнительный',
        'role': 'Замерщик',
        'phone': '+79990000008',
    },
}


@pytest.fixture(scope="session")
def test_employees(api_base, admin_headers):
    """
    Создание 8 тестовых сотрудников с разными ролями.
    Удаление в финализаторе.

    Returns:
        dict: {'sdp': {'id': 123, ...}, 'gap': {'id': 124, ...}, ...}
    """
    created = {}

    # Сначала удаляем возможные остатки от предыдущих запусков
    _cleanup_test_employees(api_base, admin_headers)

    for role_key, role_data in ROLE_DEFINITIONS.items():
        payload = {
            **role_data,
            'password': TEST_PASSWORD,
            'status': 'активный',
        }
        response = _http_session.post(
            f"{api_base}/api/employees",
            json=payload,
            headers=admin_headers,
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code in (200, 201):
            emp = response.json()
            created[role_key] = emp
            print(f"  [+] Создан тестовый сотрудник: {role_key} (id={emp['id']})")
        elif response.status_code == 400 and "уже занят" in response.text:
            # Логин уже существует — найти и использовать
            all_resp = _http_session.get(
                f"{api_base}/api/employees",
                headers=admin_headers,
                timeout=REQUEST_TIMEOUT
            )
            if all_resp.status_code == 200:
                for emp in all_resp.json():
                    if emp.get('login') == role_data['login']:
                        created[role_key] = emp
                        print(f"  [~] Используем существующего: {role_key} (id={emp['id']})")
                        break
        else:
            print(f"  [!] Ошибка создания {role_key}: {response.status_code} {response.text}")

    yield created

    # Очистка: переавторизуемся (старый токен мог протухнуть)
    print("\n[CLEANUP] Удаление тестовых сотрудников...")
    try:
        re_auth = _http_session.post(
            f"{api_base}/api/auth/login",
            data={"username": ADMIN_LOGIN, "password": ADMIN_PASSWORD},
            timeout=REQUEST_TIMEOUT
        )
        if re_auth.status_code == 200:
            fresh_headers = {"Authorization": f"Bearer {re_auth.json()['access_token']}"}
        else:
            fresh_headers = admin_headers
    except Exception:
        fresh_headers = admin_headers

    for role_key, emp_data in created.items():
        emp_id = emp_data.get('id')
        if emp_id:
            try:
                resp = _http_session.delete(
                    f"{api_base}/api/employees/{emp_id}",
                    headers=fresh_headers,
                    timeout=30
                )
                print(f"  [-] Удалён: {role_key} (id={emp_id}) -> {resp.status_code}")
            except Exception as e:
                print(f"  [!] Ошибка удаления {role_key}: {e}")


def _cleanup_test_employees(api_base, admin_headers):
    """Удаление остатков тестовых сотрудников от предыдущих запусков"""
    try:
        response = _http_session.get(
            f"{api_base}/api/employees",
            headers=admin_headers,
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            for emp in response.json():
                if emp.get('login', '').startswith(TEST_PREFIX) or \
                   emp.get('full_name', '').startswith(TEST_PREFIX):
                    try:
                        _http_session.delete(
                            f"{api_base}/api/employees/{emp['id']}",
                            headers=admin_headers,
                            timeout=REQUEST_TIMEOUT
                        )
                        print(f"  [cleanup] Удалён старый тестовый: {emp.get('login')} (id={emp['id']})")
                    except Exception:
                        pass
    except Exception:
        pass


@pytest.fixture(scope="session")
def role_tokens(api_base, test_employees):
    """
    Токены авторизации для каждой роли.

    Returns:
        dict: {'sdp': {'Authorization': 'Bearer ...'}, ...}
    """
    tokens = {}
    for role_key, emp_data in test_employees.items():
        login = emp_data.get('login')
        if not login:
            continue
        try:
            response = _http_session.post(
                f"{api_base}/api/auth/login",
                data={"username": login, "password": TEST_PASSWORD},
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                token = response.json()["access_token"]
                tokens[role_key] = {"Authorization": f"Bearer {token}"}
                print(f"  [auth] Токен получен для: {role_key}")
            elif response.status_code == 429:
                # Rate limit — ждём и повторяем
                print(f"  [auth] Rate limit для {role_key}, ждём 10с...")
                time.sleep(10)
                response = _http_session.post(
                    f"{api_base}/api/auth/login",
                    data={"username": login, "password": TEST_PASSWORD},
                    timeout=REQUEST_TIMEOUT
                )
                if response.status_code == 200:
                    token = response.json()["access_token"]
                    tokens[role_key] = {"Authorization": f"Bearer {token}"}
                    print(f"  [auth] Токен получен для: {role_key} (после retry)")
                else:
                    print(f"  [!] Не удалось получить токен для {role_key}: {response.status_code}")
            else:
                print(f"  [!] Не удалось получить токен для {role_key}: {response.status_code}")
        except Exception as e:
            print(f"  [!] Ошибка авторизации {role_key}: {e}")

    return tokens


# ==============================================================
# ФАБРИКА ТЕСТОВЫХ ДАННЫХ
# ==============================================================

class TestDataFactory:
    """
    Фабрика тестовых данных с отслеживанием для автоочистки.
    Все создаваемые сущности удаляются при вызове cleanup_all().
    """

    def __init__(self, api_base: str, admin_headers: dict):
        self.api_base = api_base
        self.headers = admin_headers
        self._created_clients: List[int] = []
        self._created_contracts: List[int] = []
        self._created_crm_cards: List[int] = []
        self._created_supervision_cards: List[int] = []
        self._created_payments: List[int] = []
        self._created_files: List[int] = []
        self._created_rates: List[int] = []
        self._created_salaries: List[int] = []
        self._counter = int(time.time()) % 100000

    def _next_id(self) -> int:
        self._counter += 1
        return self._counter

    # --- Клиенты ---

    def create_client(self, **overrides) -> dict:
        """Создать тестового клиента"""
        n = self._next_id()
        data = {
            "client_type": "Физическое лицо",
            "full_name": f"{TEST_PREFIX}Клиент_{n}",
            "phone": f"+7999{n:07d}",
            "email": f"test_{n}@test.com",
        }
        data.update(overrides)
        resp = _http_session.post(
            f"{self.api_base}/api/clients",
            json=data,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT
        )
        assert resp.status_code == 200, f"Ошибка создания клиента: {resp.status_code} {resp.text}"
        client = resp.json()
        self._created_clients.append(client["id"])
        return client

    # --- Договоры ---

    def create_contract(self, client_id: int, **overrides) -> dict:
        """Создать тестовый договор"""
        n = self._next_id()
        data = {
            "client_id": client_id,
            "project_type": "Индивидуальный",
            "agent_type": "ФЕСТИВАЛЬ",
            "city": "СПБ",
            "contract_number": f"{TEST_PREFIX}{n}",
            "contract_date": datetime.now().strftime("%Y-%m-%d"),
            "address": f"Тестовый адрес {n}",
            "area": 75.0,
            "total_amount": 300000.0,
            "advance_payment": 150000.0,
            "additional_payment": 150000.0,
            "contract_period": 30,
            "status": "Новый заказ",
        }
        data.update(overrides)
        resp = _http_session.post(
            f"{self.api_base}/api/contracts",
            json=data,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT
        )
        assert resp.status_code == 200, f"Ошибка создания договора: {resp.status_code} {resp.text}"
        contract = resp.json()
        self._created_contracts.append(contract["id"])
        return contract

    # --- CRM карточки ---

    def create_crm_card(self, contract_id: int, **overrides) -> dict:
        """Создать или получить CRM карточку (контракт авто-создаёт карточку)"""
        data = {
            "contract_id": contract_id,
            "column_name": "Новый заказ",
            "order_position": 0,
        }
        data.update(overrides)
        resp = _http_session.post(
            f"{self.api_base}/api/crm/cards",
            json=data,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT
        )
        if resp.status_code == 409:
            # Карточка уже создана автоматически при создании контракта
            cards_resp = _http_session.get(
                f"{self.api_base}/api/crm/cards",
                params={"project_type": "Индивидуальный"},
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            assert cards_resp.status_code == 200, f"Ошибка получения CRM карточек: {cards_resp.status_code}"
            cards = cards_resp.json()
            card = next((c for c in cards if c["contract_id"] == contract_id), None)
            if not card:
                # Попробуем шаблонные
                cards_resp = _http_session.get(
                    f"{self.api_base}/api/crm/cards",
                    params={"project_type": "Шаблонный"},
                    headers=self.headers,
                    timeout=REQUEST_TIMEOUT
                )
                cards = cards_resp.json() if cards_resp.status_code == 200 else []
                card = next((c for c in cards if c["contract_id"] == contract_id), None)
            assert card, f"Карточка для contract_id={contract_id} не найдена после 409"
        else:
            assert resp.status_code == 200, f"Ошибка создания CRM карточки: {resp.status_code} {resp.text}"
            card = resp.json()
        self._created_crm_cards.append(card["id"])
        return card

    # --- Надзор ---

    def create_supervision_card(self, contract_id: int, **overrides) -> dict:
        """Создать карточку надзора через POST /api/supervision/cards"""
        data = {
            "contract_id": contract_id,
            "column_name": "Новый заказ",
        }
        data.update(overrides)
        resp = _http_session.post(
            f"{self.api_base}/api/supervision/cards",
            json=data,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT
        )
        assert resp.status_code == 200, \
            f"Ошибка создания карточки надзора: {resp.status_code} {resp.text}"
        card = resp.json()
        self._created_supervision_cards.append(card["id"])
        return card

    # --- Платежи ---

    def create_payment(self, contract_id: int, employee_id: int,
                       role: str, stage_name: str = None,
                       crm_card_id: int = None,
                       supervision_card_id: int = None,
                       **overrides) -> dict:
        """Создать платёж"""
        data = {
            "contract_id": contract_id,
            "employee_id": employee_id,
            "role": role,
            "stage_name": stage_name,
            "crm_card_id": crm_card_id,
            "supervision_card_id": supervision_card_id,
            "calculated_amount": 0.0,
            "final_amount": 0.0,
            "is_manual": False,
            "reassigned": False,
        }
        data.update(overrides)
        resp = _http_session.post(
            f"{self.api_base}/api/payments",
            json=data,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT
        )
        assert resp.status_code == 200, f"Ошибка создания платежа: {resp.status_code} {resp.text}"
        payment = resp.json()
        self._created_payments.append(payment["id"])
        return payment

    # --- Файлы ---

    def create_file_record(self, contract_id: int, stage: str,
                           file_type: str, file_name: str = None,
                           **overrides) -> dict:
        """Создать запись файла в БД (без реальной загрузки на ЯД)"""
        n = self._next_id()
        data = {
            "contract_id": contract_id,
            "stage": stage,
            "file_type": file_type,
            "file_name": file_name or f"{TEST_PREFIX}file_{n}.txt",
            "yandex_path": f"/{TEST_PREFIX}/files/{n}.txt",
            "public_link": "",
            "file_order": 0,
            "variation": 1,
        }
        data.update(overrides)
        resp = _http_session.post(
            f"{self.api_base}/api/files",
            json=data,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT
        )
        assert resp.status_code == 200, f"Ошибка создания файла: {resp.status_code} {resp.text}"
        file_record = resp.json()
        self._created_files.append(file_record["id"])
        return file_record

    # --- Тарифы ---

    def create_rate(self, **overrides) -> dict:
        """Создать тестовый тариф"""
        n = self._next_id()
        data = {
            "project_type": "Индивидуальный",
            "role": "Дизайнер",
            "rate_per_m2": 100.0,
            "stage_name": f"{TEST_PREFIX}stage_{n}",
        }
        data.update(overrides)
        resp = _http_session.post(
            f"{self.api_base}/api/rates",
            json=data,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT
        )
        assert resp.status_code == 200, f"Ошибка создания тарифа: {resp.status_code} {resp.text}"
        rate = resp.json()
        self._created_rates.append(rate["id"])
        return rate

    def track_rate(self, rate_id: int):
        """Добавить внешне созданный тариф в трекинг"""
        if rate_id not in self._created_rates:
            self._created_rates.append(rate_id)

    # --- Зарплаты ---

    def create_salary(self, employee_id: int, **overrides) -> dict:
        """Создать тестовую зарплату"""
        n = self._next_id()
        data = {
            "employee_id": employee_id,
            "payment_type": "Оклад",
            "amount": 50000.0,
            "report_month": datetime.now().strftime("%Y-%m"),
        }
        data.update(overrides)
        resp = _http_session.post(
            f"{self.api_base}/api/salaries",
            json=data,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT
        )
        assert resp.status_code == 200, f"Ошибка создания зарплаты: {resp.status_code} {resp.text}"
        salary = resp.json()
        self._created_salaries.append(salary["id"])
        return salary

    def track_salary(self, salary_id: int):
        """Добавить внешне созданную зарплату в трекинг"""
        if salary_id not in self._created_salaries:
            self._created_salaries.append(salary_id)

    # --- Очистка ---

    def cleanup_all(self):
        """
        Удаление всех созданных тестовых данных.
        Порядок: salaries -> rates -> files -> payments -> supervision -> crm -> contracts -> clients
        """
        def _delete(entity_name, url, id_val):
            try:
                resp = _http_session.delete(
                    url,
                    headers=self.headers,
                    timeout=REQUEST_TIMEOUT
                )
                if resp.status_code not in (200, 204, 404):
                    print(f"  [cleanup] {entity_name} id={id_val}: HTTP {resp.status_code}")
            except Exception as e:
                print(f"  [cleanup] {entity_name} id={id_val}: {e}")

        for sal_id in self._created_salaries:
            _delete('salary', f"{self.api_base}/api/salaries/{sal_id}", sal_id)
        self._created_salaries.clear()

        for rate_id in self._created_rates:
            _delete('rate', f"{self.api_base}/api/rates/{rate_id}", rate_id)
        self._created_rates.clear()

        for file_id in self._created_files:
            _delete('file', f"{self.api_base}/api/files/{file_id}", file_id)
        self._created_files.clear()

        for pay_id in self._created_payments:
            _delete('payment', f"{self.api_base}/api/payments/{pay_id}", pay_id)
        self._created_payments.clear()

        for sv_id in self._created_supervision_cards:
            _delete('supervision', f"{self.api_base}/api/supervision/orders/{sv_id}", sv_id)
        self._created_supervision_cards.clear()

        for crm_id in self._created_crm_cards:
            _delete('crm_card', f"{self.api_base}/api/crm/cards/{crm_id}", crm_id)
        self._created_crm_cards.clear()

        for con_id in self._created_contracts:
            _delete('contract', f"{self.api_base}/api/contracts/{con_id}", con_id)
        self._created_contracts.clear()

        for cl_id in self._created_clients:
            _delete('client', f"{self.api_base}/api/clients/{cl_id}", cl_id)
        self._created_clients.clear()

    def track_crm_card(self, card_id: int):
        """Добавить внешне созданную CRM карточку в трекинг для очистки"""
        if card_id not in self._created_crm_cards:
            self._created_crm_cards.append(card_id)

    def track_supervision_card(self, card_id: int):
        """Добавить внешне созданную карточку надзора в трекинг"""
        if card_id not in self._created_supervision_cards:
            self._created_supervision_cards.append(card_id)

    def track_payment(self, payment_id: int):
        """Добавить внешне созданный платёж в трекинг"""
        if payment_id not in self._created_payments:
            self._created_payments.append(payment_id)

    def track_file(self, file_id: int):
        """Добавить внешне созданный файл в трекинг"""
        if file_id not in self._created_files:
            self._created_files.append(file_id)


def _factory_teardown(f, api_base, force_cleanup=False):
    """Общая логика очистки для фабрики тестовых данных."""
    try:
        re_auth = _http_session.post(
            f"{api_base}/api/auth/login",
            data={"username": ADMIN_LOGIN, "password": ADMIN_PASSWORD},
            timeout=REQUEST_TIMEOUT
        )
        if re_auth.status_code == 200:
            f.headers = {"Authorization": f"Bearer {re_auth.json()['access_token']}"}
    except Exception:
        pass
    f.cleanup_all()
    if force_cleanup:
        _force_cleanup_all_test_data(api_base, f.headers)


@pytest.fixture(scope="session")
def factory(api_base, admin_headers):
    """Фабрика тестовых данных с автоочисткой (session scope)"""
    f = TestDataFactory(api_base, admin_headers)
    yield f
    print("\n[CLEANUP] Очистка тестовых данных...")
    _factory_teardown(f, api_base, force_cleanup=True)
    print("[CLEANUP] Готово")


@pytest.fixture(scope="module")
def module_factory(api_base, admin_headers):
    """Фабрика тестовых данных с module-scoped очисткой"""
    f = TestDataFactory(api_base, admin_headers)
    yield f
    _factory_teardown(f, api_base, force_cleanup=False)


def _force_cleanup_all_test_data(api_base: str, headers: dict):
    """
    Принудительная зачистка ВСЕХ __TEST__ данных на сервере.
    Ищет по имени/логину и удаляет, не полагаясь на tracked IDs.
    """
    try:
        # 1. Удаляем тестовые контракты (каскадно удалит crm_cards, payments, files)
        resp = _http_session.get(f"{api_base}/api/contracts", headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            test_contracts = [c for c in resp.json()
                             if TEST_PREFIX in (c.get('contract_number') or '')
                             or TEST_PREFIX in (c.get('address') or '')]
            for c in test_contracts:
                try:
                    _http_session.delete(f"{api_base}/api/contracts/{c['id']}", headers=headers, timeout=REQUEST_TIMEOUT)
                    print(f"  [force] Удалён контракт: {c['id']}")
                except Exception:
                    pass

        # 2. Удаляем тестовых клиентов
        resp = _http_session.get(f"{api_base}/api/clients", headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            test_clients = [c for c in resp.json() if TEST_PREFIX in (c.get('full_name') or '')]
            for c in test_clients:
                try:
                    _http_session.delete(f"{api_base}/api/clients/{c['id']}", headers=headers, timeout=REQUEST_TIMEOUT)
                    print(f"  [force] Удалён клиент: {c['id']}")
                except Exception:
                    pass

        # 3. Удаляем тестовых сотрудников
        _cleanup_test_employees(api_base, headers)

        if test_contracts or test_clients:
            print(f"  [force] Итого удалено: {len(test_contracts)} контрактов, {len(test_clients)} клиентов")
    except Exception as e:
        print(f"  [force] Ошибка принудительной очистки: {e}")


# ==============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================================================

def api_get(api_base: str, path: str, headers: dict, params: dict = None) -> requests.Response:
    """GET запрос к API"""
    return _http_session.get(
        f"{api_base}{path}",
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT
    )


def api_post(api_base: str, path: str, headers: dict, json: dict = None, data: dict = None, params: dict = None) -> requests.Response:
    """POST запрос к API"""
    return _http_session.post(
        f"{api_base}{path}",
        headers=headers,
        json=json,
        data=data,
        params=params,
        timeout=REQUEST_TIMEOUT
    )


def api_patch(api_base: str, path: str, headers: dict, json: dict = None, params: dict = None) -> requests.Response:
    """PATCH запрос к API"""
    return _http_session.patch(
        f"{api_base}{path}",
        headers=headers,
        json=json,
        params=params,
        timeout=REQUEST_TIMEOUT
    )


def api_put(api_base: str, path: str, headers: dict, json: dict = None) -> requests.Response:
    """PUT запрос к API"""
    return _http_session.put(
        f"{api_base}{path}",
        headers=headers,
        json=json,
        timeout=REQUEST_TIMEOUT
    )


def api_delete(api_base: str, path: str, headers: dict, params: dict = None) -> requests.Response:
    """DELETE запрос к API"""
    return _http_session.delete(
        f"{api_base}{path}",
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT
    )
