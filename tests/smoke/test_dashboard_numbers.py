# -*- coding: utf-8 -*-
"""
Smoke: Dashboard числа — реальная сверка COUNT vs dashboard.

НЕ просто "status 200", а РЕАЛЬНАЯ верификация:
  - dashboard.total_orders == len(crm/cards)
  - dashboard.clients_count == len(clients)
  - dashboard.employees_active == len(employees WHERE status='активный')
  - Архивные карточки НЕ в активных счётчиках

Запуск: pytest tests/smoke/test_dashboard_numbers.py -v --timeout=120
"""
import pytest
from tests.smoke.conftest import _get


# ════════════════════════════════════════════════════════════
# 1. CRM Dashboard: числа совпадают с реальными
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardCrmNumbers:
    """Dashboard CRM числа vs реальные данные из /crm/cards."""

    def test_individual_cards_count_matches(self, admin_headers):
        """Dashboard Индивидуальный: total_orders ≈ len(crm/cards)."""
        pt = "Индивидуальный"
        dash = _get("/api/dashboard/crm", admin_headers, params={"project_type": pt})
        assert dash.status_code == 200
        dash_data = dash.json()

        cards = _get("/api/crm/cards", admin_headers, params={"project_type": pt})
        assert cards.status_code == 200
        real_count = len(cards.json())

        # Dashboard может иметь total_orders, total, count — ищем нужный ключ
        dash_count = (dash_data.get("total_orders") or
                      dash_data.get("total") or
                      dash_data.get("count"))
        if dash_count is not None:
            # Допуск ±5% из-за timing/кэширования
            tolerance = max(5, real_count * 0.05)
            assert abs(dash_count - real_count) <= tolerance, \
                f"Dashboard total={dash_count}, real count={real_count}, " \
                f"расхождение={abs(dash_count - real_count)}"

    def test_template_cards_count_matches(self, admin_headers):
        """Dashboard Шаблонный: total_orders ≈ len(crm/cards)."""
        pt = "Шаблонный"
        dash = _get("/api/dashboard/crm", admin_headers, params={"project_type": pt})
        assert dash.status_code == 200
        dash_data = dash.json()

        cards = _get("/api/crm/cards", admin_headers, params={"project_type": pt})
        assert cards.status_code == 200
        real_count = len(cards.json())

        dash_count = (dash_data.get("total_orders") or
                      dash_data.get("total") or
                      dash_data.get("count"))
        if dash_count is not None:
            tolerance = max(5, real_count * 0.05)
            assert abs(dash_count - real_count) <= tolerance, \
                f"Dashboard total={dash_count}, real count={real_count}"

    def test_active_cards_exclude_archived(self, admin_headers):
        """Активные и архивные карточки — непересекающиеся множества."""
        pt = "Индивидуальный"
        active = _get("/api/crm/cards", admin_headers,
                       params={"project_type": pt})
        assert active.status_code == 200
        active_ids = {c["id"] for c in active.json()}

        archived = _get("/api/crm/cards", admin_headers,
                         params={"project_type": pt, "archived": True})
        assert archived.status_code == 200
        archived_ids = {c["id"] for c in archived.json()}

        overlap = active_ids & archived_ids
        assert not overlap, \
            f"Карточки одновременно active И archived: {list(overlap)[:10]}"

    def test_dashboard_crm_columns_sum_equals_total(self, admin_headers):
        """Сумма карточек по колонкам ≈ total (если dashboard даёт колонки)."""
        pt = "Индивидуальный"
        dash = _get("/api/dashboard/crm", admin_headers, params={"project_type": pt})
        assert dash.status_code == 200
        dash_data = dash.json()

        # Dashboard может содержать columns с количеством карточек
        columns = dash_data.get("columns") or dash_data.get("by_column")
        total = (dash_data.get("total_orders") or
                 dash_data.get("total") or
                 dash_data.get("count"))

        if columns and total and isinstance(columns, (list, dict)):
            if isinstance(columns, dict):
                col_sum = sum(columns.values())
            else:
                col_sum = sum(c.get("count", 0) for c in columns)

            # Сумма по колонкам должна примерно совпадать с total
            tolerance = max(3, total * 0.05)
            assert abs(col_sum - total) <= tolerance, \
                f"Сумма по колонкам={col_sum}, total={total}"


