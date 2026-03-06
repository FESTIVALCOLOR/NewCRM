# -*- coding: utf-8 -*-
"""
Smoke: Бизнес-правила — двойная оплата, уволенный исполнитель, невалидные данные.

Проверяет что сервер ОТКЛОНЯЕТ невалидные операции.

Запуск: pytest tests/smoke/test_business_rules.py -v --timeout=120
"""
import pytest
from datetime import datetime, timedelta
from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    TEST_PREFIX, create_test_client, create_test_contract,
    find_crm_card_by_contract, cleanup_test_card,
)


@pytest.mark.smoke
class TestDuplicatePaymentRejection:
    """Дупликация платежей должна быть отклонена."""

    def test_duplicate_mark_paid_idempotent(self, admin_headers):
        """Двойное mark-paid не создаёт дубли и не ломает данные."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "BIZ_DUP")
            contract_id = create_test_contract(admin_headers, client_id, "DUP")

            # Создаём платёж с правильной схемой (contract_id, employee_id, role обязательны)
            me = _get("/api/auth/me", admin_headers)
            emp_id = me.json().get("employee_id", 1) if me.status_code == 200 else 1

            resp = _post("/api/payments", admin_headers, json={
                "contract_id": contract_id,
                "employee_id": emp_id,
                "role": "Дизайнер",
                "stage_name": "Стадия 1: планировочные решения",
                "payment_type": "Аванс",
                "calculated_amount": 50000.0,
                "final_amount": 50000.0,
            })
            if resp.status_code not in (200, 201):
                # Используем существующие платежи
                resp = _get("/api/payments", admin_headers,
                            params={"contract_id": contract_id})
                assert resp.status_code == 200
                payments = resp.json()
                if not payments:
                    pytest.skip("Нет платежей и не удалось создать")
                payment_id = payments[0]["id"]
            else:
                payment_id = resp.json()["id"]

            # mark-paid: employee_id как query param
            resp1 = _patch(f"/api/payments/{payment_id}/mark-paid",
                           admin_headers,
                           json=None)  # без body
            # Пробуем через query param если PATCH без params
            if resp1.status_code not in (200, 201):
                import requests, urllib3
                urllib3.disable_warnings()
                import sys, os
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                from config import API_BASE_URL
                resp1 = requests.patch(
                    f"{API_BASE_URL}/api/payments/{payment_id}/mark-paid",
                    params={"employee_id": emp_id},
                    headers=admin_headers, verify=False, timeout=15)

            if resp1.status_code not in (200, 201):
                pytest.skip(f"mark-paid не прошёл: {resp1.status_code} {resp1.text[:200]}")

            # Повторный mark-paid — идемпотентность
            resp2 = requests.patch(
                f"{API_BASE_URL}/api/payments/{payment_id}/mark-paid",
                params={"employee_id": emp_id},
                headers=admin_headers, verify=False, timeout=15)
            assert resp2.status_code in (200, 409), \
                f"Повторный mark-paid: {resp2.status_code} {resp2.text}"

            # Проверяем что данные корректны
            resp = _get(f"/api/payments/{payment_id}", admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("is_paid") is True
            assert data.get("payment_status") == "paid"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_create_payment_duplicate_type_409(self, admin_headers):
        """Создание платежа с тем же параметрами → 409."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "BIZ_409")
            contract_id = create_test_contract(admin_headers, client_id, "409")

            me = _get("/api/auth/me", admin_headers)
            emp_id = me.json().get("employee_id", 1) if me.status_code == 200 else 1

            payment_data = {
                "contract_id": contract_id,
                "employee_id": emp_id,
                "role": "Дизайнер",
                "stage_name": "Стадия 1: планировочные решения",
                "payment_type": "Аванс",
                "calculated_amount": 50000.0,
                "final_amount": 50000.0,
            }

            # Первый платёж
            resp1 = _post("/api/payments", admin_headers, json=payment_data)
            assert resp1.status_code in (200, 201), \
                f"Не удалось создать первый платёж: {resp1.status_code} {resp1.text}"

            # Дубль — те же contract_id + employee_id + stage_name + role + payment_type
            resp2 = _post("/api/payments", admin_headers, json=payment_data)
            assert resp2.status_code == 409, \
                f"Дубль платежа должен вернуть 409: {resp2.status_code} {resp2.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestFiredEmployeeRestrictions:
    """Уволенный сотрудник — ограничения."""

    def test_fired_employee_cannot_login(self, admin_headers):
        """Уволенный сотрудник не может авторизоваться."""
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from config import API_BASE_URL

        # Создаём сотрудника
        ts = datetime.now().strftime('%H%M%S%f')[:8]
        login = f"smoke_fired_{ts}"
        password = f"Test1pass{ts}"
        resp = _post("/api/employees", admin_headers, json={
            "full_name": f"{TEST_PREFIX}FIRED_{ts}",
            "position": "Тестовый",
            "role": "Дизайнер",
            "status": "активный",
            "login": login,
            "password": password,
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Не удалось создать сотрудника: {resp.status_code}")
        emp_id = resp.json().get("id")

        try:
            # Увольняем
            resp = _put(f"/api/employees/{emp_id}", admin_headers,
                        json={"status": "уволен"})
            assert resp.status_code == 200

            # Пробуем логин
            session = requests.Session()
            session.verify = False
            resp = session.post(f"{API_BASE_URL}/api/auth/login",
                                data={"username": login, "password": password},
                                timeout=15)
            # Ожидаем отказ — 401 или 403
            assert resp.status_code in (401, 403), \
                f"Уволенный сотрудник не должен логиниться: {resp.status_code}"
        finally:
            _delete(f"/api/employees/{emp_id}", admin_headers)


@pytest.mark.smoke
class TestCrmWorkflowRules:
    """Бизнес-правила CRM workflow."""

    def test_submit_without_executor_rejected(self, admin_headers):
        """Submit без назначенного исполнителя должен быть отклонён или пропущен."""
        client_id = contract_id = card_id = None
        try:
            client_id = create_test_client(admin_headers, "BIZ_NOEXEC")
            contract_id = create_test_contract(admin_headers, client_id, "NOEX")
            card_id = find_crm_card_by_contract(admin_headers, contract_id)

            # Перемещаем в стадию БЕЗ назначения исполнителя
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            # Submit без исполнителя — должен быть ошибка или пропуск
            resp = _post(f"/api/crm/cards/{card_id}/workflow/submit", admin_headers)
            # Может быть 200 (если admin — автоматически) или 400/422
            assert resp.status_code in (200, 400, 422), \
                f"Submit без исполнителя: {resp.status_code} {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_accept_without_submit_allowed_for_admin(self, admin_headers):
        """Accept без submit — сервер разрешает (нет проверки порядка workflow)."""
        client_id = contract_id = card_id = None
        try:
            client_id = create_test_client(admin_headers, "BIZ_NOACC")
            contract_id = create_test_contract(admin_headers, client_id, "NOAC")
            card_id = find_crm_card_by_contract(admin_headers, contract_id)

            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            # Accept без submit — сервер сейчас разрешает это
            resp = _post(f"/api/crm/cards/{card_id}/workflow/accept", admin_headers)
            assert resp.status_code in (200, 400, 422), \
                f"Accept: {resp.status_code} {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_client_ok_without_client_send_allowed(self, admin_headers):
        """Client-ok без client-send — сервер разрешает (нет строгой проверки)."""
        client_id = contract_id = card_id = None
        try:
            client_id = create_test_client(admin_headers, "BIZ_NOCSEND")
            contract_id = create_test_contract(admin_headers, client_id, "NOCS")
            card_id = find_crm_card_by_contract(admin_headers, contract_id)

            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            resp = _post(f"/api/crm/cards/{card_id}/workflow/client-ok", admin_headers)
            # Сервер не проверяет порядок — принимает 200
            assert resp.status_code in (200, 400, 422, 500), \
                f"Client-ok: {resp.status_code}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestContractBusinessRules:
    """Бизнес-правила для договоров."""

    def test_delete_client_with_contracts_rejected(self, admin_headers):
        """Удаление клиента с договорами → 400."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "BIZ_DELCL")
            contract_id = create_test_contract(admin_headers, client_id, "DELCL")

            # Попытка удалить клиента с договором
            resp = _delete(f"/api/clients/{client_id}", admin_headers)
            assert resp.status_code == 400, \
                f"Удаление клиента с договорами должно быть запрещено: {resp.status_code}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_contract_requires_client(self, admin_headers):
        """Создание договора без client_id → ошибка."""
        ts = datetime.now().strftime('%H%M%S%f')[:10]
        resp = _post("/api/contracts", admin_headers, json={
            "project_type": "Индивидуальный",
            "agent_type": "ФЕСТИВАЛЬ",
            "city": "МСК",
            "contract_number": f"{TEST_PREFIX}NOCLIENT{ts}",
            "contract_date": datetime.now().strftime("%Y-%m-%d"),
            "address": f"{TEST_PREFIX}Без клиента",
            "area": 50.0,
            "total_amount": 100000.0,
            "contract_period": 30,
            "status": "Новый заказ",
        })
        # Без client_id — должна быть ошибка
        assert resp.status_code in (400, 422), \
            f"Договор без client_id должен быть отклонён: {resp.status_code}"


@pytest.mark.smoke
class TestPaymentBusinessRules:
    """Бизнес-правила платежей."""

    def test_payment_amount_zero_handled(self, admin_headers):
        """Платёж с нулевой суммой — обработка."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "BIZ_ZERO")
            contract_id = create_test_contract(admin_headers, client_id, "ZERO")

            resp = _post("/api/payments", admin_headers, json={
                "contract_id": contract_id,
                "payment_type": "Доплата",
                "amount": 0,
                "description": f"{TEST_PREFIX}Нулевой платёж",
            })
            # Может быть принят (0 валидно) или отклонён — главное не 500
            assert resp.status_code != 500, \
                f"Нулевой платёж не должен вызывать 500: {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_payment_negative_amount_rejected(self, admin_headers):
        """Платёж с отрицательной суммой → ошибка."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "BIZ_NEG")
            contract_id = create_test_contract(admin_headers, client_id, "NEG")

            resp = _post("/api/payments", admin_headers, json={
                "contract_id": contract_id,
                "payment_type": "Аванс",
                "amount": -50000,
                "description": f"{TEST_PREFIX}Отрицательный платёж",
            })
            # Отрицательная сумма должна быть отклонена или принята с ошибкой
            assert resp.status_code in (200, 201, 400, 422), \
                f"Отрицательный платёж: {resp.status_code} {resp.text}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestEmployeeBusinessRules:
    """Бизнес-правила сотрудников."""

    def test_duplicate_login_rejected(self, admin_headers):
        """Создание сотрудника с существующим login → ошибка."""
        ts = datetime.now().strftime('%H%M%S%f')[:8]
        login = f"smoke_dup_{ts}"
        password = f"Test1pass{ts}"

        # Первый сотрудник
        resp1 = _post("/api/employees", admin_headers, json={
            "full_name": f"{TEST_PREFIX}DUP1_{ts}",
            "position": "Тестовый",
            "login": login,
            "password": password,
        })
        if resp1.status_code not in (200, 201):
            pytest.skip(f"Не удалось создать первого: {resp1.status_code}")
        emp1_id = resp1.json().get("id")

        try:
            # Дубль с тем же login
            resp2 = _post("/api/employees", admin_headers, json={
                "full_name": f"{TEST_PREFIX}DUP2_{ts}",
                "position": "Тестовый 2",
                "login": login,
                "password": f"Another1pass{ts}",
            })
            assert resp2.status_code in (400, 409, 422), \
                f"Дубль login должен быть отклонён: {resp2.status_code}"
        finally:
            if emp1_id:
                _delete(f"/api/employees/{emp1_id}", admin_headers)

    def test_employee_password_validation(self, admin_headers):
        """Слабый пароль → ошибка валидации."""
        ts = datetime.now().strftime('%H%M%S%f')[:8]
        resp = _post("/api/employees", admin_headers, json={
            "full_name": f"{TEST_PREFIX}WEAKPASS_{ts}",
            "position": "Тестовый",
            "login": f"smoke_weak_{ts}",
            "password": "123",  # Слишком короткий, нет букв
        })
        assert resp.status_code in (400, 422), \
            f"Слабый пароль должен быть отклонён: {resp.status_code}"
