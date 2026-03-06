# -*- coding: utf-8 -*-
"""
MEDIUM/LOW тесты для DataAccess:
- CRM Workflow (submit/accept/reject/client-send/client-ok) — API-only, fallback None
- CRM Cards CRUD (create/update/delete/move + offline-очередь)
- Supervision Cards CRUD (create/update/delete/move/pause/resume + offline-очередь)
- Employees CRUD с fallback
- Archived cards (длинный TTL кеша)
- move_supervision_card — бизнес-ошибки 422 пробрасываются
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _make_da(api_client=None, db=None, online=True):
    """Создать DataAccess с моками."""
    from utils.data_access import DataAccess, _global_cache
    _global_cache.invalidate()
    mock_api = api_client or MagicMock()
    mock_db = db or MagicMock()
    mock_om = MagicMock()
    mock_om.is_online.return_value = online
    with patch('utils.data_access.get_offline_manager', return_value=mock_om):
        da = DataAccess(api_client=mock_api, db=mock_db)
    da._om = mock_om
    return da


# ==================== CRM Workflow ====================

class TestCRMWorkflow:
    """DataAccess CRM Workflow — API-only операции."""

    def test_workflow_submit_success(self):
        da = _make_da()
        da.api_client.workflow_submit.return_value = {"status": "submitted"}
        result = da.workflow_submit(1)
        assert result == {"status": "submitted"}

    def test_workflow_submit_api_error_returns_none(self):
        da = _make_da()
        da.api_client.workflow_submit.side_effect = Exception("API down")
        result = da.workflow_submit(1)
        assert result is None

    def test_workflow_submit_no_api_returns_none(self):
        from utils.data_access import DataAccess, _global_cache
        _global_cache.invalidate()
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = DataAccess(api_client=None, db=MagicMock())
        result = da.workflow_submit(1)
        assert result is None

    def test_workflow_accept_success(self):
        da = _make_da()
        da.api_client.workflow_accept.return_value = {"status": "accepted"}
        result = da.workflow_accept(1)
        assert result == {"status": "accepted"}

    def test_workflow_accept_api_error(self):
        da = _make_da()
        da.api_client.workflow_accept.side_effect = Exception("err")
        assert da.workflow_accept(1) is None

    def test_workflow_reject_success(self):
        da = _make_da()
        da.api_client.workflow_reject.return_value = {"status": "rejected"}
        result = da.workflow_reject(1, corrections_path="/path/to/corrections")
        assert result == {"status": "rejected"}
        da.api_client.workflow_reject.assert_called_once_with(1, corrections_path="/path/to/corrections")

    def test_workflow_reject_no_path(self):
        da = _make_da()
        da.api_client.workflow_reject.return_value = {"status": "rejected"}
        da.workflow_reject(1)
        da.api_client.workflow_reject.assert_called_once_with(1, corrections_path='')

    def test_workflow_reject_api_error(self):
        da = _make_da()
        da.api_client.workflow_reject.side_effect = Exception("err")
        assert da.workflow_reject(1) is None

    def test_workflow_client_send_success(self):
        da = _make_da()
        da.api_client.workflow_client_send.return_value = {"status": "sent"}
        assert da.workflow_client_send(1) == {"status": "sent"}

    def test_workflow_client_send_api_error(self):
        da = _make_da()
        da.api_client.workflow_client_send.side_effect = Exception("err")
        assert da.workflow_client_send(1) is None

    def test_workflow_client_ok_success(self):
        da = _make_da()
        da.api_client.workflow_client_ok.return_value = {"status": "ok"}
        assert da.workflow_client_ok(1) == {"status": "ok"}

    def test_workflow_client_ok_api_error(self):
        da = _make_da()
        da.api_client.workflow_client_ok.side_effect = Exception("err")
        assert da.workflow_client_ok(1) is None

    def test_get_workflow_state_success(self):
        da = _make_da()
        da.api_client.get_workflow_state.return_value = [{"stage": "design"}]
        result = da.get_workflow_state(1)
        assert result == [{"stage": "design"}]

    def test_get_workflow_state_no_api(self):
        from utils.data_access import DataAccess, _global_cache
        _global_cache.invalidate()
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = DataAccess(api_client=None, db=MagicMock())
        assert da.get_workflow_state(1) is None

    def test_get_workflow_state_api_error(self):
        da = _make_da()
        da.api_client.get_workflow_state.side_effect = Exception("err")
        assert da.get_workflow_state(1) is None


# ==================== CRM Cards CRUD ====================

class TestCRMCardsCRUD:
    """DataAccess CRM карточки — CRUD с fallback и очередью."""

    def test_get_crm_cards_api_success(self):
        da = _make_da()
        da.api_client.get_crm_cards.return_value = [{"id": 1}]
        result = da.get_crm_cards("Индивидуальный")
        assert result == [{"id": 1}]

    def test_get_crm_cards_api_fails_fallback(self):
        da = _make_da()
        da.api_client.get_crm_cards.side_effect = Exception("err")
        da.db.get_crm_cards_by_project_type.return_value = [{"id": 2}]
        result = da.get_crm_cards("Индивидуальный")
        assert result == [{"id": 2}]

    def test_get_crm_card_api_success(self):
        da = _make_da()
        da.api_client.get_crm_card.return_value = {"id": 10}
        assert da.get_crm_card(10) == {"id": 10}

    def test_get_crm_card_api_fails_fallback(self):
        da = _make_da()
        da.api_client.get_crm_card.side_effect = Exception("err")
        da.db.get_crm_card_data.return_value = {"id": 10, "source": "local"}
        result = da.get_crm_card(10)
        assert result["source"] == "local"

    def test_get_archived_crm_cards_api(self):
        da = _make_da()
        da.api_client.get_archived_crm_cards.return_value = [{"id": 5, "column_name": "СДАН"}]
        result = da.get_archived_crm_cards("Шаблонный")
        assert result[0]["column_name"] == "СДАН"

    def test_get_archived_crm_cards_fallback(self):
        da = _make_da()
        da.api_client.get_archived_crm_cards.side_effect = Exception("err")
        da.db.get_archived_crm_cards.return_value = [{"id": 5}]
        result = da.get_archived_crm_cards("Шаблонный")
        assert len(result) == 1

    def test_create_crm_card_online(self):
        da = _make_da()
        da.api_client.create_crm_card.return_value = {"id": 100}
        da.db.add_crm_card.return_value = 1
        result = da.create_crm_card({"contract_id": 10})
        assert result["id"] == 100

    def test_create_crm_card_api_fails_queues(self):
        from utils.api_client.exceptions import APIConnectionError
        da = _make_da()
        da.api_client.create_crm_card.side_effect = APIConnectionError("err")
        da.db.add_crm_card.return_value = 5
        with patch('utils.data_access.get_offline_manager', return_value=da._om):
            result = da.create_crm_card({"contract_id": 10})
        assert result["id"] == 5

    def test_update_crm_card_online(self):
        da = _make_da()
        da.api_client.update_crm_card.return_value = {"id": 1}
        assert da.update_crm_card(1, {"notes": "test"}) is True
        da.db.update_crm_card.assert_called_once()

    def test_delete_crm_card_online(self):
        da = _make_da()
        da.db.get_contract_id_by_crm_card.return_value = 10
        assert da.delete_crm_card(1) is True

    def test_update_crm_card_column(self):
        da = _make_da()
        da.api_client.update_crm_card.return_value = {"id": 1}
        assert da.update_crm_card_column(1, "В работе") is True
        da.db.update_crm_card_column.assert_called_once_with(1, "В работе")

    def test_move_crm_card(self):
        da = _make_da()
        da.api_client.move_crm_card.return_value = {"id": 1}
        assert da.move_crm_card(1, "СДАН") is True


# ==================== Supervision Cards CRUD ====================

class TestSupervisionCardsCRUD:
    """DataAccess Supervision — CRUD с fallback и очередью."""

    def test_get_active_cards_api(self):
        da = _make_da()
        da.api_client.get_supervision_cards.return_value = [{"id": 1}]
        result = da.get_supervision_cards_active()
        assert result == [{"id": 1}]

    def test_get_active_cards_fallback(self):
        da = _make_da()
        da.api_client.get_supervision_cards.side_effect = Exception("err")
        da.db.get_supervision_cards_active.return_value = [{"id": 2}]
        result = da.get_supervision_cards_active()
        assert result == [{"id": 2}]

    def test_get_archived_cards_api(self):
        da = _make_da()
        da.api_client.get_supervision_cards.return_value = [{"id": 3}]
        result = da.get_supervision_cards_archived()
        assert result == [{"id": 3}]

    def test_get_card_fallback(self):
        da = _make_da()
        da.api_client.get_supervision_card.side_effect = Exception("err")
        da.db.get_supervision_card_data.return_value = {"id": 1}
        assert da.get_supervision_card(1) == {"id": 1}

    def test_create_card_with_dict(self):
        da = _make_da()
        da.api_client.create_supervision_card.return_value = {"id": 50}
        da.db.add_supervision_card.return_value = 1
        result = da.create_supervision_card({"contract_id": 10})
        assert result["id"] == 50

    def test_create_card_with_int(self):
        """contract_id как int — конвертируется в dict."""
        da = _make_da()
        da.api_client.create_supervision_card.return_value = {"id": 60}
        da.db.add_supervision_card.return_value = 2
        result = da.create_supervision_card(10)
        assert result["id"] == 60

    def test_update_card(self):
        da = _make_da()
        da.api_client.update_supervision_card.return_value = {"id": 1}
        assert da.update_supervision_card(1, {"notes": "test"}) is True

    def test_update_card_column(self):
        da = _make_da()
        da.api_client.update_supervision_card.return_value = {"id": 1}
        assert da.update_supervision_card_column(1, "В работе") is True

    def test_complete_stage(self):
        da = _make_da()
        da.api_client.complete_supervision_stage.return_value = {"success": True}
        result = da.complete_supervision_stage(1, stage_name="STAGE_1_CERAMIC")
        assert result == {"success": True}

    def test_complete_stage_api_error(self):
        da = _make_da()
        da.api_client.complete_supervision_stage.side_effect = Exception("err")
        with patch('utils.data_access.get_offline_manager', return_value=da._om):
            result = da.complete_supervision_stage(1, stage_name="STAGE_1")
        assert result == {"success": True}  # Локально успешно

    def test_reset_stage_completion(self):
        da = _make_da()
        da.api_client.reset_supervision_stage_completion.return_value = {"ok": True}
        assert da.reset_supervision_stage_completion(1) is True

    def test_pause_card(self):
        da = _make_da()
        da.api_client.pause_supervision_card.return_value = {"paused": True}
        result = da.pause_supervision_card(1, reason="Ожидание материалов", employee_id=5)
        assert result == {"paused": True}

    def test_pause_card_api_error(self):
        da = _make_da()
        da.api_client.pause_supervision_card.side_effect = Exception("err")
        with patch('utils.data_access.get_offline_manager', return_value=da._om):
            result = da.pause_supervision_card(1, reason="test")
        assert result == {"success": True}

    def test_resume_card(self):
        da = _make_da()
        da.api_client.resume_supervision_card.return_value = {"resumed": True}
        result = da.resume_supervision_card(1, employee_id=3)
        assert result == {"resumed": True}

    def test_delete_supervision_order(self):
        da = _make_da()
        da.api_client.delete_supervision_order.return_value = True
        assert da.delete_supervision_order(10, 5) is True

    def test_get_contract_id_by_supervision_card_api(self):
        da = _make_da()
        da.api_client.get_contract_id_by_supervision_card.return_value = 42
        assert da.get_contract_id_by_supervision_card(1) == 42

    def test_get_contract_id_by_supervision_card_fallback(self):
        da = _make_da()
        da.api_client.get_contract_id_by_supervision_card.side_effect = Exception("err")
        da.db.get_contract_id_by_supervision_card.return_value = 42
        assert da.get_contract_id_by_supervision_card(1) == 42


# ==================== move_supervision_card — бизнес-ошибки ====================

class TestMoveSupervisionCard:
    """move_supervision_card — бизнес-ошибки 422 пробрасываются, сетевые → очередь."""

    def test_move_success(self):
        da = _make_da()
        da.api_client.move_supervision_card.return_value = {"id": 1}
        assert da.move_supervision_card(1, "В работе") is True
        da.db.update_supervision_card_column.assert_called()

    def test_move_422_raises(self):
        """422 бизнес-ошибка — пробрасывается наверх."""
        from utils.api_client.exceptions import APIResponseError
        da = _make_da()
        da.api_client.move_supervision_card.side_effect = APIResponseError("Запрещено", status_code=422)
        with pytest.raises(APIResponseError):
            da.move_supervision_card(1, "СДАН")

    def test_move_400_raises(self):
        from utils.api_client.exceptions import APIResponseError
        da = _make_da()
        da.api_client.move_supervision_card.side_effect = APIResponseError("Bad request", status_code=400)
        with pytest.raises(APIResponseError):
            da.move_supervision_card(1, "СДАН")

    def test_move_network_error_queues(self):
        """Сетевая ошибка — обновляет локально + ставит в очередь."""
        from utils.api_client.exceptions import APIConnectionError
        da = _make_da()
        da.api_client.move_supervision_card.side_effect = APIConnectionError("timeout")
        with patch('utils.data_access.get_offline_manager', return_value=da._om):
            result = da.move_supervision_card(1, "В работе")
        assert result is True
        da.db.update_supervision_card_column.assert_called()

    def test_move_offline(self):
        """Офлайн — обновляет локально + очередь."""
        from utils.data_access import DataAccess, _global_cache
        _global_cache.invalidate()
        mock_api = MagicMock()
        mock_db = MagicMock()
        mock_om = MagicMock()
        mock_om.is_online.return_value = False
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            da = DataAccess(api_client=mock_api, db=mock_db)
        da._is_online = False
        result = da.move_supervision_card(1, "Пауза")
        assert result is True
        mock_db.update_supervision_card_column.assert_called()


# ==================== Employees CRUD ====================

class TestEmployeesCRUD:
    """DataAccess Employees — CRUD с fallback."""

    def test_get_all_employees_api(self):
        da = _make_da()
        da.api_client.get_employees.return_value = [{"id": 1, "name": "Тест"}]
        result = da.get_all_employees()
        assert result[0]["name"] == "Тест"

    def test_get_all_employees_fallback(self):
        da = _make_da()
        da.api_client.get_employees.side_effect = Exception("err")
        da.db.get_all_employees.return_value = [{"id": 1}]
        assert len(da.get_all_employees()) == 1

    def test_get_employees_by_position_api(self):
        da = _make_da()
        da.api_client.get_employees_by_position.return_value = [{"id": 1}]
        result = da.get_employees_by_position("Дизайнер")
        assert len(result) == 1

    def test_get_employees_by_position_fallback(self):
        da = _make_da()
        da.api_client.get_employees_by_position.side_effect = Exception("err")
        da.db.get_employees_by_position.return_value = [{"id": 2}]
        result = da.get_employees_by_position("Дизайнер")
        assert result == [{"id": 2}]

    def test_get_employee_fallback(self):
        da = _make_da()
        da.api_client.get_employee.side_effect = Exception("err")
        da.db.get_employee_by_id.return_value = {"id": 5}
        assert da.get_employee(5) == {"id": 5}

    def test_create_employee_online(self):
        da = _make_da()
        da.api_client.create_employee.return_value = {"id": 100}
        da.db.add_employee.return_value = 1
        result = da.create_employee({"full_name": "Новый"})
        assert result["id"] == 100

    def test_update_employee_online(self):
        da = _make_da()
        da.api_client.update_employee.return_value = {"id": 1}
        assert da.update_employee(1, {"full_name": "Updated"}) is True

    def test_delete_employee_online(self):
        da = _make_da()
        da.api_client.delete_employee.return_value = True
        assert da.delete_employee(1) is True

    def test_get_employee_active_assignments_api(self):
        da = _make_da()
        da.api_client.get_crm_cards.return_value = [
            {"id": 1, "contract_number": "DP-001", "team": [
                {"executor_id": 5, "status": "active", "stage_name": "Дизайн"}
            ]}
        ]
        result = da.get_employee_active_assignments(5)
        assert len(result) >= 1

    def test_get_employee_active_assignments_fallback(self):
        da = _make_da()
        da.api_client.get_crm_cards.side_effect = Exception("err")
        da.db.get_employee_active_assignments.return_value = [{"card_id": 1}]
        result = da.get_employee_active_assignments(5)
        assert len(result) >= 1

    def test_get_employee_active_assignments_no_method(self):
        da = _make_da()
        da.api_client.get_crm_cards.side_effect = Exception("err")
        del da.db.get_employee_active_assignments
        result = da.get_employee_active_assignments(5)
        assert result == []


# ==================== Contract operations ====================

class TestContractOperations:
    """DataAccess contracts — create/update/delete с очередью."""

    def test_create_contract_online(self):
        da = _make_da()
        da.api_client.create_contract.return_value = {"id": 200}
        da.db.add_contract.return_value = 1
        result = da.create_contract({"number": "DP-001"})
        assert result["id"] == 200

    def test_create_contract_api_returns_list(self):
        da = _make_da()
        da.api_client.create_contract.return_value = [{"id": 300}]
        da.db.add_contract.return_value = 1
        result = da.create_contract({"number": "DP-002"})
        assert result["id"] == 300

    def test_update_contract(self):
        da = _make_da()
        da.api_client.update_contract.return_value = {"id": 1}
        assert da.update_contract(1, {"status": "active"}) is True

    def test_delete_contract_online(self):
        da = _make_da()
        da.api_client.delete_contract.return_value = True
        da.db.get_crm_card_id_by_contract.return_value = 10
        assert da.delete_contract(1) is True

    def test_delete_contract_api_fails(self):
        from utils.api_client.exceptions import APIConnectionError
        da = _make_da()
        da.api_client.delete_contract.side_effect = APIConnectionError("err")
        da.db.get_crm_card_id_by_contract.return_value = 10
        da.db.delete_order.return_value = True
        with patch('utils.data_access.get_offline_manager', return_value=da._om):
            result = da.delete_contract(1)
        assert result is True

    def test_check_contract_number_exists(self):
        da = _make_da()
        da.api_client.check_contract_number_exists.return_value = True
        assert da.check_contract_number_exists("DP-001") is True

    def test_get_contracts_paginated_api(self):
        da = _make_da()
        da.api_client.get_contracts_paginated.return_value = ([{"id": 1}], 100)
        contracts, total = da.get_contracts_paginated(skip=0, limit=50)
        assert total == 100

    def test_get_contracts_paginated_fallback(self):
        da = _make_da()
        da.api_client.get_contracts_paginated.side_effect = Exception("err")
        da.db.get_all_contracts.return_value = [{"id": 1}]
        da.db.get_contracts_count.return_value = 1
        contracts, total = da.get_contracts_paginated()
        assert total == 1

    def test_get_contracts_count_by_client(self):
        da = _make_da()
        da.api_client.get_contracts.return_value = [
            {"client_id": 5}, {"client_id": 5}, {"client_id": 10}
        ]
        assert da.get_contracts_count_by_client(5) == 2

    def test_get_contracts_count_by_client_fallback(self):
        da = _make_da()
        da.api_client.get_contracts.side_effect = Exception("err")
        da.db.get_contracts_count_by_client.return_value = 3
        assert da.get_contracts_count_by_client(5) == 3

    def test_get_clients_paginated_api(self):
        da = _make_da()
        da.api_client.get_clients_paginated.return_value = ([{"id": 1}], 50)
        clients, total = da.get_clients_paginated()
        assert total == 50

    def test_get_clients_paginated_fallback(self):
        da = _make_da()
        da.api_client.get_clients_paginated.side_effect = Exception("err")
        da.db.get_all_clients.return_value = [{"id": 1}]
        da.db.get_clients_count.return_value = 1
        clients, total = da.get_clients_paginated()
        assert total == 1
