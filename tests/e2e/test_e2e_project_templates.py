# -*- coding: utf-8 -*-
"""
E2E Tests: Шаблоны проектов
5 тестов — CRUD endpoints project-templates.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get, api_post, api_delete


class TestProjectTemplates:
    """Тесты шаблонов проектов"""

    @pytest.fixture(autouse=True)
    def setup_data(self, api_base, admin_headers, factory):
        """Создание тестовых данных: клиент + договор"""
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = factory
        self.client = factory.create_client()
        self.contract = factory.create_contract(self.client["id"])

    def test_add_project_template(self):
        """POST /api/project-templates — добавить шаблон"""
        resp = api_post(
            self.api_base,
            "/api/project-templates",
            self.headers,
            params={
                "contract_id": self.contract["id"],
                "template_url": "https://example.com/template/1"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    def test_get_project_templates(self):
        """GET /api/project-templates/{contract_id} — получить шаблоны"""
        # Сначала создаём
        api_post(self.api_base, "/api/project-templates", self.headers,
                 params={"contract_id": self.contract["id"],
                         "template_url": "https://example.com/template/2"})
        resp = api_get(
            self.api_base,
            f"/api/project-templates/{self.contract['id']}",
            self.headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_delete_project_template(self):
        """DELETE /api/project-templates/{template_id} — удалить шаблон"""
        # Создаём
        create_resp = api_post(
            self.api_base, "/api/project-templates", self.headers,
            params={"contract_id": self.contract["id"],
                    "template_url": "https://example.com/template/3"})
        assert create_resp.status_code == 200
        template_id = create_resp.json()["id"]
        # Удаляем
        resp = api_delete(self.api_base, f"/api/project-templates/{template_id}", self.headers)
        assert resp.status_code == 200

    def test_get_templates_nonexistent_contract(self):
        """GET /api/project-templates/999999 — несуществующий договор"""
        resp = api_get(self.api_base, "/api/project-templates/999999", self.headers)
        assert resp.status_code in (200, 404)  # 200 с пустым списком или 404

    def test_delete_nonexistent_template(self):
        """DELETE /api/project-templates/999999 — несуществующий шаблон"""
        resp = api_delete(self.api_base, "/api/project-templates/999999", self.headers)
        assert resp.status_code in (404, 422)
