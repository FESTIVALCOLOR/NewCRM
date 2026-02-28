# -*- coding: utf-8 -*-
"""
E2E Tests: Отчёты и Статистика — 6 новых endpoints.
Проверка всех endpoints аналитики для обновлённой страницы ReportsTab.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get


class TestReportsSummary:
    """GET /api/dashboard/reports/summary — KPI-метрики"""

    def test_summary_returns_200(self, api_base, admin_headers):
        """Базовый вызов без фильтров"""
        resp = api_get(api_base, "/api/dashboard/reports/summary", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_summary_has_client_keys(self, api_base, admin_headers):
        """Ответ содержит ключи клиентской статистики"""
        data = api_get(api_base, "/api/dashboard/reports/summary", admin_headers).json()
        for key in ("total_clients", "new_clients", "returning_clients"):
            assert key in data, f"Ожидается ключ {key}"
            assert isinstance(data[key], (int, float)), f"{key} должен быть числом"
            assert data[key] >= 0, f"{key} не может быть отрицательным"

    def test_summary_has_contract_keys(self, api_base, admin_headers):
        """Ответ содержит ключи договоров"""
        data = api_get(api_base, "/api/dashboard/reports/summary", admin_headers).json()
        for key in ("total_contracts", "total_amount", "avg_amount", "total_area", "avg_area"):
            assert key in data, f"Ожидается ключ {key}"
            assert isinstance(data[key], (int, float)), f"{key} должен быть числом"

    def test_summary_has_by_agent(self, api_base, admin_headers):
        """Ответ содержит массив by_agent с данными по агентам"""
        data = api_get(api_base, "/api/dashboard/reports/summary", admin_headers).json()
        assert "by_agent" in data, "Ожидается ключ by_agent"
        assert isinstance(data["by_agent"], list), "by_agent должен быть списком"
        for agent in data["by_agent"]:
            assert "agent_name" in agent, "Каждый агент должен содержать agent_name"
            assert "agent_color" in agent, "Каждый агент должен содержать agent_color"

    def test_summary_has_trends(self, api_base, admin_headers):
        """Ответ содержит тренды"""
        data = api_get(api_base, "/api/dashboard/reports/summary", admin_headers).json()
        for key in ("trend_clients", "trend_contracts", "trend_amount"):
            assert key in data, f"Ожидается ключ {key}"

    def test_summary_with_year_filter(self, api_base, admin_headers):
        """Фильтр по году"""
        resp = api_get(api_base, "/api/dashboard/reports/summary", admin_headers,
                       params={"year": 2025})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "total_clients" in data

    def test_summary_with_quarter_filter(self, api_base, admin_headers):
        """Фильтр по кварталу"""
        resp = api_get(api_base, "/api/dashboard/reports/summary", admin_headers,
                       params={"year": 2025, "quarter": 1})
        assert resp.status_code == 200

    def test_summary_with_agent_type_filter(self, api_base, admin_headers):
        """Фильтр по типу агента"""
        resp = api_get(api_base, "/api/dashboard/reports/summary", admin_headers,
                       params={"agent_type": "Фестиваль"})
        assert resp.status_code == 200

    def test_summary_with_project_type_filter(self, api_base, admin_headers):
        """Фильтр по типу проекта"""
        resp = api_get(api_base, "/api/dashboard/reports/summary", admin_headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200


class TestReportsClientsDynamics:
    """GET /api/dashboard/reports/clients-dynamics — динамика клиентов"""

    def test_clients_dynamics_returns_200(self, api_base, admin_headers):
        """Базовый вызов"""
        resp = api_get(api_base, "/api/dashboard/reports/clients-dynamics", admin_headers)
        assert resp.status_code == 200

    def test_clients_dynamics_is_list(self, api_base, admin_headers):
        """Ответ — список периодов"""
        data = api_get(api_base, "/api/dashboard/reports/clients-dynamics", admin_headers).json()
        assert isinstance(data, list), "Ожидается список периодов"

    def test_clients_dynamics_entry_keys(self, api_base, admin_headers):
        """Каждый элемент содержит нужные ключи"""
        data = api_get(api_base, "/api/dashboard/reports/clients-dynamics", admin_headers).json()
        if data:  # Может быть пустым если нет данных
            entry = data[0]
            assert "period" in entry, "Ожидается ключ period"
            for key in ("new_clients", "returning_clients", "individual", "legal"):
                assert key in entry, f"Ожидается ключ {key}"

    def test_clients_dynamics_with_year(self, api_base, admin_headers):
        """Фильтр по году"""
        resp = api_get(api_base, "/api/dashboard/reports/clients-dynamics", admin_headers,
                       params={"year": 2025})
        assert resp.status_code == 200

    def test_clients_dynamics_quarterly_granularity(self, api_base, admin_headers):
        """Квартальная гранулярность"""
        resp = api_get(api_base, "/api/dashboard/reports/clients-dynamics", admin_headers,
                       params={"granularity": "quarter"})
        assert resp.status_code == 200


class TestReportsContractsDynamics:
    """GET /api/dashboard/reports/contracts-dynamics — динамика договоров"""

    def test_contracts_dynamics_returns_200(self, api_base, admin_headers):
        """Базовый вызов"""
        resp = api_get(api_base, "/api/dashboard/reports/contracts-dynamics", admin_headers)
        assert resp.status_code == 200

    def test_contracts_dynamics_is_list(self, api_base, admin_headers):
        """Ответ — список периодов"""
        data = api_get(api_base, "/api/dashboard/reports/contracts-dynamics", admin_headers).json()
        assert isinstance(data, list), "Ожидается список периодов"

    def test_contracts_dynamics_entry_keys(self, api_base, admin_headers):
        """Каждый элемент содержит нужные ключи"""
        data = api_get(api_base, "/api/dashboard/reports/contracts-dynamics", admin_headers).json()
        if data:
            entry = data[0]
            assert "period" in entry
            for key in ("individual_count", "template_count", "supervision_count", "total_amount"):
                assert key in entry, f"Ожидается ключ {key}"

    def test_contracts_dynamics_with_filters(self, api_base, admin_headers):
        """Фильтр по году и агенту"""
        resp = api_get(api_base, "/api/dashboard/reports/contracts-dynamics", admin_headers,
                       params={"year": 2025, "agent_type": "Фестиваль"})
        assert resp.status_code == 200


class TestReportsCRMAnalytics:
    """GET /api/dashboard/reports/crm-analytics — CRM аналитика"""

    def test_crm_analytics_individual(self, api_base, admin_headers):
        """CRM аналитика для индивидуальных проектов"""
        resp = api_get(api_base, "/api/dashboard/reports/crm-analytics", admin_headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_crm_analytics_template(self, api_base, admin_headers):
        """CRM аналитика для шаблонных проектов"""
        resp = api_get(api_base, "/api/dashboard/reports/crm-analytics", admin_headers,
                       params={"project_type": "Шаблонный"})
        assert resp.status_code == 200

    def test_crm_analytics_has_funnel(self, api_base, admin_headers):
        """Ответ содержит воронку"""
        data = api_get(api_base, "/api/dashboard/reports/crm-analytics", admin_headers).json()
        assert "funnel" in data, "Ожидается ключ funnel"
        assert isinstance(data["funnel"], list), "funnel должен быть списком"

    def test_crm_analytics_has_on_time_stats(self, api_base, admin_headers):
        """Ответ содержит статистику по срокам"""
        data = api_get(api_base, "/api/dashboard/reports/crm-analytics", admin_headers).json()
        assert "on_time_stats" in data, "Ожидается ключ on_time_stats"
        on_time = data["on_time_stats"]
        assert isinstance(on_time, dict)
        for key in ("projects_pct", "stages_pct", "avg_deviation_days"):
            assert key in on_time, f"Ожидается ключ {key} в on_time_stats"

    def test_crm_analytics_has_stage_durations(self, api_base, admin_headers):
        """Ответ содержит время стадий"""
        data = api_get(api_base, "/api/dashboard/reports/crm-analytics", admin_headers).json()
        assert "stage_durations" in data, "Ожидается ключ stage_durations"
        assert isinstance(data["stage_durations"], list)

    def test_crm_analytics_has_paused_count(self, api_base, admin_headers):
        """Ответ содержит количество на паузе"""
        data = api_get(api_base, "/api/dashboard/reports/crm-analytics", admin_headers).json()
        assert "paused_count" in data, "Ожидается ключ paused_count"
        assert isinstance(data["paused_count"], (int, float))

    def test_crm_analytics_with_year_filter(self, api_base, admin_headers):
        """Фильтр по году"""
        resp = api_get(api_base, "/api/dashboard/reports/crm-analytics", admin_headers,
                       params={"year": 2025})
        assert resp.status_code == 200


class TestReportsSupervisionAnalytics:
    """GET /api/dashboard/reports/supervision-analytics — авторский надзор"""

    def test_supervision_analytics_returns_200(self, api_base, admin_headers):
        """Базовый вызов"""
        resp = api_get(api_base, "/api/dashboard/reports/supervision-analytics", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_supervision_has_totals(self, api_base, admin_headers):
        """Ответ содержит общие показатели"""
        data = api_get(api_base, "/api/dashboard/reports/supervision-analytics", admin_headers).json()
        for key in ("total", "active"):
            assert key in data, f"Ожидается ключ {key}"

    def test_supervision_has_stages(self, api_base, admin_headers):
        """Ответ содержит стадии закупок"""
        data = api_get(api_base, "/api/dashboard/reports/supervision-analytics", admin_headers).json()
        assert "stages" in data, "Ожидается ключ stages"
        assert isinstance(data["stages"], list)

    def test_supervision_has_by_agent(self, api_base, admin_headers):
        """Ответ содержит разбивку по агентам"""
        data = api_get(api_base, "/api/dashboard/reports/supervision-analytics", admin_headers).json()
        assert "by_agent" in data, "Ожидается ключ by_agent"
        assert isinstance(data["by_agent"], list)

    def test_supervision_has_by_city(self, api_base, admin_headers):
        """Ответ содержит разбивку по городам"""
        data = api_get(api_base, "/api/dashboard/reports/supervision-analytics", admin_headers).json()
        assert "by_city" in data, "Ожидается ключ by_city"
        assert isinstance(data["by_city"], list)

    def test_supervision_has_by_project_type(self, api_base, admin_headers):
        """Ответ содержит разбивку по типам проектов"""
        data = api_get(api_base, "/api/dashboard/reports/supervision-analytics", admin_headers).json()
        assert "by_project_type" in data, "Ожидается ключ by_project_type"
        assert isinstance(data["by_project_type"], dict)

    def test_supervision_has_budget(self, api_base, admin_headers):
        """Ответ содержит бюджетные данные"""
        data = api_get(api_base, "/api/dashboard/reports/supervision-analytics", admin_headers).json()
        assert "budget" in data, "Ожидается ключ budget"
        budget = data["budget"]
        assert isinstance(budget, dict)

    def test_supervision_has_defects(self, api_base, admin_headers):
        """Ответ содержит дефекты"""
        data = api_get(api_base, "/api/dashboard/reports/supervision-analytics", admin_headers).json()
        assert "defects" in data, "Ожидается ключ defects"

    def test_supervision_with_year_filter(self, api_base, admin_headers):
        """Фильтр по году"""
        resp = api_get(api_base, "/api/dashboard/reports/supervision-analytics", admin_headers,
                       params={"year": 2025})
        assert resp.status_code == 200


class TestReportsDistribution:
    """GET /api/dashboard/reports/distribution — распределение по измерению"""

    def test_distribution_by_city(self, api_base, admin_headers):
        """Распределение по городам"""
        resp = api_get(api_base, "/api/dashboard/reports/distribution", admin_headers,
                       params={"dimension": "city"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_distribution_by_agent(self, api_base, admin_headers):
        """Распределение по агентам"""
        resp = api_get(api_base, "/api/dashboard/reports/distribution", admin_headers,
                       params={"dimension": "agent"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_distribution_by_project_type(self, api_base, admin_headers):
        """Распределение по типам проектов"""
        resp = api_get(api_base, "/api/dashboard/reports/distribution", admin_headers,
                       params={"dimension": "project_type"})
        assert resp.status_code == 200

    def test_distribution_by_subtype(self, api_base, admin_headers):
        """Распределение по подтипам"""
        resp = api_get(api_base, "/api/dashboard/reports/distribution", admin_headers,
                       params={"dimension": "subtype"})
        assert resp.status_code == 200

    def test_distribution_entry_has_name_and_count(self, api_base, admin_headers):
        """Каждая запись содержит name и count"""
        data = api_get(api_base, "/api/dashboard/reports/distribution", admin_headers,
                       params={"dimension": "city"}).json()
        if data:
            entry = data[0]
            assert "name" in entry, "Ожидается ключ name"
            assert "count" in entry, "Ожидается ключ count"

    def test_distribution_with_year_filter(self, api_base, admin_headers):
        """Фильтр по году"""
        resp = api_get(api_base, "/api/dashboard/reports/distribution", admin_headers,
                       params={"dimension": "agent", "year": 2025})
        assert resp.status_code == 200

    def test_distribution_missing_dimension(self, api_base, admin_headers):
        """Без указания dimension — ошибка 422"""
        resp = api_get(api_base, "/api/dashboard/reports/distribution", admin_headers)
        assert resp.status_code == 422, "Без dimension должен быть 422"
