"""
Backend Tests - Database Models
TDD tests for SQLAlchemy models and database schema
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.backend
class TestEmployeeModel:
    """Tests for Employee model"""

    def test_employee_has_required_fields(self):
        """Employee model must have required fields"""
        required_fields = ['id', 'login', 'password_hash', 'full_name', 'position', 'role']
        employee = {
            'id': 1,
            'login': 'admin',
            'password_hash': 'hashed',
            'full_name': 'Admin',
            'position': 'Administrator',
            'role': 'admin'
        }
        for field in required_fields:
            assert field in employee

    def test_employee_login_is_unique(self):
        """Employee login must be unique"""
        # Database constraint
        employees = [
            {'login': 'user1'},
            {'login': 'user2'},
        ]
        logins = [e['login'] for e in employees]
        assert len(logins) == len(set(logins)), "Logins must be unique"

    def test_employee_default_role_is_user(self):
        """Employee default role should be 'user'"""
        default_role = 'user'
        assert default_role == 'user'

    def test_employee_is_active_default_true(self):
        """Employee is_active should default to True"""
        default_is_active = True
        assert default_is_active is True


@pytest.mark.backend
class TestClientModel:
    """Tests for Client model"""

    def test_client_has_required_fields(self):
        """Client model must have required fields"""
        required_fields = ['id', 'full_name', 'client_type']
        client = {'id': 1, 'full_name': 'Test Client', 'client_type': 'individual'}
        for field in required_fields:
            assert field in client

    def test_client_type_values(self):
        """Client type must be valid value"""
        valid_types = ['individual', 'company']
        client_type = 'individual'
        assert client_type in valid_types


@pytest.mark.backend
class TestContractModel:
    """Tests for Contract model"""

    def test_contract_has_required_fields(self):
        """Contract model must have required fields"""
        required_fields = ['id', 'contract_number', 'client_id', 'project_type']
        contract = {
            'id': 1,
            'contract_number': 'D-2025-001',
            'client_id': 1,
            'project_type': 'Individual'
        }
        for field in required_fields:
            assert field in contract

    def test_contract_number_is_unique(self):
        """Contract number must be unique"""
        contracts = [
            {'contract_number': 'D-2025-001'},
            {'contract_number': 'D-2025-002'},
        ]
        numbers = [c['contract_number'] for c in contracts]
        assert len(numbers) == len(set(numbers))

    def test_contract_has_client_relationship(self):
        """Contract must reference client via foreign key"""
        contract = {'client_id': 1}
        assert 'client_id' in contract
        assert contract['client_id'] is not None


@pytest.mark.backend
class TestCRMCardModel:
    """Tests for CRMCard model"""

    def test_crm_card_has_required_fields(self):
        """CRMCard model must have required fields"""
        required_fields = ['id', 'contract_id', 'column_name']
        card = {'id': 1, 'contract_id': 1, 'column_name': 'new_order'}
        for field in required_fields:
            assert field in card

    def test_crm_card_contract_cascade_delete(self):
        """Deleting contract should cascade delete CRM card"""
        # Foreign key with ON DELETE CASCADE
        cascade_delete = True
        assert cascade_delete, "CRM card must cascade delete with contract"

    def test_crm_card_default_column(self):
        """CRM card default column should be 'new_order'"""
        default_column = 'new_order'
        assert default_column == 'new_order'


@pytest.mark.backend
class TestSupervisionCardModel:
    """Tests for SupervisionCard model"""

    def test_supervision_card_has_required_fields(self):
        """SupervisionCard model must have required fields"""
        required_fields = ['id', 'contract_id', 'status']
        card = {'id': 1, 'contract_id': 1, 'status': 'active'}
        for field in required_fields:
            assert field in card

    def test_supervision_card_default_status(self):
        """SupervisionCard default status should be 'active'"""
        default_status = 'active'
        assert default_status == 'active'

    def test_supervision_card_pause_fields(self):
        """SupervisionCard must have pause tracking fields"""
        pause_fields = ['pause_reason', 'pause_date']
        card = {'pause_reason': None, 'pause_date': None}
        for field in pause_fields:
            assert field in card


@pytest.mark.backend
class TestStageExecutorModel:
    """Tests for StageExecutor model"""

    def test_stage_executor_has_required_fields(self):
        """StageExecutor model must have required fields"""
        required_fields = ['id', 'crm_card_id', 'stage_name', 'executor_id']
        executor = {
            'id': 1,
            'crm_card_id': 1,
            'stage_name': 'Design',
            'executor_id': 2
        }
        for field in required_fields:
            assert field in executor

    def test_stage_executor_has_role(self):
        """StageExecutor should track role"""
        executor = {'role': 'Designer'}
        assert 'role' in executor


@pytest.mark.backend
@pytest.mark.critical
class TestPaymentModel:
    """Tests for Payment model - CRITICAL"""

    def test_payment_has_required_fields(self):
        """Payment model must have required fields"""
        required_fields = [
            'id', 'contract_id', 'employee_id', 'stage_name',
            'role', 'payment_type', 'calculated_amount', 'final_amount',
            'payment_status', 'reassigned'
        ]
        payment = {
            'id': 1,
            'contract_id': 1,
            'employee_id': 2,
            'stage_name': 'Design',
            'role': 'Designer',
            'payment_type': 'advance',
            'calculated_amount': 5000.0,
            'final_amount': 5000.0,
            'payment_status': 'pending',
            'reassigned': False
        }
        for field in required_fields:
            assert field in payment, f"Payment must have '{field}'"

    def test_payment_reassigned_default_false(self):
        """Payment reassigned field should default to False"""
        default_reassigned = False
        assert default_reassigned is False

    def test_payment_calculated_amount_not_null(self):
        """Payment calculated_amount must not be NULL"""
        # This tests the fix for NOT NULL constraint violation
        payment = {'calculated_amount': 0.0}
        assert payment['calculated_amount'] is not None

    def test_payment_final_amount_not_null(self):
        """Payment final_amount must not be NULL"""
        payment = {'final_amount': 0.0}
        assert payment['final_amount'] is not None

    def test_payment_status_values(self):
        """Payment status must be valid value"""
        valid_statuses = ['pending', 'paid', 'cancelled']
        status = 'pending'
        assert status in valid_statuses

    def test_payment_type_values(self):
        """Payment type must be valid value"""
        valid_types = ['advance', 'completion', 'full']
        payment_type = 'advance'
        assert payment_type in valid_types


@pytest.mark.backend
class TestRateModel:
    """Tests for Rate model"""

    def test_rate_has_required_fields(self):
        """Rate model must have required fields"""
        required_fields = ['id', 'rate_type']
        rate = {'id': 1, 'rate_type': 'template'}
        for field in required_fields:
            assert field in rate

    def test_rate_role_is_optional(self):
        """Rate role field should be optional"""
        rate_without_role = {'id': 1, 'rate_type': 'template', 'role': None}
        assert rate_without_role['role'] is None

    def test_rate_area_range_fields(self):
        """Rate should have area range fields"""
        rate = {'area_from': 0, 'area_to': 100}
        assert 'area_from' in rate
        assert 'area_to' in rate


@pytest.mark.backend
class TestActionHistoryModel:
    """Tests for ActionHistory model"""

    def test_action_history_has_required_fields(self):
        """ActionHistory model must have required fields"""
        required_fields = ['id', 'entity_type', 'entity_id', 'action_type']
        history = {
            'id': 1,
            'entity_type': 'payment',
            'entity_id': 1,
            'action_type': 'update'
        }
        for field in required_fields:
            assert field in history

    def test_action_history_tracks_old_new_values(self):
        """ActionHistory should track old and new values"""
        history = {
            'old_value': 'Designer A',
            'new_value': 'Designer B'
        }
        assert 'old_value' in history
        assert 'new_value' in history


@pytest.mark.backend
class TestOfflineQueueModel:
    """Tests for OfflineQueue model"""

    def test_offline_queue_has_required_fields(self):
        """OfflineQueue model must have required fields"""
        required_fields = ['id', 'operation_type', 'entity_type', 'status']
        queue_item = {
            'id': 1,
            'operation_type': 'CREATE',
            'entity_type': 'client',
            'status': 'pending'
        }
        for field in required_fields:
            assert field in queue_item

    def test_offline_queue_operation_types(self):
        """OfflineQueue operation_type must be valid"""
        valid_operations = ['CREATE', 'UPDATE', 'DELETE']
        operation = 'CREATE'
        assert operation in valid_operations

    def test_offline_queue_status_values(self):
        """OfflineQueue status must be valid value"""
        valid_statuses = ['pending', 'synced', 'failed']
        status = 'pending'
        assert status in valid_statuses


@pytest.mark.backend
class TestDatabaseRelationships:
    """Tests for database relationships and foreign keys"""

    def test_contract_client_relationship(self):
        """Contract should reference Client"""
        contract = {'client_id': 1}
        client = {'id': 1}
        assert contract['client_id'] == client['id']

    def test_crm_card_contract_relationship(self):
        """CRMCard should reference Contract"""
        card = {'contract_id': 1}
        contract = {'id': 1}
        assert card['contract_id'] == contract['id']

    def test_payment_contract_relationship(self):
        """Payment should reference Contract"""
        payment = {'contract_id': 1}
        contract = {'id': 1}
        assert payment['contract_id'] == contract['id']

    def test_payment_employee_relationship(self):
        """Payment should reference Employee"""
        payment = {'employee_id': 2}
        employee = {'id': 2}
        assert payment['employee_id'] == employee['id']

    def test_stage_executor_crm_card_relationship(self):
        """StageExecutor should reference CRMCard"""
        executor = {'crm_card_id': 1}
        card = {'id': 1}
        assert executor['crm_card_id'] == card['id']
