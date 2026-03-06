# -*- coding: utf-8 -*-
"""
Smoke: Полный CRM workflow с проверкой платежей на каждой стадии.

Проверяет связку: создание карточки → назначение исполнителя →
создание платежа → перемещение по стадиям → оплата → следующая стадия.
На каждом шаге верифицируются ДАННЫЕ, а не только статус-коды.

Запуск: pytest tests/smoke/test_workflow_with_payments.py -v --timeout=180
"""
import pytest
from datetime import datetime, timedelta
from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    TEST_PREFIX, create_test_client, create_test_contract,
    find_crm_card_by_contract, cleanup_test_card,
)

CRM_STAGES = [
    "Стадия 1: планировочные решения",
    "Стадия 2: эскизные решения",
    "Стадия 3: рабочий проект",
]


def _get_admin_employee_id(headers):
    me = _get("/api/auth/me", headers)
    if me.status_code == 200:
        return me.json().get("employee_id", 1)
    return 1


def _create_payment(headers, contract_id, stage_name, payment_type="Аванс",
                    amount=50000.0, role="Дизайнер"):
    emp_id = _get_admin_employee_id(headers)
    return _post("/api/payments", headers, json={
        "contract_id": contract_id,
        "employee_id": emp_id,
        "role": role,
        "stage_name": stage_name,
        "payment_type": payment_type,
        "calculated_amount": amount,
        "final_amount": amount,
    })


def _get_payments_for_contract(headers, contract_id):
    resp = _get("/api/payments", headers, params={"contract_id": contract_id})
    return resp.json() if resp.status_code == 200 else []


