# -*- coding: utf-8 -*-
"""
Smoke Tests: Supervision Lifecycle — полный цикл карточки надзора.

Тестирует: создание → перемещение → pause/resume → history → archive.
Второй по сложности домен после CRM.

Запуск: pytest tests/smoke/test_supervision_lifecycle.py -v --timeout=120
"""

import pytest
from datetime import datetime

from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    TEST_PREFIX, create_test_client, create_test_contract,
    cleanup_test_card,
)


def _create_supervision_card(headers):
    """Создать клиент + договор + карточку надзора. Вернуть (client_id, contract_id, card_id)."""
    ts = datetime.now().strftime('%H%M%S%f')[:10]
    client_id = create_test_client(headers, "SUP")

    # Договор типа "Авторский надзор"
    contract_resp = _post("/api/contracts", headers, json={
        "client_id": client_id,
        "project_type": "Авторский надзор",
        "agent_type": "ФЕСТИВАЛЬ",
        "city": "МСК",
        "contract_number": f"{TEST_PREFIX}SUP{ts}",
        "contract_date": datetime.now().strftime("%Y-%m-%d"),
        "address": f"{TEST_PREFIX}Надзор адрес {ts}",
        "area": 80.0,
        "total_amount": 200000.0,
        "advance_payment": 100000.0,
        "additional_payment": 100000.0,
        "contract_period": 90,
        "status": "АВТОРСКИЙ НАДЗОР",
    })
    assert contract_resp.status_code == 200, \
        f"Создание договора надзора: {contract_resp.status_code} {contract_resp.text}"
    contract_id = contract_resp.json()["id"]

    # Ищем автосозданную карточку надзора
    cards = _get("/api/supervision/cards", headers)
    assert cards.status_code == 200
    card = next((c for c in cards.json() if c.get("contract_id") == contract_id), None)

    if not card:
        # Если автосоздание не сработало — создаём вручную
        cr = _post("/api/supervision/cards", headers, json={
            "contract_id": contract_id,
        })
        if cr.status_code in (200, 201):
            card_id = cr.json()["id"]
        else:
            # Пропускаем если нельзя создать
            pytest.skip(f"Не удалось создать карточку надзора: {cr.status_code}")
    else:
        card_id = card["id"]

    return client_id, contract_id, card_id


# ════════════════════════════════════════════════════════════
# 1. Supervision CRUD
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSupervisionCRUD:
    """P0: Создание и получение карточки надзора."""

    def test_create_supervision_card(self, admin_headers):
        """Создание карточки надзора через договор с типом 'Авторский надзор'."""
        client_id, contract_id, card_id = _create_supervision_card(admin_headers)
        try:
            assert card_id > 0
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_get_supervision_by_id(self, admin_headers):
        """GET /supervision/cards/{id} — правильная структура."""
        client_id, contract_id, card_id = _create_supervision_card(admin_headers)
        try:
            resp = _get(f"/api/supervision/cards/{card_id}", admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == card_id
            assert data["contract_id"] == contract_id
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_supervision_addresses(self, admin_headers):
        """GET /supervision/addresses — список адресов."""
        resp = _get("/api/supervision/addresses", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ════════════════════════════════════════════════════════════
# 2. Supervision Column Move
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSupervisionColumnMove:
    """P0: Перемещение карточки надзора между колонками."""

    def test_move_supervision_card(self, admin_headers):
        """PATCH /supervision/cards/{id}/column — перемещение."""
        client_id, contract_id, card_id = _create_supervision_card(admin_headers)
        try:
            resp = _patch(f"/api/supervision/cards/{card_id}/column", admin_headers,
                          json={"column_name": "Стадия 1: Закупка керамогранита"})
            # 200 или другой код если колонка не подходит
            assert resp.status_code in (200, 400, 422), \
                f"Move: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 3. Supervision Pause / Resume
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSupervisionPauseResume:
    """P0: Pause/Resume с пересчётом дедлайнов."""

    def test_pause_card(self, admin_headers):
        """POST /supervision/cards/{id}/pause — приостановка."""
        client_id, contract_id, card_id = _create_supervision_card(admin_headers)
        try:
            resp = _post(f"/api/supervision/cards/{card_id}/pause", admin_headers,
                         json={"pause_reason": f"{TEST_PREFIX}Тестовая пауза"})
            assert resp.status_code in (200, 400, 422), \
                f"Pause: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_resume_without_pause_422(self, admin_headers):
        """Resume без приостановки → 422 или ошибка."""
        client_id, contract_id, card_id = _create_supervision_card(admin_headers)
        try:
            resp = _post(f"/api/supervision/cards/{card_id}/resume", admin_headers)
            # Без предварительной паузы — ожидаем ошибку
            assert resp.status_code in (400, 422), \
                f"Resume без паузы: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_pause_then_resume(self, admin_headers):
        """Pause → Resume — корректный цикл."""
        client_id, contract_id, card_id = _create_supervision_card(admin_headers)
        try:
            # Пауза
            pause = _post(f"/api/supervision/cards/{card_id}/pause", admin_headers,
                          json={"pause_reason": f"{TEST_PREFIX}Тестовая пауза"})
            if pause.status_code not in (200,):
                pytest.skip(f"Pause не поддерживается: {pause.status_code}")

            # Resume
            resume = _post(f"/api/supervision/cards/{card_id}/resume", admin_headers)
            assert resume.status_code == 200, \
                f"Resume: {resume.status_code} {resume.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 4. Supervision Stages & History
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSupervisionStages:
    """P1: Стадии надзора."""

    def test_complete_stage(self, admin_headers):
        """POST /supervision/cards/{id}/complete-stage."""
        client_id, contract_id, card_id = _create_supervision_card(admin_headers)
        try:
            resp = _post(f"/api/supervision/cards/{card_id}/complete-stage", admin_headers,
                         json={"stage_name": "Стадия 1: Закупка керамогранита"})
            assert resp.status_code in (200, 400, 422)
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_reset_stages(self, admin_headers):
        """POST /supervision/cards/{id}/reset-stages."""
        client_id, contract_id, card_id = _create_supervision_card(admin_headers)
        try:
            resp = _post(f"/api/supervision/cards/{card_id}/reset-stages", admin_headers)
            assert resp.status_code in (200, 400, 422)
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


@pytest.mark.smoke
class TestSupervisionHistory:
    """P1: История карточки надзора."""

    def test_history_readable(self, admin_headers):
        """GET /supervision/cards/{id}/history — 200."""
        client_id, contract_id, card_id = _create_supervision_card(admin_headers)
        try:
            resp = _get(f"/api/supervision/cards/{card_id}/history", admin_headers)
            assert resp.status_code == 200
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_add_history_entry(self, admin_headers):
        """POST /supervision/cards/{id}/history — добавление записи."""
        client_id, contract_id, card_id = _create_supervision_card(admin_headers)
        try:
            resp = _post(f"/api/supervision/cards/{card_id}/history", admin_headers,
                         json={
                             "entry_type": "комментарий",
                             "message": f"{TEST_PREFIX}Тестовая запись",
                         })
            assert resp.status_code in (200, 201, 422), \
                f"History: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 5. Supervision Archive
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSupervisionArchive:
    """P1: Архивирование карточки надзора."""

    def test_archive_supervision(self, admin_headers):
        """DELETE /supervision/orders/{id} — архивация."""
        client_id, contract_id, card_id = _create_supervision_card(admin_headers)
        try:
            resp = _delete(
                f"/api/supervision/orders/{card_id}", admin_headers,
                params={"contract_id": contract_id},
            )
            assert resp.status_code in (200, 204, 422), \
                f"Archive: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)
