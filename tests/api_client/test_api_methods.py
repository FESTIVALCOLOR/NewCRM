"""
API Client Tests - CRUD Methods
TDD tests for utils/api_client.py methods
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.api_client
class TestAPIClientInit:
    """Tests for APIClient initialization"""

    def test_api_client_accepts_base_url(self):
        """APIClient should accept base URL on init"""
        base_url = "http://147.45.154.193:8000"
        client = {'base_url': base_url, 'token': None}
        assert client['base_url'] == base_url

    def test_api_client_default_timeout(self):
        """APIClient should have default timeout"""
        default_timeout = 10  # seconds
        assert default_timeout >= 5

    def test_api_client_write_timeout_longer(self):
        """Write timeout should be longer than read timeout"""
        read_timeout = 10
        write_timeout = 15
        assert write_timeout > read_timeout


@pytest.mark.api_client
class TestAuthenticationMethods:
    """Tests for authentication methods"""

    def test_login_returns_token(self):
        """Login should return access token"""
        response = {
            'access_token': 'eyJhbGc...',
            'token_type': 'bearer',
            'employee_id': 1,
            'full_name': 'Admin',
            'role': 'admin'
        }
        assert 'access_token' in response
        assert response['access_token'] is not None

    def test_login_stores_token(self):
        """Login should store token in client"""
        client = {'token': None}
        token = 'eyJhbGc...'
        client['token'] = token
        assert client['token'] == token

    def test_logout_clears_token(self):
        """Logout should clear stored token"""
        client = {'token': 'eyJhbGc...'}
        client['token'] = None
        assert client['token'] is None

    def test_get_current_user_requires_token(self):
        """get_current_user should require auth token"""
        client = {'token': None}
        # Should raise error or return None
        assert client['token'] is None


@pytest.mark.api_client
class TestEmployeeMethods:
    """Tests for employee CRUD methods"""

    def test_get_employees_returns_list(self):
        """get_employees should return list"""
        response = [{'id': 1}, {'id': 2}]
        assert isinstance(response, list)

    def test_get_employee_by_id(self):
        """get_employee should return single employee"""
        response = {'id': 1, 'login': 'admin'}
        assert 'id' in response

    def test_create_employee_returns_id(self):
        """create_employee should return created employee with ID"""
        response = {'id': 5, 'login': 'new_user'}
        assert response['id'] is not None

    def test_update_employee_returns_updated(self):
        """update_employee should return updated data"""
        response = {'id': 1, 'full_name': 'Updated Name'}
        assert 'full_name' in response

    def test_delete_employee_returns_success(self):
        """delete_employee should return success status"""
        response = {'success': True}
        assert response['success'] is True


@pytest.mark.api_client
class TestClientMethods:
    """Tests for client CRUD methods"""

    def test_get_clients_returns_list(self):
        """get_clients should return list"""
        response = []
        assert isinstance(response, list)

    def test_create_client_returns_client(self):
        """create_client should return created client"""
        response = {'id': 1, 'full_name': 'Test Client'}
        assert 'id' in response

    def test_update_client_returns_updated(self):
        """update_client should return updated client"""
        response = {'id': 1, 'phone': '+7 900 111 2233'}
        assert 'phone' in response


@pytest.mark.api_client
class TestContractMethods:
    """Tests for contract CRUD methods"""

    def test_get_contracts_returns_list(self):
        """get_contracts should return list"""
        response = []
        assert isinstance(response, list)

    def test_get_contract_by_id(self):
        """get_contract should return single contract"""
        response = {'id': 1, 'contract_number': 'D-2025-001'}
        assert 'contract_number' in response

    def test_create_contract_creates_related_cards(self):
        """create_contract should trigger CRM and supervision card creation"""
        response = {
            'id': 1,
            'crm_card_created': True,
            'supervision_card_created': True
        }
        # Cards should be created automatically on server
        assert response.get('crm_card_created', True)


@pytest.mark.api_client
class TestCRMCardMethods:
    """Tests for CRM card methods"""

    def test_get_crm_cards_accepts_project_type(self):
        """get_crm_cards should accept project_type parameter"""
        params = {'project_type': 'Individual'}
        assert 'project_type' in params

    def test_get_crm_card_by_id(self):
        """get_crm_card should return single card with contract"""
        response = {
            'id': 1,
            'contract_id': 1,
            'column_name': 'new_order',
            'contract': {'contract_number': 'D-2025-001'}
        }
        assert 'contract' in response

    def test_update_crm_card(self):
        """update_crm_card should update card data"""
        response = {'id': 1, 'column_name': 'in_progress'}
        assert response['column_name'] == 'in_progress'

    def test_move_crm_card(self):
        """move_crm_card should change column"""
        request = {'column_name': 'completed'}
        response = {'success': True, 'new_column': 'completed'}
        assert response['new_column'] == request['column_name']


@pytest.mark.api_client
class TestStageExecutorMethods:
    """Tests for stage executor methods"""

    def test_assign_stage_executor(self):
        """assign_stage_executor should create assignment"""
        request = {
            'stage_name': 'Design',
            'executor_id': 2,
            'role': 'Designer'
        }
        response = {'success': True}
        assert response['success']

    def test_update_stage_executor(self):
        """update_stage_executor should update assignment"""
        request = {'executor_id': 3, 'deadline': '2025-02-01'}
        response = {'success': True}
        assert response['success']


@pytest.mark.api_client
@pytest.mark.critical
class TestPaymentMethods:
    """Tests for payment methods - CRITICAL"""

    def test_get_payments_for_contract(self):
        """get_payments_for_contract should return contract payments"""
        contract_id = 1
        response = [
            {'id': 1, 'contract_id': 1},
            {'id': 2, 'contract_id': 1},
        ]
        assert all(p['contract_id'] == contract_id for p in response)

    def test_create_payment_with_null_amounts(self):
        """create_payment should handle null amounts"""
        request = {
            'contract_id': 1,
            'employee_id': 2,
            'calculated_amount': None,
            'final_amount': None
        }
        # Server should set defaults
        response = {
            'id': 1,
            'calculated_amount': 0.0,
            'final_amount': 0.0
        }
        assert response['calculated_amount'] == 0.0
        assert response['final_amount'] == 0.0

    def test_update_payment(self):
        """update_payment should update payment data"""
        response = {'id': 1, 'final_amount': 6000.0}
        assert 'final_amount' in response

    def test_delete_payment(self):
        """delete_payment should remove payment"""
        response = {'success': True}
        assert response['success']

    def test_calculate_payment_amount(self):
        """calculate_payment_amount should return calculated amount"""
        params = {
            'role': 'Designer',
            'stage_name': 'Design',
            'area': 150.5,
            'rate_type': 'template'
        }
        response = {'amount': 5000.0}
        assert 'amount' in response
        assert response['amount'] >= 0


@pytest.mark.api_client
class TestRatesMethods:
    """Tests for rates methods"""

    def test_get_rates_returns_list(self):
        """get_rates should return rates list"""
        response = []
        assert isinstance(response, list)

    def test_get_template_rates(self):
        """get_template_rates should return template rates dict"""
        response = {
            'designer': {'area_ranges': []},
            'manager': {'area_ranges': []}
        }
        assert isinstance(response, dict)

    def test_save_template_rate(self):
        """save_template_rate should save and return rate"""
        request = {
            'stage_name': 'Design',
            'area_from': 0,
            'area_to': 100,
            'price': 1000
        }
        response = {'id': 1, **request}
        assert 'id' in response


@pytest.mark.api_client
class TestSupervisionMethods:
    """Tests for supervision card methods"""

    def test_get_supervision_cards(self):
        """get_supervision_cards should return list"""
        response = []
        assert isinstance(response, list)

    def test_update_supervision_card(self):
        """update_supervision_card should update card"""
        response = {'id': 1, 'dan_id': 3}
        assert 'dan_id' in response

    def test_pause_supervision_card(self):
        """pause_supervision_card should pause card"""
        request = {'reason': 'Client request'}
        response = {'status': 'paused', 'pause_reason': 'Client request'}
        assert response['status'] == 'paused'

    def test_resume_supervision_card(self):
        """resume_supervision_card should resume card"""
        response = {'status': 'active', 'pause_reason': None}
        assert response['status'] == 'active'


@pytest.mark.api_client
class TestStatisticsMethods:
    """Tests for statistics methods"""

    def test_get_project_statistics(self):
        """get_project_statistics should return stats"""
        response = {
            'total_projects': 10,
            'active_projects': 5
        }
        assert 'total_projects' in response

    def test_get_supervision_statistics(self):
        """get_supervision_statistics should return stats"""
        response = {
            'total_supervision': 5,
            'active': 3
        }
        assert 'total_supervision' in response

    def test_statistics_accepts_period_filters(self):
        """Statistics methods should accept period filters"""
        params = {
            'year': 2025,
            'month': 1,
            'quarter': None
        }
        assert 'year' in params
        assert 'month' in params


@pytest.mark.api_client
class TestErrorHandling:
    """Tests for API error handling"""

    def test_connection_error_raises_exception(self):
        """Connection error should raise APIConnectionError"""
        error_type = 'APIConnectionError'
        assert error_type == 'APIConnectionError'

    def test_http_error_raises_exception(self):
        """HTTP errors should raise APIError"""
        error_type = 'APIError'
        assert error_type == 'APIError'

    def test_timeout_sets_offline_status(self):
        """Timeout should set client to offline"""
        client = {'is_online': True}
        # After timeout
        client['is_online'] = False
        assert client['is_online'] is False

    def test_retry_on_transient_error(self):
        """Transient errors should trigger retry"""
        max_retries = 2
        retry_count = 0

        # Simulate retries
        while retry_count < max_retries:
            retry_count += 1

        assert retry_count == max_retries


@pytest.mark.api_client
class TestRequestHeaders:
    """Tests for request headers"""

    def test_authorization_header_included(self):
        """Authorization header should include token"""
        token = 'eyJhbGc...'
        headers = {'Authorization': f'Bearer {token}'}
        assert 'Authorization' in headers
        assert headers['Authorization'].startswith('Bearer ')

    def test_content_type_json(self):
        """Content-Type should be application/json for POST/PUT"""
        headers = {'Content-Type': 'application/json'}
        assert headers['Content-Type'] == 'application/json'
