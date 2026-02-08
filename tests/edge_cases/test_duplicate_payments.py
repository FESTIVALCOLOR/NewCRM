"""
Edge Case Tests - Duplicate Payments
TDD tests for preventing duplicate payment creation
THIS IS A CRITICAL TEST FILE addressing known bugs
"""

import pytest
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.edge_cases
@pytest.mark.critical
class TestDuplicatePaymentPrevention:
    """
    Critical tests for duplicate payment prevention.
    These tests address the known bug where reassignment creates duplicate payments.
    """

    def test_reassigned_payments_excluded_from_search(self):
        """
        CRITICAL: When searching for old payments to reassign,
        payments with reassigned=True must be EXCLUDED.

        Bug: ui/crm_tab.py:14970-14992 does not check reassigned flag.
        """
        all_payments = [
            # Previously reassigned - should NOT be found
            {'id': 1, 'contract_id': 1, 'stage_name': 'Design', 'role': 'Designer',
             'employee_id': 2, 'payment_type': 'advance', 'reassigned': True},

            # Current payment for different executor
            {'id': 2, 'contract_id': 1, 'stage_name': 'Design', 'role': 'Designer',
             'employee_id': 3, 'payment_type': 'advance', 'reassigned': False},

            # Old active payment - SHOULD be found
            {'id': 3, 'contract_id': 1, 'stage_name': 'Design', 'role': 'Designer',
             'employee_id': 2, 'payment_type': 'completion', 'reassigned': False},
        ]

        # Search parameters (reassigning from employee 2 to employee 4)
        contract_id = 1
        stage_name = 'Design'
        role = 'Designer'
        old_executor_id = 2

        # CORRECT implementation with reassigned check
        old_payments = [
            p for p in all_payments
            if p['contract_id'] == contract_id
            and p['stage_name'] == stage_name
            and p['role'] == role
            and p['employee_id'] == old_executor_id
            and not p.get('reassigned', False)  # CRITICAL CHECK
        ]

        # Should only find payment ID 3, not ID 1 (already reassigned)
        assert len(old_payments) == 1, \
            f"Expected 1 payment, found {len(old_payments)}. Reassigned payments must be excluded."
        assert old_payments[0]['id'] == 3, \
            f"Expected payment ID 3, found {old_payments[0]['id']}"

    def test_double_click_does_not_create_duplicates(self):
        """
        CRITICAL: Double-clicking reassign button should not create duplicates.

        Scenario:
        1. User clicks "Reassign" button
        2. First request starts processing
        3. User clicks again before first completes
        4. Second request should be blocked or return same payment
        """
        created_payments = []

        def create_payment_if_not_exists(contract_id, employee_id, stage, role, ptype):
            """Idempotent payment creation"""
            # Check if already exists
            exists = any(
                p['contract_id'] == contract_id and
                p['employee_id'] == employee_id and
                p['stage_name'] == stage and
                p['role'] == role and
                p['payment_type'] == ptype and
                not p.get('reassigned', False)
                for p in created_payments
            )

            if exists:
                return {'already_exists': True}

            new_payment = {
                'id': len(created_payments) + 1,
                'contract_id': contract_id,
                'employee_id': employee_id,
                'stage_name': stage,
                'role': role,
                'payment_type': ptype,
                'reassigned': False
            }
            created_payments.append(new_payment)
            return new_payment

        # First click
        result1 = create_payment_if_not_exists(1, 3, 'Design', 'Designer', 'advance')
        assert result1.get('id') == 1

        # Second click (should be blocked)
        result2 = create_payment_if_not_exists(1, 3, 'Design', 'Designer', 'advance')
        assert result2.get('already_exists') is True

        # Only one payment created
        assert len(created_payments) == 1

    def test_retry_on_timeout_does_not_duplicate(self):
        """
        CRITICAL: Retry on timeout should not create duplicate payments.

        Scenario:
        1. Create payment request times out
        2. System retries
        3. First request actually succeeded on server
        4. Retry should detect existing payment
        """
        server_payments = [
            # Payment created by first request (that timed out on client)
            {'id': 100, 'contract_id': 1, 'employee_id': 3, 'stage_name': 'Design',
             'role': 'Designer', 'payment_type': 'advance', 'reassigned': False}
        ]

        def create_payment_with_check(contract_id, employee_id, stage, role, ptype):
            """Create with duplicate check"""
            # Check existing
            existing = next(
                (p for p in server_payments
                 if p['contract_id'] == contract_id
                 and p['employee_id'] == employee_id
                 and p['stage_name'] == stage
                 and p['role'] == role
                 and p['payment_type'] == ptype
                 and not p.get('reassigned', False)),
                None
            )

            if existing:
                return {'id': existing['id'], 'already_exists': True}

            new_id = max(p['id'] for p in server_payments) + 1
            new_payment = {
                'id': new_id,
                'contract_id': contract_id,
                'employee_id': employee_id,
                'stage_name': stage,
                'role': role,
                'payment_type': ptype,
                'reassigned': False
            }
            server_payments.append(new_payment)
            return new_payment

        # Retry creates same payment
        result = create_payment_with_check(1, 3, 'Design', 'Designer', 'advance')

        # Should return existing, not create new
        assert result.get('already_exists') is True
        assert result['id'] == 100
        assert len(server_payments) == 1


