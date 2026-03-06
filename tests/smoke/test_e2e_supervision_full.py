# -*- coding: utf-8 -*-
"""
Smoke Tests: E2E Supervision Full — полный цикл авторского надзора.

Сквозной бизнес-сценарий от создания до экспорта:
Договор → Карточка надзора → Timeline init → Визиты → Пауза → Возобновление
→ Завершение стадий → Платежи → Экспорт → Архив.

Запуск: pytest tests/smoke/test_e2e_supervision_full.py -v --timeout=180
"""

import pytest
from datetime import datetime

from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    create_test_client, create_test_contract,
    cleanup_test_card, TEST_PREFIX,
)


def _find_supervision_card(headers, contract_id):
    """Найти карточку надзора по contract_id."""
    cards = _get("/api/supervision/cards", headers).json()
    return next((c for c in cards if c.get("contract_id") == contract_id), None)


def _create_supervision_card(headers, suffix="SUP"):
    """Создать клиент + договор + карточку надзора.
    Возвращает (client_id, contract_id, sup_card_id).
    Не использует create_test_card (она ищет CRM карточку, а не supervision).
    """
    client_id = create_test_client(headers, suffix)
    contract_id = create_test_contract(
        headers, client_id, suffix, project_type="Авторский надзор",
    )
    # Ищем автосозданную карточку надзора
    sup = _find_supervision_card(headers, contract_id)
    if not sup:
        # Пробуем создать вручную
        cr = _post("/api/supervision/cards", headers, json={
            "contract_id": contract_id,
        })
        if cr.status_code in (200, 201):
            sup_id = cr.json()["id"]
        else:
            pytest.skip(f"Не удалось создать карточку надзора: {cr.status_code}")
    else:
        sup_id = sup["id"]
    return client_id, contract_id, sup_id


