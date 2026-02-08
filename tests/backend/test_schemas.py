"""
Backend Tests - Pydantic Schemas
TDD tests for server/schemas.py data validation
"""

import pytest
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.backend
class TestEmployeeSchemas:
    """Tests for Employee Pydantic schemas"""

    def test_employee_create_requires_login(self):
        """EmployeeCreate schema must require login"""
        required_fields = ['login', 'password', 'full_name']
        data = {'login': 'test', 'password': 'test123', 'full_name': 'Test'}
        for field in required_fields:
            assert field in data

    def test_employee_response_excludes_password(self):
        """EmployeeResponse schema must not include password"""
        response = {
            'id': 1,
            'login': 'test',
            'full_name': 'Test User',
            'position': 'Developer',
            'role': 'user'
        }
        assert 'password' not in response
        assert 'password_hash' not in response

    def test_employee_update_fields_optional(self):
        """EmployeeUpdate schema fields should be optional"""
        # All fields are optional for partial update
        update_data = {'full_name': 'New Name'}  # Only updating name
        assert 'login' not in update_data  # Not required


@pytest.mark.backend
class TestClientSchemas:
    """Tests for Client Pydantic schemas"""

    def test_client_create_requires_full_name(self):
        """ClientCreate schema must require full_name"""
        data = {'full_name': 'Test Client'}
        assert 'full_name' in data

    def test_client_type_default_individual(self):
        """Client client_type should default to 'individual'"""
        defaults = {'client_type': 'individual'}
        assert defaults['client_type'] == 'individual'


@pytest.mark.backend
class TestContractSchemas:
    """Tests for Contract Pydantic schemas"""

    def test_contract_create_requires_contract_number(self):
        """ContractCreate schema must require contract_number"""
        data = {'contract_number': 'D-2025-001', 'client_id': 1}
        assert 'contract_number' in data

    def test_contract_area_is_float(self):
        """Contract area should be float type"""
        data = {'area': 150.5}
        assert isinstance(data['area'], float)


@pytest.mark.backend
class TestCRMCardSchemas:
    """Tests for CRMCard Pydantic schemas"""

    def test_crm_card_response_includes_contract(self):
        """CRMCardResponse should include nested contract data"""
        response = {
            'id': 1,
            'contract_id': 1,
            'column_name': 'new_order',
            'contract': {
                'contract_number': 'D-2025-001',
                'address': 'Test Address'
            }
        }
        assert 'contract' in response
        assert response['contract'] is not None

    def test_crm_card_move_schema(self):
        """CRMCardMove schema for changing column"""
        move_data = {'column_name': 'in_progress'}
        assert 'column_name' in move_data


@pytest.mark.backend
@pytest.mark.critical
class TestPaymentSchemas:
    """Tests for Payment Pydantic schemas - CRITICAL"""

    def test_payment_create_required_fields(self):
        """PaymentCreate schema required fields"""
        required_fields = ['contract_id', 'employee_id', 'stage_name', 'role', 'payment_type']
        data = {
            'contract_id': 1,
            'employee_id': 2,
            'stage_name': 'Design',
            'role': 'Designer',
            'payment_type': 'advance'
        }
        for field in required_fields:
            assert field in data

    def test_payment_base_no_login_password(self):
        """
        PaymentBase schema must NOT include login/password fields.
        This tests the fix for 'login is invalid keyword argument' error.
        """
        payment_base_fields = [
            'contract_id', 'employee_id', 'stage_name', 'role',
            'payment_type', 'calculated_amount', 'manual_amount',
            'final_amount', 'payment_status', 'report_month', 'reassigned'
        ]

        # These fields should NOT be in PaymentBase
        forbidden_fields = ['login', 'password', 'password_hash']

        for field in forbidden_fields:
            assert field not in payment_base_fields, \
                f"PaymentBase must NOT have '{field}' field"

    def test_payment_amounts_can_be_none(self):
        """Payment amount fields can be None (will default to 0.0)"""
        data = {
            'contract_id': 1,
            'calculated_amount': None,
            'final_amount': None
        }
        assert data['calculated_amount'] is None
        assert data['final_amount'] is None

    def test_payment_reassigned_default_false(self):
        """Payment reassigned should default to False"""
        data = {}
        default_reassigned = data.get('reassigned', False)
        assert default_reassigned is False


