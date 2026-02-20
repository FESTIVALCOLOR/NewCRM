# -*- coding: utf-8 -*-
"""
E2E Tests: Зарплаты (Salaries)
15 тестов -- CRUD зарплат, фильтрация, отчёт по сотрудникам.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_put, api_delete

REQUEST_TIMEOUT = 15


class TestSalaryCRUD:
    """CRUD операции с зарплатами"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees

    @pytest.mark.critical
    def test_create_salary(self):
        """Создание зарплаты"""
        sdp = self.employees.get('sdp')
        if not sdp:
            pytest.skip("Нет СДП")

        salary = self.factory.create_salary(
            employee_id=sdp["id"],
            payment_type="Оклад",
            amount=50000.0,
            report_month="2026-02",
        )
        assert salary["id"] > 0
        assert salary["employee_id"] == sdp["id"]
        assert salary["payment_type"] == "Оклад"
        assert salary["amount"] == 50000.0
        assert salary["report_month"] == "2026-02"

    def test_create_salary_with_contract(self):
        """Создание зарплаты с привязкой к договору"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])

        salary = self.factory.create_salary(
            employee_id=designer["id"],
            payment_type="Оклад",
            amount=45000.0,
            report_month="2026-02",
            contract_id=contract["id"],
            stage_name="Стадия 1: планировочные решения",
        )
        assert salary["id"] > 0
        assert salary["contract_id"] == contract["id"]
        assert salary["stage_name"] == "Стадия 1: планировочные решения"

    def test_create_salary_with_optional_fields(self):
        """Создание зарплаты со всеми необязательными полями"""
        gap = self.employees.get('gap')
        if not gap:
            pytest.skip("Нет ГАП")

        salary = self.factory.create_salary(
            employee_id=gap["id"],
            payment_type="Оклад",
            amount=60000.0,
            report_month="2026-01",
            advance_payment=20000.0,
            project_type="Индивидуальный",
            payment_status="Оплачено",
            comments=f"{TEST_PREFIX}Тестовый комментарий",
        )
        assert salary["id"] > 0
        assert salary["advance_payment"] == 20000.0
        assert salary["project_type"] == "Индивидуальный"
        assert salary["payment_status"] == "Оплачено"

    def test_get_salary_by_id(self):
        """Получение зарплаты по ID"""
        sdp = self.employees.get('sdp')
        if not sdp:
            pytest.skip("Нет СДП")

        salary = self.factory.create_salary(
            employee_id=sdp["id"],
            amount=55000.0,
            report_month="2026-03",
        )
        resp = api_get(self.api_base, f"/api/salaries/{salary['id']}", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == salary["id"]
        assert data["employee_id"] == sdp["id"]
        assert data["amount"] == 55000.0

    def test_get_salary_not_found(self):
        """Получение несуществующей зарплаты -> 404"""
        resp = api_get(self.api_base, "/api/salaries/999999", self.headers)
        assert resp.status_code == 404

    @pytest.mark.critical
    def test_update_salary(self):
        """Обновление зарплаты"""
        manager = self.employees.get('manager')
        if not manager:
            pytest.skip("Нет менеджера")

        salary = self.factory.create_salary(
            employee_id=manager["id"],
            amount=40000.0,
            report_month="2026-02",
        )
        resp = api_put(
            self.api_base,
            f"/api/salaries/{salary['id']}",
            self.headers,
            json={"amount": 60000.0}
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["amount"] == 60000.0

    def test_update_salary_multiple_fields(self):
        """Обновление нескольких полей зарплаты"""
        sdp = self.employees.get('sdp')
        if not sdp:
            pytest.skip("Нет СДП")

        salary = self.factory.create_salary(
            employee_id=sdp["id"],
            amount=50000.0,
            report_month="2026-01",
        )
        resp = api_put(
            self.api_base,
            f"/api/salaries/{salary['id']}",
            self.headers,
            json={
                "amount": 70000.0,
                "advance_payment": 25000.0,
                "payment_status": "Оплачено",
                "comments": f"{TEST_PREFIX}Обновлённый комментарий",
            }
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["amount"] == 70000.0
        assert updated["advance_payment"] == 25000.0
        assert updated["payment_status"] == "Оплачено"

    def test_update_salary_not_found(self):
        """Обновление несуществующей зарплаты -> 404"""
        resp = api_put(
            self.api_base,
            "/api/salaries/999999",
            self.headers,
            json={"amount": 99999.0}
        )
        assert resp.status_code == 404

    @pytest.mark.critical
    def test_delete_salary(self):
        """Удаление зарплаты"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        # Создаём напрямую (не через фабрику) чтобы сами удалили
        resp = api_post(self.api_base, "/api/salaries", self.headers, json={
            "employee_id": designer["id"],
            "payment_type": "Оклад",
            "amount": 33000.0,
            "report_month": "2026-04",
        })
        assert resp.status_code == 200
        salary_id = resp.json()["id"]

        # Удаляем
        resp = api_delete(self.api_base, f"/api/salaries/{salary_id}", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

        # Проверяем что удалён
        resp = api_get(self.api_base, f"/api/salaries/{salary_id}", self.headers)
        assert resp.status_code == 404

    def test_delete_salary_not_found(self):
        """Удаление несуществующей зарплаты -> 404"""
        resp = api_delete(self.api_base, "/api/salaries/999999", self.headers)
        assert resp.status_code == 404


class TestSalaryFiltering:
    """Фильтрация зарплат"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees

    @pytest.mark.critical
    def test_get_all_salaries(self):
        """Получение списка всех зарплат"""
        sdp = self.employees.get('sdp')
        if not sdp:
            pytest.skip("Нет СДП")

        self.factory.create_salary(
            employee_id=sdp["id"],
            amount=50000.0,
            report_month="2026-05",
        )
        resp = api_get(self.api_base, "/api/salaries", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_filter_by_report_month(self):
        """Фильтрация зарплат по report_month"""
        gap = self.employees.get('gap')
        if not gap:
            pytest.skip("Нет ГАП")

        unique_month = "2025-06"
        self.factory.create_salary(
            employee_id=gap["id"],
            amount=48000.0,
            report_month=unique_month,
        )

        resp = api_get(
            self.api_base, "/api/salaries", self.headers,
            params={"report_month": unique_month}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for salary in data:
            assert salary["report_month"] == unique_month

    def test_filter_by_employee_id(self):
        """Фильтрация зарплат по employee_id"""
        draftsman = self.employees.get('draftsman')
        if not draftsman:
            pytest.skip("Нет чертёжника")

        self.factory.create_salary(
            employee_id=draftsman["id"],
            amount=42000.0,
            report_month="2026-06",
        )

        resp = api_get(
            self.api_base, "/api/salaries", self.headers,
            params={"employee_id": draftsman["id"]}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for salary in data:
            assert salary["employee_id"] == draftsman["id"]

    def test_filter_by_both(self):
        """Фильтрация по report_month и employee_id одновременно"""
        surveyor = self.employees.get('surveyor')
        if not surveyor:
            pytest.skip("Нет замерщика")

        unique_month = "2025-07"
        self.factory.create_salary(
            employee_id=surveyor["id"],
            amount=35000.0,
            report_month=unique_month,
        )

        resp = api_get(
            self.api_base, "/api/salaries", self.headers,
            params={
                "report_month": unique_month,
                "employee_id": surveyor["id"],
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for salary in data:
            assert salary["report_month"] == unique_month
            assert salary["employee_id"] == surveyor["id"]

    def test_filter_returns_empty(self):
        """Фильтр без совпадений возвращает пустой список"""
        resp = api_get(
            self.api_base, "/api/salaries", self.headers,
            params={"report_month": "1990-01"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestSalaryReport:
    """Отчёт по зарплатам (/api/salaries/report)"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees

    @pytest.mark.critical
    def test_report_basic(self):
        """Базовый отчёт по зарплатам"""
        sdp = self.employees.get('sdp')
        if not sdp:
            pytest.skip("Нет СДП")

        unique_month = "2025-08"
        self.factory.create_salary(
            employee_id=sdp["id"],
            amount=50000.0,
            report_month=unique_month,
        )

        resp = api_get(
            self.api_base, "/api/salaries/report", self.headers,
            params={"report_month": unique_month}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "report_month" in data
        assert "total_amount" in data
        assert "employees" in data
        assert data["report_month"] == unique_month
        assert data["total_amount"] >= 50000.0
        assert isinstance(data["employees"], list)
        assert len(data["employees"]) >= 1

    def test_report_aggregates_by_employee(self):
        """Отчёт группирует записи по сотруднику"""
        gap = self.employees.get('gap')
        if not gap:
            pytest.skip("Нет ГАП")

        unique_month = "2025-09"
        self.factory.create_salary(
            employee_id=gap["id"],
            amount=30000.0,
            report_month=unique_month,
            payment_type="Оклад",
        )
        self.factory.create_salary(
            employee_id=gap["id"],
            amount=20000.0,
            report_month=unique_month,
            payment_type="Оклад",
        )

        resp = api_get(
            self.api_base, "/api/salaries/report", self.headers,
            params={
                "report_month": unique_month,
                "employee_id": gap["id"],
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_amount"] >= 50000.0

        # Должен быть один сотрудник с двумя записями
        emp_entry = None
        for emp in data["employees"]:
            if emp["employee_id"] == gap["id"]:
                emp_entry = emp
                break
        assert emp_entry is not None, "Сотрудник не найден в отчёте"
        assert emp_entry["total_amount"] >= 50000.0
        assert len(emp_entry["records"]) >= 2

    def test_report_filter_by_payment_type(self):
        """Отчёт с фильтрацией по payment_type"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        unique_month = "2025-10"
        self.factory.create_salary(
            employee_id=designer["id"],
            amount=55000.0,
            report_month=unique_month,
            payment_type="Оклад",
        )

        resp = api_get(
            self.api_base, "/api/salaries/report", self.headers,
            params={
                "report_month": unique_month,
                "payment_type": "Оклад",
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_amount"] >= 55000.0

    def test_report_employee_details(self):
        """Отчёт содержит полные данные по сотрудникам"""
        manager = self.employees.get('manager')
        if not manager:
            pytest.skip("Нет менеджера")

        unique_month = "2025-11"
        self.factory.create_salary(
            employee_id=manager["id"],
            amount=38000.0,
            report_month=unique_month,
            payment_type="Оклад",
        )

        resp = api_get(
            self.api_base, "/api/salaries/report", self.headers,
            params={
                "report_month": unique_month,
                "employee_id": manager["id"],
            }
        )
        assert resp.status_code == 200
        data = resp.json()

        emp_entry = None
        for emp in data["employees"]:
            if emp["employee_id"] == manager["id"]:
                emp_entry = emp
                break
        assert emp_entry is not None

        # Проверяем структуру данных сотрудника
        assert "employee_id" in emp_entry
        assert "employee_name" in emp_entry
        assert "position" in emp_entry
        assert "total_amount" in emp_entry
        assert "advance_payment" in emp_entry
        assert "records" in emp_entry

        # Проверяем структуру записи
        record = emp_entry["records"][0]
        assert "id" in record
        assert "payment_type" in record
        assert "amount" in record
        assert "report_month" in record

    def test_report_empty_month(self):
        """Отчёт за месяц без зарплат"""
        resp = api_get(
            self.api_base, "/api/salaries/report", self.headers,
            params={"report_month": "1990-01"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_amount"] == 0
        assert data["employees"] == []
