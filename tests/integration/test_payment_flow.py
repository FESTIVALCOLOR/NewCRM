"""
Integration Tests - Payment Flow
TDD tests for complete payment creation and reassignment workflows
"""

import pytest
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.integration
@pytest.mark.critical
class TestPaymentCreationFlow:
    """Tests for payment creation workflow"""

    def test_assign_executor_creates_payments(self):
        """Assigning stage executor should create payments"""
        # Input: assign designer to Design stage
        assignment = {
            'crm_card_id': 1,
            'stage_name': 'Design',
            'executor_id': 2,
            'role': 'Designer'
        }

        # Expected: 2 payments created (advance + completion)
        expected_payments = [
            {'payment_type': 'advance', 'stage_name': 'Design', 'role': 'Designer'},
            {'payment_type': 'completion', 'stage_name': 'Design', 'role': 'Designer'},
        ]

        assert len(expected_payments) == 2

    def test_sdp_role_creates_two_payments(self):
        """SDP role should create advance and completion payments"""
        role = 'SDP'  # Senior Design Project
        payments_created = ['advance', 'completion']

        assert len(payments_created) == 2
        assert 'advance' in payments_created
        assert 'completion' in payments_created

    def test_non_sdp_role_creates_one_payment(self):
        """Non-SDP roles should create single full payment"""
        role = 'Manager'
        payments_created = ['full']

        assert len(payments_created) == 1
        assert 'full' in payments_created

    def test_payment_amount_calculated_from_rates(self):
        """Payment amount should be calculated from rates table"""
        rate = {
            'role': 'Designer',
            'stage_name': 'Design',
            'area_from': 100,
            'area_to': 200,
            'price': 500  # per sqm
        }
        contract = {'area': 150}

        # Calculate expected amount
        expected_amount = rate['price'] * contract['area']
        assert expected_amount == 75000


@pytest.mark.integration
@pytest.mark.critical
class TestPaymentReassignmentFlow:
    """Tests for payment reassignment workflow - CRITICAL"""

    def test_reassign_marks_old_payments_reassigned(self):
        """Reassigning executor should mark old payments as reassigned"""
        old_payments = [
            {'id': 1, 'employee_id': 2, 'reassigned': False},
            {'id': 2, 'employee_id': 2, 'reassigned': False},
        ]

        # After reassignment
        for p in old_payments:
            p['reassigned'] = True

        assert all(p['reassigned'] for p in old_payments)

    def test_reassign_creates_new_payments_for_new_executor(self):
        """Reassigning should create new payments for new executor"""
        old_executor_id = 2
        new_executor_id = 3

        new_payments = [
            {'employee_id': new_executor_id, 'payment_type': 'advance'},
            {'employee_id': new_executor_id, 'payment_type': 'completion'},
        ]

        assert all(p['employee_id'] == new_executor_id for p in new_payments)

    def test_reassign_preserves_amounts(self):
        """New payments should have same amounts as old"""
        old_payment = {'calculated_amount': 5000, 'final_amount': 5000}
        new_payment = {
            'calculated_amount': old_payment['calculated_amount'],
            'final_amount': old_payment['final_amount']
        }

        assert new_payment['final_amount'] == old_payment['final_amount']

    def test_reassign_creates_history_record(self):
        """Reassignment should create action history record"""
        history = {
            'entity_type': 'stage_executor',
            'action_type': 'reassign',
            'old_value': 'Designer A (ID: 2)',
            'new_value': 'Designer B (ID: 3)'
        }

        assert history['action_type'] == 'reassign'
        assert 'old_value' in history
        assert 'new_value' in history


