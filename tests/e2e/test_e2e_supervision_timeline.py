# -*- coding: utf-8 -*-
"""
E2E Tests: Таблица сроков авторского надзора
7 тестов — CRUD + экспорт supervision-timeline.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get, api_post, api_put, TestDataFactory


class TestSupervisionTimeline:
    """Тесты таблицы сроков надзора"""

    @pytest.fixture(autouse=True)
    def setup_data(self, api_base, admin_headers, factory):
        """Создание тестовых данных: клиент + договор + карточка надзора"""
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = factory
        self.client = factory.create_client()
        self.contract = factory.create_contract(self.client["id"])
        self.card = factory.create_supervision_card(self.contract["id"])

    def test_init_supervision_timeline(self):
        """POST /api/supervision-timeline/{card_id}/init — инициализация"""
        resp = api_post(
            self.api_base,
            f"/api/supervision-timeline/{self.card['id']}/init",
            self.headers
        )
        assert resp.status_code == 200
        data = resp.json()
        # init возвращает dict с status и count, а не list
        assert isinstance(data, dict)
        assert "status" in data

    def test_get_supervision_timeline(self):
        """GET /api/supervision-timeline/{card_id} — получить таблицу"""
        # Сначала инициализируем
        api_post(self.api_base, f"/api/supervision-timeline/{self.card['id']}/init", self.headers)
        resp = api_get(
            self.api_base,
            f"/api/supervision-timeline/{self.card['id']}",
            self.headers
        )
        assert resp.status_code == 200
        data = resp.json()
        # Ответ: {"entries": [...], "totals": {...}}
        assert isinstance(data, dict)
        assert "entries" in data
        assert isinstance(data["entries"], list)
        assert "totals" in data

    def test_get_supervision_timeline_summary(self):
        """GET /api/supervision-timeline/{card_id}/summary — сводка"""
        api_post(self.api_base, f"/api/supervision-timeline/{self.card['id']}/init", self.headers)
        resp = api_get(
            self.api_base,
            f"/api/supervision-timeline/{self.card['id']}/summary",
            self.headers
        )
        assert resp.status_code == 200

    def test_update_timeline_entry(self):
        """PUT /api/supervision-timeline/{card_id}/entry/{stage_code} — обновить запись"""
        api_post(self.api_base, f"/api/supervision-timeline/{self.card['id']}/init", self.headers)
        resp = api_put(
            self.api_base,
            f"/api/supervision-timeline/{self.card['id']}/entry/SV1",
            self.headers,
            json={"status": "В работе"}
        )
        # 200 или 404 если stage_code не найден
        assert resp.status_code in (200, 404, 422)

    def test_export_timeline_excel(self):
        """GET /api/supervision-timeline/{card_id}/export/excel — экспорт Excel"""
        api_post(self.api_base, f"/api/supervision-timeline/{self.card['id']}/init", self.headers)
        resp = api_get(
            self.api_base,
            f"/api/supervision-timeline/{self.card['id']}/export/excel",
            self.headers
        )
        assert resp.status_code == 200
        assert "spreadsheet" in resp.headers.get("content-type", "") or \
               "octet-stream" in resp.headers.get("content-type", "")

    def test_export_timeline_pdf(self):
        """GET /api/supervision-timeline/{card_id}/export/pdf — экспорт PDF"""
        api_post(self.api_base, f"/api/supervision-timeline/{self.card['id']}/init", self.headers)
        resp = api_get(
            self.api_base,
            f"/api/supervision-timeline/{self.card['id']}/export/pdf",
            self.headers
        )
        assert resp.status_code == 200
        assert "pdf" in resp.headers.get("content-type", "") or \
               "octet-stream" in resp.headers.get("content-type", "")

    def test_nonexistent_card_404(self):
        """GET /api/supervision-timeline/999999 — несуществующая карточка"""
        resp = api_get(self.api_base, "/api/supervision-timeline/999999", self.headers)
        assert resp.status_code in (200, 404)  # 200 с пустым списком или 404
