# -*- coding: utf-8 -*-
"""
Нагрузочные тесты Interior Studio CRM API — locust.

Запуск:
    locust -f tests/load/locustfile.py --host http://147.45.154.193:8000
    locust -f tests/load/locustfile.py --host http://147.45.154.193:8000 --headless -u 10 -r 2 -t 30s

Параметры:
    -u N  — количество пользователей
    -r N  — скорость подключения (пользователей/сек)
    -t Ns — длительность теста
"""

from locust import HttpUser, task, between


class CRMUser(HttpUser):
    """Нагрузочный тест основных API endpoints."""

    wait_time = between(0.5, 2)

    def on_start(self):
        """Авторизация при старте сессии."""
        resp = self.client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("access_token", "")
            self.auth_headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = ""
            self.auth_headers = {}

    @task(5)
    def get_clients(self):
        """GET /api/clients — список клиентов."""
        self.client.get("/api/clients", headers=self.auth_headers)

    @task(5)
    def get_contracts(self):
        """GET /api/contracts — список договоров."""
        self.client.get("/api/contracts", headers=self.auth_headers)

    @task(3)
    def get_crm_cards(self):
        """GET /api/crm/cards — CRM карточки."""
        self.client.get(
            "/api/crm/cards",
            headers=self.auth_headers,
            params={"project_type": "Индивидуальный"}
        )

    @task(3)
    def get_supervision_cards(self):
        """GET /api/supervision/cards — карточки надзора."""
        self.client.get(
            "/api/supervision/cards",
            headers=self.auth_headers,
            params={"status": "active"}
        )

    @task(2)
    def get_employees(self):
        """GET /api/employees — список сотрудников."""
        self.client.get("/api/employees", headers=self.auth_headers)

    @task(2)
    def get_dashboard_stats(self):
        """GET /api/statistics/dashboard — статистика дашборда."""
        self.client.get(
            "/api/statistics/dashboard",
            headers=self.auth_headers,
            params={"year": 2026}
        )

    @task(1)
    def get_payments(self):
        """GET /api/payments — список платежей."""
        self.client.get(
            "/api/payments",
            headers=self.auth_headers,
            params={"year": 2026}
        )

    @task(1)
    def get_rates(self):
        """GET /api/rates — тарифы."""
        self.client.get("/api/rates", headers=self.auth_headers)

    @task(1)
    def health_check(self):
        """GET / — health check."""
        self.client.get("/")
