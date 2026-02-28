# -*- coding: utf-8 -*-
"""
E2E Tests: Статистика (расширенная)
9 тестов — непокрытые endpoints статистики.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get


class TestStatistics:
    """Тесты расширенной статистики"""

    def test_dashboard_statistics(self, api_base, admin_headers):
        """GET /api/statistics/dashboard — статистика дашборда"""
        resp = api_get(api_base, "/api/statistics/dashboard", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Проверяем основные ключи статистики дашборда
        assert "total_contracts" in data, "Ожидается ключ total_contracts"
        assert "total_amount" in data, "Ожидается ключ total_amount"
        assert "total_area" in data, "Ожидается ключ total_area"
        assert "status_counts" in data, "Ожидается ключ status_counts"
        assert isinstance(data["total_contracts"], (int, float))
        assert data["total_contracts"] >= 0
        assert isinstance(data["status_counts"], dict)

    def test_employees_statistics(self, api_base, admin_headers):
        """GET /api/statistics/employees — статистика по сотрудникам"""
        resp = api_get(api_base, "/api/statistics/employees", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Если список не пустой — каждый элемент должен содержать id и full_name
        if data:
            first = data[0]
            assert "id" in first, "Каждый сотрудник должен иметь поле id"
            assert "full_name" in first, "Каждый сотрудник должен иметь поле full_name"
            assert "total_stages" in first, "Каждый сотрудник должен иметь поле total_stages"
            assert "completed_stages" in first, "Каждый сотрудник должен иметь поле completed_stages"

    def test_agent_types_statistics(self, api_base, admin_headers):
        """GET /api/statistics/agent-types — список типов агентов"""
        resp = api_get(api_base, "/api/statistics/agent-types", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Первый элемент всегда 'Все'
        if data:
            assert data[0] == "Все", f"Первый элемент должен быть 'Все', получено '{data[0]}'"
            # Все элементы — строки
            for item in data:
                assert isinstance(item, str), f"Каждый тип агента должен быть строкой, получено {type(item)}"

    def test_cities_statistics(self, api_base, admin_headers):
        """GET /api/statistics/cities — список городов"""
        resp = api_get(api_base, "/api/statistics/cities", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Первый элемент всегда 'Все'
        if data:
            assert data[0] == "Все", f"Первый элемент должен быть 'Все', получено '{data[0]}'"
            # Все элементы — строки
            for item in data:
                assert isinstance(item, str), f"Каждый город должен быть строкой, получено {type(item)}"

    def test_projects_statistics(self, api_base, admin_headers):
        """GET /api/statistics/projects — статистика проектов"""
        resp = api_get(api_base, "/api/statistics/projects", admin_headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Проверяем ключи статистики проектов
        assert "total_orders" in data, "Ожидается ключ total_orders"
        assert "active" in data, "Ожидается ключ active"
        assert "completed" in data, "Ожидается ключ completed"
        assert "cancelled" in data, "Ожидается ключ cancelled"
        assert "by_cities" in data, "Ожидается ключ by_cities"
        assert "by_agents" in data, "Ожидается ключ by_agents"
        assert data["total_orders"] >= 0
        assert isinstance(data["by_cities"], dict)
        assert isinstance(data["by_agents"], dict)

    def test_supervision_filtered_statistics(self, api_base, admin_headers):
        """GET /api/statistics/supervision/filtered — фильтрованная статистика надзора"""
        resp = api_get(api_base, "/api/statistics/supervision/filtered", admin_headers,
                       params={"year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Проверяем ключи отфильтрованной статистики надзора
        assert "total_count" in data, "Ожидается ключ total_count"
        assert "total_area" in data, "Ожидается ключ total_area"
        assert "cards" in data, "Ожидается ключ cards"
        assert isinstance(data["cards"], list)
        assert data["total_count"] >= 0
        # Если карточки есть — проверяем структуру первой
        if data["cards"]:
            card = data["cards"][0]
            assert "id" in card, "Карточка надзора должна иметь поле id"
            assert "contract_number" in card, "Карточка надзора должна иметь поле contract_number"

    def test_crm_statistics(self, api_base, admin_headers):
        """GET /api/statistics/crm — статистика CRM"""
        resp = api_get(api_base, "/api/statistics/crm", admin_headers,
                       params={"project_type": "Индивидуальный", "period": "year", "year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Если список не пустой — каждый элемент должен иметь id и column_name
        if data:
            first = data[0]
            assert "id" in first, "CRM-карточка должна иметь поле id"
            assert "column_name" in first, "CRM-карточка должна иметь поле column_name"
            assert "contract_id" in first, "CRM-карточка должна иметь поле contract_id"

    def test_crm_filtered_statistics(self, api_base, admin_headers):
        """GET /api/statistics/crm/filtered — статистика CRM с фильтрами"""
        resp = api_get(api_base, "/api/statistics/crm/filtered", admin_headers,
                       params={"project_type": "Индивидуальный", "period": "year", "year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Если список не пустой — проверяем структуру элемента
        if data:
            first = data[0]
            assert "id" in first, "CRM-карточка должна иметь поле id"
            assert "contract_id" in first, "CRM-карточка должна иметь поле contract_id"
            assert "column_name" in first, "CRM-карточка должна иметь поле column_name"
            assert "is_approved" in first, "CRM-карточка должна иметь поле is_approved"

    def test_approvals_statistics(self, api_base, admin_headers):
        """GET /api/statistics/approvals — статистика согласований"""
        resp = api_get(api_base, "/api/statistics/approvals", admin_headers,
                       params={"project_type": "Индивидуальный", "period": "year", "year": 2026})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Если список не пустой — каждый элемент должен иметь id и is_approved=True
        if data:
            first = data[0]
            assert "id" in first, "Запись согласования должна иметь поле id"
            assert "contract_id" in first, "Запись согласования должна иметь поле contract_id"
            assert "is_approved" in first, "Запись согласования должна иметь поле is_approved"
            assert first["is_approved"] is True, "Все записи в approvals должны быть согласованы"
