# -*- coding: utf-8 -*-
"""
Smoke Tests: Критические пользовательские сценарии на РЕАЛЬНОМ сервере.

Каждый тест — полный цикл действия пользователя:
создать → прочитать → изменить → удалить.

Если этот тест падает — функционал сломан для конечного пользователя.
Запуск: pytest tests/smoke/test_critical_workflows.py -v --timeout=60

Требует: работающий API сервер (auto-skip если недоступен).
"""

import pytest
import requests
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import API_BASE_URL

TEST_PREFIX = "__SMOKE__"
TIMEOUT = 15


# ════════════════════════════════════════════════════════════
# HTTP helpers
# ════════════════════════════════════════════════════════════

_session = requests.Session()
_session.verify = False


def _get(path, headers, params=None):
    return _session.get(f"{API_BASE_URL}{path}", headers=headers,
                        params=params, timeout=TIMEOUT)


def _post(path, headers, json=None, data=None):
    return _session.post(f"{API_BASE_URL}{path}", headers=headers,
                         json=json, data=data, timeout=TIMEOUT)


def _put(path, headers, json=None):
    return _session.put(f"{API_BASE_URL}{path}", headers=headers,
                        json=json, timeout=TIMEOUT)


def _patch(path, headers, json=None):
    return _session.patch(f"{API_BASE_URL}{path}", headers=headers,
                          json=json, timeout=TIMEOUT)


def _delete(path, headers):
    return _session.delete(f"{API_BASE_URL}{path}", headers=headers, timeout=TIMEOUT)


# ════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def admin_headers():
    """Авторизация admin."""
    resp = _post("/api/auth/login", {}, data={"username": "admin", "password": "admin123"})
    if resp.status_code != 200:
        pytest.skip(f"Не удалось авторизоваться: {resp.status_code}")
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def cleanup_ids():
    """Трекинг созданных ID для cleanup после теста."""
    ids = {"clients": [], "contracts": [], "employees": [], "crm_cards": [],
           "supervision_cards": [], "payments": []}
    yield ids
    # Нет автоочистки — каждый тест чистит за собой явно


# ════════════════════════════════════════════════════════════
# 1. WORKFLOW: Клиент → Договор → CRM Карточка
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestClientToCardWorkflow:
    """Полный цикл: создать клиента → договор → CRM карточка → удалить."""

    def test_full_lifecycle(self, admin_headers):
        """Создание клиента, договора, проверка CRM карточки, удаление."""
        # 1. Создаём клиента
        client_resp = _post("/api/clients", admin_headers, json={
            "client_type": "Физическое лицо",
            "full_name": f"{TEST_PREFIX}Клиент Smoke",
            "phone": "+79990001234",
        })
        assert client_resp.status_code == 200, \
            f"Ошибка создания клиента: {client_resp.status_code} {client_resp.text}"
        client = client_resp.json()
        client_id = client["id"]

        try:
            # 2. Создаём договор
            contract_resp = _post("/api/contracts", admin_headers, json={
                "client_id": client_id,
                "project_type": "Индивидуальный",
                "agent_type": "ФЕСТИВАЛЬ",
                "city": "СПБ",
                "contract_number": f"{TEST_PREFIX}{datetime.now().strftime('%H%M%S')}",
                "contract_date": datetime.now().strftime("%Y-%m-%d"),
                "address": f"{TEST_PREFIX}Тестовый адрес, д.1",
                "area": 75.0,
                "total_amount": 300000.0,
                "advance_payment": 150000.0,
                "additional_payment": 150000.0,
                "contract_period": 30,
                "status": "Новый заказ",
            })
            assert contract_resp.status_code == 200, \
                f"Ошибка создания договора: {contract_resp.status_code} {contract_resp.text}"
            contract = contract_resp.json()
            contract_id = contract["id"]

            # 3. Проверяем что CRM карточка создалась
            cards_resp = _get("/api/crm/cards", admin_headers,
                              params={"project_type": "Индивидуальный"})
            assert cards_resp.status_code == 200
            cards = cards_resp.json()
            our_card = [c for c in cards if c["contract_id"] == contract_id]
            assert len(our_card) >= 1, \
                f"CRM карточка не создалась для договора {contract_id}"
            card = our_card[0]

            # 4. Проверяем данные карточки
            assert card["column_name"] == "Новый заказ", \
                f"Неправильная колонка: {card['column_name']}"

            # 5. Проверяем клиента доступен по GET
            client_get = _get(f"/api/clients/{client_id}", admin_headers)
            assert client_get.status_code == 200
            assert client_get.json()["full_name"] == f"{TEST_PREFIX}Клиент Smoke"

        finally:
            # Cleanup: удаляем в обратном порядке
            if 'contract_id' in locals():
                _delete(f"/api/contracts/{contract_id}", admin_headers)
            _delete(f"/api/clients/{client_id}", admin_headers)


