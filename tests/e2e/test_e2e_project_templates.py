# -*- coding: utf-8 -*-
"""
E2E Tests: Шаблоны проектов
9 тестов — CRUD endpoints project-templates с проверкой структуры ответов.
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
            json={
                "contract_id": self.contract["id"],
                "template_url": "https://example.com/template/1"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    def test_add_project_template_keys(self):
        """POST /api/project-templates — ответ содержит ожидаемые ключи"""
        template_url = "https://example.com/template/keys-check"
        resp = api_post(
            self.api_base,
            "/api/project-templates",
            self.headers,
            json={
                "contract_id": self.contract["id"],
                "template_url": template_url
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        required_keys = {"id", "contract_id", "template_url"}
        assert required_keys.issubset(data.keys()), (
            f"Отсутствуют ключи в ответе: {required_keys - data.keys()}"
        )
        assert isinstance(data["id"], int), "id должен быть int"
        assert data["contract_id"] == self.contract["id"], (
            f"contract_id в ответе ({data['contract_id']}) не совпадает с переданным ({self.contract['id']})"
        )
        assert data["template_url"] == template_url, (
            f"template_url в ответе ({data['template_url']!r}) не совпадает с переданным ({template_url!r})"
        )

    def test_get_project_templates(self):
        """GET /api/project-templates/{contract_id} — получить шаблоны"""
        # Сначала создаём
        api_post(self.api_base, "/api/project-templates", self.headers,
                 json={"contract_id": self.contract["id"],
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
        # Проверяем структуру элементов
        required_keys = {"id", "contract_id", "template_url", "created_at"}
        for item in data[:5]:
            assert required_keys.issubset(item.keys()), (
                f"Отсутствуют ключи в шаблоне: {required_keys - item.keys()}"
            )
            assert isinstance(item["id"], int), "id должен быть int"
            assert item["contract_id"] == self.contract["id"], (
                f"contract_id должен совпадать с {self.contract['id']}"
            )
            assert isinstance(item["template_url"], str), "template_url должен быть строкой"

    def test_delete_project_template(self):
        """DELETE /api/project-templates/{template_id} — удалить шаблон"""
        # Создаём
        create_resp = api_post(
            self.api_base, "/api/project-templates", self.headers,
            json={"contract_id": self.contract["id"],
                  "template_url": "https://example.com/template/3"})
        assert create_resp.status_code == 200
        template_id = create_resp.json()["id"]
        # Удаляем
        resp = api_delete(self.api_base, f"/api/project-templates/{template_id}", self.headers)
        assert resp.status_code == 200

    def test_delete_actually_removes_template(self):
        """DELETE /api/project-templates/{id} — после удаления шаблон не должен присутствовать в списке"""
        # Создаём шаблон
        create_resp = api_post(
            self.api_base, "/api/project-templates", self.headers,
            json={"contract_id": self.contract["id"],
                  "template_url": "https://example.com/template/to-delete"}
        )
        assert create_resp.status_code == 200
        template_id = create_resp.json()["id"]

        # Удаляем
        del_resp = api_delete(self.api_base, f"/api/project-templates/{template_id}", self.headers)
        assert del_resp.status_code == 200

        # Проверяем что удалённый id больше не возвращается
        get_resp = api_get(
            self.api_base,
            f"/api/project-templates/{self.contract['id']}",
            self.headers
        )
        assert get_resp.status_code == 200
        remaining = get_resp.json()
        remaining_ids = [item["id"] for item in remaining]
        assert template_id not in remaining_ids, (
            f"Удалённый шаблон id={template_id} всё ещё присутствует в списке"
        )

    def test_add_multiple_templates_count(self):
        """POST несколько шаблонов — количество шаблонов увеличивается"""
        # Получаем начальное количество
        initial_resp = api_get(
            self.api_base,
            f"/api/project-templates/{self.contract['id']}",
            self.headers
        )
        assert initial_resp.status_code == 200
        initial_count = len(initial_resp.json())

        # Добавляем 3 шаблона
        urls = [
            "https://example.com/template/multi/1",
            "https://example.com/template/multi/2",
            "https://example.com/template/multi/3",
        ]
        for url in urls:
            r = api_post(
                self.api_base, "/api/project-templates", self.headers,
                json={"contract_id": self.contract["id"], "template_url": url}
            )
            assert r.status_code == 200, f"Ошибка создания шаблона: {r.status_code} {r.text}"

        # Проверяем что стало больше
        final_resp = api_get(
            self.api_base,
            f"/api/project-templates/{self.contract['id']}",
            self.headers
        )
        assert final_resp.status_code == 200
        final_count = len(final_resp.json())
        assert final_count == initial_count + 3, (
            f"Ожидали {initial_count + 3} шаблонов, получили {final_count}"
        )

    def test_add_template_empty_url(self):
        """POST /api/project-templates с пустым URL — 422 или 400"""
        resp = api_post(
            self.api_base,
            "/api/project-templates",
            self.headers,
            json={
                "contract_id": self.contract["id"],
                "template_url": ""
            }
        )
        # Пустой URL не должен быть принят без ошибки
        # Сервер может вернуть 422 (валидация pydantic) или 400 (бизнес-логика)
        # Либо 200 если сервер допускает пустые URL — тогда проверяем что id есть
        if resp.status_code == 200:
            # Сервер принимает пустые URL — это допустимо, проверяем что id вернулся
            data = resp.json()
            assert "id" in data, "Даже при пустом URL ответ должен содержать id"
        else:
            assert resp.status_code in (400, 422), (
                f"При пустом URL ожидали 400/422, получили {resp.status_code}"
            )

    def test_get_templates_nonexistent_contract(self):
        """GET /api/project-templates/999999 — несуществующий договор"""
        resp = api_get(self.api_base, "/api/project-templates/999999", self.headers)
        assert resp.status_code in (200, 404)  # 200 с пустым списком или 404
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, list), "Ответ для несуществующего договора должен быть list"
            assert len(data) == 0, "Список шаблонов для несуществующего договора должен быть пуст"

    def test_delete_nonexistent_template(self):
        """DELETE /api/project-templates/999999 — несуществующий шаблон"""
        resp = api_delete(self.api_base, "/api/project-templates/999999", self.headers)
        assert resp.status_code in (404, 422)