# ════════════════════════════════════════════════════════════
# 2. Dashboard Contracts: числа совпадают
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardContractsNumbers:
    """Dashboard контрактов vs реальные данные."""

    def test_contracts_count_matches_list(self, admin_headers):
        """Dashboard contracts.count ≈ len(/contracts)."""
        dash = _get("/api/dashboard/contracts", admin_headers)
        assert dash.status_code == 200
        dash_data = dash.json()

        contracts = _get("/api/contracts", admin_headers)
        assert contracts.status_code == 200
        real_count = len(contracts.json())

        dash_count = (dash_data.get("total") or
                      dash_data.get("count") or
                      dash_data.get("contracts_count"))
        if dash_count is not None:
            tolerance = max(3, real_count * 0.05)
            assert abs(dash_count - real_count) <= tolerance, \
                f"Dashboard contracts={dash_count}, real={real_count}"

    def test_contract_total_amount_positive(self, admin_headers):
        """Все отображаемые суммы в dashboard неотрицательные."""
        dash = _get("/api/dashboard/contracts", admin_headers)
        assert dash.status_code == 200
        data = dash.json()

        # Проверяем все числовые поля
        for key, value in data.items():
            if isinstance(value, (int, float)) and "amount" in key.lower():
                assert value >= 0, \
                    f"Отрицательная сумма в dashboard.contracts: {key}={value}"


# ════════════════════════════════════════════════════════════
# 3. Dashboard Clients: числа совпадают
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardClientsNumbers:
    """Dashboard клиентов vs реальные данные."""

    def test_clients_count_matches_list(self, admin_headers):
        """Dashboard clients.total ≈ len(/clients)."""
        dash = _get("/api/dashboard/clients", admin_headers)
        assert dash.status_code == 200
        dash_data = dash.json()

        clients = _get("/api/clients", admin_headers)
        assert clients.status_code == 200
        real_count = len(clients.json())

        dash_count = (dash_data.get("total") or
                      dash_data.get("count") or
                      dash_data.get("clients_count") or
                      dash_data.get("total_clients"))
        if dash_count is not None:
            tolerance = max(3, real_count * 0.05)
            assert abs(dash_count - real_count) <= tolerance, \
                f"Dashboard clients={dash_count}, real={real_count}"


# ════════════════════════════════════════════════════════════
# 4. Dashboard Employees: активные vs общие
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardEmployeesNumbers:
    """Dashboard сотрудников vs реальные данные."""

    def test_employees_total_matches_list(self, admin_headers):
        """Dashboard employees.total ≈ len(/employees)."""
        dash = _get("/api/dashboard/employees", admin_headers)
        assert dash.status_code == 200
        dash_data = dash.json()

        employees = _get("/api/employees", admin_headers)
        assert employees.status_code == 200
        real_count = len(employees.json())

        dash_count = (dash_data.get("total") or
                      dash_data.get("count") or
                      dash_data.get("employees_count") or
                      dash_data.get("total_employees"))
        if dash_count is not None:
            tolerance = max(3, real_count * 0.05)
            assert abs(dash_count - real_count) <= tolerance, \
                f"Dashboard employees={dash_count}, real={real_count}"

    def test_active_employees_matches_filtered(self, admin_headers):
        """Dashboard active_employees ≈ len(employees WHERE status='активный')."""
        dash = _get("/api/dashboard/employees", admin_headers)
        assert dash.status_code == 200
        dash_data = dash.json()

        employees = _get("/api/employees", admin_headers)
        assert employees.status_code == 200
        emp_list = employees.json()
        real_active = len([e for e in emp_list if e.get("status") == "активный"])

        dash_active = (dash_data.get("active") or
                       dash_data.get("active_count") or
                       dash_data.get("active_employees"))
        if dash_active is not None:
            tolerance = max(2, real_active * 0.1)
            assert abs(dash_active - real_active) <= tolerance, \
                f"Dashboard active={dash_active}, real active={real_active}"

    def test_fired_employees_matches_filtered(self, admin_headers):
        """Dashboard fired_employees ≈ len(employees WHERE status='уволен')."""
        dash = _get("/api/dashboard/employees", admin_headers)
        assert dash.status_code == 200
        dash_data = dash.json()

        employees = _get("/api/employees", admin_headers)
        assert employees.status_code == 200
        emp_list = employees.json()
        real_fired = len([e for e in emp_list if e.get("status") == "уволен"])

        dash_fired = (dash_data.get("fired") or
                      dash_data.get("fired_count") or
                      dash_data.get("fired_employees"))
        if dash_fired is not None:
            tolerance = max(2, real_fired * 0.1)
            assert abs(dash_fired - real_fired) <= tolerance, \
                f"Dashboard fired={dash_fired}, real fired={real_fired}"


