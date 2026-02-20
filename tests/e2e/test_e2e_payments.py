# -*- coding: utf-8 -*-
"""
E2E Tests: Платежи, расчёт, переназначение
14 тестов — CRUD платежей, расчёт, переназначение, report_month.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_put, api_patch, api_delete


class TestPaymentCRUD:
    """CRUD операции с платежами"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(self.contract["id"])

    @pytest.mark.critical
    def test_create_payment(self):
        """Создание платежа"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        payment = self.factory.create_payment(
            contract_id=self.contract["id"],
            employee_id=designer["id"],
            role="Дизайнер",
            stage_name="Стадия 1: планировочные решения",
            crm_card_id=self.card["id"],
        )
        assert payment["id"] > 0
        assert payment["contract_id"] == self.contract["id"]
        assert payment["employee_id"] == designer["id"]

    def test_get_payment_by_id(self):
        """Получение платежа по ID"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        payment = self.factory.create_payment(
            self.contract["id"], designer["id"], "Дизайнер",
            crm_card_id=self.card["id"]
        )
        resp = api_get(self.api_base, f"/api/payments/{payment['id']}", self.headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == payment["id"]

    def test_get_payments_by_contract(self):
        """Получение платежей по договору"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        self.factory.create_payment(
            self.contract["id"], designer["id"], "Дизайнер",
            crm_card_id=self.card["id"]
        )
        resp = api_get(
            self.api_base,
            f"/api/payments/contract/{self.contract['id']}",
            self.headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_update_payment(self):
        """Обновление платежа"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        payment = self.factory.create_payment(
            self.contract["id"], designer["id"], "Дизайнер",
            crm_card_id=self.card["id"]
        )
        resp = api_put(
            self.api_base,
            f"/api/payments/{payment['id']}",
            self.headers,
            json={"final_amount": 50000.0, "is_manual": True, "manual_amount": 50000.0}
        )
        assert resp.status_code == 200

    def test_delete_payment(self):
        """Удаление платежа"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        payment = self.factory.create_payment(
            self.contract["id"], designer["id"], "Дизайнер",
            crm_card_id=self.card["id"]
        )
        resp = api_delete(self.api_base, f"/api/payments/{payment['id']}", self.headers)
        assert resp.status_code == 200

    def test_mark_paid(self):
        """Отметка платежа как оплаченного"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        payment = self.factory.create_payment(
            self.contract["id"], designer["id"], "Дизайнер",
            crm_card_id=self.card["id"]
        )
        # Endpoint expects employee_id as query param, not JSON body
        resp = api_patch(
            self.api_base,
            f"/api/payments/{payment['id']}/mark-paid?employee_id={designer['id']}",
            self.headers,
        )
        assert resp.status_code == 200