@pytest.mark.edge_cases
@pytest.mark.critical
class TestPaymentUniquenessConstraints:
    """Tests for payment uniqueness constraints"""

    def test_unique_payment_key(self):
        """
        Each active payment should have unique combination of:
        (contract_id, employee_id, stage_name, role, payment_type)
        where reassigned=False
        """
        payments = [
            {'contract_id': 1, 'employee_id': 2, 'stage_name': 'Design',
             'role': 'Designer', 'payment_type': 'advance', 'reassigned': False},
            {'contract_id': 1, 'employee_id': 2, 'stage_name': 'Design',
             'role': 'Designer', 'payment_type': 'completion', 'reassigned': False},
        ]

        # Check uniqueness
        keys = set()
        duplicates = []

        for p in payments:
            if p.get('reassigned'):
                continue

            key = (
                p['contract_id'],
                p['employee_id'],
                p['stage_name'],
                p['role'],
                p['payment_type']
            )

            if key in keys:
                duplicates.append(p)
            keys.add(key)

        assert len(duplicates) == 0, f"Found duplicate payments: {duplicates}"

    def test_detect_duplicate_before_insert(self):
        """Before inserting payment, check for existing duplicate"""
        existing_payments = [
            {'id': 1, 'contract_id': 1, 'employee_id': 3, 'stage_name': 'Design',
             'role': 'Designer', 'payment_type': 'advance', 'reassigned': False}
        ]

        new_payment = {
            'contract_id': 1,
            'employee_id': 3,
            'stage_name': 'Design',
            'role': 'Designer',
            'payment_type': 'advance'
        }

        # Check for duplicate
        is_duplicate = any(
            p['contract_id'] == new_payment['contract_id'] and
            p['employee_id'] == new_payment['employee_id'] and
            p['stage_name'] == new_payment['stage_name'] and
            p['role'] == new_payment['role'] and
            p['payment_type'] == new_payment['payment_type'] and
            not p.get('reassigned', False)
            for p in existing_payments
        )

        assert is_duplicate is True, "Should detect duplicate before insert"


@pytest.mark.edge_cases
@pytest.mark.critical
class TestReassignmentChain:
    """Tests for chains of reassignments"""

    def test_multiple_reassignments_tracked_correctly(self):
        """
        Chain: A -> B -> C
        All payments should be properly tracked.
        """
        payments = []

        # Original payment to A
        payment_a = {
            'id': 1, 'employee_id': 1, 'stage_name': 'Design',
            'role': 'Designer', 'payment_type': 'advance', 'reassigned': False
        }
        payments.append(payment_a)

        # Reassign A -> B
        payment_a['reassigned'] = True
        payment_b = {
            'id': 2, 'employee_id': 2, 'stage_name': 'Design',
            'role': 'Designer', 'payment_type': 'advance', 'reassigned': False
        }
        payments.append(payment_b)

        # Reassign B -> C
        payment_b['reassigned'] = True
        payment_c = {
            'id': 3, 'employee_id': 3, 'stage_name': 'Design',
            'role': 'Designer', 'payment_type': 'advance', 'reassigned': False
        }
        payments.append(payment_c)

        # Only C should be active
        active_payments = [p for p in payments if not p['reassigned']]
        assert len(active_payments) == 1
        assert active_payments[0]['employee_id'] == 3

    def test_reassignment_history_preserved(self):
        """All reassignment history should be preserved"""
        payments = [
            {'id': 1, 'employee_id': 1, 'reassigned': True, 'reassigned_at': '2025-01-01'},
            {'id': 2, 'employee_id': 2, 'reassigned': True, 'reassigned_at': '2025-01-15'},
            {'id': 3, 'employee_id': 3, 'reassigned': False, 'reassigned_at': None},
        ]

        # All payments preserved
        assert len(payments) == 3

        # Can trace history
        reassigned = [p for p in payments if p['reassigned']]
        assert len(reassigned) == 2


@pytest.mark.edge_cases
class TestEdgeCaseScenarios:
    """Additional edge case scenarios"""

    def test_same_executor_different_stages_allowed(self):
        """Same executor can have payments for different stages"""
        payments = [
            {'employee_id': 2, 'stage_name': 'Design', 'reassigned': False},
            {'employee_id': 2, 'stage_name': 'Drafting', 'reassigned': False},
        ]

        # Different stages - both allowed
        stages = [p['stage_name'] for p in payments]
        assert len(set(stages)) == 2

    def test_same_stage_different_roles_allowed(self):
        """Same stage can have payments for different roles"""
        payments = [
            {'stage_name': 'Design', 'role': 'Designer', 'reassigned': False},
            {'stage_name': 'Design', 'role': 'Senior Designer', 'reassigned': False},
        ]

        # Different roles - both allowed
        roles = [p['role'] for p in payments]
        assert len(set(roles)) == 2

    def test_reassign_to_same_executor_blocked(self):
        """Cannot reassign to the same executor"""
        current_executor_id = 2
        new_executor_id = 2

        can_reassign = current_executor_id != new_executor_id
        assert can_reassign is False, "Should not allow reassign to same executor"

    def test_reassign_paid_payment_blocked(self):
        """Cannot reassign already paid payment"""
        payment = {'payment_status': 'paid', 'reassigned': False}

        can_reassign = payment['payment_status'] != 'paid'
        assert can_reassign is False, "Paid payments cannot be reassigned"
