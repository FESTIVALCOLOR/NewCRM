# -*- coding: utf-8 -*-
"""
E2E Tests: Нормо-дни (norm-days)
7 тестов — шаблоны нормо-дней: получение, сохранение, предпросмотр, сброс.
Endpoint prefix: /api/norm-days
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import api_get, api_post, api_put


# ==============================================================
# ШАБЛОНЫ НОРМО-ДНЕЙ
# ==============================================================

@pytest.mark.e2e
class TestNormDays:
    """Тесты шаблонов нормо-дней"""

    def test_get_template_individualniy(self, api_base, admin_headers):
        """GET /api/norm-days/templates — шаблон для Индивидуального типа проекта"""
        resp = api_get(
            api_base, "/api/norm-days/templates", admin_headers,
            params={
                "project_type": "Индивидуальный",
                "project_subtype": "Полный (с 3д визуализацией)"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "project_type" in data
        assert "project_subtype" in data
        assert "entries" in data
        assert isinstance(data["entries"], list)
        assert "is_custom" in data

    def test_get_template_shablon(self, api_base, admin_headers):
        """GET /api/norm-days/templates — шаблон для Шаблонного типа проекта"""
        resp = api_get(
            api_base, "/api/norm-days/templates", admin_headers,
            params={
                "project_type": "Шаблонный",
                "project_subtype": "Стандарт"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_type"] == "Шаблонный"
        assert isinstance(data["entries"], list)

    def test_get_template_requires_auth(self, api_base):
        """GET /api/norm-days/templates без токена — 401/403"""
        resp = api_get(
            api_base, "/api/norm-days/templates", {},
            params={
                "project_type": "Индивидуальный",
                "project_subtype": "Полный (с 3д визуализацией)"
            }
        )
        assert resp.status_code in (401, 403)

    def test_preview_norm_days(self, api_base, admin_headers):
        """POST /api/norm-days/templates/preview — предпросмотр расчёта нормо-дней"""
        payload = {
            "project_type": "Индивидуальный",
            "project_subtype": "Полный (с 3д визуализацией)",
            "area": 80.0
        }
        resp = api_post(
            api_base, "/api/norm-days/templates/preview", admin_headers,
            json=payload
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        assert isinstance(data["entries"], list)
        assert "contract_term" in data
        assert "k_coefficient" in data

    def test_preview_zero_area_returns_error(self, api_base, admin_headers):
        """POST /api/norm-days/templates/preview с нулевой площадью — 400"""
        payload = {
            "project_type": "Индивидуальный",
            "project_subtype": "Полный (с 3д визуализацией)",
            "area": 0.0
        }
        resp = api_post(
            api_base, "/api/norm-days/templates/preview", admin_headers,
            json=payload
        )
        assert resp.status_code in (400, 422)

    def test_save_and_reset_template(self, api_base, admin_headers):
        """PUT /api/norm-days/templates + POST /templates/reset — сохранение и сброс шаблона"""
        # Сначала получаем текущие записи (из формул)
        get_resp = api_get(
            api_base, "/api/norm-days/templates", admin_headers,
            params={
                "project_type": "Индивидуальный",
                "project_subtype": "Эскизный (с коллажами)"
            }
        )
        assert get_resp.status_code == 200
        entries = get_resp.json().get("entries", [])

        if not entries:
            # Если формула не вернула записей — пропускаем
            pytest.skip("Формула не вернула записей для Эскизный (с коллажами)")

        # Сохраняем шаблон (PUT)
        save_payload = {
            "project_type": "Индивидуальный",
            "project_subtype": "Эскизный (с коллажами)",
            "entries": entries
        }
        save_resp = api_put(
            api_base, "/api/norm-days/templates", admin_headers,
            json=save_payload
        )
        assert save_resp.status_code == 200
        save_data = save_resp.json()
        assert save_data.get("status") == "saved"

        # Проверяем что шаблон теперь помечен как кастомный
        check_resp = api_get(
            api_base, "/api/norm-days/templates", admin_headers,
            params={
                "project_type": "Индивидуальный",
                "project_subtype": "Эскизный (с коллажами)"
            }
        )
        assert check_resp.status_code == 200
        assert check_resp.json().get("is_custom") is True

        # Сбрасываем шаблон (POST /templates/reset)
        reset_resp = api_post(
            api_base, "/api/norm-days/templates/reset", admin_headers,
            json={
                "project_type": "Индивидуальный",
                "project_subtype": "Эскизный (с коллажами)"
            }
        )
        assert reset_resp.status_code == 200
        reset_data = reset_resp.json()
        assert reset_data.get("status") == "reset"

    def test_save_template_empty_entries_returns_error(self, api_base, admin_headers):
        """PUT /api/norm-days/templates с пустым entries — 400"""
        payload = {
            "project_type": "Индивидуальный",
            "project_subtype": "Полный (с 3д визуализацией)",
            "entries": []
        }
        resp = api_put(
            api_base, "/api/norm-days/templates", admin_headers,
            json=payload
        )
        assert resp.status_code in (400, 422)