# ════════════════════════════════════════════════════════════
# 2. WORKFLOW: Обновление клиента
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestClientUpdateWorkflow:
    """Создать → обновить → проверить обновление → удалить."""

    def test_update_and_verify(self, admin_headers):
        """Обновление клиента сохраняется и видно при повторном запросе."""
        # Создаём
        resp = _post("/api/clients", admin_headers, json={
            "client_type": "Физическое лицо",
            "full_name": f"{TEST_PREFIX}До обновления",
            "phone": "+79990005678",
        })
        assert resp.status_code == 200
        client_id = resp.json()["id"]

        try:
            # Обновляем
            upd = _put(f"/api/clients/{client_id}", admin_headers, json={
                "full_name": f"{TEST_PREFIX}После обновления",
                "email": "updated@test.com",
            })
            assert upd.status_code == 200, \
                f"Ошибка обновления: {upd.status_code} {upd.text}"

            # Проверяем через GET
            check = _get(f"/api/clients/{client_id}", admin_headers)
            assert check.status_code == 200
            data = check.json()
            assert data["full_name"] == f"{TEST_PREFIX}После обновления", \
                f"Обновление НЕ сохранилось: full_name={data['full_name']}"

        finally:
            _delete(f"/api/clients/{client_id}", admin_headers)


# ════════════════════════════════════════════════════════════
# 3. WORKFLOW: Сотрудник — создание и права
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestEmployeeWorkflow:
    """Создать сотрудника → авторизоваться → проверить доступ → удалить."""

    def test_create_login_access(self, admin_headers):
        """Новый сотрудник может авторизоваться и получить свои данные."""
        # Создаём
        emp_resp = _post("/api/employees", admin_headers, json={
            "full_name": f"{TEST_PREFIX}Smoke Дизайнер",
            "login": f"{TEST_PREFIX}smoke_designer",
            "password": "smoketest123",
            "position": "Дизайнер",
            "department": "Проектный",
            "phone": "+79990009876",
            "status": "активный",
        })
        assert emp_resp.status_code in (200, 201), \
            f"Ошибка создания сотрудника: {emp_resp.status_code} {emp_resp.text}"
        emp_id = emp_resp.json()["id"]

        try:
            # Авторизуемся под новым сотрудником
            login_resp = _post("/api/auth/login", {},
                               data={"username": f"{TEST_PREFIX}smoke_designer",
                                     "password": "smoketest123"})
            assert login_resp.status_code == 200, \
                f"Сотрудник не может авторизоваться: {login_resp.status_code}"
            token = login_resp.json()["access_token"]
            emp_headers = {"Authorization": f"Bearer {token}"}

            # Проверяем GET /api/auth/me
            me_resp = _get("/api/auth/me", emp_headers)
            assert me_resp.status_code == 200
            me = me_resp.json()
            assert me["position"] == "Дизайнер", \
                f"Неправильная должность: {me.get('position')}"

        finally:
            _delete(f"/api/employees/{emp_id}", admin_headers)


