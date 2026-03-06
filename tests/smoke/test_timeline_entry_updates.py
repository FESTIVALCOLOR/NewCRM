# -*- coding: utf-8 -*-
"""
Smoke Tests: Timeline Entry Updates — PUT entries, init, reinit, summary.

Покрывает: GET /timeline, POST /timeline/init, PUT /timeline/entries/{id},
GET /timeline/summary, POST /timeline/reinit, export operations.

Запуск: pytest tests/smoke/test_timeline_entry_updates.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    create_test_card, cleanup_test_card, TEST_PREFIX,
)


@pytest.mark.smoke
class TestTimelineInit:
    """P0: Инициализация таймлайна для договора."""

    def test_init_timeline_for_new_card(self, admin_headers):
        """POST /timeline/{contract_id}/init — инициализация таймлайна."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "TL_INIT")
        try:
            # Двигаем карточку чтобы был contract с card
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "В ожидании"})

            resp = _post(f"/api/timeline/{contract_id}/init", admin_headers, json={
                "project_type": "Индивидуальный",
                "area": 100.0,
                "project_subtype": "Стандарт",
            })
            assert resp.status_code in (200, 201, 409, 422), \
                f"Timeline init: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_reinit_timeline(self, admin_headers):
        """POST /timeline/{contract_id}/reinit — повторная инициализация."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "TL_REINIT")
        try:
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "В ожидании"})

            # Init
            _post(f"/api/timeline/{contract_id}/init", admin_headers, json={
                "project_type": "Индивидуальный",
                "area": 100.0,
                "project_subtype": "Стандарт",
            })

            # Reinit
            resp = _post(f"/api/timeline/{contract_id}/reinit", admin_headers, json={
                "project_type": "Индивидуальный",
                "area": 100.0,
                "project_subtype": "Стандарт",
                "force": True,
            })
            assert resp.status_code in (200, 201, 422), \
                f"Timeline reinit: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestTimelineEntryUpdate:
    """P0: Обновление записей таймлайна (PUT)."""

    def test_update_entry_dates(self, admin_headers):
        """PUT /timeline/entries/{id} — обновление дат записи."""
        # Находим договор с таймлайном
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")

        for contract in contracts[:10]:
            cid = contract["id"]
            timeline = _get(f"/api/timeline/contract/{cid}", admin_headers).json()
            if isinstance(timeline, list) and len(timeline) > 0:
                entry = timeline[0]
                entry_id = entry.get("id")
                if not entry_id:
                    continue

                # Обновляем запись (идемпотентно — те же данные)
                update_data = {}
                if entry.get("plan_start"):
                    update_data["plan_start"] = entry["plan_start"]
                if entry.get("plan_end"):
                    update_data["plan_end"] = entry["plan_end"]

                if not update_data:
                    update_data = {"plan_start": "2026-04-01", "plan_end": "2026-05-01"}

                resp = _put(f"/api/timeline/entries/{entry_id}", admin_headers,
                            json=update_data)
                assert resp.status_code in (200, 422), \
                    f"Update entry: {resp.status_code} {resp.text}"
                return

        pytest.skip("Нет записей таймлайна для обновления")

    def test_update_entry_fact_dates(self, admin_headers):
        """PUT /timeline/entries/{id} — обновление фактических дат."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")

        for contract in contracts[:10]:
            cid = contract["id"]
            timeline = _get(f"/api/timeline/contract/{cid}", admin_headers).json()
            if isinstance(timeline, list) and len(timeline) > 0:
                entry = timeline[0]
                entry_id = entry.get("id")
                if not entry_id:
                    continue

                resp = _put(f"/api/timeline/entries/{entry_id}", admin_headers, json={
                    "fact_start": "2026-03-01",
                    "fact_end": "2026-03-15",
                })
                assert resp.status_code in (200, 422), \
                    f"Update fact dates: {resp.status_code} {resp.text}"
                return

        pytest.skip("Нет записей таймлайна")


@pytest.mark.smoke
class TestTimelineSummary:
    """P1: Сводка таймлайна."""

    def test_timeline_summary(self, admin_headers):
        """GET /timeline/{contract_id}/summary — сводка по договору."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        cid = contracts[0]["id"]
        resp = _get(f"/api/timeline/{cid}/summary", admin_headers)
        assert resp.status_code in (200, 404, 422)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (dict, list))

    def test_timeline_by_contract(self, admin_headers):
        """GET /timeline/contract/{id} — таймлайн по договору."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")

        cid = contracts[0]["id"]
        resp = _get(f"/api/timeline/contract/{cid}", admin_headers)
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            assert isinstance(resp.json(), list)

    def test_timeline_export_excel(self, admin_headers):
        """GET /timeline/export/excel — экспорт в Excel."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")

        cid = contracts[0]["id"]
        resp = _get(f"/api/timeline/export/excel", admin_headers, params={
            "contract_id": cid,
        })
        assert resp.status_code in (200, 404, 422)
        if resp.status_code == 200:
            assert len(resp.content) > 0

    def test_timeline_export_pdf(self, admin_headers):
        """GET /timeline/export/pdf — экспорт в PDF."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")

        cid = contracts[0]["id"]
        resp = _get(f"/api/timeline/export/pdf", admin_headers, params={
            "contract_id": cid,
        })
        assert resp.status_code in (200, 404, 422)
        if resp.status_code == 200:
            assert len(resp.content) > 0
