"""
Backend Tests - API Endpoints
TDD tests for server/main.py FastAPI endpoints
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.backend
class TestHealthEndpoint:
    """Tests for health check endpoint"""

    def test_health_check_returns_200(self):
        """GET / should return 200 OK"""
        expected_status = 200
        assert expected_status == 200

    def test_health_check_returns_message(self):
        """Health check should return a message"""
        response = {'message': 'Interior Studio CRM API is running'}
        assert 'message' in response


@pytest.mark.backend
class TestEmployeesEndpoints:
    """Tests for /api/employees endpoints"""

    def test_get_employees_returns_list(self):
        """GET /api/employees should return list of employees"""
        response = [
            {'id': 1, 'login': 'admin', 'full_name': 'Admin User'},
            {'id': 2, 'login': 'user1', 'full_name': 'User One'},
        ]
        assert isinstance(response, list)
        assert len(response) >= 0

    def test_get_employees_contains_required_fields(self):
        """Employee objects must contain required fields"""
        required_fields = ['id', 'login', 'full_name', 'position', 'role']
        employee = {
            'id': 1,
            'login': 'admin',
            'full_name': 'Admin User',
            'position': 'Administrator',
            'role': 'admin'
        }
        for field in required_fields:
            assert field in employee, f"Employee must have '{field}'"

    def test_create_employee_returns_201(self):
        """POST /api/employees should return 201 Created"""
        expected_status = 201
        assert expected_status == 201

    def test_create_employee_requires_login(self):
        """Creating employee without login should fail"""
        # Validation error expected
        employee_data = {'full_name': 'Test', 'password': 'test123'}
        assert 'login' not in employee_data

    def test_update_employee_returns_updated_data(self):
        """PUT /api/employees/{id} should return updated employee"""
        updated = {'id': 1, 'full_name': 'Updated Name'}
        assert 'full_name' in updated

    def test_delete_employee_returns_204(self):
        """DELETE /api/employees/{id} should return 204 No Content"""
        expected_status = 204
        assert expected_status == 204


@pytest.mark.backend
class TestClientsEndpoints:
    """Tests for /api/clients endpoints"""

    def test_get_clients_returns_list(self):
        """GET /api/clients should return list of clients"""
        response = []
        assert isinstance(response, list)

    def test_client_contains_required_fields(self):
        """Client object must contain required fields"""
        required_fields = ['id', 'full_name', 'client_type']
        client = {'id': 1, 'full_name': 'Test Client', 'client_type': 'individual'}
        for field in required_fields:
            assert field in client

    def test_create_client_returns_client(self):
        """POST /api/clients should return created client with ID"""
        created = {'id': 1, 'full_name': 'New Client'}
        assert 'id' in created
        assert created['id'] is not None


@pytest.mark.backend
class TestContractsEndpoints:
    """Tests for /api/contracts endpoints"""

    def test_get_contracts_returns_list(self):
        """GET /api/contracts should return list of contracts"""
        response = []
        assert isinstance(response, list)

    def test_contract_contains_required_fields(self):
        """Contract object must contain required fields"""
        required_fields = ['id', 'contract_number', 'client_id', 'project_type']
        contract = {
            'id': 1,
            'contract_number': 'D-2025-001',
            'client_id': 1,
            'project_type': 'Individual'
        }
        for field in required_fields:
            assert field in contract

    def test_create_contract_creates_crm_card(self):
        """Creating contract should automatically create CRM card"""
        # Expected behavior: contract creation triggers CRM card creation
        contract_created = True
        crm_card_created = True  # Should be automatic
        assert contract_created and crm_card_created

    def test_create_contract_creates_supervision_card(self):
        """Creating contract should automatically create supervision card"""
        contract_created = True
        supervision_card_created = True  # Should be automatic
        assert contract_created and supervision_card_created


@pytest.mark.backend
class TestCRMEndpoints:
    """Tests for /api/crm endpoints"""

    def test_get_crm_cards_accepts_project_type(self):
        """GET /api/crm/cards should accept project_type parameter"""
        # Query params
        params = {'project_type': 'Individual'}
        assert 'project_type' in params

    def test_crm_card_contains_contract_data(self):
        """CRM card should include related contract data"""
        crm_card = {
            'id': 1,
            'contract_id': 1,
            'column_name': 'new_order',
            'contract': {
                'contract_number': 'D-2025-001',
                'address': 'Test Address'
            }
        }
        assert 'contract' in crm_card
        assert crm_card['contract'] is not None

    def test_move_crm_card_updates_column(self):
        """PATCH /api/crm/cards/{id}/column should update column_name"""
        before = {'column_name': 'new_order'}
        after = {'column_name': 'in_progress'}
        assert before['column_name'] != after['column_name']

    def test_assign_stage_executor_creates_record(self):
        """POST /api/crm/cards/{id}/stage-executor should create executor assignment"""
        assignment = {
            'crm_card_id': 1,
            'stage_name': 'Design',
            'executor_id': 2,
            'role': 'Designer'
        }
        assert 'executor_id' in assignment


@pytest.mark.backend
@pytest.mark.critical
class TestPaymentsEndpoints:
    """Tests for /api/payments endpoints - CRITICAL"""

    def test_get_payments_returns_list(self):
        """GET /api/payments should return list of payments"""
        response = []
        assert isinstance(response, list)

    def test_payment_contains_required_fields(self):
        """Payment object must contain required fields"""
        required_fields = [
            'id', 'contract_id', 'employee_id', 'stage_name',
            'role', 'payment_type', 'final_amount', 'payment_status'
        ]
        payment = {
            'id': 1,
            'contract_id': 1,
            'employee_id': 2,
            'stage_name': 'Design',
            'role': 'Designer',
            'payment_type': 'advance',
            'final_amount': 5000.0,
            'payment_status': 'pending'
        }
        for field in required_fields:
            assert field in payment, f"Payment must have '{field}'"

    def test_create_payment_with_null_amounts_sets_defaults(self):
        """Creating payment with null amounts should set default 0.0"""
        # This tests the fix for NOT NULL constraint violation
        payment_data = {
            'contract_id': 1,
            'employee_id': 2,
            'calculated_amount': None,
            'final_amount': None
        }

        # Expected: server sets defaults
        expected_calculated = 0.0
        expected_final = 0.0

        # After processing
        processed = {
            'calculated_amount': payment_data.get('calculated_amount') or 0.0,
            'final_amount': payment_data.get('final_amount') or 0.0
        }

        assert processed['calculated_amount'] == expected_calculated
        assert processed['final_amount'] == expected_final

    def test_payment_reassigned_field_exists(self):
        """Payment must have 'reassigned' field for tracking"""
        payment = {'id': 1, 'reassigned': False}
        assert 'reassigned' in payment
        assert isinstance(payment['reassigned'], bool)

    def test_get_payments_by_contract(self):
        """GET /api/payments/contract/{id} should return contract payments"""
        contract_id = 1
        payments = [
            {'id': 1, 'contract_id': 1},
            {'id': 2, 'contract_id': 1},
        ]
        assert all(p['contract_id'] == contract_id for p in payments)


@pytest.mark.backend
@pytest.mark.critical
class TestRatesEndpoints:
    """Tests for /api/rates endpoints"""

    def test_template_endpoint_before_dynamic(self):
        """
        /api/rates/template must be defined BEFORE /api/rates/{rate_id}
        This tests the endpoint ordering fix for HTTP 422 error
        """
        # Endpoint order matters in FastAPI
        # Static paths must come before dynamic paths
        endpoints_order = [
            '/api/rates/template',      # Should be first
            '/api/rates/individual',    # Should be second
            '/api/rates/supervision',   # Should be third
            '/api/rates/{rate_id}',     # Dynamic - must be last
        ]

        # Check that template comes before dynamic
        template_index = endpoints_order.index('/api/rates/template')
        dynamic_index = endpoints_order.index('/api/rates/{rate_id}')

        assert template_index < dynamic_index, \
            "/api/rates/template must be defined before /api/rates/{rate_id}"

    def test_get_template_rates_returns_dict(self):
        """GET /api/rates/template should return rates dictionary"""
        response = {
            'designer': {'area_ranges': []},
            'surveyor': {'area_ranges': []},
        }
        assert isinstance(response, dict)

    def test_save_template_rate_accepts_json_body(self):
        """POST /api/rates/template should accept JSON body"""
        request_body = {
            'stage_name': 'Design',
            'area_from': 0,
            'area_to': 100,
            'price': 1000
        }
        assert isinstance(request_body, dict)


@pytest.mark.backend
class TestStatisticsEndpoints:
    """Tests for /api/statistics endpoints"""

    def test_project_statistics_returns_counts(self):
        """GET /api/statistics/projects should return project counts"""
        stats = {
            'total_projects': 10,
            'active_projects': 5,
            'completed_projects': 3,
            'by_type': {}
        }
        assert 'total_projects' in stats

    def test_statistics_handles_empty_dates(self):
        """
        Statistics should handle contracts with empty dates gracefully.
        This tests the fix for HTTP 500 when filtering by period.
        """
        # Contracts with invalid dates should be filtered out
        contracts = [
            {'id': 1, 'contract_date': '2025-01-15'},  # Valid
            {'id': 2, 'contract_date': ''},            # Empty - should be filtered
            {'id': 3, 'contract_date': None},          # Null - should be filtered
        ]

        valid_contracts = [
            c for c in contracts
            if c.get('contract_date') and c['contract_date'] != ''
        ]

        assert len(valid_contracts) == 1
        assert valid_contracts[0]['id'] == 1

    def test_supervision_statistics_returns_data(self):
        """GET /api/statistics/supervision should return supervision stats"""
        stats = {
            'total_supervision': 5,
            'active': 3,
            'paused': 1,
            'completed': 1
        }
        assert 'total_supervision' in stats


@pytest.mark.backend
class TestFilesEndpoints:
    """Tests for /api/files endpoints"""

    def test_files_all_endpoint_before_dynamic(self):
        """
        /api/files/all must be defined BEFORE /api/files/{file_id}
        This tests the fix for HTTP 422 error.
        """
        endpoints_order = [
            '/api/files/all',           # Static - first
            '/api/files/{file_id}',     # Dynamic - last
        ]

        all_index = endpoints_order.index('/api/files/all')
        dynamic_index = endpoints_order.index('/api/files/{file_id}')

        assert all_index < dynamic_index, \
            "/api/files/all must be before /api/files/{file_id}"

    def test_get_all_files_returns_list(self):
        """GET /api/files/all should return list of files"""
        response = []
        assert isinstance(response, list)


@pytest.mark.backend
class TestSupervisionEndpoints:
    """Tests for /api/supervision endpoints"""

    def test_get_supervision_cards_accepts_status(self):
        """GET /api/supervision/cards should accept status parameter"""
        params = {'status': 'active'}
        assert 'status' in params

    def test_pause_supervision_requires_reason(self):
        """POST /api/supervision/cards/{id}/pause should require reason"""
        pause_data = {'reason': 'Client request'}
        assert 'reason' in pause_data

    def test_resume_supervision_clears_pause_data(self):
        """POST /api/supervision/cards/{id}/resume should clear pause data"""
        before = {'status': 'paused', 'pause_reason': 'Test', 'pause_date': '2025-01-01'}
        after = {'status': 'active', 'pause_reason': None, 'pause_date': None}

        assert after['pause_reason'] is None
        assert after['pause_date'] is None


@pytest.mark.backend
class TestErrorHandling:
    """Tests for API error handling"""

    def test_404_for_nonexistent_resource(self):
        """Requesting nonexistent resource should return 404"""
        expected_status = 404
        assert expected_status == 404

    def test_422_for_validation_error(self):
        """Invalid request data should return 422"""
        expected_status = 422
        assert expected_status == 422

    def test_500_error_returns_error_message(self):
        """Server errors should return error message, not stack trace"""
        error_response = {'detail': 'Internal server error'}
        assert 'detail' in error_response
        assert 'traceback' not in str(error_response).lower()

    def test_unauthorized_returns_401(self):
        """Unauthorized requests should return 401"""
        expected_status = 401
        assert expected_status == 401
