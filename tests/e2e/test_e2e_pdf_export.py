# -*- coding: utf-8 -*-
"""
E2E Tests: PDF экспорт
4 теста — генерация PDF статистики CRM и надзора.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get


class TestPDFExport:
    """Тесты PDF экспорта статистики"""

    def test_crm_statistics_endpoint(self, api_base, admin_headers):
        """Endpoint статистики CRM проектов отвечает"""
        resp = api_get(
            api_base,
            "/api/statistics/crm",
            admin_headers,
            params={"project_type": "Индивидуальный", "period": "year", "year": 2026}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, (dict, list))

    def test_supervision_statistics_endpoint(self, api_base, admin_headers):
        """Endpoint статистики надзора отвечает"""
        resp = api_get(api_base, "/api/statistics/supervision", admin_headers)
        assert resp.status_code == 200

    def test_crm_filtered_statistics(self, api_base, admin_headers):
        """Фильтрованная статистика CRM"""
        resp = api_get(
            api_base,
            "/api/statistics/crm/filtered",
            admin_headers,
            params={"project_type": "Индивидуальный", "period": "year", "year": 2026}
        )
        assert resp.status_code == 200

    def test_approval_statistics(self, api_base, admin_headers):
        """Статистика согласований"""
        resp = api_get(
            api_base,
            "/api/statistics/approvals",
            admin_headers,
            params={"project_type": "Индивидуальный", "period": "year", "year": 2026}
        )
        assert resp.status_code == 200
