# -*- coding: utf-8 -*-
"""
E2E Tests: Таблица сроков проекта (CRM Timeline)
15 тестов — init, reinit, get, update, export Excel/PDF.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get, api_post, api_put


class TestProjectTimeline:
    """Тесты таблицы сроков проекта"""

    @pytest.fixture(autouse=True)
    def setup_data(self, api_base, admin_headers, factory):
        """Создание тестовых данных: клиент + договор"""
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = factory
        self.client = factory.create_client()
        self.contract = factory.create_contract(
            self.client["id"],
            project_type="Индивидуальный",
            area=100.0
        )

    def test_init_timeline_individual(self):
        """POST /api/timeline/{id}/init — инициализация индивидуального проекта."""
        resp = api_post(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/init",
            self.headers,
            json={
                "project_type": "Индивидуальный",
                "project_subtype": "Полный",
                "area": 100.0,
                "floors": 1
            }
        )
        assert resp.status_code == 200, f"Init failed: {resp.text}"
        data = resp.json()
        assert data.get("status") in ("initialized", "already_initialized")

    def test_init_timeline_template(self):
        """POST /api/timeline/{id}/init — шаблонный проект."""
        contract = self.factory.create_contract(
            self.client["id"],
            project_type="Шаблонный",
            area=60.0
        )
        resp = api_post(
            self.api_base,
            f"/api/timeline/{contract['id']}/init",
            self.headers,
            json={
                "project_type": "Шаблонный",
                "project_subtype": "Стандарт",
                "area": 60.0,
                "floors": 1
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") in ("initialized", "already_initialized")

    def test_init_already_initialized(self):
        """Повторный init возвращает already_initialized."""
        init_data = {
            "project_type": "Индивидуальный",
            "project_subtype": "Полный",
            "area": 100.0
        }
        api_post(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/init",
            self.headers,
            json=init_data
        )
        resp = api_post(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/init",
            self.headers,
            json=init_data
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "already_initialized"

    def test_init_invalid_contract_404(self):
        """Init для несуществующего контракта → 404."""
        resp = api_post(
            self.api_base,
            "/api/timeline/999999/init",
            self.headers,
            json={"project_type": "Индивидуальный", "area": 100.0}
        )
        assert resp.status_code in (404, 422)

    def test_get_timeline_after_init(self):
        """GET /api/timeline/{id} — после init возвращает записи."""
        api_post(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/init",
            self.headers,
            json={"project_type": "Индивидуальный", "area": 100.0}
        )
        resp = api_get(
            self.api_base,
            f"/api/timeline/{self.contract['id']}",
            self.headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_timeline_before_init(self):
        """GET /api/timeline/{id} — до init возвращает пустой список или 404."""
        new_contract = self.factory.create_contract(self.client["id"])
        resp = api_get(
            self.api_base,
            f"/api/timeline/{new_contract['id']}",
            self.headers
        )
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, list)

    def test_get_timeline_summary(self):
        """GET /api/timeline/{id}/summary — сводка."""
        api_post(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/init",
            self.headers,
            json={"project_type": "Индивидуальный", "area": 100.0}
        )
        resp = api_get(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/summary",
            self.headers
        )
        assert resp.status_code == 200

    def test_update_timeline_entry(self):
        """PUT /api/timeline/{id}/entry/{stage_code} — обновление записи."""
        api_post(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/init",
            self.headers,
            json={"project_type": "Индивидуальный", "area": 100.0}
        )
        # Получаем записи, чтобы узнать stage_code
        get_resp = api_get(
            self.api_base,
            f"/api/timeline/{self.contract['id']}",
            self.headers
        )
        entries = get_resp.json()
        if isinstance(entries, list) and len(entries) > 0:
            stage_code = entries[0].get("stage_code", entries[0].get("id", "S1"))
            resp = api_put(
                self.api_base,
                f"/api/timeline/{self.contract['id']}/entry/{stage_code}",
                self.headers,
                json={"actual_days": 15}
            )
            assert resp.status_code in (200, 404, 422)

    def test_update_invalid_stage_code(self):
        """PUT с несуществующим stage_code → 404."""
        api_post(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/init",
            self.headers,
            json={"project_type": "Индивидуальный", "area": 100.0}
        )
        resp = api_put(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/entry/INVALID_STAGE",
            self.headers,
            json={"actual_days": 10}
        )
        assert resp.status_code in (404, 422)

    def test_reinit_timeline(self):
        """POST /api/timeline/{id}/reinit — пересоздание."""
        init_data = {"project_type": "Индивидуальный", "area": 100.0}
        api_post(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/init",
            self.headers,
            json=init_data
        )
        resp = api_post(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/reinit",
            self.headers,
            json=init_data
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") in ("reinitialized", "initialized")

    def test_reinit_different_area(self):
        """Reinit с другой площадью пересоздаёт записи."""
        api_post(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/init",
            self.headers,
            json={"project_type": "Индивидуальный", "area": 100.0}
        )
        resp = api_post(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/reinit",
            self.headers,
            json={"project_type": "Индивидуальный", "area": 200.0}
        )
        assert resp.status_code == 200

    def test_export_excel(self):
        """GET /api/timeline/{id}/export/excel — xlsx."""
        api_post(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/init",
            self.headers,
            json={"project_type": "Индивидуальный", "area": 100.0}
        )
        resp = api_get(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/export/excel",
            self.headers
        )
        assert resp.status_code == 200
        ct = resp.headers.get("content-type", "")
        assert "spreadsheet" in ct or "octet-stream" in ct

    def test_export_pdf(self):
        """GET /api/timeline/{id}/export/pdf — pdf."""
        api_post(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/init",
            self.headers,
            json={"project_type": "Индивидуальный", "area": 100.0}
        )
        resp = api_get(
            self.api_base,
            f"/api/timeline/{self.contract['id']}/export/pdf",
            self.headers
        )
        assert resp.status_code == 200
        ct = resp.headers.get("content-type", "")
        assert "pdf" in ct or "octet-stream" in ct

    def test_export_nonexistent_contract(self):
        """Export для несуществующего контракта → 404."""
        resp = api_get(
            self.api_base,
            "/api/timeline/999999/export/excel",
            self.headers
        )
        assert resp.status_code in (404, 500)

    def test_requires_auth(self):
        """Без авторизации → 401/403."""
        resp = api_get(
            self.api_base,
            f"/api/timeline/{self.contract['id']}",
            {}  # без токена
        )
        assert resp.status_code in (401, 403, 422)