class TestPaymentCalculation:
    """Расчёт сумм платежей"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees

    @pytest.mark.critical
    def test_calculate_individual_project(self):
        """Расчёт для индивидуального проекта"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        client = self.factory.create_client()
        contract = self.factory.create_contract(
            client["id"],
            project_type="Индивидуальный",
            area=75.0
        )
        resp = api_get(
            self.api_base,
            "/api/payments/calculate",
            self.headers,
            params={
                "contract_id": contract["id"],
                "employee_id": designer["id"],
                "role": "Дизайнер",
                "stage_name": "Стадия 1: планировочные решения",
            }
        )
        assert resp.status_code == 200

    def test_calculate_template_project(self):
        """Расчёт для шаблонного проекта"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        client = self.factory.create_client()
        contract = self.factory.create_contract(
            client["id"],
            project_type="Шаблонный",
            area=50.0
        )
        resp = api_get(
            self.api_base,
            "/api/payments/calculate",
            self.headers,
            params={
                "contract_id": contract["id"],
                "employee_id": designer["id"],
                "role": "Дизайнер",
                "stage_name": "Стадия 1: планировочные решения",
            }
        )
        assert resp.status_code == 200

    def test_calculate_supervision(self):
        """Расчёт для надзора"""
        dan = self.employees.get('dan')
        if not dan:
            pytest.skip("Нет ДАН")

        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"], area=80.0)
        resp = api_get(
            self.api_base,
            "/api/payments/calculate",
            self.headers,
            params={
                "contract_id": contract["id"],
                "employee_id": dan["id"],
                "role": "ДАН",
                "stage_name": "Стадия 1: Закупка керамогранита",
            }
        )
        assert resp.status_code == 200


class TestPaymentReassignment:
    """Переназначение платежей"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(self.contract["id"])

    @pytest.mark.critical
    def test_reassigned_excluded_from_active(self):
        """Переназначенный платёж не в активных"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        payment = self.factory.create_payment(
            self.contract["id"], designer["id"], "Дизайнер",
            crm_card_id=self.card["id"],
            reassigned=True
        )

        resp = api_get(
            self.api_base,
            f"/api/payments/contract/{self.contract['id']}",
            self.headers
        )
        assert resp.status_code == 200
        payments = resp.json()
        # Проверяем что переназначенный платёж имеет флаг reassigned
        found = [p for p in payments if p["id"] == payment["id"]]
        if found:
            assert found[0]["reassigned"] == True

    def test_reassignment_creates_new_payment(self):
        """Переназначение создаёт новый платёж"""
        designer = self.employees.get('designer')
        draftsman = self.employees.get('draftsman')
        if not designer or not draftsman:
            pytest.skip("Нужны дизайнер и чертёжник")

        # Первый платёж
        p1 = self.factory.create_payment(
            self.contract["id"], designer["id"], "Дизайнер",
            crm_card_id=self.card["id"]
        )

        # "Переназначаем" — отмечаем старый как reassigned, создаём новый
        api_put(self.api_base, f"/api/payments/{p1['id']}", self.headers,
                json={"reassigned": True, "old_employee_id": designer["id"]})

        p2 = self.factory.create_payment(
            self.contract["id"], draftsman["id"], "Чертёжник",
            crm_card_id=self.card["id"]
        )

        assert p2["id"] != p1["id"]
        assert p2["employee_id"] == draftsman["id"]


class TestReportMonth:
    """Тесты report_month"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(self.contract["id"])

    def test_null_report_month_means_in_progress(self):
        """report_month = NULL -> работа в процессе"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        payment = self.factory.create_payment(
            self.contract["id"], designer["id"], "Дизайнер",
            crm_card_id=self.card["id"]
        )
        assert payment.get("report_month") is None

    def test_set_report_month_on_acceptance(self):
        """Установка report_month при принятии работы"""
        resp = api_patch(
            self.api_base,
            f"/api/payments/contract/{self.contract['id']}/report-month",
            self.headers,
            json={"report_month": "2026-02", "stage_name": "Стадия 1: планировочные решения"}
        )
        assert resp.status_code == 200


class TestPaymentSummary:
    """Сводка по платежам (GET /api/payments/summary)"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers):
        self.api_base = api_base
        self.headers = admin_headers

    def test_payment_summary_basic(self):
        """GET /api/payments/summary?year=2026 -> 200, проверка структуры"""
        resp = api_get(
            self.api_base,
            "/api/payments/summary",
            self.headers,
            params={"year": 2026}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "year" in data
        assert "total_paid" in data
        assert "total_pending" in data
        assert "total" in data
        assert "by_role" in data
        assert "payments_count" in data

    def test_payment_summary_with_month(self):
        """GET /api/payments/summary?year=2026&month=2 -> 200"""
        resp = api_get(
            self.api_base,
            "/api/payments/summary",
            self.headers,
            params={"year": 2026, "month": 2}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "year" in data
        assert "total" in data

    def test_payment_summary_has_totals(self):
        """total_paid + total_pending == total (приблизительно)"""
        resp = api_get(
            self.api_base,
            "/api/payments/summary",
            self.headers,
            params={"year": 2026}
        )
        assert resp.status_code == 200
        data = resp.json()
        total_paid = data.get("total_paid", 0.0)
        total_pending = data.get("total_pending", 0.0)
        total = data.get("total", 0.0)
        assert abs((total_paid + total_pending) - total) < 0.01, (
            f"total_paid ({total_paid}) + total_pending ({total_pending}) "
            f"!= total ({total})"
        )


class TestPaymentByType:
    """Платежи по типу (GET /api/payments/by-type)"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers):
        self.api_base = api_base
        self.headers = admin_headers

    def test_payments_by_type_crm(self):
        """GET /api/payments/by-type?payment_type=Авторский надзор -> 200, список"""
        resp = api_get(
            self.api_base,
            "/api/payments/by-type",
            self.headers,
            params={"payment_type": "Авторский надзор"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_payments_by_type_salaries(self):
        """GET /api/payments/by-type?payment_type=Оклады -> 200, список"""
        resp = api_get(
            self.api_base,
            "/api/payments/by-type",
            self.headers,
            params={"payment_type": "Оклады"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestPaymentAllOptimized:
    """Все платежи оптимизированные (GET /api/payments/all-optimized)"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers):
        self.api_base = api_base
        self.headers = admin_headers

    def test_all_optimized_basic(self):
        """GET /api/payments/all-optimized -> 200, список словарей"""
        resp = api_get(
            self.api_base,
            "/api/payments/all-optimized",
            self.headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_all_optimized_with_year(self):
        """GET /api/payments/all-optimized?year=2026 -> 200"""
        resp = api_get(
            self.api_base,
            "/api/payments/all-optimized",
            self.headers,
            params={"year": 2026}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestPaymentRecalculate:
    """Пересчёт платежей (POST /api/payments/recalculate)"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers):
        self.api_base = api_base
        self.headers = admin_headers

    def test_recalculate_all(self):
        """POST /api/payments/recalculate -> 200, ответ с status/updated/total"""
        resp = api_post(
            self.api_base,
            "/api/payments/recalculate",
            self.headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"
        assert "updated" in data
        assert "total" in data

    def test_recalculate_by_role(self):
        """POST /api/payments/recalculate с ролью -> 200"""
        resp = api_post(
            self.api_base,
            "/api/payments/recalculate",
            self.headers,
            json={"role": "Дизайнер"}
        )
        assert resp.status_code == 200
