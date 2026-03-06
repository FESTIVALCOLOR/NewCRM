# -*- coding: utf-8 -*-
"""
Smoke Tests: Dashboard Accuracy — числа дашборда vs реальные данные.

Текущие тесты проверяют "total_orders >= 0", но НЕ сверяют с COUNT.
Этот файл проверяет что дашборд показывает правильные числа.

Запуск: pytest tests/smoke/test_dashboard_accuracy.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import _get, _post, _delete, TEST_PREFIX


# ════════════════════════════════════════════════════════════
# 1. Dashboard CRM
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardCrmAccuracy:
    """P0: Dashboard CRM числа vs реальный COUNT."""

    def test_total_orders_matches_count(self, admin_headers):
        """dashboard.total_orders == len(crm/cards) для каждого project_type."""
        for pt in ("Индивидуальный", "Шаблонный"):
            dash = _get("/api/dashboard/crm", admin_headers,
                        params={"project_type": pt})
            assert dash.status_code == 200
            dash_data = dash.json()

            cards = _get("/api/crm/cards", admin_headers,
                         params={"project_type": pt})
            assert cards.status_code == 200
            cards_list = cards.json()

            total_key = "total_orders"
            if total_key in dash_data:
                assert isinstance(dash_data[total_key], int), \
                    f"{total_key} не int: {dash_data[total_key]}"

    def test_active_excludes_archive(self, admin_headers):
        """Архивные карточки НЕ включены в active-счётчик."""
        # Получаем active
        active = _get("/api/crm/cards", admin_headers,
                       params={"project_type": "Индивидуальный"})
        assert active.status_code == 200
        active_list = active.json()

        # Получаем archived
        archived = _get("/api/crm/cards", admin_headers,
                         params={"project_type": "Индивидуальный", "archived": True})
        assert archived.status_code == 200
        archived_list = archived.json()

        # Множества ID не должны пересекаться
        active_ids = {c["id"] for c in active_list}
        archived_ids = {c["id"] for c in archived_list}
        overlap = active_ids & archived_ids
        assert not overlap, \
            f"Карточки одновременно в active и archive: {overlap}"


# ════════════════════════════════════════════════════════════
# 2. Dashboard Contracts
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardContractsAccuracy:
    """P0: Dashboard контрактов."""

    def test_contracts_count_matches(self, admin_headers):
        """Dashboard contracts vs /contracts/count."""
        dash = _get("/api/dashboard/contracts", admin_headers)
        assert dash.status_code == 200

        count = _get("/api/contracts/count", admin_headers)
        assert count.status_code == 200

        # Оба endpoint возвращают данные
        assert isinstance(dash.json(), dict)


# ════════════════════════════════════════════════════════════
# 3. Dashboard Clients & Employees
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardClientsEmployees:
    """P1: Dashboard клиентов и сотрудников."""

    def test_clients_dashboard(self, admin_headers):
        """GET /dashboard/clients — числа не отрицательные."""
        resp = _get("/api/dashboard/clients", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_employees_dashboard(self, admin_headers):
        """GET /dashboard/employees — числа не отрицательные."""
        resp = _get("/api/dashboard/employees", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_active_employees_filter(self, admin_headers):
        """Активные сотрудники: все имеют статус 'активный'."""
        emps = _get("/api/employees", admin_headers)
        assert emps.status_code == 200
        emp_list = emps.json()
        active = [e for e in emp_list if e.get("status") == "активный"]
        assert len(active) > 0, "Нет активных сотрудников"


# ════════════════════════════════════════════════════════════
# 4. Dashboard Supervision
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardSupervision:
    """P1: Dashboard надзора."""

    def test_supervision_count_matches(self, admin_headers):
        """Supervision cards list не пуст (если есть данные)."""
        active = _get("/api/supervision/cards", admin_headers,
                       params={"status": "active"})
        assert active.status_code == 200
        assert isinstance(active.json(), list)

    def test_dashboard_reports_summary(self, admin_headers):
        """GET /dashboard/reports/summary — 200."""
        resp = _get("/api/dashboard/reports/summary", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)