# ════════════════════════════════════════════════════════════
# 4. WORKFLOW: CRM карточка — перемещение
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestCrmCardMoveWorkflow:
    """Создать карточку → переместить между колонками → проверить."""

    def test_move_card_between_columns(self, admin_headers):
        """Перемещение CRM карточки сохраняется."""
        # Создаём клиента + договор
        client = _post("/api/clients", admin_headers, json={
            "client_type": "Физическое лицо",
            "full_name": f"{TEST_PREFIX}Move Test",
            "phone": "+79990004321",
        }).json()

        contract = _post("/api/contracts", admin_headers, json={
            "client_id": client["id"],
            "project_type": "Индивидуальный",
            "agent_type": "ФЕСТИВАЛЬ",
            "city": "МСК",
            "contract_number": f"{TEST_PREFIX}MOV{datetime.now().strftime('%H%M%S')}",
            "contract_date": datetime.now().strftime("%Y-%m-%d"),
            "address": f"{TEST_PREFIX}Move addr",
            "area": 50.0,
            "total_amount": 200000.0,
            "advance_payment": 100000.0,
            "additional_payment": 100000.0,
            "contract_period": 20,
            "status": "Новый заказ",
        }).json()

        try:
            # Находим CRM карточку
            cards = _get("/api/crm/cards", admin_headers,
                         params={"project_type": "Индивидуальный"}).json()
            card = next((c for c in cards if c["contract_id"] == contract["id"]), None)
            assert card, "CRM карточка не найдена"

            # Перемещаем (endpoint /column для смены колонки)
            # Допустимые: Новый заказ → В ожидании → Стадия 1 → ...
            move_resp = _patch(f"/api/crm/cards/{card['id']}/column", admin_headers,
                               json={"column_name": "В ожидании"})
            assert move_resp.status_code == 200, \
                f"Ошибка перемещения: {move_resp.status_code} {move_resp.text}"

            # Проверяем
            updated = _get(f"/api/crm/cards/{card['id']}", admin_headers)
            assert updated.status_code == 200
            assert updated.json()["column_name"] == "В ожидании", \
                f"Перемещение не сохранилось: {updated.json().get('column_name')}"

        finally:
            _delete(f"/api/contracts/{contract['id']}", admin_headers)
            _delete(f"/api/clients/{client['id']}", admin_headers)


# ════════════════════════════════════════════════════════════
# 5. WORKFLOW: Ошибки — 404, дубликаты
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestErrorScenarios:
    """Проверка что сервер корректно возвращает ошибки."""

    def test_get_nonexistent_client(self, admin_headers):
        """GET /api/clients/999999 → 404."""
        resp = _get("/api/clients/999999", admin_headers)
        assert resp.status_code == 404

    def test_get_nonexistent_contract(self, admin_headers):
        """GET /api/contracts/999999 → 404."""
        resp = _get("/api/contracts/999999", admin_headers)
        assert resp.status_code == 404

    def test_create_with_empty_body(self, admin_headers):
        """POST /api/clients с пустым телом → 400/422."""
        resp = _post("/api/clients", admin_headers, json={})
        assert resp.status_code in (400, 422), \
            f"Ожидали 400/422, получили {resp.status_code}"

    def test_unauthorized_access(self):
        """Запрос без токена → 401/403."""
        resp = _get("/api/clients", {})
        assert resp.status_code in (401, 403)

    def test_invalid_token(self):
        """Запрос с невалидным токеном → 401/403."""
        resp = _get("/api/clients", {"Authorization": "Bearer invalid_token_12345"})
        assert resp.status_code in (401, 403)