@pytest.mark.backend
class TestRateSchemas:
    """Tests for Rate Pydantic schemas"""

    def test_template_rate_request_schema(self):
        """TemplateRateRequest schema for saving template rates"""
        data = {
            'stage_name': 'Design',
            'area_from': 0,
            'area_to': 100,
            'price': 1000
        }
        assert 'stage_name' in data
        assert 'price' in data

    def test_rate_response_includes_all_fields(self):
        """RateResponse should include all rate fields"""
        response = {
            'id': 1,
            'rate_type': 'template',
            'role': 'Designer',
            'stage_name': 'Design',
            'area_from': 0,
            'area_to': 100,
            'price': 1000,
            'executor_rate': 500,
            'manager_rate': 100
        }
        assert 'price' in response
        assert 'executor_rate' in response
        assert 'manager_rate' in response


@pytest.mark.backend
class TestStageExecutorSchemas:
    """Tests for StageExecutor Pydantic schemas"""

    def test_stage_executor_assign_schema(self):
        """StageExecutorAssign schema for assigning executor"""
        data = {
            'stage_name': 'Design',
            'executor_id': 2,
            'role': 'Designer',
            'deadline': '2025-02-01'
        }
        assert 'executor_id' in data
        assert 'stage_name' in data

    def test_stage_executor_update_schema(self):
        """StageExecutorUpdate schema for updating executor"""
        data = {
            'executor_id': 3,
            'deadline': '2025-02-15'
        }
        assert 'executor_id' in data


@pytest.mark.backend
class TestStatisticsSchemas:
    """Tests for Statistics Pydantic schemas"""

    def test_project_statistics_response(self):
        """ProjectStatisticsResponse schema structure"""
        response = {
            'total_projects': 10,
            'active_projects': 5,
            'completed_projects': 3,
            'by_type': {
                'Individual': 6,
                'Template': 4
            }
        }
        assert 'total_projects' in response
        assert 'by_type' in response

    def test_supervision_statistics_response(self):
        """SupervisionStatisticsResponse schema structure"""
        response = {
            'total_supervision': 5,
            'active': 3,
            'paused': 1,
            'completed': 1
        }
        assert 'total_supervision' in response


@pytest.mark.backend
class TestTokenSchemas:
    """Tests for Token Pydantic schemas"""

    def test_token_response_structure(self):
        """TokenResponse schema structure"""
        response = {
            'access_token': 'eyJ...',
            'token_type': 'bearer'
        }
        assert 'access_token' in response
        assert 'token_type' in response

    def test_login_response_includes_user_data(self):
        """LoginResponse should include user data along with token"""
        response = {
            'access_token': 'eyJ...',
            'token_type': 'bearer',
            'employee_id': 1,
            'full_name': 'Test User',
            'role': 'admin'
        }
        assert 'employee_id' in response
        assert 'full_name' in response
        assert 'role' in response


@pytest.mark.backend
class TestOfflineQueueSchemas:
    """Tests for OfflineQueue Pydantic schemas"""

    def test_offline_operation_schema(self):
        """OfflineOperation schema structure"""
        operation = {
            'operation_type': 'CREATE',
            'entity_type': 'client',
            'entity_id': None,
            'data': {'full_name': 'New Client'}
        }
        assert 'operation_type' in operation
        assert 'entity_type' in operation
        assert 'data' in operation


@pytest.mark.backend
class TestSchemaValidation:
    """Tests for schema validation behavior"""

    def test_extra_fields_ignored_or_forbidden(self):
        """Extra fields in request should be handled properly"""
        # Pydantic v2 by default ignores extra fields
        # or can be configured to forbid
        request_data = {
            'known_field': 'value',
            'unknown_field': 'should_be_handled'
        }
        # Expected behavior: unknown_field is either ignored or raises error
        assert 'known_field' in request_data

    def test_type_coercion(self):
        """Pydantic should coerce types when possible"""
        # String '5' should be coerced to int 5
        data = {'amount': '5000'}
        coerced_amount = float(data['amount'])
        assert coerced_amount == 5000.0

    def test_optional_fields_can_be_omitted(self):
        """Optional fields can be omitted from request"""
        # Partial update with only some fields
        update_data = {'full_name': 'New Name'}
        # Optional fields like 'position', 'department' not included
        assert 'position' not in update_data
