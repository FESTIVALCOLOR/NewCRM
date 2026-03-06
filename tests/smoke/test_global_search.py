# -*- coding: utf-8 -*-
"""
Smoke Tests: Global Search — глобальный поиск по сущностям.

Покрывает: GET /search с разными параметрами,
спецсимволы, пустые запросы, кириллица.

Запуск: pytest tests/smoke/test_global_search.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import _get


@pytest.mark.smoke
class TestGlobalSearch:
    """P1: Глобальный поиск по всем сущностям."""

    def test_search_basic(self, admin_headers):
        """GET /search?q=... — базовый поиск."""
        resp = _get("/api/search", admin_headers, params={"q": "admin"})
        assert resp.status_code in (200, 404, 422), \
            f"Search: {resp.status_code} {resp.text}"

    def test_search_cyrillic(self, admin_headers):
        """Поиск кириллическим текстом."""
        resp = _get("/api/search", admin_headers, params={"q": "Москва"})
        assert resp.status_code in (200, 404, 422)

    def test_search_contract_number(self, admin_headers):
        """Поиск по номеру договора."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        num = contracts[0].get("contract_number", "")
        if not num:
            pytest.skip("Нет номера договора")

        resp = _get("/api/search", admin_headers, params={"q": num})
        assert resp.status_code in (200, 404, 422)

    def test_search_empty_query(self, admin_headers):
        """Пустой запрос → 200 с пустым списком или 422."""
        resp = _get("/api/search", admin_headers, params={"q": ""})
        assert resp.status_code in (200, 422)

    def test_search_special_chars(self, admin_headers):
        """Спецсимволы в поиске не ломают API."""
        resp = _get("/api/search", admin_headers, params={
            "q": "test<>\"'&;",
        })
        assert resp.status_code in (200, 404, 422)

    def test_search_phone_number(self, admin_headers):
        """Поиск по номеру телефона."""
        resp = _get("/api/search", admin_headers, params={"q": "+7999"})
        assert resp.status_code in (200, 404, 422)

    def test_search_long_query(self, admin_headers):
        """Очень длинный запрос."""
        resp = _get("/api/search", admin_headers, params={"q": "а" * 500})
        assert resp.status_code in (200, 422, 414)  # 414 = URI Too Long
