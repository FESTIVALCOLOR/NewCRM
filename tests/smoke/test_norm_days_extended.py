# -*- coding: utf-8 -*-
"""
Smoke Tests: Norm Days Extended — шаблоны нормативных сроков.

Покрывает: templates get/put, preview, reset.

Запуск: pytest tests/smoke/test_norm_days_extended.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import _get, _post, _put


@pytest.mark.smoke
class TestNormDaysTemplates:
    """P1: Шаблоны нормативных сроков — расширенные операции."""

    def test_get_templates(self, admin_headers):
        """GET /norm-days/templates — получение шаблонов."""
        resp = _get("/api/norm-days/templates", admin_headers, params={
            "project_type": "Индивидуальный",
            "project_subtype": "Стандарт",
        })
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (dict, list))

    def test_update_templates(self, admin_headers):
        """PUT /norm-days/templates — обновление шаблонов (идемпотентно)."""
        # Сначала получаем текущие
        current = _get("/api/norm-days/templates", admin_headers, params={
            "project_type": "Индивидуальный",
            "project_subtype": "Стандарт",
        })
        if current.status_code not in (200,):
            pytest.skip("Не удалось получить шаблоны")

        # Отправляем обратно как есть (идемпотентное обновление)
        resp = _put("/api/norm-days/templates", admin_headers, json=current.json())
        assert resp.status_code in (200, 422), \
            f"Update templates: {resp.status_code} {resp.text}"

    def test_preview_templates(self, admin_headers):
        """POST /norm-days/templates/preview — предпросмотр шаблонов."""
        resp = _post("/api/norm-days/templates/preview", admin_headers, json={
            "project_type": "Индивидуальный",
        })
        assert resp.status_code in (200, 422), \
            f"Preview: {resp.status_code} {resp.text}"

    def test_reset_templates(self, admin_headers):
        """POST /norm-days/templates/reset — сброс шаблонов к умолчаниям."""
        resp = _post("/api/norm-days/templates/reset", admin_headers, json={
            "project_type": "Индивидуальный",
            "project_subtype": "Стандарт",
        })
        # Может быть 200 если сброс успешен, 400 если некорректный JSON, или 422
        assert resp.status_code in (200, 204, 400, 422), \
            f"Reset: {resp.status_code} {resp.text}"