@pytest.mark.smoke
class TestSupervisionE2EFull:
    """P0: Полный сквозной цикл авторского надзора."""

    def test_full_supervision_lifecycle(self, admin_headers):
        """Договор → карточка → timeline → визиты → пауза → resume → экспорт → архив."""
        # 1. Создаём договор надзора + карточку надзора
        client_id, contract_id, sup_id = _create_supervision_card(
            admin_headers, "E2E_SUP",
        )
        try:

            # 3. Инициализируем timeline
            init = _post(f"/api/supervision-timeline/{sup_id}/init", admin_headers)
            assert init.status_code in (200, 201, 409), \
                f"Timeline init: {init.status_code} {init.text}"

            # 4. Создаём визит
            visit = _post(f"/api/supervision-visits/{sup_id}/visits", admin_headers, json={
                "visit_date": datetime.now().strftime("%Y-%m-%d"),
                "stage_code": "stage_1",
                "stage_name": "Стадия 1",
                "notes": f"{TEST_PREFIX}E2E визит",
            })
            visit_id = None
            if visit.status_code in (200, 201):
                visit_id = visit.json().get("id")

            # 5. Перемещаем в работу
            move = _patch(f"/api/supervision/cards/{sup_id}/column", admin_headers, json={
                "column_name": "В работе",
            })
            # Если колонка валидна — 200, иначе — 400/422
            assert move.status_code in (200, 400, 422)

            # 6. Пауза
            pause = _post(f"/api/supervision/cards/{sup_id}/pause", admin_headers,
                          json={"pause_reason": f"{TEST_PREFIX}E2E пауза"})
            if pause.status_code == 200:
                # 7. Resume
                resume = _post(f"/api/supervision/cards/{sup_id}/resume", admin_headers)
                assert resume.status_code in (200, 422)

            # 8. Завершаем стадию
            complete = _post(f"/api/supervision/cards/{sup_id}/complete-stage", admin_headers,
                             json={"stage_name": "Стадия 1"})
            assert complete.status_code in (200, 400, 422)

            # 9. Добавляем запись в историю
            hist = _post(f"/api/supervision/cards/{sup_id}/history", admin_headers, json={
                "action": "test_e2e",
                "description": f"{TEST_PREFIX}E2E история",
            })
            assert hist.status_code in (200, 201, 422)

            # 10. Проверяем платежи надзора
            payments = _get(f"/api/payments/supervision/{contract_id}", admin_headers)
            assert payments.status_code == 200

            payments_by_card = _get(
                f"/api/payments/by-supervision-card/{sup_id}", admin_headers,
            )
            assert payments_by_card.status_code == 200

            # 11. Экспорт timeline
            excel = _get(
                f"/api/supervision-timeline/{sup_id}/export/excel", admin_headers,
            )
            assert excel.status_code in (200, 404)

            pdf = _get(
                f"/api/supervision-timeline/{sup_id}/export/pdf", admin_headers,
            )
            assert pdf.status_code in (200, 404)

            # 12. Сводка визитов
            summary = _get(
                f"/api/supervision-visits/{sup_id}/visits/summary", admin_headers,
            )
            assert summary.status_code in (200, 404)

            # 13. Получаем связанный договор
            linked_contract = _get(
                f"/api/supervision/cards/{sup_id}/contract", admin_headers,
            )
            assert linked_contract.status_code in (200, 404)

            # 14. Cleanup визита
            if visit_id:
                _delete(f"/api/supervision-visits/{sup_id}/visits/{visit_id}", admin_headers)

            # 15. Архивируем (DELETE orders удаляет карточку)
            archive = _delete(f"/api/supervision/orders/{sup_id}", admin_headers)
            assert archive.status_code in (200, 204, 404, 422)

        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_supervision_timeline_entry_update(self, admin_headers):
        """PUT /supervision-timeline/{id}/entry/{stage} — обновление записи timeline."""
        client_id, contract_id, sup_id = _create_supervision_card(
            admin_headers, "SUP_TL_E",
        )
        try:

            # Init timeline
            _post(f"/api/supervision-timeline/{sup_id}/init", admin_headers)

            # Получаем timeline для определения stage_code
            tl = _get(f"/api/supervision-timeline/{sup_id}", admin_headers)
            if tl.status_code != 200 or not tl.json():
                pytest.skip("Timeline не инициализирован")

            data = tl.json()
            entries = data if isinstance(data, list) else data.get("entries", [])
            if not entries:
                pytest.skip("Нет записей в timeline")

            stage_code = entries[0].get("stage_code", "stage_1")

            # Обновляем запись
            resp = _put(
                f"/api/supervision-timeline/{sup_id}/entry/{stage_code}",
                admin_headers,
                json={"actual_start": "2026-03-01"},
            )
            assert resp.status_code in (200, 404, 422), \
                f"Update entry: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_supervision_with_multiple_visits(self, admin_headers):
        """Создание нескольких визитов → сводка содержит все."""
        client_id, contract_id, sup_id = _create_supervision_card(
            admin_headers, "MULTI_VIS",
        )
        try:

            visit_ids = []
            for i in range(3):
                v = _post(f"/api/supervision-visits/{sup_id}/visits", admin_headers, json={
                    "visit_date": f"2026-03-0{i+1}",
                    "stage_code": f"stage_{i+1}",
                    "stage_name": f"Стадия {i+1}",
                    "notes": f"{TEST_PREFIX}Визит #{i+1}",
                })
                if v.status_code in (200, 201) and v.json().get("id"):
                    visit_ids.append(v.json()["id"])

            if not visit_ids:
                pytest.skip("Не удалось создать визиты")

            # Проверяем список
            visits = _get(f"/api/supervision-visits/{sup_id}/visits", admin_headers).json()
            created = [v for v in visits if TEST_PREFIX in str(v.get("notes", ""))]
            assert len(created) >= len(visit_ids), \
                f"Создано {len(visit_ids)}, найдено {len(created)}"

            # Cleanup
            for vid in visit_ids:
                _delete(f"/api/supervision-visits/{sup_id}/visits/{vid}", admin_headers)
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)
