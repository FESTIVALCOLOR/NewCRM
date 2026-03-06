# -*- coding: utf-8 -*-
"""
Smoke Tests: Boundary Values — спецсимволы, крайние даты, пустые списки,
максимальные значения, Unicode.

Запуск: pytest tests/smoke/test_boundary_values.py -v --timeout=120
"""

import pytest
from datetime import datetime

from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    create_test_client, create_test_contract,
    create_test_card, cleanup_test_card, TEST_PREFIX,
)


# ════════════════════════════════════════════════════════════
# 1. Специальные символы
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSpecialCharacters:
    """P1: API корректно обрабатывает спецсимволы."""

    def test_client_name_cyrillic_long(self, admin_headers):
        """Создание клиента с длинным кириллическим именем."""
        long_name = f"{TEST_PREFIX}" + "А" * 200
        resp = _post("/api/clients", admin_headers, json={
            "client_type": "Физическое лицо",
            "full_name": long_name,
            "phone": "+79991111111",
        })
        if resp.status_code in (200, 201):
            cid = resp.json()["id"]
            check = _get(f"/api/clients/{cid}", admin_headers).json()
            # Имя сохранилось (может быть обрезано)
            assert len(check["full_name"]) > 0
            _delete(f"/api/clients/{cid}", admin_headers)
        else:
            assert resp.status_code == 422

    def test_contract_address_unicode(self, admin_headers):
        """Адрес с Unicode символами (кириллица, тире, кавычки)."""
        client_id = create_test_client(admin_headers, "UNICODE")
        try:
            ts = datetime.now().strftime('%H%M%S%f')[:10]
            resp = _post("/api/contracts", admin_headers, json={
                "client_id": client_id,
                "project_type": "Индивидуальный",
                "agent_type": "ФЕСТИВАЛЬ",
                "city": "МСК",
                "contract_number": f"{TEST_PREFIX}UNI{ts}",
                "contract_date": datetime.now().strftime("%Y-%m-%d"),
                "address": "г. Москва, ул. «Большая Пироговская» д.1/2, кв.3 — корп.А",
                "area": 100.0,
                "total_amount": 500000.0,
                "advance_payment": 250000.0,
                "additional_payment": 250000.0,
                "contract_period": 60,
                "status": "Новый заказ",
            })
            assert resp.status_code in (200, 201), \
                f"Unicode адрес: {resp.status_code} {resp.text}"
            if resp.status_code in (200, 201):
                cid = resp.json()["id"]
                check = _get(f"/api/contracts/{cid}", admin_headers).json()
                assert "Пироговская" in check["address"]
                _delete(f"/api/contracts/{cid}", admin_headers)
        finally:
            _delete(f"/api/clients/{client_id}", admin_headers)


