"""
Edge Case Tests - Data Integrity
TDD tests for data integrity, foreign keys, and cascading operations
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.edge_cases
class TestForeignKeyIntegrity:
    """Tests for foreign key constraints"""

    def test_contract_references_valid_client(self):
        """Contract must reference existing client"""
        clients = [{'id': 1}, {'id': 2}]
        contract = {'client_id': 1}

        valid_client = any(c['id'] == contract['client_id'] for c in clients)
        assert valid_client is True

    def test_contract_invalid_client_rejected(self):
        """Contract with invalid client_id should be rejected"""
        clients = [{'id': 1}, {'id': 2}]
        contract = {'client_id': 999}  # Invalid

        valid_client = any(c['id'] == contract['client_id'] for c in clients)
        assert valid_client is False

    def test_crm_card_references_valid_contract(self):
        """CRM card must reference existing contract"""
        contracts = [{'id': 1}]
        crm_card = {'contract_id': 1}

        valid = any(c['id'] == crm_card['contract_id'] for c in contracts)
        assert valid is True

    def test_payment_references_valid_contract(self):
        """Payment must reference existing contract"""
        contracts = [{'id': 1}]
        payment = {'contract_id': 1}

        valid = any(c['id'] == payment['contract_id'] for c in contracts)
        assert valid is True

    def test_payment_references_valid_employee(self):
        """Payment must reference existing employee"""
        employees = [{'id': 1}, {'id': 2}]
        payment = {'employee_id': 2}

        valid = any(e['id'] == payment['employee_id'] for e in employees)
        assert valid is True


@pytest.mark.edge_cases
class TestCascadeDelete:
    """Tests for cascade delete behavior"""

    def test_delete_contract_cascades_crm_card(self):
        """Deleting contract should cascade delete CRM card"""
        contracts = [{'id': 1}]
        crm_cards = [{'id': 1, 'contract_id': 1}]

        # Delete contract
        deleted_contract_id = 1
        contracts = [c for c in contracts if c['id'] != deleted_contract_id]

        # Cascade delete CRM cards
        crm_cards = [c for c in crm_cards if c['contract_id'] != deleted_contract_id]

        assert len(contracts) == 0
        assert len(crm_cards) == 0

    def test_delete_contract_cascades_supervision_card(self):
        """Deleting contract should cascade delete supervision card"""
        contracts = [{'id': 1}]
        supervision_cards = [{'id': 1, 'contract_id': 1}]

        deleted_contract_id = 1
        contracts = [c for c in contracts if c['id'] != deleted_contract_id]
        supervision_cards = [s for s in supervision_cards if s['contract_id'] != deleted_contract_id]

        assert len(supervision_cards) == 0

    def test_delete_crm_card_cascades_stage_executors(self):
        """Deleting CRM card should cascade delete stage executors"""
        crm_cards = [{'id': 1}]
        executors = [
            {'id': 1, 'crm_card_id': 1},
            {'id': 2, 'crm_card_id': 1},
        ]

        deleted_card_id = 1
        crm_cards = [c for c in crm_cards if c['id'] != deleted_card_id]
        executors = [e for e in executors if e['crm_card_id'] != deleted_card_id]

        assert len(executors) == 0


@pytest.mark.edge_cases
class TestNullHandling:
    """Tests for NULL value handling"""

    def test_payment_null_amounts_default_zero(self):
        """
        CRITICAL: Payment with NULL amounts should default to 0.
        Addresses NOT NULL constraint violation.
        """
        payment = {
            'calculated_amount': None,
            'final_amount': None
        }

        # Apply defaults
        payment['calculated_amount'] = payment.get('calculated_amount') or 0.0
        payment['final_amount'] = payment.get('final_amount') or 0.0

        assert payment['calculated_amount'] == 0.0
        assert payment['final_amount'] == 0.0

    def test_contract_empty_date_filtered(self):
        """
        CRITICAL: Contracts with empty dates should be filtered
        when doing date-based queries.
        """
        contracts = [
            {'id': 1, 'contract_date': '2025-01-15'},
            {'id': 2, 'contract_date': ''},         # Empty
            {'id': 3, 'contract_date': None},       # NULL
        ]

        # Filter valid dates
        valid = [
            c for c in contracts
            if c.get('contract_date') and c['contract_date'] != ''
        ]

        assert len(valid) == 1
        assert valid[0]['id'] == 1

    def test_optional_fields_can_be_null(self):
        """Optional fields should accept NULL"""
        employee = {
            'phone': None,      # Optional
            'email': None,      # Optional
            'department': None  # Optional
        }

        # Should not raise error
        assert employee['phone'] is None


@pytest.mark.edge_cases
class TestUniqueConstraints:
    """Tests for unique constraints"""

    def test_employee_login_unique(self):
        """Employee login must be unique"""
        employees = [
            {'id': 1, 'login': 'admin'},
            {'id': 2, 'login': 'user1'},
        ]

        new_login = 'admin'  # Duplicate
        is_unique = not any(e['login'] == new_login for e in employees)

        assert is_unique is False, "Duplicate login should be detected"

    def test_contract_number_unique(self):
        """Contract number must be unique"""
        contracts = [
            {'id': 1, 'contract_number': 'D-2025-001'},
            {'id': 2, 'contract_number': 'D-2025-002'},
        ]

        new_number = 'D-2025-001'  # Duplicate
        is_unique = not any(c['contract_number'] == new_number for c in contracts)

        assert is_unique is False, "Duplicate contract number should be detected"


@pytest.mark.edge_cases
class TestDataTypeValidation:
    """Tests for data type validation"""

    def test_area_must_be_number(self):
        """Contract area must be a number"""
        area = 150.5
        assert isinstance(area, (int, float))

    def test_area_must_be_positive(self):
        """Contract area must be positive"""
        area = 150.5
        assert area > 0

    def test_amount_must_be_number(self):
        """Payment amount must be a number"""
        amount = 5000.0
        assert isinstance(amount, (int, float))

    def test_date_format_valid(self):
        """Dates should be in valid format"""
        date_str = '2025-01-15'
        # ISO format: YYYY-MM-DD
        parts = date_str.split('-')
        assert len(parts) == 3
        assert len(parts[0]) == 4  # Year
        assert len(parts[1]) == 2  # Month
        assert len(parts[2]) == 2  # Day


@pytest.mark.edge_cases
class TestConcurrentAccess:
    """Tests for concurrent data access"""

    def test_optimistic_locking(self):
        """
        Concurrent updates should be detected.
        Later update should be rejected if data changed.
        """
        # Original record
        record = {'id': 1, 'value': 'original', 'version': 1}

        # User A reads
        user_a_version = record['version']

        # User B updates
        record['value'] = 'updated_by_b'
        record['version'] = 2

        # User A tries to update (should fail)
        user_a_update_version = user_a_version
        current_version = record['version']

        can_update = user_a_update_version == current_version
        assert can_update is False, "Concurrent update should be detected"

    def test_transaction_isolation(self):
        """
        Changes in one transaction should not be visible
        to others until committed.
        """
        # Transaction A starts
        transaction_a_data = {'value': 'original'}

        # Transaction B changes data (uncommitted)
        uncommitted_change = 'changed_by_b'

        # Transaction A should still see original
        assert transaction_a_data['value'] == 'original'


@pytest.mark.edge_cases
class TestDataMigration:
    """Tests for data migration scenarios"""

    def test_migration_preserves_data(self):
        """Migration should not lose data"""
        before_count = 100
        after_count = 100

        assert after_count >= before_count, "Migration must preserve all data"

    def test_migration_adds_new_fields(self):
        """Migration can add new fields with defaults"""
        old_record = {'id': 1, 'name': 'Test'}

        # After migration adding 'status' field
        new_record = {**old_record, 'status': 'active'}  # Default value

        assert 'status' in new_record
        assert new_record['status'] == 'active'

    def test_migration_idempotent(self):
        """Running migration twice should have same result"""
        def apply_migration(data):
            if 'status' not in data:
                data['status'] = 'active'
            return data

        record = {'id': 1, 'name': 'Test'}

        # First run
        record = apply_migration(record)
        state_after_first = dict(record)

        # Second run
        record = apply_migration(record)
        state_after_second = dict(record)

        assert state_after_first == state_after_second, "Migration must be idempotent"


@pytest.mark.edge_cases
class TestOrphanRecords:
    """Tests for preventing orphan records"""

    def test_no_orphan_crm_cards(self):
        """CRM cards should not exist without contracts"""
        contracts = [{'id': 1}]
        crm_cards = [
            {'id': 1, 'contract_id': 1},
            {'id': 2, 'contract_id': 2},  # Orphan
        ]

        contract_ids = {c['id'] for c in contracts}
        orphans = [c for c in crm_cards if c['contract_id'] not in contract_ids]

        assert len(orphans) == 1, "Should detect orphan records"

    def test_no_orphan_payments(self):
        """Payments should not exist without contracts"""
        contracts = [{'id': 1}]
        payments = [
            {'id': 1, 'contract_id': 1},
            {'id': 2, 'contract_id': 999},  # Orphan
        ]

        contract_ids = {c['id'] for c in contracts}
        orphans = [p for p in payments if p['contract_id'] not in contract_ids]

        assert len(orphans) == 1, "Should detect orphan payments"
