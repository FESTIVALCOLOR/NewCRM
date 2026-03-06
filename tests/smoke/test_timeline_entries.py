# -*- coding: utf-8 -*-
"""
Smoke Tests: Timeline — таблица сроков проекта.

Запуск: pytest tests/smoke/test_timeline_entries.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import (
    _get, _post, _delete,
    create_test_card, cleanup_test_card,
)


@pytest.mark.smoke
class TestTimelineRead:
    """P1: Чтение timeline."""

    def test_timeline_by_contract(self, admin_headers):
        """GET /timeline/{contract_id} — timeline конкретного договора."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        cid = contracts[0]["id"]
        resp = _get(f"/api/timeline/{cid}", admin_headers)
        assert resp.status_code in (200, 404)  # 404 если не инициализирован

    def test_timeline_summary(self, admin_headers):
        """GET /timeline/{contract_id}/summary — сводка."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        cid = contracts[0]["id"]
        resp = _get(f"/api/timeline/{cid}/summary", admin_headers)
        assert resp.status_code in (200, 404)


@pytest.mark.smoke
class TestTimelineInit:
    """P1: Инициализация timeline."""

    def test_init_timeline(self, admin_headers):
        """POST /timeline/{contract_id}/init — инициализация."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "TL_INIT")
        try:
            resp = _post(f"/api/timeline/{contract_id}/init", admin_headers, json={
                "project_type": "Индивидуальный",
                "area": 100.0,
                "project_subtype": "Стандарт",
            })
            assert resp.status_code in (200, 201, 409, 422), \
                f"Init: {resp.status_code} {resp.text}"

            # Проверяем что timeline создался
            check = _get(f"/api/timeline/{contract_id}", admin_headers)
            assert check.status_code in (200, 404)
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_reinit_timeline(self, admin_headers):
        """POST /timeline/{contract_id}/reinit — переинициализация."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "TL_REINIT")
        try:
            # Сначала init
            _post(f"/api/timeline/{contract_id}/init", admin_headers, json={
                "project_type": "Индивидуальный",
                "area": 100.0,
                "project_subtype": "Стандарт",
            })
            # Потом reinit
            resp = _post(f"/api/timeline/{contract_id}/reinit", admin_headers, json={
                "project_type": "Индивидуальный",
                "area": 100.0,
                "project_subtype": "Стандарт",
                "force": True,
            })
            assert resp.status_code in (200, 201, 422)
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestTimelineExport:
    """P1: Экспорт timeline."""

    def test_timeline_export_excel(self, admin_headers):
        """GET /timeline/{contract_id}/export/excel — экспорт в Excel."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        cid = contracts[0]["id"]
        resp = _get(f"/api/timeline/{cid}/export/excel", admin_headers)
        # 200 если есть данные, 404 если нет timeline
        assert resp.status_code in (200, 404)

    def test_timeline_export_pdf(self, admin_headers):
        """GET /timeline/{contract_id}/export/pdf — экспорт в PDF."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        cid = contracts[0]["id"]
        resp = _get(f"/api/timeline/{cid}/export/pdf", admin_headers)
        assert resp.status_code in (200, 404)