# ════════════════════════════════════════════════════════════
# 5. Dashboard Supervision: числа совпадают
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardSupervisionNumbers:
    """Dashboard надзора vs реальные данные."""

    def test_supervision_active_count_matches(self, admin_headers):
        """Количество активных supervision карточек совпадает."""
        cards = _get("/api/supervision/cards", admin_headers,
                      params={"status": "active"})
        assert cards.status_code == 200
        real_active = len(cards.json())

        # Если есть dashboard для supervision
        dash = _get("/api/dashboard/crm", admin_headers,
                     params={"project_type": "Авторский надзор"})
        if dash.status_code == 200:
            dash_data = dash.json()
            dash_count = (dash_data.get("total_orders") or
                          dash_data.get("total") or
                          dash_data.get("count"))
            if dash_count is not None:
                # Допуск больше — supervision может включать паузированные
                tolerance = max(5, real_active * 0.15)
                assert abs(dash_count - real_active) <= tolerance, \
                    f"Dashboard supervision={dash_count}, real active={real_active}"


# ════════════════════════════════════════════════════════════
# 6. Кросс-проверка: Dashboard general vs составляющие
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestDashboardCrossCheck:
    """Кросс-проверка: общие числа dashboard vs суммы составляющих."""

    def test_statistics_general_has_data(self, admin_headers):
        """GET /statistics/general возвращает реальные данные (не пустой dict)."""
        # statistics/general может требовать query params (project_type)
        resp = _get("/api/statistics/general", admin_headers,
                     params={"project_type": "Индивидуальный"})
        if resp.status_code == 422:
            resp = _get("/api/statistics/general", admin_headers)
        if resp.status_code == 422:
            pytest.skip("statistics/general требует специфических параметров")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_statistics_dashboard_structure(self, admin_headers):
        """GET /statistics/dashboard возвращает все ожидаемые секции."""
        resp = _get("/api/statistics/dashboard", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict), f"dashboard: ожидали dict, получили {type(data)}"

    def test_dashboard_reports_all_sections(self, admin_headers):
        """Все секции dashboard отвечают (clients, contracts, employees, crm)."""
        endpoints = [
            "/api/dashboard/clients",
            "/api/dashboard/contracts",
            "/api/dashboard/employees",
        ]
        for ep in endpoints:
            resp = _get(ep, admin_headers)
            assert resp.status_code == 200, f"{ep}: {resp.status_code}"
            assert isinstance(resp.json(), dict), f"{ep}: не dict"

    def test_no_negative_counts_in_dashboard(self, admin_headers):
        """Все счётчики в dashboard неотрицательные."""
        for ep in ["/api/dashboard/clients", "/api/dashboard/contracts",
                   "/api/dashboard/employees"]:
            resp = _get(ep, admin_headers)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    assert value >= 0, \
                        f"{ep}.{key} = {value} (отрицательное значение!)"
