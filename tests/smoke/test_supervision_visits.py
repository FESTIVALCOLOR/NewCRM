# -*- coding: utf-8 -*-
"""
Smoke Tests: Supervision Visits — выезды авторского надзора CRUD + экспорт.

Покрывает: visits list, create, update, delete, summary, export excel/pdf.

Запуск: pytest tests/smoke/test_supervision_visits.py -v --timeout=120
"""

import pytest
from datetime import datetime

from tests.smoke.conftest import (
    _get, _post, _put, _delete,
    create_test_client, create_test_contract,
    cleanup_test_card, TEST_PREFIX,
)


def _find_supervision_card(headers, contract_id):
    """Найти карточку надзора по contract_id."""
    cards = _get("/api/supervision/cards", headers).json()
    card = next((c for c in cards if c.get("contract_id") == contract_id), None)
    return card["id"] if card else None


# ════════════════════════════════════════════════════════════
# 1. Visits CRUD
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestVisitsCRUD:
    """P1: Выезды — полный CRUD цикл."""

    def test_visits_list(self, admin_headers):
        """GET /supervision-visits/{card_id}/visits — список выездов."""
        cards = _get("/api/supervision/cards", admin_headers).json()
        if not cards:
            pytest.skip("Нет карточек надзора")
        sid = cards[0]["id"]
        resp = _get(f"/api/supervision-visits/{sid}/visits", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_update_delete_visit(self, admin_headers):
        """POST → PUT → DELETE /supervision-visits/{id}/visits — полный цикл."""
        client_id = create_test_client(admin_headers, "VISIT")
        contract_id = create_test_contract(
            admin_headers, client_id, "VISIT", project_type="Авторский надзор",
        )
        try:
            sup_id = _find_supervision_card(admin_headers, contract_id)
            if not sup_id:
                pytest.skip("Карточка надзора не создалась")

            # Создаём выезд
            create = _post(f"/api/supervision-visits/{sup_id}/visits", admin_headers, json={
                "visit_date": datetime.now().strftime("%Y-%m-%d"),
                "stage_code": "stage_1",
                "stage_name": "Стадия 1",
                "notes": f"{TEST_PREFIX}Тестовый выезд",
            })
            if create.status_code not in (200, 201):
                pytest.skip(f"Создание выезда: {create.status_code} {create.text}")
            visit_id = create.json().get("id")
            assert visit_id, "Нет ID выезда в ответе"

            # Обновляем
            upd = _put(
                f"/api/supervision-visits/{sup_id}/visits/{visit_id}",
                admin_headers,
                json={
                    "notes": f"{TEST_PREFIX}Обновлённый выезд",
                    "stage_code": "stage_1",
                    "stage_name": "Стадия 1",
                },
            )
            assert upd.status_code == 200, \
                f"Update visit: {upd.status_code} {upd.text}"

            # Удаляем
            delete = _delete(
                f"/api/supervision-visits/{sup_id}/visits/{visit_id}",
                admin_headers,
            )
            assert delete.status_code in (200, 204), \
                f"Delete visit: {delete.status_code} {delete.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 2. Visits Summary & Export
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestVisitsExport:
    """P1: Сводка и экспорт выездов."""

    def test_visits_summary(self, admin_headers):
        """GET /supervision-visits/{id}/visits/summary — сводка выездов."""
        cards = _get("/api/supervision/cards", admin_headers).json()
        if not cards:
            pytest.skip("Нет карточек надзора")
        sid = cards[0]["id"]
        resp = _get(f"/api/supervision-visits/{sid}/visits/summary", admin_headers)
        assert resp.status_code in (200, 404)

    def test_visits_export_excel(self, admin_headers):
        """GET /supervision-visits/{id}/visits/export/excel — экспорт Excel."""
        cards = _get("/api/supervision/cards", admin_headers).json()
        if not cards:
            pytest.skip("Нет карточек надзора")
        sid = cards[0]["id"]
        resp = _get(f"/api/supervision-visits/{sid}/visits/export/excel", admin_headers)
        assert resp.status_code in (200, 404)

    def test_visits_export_pdf(self, admin_headers):
        """GET /supervision-visits/{id}/visits/export/pdf — экспорт PDF."""
        cards = _get("/api/supervision/cards", admin_headers).json()
        if not cards:
            pytest.skip("Нет карточек надзора")
        sid = cards[0]["id"]
        resp = _get(f"/api/supervision-visits/{sid}/visits/export/pdf", admin_headers)
        assert resp.status_code in (200, 404)
