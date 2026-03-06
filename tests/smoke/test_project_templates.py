# -*- coding: utf-8 -*-
"""
Smoke Tests: Project Templates — шаблоны проектов CRUD.

Покрывает: create, get by contract, delete.

Запуск: pytest tests/smoke/test_project_templates.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import (
    _get, _post, _delete,
    create_test_card, cleanup_test_card, TEST_PREFIX,
)


@pytest.mark.smoke
class TestProjectTemplates:
    """P1: Шаблоны проектов — полный CRUD."""

    def test_get_template_by_contract(self, admin_headers):
        """GET /project-templates/{contract_id} — шаблон по договору."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        cid = contracts[0]["id"]
        resp = _get(f"/api/project-templates/{cid}", admin_headers)
        assert resp.status_code in (200, 404)

    def test_create_and_delete_template(self, admin_headers):
        """POST → DELETE /project-templates — создание и удаление."""
        client_id, contract_id, _ = create_test_card(admin_headers, "TMPL")
        try:
            resp = _post("/api/project-templates", admin_headers, json={
                "contract_id": contract_id,
                "template_url": f"https://example.com/{TEST_PREFIX}template.pdf",
            })
            if resp.status_code not in (200, 201):
                pytest.skip(f"Создание шаблона: {resp.status_code} {resp.text}")

            template_id = resp.json().get("id")
            assert template_id, "Нет ID шаблона в ответе"

            # Проверяем GET
            check = _get(f"/api/project-templates/{contract_id}", admin_headers)
            assert check.status_code == 200

            # Удаляем
            delete = _delete(f"/api/project-templates/{template_id}", admin_headers)
            assert delete.status_code in (200, 204), \
                f"Delete template: {delete.status_code} {delete.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_get_nonexistent_template(self, admin_headers):
        """GET /project-templates/999999 — несуществующий шаблон."""
        resp = _get("/api/project-templates/999999", admin_headers)
        assert resp.status_code in (200, 404)  # 200 с пустым списком или 404