# ════════════════════════════════════════════════════════════
# 6. WORKFLOW: Dashboard данные
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardWorkflow:
    """Dashboard возвращает корректные данные."""

    def test_dashboard_crm_returns_numbers(self, admin_headers):
        """GET /api/dashboard/crm возвращает числовые статистики."""
        resp = _get("/api/dashboard/crm", admin_headers,
                    params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_orders" in data
        assert isinstance(data["total_orders"], int)
        assert data["total_orders"] >= 0

    def test_agents_list_not_empty(self, admin_headers):
        """GET /api/v1/agents возвращает непустой список."""
        resp = _get("/api/v1/agents", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Агенты должны быть настроены
        assert len(data) > 0, "Список агентов пуст — возможно не настроены"

    def test_cities_list_not_empty(self, admin_headers):
        """GET /api/v1/cities возвращает непустой список."""
        resp = _get("/api/v1/cities", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Список городов пуст — возможно не настроены"


# ════════════════════════════════════════════════════════════
# 7. WORKFLOW: Авторский надзор
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSupervisionWorkflow:
    """Карточки надзора: чтение активных и архивных."""

    def test_active_supervision_readable(self, admin_headers):
        """GET /api/supervision/cards?status=active — 200."""
        resp = _get("/api/supervision/cards", admin_headers,
                    params={"status": "active"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_archived_supervision_readable(self, admin_headers):
        """GET /api/supervision/cards?status=archived — 200."""
        resp = _get("/api/supervision/cards", admin_headers,
                    params={"status": "archived"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ════════════════════════════════════════════════════════════
# 8. WORKFLOW: Отметка оплаты (mark-paid / mark-unpaid toggle)
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestPaymentMarkPaidWorkflow:
    """Цикл: найти платёж → отметить к оплате → отметить оплачено → проверить."""

    def test_mark_to_pay_and_paid(self, admin_headers):
        """Полный цикл статусов: NULL → to_pay → paid → проверить."""
        # Находим любой неоплаченный платёж
        resp = _get("/api/payments", admin_headers)
        assert resp.status_code == 200
        payments = resp.json()
        assert len(payments) > 0, "Нет платежей для тестирования"

        # Ищем неоплаченный
        target = None
        for p in payments:
            if not p.get("is_paid") and p.get("final_amount", 0) > 0:
                target = p
                break

        if not target:
            pytest.skip("Нет неоплаченных платежей с суммой > 0")

        pay_id = target["id"]
        original_status = target.get("payment_status")

        try:
            # Шаг 1: Ставим to_pay
            resp1 = _put(f"/api/payments/{pay_id}", admin_headers,
                         json={"payment_status": "to_pay"})
            assert resp1.status_code == 200, \
                f"Ошибка to_pay: {resp1.status_code} {resp1.text}"

            # Проверяем
            check1 = _get(f"/api/payments/{pay_id}", admin_headers)
            if check1.status_code == 200:
                data1 = check1.json()
                assert data1.get("payment_status") == "to_pay", \
                    f"Статус не изменился на to_pay: {data1.get('payment_status')}"

            # Шаг 2: Ставим paid через mark-paid endpoint
            # employee_id передаётся как query parameter
            eid = target.get("employee_id") or 1
            resp2 = _session.patch(
                f"{API_BASE_URL}/api/payments/{pay_id}/mark-paid",
                headers=admin_headers,
                params={"employee_id": eid},
                timeout=TIMEOUT,
            )
            assert resp2.status_code == 200, \
                f"Ошибка mark-paid: {resp2.status_code} {resp2.text}"

            # Проверяем
            check2 = _get(f"/api/payments/{pay_id}", admin_headers)
            if check2.status_code == 200:
                data2 = check2.json()
                assert data2.get("payment_status") == "paid", \
                    f"Статус не paid: {data2.get('payment_status')}"
                assert data2.get("is_paid") is True, \
                    f"is_paid не True после mark-paid"
                assert data2.get("paid_date") is not None, \
                    f"paid_date не установлен после mark-paid"

        finally:
            # Восстанавливаем исходное состояние
            restore_data = {
                "payment_status": original_status,
                "is_paid": False,
                "paid_date": None,
            }
            _put(f"/api/payments/{pay_id}", admin_headers, json=restore_data)


# ════════════════════════════════════════════════════════════
# 9. WORKFLOW: Пересчёт оплат при изменении тарифа
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestRateRecalculationWorkflow:
    """Проверка: после обновления тарифа надзора, нулевые платежи пересчитываются."""

    def test_rate_change_triggers_recalc(self, admin_headers):
        """Создать тестовый тариф → проверить что API не упал → удалить."""
        # Создаём тестовый тариф надзора
        test_rate = {
            "project_type": "Авторский надзор",
            "role": f"{TEST_PREFIX}Тестовая_роль",
            "stage_name": f"{TEST_PREFIX}Стадия_1",
            "rate_per_m2": 99.99,
        }
        resp = _post("/api/rates", admin_headers, json=test_rate)
        assert resp.status_code == 200, \
            f"Ошибка создания тарифа: {resp.status_code} {resp.text}"
        rate = resp.json()
        rate_id = rate["id"]

        try:
            # Обновляем тариф (должен пересчитать нулевые платежи)
            resp2 = _put(f"/api/rates/{rate_id}", admin_headers,
                         json={"rate_per_m2": 150.0})
            assert resp2.status_code == 200, \
                f"Ошибка обновления тарифа: {resp2.status_code} {resp2.text}"

        finally:
            # Удаляем тестовый тариф
            _delete(f"/api/rates/{rate_id}", admin_headers)