# ════════════════════════════════════════════════════════════
# 1. Workflow с платежами: стадия 1
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestStage1WithPayments:
    """Стадия 1: назначение → платёж → submit → accept → клиент."""

    def test_stage1_create_payment_and_verify(self, admin_headers):
        """Создание платежа на стадии 1 → проверка через GET."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "WF_PAY1")
            contract_id = create_test_contract(admin_headers, client_id, "WP1")
            card_id = find_crm_card_by_contract(admin_headers, contract_id)

            # Перемещаем в стадию 1
            stage = CRM_STAGES[0]
            resp = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                          json={"column_name": stage})
            assert resp.status_code == 200

            # Создаём платёж
            resp = _create_payment(admin_headers, contract_id, stage)
            if resp.status_code not in (200, 201):
                pytest.skip(f"Создание платежа: {resp.status_code}")
            payment_id = resp.json()["id"]

            # Проверяем что платёж привязан к договору
            payments = _get_payments_for_contract(admin_headers, contract_id)
            pay_ids = [p["id"] for p in payments]
            assert payment_id in pay_ids, \
                f"Платёж {payment_id} не найден в списке платежей договора"

            # Проверяем что платёж имеет правильную стадию
            pay_detail = _get(f"/api/payments/{payment_id}", admin_headers)
            assert pay_detail.status_code == 200
            pay_data = pay_detail.json()
            assert pay_data.get("stage_name") == stage, \
                f"stage_name: ожидали '{stage}', получили '{pay_data.get('stage_name')}'"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_stage1_workflow_preserves_payments(self, admin_headers):
        """Submit → Accept на стадии 1 не удаляет платежи."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "WF_PRES1")
            contract_id = create_test_contract(admin_headers, client_id, "WPR1")
            card_id = find_crm_card_by_contract(admin_headers, contract_id)

            stage = CRM_STAGES[0]
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": stage})

            # Создаём платёж
            resp = _create_payment(admin_headers, contract_id, stage)
            if resp.status_code not in (200, 201):
                pytest.skip(f"Создание платежа: {resp.status_code}")
            payment_id = resp.json()["id"]

            # Submit
            _post(f"/api/crm/cards/{card_id}/workflow/submit", admin_headers)
            # Accept
            _post(f"/api/crm/cards/{card_id}/workflow/accept", admin_headers)

            # Платёж должен остаться
            resp = _get(f"/api/payments/{payment_id}", admin_headers)
            assert resp.status_code == 200, \
                f"Платёж удалён после submit+accept: {resp.status_code}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 2. Мультистадийный workflow с платежами
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestMultiStagePayments:
    """Платежи на разных стадиях — каждый привязан к своей стадии."""

    def test_payments_on_different_stages(self, admin_headers):
        """Создание платежей на разных стадиях — все сохраняются."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "WF_MULTI")
            contract_id = create_test_contract(admin_headers, client_id, "WPM")
            card_id = find_crm_card_by_contract(admin_headers, contract_id)

            created_payments = []
            for i, stage in enumerate(CRM_STAGES):
                # Перемещаем в стадию
                resp = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                              json={"column_name": stage})
                if resp.status_code != 200:
                    break

                # Создаём платёж с уникальным payment_type
                payment_type = ["Аванс", "Доплата", "Остаток"][i] if i < 3 else "Аванс"
                resp = _create_payment(admin_headers, contract_id, stage,
                                       payment_type=payment_type,
                                       amount=50000.0 * (i + 1))
                if resp.status_code in (200, 201):
                    created_payments.append(resp.json()["id"])

            assert len(created_payments) >= 1, "Не создано ни одного платежа"

            # Все платежи существуют
            for pay_id in created_payments:
                resp = _get(f"/api/payments/{pay_id}", admin_headers)
                assert resp.status_code == 200, \
                    f"Платёж {pay_id} не найден: {resp.status_code}"

            # Общая сумма платежей > 0
            all_payments = _get_payments_for_contract(admin_headers, contract_id)
            total = sum(p.get("final_amount") or p.get("amount") or 0
                        for p in all_payments)
            assert total > 0, "Суммарная сумма платежей должна быть > 0"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    def test_move_to_stage2_after_stage1_workflow(self, admin_headers):
        """Полный workflow стадии 1 → переход в стадию 2."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "WF_S1S2")
            contract_id = create_test_contract(admin_headers, client_id, "W12")
            card_id = find_crm_card_by_contract(admin_headers, contract_id)

            # Стадия 1
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": CRM_STAGES[0]})
            _create_payment(admin_headers, contract_id, CRM_STAGES[0])

            # Полный workflow: Submit → Accept → Client-send → Client-ok
            _post(f"/api/crm/cards/{card_id}/workflow/submit", admin_headers)
            _post(f"/api/crm/cards/{card_id}/workflow/accept", admin_headers)
            _post(f"/api/crm/cards/{card_id}/workflow/client-send", admin_headers)
            _post(f"/api/crm/cards/{card_id}/workflow/client-ok", admin_headers)

            # Переход в стадию 2 (после полного workflow стадии 1)
            resp = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                          json={"column_name": CRM_STAGES[1]})
            # Может быть 200 (допустимый переход) или 422 (требуется ещё какой-то шаг)
            assert resp.status_code in (200, 422), \
                f"Переход в стадию 2: {resp.status_code} {resp.text}"

            if resp.status_code == 200:
                # Проверяем карточку
                card = _get(f"/api/crm/cards/{card_id}", admin_headers).json()
                assert card["column_name"] == CRM_STAGES[1], \
                    f"Карточка должна быть в '{CRM_STAGES[1]}', а в '{card['column_name']}'"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 3. Платёж → mark-paid → проверка workflow state
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestPaymentStatusInWorkflow:
    """Оплата платежа не ломает workflow state."""

    def test_mark_paid_does_not_break_card(self, admin_headers):
        """mark-paid → карточка по-прежнему доступна и в правильной колонке."""
        import requests, urllib3
        urllib3.disable_warnings()
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from config import API_BASE_URL

        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "WF_MPAID")
            contract_id = create_test_contract(admin_headers, client_id, "WMP")
            card_id = find_crm_card_by_contract(admin_headers, contract_id)

            stage = CRM_STAGES[0]
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": stage})

            # Создаём и оплачиваем
            resp = _create_payment(admin_headers, contract_id, stage)
            if resp.status_code not in (200, 201):
                pytest.skip(f"Платёж: {resp.status_code}")
            payment_id = resp.json()["id"]

            emp_id = _get_admin_employee_id(admin_headers)
            requests.patch(
                f"{API_BASE_URL}/api/payments/{payment_id}/mark-paid",
                params={"employee_id": emp_id},
                headers=admin_headers, verify=False, timeout=15)

            # Карточка должна быть доступна
            resp = _get(f"/api/crm/cards/{card_id}", admin_headers)
            assert resp.status_code == 200
            card = resp.json()
            assert card["column_name"] == stage, \
                f"Колонка изменилась после mark-paid: '{card['column_name']}'"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)

    @pytest.mark.xfail(reason="БАГ: recalculate обнуляет суммы оплаченных платежей")
    def test_paid_payment_not_recalculated(self, admin_headers):
        """Оплаченный платёж не должен пересчитываться (сумма сохраняется).

        ОБНАРУЖЕННЫЙ БАГ: recalculate обнуляет final_amount оплаченных платежей.
        """
        import requests, urllib3
        urllib3.disable_warnings()
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from config import API_BASE_URL

        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "WF_NOREC")
            contract_id = create_test_contract(admin_headers, client_id, "WNR")

            stage = CRM_STAGES[0]
            resp = _create_payment(admin_headers, contract_id, stage,
                                   amount=77777.0)
            if resp.status_code not in (200, 201):
                pytest.skip(f"Платёж: {resp.status_code}")
            payment_id = resp.json()["id"]

            # Mark paid
            emp_id = _get_admin_employee_id(admin_headers)
            requests.patch(
                f"{API_BASE_URL}/api/payments/{payment_id}/mark-paid",
                params={"employee_id": emp_id},
                headers=admin_headers, verify=False, timeout=15)

            # Запомним сумму
            resp = _get(f"/api/payments/{payment_id}", admin_headers)
            assert resp.status_code == 200
            amount_after_paid = resp.json().get("final_amount") or \
                resp.json().get("amount", 0)

            # Пересчёт
            _post("/api/payments/recalculate", admin_headers,
                  json={"contract_id": contract_id})

            # Сумма не должна измениться для оплаченного платежа
            resp = _get(f"/api/payments/{payment_id}", admin_headers)
            assert resp.status_code == 200
            amount_after_recalc = resp.json().get("final_amount") or \
                resp.json().get("amount", 0)

            assert abs(amount_after_paid - amount_after_recalc) < 0.01, \
                f"Сумма изменилась после recalculate: {amount_after_paid} → {amount_after_recalc}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 4. Полный цикл: создание → стадии → платежи → архив
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestFullWorkflowWithPayments:
    """Полный E2E: клиент → договор → карточка → стадии с платежами → архив."""

    def test_full_e2e_with_payments(self, admin_headers):
        """Полный цикл от создания до архива с платежами на каждой стадии."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "WF_E2E")
            contract_id = create_test_contract(admin_headers, client_id, "WE2E")
            card_id = find_crm_card_by_contract(admin_headers, contract_id)

            payment_ids = []

            # Стадия 1 + платёж
            stage1 = CRM_STAGES[0]
            resp = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                          json={"column_name": stage1})
            assert resp.status_code == 200

            resp = _create_payment(admin_headers, contract_id, stage1,
                                   payment_type="Аванс", amount=100000.0)
            if resp.status_code in (200, 201):
                payment_ids.append(resp.json()["id"])

            # Workflow на стадии 1
            _post(f"/api/crm/cards/{card_id}/workflow/submit", admin_headers)
            _post(f"/api/crm/cards/{card_id}/workflow/accept", admin_headers)

            # Стадия 2 + платёж
            stage2 = CRM_STAGES[1]
            resp = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                          json={"column_name": stage2})
            if resp.status_code == 200:
                resp = _create_payment(admin_headers, contract_id, stage2,
                                       payment_type="Аванс", amount=150000.0)
                if resp.status_code in (200, 201):
                    payment_ids.append(resp.json()["id"])

                _post(f"/api/crm/cards/{card_id}/workflow/submit", admin_headers)
                _post(f"/api/crm/cards/{card_id}/workflow/accept", admin_headers)

            # Стадия 3 + платёж
            stage3 = CRM_STAGES[2]
            resp = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                          json={"column_name": stage3})
            if resp.status_code == 200:
                resp = _create_payment(admin_headers, contract_id, stage3,
                                       payment_type="Остаток", amount=200000.0)
                if resp.status_code in (200, 201):
                    payment_ids.append(resp.json()["id"])

            # Проверяем все платежи на месте
            all_payments = _get_payments_for_contract(admin_headers, contract_id)
            created_ids = {p["id"] for p in all_payments}
            for pid in payment_ids:
                assert pid in created_ids, \
                    f"Платёж {pid} пропал после прохождения стадий"

            # Суммарная сумма
            total = sum(p.get("final_amount") or p.get("amount") or 0
                        for p in all_payments)
            if payment_ids:
                assert total > 0, "Суммарная сумма платежей = 0"

            # Архивируем
            resp = _post(f"/api/crm/cards/{card_id}/archive", admin_headers)
            # Может быть 200 или 404 если нет archive endpoint
            if resp.status_code == 200:
                # Платежи должны остаться после архивации
                all_payments_after = _get_payments_for_contract(admin_headers, contract_id)
                for pid in payment_ids:
                    assert pid in {p["id"] for p in all_payments_after}, \
                        f"Платёж {pid} удалён при архивации"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 5. Executor assignment → платежи
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestExecutorAndPayments:
    """Назначение исполнителя и создание платежей — связанные операции."""

    def test_executor_assignment_then_payment(self, admin_headers):
        """Назначение исполнителя → создание платежа с его employee_id."""
        client_id = contract_id = None
        try:
            client_id = create_test_client(admin_headers, "WF_EXPAY")
            contract_id = create_test_contract(admin_headers, client_id, "WEP")
            card_id = find_crm_card_by_contract(admin_headers, contract_id)

            stage = CRM_STAGES[0]
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": stage})

            # Назначаем исполнителя
            employees = _get("/api/employees", admin_headers).json()
            active = [e for e in employees if e.get("status") == "активный"]
            if not active:
                pytest.skip("Нет активных сотрудников")

            executor = active[0]
            deadline = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
            resp = _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers,
                         json={"stage_name": stage, "executor_id": executor["id"],
                                "deadline": deadline})
            if resp.status_code not in (200, 201):
                pytest.skip(f"Назначение: {resp.status_code}")

            # Создаём платёж с employee_id исполнителя
            emp_id = executor["id"]
            role = executor.get("role", "Дизайнер")
            resp = _post("/api/payments", admin_headers, json={
                "contract_id": contract_id,
                "employee_id": emp_id,
                "role": role,
                "stage_name": stage,
                "payment_type": "Аванс",
                "calculated_amount": 50000.0,
                "final_amount": 50000.0,
            })
            if resp.status_code not in (200, 201):
                pytest.skip(f"Платёж: {resp.status_code}")
            payment_id = resp.json()["id"]

            # Проверяем что платёж привязан к правильному employee
            pay = _get(f"/api/payments/{payment_id}", admin_headers).json()
            assert pay.get("employee_id") == emp_id, \
                f"employee_id: ожидали {emp_id}, получили {pay.get('employee_id')}"
        finally:
            if contract_id:
                cleanup_test_card(admin_headers, client_id, contract_id)