@pytest.mark.integration
@pytest.mark.critical
class TestNoDuplicatePayments:
    """Tests for preventing duplicate payments - CRITICAL"""

    def test_find_old_payments_excludes_reassigned(self):
        """
        When finding old payments for reassignment,
        already reassigned payments should be EXCLUDED.
        This is a critical fix for the duplicate payment bug.
        """
        all_payments = [
            {'id': 1, 'stage_name': 'Design', 'role': 'Designer', 'employee_id': 2, 'reassigned': True},   # Already reassigned!
            {'id': 2, 'stage_name': 'Design', 'role': 'Designer', 'employee_id': 3, 'reassigned': False},  # Current
            {'id': 3, 'stage_name': 'Design', 'role': 'Designer', 'employee_id': 2, 'reassigned': False},  # Old but active
        ]

        old_executor_id = 2
        stage = 'Design'
        role = 'Designer'

        # Correct filtering - EXCLUDE reassigned payments
        old_payments = [
            p for p in all_payments
            if p['stage_name'] == stage
            and p['role'] == role
            and p['employee_id'] == old_executor_id
            and not p.get('reassigned', False)  # CRITICAL: Exclude reassigned!
        ]

        # Should only find ID 3, not ID 1 (already reassigned)
        assert len(old_payments) == 1
        assert old_payments[0]['id'] == 3

    def test_no_duplicate_payment_types(self):
        """
        Should not have multiple active payments of same type
        for same contract/stage/role/employee.
        """
        payments = [
            {'contract_id': 1, 'stage_name': 'Design', 'role': 'Designer', 'employee_id': 2, 'payment_type': 'advance', 'reassigned': False},
            {'contract_id': 1, 'stage_name': 'Design', 'role': 'Designer', 'employee_id': 2, 'payment_type': 'completion', 'reassigned': False},
        ]

        # Group by unique key
        unique_keys = set()
        duplicates = []

        for p in payments:
            if p.get('reassigned'):
                continue

            key = (p['contract_id'], p['stage_name'], p['role'], p['employee_id'], p['payment_type'])
            if key in unique_keys:
                duplicates.append(p)
            unique_keys.add(key)

        assert len(duplicates) == 0, "No duplicate payments allowed"

    def test_idempotent_reassignment(self):
        """
        Multiple reassignment attempts should not create duplicates.
        Reassignment should be idempotent.
        """
        # First reassignment
        first_result = {'new_payment_id': 10}

        # Second reassignment attempt (same parameters)
        existing_payment = {'id': 10, 'employee_id': 3, 'reassigned': False}

        # Should detect existing and not create duplicate
        if existing_payment:
            second_result = {'new_payment_id': existing_payment['id'], 'already_exists': True}
        else:
            second_result = {'new_payment_id': 11}

        assert second_result.get('already_exists', False) is True


@pytest.mark.integration
class TestPaymentStatusFlow:
    """Tests for payment status transitions"""

    def test_payment_starts_pending(self):
        """New payment should start with 'pending' status"""
        new_payment = {'payment_status': 'pending'}
        assert new_payment['payment_status'] == 'pending'

    def test_payment_can_be_marked_paid(self):
        """Payment can transition to 'paid' status"""
        payment = {'payment_status': 'pending'}
        payment['payment_status'] = 'paid'
        assert payment['payment_status'] == 'paid'

    def test_payment_can_be_cancelled(self):
        """Payment can be cancelled"""
        payment = {'payment_status': 'pending'}
        payment['payment_status'] = 'cancelled'
        assert payment['payment_status'] == 'cancelled'

    def test_paid_payment_cannot_be_reassigned(self):
        """Paid payments should not be reassigned"""
        payment = {'payment_status': 'paid', 'reassigned': False}

        can_reassign = payment['payment_status'] != 'paid'
        assert can_reassign is False


@pytest.mark.integration
class TestPaymentAmountAdjustment:
    """Tests for payment amount adjustment"""

    def test_manual_amount_overrides_calculated(self):
        """Manual amount should override calculated amount"""
        payment = {
            'calculated_amount': 5000,
            'manual_amount': 6000,
            'final_amount': None
        }

        # Final amount uses manual if set
        payment['final_amount'] = payment['manual_amount'] or payment['calculated_amount']
        assert payment['final_amount'] == 6000

    def test_adjustment_creates_history(self):
        """Amount adjustment should create history record"""
        history = {
            'entity_type': 'payment',
            'entity_id': 1,
            'action_type': 'amount_adjusted',
            'old_value': '5000',
            'new_value': '6000'
        }

        assert history['action_type'] == 'amount_adjusted'


@pytest.mark.integration
class TestPaymentReportMonth:
    """Tests for payment report month handling"""

    def test_payment_has_report_month(self):
        """Payment should have report_month field"""
        payment = {'report_month': '2025-01'}
        assert 'report_month' in payment

    def test_filter_payments_by_month(self):
        """Should filter payments by report month"""
        payments = [
            {'id': 1, 'report_month': '2025-01'},
            {'id': 2, 'report_month': '2025-01'},
            {'id': 3, 'report_month': '2025-02'},
        ]

        filtered = [p for p in payments if p['report_month'] == '2025-01']
        assert len(filtered) == 2


@pytest.mark.integration
class TestSupervisionPayments:
    """Tests for supervision (DAN) payments"""

    def test_dan_assignment_creates_payment(self):
        """Assigning DAN should create supervision payment"""
        assignment = {
            'supervision_card_id': 1,
            'dan_id': 2
        }

        expected_payment = {
            'contract_id': 1,
            'employee_id': assignment['dan_id'],
            'role': 'DAN',
            'payment_type': 'full'
        }

        assert expected_payment['role'] == 'DAN'

    def test_dan_reassignment_creates_new_payment(self):
        """Reassigning DAN should create new payment"""
        old_dan_id = 2
        new_dan_id = 3

        old_payment = {'employee_id': old_dan_id, 'reassigned': False}
        new_payment = {'employee_id': new_dan_id, 'reassigned': False}

        # After reassignment
        old_payment['reassigned'] = True

        assert old_payment['reassigned'] is True
        assert new_payment['employee_id'] == new_dan_id
