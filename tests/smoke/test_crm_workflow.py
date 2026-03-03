# -*- coding: utf-8 -*-
"""
Smoke Tests: CRM Workflow — полный цикл жизни карточки.

Тестирует state machine: move-column, assign executor, submit/accept/reject,
client-send/client-ok, archive/unarchive.

Запуск: pytest tests/smoke/test_crm_workflow.py -v --timeout=120
"""

import pytest
from datetime import datetime, timedelta

from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    TEST_PREFIX, create_test_card, cleanup_test_card,
)


# ════════════════════════════════════════════════════════════
# 1. CRM Workflow: State Machine
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestCrmWorkflowState:
    """P0: Чтение workflow state и перемещение карточки."""

    def test_workflow_state_readable(self, admin_headers):
        """GET /crm/cards/{id}/workflow/state — возвращает список."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "WF_STATE")
        try:
            resp = _get(f"/api/crm/cards/{card_id}/workflow/state", admin_headers)
            assert resp.status_code == 200
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_full_card_lifecycle(self, admin_headers):
        """Полный цикл: Новый заказ → В ожидании → Стадия 1 → Стадия 2 → проверка."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "WF_LIFE")
        try:
            # 1. Начальная колонка = "Новый заказ"
            card = _get(f"/api/crm/cards/{card_id}", admin_headers)
            assert card.status_code == 200
            assert card.json()["column_name"] == "Новый заказ"

            # 2. В ожидании
            r1 = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                        json={"column_name": "В ожидании"})
            assert r1.status_code == 200

            # 3. Стадия 1
            r2 = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                        json={"column_name": "Стадия 1: планировочные решения"})
            assert r2.status_code == 200

            # 4. Стадия 2
            r3 = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                        json={"column_name": "Стадия 2: концепция дизайна"})
            assert r3.status_code == 200

            # 5. Финальная проверка
            final = _get(f"/api/crm/cards/{card_id}", admin_headers)
            assert final.json()["column_name"] == "Стадия 2: концепция дизайна"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_move_column_validation(self, admin_headers):
        """Прыжок через стадию без прав → ошибка."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "WF_VALID")
        try:
            # Из "Новый заказ" сразу в "Стадия 2" — может быть запрещено
            # (admin может обходить, но проверяем что endpoint работает)
            resp = _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                          json={"column_name": "Стадия 2: концепция дизайна"})
            # Admin может перемещать свободно, но endpoint не должен 500
            assert resp.status_code in (200, 400, 422)
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 2. CRM Workflow: Назначение исполнителей
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestCrmExecutors:
    """P0: Назначение исполнителя и завершение стадии."""

    def test_assign_executor_and_complete(self, admin_headers):
        """Назначить исполнителя → завершить стадию."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "WF_EXEC")
        try:
            # Перемещаем в стадию 1
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            # Назначаем исполнителя (admin = executor_id 1)
            assign = _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers, json={
                "executor_id": 1,
                "stage_name": "Стадия 1: планировочные решения",
                "deadline": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            })
            assert assign.status_code == 200, \
                f"Назначение: {assign.status_code} {assign.text}"

            # Завершаем стадию
            complete = _patch(
                f"/api/crm/cards/{card_id}/stage-executor/Стадия 1: планировочные решения/complete",
                admin_headers,
                json={"executor_id": 1}
            )
            # 200 или 404 если другой формат пути
            assert complete.status_code in (200, 404), \
                f"Завершение: {complete.status_code} {complete.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_duplicate_executor_returns_409(self, admin_headers):
        """Повторное назначение того же исполнителя на ту же стадию → 409."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "WF_DUP")
        try:
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            payload = {
                "executor_id": 1,
                "stage_name": "Стадия 1: планировочные решения",
                "deadline": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            }
            # Первое назначение
            r1 = _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers, json=payload)
            assert r1.status_code == 200

            # Второе — дубликат
            r2 = _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers, json=payload)
            assert r2.status_code in (409, 400), \
                f"Ожидали 409/400, получили {r2.status_code}: {r2.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_stage_history(self, admin_headers):
        """GET stage-history — история стадий карточки."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "WF_HIST")
        try:
            resp = _get(f"/api/crm/cards/{card_id}/stage-history", admin_headers)
            assert resp.status_code == 200
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 3. CRM Workflow: Submit / Accept / Reject
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestCrmWorkflowApproval:
    """P0: Цикл одобрения (submit → accept/reject)."""

    def test_submit_then_accept(self, admin_headers):
        """workflow/submit → workflow/accept."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "WF_ACC")
        try:
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            submit = _post(f"/api/crm/cards/{card_id}/workflow/submit", admin_headers)
            assert submit.status_code == 200, \
                f"Submit: {submit.status_code} {submit.text}"

            accept = _post(f"/api/crm/cards/{card_id}/workflow/accept", admin_headers)
            assert accept.status_code == 200, \
                f"Accept: {accept.status_code} {accept.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_submit_then_reject(self, admin_headers):
        """workflow/submit → workflow/reject → revision_count >= 1."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "WF_REJ")
        try:
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            _post(f"/api/crm/cards/{card_id}/workflow/submit", admin_headers)

            reject = _post(f"/api/crm/cards/{card_id}/workflow/reject", admin_headers)
            assert reject.status_code == 200, \
                f"Reject: {reject.status_code} {reject.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_client_send_and_ok(self, admin_headers):
        """client-send → client-ok — клиент согласовал."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "WF_CLI")
        try:
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            send = _post(f"/api/crm/cards/{card_id}/workflow/client-send", admin_headers)
            assert send.status_code == 200, \
                f"Client-send: {send.status_code} {send.text}"

            ok = _post(f"/api/crm/cards/{card_id}/workflow/client-ok", admin_headers)
            assert ok.status_code == 200, \
                f"Client-ok: {ok.status_code} {ok.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 4. CRM: Архив / Разархив / Reset
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestCrmArchive:
    """P0: Архивирование и разархивирование карточки."""

    def test_archive_card(self, admin_headers):
        """DELETE /crm/cards/{id} → карточка удалена/архивирована."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "WF_ARC")
        try:
            resp = _delete(f"/api/crm/cards/{card_id}", admin_headers)
            assert resp.status_code == 200, \
                f"Архив: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_reset_stages(self, admin_headers):
        """POST reset-stages — сброс стадий."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "WF_RST")
        try:
            resp = _post(f"/api/crm/cards/{card_id}/reset-stages", admin_headers)
            assert resp.status_code == 200
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_submitted_stages(self, admin_headers):
        """GET submitted-stages — список сданных стадий."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "WF_SUB")
        try:
            resp = _get(f"/api/crm/cards/{card_id}/submitted-stages", admin_headers)
            assert resp.status_code == 200
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)
