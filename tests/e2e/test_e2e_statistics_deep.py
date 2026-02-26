# -*- coding: utf-8 -*-
"""
E2E Tests: Углублённые тесты статистики (Этап 6)
~20 тестов — проверка всех 14 endpoints statistics_router.py
с фильтрами, пустыми данными, кварталами и проверкой структуры.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get


# ================================================================
# GET /api/statistics/dashboard
# ================================================================

class TestStatisticsDashboardDeep:
    """Углублённые тесты статистики дашборда"""

    def test_dashboard_with_year(self, api_base, admin_headers):
        """GET /api/statistics/dashboard?year=2026 — с годом."""
        resp = api_get(api_base, "/api/statistics/dashboard", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = ["total_contracts", "total_amount", "total_area",
                         "individual_count", "template_count",
                         "status_counts", "city_counts", "monthly_data",
                         "active_crm_cards", "supervision_cards"]
        for key in expected_keys:
            assert key in data, f"Ожидается ключ '{key}'"
        assert isinstance(data["status_counts"], dict)
        assert isinstance(data["city_counts"], dict)
        assert isinstance(data["monthly_data"], dict)

    def test_dashboard_with_quarter(self, api_base, admin_headers):
        """GET /api/statistics/dashboard?year=2026&quarter=1 — фильтр по кварталу."""
        resp = api_get(api_base, "/api/statistics/dashboard", admin_headers,
                       params={"year": 2026, "quarter": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_contracts"] >= 0

    def test_dashboard_with_city_filter(self, api_base, admin_headers):
        """GET /api/statistics/dashboard?year=2026&city=СПБ — фильтр по городу."""
        resp = api_get(api_base, "/api/statistics/dashboard", admin_headers,
                       params={"year": 2026, "city": "СПБ"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_contracts" in data

    def test_dashboard_with_agent_filter(self, api_base, admin_headers):
        """GET /api/statistics/dashboard?year=2026&agent_type=ФЕСТИВАЛЬ — фильтр по агенту."""
        resp = api_get(api_base, "/api/statistics/dashboard", admin_headers,
                       params={"year": 2026, "agent_type": "ФЕСТИВАЛЬ"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_contracts"] >= 0

    def test_dashboard_empty_year(self, api_base, admin_headers):
        """GET /api/statistics/dashboard?year=2099 — год без данных."""
        resp = api_get(api_base, "/api/statistics/dashboard", admin_headers,
                       params={"year": 2099})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_contracts"] == 0, "За 2099 год не должно быть договоров"
        assert data["total_amount"] == 0
        assert data["total_area"] == 0


# ================================================================
# GET /api/statistics/employees
# ================================================================

class TestStatisticsEmployeesDeep:
    """Углублённые тесты статистики сотрудников"""

    def test_employees_no_params(self, api_base, admin_headers):
        """GET /api/statistics/employees — без параметров."""
        resp = api_get(api_base, "/api/statistics/employees", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Хотя бы admin должен быть в списке
        assert len(data) > 0, "Должен быть хотя бы один активный сотрудник"
        first = data[0]
        for key in ["id", "full_name", "position", "total_stages",
                     "completed_stages", "completion_rate", "total_salary"]:
            assert key in first, f"Ожидается ключ '{key}' в записи сотрудника"

    def test_employees_with_year_and_month(self, api_base, admin_headers):
        """GET /api/statistics/employees?year=2026&month=1 — фильтр по дате."""
        resp = api_get(api_base, "/api/statistics/employees", admin_headers,
                       params={"year": 2026, "month": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


# ================================================================
# GET /api/statistics/contracts-by-period
# ================================================================

class TestStatisticsContractsByPeriodDeep:
    """Углублённые тесты договоров по периодам"""

    def test_group_by_month(self, api_base, admin_headers):
        """GET /api/statistics/contracts-by-period?year=2026&group_by=month — по месяцам."""
        resp = api_get(api_base, "/api/statistics/contracts-by-period", admin_headers,
                       params={"year": 2026, "group_by": "month"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 12, f"Ожидается 12 месяцев, получено {len(data)}"
        for m in range(1, 13):
            key = str(m)
            assert key in data, f"Ожидается ключ месяца '{key}'"
            assert "count" in data[key]
            assert "amount" in data[key]

    def test_group_by_quarter(self, api_base, admin_headers):
        """GET /api/statistics/contracts-by-period?year=2026&group_by=quarter — по кварталам."""
        resp = api_get(api_base, "/api/statistics/contracts-by-period", admin_headers,
                       params={"year": 2026, "group_by": "quarter"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4, f"Ожидается 4 квартала, получено {len(data)}"
        for q in range(1, 5):
            key = str(q)
            assert key in data, f"Ожидается ключ квартала '{key}'"
            assert "count" in data[key]
            assert "amount" in data[key]

    def test_group_by_status(self, api_base, admin_headers):
        """GET /api/statistics/contracts-by-period?year=2026&group_by=status — по статусам."""
        resp = api_get(api_base, "/api/statistics/contracts-by-period", admin_headers,
                       params={"year": 2026, "group_by": "status"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        for status_key, status_val in data.items():
            assert "count" in status_val, f"Статус '{status_key}' должен содержать 'count'"
            assert "amount" in status_val, f"Статус '{status_key}' должен содержать 'amount'"

    def test_with_project_type_filter(self, api_base, admin_headers):
        """GET /api/statistics/contracts-by-period?year=2026&group_by=month&project_type=Индивидуальный."""
        resp = api_get(api_base, "/api/statistics/contracts-by-period", admin_headers,
                       params={"year": 2026, "group_by": "month", "project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 12

    def test_empty_year(self, api_base, admin_headers):
        """GET /api/statistics/contracts-by-period?year=2099&group_by=month — пустой год."""
        resp = api_get(api_base, "/api/statistics/contracts-by-period", admin_headers,
                       params={"year": 2099, "group_by": "month"})
        assert resp.status_code == 200
        data = resp.json()
        total_count = sum(v["count"] for v in data.values())
        assert total_count == 0, "За 2099 год не должно быть договоров"


# ================================================================
# GET /api/statistics/agent-types и /cities
# ================================================================

class TestStatisticsReferencesDeep:
    """Углублённые тесты справочников статистики"""

    def test_agent_types_starts_with_all(self, api_base, admin_headers):
        """GET /api/statistics/agent-types — начинается с 'Все'."""
        resp = api_get(api_base, "/api/statistics/agent-types", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0] == "Все", f"Первый элемент должен быть 'Все', получено '{data[0]}'"

    def test_cities_starts_with_all(self, api_base, admin_headers):
        """GET /api/statistics/cities — начинается с 'Все'."""
        resp = api_get(api_base, "/api/statistics/cities", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0] == "Все"


# ================================================================
# GET /api/statistics/projects
# ================================================================

class TestStatisticsProjectsDeep:
    """Углублённые тесты статистики проектов"""

    def test_projects_individual_full(self, api_base, admin_headers):
        """GET /api/statistics/projects?project_type=Индивидуальный — полная структура."""
        resp = api_get(api_base, "/api/statistics/projects", admin_headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        for key in ["total_orders", "total_area", "active", "completed",
                     "cancelled", "overdue", "by_cities", "by_agents", "by_stages"]:
            assert key in data, f"Ожидается ключ '{key}'"
        assert data["total_orders"] >= 0
        assert isinstance(data["by_cities"], dict)
        assert isinstance(data["by_agents"], dict)
        assert isinstance(data["by_stages"], dict)

    def test_projects_template(self, api_base, admin_headers):
        """GET /api/statistics/projects?project_type=Шаблонный — шаблонные проекты."""
        resp = api_get(api_base, "/api/statistics/projects", admin_headers,
                       params={"project_type": "Шаблонный"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_orders" in data
        assert data["total_orders"] >= 0

    def test_projects_with_year_and_city(self, api_base, admin_headers):
        """GET /api/statistics/projects?project_type=Индивидуальный&year=2026&city=СПБ."""
        resp = api_get(api_base, "/api/statistics/projects", admin_headers,
                       params={"project_type": "Индивидуальный", "year": 2026, "city": "СПБ"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_orders"] >= 0

    def test_projects_with_quarter(self, api_base, admin_headers):
        """GET /api/statistics/projects?project_type=Индивидуальный&year=2026&quarter=1."""
        resp = api_get(api_base, "/api/statistics/projects", admin_headers,
                       params={"project_type": "Индивидуальный", "year": 2026, "quarter": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_orders"] >= 0


# ================================================================
# GET /api/statistics/supervision и /supervision/filtered
# ================================================================

class TestStatisticsSupervisionDeep:
    """Углублённые тесты статистики надзора"""

    def test_supervision_full_structure(self, api_base, admin_headers):
        """GET /api/statistics/supervision — полная структура ответа."""
        resp = api_get(api_base, "/api/statistics/supervision", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        for key in ["total_orders", "total_area", "active", "completed",
                     "cancelled", "overdue", "by_cities", "by_agents", "by_stages"]:
            assert key in data, f"Ожидается ключ '{key}'"
        assert isinstance(data["by_stages"], dict)

    def test_supervision_with_year(self, api_base, admin_headers):
        """GET /api/statistics/supervision?year=2026 — по году."""
        resp = api_get(api_base, "/api/statistics/supervision", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_orders"] >= 0

    def test_supervision_filtered_full(self, api_base, admin_headers):
        """GET /api/statistics/supervision/filtered — полная структура."""
        resp = api_get(api_base, "/api/statistics/supervision/filtered", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_count" in data
        assert "total_area" in data
        assert "cards" in data
        assert isinstance(data["cards"], list)

    def test_supervision_filtered_with_city(self, api_base, admin_headers):
        """GET /api/statistics/supervision/filtered?city=СПБ — фильтр по городу."""
        resp = api_get(api_base, "/api/statistics/supervision/filtered", admin_headers,
                       params={"city": "СПБ"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] >= 0


# ================================================================
# GET /api/statistics/crm и /crm/filtered
# ================================================================

class TestStatisticsCrmDeep:
    """Углублённые тесты статистики CRM"""

    def test_crm_default_params(self, api_base, admin_headers):
        """GET /api/statistics/crm — параметры по умолчанию."""
        resp = api_get(api_base, "/api/statistics/crm", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            first = data[0]
            for key in ["id", "contract_id", "column_name", "contract_number", "address", "area"]:
                assert key in first, f"CRM-карточка должна содержать '{key}'"

    def test_crm_filtered_year_period(self, api_base, admin_headers):
        """GET /api/statistics/crm/filtered?project_type=Индивидуальный&period=За год&year=2026."""
        resp = api_get(api_base, "/api/statistics/crm/filtered", admin_headers,
                       params={"project_type": "Индивидуальный", "period": "За год", "year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            first = data[0]
            assert "is_approved" in first, "Фильтрованная CRM должна содержать 'is_approved'"

    def test_crm_filtered_quarter_period(self, api_base, admin_headers):
        """GET /api/statistics/crm/filtered с кварталом."""
        resp = api_get(api_base, "/api/statistics/crm/filtered", admin_headers,
                       params={"project_type": "Индивидуальный", "period": "За квартал",
                               "year": 2026, "quarter": 1})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_crm_filtered_month_period(self, api_base, admin_headers):
        """GET /api/statistics/crm/filtered с месяцем."""
        resp = api_get(api_base, "/api/statistics/crm/filtered", admin_headers,
                       params={"project_type": "Индивидуальный", "period": "За месяц",
                               "year": 2026, "month": 1})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ================================================================
# GET /api/statistics/approvals
# ================================================================

class TestStatisticsApprovalsDeep:
    """Углублённые тесты статистики согласований"""

    def test_approvals_year(self, api_base, admin_headers):
        """GET /api/statistics/approvals?project_type=Индивидуальный&period=За год&year=2026."""
        resp = api_get(api_base, "/api/statistics/approvals", admin_headers,
                       params={"project_type": "Индивидуальный", "period": "За год", "year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Все элементы должны быть is_approved == True
        for item in data:
            assert item.get("is_approved") is True, "Все записи approvals должны быть согласованы"

    def test_approvals_empty_year(self, api_base, admin_headers):
        """GET /api/statistics/approvals за 2099 — пустой результат."""
        resp = api_get(api_base, "/api/statistics/approvals", admin_headers,
                       params={"project_type": "Индивидуальный", "period": "За год", "year": 2099})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 0, "За 2099 год не должно быть согласований"


# ================================================================
# GET /api/statistics/general
# ================================================================

class TestStatisticsGeneralDeep:
    """Углублённые тесты общей статистики"""

    def test_general_full_structure(self, api_base, admin_headers):
        """GET /api/statistics/general?year=2026 — полная структура."""
        resp = api_get(api_base, "/api/statistics/general", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = ["total_orders", "active", "completed", "cancelled",
                         "individual_count", "template_count",
                         "total_area", "total_amount",
                         "active_employees", "total_payments",
                         "paid_payments", "pending_payments"]
        for key in expected_keys:
            assert key in data, f"Ожидается ключ '{key}'"

    def test_general_with_quarter(self, api_base, admin_headers):
        """GET /api/statistics/general?year=2026&quarter=1 — по кварталу."""
        resp = api_get(api_base, "/api/statistics/general", admin_headers,
                       params={"year": 2026, "quarter": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_orders"] >= 0

    def test_general_empty_year(self, api_base, admin_headers):
        """GET /api/statistics/general?year=2099 — пустая статистика."""
        resp = api_get(api_base, "/api/statistics/general", admin_headers,
                       params={"year": 2099})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_orders"] == 0
        assert data["total_amount"] == 0


# ================================================================
# GET /api/statistics/funnel
# ================================================================

class TestStatisticsFunnelDeep:
    """Углублённые тесты воронки"""

    def test_funnel_no_params(self, api_base, admin_headers):
        """GET /api/statistics/funnel — без параметров."""
        resp = api_get(api_base, "/api/statistics/funnel", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "funnel" in data, "Ожидается ключ 'funnel'"
        assert "total" in data, "Ожидается ключ 'total'"
        assert isinstance(data["funnel"], dict)
        assert data["total"] >= 0
        # total == сумма значений funnel
        funnel_sum = sum(data["funnel"].values())
        assert data["total"] == funnel_sum, "total должен равняться сумме значений воронки"

    def test_funnel_with_project_type(self, api_base, admin_headers):
        """GET /api/statistics/funnel?project_type=Индивидуальный — по типу проекта."""
        resp = api_get(api_base, "/api/statistics/funnel", admin_headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert "funnel" in data
        assert data["total"] >= 0

    def test_funnel_with_year(self, api_base, admin_headers):
        """GET /api/statistics/funnel?year=2026 — по году."""
        resp = api_get(api_base, "/api/statistics/funnel", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert "funnel" in data


# ================================================================
# GET /api/statistics/executor-load
# ================================================================

class TestStatisticsExecutorLoadDeep:
    """Углублённые тесты нагрузки исполнителей"""

    def test_executor_load_no_params(self, api_base, admin_headers):
        """GET /api/statistics/executor-load — без параметров."""
        resp = api_get(api_base, "/api/statistics/executor-load", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            first = data[0]
            assert "name" in first, "Ожидается ключ 'name'"
            assert "active_stages" in first, "Ожидается ключ 'active_stages'"
            assert first["active_stages"] >= 0

    def test_executor_load_with_year(self, api_base, admin_headers):
        """GET /api/statistics/executor-load?year=2026 — по году."""
        resp = api_get(api_base, "/api/statistics/executor-load", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_executor_load_limit_15(self, api_base, admin_headers):
        """GET /api/statistics/executor-load — не более 15 записей."""
        resp = api_get(api_base, "/api/statistics/executor-load", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 15, f"Нагрузка ограничена 15 записями, получено {len(data)}"
