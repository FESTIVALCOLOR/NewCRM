# -*- coding: utf-8 -*-
"""
Smoke Tests: Supervision Timeline Operations — timeline надзора.

Покрывает: get by card, init, entry update, summary, export excel/pdf.

Запуск: pytest tests/smoke/test_supervision_timeline_ops.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import (
    _get, _post, _put,
    create_test_client, create_test_contract,
    cleanup_test_card,
)


def _find_supervision_card(headers, contract_id):
    """Найти карточку надзора по contract_id."""
    cards = _get("/api/supervision/cards", headers).json()
    card = next((c for c in cards if c.get("contract_id") == contract_id), None)
    return card["id"] if card else None


def _create_supervision_card(headers, suffix="STL"):
    """Создать клиент + договор + карточку надзора.
    Возвращает (client_id, contract_id, sup_card_id).
    """
    client_id = create_test_client(headers, suffix)
    contract_id = create_test_contract(
        headers, client_id, suffix, project_type="Авторский надзор",
    )
    sup_id = _find_supervision_card(headers, contract_id)
    if not sup_id:
        cr = _post("/api/supervision/cards", headers, json={
            "contract_id": contract_id,
        })
        if cr.status_code in (200, 201):
            sup_id = cr.json()["id"]
        else:
            pytest.skip(f"Не удалось создать карточку надзора: {cr.status_code}")
    return client_id, contract_id, sup_id


# ════════════════════════════════════════════════════════════
# 1. Read Operations
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSupervisionTimelineRead:
    """P1: Чтение timeline надзора."""

    def test_timeline_by_card(self, admin_headers):
        """GET /supervision-timeline/{card_id} — timeline конкретной карточки."""
        cards = _get("/api/supervision/cards", admin_headers).json()
        if not cards:
            pytest.skip("Нет карточек надзора")
        sid = cards[0]["id"]
        resp = _get(f"/api/supervision-timeline/{sid}", admin_headers)
        assert resp.status_code in (200, 404)

    def test_timeline_summary(self, admin_headers):
        """GET /supervision-timeline/{card_id}/summary — сводка."""
        cards = _get("/api/supervision/cards", admin_headers).json()
        if not cards:
            pytest.skip("Нет карточек надзора")
        sid = cards[0]["id"]
        resp = _get(f"/api/supervision-timeline/{sid}/summary", admin_headers)
        assert resp.status_code in (200, 404)


# ════════════════════════════════════════════════════════════
# 2. Init & Update
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSupervisionTimelineWrite:
    """P1: Инициализация и обновление timeline надзора."""

    def test_init_supervision_timeline(self, admin_headers):
        """POST /supervision-timeline/{card_id}/init — инициализация."""
        client_id, contract_id, sup_id = _create_supervision_card(
            admin_headers, "STL_INIT",
        )
        try:

            resp = _post(f"/api/supervision-timeline/{sup_id}/init", admin_headers)
            assert resp.status_code in (200, 201, 409), \
                f"Init: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_update_timeline_entry(self, admin_headers):
        """PUT /supervision-timeline/{card_id}/entry/{stage_code} — обновление записи."""
        client_id, contract_id, sup_id = _create_supervision_card(
            admin_headers, "STL_UPD",
        )
        try:
            # Инициализируем timeline
            _post(f"/api/supervision-timeline/{sup_id}/init", admin_headers)

            # Обновляем запись (stage_code — первый этап)
            resp = _put(
                f"/api/supervision-timeline/{sup_id}/entry/stage_1",
                admin_headers,
                json={"actual_start": "2026-03-01"},
            )
            # 200 или 404 если stage_code не найден
            assert resp.status_code in (200, 404, 422), \
                f"Update entry: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 3. Export
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSupervisionTimelineExport:
    """P1: Экспорт timeline надзора."""

    def test_export_excel(self, admin_headers):
        """GET /supervision-timeline/{card_id}/export/excel — Excel."""
        cards = _get("/api/supervision/cards", admin_headers).json()
        if not cards:
            pytest.skip("Нет карточек надзора")
        sid = cards[0]["id"]
        resp = _get(f"/api/supervision-timeline/{sid}/export/excel", admin_headers)
        assert resp.status_code in (200, 404)

    def test_export_pdf(self, admin_headers):
        """GET /supervision-timeline/{card_id}/export/pdf — PDF."""
        cards = _get("/api/supervision/cards", admin_headers).json()
        if not cards:
            pytest.skip("Нет карточек надзора")
        sid = cards[0]["id"]
        resp = _get(f"/api/supervision-timeline/{sid}/export/pdf", admin_headers)
        assert resp.status_code in (200, 404)
