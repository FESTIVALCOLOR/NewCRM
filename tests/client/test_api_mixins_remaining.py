# -*- coding: utf-8 -*-
"""
Тесты для оставшихся 6 API Client миксинов:
- utils/api_client/crm_mixin.py (CrmMixin)
- utils/api_client/files_mixin.py (FilesMixin)
- utils/api_client/payments_mixin.py (PaymentsMixin)
- utils/api_client/permissions_mixin.py (PermissionsMixin)
- utils/api_client/misc_mixin.py (MiscMixin)
- utils/api_client/supervision_mixin.py (SupervisionMixin)

Покрытие:
- HTTP метод + URL для каждого endpoint
- Обработка ответов (success + errors)
- Graceful degradation (return False/None/[] при ошибках)
- Бизнес-логика (fallback в get_crm_card, calculate_payment_amount и т.д.)
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.api_client.exceptions import APIError


class _FakeResponse:
    """Минимальная заглушка HTTP response."""
    def __init__(self, status_code=200, json_data=None, headers=None, text=''):
        self.status_code = status_code
        self._json = json_data
        self.headers = headers or {}
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("No JSON")
        return self._json


def _make_client():
    """Создать APIClient с замоканным _request и _handle_response."""
    from utils.api_client.base import APIClientBase
    from utils.api_client.crm_mixin import CrmMixin
    from utils.api_client.files_mixin import FilesMixin
    from utils.api_client.payments_mixin import PaymentsMixin
    from utils.api_client.permissions_mixin import PermissionsMixin
    from utils.api_client.misc_mixin import MiscMixin
    from utils.api_client.supervision_mixin import SupervisionMixin

    class TestClient(
        CrmMixin, FilesMixin, PaymentsMixin, PermissionsMixin,
        MiscMixin, SupervisionMixin, APIClientBase
    ):
        pass

    client = TestClient("https://test.example.com")
    client.set_token("test_token", "test_refresh")
    return client


# ==================== CrmMixin ====================

class TestCrmMixin:
    """CrmMixin — CRM карточки и стадии."""

    def test_get_crm_cards(self):
        client = _make_client()
        cards = [{"id": 1, "column_name": "Новый заказ"}]
        client._request = MagicMock(return_value=_FakeResponse(200, cards))
        client._handle_response = MagicMock(return_value=cards)
        result = client.get_crm_cards("Индивидуальный")
        client._request.assert_called_once()
        assert "project_type" in client._request.call_args[1].get("params", {})
        assert result == cards

    def test_get_crm_card_direct(self):
        client = _make_client()
        card = {"id": 5, "column_name": "В работе"}
        client._request = MagicMock(return_value=_FakeResponse(200, card))
        client._handle_response = MagicMock(return_value=card)
        result = client.get_crm_card(5)
        assert result == card

    def test_get_crm_card_fallback(self):
        """Если direct endpoint упал — ищем по всем типам."""
        client = _make_client()
        target = {"id": 7, "column_name": "Готов"}
        call_count = [0]

        def fake_request(method, url, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Not found")
            return _FakeResponse(200, [target])

        client._request = fake_request
        client._handle_response = lambda resp: resp.json()
        result = client.get_crm_card(7)
        assert result == target

    def test_get_crm_card_not_found_raises(self):
        """Если карточка не найдена ни в одном типе — APIError."""
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        with pytest.raises(APIError):
            client.get_crm_card(999)

    def test_create_crm_card(self):
        client = _make_client()
        new_card = {"id": 10, "column_name": "Новый заказ"}
        client._request = MagicMock(return_value=_FakeResponse(200, new_card))
        client._handle_response = MagicMock(return_value=new_card)
        result = client.create_crm_card({"contract_id": 1})
        assert result == new_card
        assert client._request.call_args[0][0] == 'POST'

    def test_update_crm_card(self):
        client = _make_client()
        updated = {"id": 5, "column_name": "Готов"}
        client._request = MagicMock(return_value=_FakeResponse(200, updated))
        client._handle_response = MagicMock(return_value=updated)
        result = client.update_crm_card(5, {"column_name": "Готов"})
        assert result == updated
        assert client._request.call_args[0][0] == 'PATCH'

    def test_move_crm_card(self):
        client = _make_client()
        moved = {"id": 5, "column_name": "Сдан"}
        client._request = MagicMock(return_value=_FakeResponse(200, moved))
        client._handle_response = MagicMock(return_value=moved)
        result = client.move_crm_card(5, "Сдан")
        assert "column" in client._request.call_args[0][1]

    def test_delete_crm_card(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        assert client.delete_crm_card(5) is True
        assert client._request.call_args[0][0] == 'DELETE'

    def test_assign_stage_executor(self):
        client = _make_client()
        data = {"stage_name": "Обмеры", "executor_id": 3}
        client._request = MagicMock(return_value=_FakeResponse(200, {"id": 1}))
        client._handle_response = MagicMock(return_value={"id": 1})
        result = client.assign_stage_executor(5, data)
        assert result == {"id": 1}
        assert client._request.call_args[0][0] == 'POST'

    def test_complete_stage(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {"completed": True}))
        client._handle_response = MagicMock(return_value={"completed": True})
        result = client.complete_stage(5, "Обмеры", True)
        assert result["completed"] is True

    def test_get_archived_crm_cards(self):
        client = _make_client()
        archived = [{"id": 1, "archived": True}]
        client._request = MagicMock(return_value=_FakeResponse(200, archived))
        client._handle_response = MagicMock(return_value=archived)
        result = client.get_archived_crm_cards("Индивидуальный")
        params = client._request.call_args[1].get("params", {})
        assert params.get("archived") is True

    def test_get_stage_executors(self):
        client = _make_client()
        card = {"id": 5, "stage_executors": [{"id": 1, "stage": "Обмеры"}]}
        client._request = MagicMock(return_value=_FakeResponse(200, card))
        client._handle_response = MagicMock(return_value=card)
        result = client.get_stage_executors(5)
        assert len(result) == 1

    def test_complete_stage_for_executor_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        assert client.complete_stage_for_executor(5, "Обмеры", 3) is True

    def test_complete_stage_for_executor_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.complete_stage_for_executor(5, "Обмеры", 3) is False

    def test_reset_designer_completion_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        assert client.reset_designer_completion(5) is True

    def test_reset_designer_completion_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.reset_designer_completion(5) is False

    def test_reset_draftsman_completion_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.reset_draftsman_completion(5) is False

    def test_complete_approval_stage_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        assert client.complete_approval_stage(5, "Стадия1") is True

    def test_complete_approval_stage_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.complete_approval_stage(5, "Стадия1") is False

    def test_save_manager_acceptance_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        assert client.save_manager_acceptance(5, "Обмеры", "Иванов", 1) is True

    def test_save_manager_acceptance_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.save_manager_acceptance(5, "Обмеры", "Иванов", 1) is False

    def test_workflow_submit(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {"status": "ok"}))
        client._handle_response = MagicMock(return_value={"status": "ok"})
        result = client.workflow_submit(5)
        assert "workflow/submit" in client._request.call_args[0][1]

    def test_workflow_reject_with_path(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.workflow_reject(5, corrections_path="/disk/path")
        json_arg = client._request.call_args[1].get("json", {})
        assert json_arg.get("revision_file_path") == "/disk/path"

    def test_workflow_reject_without_path(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.workflow_reject(5)
        json_arg = client._request.call_args[1].get("json", {})
        assert "revision_file_path" not in json_arg

    def test_get_workflow_state_empty(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, None))
        client._handle_response = MagicMock(return_value=None)
        result = client.get_workflow_state(5)
        assert result == []


# ==================== FilesMixin ====================

class TestFilesMixin:
    """FilesMixin — файлы проектов и Яндекс.Диск."""

    def test_get_contract_files_no_stage(self):
        client = _make_client()
        files = [{"id": 1, "file_name": "plan.pdf"}]
        client._request = MagicMock(return_value=_FakeResponse(200, files))
        client._handle_response = MagicMock(return_value=files)
        result = client.get_contract_files(10)
        assert result == files

    def test_get_contract_files_with_stage(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, []))
        client._handle_response = MagicMock(return_value=[])
        client.get_contract_files(10, stage="Обмеры")
        params = client._request.call_args[1].get("params", {})
        assert params.get("stage") == "Обмеры"

    def test_create_file_record(self):
        client = _make_client()
        created = {"id": 5}
        client._request = MagicMock(return_value=_FakeResponse(200, created))
        client._handle_response = MagicMock(return_value=created)
        result = client.create_file_record({"file_name": "test.pdf"})
        assert result == created
        assert client._request.call_args[0][0] == 'POST'

    def test_delete_file_record(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        assert client.delete_file_record(5) is True
        assert client._request.call_args[0][0] == 'DELETE'

    def test_get_updated_files(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, []))
        client._handle_response = MagicMock(return_value=[])
        client.get_updated_files("2026-01-01T00:00:00")
        # timeout=5, retry=False
        kw = client._request.call_args[1]
        assert kw.get("retry") is False
        assert kw.get("timeout") == 5

    def test_validate_files(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, []))
        client._handle_response = MagicMock(return_value=[])
        client.validate_files([1, 2, 3], auto_clean=True)
        json_arg = client._request.call_args[1].get("json", {})
        assert json_arg["file_ids"] == [1, 2, 3]
        assert json_arg["auto_clean"] is True

    def test_scan_contract_files_timeout(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.scan_contract_files(10, scope='supervision')
        assert client._request.call_args[1].get("timeout") == 60

    def test_upload_file_to_yandex(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {"path": "/ok"}))
        client._handle_response = MagicMock(return_value={"path": "/ok"})
        result = client.upload_file_to_yandex(b"data", "test.txt", "/disk/path")
        assert result == {"path": "/ok"}
        assert client._request.call_args[0][0] == 'POST'

    def test_add_project_file_success(self):
        client = _make_client()
        client.create_file_record = MagicMock(return_value={"id": 42})
        result = client.add_project_file(
            contract_id=1, stage="Обмеры", file_type="image",
            public_link="https://...", yandex_path="/disk/...", file_name="photo.jpg"
        )
        assert result == 42

    def test_add_project_file_error(self):
        client = _make_client()
        client.create_file_record = MagicMock(side_effect=Exception("fail"))
        result = client.add_project_file(
            contract_id=1, stage="Обмеры", file_type="image",
            public_link="", yandex_path="", file_name="x.jpg"
        )
        assert result is None

    def test_get_project_files_alias(self):
        """get_project_files — alias для get_contract_files."""
        client = _make_client()
        client.get_contract_files = MagicMock(return_value=[])
        client.get_project_files(10, "stage1")
        client.get_contract_files.assert_called_once_with(10, "stage1")

    def test_get_all_project_files_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        result = client.get_all_project_files()
        assert result == []

    def test_delete_project_file_success(self):
        client = _make_client()
        file_info = {"id": 5, "file_name": "test.pdf"}
        resp_seq = [_FakeResponse(200, file_info), _FakeResponse(200, {})]
        client._request = MagicMock(side_effect=resp_seq)
        client._handle_response = MagicMock(side_effect=[file_info, {}])
        result = client.delete_project_file(5)
        assert result == file_info

    def test_delete_project_file_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        result = client.delete_project_file(5)
        assert result is None

    def test_update_project_file_order_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        assert client.update_project_file_order(5, 3) is True

    def test_update_project_file_order_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.update_project_file_order(5, 3) is False


# ==================== PaymentsMixin ====================

class TestPaymentsMixin:
    """PaymentsMixin — платежи и расчёты."""

    def test_get_payments_for_contract(self):
        client = _make_client()
        payments = [{"id": 1, "amount": 5000}]
        client._request = MagicMock(return_value=_FakeResponse(200, payments))
        client._handle_response = MagicMock(return_value=payments)
        result = client.get_payments_for_contract(10)
        assert result == payments

    def test_create_payment(self):
        client = _make_client()
        created = {"id": 5}
        client._request = MagicMock(return_value=_FakeResponse(200, created))
        client._handle_response = MagicMock(return_value=created)
        result = client.create_payment({"contract_id": 1, "amount": 1000})
        assert result == created
        assert client._request.call_args[0][0] == 'POST'

    def test_get_payment(self):
        client = _make_client()
        payment = {"id": 5, "amount": 5000}
        client._request = MagicMock(return_value=_FakeResponse(200, payment))
        client._handle_response = MagicMock(return_value=payment)
        result = client.get_payment(5)
        assert result == payment

    def test_update_payment(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.update_payment(5, {"amount": 6000})
        assert client._request.call_args[0][0] == 'PUT'

    def test_delete_payment(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.delete_payment(5)
        assert client._request.call_args[0][0] == 'DELETE'

    def test_set_payments_report_month(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {"updated": 3}))
        client._handle_response = MagicMock(return_value={"updated": 3})
        result = client.set_payments_report_month(10, "2026-01")
        assert result["updated"] == 3

    def test_get_year_payments(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, []))
        client._handle_response = MagicMock(return_value=[])
        client.get_year_payments(2026, include_null_month=True)
        params = client._request.call_args[1].get("params", {})
        assert params["year"] == 2026
        assert params["include_null_month"] == 'true'

    def test_get_payments_by_type(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, []))
        client._handle_response = MagicMock(return_value=[])
        client.get_payments_by_type("Оклады", project_type_filter="Индивидуальный")
        params = client._request.call_args[1].get("params", {})
        assert params["payment_type"] == "Оклады"
        assert params["project_type_filter"] == "Индивидуальный"

    def test_get_payments_by_supervision_card(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, []))
        client._handle_response = MagicMock(return_value=[])
        client.get_payments_by_supervision_card(10)
        assert "by-supervision-card/10" in client._request.call_args[0][1]

    def test_mark_payment_as_paid(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.mark_payment_as_paid(5, employee_id=1)
        assert "mark-paid" in client._request.call_args[0][1]

    def test_calculate_payment_amount_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {"amount": 15000}))
        client._handle_response = MagicMock(return_value={"amount": 15000})
        result = client.calculate_payment_amount(1, 2, "Дизайнер")
        assert result == 15000

    def test_calculate_payment_amount_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        result = client.calculate_payment_amount(1, 2, "Дизайнер")
        assert result == 0

    def test_create_payment_record_success(self):
        client = _make_client()
        client.create_payment = MagicMock(return_value={"id": 99})
        result = client.create_payment_record(1, 2, "Дизайнер", stage_name="Обмеры")
        assert result == 99

    def test_create_payment_record_error(self):
        client = _make_client()
        client.create_payment = MagicMock(side_effect=Exception("fail"))
        result = client.create_payment_record(1, 2, "Дизайнер")
        assert result is None

    def test_recalculate_payments_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {"updated": 5}))
        client._handle_response = MagicMock(return_value={"updated": 5})
        result = client.recalculate_payments(contract_id=1, role="Дизайнер")
        assert result["updated"] == 5

    def test_recalculate_payments_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        result = client.recalculate_payments()
        assert result["status"] == "error"

    def test_update_payment_manual(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.update_payment_manual(5, 10000.0, report_month="2026-01")
        json_arg = client._request.call_args[1].get("json", {})
        assert json_arg["amount"] == 10000.0
        assert json_arg["report_month"] == "2026-01"


# ==================== PermissionsMixin ====================

class TestPermissionsMixin:
    """PermissionsMixin — права сотрудников."""

    def test_get_permission_definitions(self):
        client = _make_client()
        defs = [{"name": "can_edit", "description": "Редактирование"}]
        client._request = MagicMock(return_value=_FakeResponse(200, defs))
        client._handle_response = MagicMock(return_value=defs)
        result = client.get_permission_definitions()
        assert result == defs

    def test_get_employee_permissions(self):
        client = _make_client()
        perms = {"permissions": ["can_edit", "can_view"]}
        client._request = MagicMock(return_value=_FakeResponse(200, perms))
        client._handle_response = MagicMock(return_value=perms)
        result = client.get_employee_permissions(1)
        assert "permissions" in result

    def test_set_employee_permissions(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.set_employee_permissions(1, ["can_edit", "can_delete"])
        assert client._request.call_args[0][0] == 'PUT'
        json_arg = client._request.call_args[1].get("json", {})
        assert json_arg["permissions"] == ["can_edit", "can_delete"]

    def test_reset_employee_permissions(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.reset_employee_permissions(1)
        assert "reset-to-defaults" in client._request.call_args[0][1]

    def test_get_role_permissions_matrix(self):
        client = _make_client()
        matrix = {"leader": ["can_edit"]}
        client._request = MagicMock(return_value=_FakeResponse(200, matrix))
        client._handle_response = MagicMock(return_value=matrix)
        result = client.get_role_permissions_matrix()
        assert result == matrix

    def test_save_role_permissions_matrix(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.save_role_permissions_matrix({"leader": ["can_edit"]})
        assert client._request.call_args[0][0] == 'PUT'


# ==================== MiscMixin ====================

class TestMiscMixin:
    """MiscMixin — health, уведомления, синхронизация, агенты, города."""

    def test_health_check_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200))
        assert client.health_check() is True
        assert client._is_online is True

    def test_health_check_failure(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("timeout"))
        assert client.health_check() is False
        assert client._is_online is False

    def test_get_notifications(self):
        client = _make_client()
        notifs = [{"id": 1, "message": "Тест"}]
        client._request = MagicMock(return_value=_FakeResponse(200, notifs))
        client._handle_response = MagicMock(return_value=notifs)
        result = client.get_notifications(unread_only=True)
        assert result == notifs

    def test_mark_notification_read(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200))
        assert client.mark_notification_read(1) is True

    def test_sync(self):
        from datetime import datetime
        client = _make_client()
        sync_data = {"clients": [], "contracts": []}
        client._request = MagicMock(return_value=_FakeResponse(200, sync_data))
        client._handle_response = MagicMock(return_value=sync_data)
        result = client.sync(datetime(2026, 1, 1), ["clients", "contracts"])
        assert result == sync_data
        kw = client._request.call_args[1]
        assert kw.get("mark_offline") is False

    def test_get_all_stage_executors_success(self):
        client = _make_client()
        executors = [{"id": 1}]
        client._request = MagicMock(return_value=_FakeResponse(200, executors))
        client._handle_response = MagicMock(return_value=executors)
        result = client.get_all_stage_executors()
        assert result == executors

    def test_get_all_stage_executors_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        result = client.get_all_stage_executors()
        assert result == []

    def test_get_all_approval_deadlines_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.get_all_approval_deadlines() == []

    def test_get_all_action_history_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.get_all_action_history() == []

    def test_get_all_supervision_history_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.get_all_supervision_history() == []

    def test_add_action_history_success(self):
        client = _make_client()
        client.create_action_history = MagicMock(return_value={"id": 1})
        result = client.add_action_history(1, "create", "contract", 10, "Создан")
        assert result is True

    def test_add_action_history_error(self):
        client = _make_client()
        client.create_action_history = MagicMock(side_effect=Exception("fail"))
        result = client.add_action_history(1, "create", "contract", 10, "Создан")
        assert result is False

    def test_add_project_template_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {"id": 5}))
        client._handle_response = MagicMock(return_value={"id": 5})
        result = client.add_project_template(1, "https://example.com")
        assert result == 5

    def test_add_project_template_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.add_project_template(1, "https://...") is None

    def test_delete_project_template_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        assert client.delete_project_template(5) is True

    def test_delete_project_template_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.delete_project_template(5) is False

    def test_add_agent_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        assert client.add_agent("Иванов", "#FF0000") is True

    def test_add_agent_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.add_agent("Иванов", "#FF0000") is False

    def test_delete_agent_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        assert client.delete_agent(1) is True

    def test_delete_agent_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.delete_agent(1) is False

    def test_update_agent_color_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        assert client.update_agent_color("Иванов", "#00FF00") is True

    def test_get_agent_color_found(self):
        client = _make_client()
        client.get_all_agents = MagicMock(return_value=[
            {"name": "Иванов", "color": "#FF0000"},
            {"name": "Петров", "color": "#00FF00"},
        ])
        assert client.get_agent_color("Петров") == "#00FF00"

    def test_get_agent_color_not_found(self):
        client = _make_client()
        client.get_all_agents = MagicMock(return_value=[])
        assert client.get_agent_color("Несуществующий") is None

    def test_get_all_cities_success(self):
        client = _make_client()
        cities = [{"id": 1, "name": "Москва"}]
        client._request = MagicMock(return_value=_FakeResponse(200, cities))
        client._handle_response = MagicMock(return_value=cities)
        result = client.get_all_cities()
        assert result == cities

    def test_get_all_cities_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.get_all_cities() == []

    def test_add_city_success(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        assert client.add_city("Казань") is True

    def test_delete_city_error(self):
        client = _make_client()
        client._request = MagicMock(side_effect=Exception("fail"))
        assert client.delete_city(1) is False

    def test_search(self):
        client = _make_client()
        results = {"results": []}
        client._request = MagicMock(return_value=_FakeResponse(200, results))
        client._handle_response = MagicMock(return_value=results)
        result = client.search("test", limit=10)
        params = client._request.call_args[1].get("params", {})
        assert params["q"] == "test"
        assert params["limit"] == 10

    def test_get_norm_days_template(self):
        client = _make_client()
        template = {"stages": {}}
        client._request = MagicMock(return_value=_FakeResponse(200, template))
        client._handle_response = MagicMock(return_value=template)
        result = client.get_norm_days_template("Индивидуальный", "Квартира")
        assert result == template


# ==================== SupervisionMixin ====================

class TestSupervisionMixin:
    """SupervisionMixin — авторский надзор."""

    def test_get_supervision_cards(self):
        client = _make_client()
        cards = [{"id": 1, "column_name": "Авторский надзор"}]
        client._request = MagicMock(return_value=_FakeResponse(200, cards))
        client._handle_response = MagicMock(return_value=cards)
        result = client.get_supervision_cards("active")
        assert result == cards

    def test_get_supervision_card(self):
        client = _make_client()
        card = {"id": 5}
        client._request = MagicMock(return_value=_FakeResponse(200, card))
        client._handle_response = MagicMock(return_value=card)
        result = client.get_supervision_card(5)
        assert result == card

    def test_create_supervision_card(self):
        client = _make_client()
        created = {"id": 10}
        client._request = MagicMock(return_value=_FakeResponse(200, created))
        client._handle_response = MagicMock(return_value=created)
        result = client.create_supervision_card({"contract_id": 1})
        assert result == created
        assert client._request.call_args[0][0] == 'POST'

    def test_update_supervision_card(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.update_supervision_card(5, {"column_name": "Готов"})
        assert client._request.call_args[0][0] == 'PATCH'

    def test_move_supervision_card(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.move_supervision_card(5, "Сдан")
        assert "column" in client._request.call_args[0][1]

    def test_pause_supervision_card(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.pause_supervision_card(5, "Ожидание материалов")
        json_arg = client._request.call_args[1].get("json", {})
        assert json_arg["pause_reason"] == "Ожидание материалов"

    def test_resume_supervision_card_with_employee(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.resume_supervision_card(5, employee_id=3)
        json_arg = client._request.call_args[1].get("json", {})
        assert json_arg["employee_id"] == 3

    def test_resume_supervision_card_no_employee(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.resume_supervision_card(5)
        json_arg = client._request.call_args[1].get("json")
        assert json_arg is None

    def test_delete_supervision_order(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        assert client.delete_supervision_order(10, 5) is True

    def test_complete_supervision_stage(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {}))
        client._handle_response = MagicMock(return_value={})
        client.complete_supervision_stage(5, stage_name="Стадия 1")
        json_arg = client._request.call_args[1].get("json", {})
        assert json_arg["stage_name"] == "Стадия 1"

    def test_get_supervision_addresses(self):
        client = _make_client()
        addrs = ["ул. Ленина", "ул. Пушкина"]
        client._request = MagicMock(return_value=_FakeResponse(200, addrs))
        client._handle_response = MagicMock(return_value=addrs)
        result = client.get_supervision_addresses()
        assert len(result) == 2

    def test_get_contract_id_by_supervision_card(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {"contract_id": 42}))
        client._handle_response = MagicMock(return_value={"contract_id": 42})
        result = client.get_contract_id_by_supervision_card(5)
        assert result == 42

    def test_add_supervision_history(self):
        client = _make_client()
        client._request = MagicMock(return_value=_FakeResponse(200, {"id": 1}))
        client._handle_response = MagicMock(return_value={"id": 1})
        result = client.add_supervision_history(5, "moved", "Перемещено", 1)
        json_arg = client._request.call_args[1].get("json", {})
        assert json_arg["entry_type"] == "moved"
        assert json_arg["created_by"] == 1
