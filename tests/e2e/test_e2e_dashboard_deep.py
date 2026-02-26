# -*- coding: utf-8 -*-
"""
E2E Tests: Углублённые тесты дашборда (Этап 6)
~20 тестов — проверка всех 13 endpoints dashboard_router.py
с различными параметрами, пустыми данными и проверкой структуры ответов.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get


# ================================================================
# GET /api/dashboard/clients
# ================================================================

class TestDashboardClientsDeep:
    """Углублённые тесты дашборда клиентов"""

    def test_clients_no_params(self, api_base, admin_headers):
        """GET /api/dashboard/clients без параметров — общая статистика."""
        resp = api_get(api_base, "/api/dashboard/clients", admin_headers)
        assert resp.status_code == 200, f"Ожидался 200, получен {resp.status_code}: {resp.text}"
        data = resp.json()
        expected_keys = ["total_clients", "total_individual", "total_legal",
                         "clients_by_year", "agent_clients_total", "agent_clients_by_year"]
        for key in expected_keys:
            assert key in data, f"Ожидается ключ '{key}' в ответе"
            assert isinstance(data[key], (int, float)), f"Значение '{key}' должно быть числом"
            assert data[key] >= 0, f"Значение '{key}' не может быть отрицательным"
        # Без year: clients_by_year должен быть 0
        assert data["clients_by_year"] == 0, "Без параметра year clients_by_year должен быть 0"

    def test_clients_with_year(self, api_base, admin_headers):
        """GET /api/dashboard/clients?year=2026 — фильтр по году."""
        resp = api_get(api_base, "/api/dashboard/clients", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert "clients_by_year" in data
        assert isinstance(data["clients_by_year"], (int, float))

    def test_clients_with_agent_type(self, api_base, admin_headers):
        """GET /api/dashboard/clients?agent_type=ФЕСТИВАЛЬ — фильтр по агенту."""
        resp = api_get(api_base, "/api/dashboard/clients", admin_headers,
                       params={"agent_type": "ФЕСТИВАЛЬ"})
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_clients_total" in data
        assert data["agent_clients_total"] >= 0

    def test_clients_with_year_and_agent(self, api_base, admin_headers):
        """GET /api/dashboard/clients?year=2026&agent_type=ФЕСТИВАЛЬ — комбинированный фильтр."""
        resp = api_get(api_base, "/api/dashboard/clients", admin_headers,
                       params={"year": 2026, "agent_type": "ФЕСТИВАЛЬ"})
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_clients_by_year" in data
        assert data["agent_clients_by_year"] >= 0

    def test_clients_empty_agent_type(self, api_base, admin_headers):
        """GET /api/dashboard/clients?agent_type= — пустой agent_type, агентские поля = 0."""
        resp = api_get(api_base, "/api/dashboard/clients", admin_headers,
                       params={"agent_type": ""})
        assert resp.status_code == 200
        data = resp.json()
        # Пустая строка => agent_clients_total == 0
        assert data["agent_clients_total"] == 0, "При пустом agent_type агентских клиентов нет"

    def test_clients_year_no_data(self, api_base, admin_headers):
        """GET /api/dashboard/clients?year=2099 — год без данных."""
        resp = api_get(api_base, "/api/dashboard/clients", admin_headers,
                       params={"year": 2099})
        assert resp.status_code == 200
        data = resp.json()
        assert data["clients_by_year"] == 0, "За 2099 год не должно быть клиентов"


# ================================================================
# GET /api/dashboard/contracts
# ================================================================

class TestDashboardContractsDeep:
    """Углублённые тесты дашборда договоров"""

    def test_contracts_no_params(self, api_base, admin_headers):
        """GET /api/dashboard/contracts без параметров — общие итоги."""
        resp = api_get(api_base, "/api/dashboard/contracts", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = ["individual_orders", "individual_area",
                         "template_orders", "template_area",
                         "agent_orders_by_year", "agent_area_by_year"]
        for key in expected_keys:
            assert key in data, f"Ожидается ключ '{key}'"
        # Без agent_type+year: агентские поля = 0
        assert data["agent_orders_by_year"] == 0
        assert data["agent_area_by_year"] == 0

    def test_contracts_with_agent_and_year(self, api_base, admin_headers):
        """GET /api/dashboard/contracts?year=2026&agent_type=ФЕСТИВАЛЬ — агентский фильтр."""
        resp = api_get(api_base, "/api/dashboard/contracts", admin_headers,
                       params={"year": 2026, "agent_type": "ФЕСТИВАЛЬ"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_orders_by_year"] >= 0
        assert isinstance(data["agent_area_by_year"], (int, float))


# ================================================================
# GET /api/dashboard/crm
# ================================================================

class TestDashboardCrmDeep:
    """Углублённые тесты дашборда CRM"""

    def test_crm_individual(self, api_base, admin_headers):
        """GET /api/dashboard/crm?project_type=Индивидуальный — индивидуальные проекты."""
        resp = api_get(api_base, "/api/dashboard/crm", admin_headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        for key in ["total_orders", "total_area", "active_orders",
                     "archive_orders", "agent_active_orders", "agent_archive_orders"]:
            assert key in data, f"Ожидается ключ '{key}'"
        assert data["total_orders"] >= 0
        assert data["active_orders"] >= 0
        assert data["archive_orders"] >= 0

    def test_crm_template(self, api_base, admin_headers):
        """GET /api/dashboard/crm?project_type=Шаблонный — шаблонные проекты."""
        resp = api_get(api_base, "/api/dashboard/crm", admin_headers,
                       params={"project_type": "Шаблонный"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_orders" in data
        assert data["total_orders"] >= 0

    def test_crm_supervision(self, api_base, admin_headers):
        """GET /api/dashboard/crm?project_type=Авторский надзор — надзор."""
        resp = api_get(api_base, "/api/dashboard/crm", admin_headers,
                       params={"project_type": "Авторский надзор"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_orders" in data
        assert "active_orders" in data

    def test_crm_with_agent_filter(self, api_base, admin_headers):
        """GET /api/dashboard/crm?project_type=Индивидуальный&agent_type=ФЕСТИВАЛЬ — с агентом."""
        resp = api_get(api_base, "/api/dashboard/crm", admin_headers,
                       params={"project_type": "Индивидуальный", "agent_type": "ФЕСТИВАЛЬ"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_active_orders"] >= 0
        assert data["agent_archive_orders"] >= 0


# ================================================================
# GET /api/dashboard/employees
# ================================================================

class TestDashboardEmployeesDeep:
    """Углублённые тесты дашборда сотрудников"""

    def test_employees_structure(self, api_base, admin_headers):
        """GET /api/dashboard/employees — полная проверка структуры."""
        resp = api_get(api_base, "/api/dashboard/employees", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = ["active_employees", "reserve_employees",
                         "active_management", "active_admin",
                         "active_projects_dept", "active_project",
                         "active_execution_dept", "active_execution",
                         "upcoming_birthdays", "nearest_birthday"]
        for key in expected_keys:
            assert key in data, f"Ожидается ключ '{key}'"
        assert data["active_employees"] > 0, "Должен быть хотя бы admin"
        assert isinstance(data["nearest_birthday"], str), "nearest_birthday должен быть строкой"


# ================================================================
# GET /api/dashboard/salaries* (6 endpoints)
# ================================================================

class TestDashboardSalariesDeep:
    """Углублённые тесты дашборда зарплат"""

    def test_salaries_with_year_and_month(self, api_base, admin_headers):
        """GET /api/dashboard/salaries?year=2026&month=1 — по году и месяцу."""
        resp = api_get(api_base, "/api/dashboard/salaries", admin_headers,
                       params={"year": 2026, "month": 1})
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = ["total_paid", "paid_by_year", "paid_by_month",
                         "individual_by_year", "template_by_year", "supervision_by_year"]
        for key in expected_keys:
            assert key in data, f"Ожидается ключ '{key}'"
            assert isinstance(data[key], (int, float)), f"'{key}' должен быть числом"

    def test_salaries_by_type_all(self, api_base, admin_headers):
        """GET /api/dashboard/salaries-by-type?payment_type=all — все типы."""
        resp = api_get(api_base, "/api/dashboard/salaries-by-type", admin_headers,
                       params={"payment_type": "all"})
        assert resp.status_code == 200
        data = resp.json()
        for key in ["total_paid", "paid_by_year", "paid_by_month",
                     "payments_count", "to_pay_amount", "by_agent"]:
            assert key in data, f"Ожидается ключ '{key}'"

    def test_salaries_by_type_individual(self, api_base, admin_headers):
        """GET /api/dashboard/salaries-by-type?payment_type=individual — индивидуальные."""
        resp = api_get(api_base, "/api/dashboard/salaries-by-type", admin_headers,
                       params={"payment_type": "individual", "year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_paid" in data

    def test_salaries_by_type_salary(self, api_base, admin_headers):
        """GET /api/dashboard/salaries-by-type?payment_type=salary — оклады (отдельная логика)."""
        resp = api_get(api_base, "/api/dashboard/salaries-by-type", admin_headers,
                       params={"payment_type": "salary", "year": 2026, "month": 1})
        assert resp.status_code == 200
        data = resp.json()
        # Для окладов to_pay_amount всегда 0 и by_agent = 0
        assert data["to_pay_amount"] == 0, "Для окладов to_pay_amount всегда 0"
        assert data["by_agent"] == 0, "Для окладов by_agent всегда 0"

    def test_salaries_by_type_with_agent(self, api_base, admin_headers):
        """GET /api/dashboard/salaries-by-type?payment_type=all&agent_type=ФЕСТИВАЛЬ — с агентом."""
        resp = api_get(api_base, "/api/dashboard/salaries-by-type", admin_headers,
                       params={"payment_type": "all", "agent_type": "ФЕСТИВАЛЬ"})
        assert resp.status_code == 200
        data = resp.json()
        assert "by_agent" in data
        assert data["by_agent"] >= 0

    def test_salaries_all_dashboard(self, api_base, admin_headers):
        """GET /api/dashboard/salaries-all?year=2026&month=1 — все выплаты."""
        resp = api_get(api_base, "/api/dashboard/salaries-all", admin_headers,
                       params={"year": 2026, "month": 1})
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = ["total_paid", "paid_by_year", "paid_by_month",
                         "individual_by_year", "template_by_year", "supervision_by_year"]
        for key in expected_keys:
            assert key in data, f"Ожидается ключ '{key}'"

    def test_salaries_individual_dashboard(self, api_base, admin_headers):
        """GET /api/dashboard/salaries-individual?year=2026 — индивидуальные."""
        resp = api_get(api_base, "/api/dashboard/salaries-individual", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        for key in ["total_paid", "paid_by_year", "paid_by_month",
                     "by_agent", "avg_payment", "payments_count"]:
            assert key in data, f"Ожидается ключ '{key}'"

    def test_salaries_template_dashboard(self, api_base, admin_headers):
        """GET /api/dashboard/salaries-template?year=2026&agent_type=ФЕСТИВАЛЬ — шаблонные."""
        resp = api_get(api_base, "/api/dashboard/salaries-template", admin_headers,
                       params={"year": 2026, "agent_type": "ФЕСТИВАЛЬ"})
        assert resp.status_code == 200
        data = resp.json()
        for key in ["total_paid", "paid_by_year", "by_agent", "avg_payment", "payments_count"]:
            assert key in data, f"Ожидается ключ '{key}'"
        assert data["by_agent"] >= 0

    def test_salaries_salary_dashboard(self, api_base, admin_headers):
        """GET /api/dashboard/salaries-salary?year=2026&month=1 — оклады."""
        resp = api_get(api_base, "/api/dashboard/salaries-salary", admin_headers,
                       params={"year": 2026, "month": 1})
        assert resp.status_code == 200
        data = resp.json()
        for key in ["total_paid", "paid_by_year", "paid_by_month",
                     "by_project_type", "avg_salary", "employees_count"]:
            assert key in data, f"Ожидается ключ '{key}'"

    def test_salaries_supervision_dashboard(self, api_base, admin_headers):
        """GET /api/dashboard/salaries-supervision?year=2026 — надзор."""
        resp = api_get(api_base, "/api/dashboard/salaries-supervision", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        for key in ["total_paid", "paid_by_year", "paid_by_month",
                     "by_agent", "avg_payment", "payments_count"]:
            assert key in data, f"Ожидается ключ '{key}'"


# ================================================================
# GET /api/dashboard/agent-types и /contract-years
# ================================================================

class TestDashboardReferencesDeep:
    """Углублённые тесты справочных endpoints дашборда"""

    def test_agent_types_list(self, api_base, admin_headers):
        """GET /api/dashboard/agent-types — список типов агентов."""
        resp = api_get(api_base, "/api/dashboard/agent-types", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list), "Ответ должен быть списком"
        for item in data:
            assert isinstance(item, str), f"Каждый элемент — строка, получено {type(item)}"
            assert len(item) > 0, "Тип агента не должен быть пустой строкой"

    def test_contract_years_list(self, api_base, admin_headers):
        """GET /api/dashboard/contract-years — список годов из договоров."""
        resp = api_get(api_base, "/api/dashboard/contract-years", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list), "Ответ должен быть списком"
        assert len(data) > 0, "Список годов не может быть пустым (всегда есть текущий год)"
        # Текущий год и следующий обязательно включены
        from datetime import datetime
        current_year = datetime.now().year
        assert current_year in data, f"Текущий год {current_year} должен быть в списке"
        assert current_year + 1 in data, f"Следующий год {current_year + 1} должен быть в списке"
        # Годы отсортированы по убыванию
        assert data == sorted(data, reverse=True), "Годы должны быть отсортированы по убыванию"

    def test_contract_years_are_integers(self, api_base, admin_headers):
        """GET /api/dashboard/contract-years — все элементы целые числа."""
        resp = api_get(api_base, "/api/dashboard/contract-years", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        for year in data:
            assert isinstance(year, int), f"Год должен быть int, получено {type(year)}: {year}"
            assert 2000 <= year <= 2100, f"Год {year} вне разумного диапазона"
