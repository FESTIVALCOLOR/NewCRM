# -*- coding: utf-8 -*-
"""
E2E Tests: Дашборд и статистика
8 тестов — проверка всех endpoints статистики и дашборда.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get


class TestDashboard:
    """Тесты дашборда"""

    def test_clients_dashboard_stats(self, api_base, admin_headers):
        """Статистика клиентов"""
        resp = api_get(api_base, "/api/dashboard/clients", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Проверяем наличие ключей ответа
        assert "total_clients" in data, "Ожидается ключ total_clients"
        assert "total_individual" in data, "Ожидается ключ total_individual"
        assert "total_legal" in data, "Ожидается ключ total_legal"
        # Числовые значения — неотрицательные целые
        assert isinstance(data["total_clients"], (int, float))
        assert data["total_clients"] >= 0
        assert isinstance(data["total_individual"], (int, float))
        assert isinstance(data["total_legal"], (int, float))

    def test_contracts_dashboard_stats(self, api_base, admin_headers):
        """Статистика договоров"""
        resp = api_get(api_base, "/api/dashboard/contracts", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Проверяем структуру ответа: индивидуальные и шаблонные заказы
        assert "individual_orders" in data, "Ожидается ключ individual_orders"
        assert "individual_area" in data, "Ожидается ключ individual_area"
        assert "template_orders" in data, "Ожидается ключ template_orders"
        assert "template_area" in data, "Ожидается ключ template_area"
        # Числовые значения — неотрицательные
        assert isinstance(data["individual_orders"], (int, float))
        assert data["individual_orders"] >= 0
        assert isinstance(data["template_orders"], (int, float))
        assert data["template_orders"] >= 0

    def test_crm_dashboard_stats(self, api_base, admin_headers):
        """Статистика CRM"""
        resp = api_get(api_base, "/api/dashboard/crm", admin_headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Проверяем обязательные ключи CRM-дашборда
        assert "total_orders" in data, "Ожидается ключ total_orders"
        assert "active_orders" in data, "Ожидается ключ active_orders"
        assert "archive_orders" in data, "Ожидается ключ archive_orders"
        # Значения должны быть неотрицательными числами
        assert data["active_orders"] >= 0, "active_orders не может быть отрицательным"
        assert data["archive_orders"] >= 0, "archive_orders не может быть отрицательным"
        assert data["total_orders"] >= 0, "total_orders не может быть отрицательным"

    def test_employees_dashboard_stats(self, api_base, admin_headers):
        """Статистика сотрудников"""
        resp = api_get(api_base, "/api/dashboard/employees", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Проверяем ключи дашборда сотрудников
        assert "active_employees" in data, "Ожидается ключ active_employees"
        assert "reserve_employees" in data, "Ожидается ключ reserve_employees"
        # active_employees — неотрицательное целое
        assert isinstance(data["active_employees"], (int, float))
        assert data["active_employees"] >= 0
        # На сервере есть хотя бы admin
        assert data["active_employees"] > 0, "Должен быть хотя бы 1 активный сотрудник (admin)"

    def test_salaries_dashboard_stats(self, api_base, admin_headers):
        """Статистика зарплат"""
        resp = api_get(api_base, "/api/dashboard/salaries", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Проверяем ключи дашборда зарплат
        assert "total_paid" in data, "Ожидается ключ total_paid"
        assert "paid_by_year" in data, "Ожидается ключ paid_by_year"
        assert "paid_by_month" in data, "Ожидается ключ paid_by_month"
        # Суммы — числа >= 0
        assert isinstance(data["total_paid"], (int, float))
        assert data["total_paid"] >= 0

    def test_supervision_statistics(self, api_base, admin_headers):
        """Статистика надзора"""
        resp = api_get(api_base, "/api/statistics/supervision", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Проверяем ключи статистики надзора
        assert "total_orders" in data, "Ожидается ключ total_orders"
        assert "active" in data, "Ожидается ключ active"
        assert "completed" in data, "Ожидается ключ completed"
        assert "by_cities" in data, "Ожидается ключ by_cities"
        assert "by_agents" in data, "Ожидается ключ by_agents"
        # Числа неотрицательные
        assert data["total_orders"] >= 0
        assert isinstance(data["by_cities"], dict)
        assert isinstance(data["by_agents"], dict)

    def test_contracts_by_period(self, api_base, admin_headers):
        """Статистика договоров по периодам"""
        resp = api_get(
            api_base,
            "/api/statistics/contracts-by-period",
            admin_headers,
            params={"year": 2026, "group_by": "month"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # group_by=month: ожидаем 12 ключей (1..12) с count и amount
        assert len(data) == 12, f"Ожидается 12 месяцев, получено {len(data)}"
        for month_num in range(1, 13):
            key = str(month_num)
            assert key in data, f"Ожидается ключ месяца '{key}'"
            assert "count" in data[key]
            assert "amount" in data[key]

    def test_general_statistics(self, api_base, admin_headers):
        """Общая статистика"""
        resp = api_get(
            api_base,
            "/api/statistics/general",
            admin_headers,
            params={"year": 2026}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        # Проверяем ключи общей статистики
        assert "total_orders" in data, "Ожидается ключ total_orders"
        assert "active" in data, "Ожидается ключ active"
        assert "completed" in data, "Ожидается ключ completed"
        assert "cancelled" in data, "Ожидается ключ cancelled"
        assert "active_employees" in data, "Ожидается ключ active_employees"
        assert "total_payments" in data, "Ожидается ключ total_payments"
        # Числа неотрицательные
        assert data["total_orders"] >= 0
        assert data["active_employees"] >= 0
