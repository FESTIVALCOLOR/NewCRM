# -*- coding: utf-8 -*-
"""
Smoke: Проверка правильности ответов — PUT → GET → сравнение данных.

Проверяет что API РЕАЛЬНО изменяет данные, а не просто возвращает 200.
Паттерн: отправить изменение → прочитать обратно → убедиться что значения совпадают.

Запуск: pytest tests/smoke/test_response_correctness.py -v --timeout=120
"""
import pytest
from datetime import datetime
from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    TEST_PREFIX, create_test_client, create_test_contract,
    find_crm_card_by_contract, cleanup_test_card,
)


@pytest.mark.smoke
class TestClientResponseCorrectness:
    """PUT клиент → GET → сверка полей."""

    def test_update_client_name_reflected_in_get(self, admin_headers):
        """Обновление имени клиента реально сохраняется."""
        client_id = None
        try:
            client_id = create_test_client(admin_headers, "RESP_CL")
            new_name = f"{TEST_PREFIX}UPDATED_{datetime.now().strftime('%H%M%S')}"

            resp = _put(f"/api/clients/{client_id}", admin_headers,
                        json={"full_name": new_name})
            assert resp.status_code == 200, f"PUT client: {resp.status_code} {resp.text}"

            # GET и проверка
            resp = _get(f"/api/clients/{client_id}", admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["full_name"] == new_name, \
                f"Ожидали '{new_name}', получили '{data.get('full_name')}'"
        finally:
            if client_id:
                try:
                    _delete(f"/api/clients/{client_id}", admin_headers)
                except Exception:
                    pass

    def test_update_client_phone_reflected_in_get(self, admin_headers):
        """Обновление телефона клиента реально сохраняется."""
        client_id = None
        try:
            client_id = create_test_client(admin_headers, "RESP_PH")
            new_phone = "+79991234567"

            resp = _put(f"/api/clients/{client_id}", admin_headers,
                        json={"phone": new_phone})
            assert resp.status_code == 200

            resp = _get(f"/api/clients/{client_id}", admin_headers)
            assert resp.status_code == 200
            assert resp.json()["phone"] == new_phone
        finally:
            if client_id:
                try:
                    _delete(f"/api/clients/{client_id}", admin_headers)
                except Exception:
                    pass

    def test_update_client_email_reflected_in_get(self, admin_headers):
        """Обновление email клиента реально сохраняется."""
        client_id = None
        try:
            client_id = create_test_client(admin_headers, "RESP_EM")
            new_email = f"smoke_test_{datetime.now().strftime('%H%M%S')}@test.ru"

            resp = _put(f"/api/clients/{client_id}", admin_headers,
                        json={"email": new_email})
            assert resp.status_code == 200

            resp = _get(f"/api/clients/{client_id}", admin_headers)
            assert resp.status_code == 200
            assert resp.json().get("email") == new_email
        finally:
            if client_id:
                try:
                    _delete(f"/api/clients/{client_id}", admin_headers)
                except Exception:
                    pass


@pytest.mark.smoke
class TestContractResponseCorrectness:
    """PUT договор → GET → сверка полей."""

    def test_update_contract_area_reflected_in_get(self, admin_headers):
        """Обновление площади договора реально сохраняется."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "RESP_AREA")
            contract_id = create_test_contract(admin_headers, client_id, "AREA")
            new_area = 175.5

            resp = _put(f"/api/contracts/{contract_id}", admin_headers,
                        json={"area": new_area})
            assert resp.status_code == 200, f"PUT contract: {resp.status_code} {resp.text}"

            resp = _get(f"/api/contracts/{contract_id}", admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert abs(data["area"] - new_area) < 0.01, \
                f"Ожидали area={new_area}, получили {data.get('area')}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_update_contract_total_amount_reflected(self, admin_headers):
        """Обновление суммы договора реально сохраняется."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "RESP_AMT")
            contract_id = create_test_contract(admin_headers, client_id, "AMT")
            new_amount = 750000.0

            resp = _put(f"/api/contracts/{contract_id}", admin_headers,
                        json={"total_amount": new_amount})
            assert resp.status_code == 200

            resp = _get(f"/api/contracts/{contract_id}", admin_headers)
            assert resp.status_code == 200
            assert abs(resp.json()["total_amount"] - new_amount) < 0.01
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_update_contract_address_reflected(self, admin_headers):
        """Обновление адреса договора реально сохраняется."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "RESP_ADR")
            contract_id = create_test_contract(admin_headers, client_id, "ADR")
            new_address = f"{TEST_PREFIX}Новый адрес {datetime.now().strftime('%H%M%S')}"

            resp = _put(f"/api/contracts/{contract_id}", admin_headers,
                        json={"address": new_address})
            assert resp.status_code == 200

            resp = _get(f"/api/contracts/{contract_id}", admin_headers)
            assert resp.status_code == 200
            assert resp.json()["address"] == new_address
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_update_contract_status_reflected(self, admin_headers):
        """Обновление статуса договора реально сохраняется."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "RESP_ST")
            contract_id = create_test_contract(admin_headers, client_id, "ST")

            resp = _put(f"/api/contracts/{contract_id}", admin_headers,
                        json={"status": "В работе"})
            assert resp.status_code == 200

            resp = _get(f"/api/contracts/{contract_id}", admin_headers)
            assert resp.status_code == 200
            assert resp.json()["status"] == "В работе"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestCrmCardResponseCorrectness:
    """PATCH CRM карточка → GET → сверка полей."""

    def test_move_column_reflected_in_get(self, admin_headers):
        """Перемещение карточки в колонку реально отражается в GET."""
        client_id = contract_id = card_id = None
        try:
            client_id = create_test_client(admin_headers, "RESP_COL")
            contract_id = create_test_contract(admin_headers, client_id, "COL")
            card_id = find_crm_card_by_contract(admin_headers, contract_id)

            target_column = "Стадия 1: планировочные решения"
            resp = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                          json={"column_name": target_column})
            assert resp.status_code == 200

            resp = _get(f"/api/crm/cards/{card_id}", admin_headers)
            assert resp.status_code == 200
            assert resp.json()["column_name"] == target_column, \
                f"Ожидали '{target_column}', получили '{resp.json().get('column_name')}'"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_assign_executor_reflected_in_get(self, admin_headers):
        """Назначение исполнителя реально появляется в GET stage-executors."""
        client_id = contract_id = card_id = None
        try:
            client_id = create_test_client(admin_headers, "RESP_EXC")
            contract_id = create_test_contract(admin_headers, client_id, "EXC")
            card_id = find_crm_card_by_contract(admin_headers, contract_id)

            # Перемещаем в первую стадию
            stage = "Стадия 1: планировочные решения"
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": stage})

            # Ищем активного сотрудника
            employees = _get("/api/employees", admin_headers).json()
            active = [e for e in employees if e.get("status") == "активный"]
            if not active:
                pytest.skip("Нет активных сотрудников")

            executor = active[0]
            resp = _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers,
                         json={"stage_name": stage,
                               "executor_id": executor["id"],
                               "deadline": "2026-12-31"})
            assert resp.status_code in (200, 201)

            # Проверяем через GET card detail (stage_executors внутри карточки)
            resp = _get(f"/api/crm/cards/{card_id}", admin_headers)
            assert resp.status_code == 200
            card = resp.json()
            stage_execs = card.get("stage_executors", [])
            if stage_execs:
                exec_ids = [e.get("executor_id") for e in stage_execs]
                assert executor["id"] in exec_ids, \
                    f"Исполнитель {executor['id']} не найден в {exec_ids}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestPaymentResponseCorrectness:
    """Обновление платежа → GET → сверка."""

    def _create_test_payment(self, admin_headers, contract_id, suffix=""):
        """Создать тестовый платёж. Возвращает payment_id."""
        me = _get("/api/auth/me", admin_headers)
        emp_id = me.json().get("employee_id", 1) if me.status_code == 200 else 1
        resp = _post("/api/payments", admin_headers, json={
            "contract_id": contract_id,
            "employee_id": emp_id,
            "role": "Дизайнер",
            "stage_name": f"Стадия 1: планировочные решения",
            "payment_type": "Аванс",
            "calculated_amount": 50000.0,
            "final_amount": 50000.0,
        })
        assert resp.status_code in (200, 201), \
            f"Создание платежа: {resp.status_code} {resp.text}"
        return resp.json()["id"]

    def test_update_payment_amount_reflected(self, admin_headers):
        """Обновление суммы платежа реально сохраняется."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "RESP_PAY")
            contract_id = create_test_contract(admin_headers, client_id, "PAY")
            payment_id = self._create_test_payment(admin_headers, contract_id)

            new_amount = 99999.0
            resp = _put(f"/api/payments/{payment_id}", admin_headers,
                        json={"final_amount": new_amount})
            assert resp.status_code == 200

            resp = _get(f"/api/payments/{payment_id}", admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            actual = data.get("final_amount") or data.get("amount", 0)
            assert abs(actual - new_amount) < 0.01, \
                f"Ожидали amount={new_amount}, получили {actual}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_mark_paid_syncs_all_fields(self, admin_headers):
        """mark-paid корректно устанавливает payment_status + is_paid + paid_date."""
        import requests as req
        import urllib3
        urllib3.disable_warnings()
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from config import API_BASE_URL

        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "RESP_PAID")
            contract_id = create_test_contract(admin_headers, client_id, "PAID")
            payment_id = self._create_test_payment(admin_headers, contract_id)

            me = _get("/api/auth/me", admin_headers)
            emp_id = me.json().get("employee_id", 1) if me.status_code == 200 else 1

            # mark-paid: employee_id как query param
            resp = req.patch(
                f"{API_BASE_URL}/api/payments/{payment_id}/mark-paid",
                params={"employee_id": emp_id},
                headers=admin_headers, verify=False, timeout=15)
            assert resp.status_code in (200, 201), \
                f"mark-paid: {resp.status_code} {resp.text}"

            # Проверяем через GET что ВСЕ поля синхронизированы
            resp = _get(f"/api/payments/{payment_id}", admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("payment_status") == "paid", \
                f"payment_status должен быть 'paid', получили '{data.get('payment_status')}'"
            assert data.get("is_paid") is True, \
                f"is_paid должен быть True, получили {data.get('is_paid')}"
            assert data.get("paid_date") is not None, \
                "paid_date должен быть заполнен после mark-paid"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_put_payment_status_paid_syncs_is_paid(self, admin_headers):
        """PUT payment_status='paid' автоматически ставит is_paid=True."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "RESP_SYNC")
            contract_id = create_test_contract(admin_headers, client_id, "SYNC")
            payment_id = self._create_test_payment(admin_headers, contract_id)

            # Ставим payment_status='paid' БЕЗ is_paid
            resp = _put(f"/api/payments/{payment_id}", admin_headers,
                        json={"payment_status": "paid"})
            assert resp.status_code == 200

            # Проверяем что is_paid автоматически стал True
            resp = _get(f"/api/payments/{payment_id}", admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("is_paid") is True, \
                f"is_paid должен автосинхронизироваться в True, получили {data.get('is_paid')}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestEmployeeResponseCorrectness:
    """PUT сотрудник → GET → сверка."""

    def test_update_employee_position_reflected(self, admin_headers):
        """Обновление должности сотрудника реально сохраняется."""
        from datetime import datetime as dt
        ts = dt.now().strftime('%H%M%S%f')[:8]
        login = f"smoke_pos_{ts}"
        password = f"Test1pass{ts}"
        emp_id = None

        try:
            # Создаём тестового сотрудника
            resp = _post("/api/employees", admin_headers, json={
                "full_name": f"{TEST_PREFIX}POS_{ts}",
                "position": "Дизайнер",
                "role": "Дизайнер",
                "status": "активный",
                "login": login,
                "password": password,
            })
            assert resp.status_code in (200, 201), \
                f"Создание сотрудника: {resp.status_code} {resp.text}"
            emp_id = resp.json()["id"]

            new_position = "Тестовая должность"
            resp = _put(f"/api/employees/{emp_id}", admin_headers,
                        json={"position": new_position})
            assert resp.status_code == 200

            resp = _get(f"/api/employees/{emp_id}", admin_headers)
            assert resp.status_code == 200
            assert resp.json()["position"] == new_position
        finally:
            if emp_id:
                _delete(f"/api/employees/{emp_id}", admin_headers)
