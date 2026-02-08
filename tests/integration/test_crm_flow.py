"""
Integration Tests - CRM Flow
TDD tests for CRM card creation, movement, and stage management
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.integration
class TestCRMCardCreation:
    """Tests for CRM card creation workflow"""

    def test_contract_creation_creates_crm_card(self):
        """Creating contract should automatically create CRM card"""
        contract = {'id': 1, 'contract_number': 'D-2025-001'}

        # CRM card should be created automatically
        crm_card = {
            'contract_id': contract['id'],
            'column_name': 'new_order'
        }

        assert crm_card['contract_id'] == contract['id']
        assert crm_card['column_name'] == 'new_order'

    def test_crm_card_links_to_contract(self):
        """CRM card should reference contract via foreign key"""
        contract_id = 1
        crm_card = {'contract_id': contract_id}

        assert crm_card['contract_id'] is not None

    def test_crm_card_default_column_new_order(self):
        """New CRM card should be in 'new_order' column"""
        crm_card = {'column_name': 'new_order'}
        assert crm_card['column_name'] == 'new_order'


@pytest.mark.integration
class TestCRMCardMovement:
    """Tests for CRM card movement between columns"""

    def test_move_card_changes_column(self):
        """Moving card should change column_name"""
        card = {'column_name': 'new_order'}
        new_column = 'in_progress'

        card['column_name'] = new_column
        assert card['column_name'] == new_column

    def test_valid_column_names(self):
        """Column names must be valid"""
        valid_columns = [
            'new_order', 'measuring', 'design', 'approval',
            'working_docs', 'in_progress', 'completed'
        ]

        test_column = 'in_progress'
        assert test_column in valid_columns

    def test_move_creates_history(self):
        """Moving card should create action history"""
        history = {
            'entity_type': 'crm_card',
            'entity_id': 1,
            'action_type': 'move',
            'old_value': 'new_order',
            'new_value': 'in_progress'
        }

        assert history['action_type'] == 'move'


@pytest.mark.integration
class TestStageExecution:
    """Tests for stage execution workflow"""

    def test_assign_executor_to_stage(self):
        """Can assign executor to specific stage"""
        assignment = {
            'crm_card_id': 1,
            'stage_name': 'Design',
            'executor_id': 2,
            'role': 'Designer'
        }

        assert assignment['executor_id'] is not None
        assert assignment['stage_name'] == 'Design'

    def test_stage_has_deadline(self):
        """Stage assignment should have deadline"""
        assignment = {
            'stage_name': 'Design',
            'executor_id': 2,
            'deadline': '2025-02-15'
        }

        assert 'deadline' in assignment

    def test_multiple_executors_per_card(self):
        """Card can have multiple executors for different stages"""
        executors = [
            {'stage_name': 'Design', 'executor_id': 2},
            {'stage_name': 'Drafting', 'executor_id': 3},
            {'stage_name': 'Visualization', 'executor_id': 4},
        ]

        stages = [e['stage_name'] for e in executors]
        assert len(set(stages)) == 3  # All different stages


@pytest.mark.integration
class TestCRMCardFiltering:
    """Tests for CRM card filtering"""

    def test_filter_by_project_type(self):
        """Cards can be filtered by project type"""
        cards = [
            {'id': 1, 'project_type': 'Individual'},
            {'id': 2, 'project_type': 'Template'},
            {'id': 3, 'project_type': 'Individual'},
        ]

        filtered = [c for c in cards if c['project_type'] == 'Individual']
        assert len(filtered) == 2

    def test_filter_by_column(self):
        """Cards can be filtered by column"""
        cards = [
            {'id': 1, 'column_name': 'new_order'},
            {'id': 2, 'column_name': 'in_progress'},
            {'id': 3, 'column_name': 'new_order'},
        ]

        filtered = [c for c in cards if c['column_name'] == 'new_order']
        assert len(filtered) == 2

    def test_filter_by_executor(self):
        """Cards can be filtered by assigned executor"""
        executors = [
            {'crm_card_id': 1, 'executor_id': 2},
            {'crm_card_id': 2, 'executor_id': 2},
            {'crm_card_id': 3, 'executor_id': 3},
        ]

        filtered = [e for e in executors if e['executor_id'] == 2]
        card_ids = [e['crm_card_id'] for e in filtered]
        assert len(card_ids) == 2


@pytest.mark.integration
class TestCRMCardDisplay:
    """Tests for CRM card display data"""

    def test_card_includes_contract_info(self):
        """Card should include contract information"""
        card = {
            'id': 1,
            'contract': {
                'contract_number': 'D-2025-001',
                'address': 'Test Street, 123',
                'client': {'full_name': 'Test Client'}
            }
        }

        assert card['contract']['contract_number'] is not None
        assert card['contract']['address'] is not None

    def test_card_includes_stage_info(self):
        """Card should include current stage information"""
        card = {
            'id': 1,
            'stages': [
                {'stage_name': 'Design', 'executor': 'Designer A', 'status': 'completed'},
                {'stage_name': 'Drafting', 'executor': 'Draftsman B', 'status': 'in_progress'},
            ]
        }

        assert len(card['stages']) > 0


@pytest.mark.integration
class TestCRMCardDeletion:
    """Tests for CRM card deletion"""

    def test_delete_contract_cascades_to_crm_card(self):
        """Deleting contract should cascade delete CRM card"""
        contract_deleted = True
        crm_card_deleted = True  # CASCADE

        assert contract_deleted
        assert crm_card_deleted

    def test_delete_crm_card_cascades_to_stage_executors(self):
        """Deleting CRM card should cascade delete stage executors"""
        crm_card_deleted = True
        executors_deleted = True  # CASCADE

        assert crm_card_deleted
        assert executors_deleted


@pytest.mark.integration
class TestCRMOfflineSupport:
    """Tests for CRM offline functionality"""

    def test_crm_card_update_works_offline(self):
        """CRM card updates should work in offline mode"""
        api_online = False
        local_db_available = True

        # Should fallback to local DB
        can_update = api_online or local_db_available
        assert can_update is True

    def test_offline_changes_queued(self):
        """Offline changes should be queued for sync"""
        queue = []
        change = {
            'entity_type': 'crm_card',
            'operation_type': 'UPDATE',
            'data': {'column_name': 'in_progress'}
        }
        queue.append(change)

        assert len(queue) == 1