# ════════════════════════════════════════════════════════════
# 2. Крайние даты
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestBoundaryDates:
    """P1: Граничные значения дат."""

    def test_contract_date_today(self, admin_headers):
        """Договор с датой = сегодня."""
        client_id = create_test_client(admin_headers, "DATE_TODAY")
        try:
            ts = datetime.now().strftime('%H%M%S%f')[:10]
            resp = _post("/api/contracts", admin_headers, json={
                "client_id": client_id,
                "project_type": "Индивидуальный",
                "agent_type": "ФЕСТИВАЛЬ",
                "city": "МСК",
                "contract_number": f"{TEST_PREFIX}DT{ts}",
                "contract_date": datetime.now().strftime("%Y-%m-%d"),
                "address": f"{TEST_PREFIX}Адрес сегодня",
                "area": 50.0,
                "total_amount": 250000.0,
                "advance_payment": 125000.0,
                "additional_payment": 125000.0,
                "contract_period": 30,
                "status": "Новый заказ",
            })
            assert resp.status_code in (200, 201)
            if resp.status_code in (200, 201):
                _delete(f"/api/contracts/{resp.json()['id']}", admin_headers)
        finally:
            _delete(f"/api/clients/{client_id}", admin_headers)

    def test_far_future_deadline(self, admin_headers):
        """Назначение дедлайна в далёком будущем (2099)."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "FUTURE_DL")
        try:
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "В ожидании"})
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})
            _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers, json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": 1,
            })

            resp = _patch(
                f"/api/crm/cards/{card_id}/stage-executor-deadline",
                admin_headers,
                json={
                    "stage_name": "Стадия 1: планировочные решения",
                    "employee_id": 1,
                    "deadline": "2099-12-31",
                },
            )
            # 404 — если назначение не найдено, 200/422 — штатные ответы
            assert resp.status_code in (200, 404, 422)
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 3. Пустые результаты
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestEmptyResults:
    """P1: API корректно обрабатывает пустые результаты."""

    def test_payments_empty_contract(self, admin_headers):
        """GET /payments/contract/{id} для нового договора → пустой список."""
        client_id = create_test_client(admin_headers, "EMPTY_PAY")
        contract_id = create_test_contract(admin_headers, client_id, "EMPTY_PAY")
        try:
            resp = _get(f"/api/payments/contract/{contract_id}", admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            # Для нового договора без исполнителей — список пуст или с авто-платежами
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_timeline_empty_contract(self, admin_headers):
        """GET /timeline/{id} для нового договора без init → 404 или пустой."""
        client_id = create_test_client(admin_headers, "EMPTY_TL")
        contract_id = create_test_contract(admin_headers, client_id, "EMPTY_TL")
        try:
            resp = _get(f"/api/timeline/{contract_id}", admin_headers)
            assert resp.status_code in (200, 404)
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_action_history_empty_entity(self, admin_headers):
        """GET /action-history/crm_card/999999 → пустой список."""
        resp = _get("/api/action-history/crm_card/999999", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 0, "История для несуществующей карточки не пуста"

    def test_files_empty_contract(self, admin_headers):
        """GET /files/contract/{id} для нового договора → пустой список."""
        client_id = create_test_client(admin_headers, "EMPTY_FILE")
        contract_id = create_test_contract(admin_headers, client_id, "EMPTY_FILE")
        try:
            resp = _get(f"/api/files/contract/{contract_id}", admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 4. Большие / крайние значения
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestExtremeValues:
    """P1: Крайние числовые значения."""

    def test_large_contract_amount(self, admin_headers):
        """Договор с очень большой суммой (999 999 999)."""
        client_id = create_test_client(admin_headers, "BIG_AMT")
        try:
            ts = datetime.now().strftime('%H%M%S%f')[:10]
            resp = _post("/api/contracts", admin_headers, json={
                "client_id": client_id,
                "project_type": "Индивидуальный",
                "agent_type": "ФЕСТИВАЛЬ",
                "city": "МСК",
                "contract_number": f"{TEST_PREFIX}BIG{ts}",
                "contract_date": datetime.now().strftime("%Y-%m-%d"),
                "address": f"{TEST_PREFIX}Адрес большой суммы",
                "area": 9999.0,
                "total_amount": 999999999.0,
                "advance_payment": 499999999.0,
                "additional_payment": 500000000.0,
                "contract_period": 365,
                "status": "Новый заказ",
            })
            assert resp.status_code in (200, 201, 422), \
                f"Большая сумма: {resp.status_code} {resp.text}"
            if resp.status_code in (200, 201):
                cid = resp.json()["id"]
                check = _get(f"/api/contracts/{cid}", admin_headers).json()
                assert check["total_amount"] == 999999999.0
                _delete(f"/api/contracts/{cid}", admin_headers)
        finally:
            _delete(f"/api/clients/{client_id}", admin_headers)

    def test_zero_area_contract(self, admin_headers):
        """Договор с нулевой площадью — должен быть допустим или 422."""
        client_id = create_test_client(admin_headers, "ZERO_AREA")
        try:
            ts = datetime.now().strftime('%H%M%S%f')[:10]
            resp = _post("/api/contracts", admin_headers, json={
                "client_id": client_id,
                "project_type": "Индивидуальный",
                "agent_type": "ФЕСТИВАЛЬ",
                "city": "МСК",
                "contract_number": f"{TEST_PREFIX}ZA{ts}",
                "contract_date": datetime.now().strftime("%Y-%m-%d"),
                "address": f"{TEST_PREFIX}Адрес нулевая площадь",
                "area": 0.0,
                "total_amount": 100000.0,
                "advance_payment": 50000.0,
                "additional_payment": 50000.0,
                "contract_period": 30,
                "status": "Новый заказ",
            })
            # 200 или 422 — оба допустимы
            assert resp.status_code in (200, 201, 422)
            if resp.status_code in (200, 201):
                _delete(f"/api/contracts/{resp.json()['id']}", admin_headers)
        finally:
            _delete(f"/api/clients/{client_id}", admin_headers)

    def test_minimal_salary_amount(self, admin_headers):
        """Зарплата с минимальной суммой (0.01)."""
        resp = _post("/api/salaries", admin_headers, json={
            "employee_id": 1,
            "amount": 0.01,
            "report_month": "2026-03",
            "description": f"{TEST_PREFIX}Минимальная зарплата",
        })
        if resp.status_code in (200, 201):
            sid = resp.json()["id"]
            check = _get(f"/api/salaries/{sid}", admin_headers).json()
            assert check["amount"] == 0.01
            _delete(f"/api/salaries/{sid}", admin_headers)
        else:
            assert resp.status_code in (422, 400)
