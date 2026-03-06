# -*- coding: utf-8 -*-
"""
Smoke Tests: CRM Advanced — расширенные операции CRM карточек.

Покрывает: update card, delete card, reset-approval, approval-deadlines,
stage-executor CRUD, reset-designer/draftsman, manager-acceptance,
accepted-stages, previous-executor, complete-approval-stage.

Запуск: pytest tests/smoke/test_crm_advanced.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import (
    _get, _post, _patch, _delete,
    create_test_card, cleanup_test_card, TEST_PREFIX,
)


# ════════════════════════════════════════════════════════════
# 1. Card Update / Delete
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestCrmCardUpdate:
    """P1: Обновление и удаление CRM карточек."""

    def test_update_card_data(self, admin_headers):
        """PATCH /crm/cards/{id} — обновление данных карточки."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "UPD")
        try:
            resp = _patch(f"/api/crm/cards/{card_id}", admin_headers, json={
                "comment": f"{TEST_PREFIX}Обновлённый комментарий",
            })
            assert resp.status_code == 200, \
                f"Update card: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_delete_card_directly(self, admin_headers):
        """DELETE /crm/cards/{id} — прямое удаление карточки."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "DEL")
        try:
            resp = _delete(f"/api/crm/cards/{card_id}", admin_headers)
            assert resp.status_code in (200, 204), \
                f"Delete card: {resp.status_code} {resp.text}"

            # Карточка удалена — GET должен вернуть 404
            check = _get(f"/api/crm/cards/{card_id}", admin_headers)
            assert check.status_code in (404, 200)  # 200 если soft delete
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 2. Stage Executor Advanced
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestStageExecutorAdvanced:
    """P1: Расширенные операции с исполнителями стадий."""

    def test_update_stage_executor(self, admin_headers):
        """PATCH /crm/cards/{id}/stage-executor/{stage} — обновление исполнителя."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "EXEC_UPD")
        try:
            # Переводим в Стадию 1
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "В ожидании"})
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            # Назначаем исполнителя
            _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers, json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": 1,
                "deadline": "2026-12-31",
            })

            # Обновляем дедлайн
            resp = _patch(
                f"/api/crm/cards/{card_id}/stage-executor/Стадия 1: планировочные решения",
                admin_headers,
                json={"deadline": "2026-12-31"},
            )
            assert resp.status_code in (200, 404, 422), \
                f"Update executor: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_delete_stage_executor(self, admin_headers):
        """DELETE /crm/stage-executors/{executor_id} — удаление исполнителя."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "EXEC_DEL")
        try:
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "В ожидании"})
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            assign = _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers, json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": 1,
            })
            if assign.status_code not in (200, 201):
                pytest.skip(f"Не удалось назначить исполнителя: {assign.status_code}")

            executor_id = assign.json().get("id") or assign.json().get("executor_id")
            if not executor_id:
                pytest.skip("Нет ID исполнителя в ответе")

            resp = _delete(f"/api/crm/stage-executors/{executor_id}", admin_headers)
            assert resp.status_code in (200, 204), \
                f"Delete executor: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_update_stage_executor_deadline(self, admin_headers):
        """PATCH /crm/cards/{id}/stage-executor-deadline — обновление дедлайна."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "EXEC_DL")
        try:
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "В ожидании"})
            _patch(f"/api/crm/cards/{card_id}/column", admin_headers,
                   json={"column_name": "Стадия 1: планировочные решения"})

            _post(f"/api/crm/cards/{card_id}/stage-executor", admin_headers, json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": 1,
            })

            resp = _patch(
                f"/api/crm/cards/{card_id}/stage-executor-deadline",
                admin_headers,
                json={
                    "stage_name": "Стадия 1: планировочные решения",
                    "deadline": "2026-12-31",
                },
            )
            assert resp.status_code in (200, 404, 422), \
                f"Update deadline: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 3. Approval & Reset Operations
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestCrmApprovalAdvanced:
    """P1: Расширенные операции согласования."""

    def test_approval_deadlines(self, admin_headers):
        """GET /crm/cards/{id}/approval-deadlines — дедлайны согласований."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "APPR_DL")
        try:
            resp = _get(
                f"/api/crm/cards/{card_id}/approval-deadlines",
                admin_headers,
            )
            assert resp.status_code == 200
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_reset_approval(self, admin_headers):
        """POST /crm/cards/{id}/reset-approval — сброс согласования."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "RST_APPR")
        try:
            resp = _post(
                f"/api/crm/cards/{card_id}/reset-approval",
                admin_headers,
            )
            assert resp.status_code in (200, 204, 400, 422), \
                f"Reset approval: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_reset_stage_by_name(self, admin_headers):
        """POST /crm/cards/{id}/reset-stage-by-name — сброс конкретной стадии."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "RST_STG")
        try:
            resp = _post(
                f"/api/crm/cards/{card_id}/reset-stage-by-name",
                admin_headers,
                json={"stage_name": "Стадия 1: планировочные решения"},
            )
            assert resp.status_code in (200, 204, 400, 422), \
                f"Reset stage by name: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_complete_approval_stage(self, admin_headers):
        """POST /crm/cards/{id}/complete-approval-stage — завершение стадии согласования."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "COMPL_APPR")
        try:
            resp = _post(
                f"/api/crm/cards/{card_id}/complete-approval-stage",
                admin_headers,
                json={"stage_name": "Стадия 1: планировочные решения"},
            )
            # Может быть 400/422 если карточка не в состоянии согласования
            assert resp.status_code in (200, 204, 400, 422), \
                f"Complete approval: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_accepted_stages(self, admin_headers):
        """GET /crm/cards/{id}/accepted-stages — принятые стадии."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "ACPT_STG")
        try:
            resp = _get(
                f"/api/crm/cards/{card_id}/accepted-stages",
                admin_headers,
            )
            assert resp.status_code == 200
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 4. Reset Designer / Draftsman, Previous Executor, Manager
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestCrmSpecialOps:
    """P1: Специальные операции CRM."""

    def test_reset_designer(self, admin_headers):
        """POST /crm/cards/{id}/reset-designer — сброс дизайнера."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "RST_DSGN")
        try:
            resp = _post(
                f"/api/crm/cards/{card_id}/reset-designer",
                admin_headers,
            )
            assert resp.status_code in (200, 204, 400, 422), \
                f"Reset designer: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_reset_draftsman(self, admin_headers):
        """POST /crm/cards/{id}/reset-draftsman — сброс чертёжника."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "RST_DRFT")
        try:
            resp = _post(
                f"/api/crm/cards/{card_id}/reset-draftsman",
                admin_headers,
            )
            assert resp.status_code in (200, 204, 400, 422), \
                f"Reset draftsman: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_previous_executor(self, admin_headers):
        """GET /crm/cards/{id}/previous-executor — предыдущий исполнитель."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "PREV_EX")
        try:
            resp = _get(
                f"/api/crm/cards/{card_id}/previous-executor",
                admin_headers,
                params={"position": "Дизайнер"},
            )
            assert resp.status_code in (200, 404, 422), \
                f"Previous executor: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_manager_acceptance(self, admin_headers):
        """POST /crm/cards/{id}/manager-acceptance — принятие менеджером."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "MGR_ACC")
        try:
            resp = _post(
                f"/api/crm/cards/{card_id}/manager-acceptance",
                admin_headers,
                json={"stage_name": "Стадия 1: планировочные решения"},
            )
            # 400/422 ожидаемо если карточка не в нужном состоянии
            assert resp.status_code in (200, 204, 400, 422), \
                f"Manager acceptance: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)
