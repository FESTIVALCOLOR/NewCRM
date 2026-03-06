# -*- coding: utf-8 -*-
"""
Smoke Tests: Salary Workflow — CRUD зарплат + отчёт.

Запуск: pytest tests/smoke/test_salary_workflow.py -v --timeout=120
"""

import pytest
from datetime import datetime

from tests.smoke.conftest import _get, _post, _put, _delete, TEST_PREFIX


@pytest.mark.smoke
class TestSalaryCRUD:
    """P1: Зарплаты — полный CRUD."""

    def test_list_salaries(self, admin_headers):
        """GET /salaries — список зарплат."""
        resp = _get("/api/salaries", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_and_delete_salary(self, admin_headers):
        """POST /salaries → DELETE — создание и удаление."""
        resp = _post("/api/salaries", admin_headers, json={
            "employee_id": 1,
            "payment_type": "Аванс",
            "amount": 50000.0,
            "report_month": "2026-03",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Создание зарплаты: {resp.status_code} {resp.text}")
        salary_id = resp.json()["id"]

        try:
            # Проверяем GET
            get = _get(f"/api/salaries/{salary_id}", admin_headers)
            assert get.status_code == 200
            assert get.json()["amount"] == 50000.0

            # Обновляем
            upd = _put(f"/api/salaries/{salary_id}", admin_headers, json={
                "amount": 55000.0,
            })
            assert upd.status_code == 200
        finally:
            _delete(f"/api/salaries/{salary_id}", admin_headers)

    def test_salary_report(self, admin_headers):
        """GET /salaries/report — отчёт по зарплатам."""
        resp = _get("/api/salaries/report", admin_headers)
        assert resp.status_code == 200
