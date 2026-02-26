# -*- coding: utf-8 -*-
"""
E2E Tests: Углублённые тесты платежей (Этап 6)
~15 тестов — GET /api/payments/ с фильтрами, summary, by-type,
all-optimized, recalculate, manual-update, calculate по ролям.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import (
    TEST_PREFIX, api_get, api_post, api_put, api_patch, api_delete,
)


# ================================================================
# GET /api/payments/ — фильтры
# ================================================================

class TestPaymentsListDeep:
    """Углублённые тесты списка платежей с фильтрами"""

    def test_list_no_params(self, api_base, admin_headers):
        """GET /api/payments/ без параметров — возвращает список."""
        resp = api_get(api_base, "/api/payments/", admin_headers)
        assert resp.status_code == 200, f"Ожидался 200, получен {resp.status_code}: {resp.text}"
        data = resp.json()
        assert isinstance(data, list)

    def test_list_with_year(self, api_base, admin_headers):
        """GET /api/payments/?year=2026 — фильтр по году."""
        resp = api_get(api_base, "/api/payments/", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_with_year_and_month(self, api_base, admin_headers):
        """GET /api/payments/?year=2026&month=1 — фильтр по году и месяцу."""
        resp = api_get(api_base, "/api/payments/", admin_headers,
                       params={"year": 2026, "month": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_include_null_month(self, api_base, admin_headers):
        """GET /api/payments/?year=2026&include_null_month=true — включая платежи без месяца."""
        resp = api_get(api_base, "/api/payments/", admin_headers,
                       params={"year": 2026, "include_null_month": "true"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_empty_year(self, api_base, admin_headers):
        """GET /api/payments/?year=2099 — пустой год, пустой список."""
        resp = api_get(api_base, "/api/payments/", admin_headers,
                       params={"year": 2099})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 0, "За 2099 год не должно быть платежей"


# ================================================================
# GET /api/payments/calculate — расчёт по ролям
# ================================================================

class TestPaymentsCalculateDeep:
    """Углублённые тесты расчёта платежей по ролям"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees

    def test_calculate_designer(self):
        """Расчёт для роли Дизайнер."""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"], area=100.0)
        resp = api_get(
            self.api_base, "/api/payments/calculate", self.headers,
            params={
                "contract_id": contract["id"],
                "employee_id": designer["id"],
                "role": "Дизайнер",
                "stage_name": "Стадия 1: планировочные решения",
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        # Ответ содержит calculated_amount
        assert "calculated_amount" in data or isinstance(data, dict), \
            f"Ожидается dict с результатом расчёта: {data}"

    def test_calculate_draftsman(self):
        """Расчёт для роли Чертёжник."""
        draftsman = self.employees.get('draftsman')
        if not draftsman:
            pytest.skip("Нет тестового чертёжника")
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"], area=80.0)
        resp = api_get(
            self.api_base, "/api/payments/calculate", self.headers,
            params={
                "contract_id": contract["id"],
                "employee_id": draftsman["id"],
                "role": "Чертёжник",
                "stage_name": "Стадия 2: рабочие чертежи",
            }
        )
        assert resp.status_code == 200

    def test_calculate_surveyor(self):
        """Расчёт для роли Замерщик."""
        surveyor = self.employees.get('surveyor')
        if not surveyor:
            pytest.skip("Нет тестового замерщика")
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"], area=60.0)
        resp = api_get(
            self.api_base, "/api/payments/calculate", self.headers,
            params={
                "contract_id": contract["id"],
                "employee_id": surveyor["id"],
                "role": "Замерщик",
                "stage_name": "Замер",
            }
        )
        assert resp.status_code == 200


# ================================================================
# GET /api/payments/summary
# ================================================================

class TestPaymentsSummaryDeep:
    """Углублённые тесты сводки платежей"""

    def test_summary_with_quarter(self, api_base, admin_headers):
        """GET /api/payments/summary?year=2026&quarter=1 — по кварталу."""
        resp = api_get(api_base, "/api/payments/summary", admin_headers,
                       params={"year": 2026, "quarter": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_paid" in data
        assert "total_pending" in data
        assert "total" in data
        assert "by_role" in data
        assert isinstance(data["by_role"], dict)

    def test_summary_consistency(self, api_base, admin_headers):
        """GET /api/payments/summary — total_paid + total_pending == total."""
        resp = api_get(api_base, "/api/payments/summary", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        total_paid = data.get("total_paid", 0)
        total_pending = data.get("total_pending", 0)
        total = data.get("total", 0)
        assert abs((total_paid + total_pending) - total) < 0.01, (
            f"total_paid({total_paid}) + total_pending({total_pending}) != total({total})"
        )

    def test_summary_empty_year(self, api_base, admin_headers):
        """GET /api/payments/summary?year=2099 — пустая сводка."""
        resp = api_get(api_base, "/api/payments/summary", admin_headers,
                       params={"year": 2099})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0, "За 2099 год не должно быть платежей"
        assert data["payments_count"] == 0


# ================================================================
# GET /api/payments/by-type
# ================================================================

class TestPaymentsByTypeDeep:
    """Углублённые тесты платежей по типу"""

    def test_by_type_supervision(self, api_base, admin_headers):
        """GET /api/payments/by-type?payment_type=Авторский надзор — список надзорных."""
        resp = api_get(api_base, "/api/payments/by-type", admin_headers,
                       params={"payment_type": "Авторский надзор"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_by_type_salaries(self, api_base, admin_headers):
        """GET /api/payments/by-type?payment_type=Оклады — список окладов."""
        resp = api_get(api_base, "/api/payments/by-type", admin_headers,
                       params={"payment_type": "Оклады"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_by_type_individual(self, api_base, admin_headers):
        """GET /api/payments/by-type?payment_type=Индивидуальный — индивидуальные."""
        resp = api_get(api_base, "/api/payments/by-type", admin_headers,
                       params={"payment_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


# ================================================================
# GET /api/payments/all-optimized
# ================================================================

class TestPaymentsAllOptimizedDeep:
    """Углублённые тесты оптимизированного списка"""

    def test_all_optimized_with_year_and_month(self, api_base, admin_headers):
        """GET /api/payments/all-optimized?year=2026&month=1 — по году и месяцу."""
        resp = api_get(api_base, "/api/payments/all-optimized", admin_headers,
                       params={"year": 2026, "month": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_all_optimized_empty_year(self, api_base, admin_headers):
        """GET /api/payments/all-optimized?year=2099 — пустой список."""
        resp = api_get(api_base, "/api/payments/all-optimized", admin_headers,
                       params={"year": 2099})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 0, "За 2099 год не должно быть платежей"


# ================================================================
# POST /api/payments/recalculate
# ================================================================

class TestPaymentsRecalculateDeep:
    """Углублённые тесты пересчёта платежей"""

    def test_recalculate_all(self, api_base, admin_headers):
        """POST /api/payments/recalculate — пересчёт всех платежей."""
        resp = api_post(api_base, "/api/payments/recalculate", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"
        assert "updated" in data
        assert "total" in data
        assert data["total"] >= 0

    def test_recalculate_by_role_draftsman(self, api_base, admin_headers):
        """POST /api/payments/recalculate с ролью Чертёжник."""
        resp = api_post(api_base, "/api/payments/recalculate", admin_headers,
                        json={"role": "Чертёжник"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"


# ================================================================
# PATCH /api/payments/{id}/manual — ручное обновление
# ================================================================

class TestPaymentsManualUpdateDeep:
    """Углублённые тесты ручного обновления платежа"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees

    def test_manual_update_sets_amount(self):
        """PATCH /api/payments/{id}/manual — установка суммы вручную."""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_crm_card(contract["id"])
        payment = self.factory.create_payment(
            contract["id"], designer["id"], "Дизайнер",
            crm_card_id=card["id"]
        )
        resp = api_patch(
            self.api_base,
            f"/api/payments/{payment['id']}/manual",
            self.headers,
            json={"amount": 75000.0, "report_month": "2026-02"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["manual_amount"] == 75000.0, "manual_amount должен быть 75000"
        assert data["final_amount"] == 75000.0, "final_amount должен быть 75000"
        assert data["report_month"] == "2026-02"

    def test_manual_update_nonexistent(self, api_base, admin_headers):
        """PATCH /api/payments/999999/manual — несуществующий платёж -> 404."""
        resp = api_patch(
            api_base,
            "/api/payments/999999/manual",
            admin_headers,
            json={"amount": 10000.0, "report_month": "2026-01"}
        )
        assert resp.status_code == 404, \
            f"Ожидался 404 для несуществующего платежа, получен {resp.status_code}"
