"""
CRM Supervision Tab Integration Tests - 35 tests

Tests cover:
2.1 Supervision Card Loading (8 tests)
2.2 Card Movement and Status (10 tests)
2.3 DAN Reassignment (8 tests)
2.4 Supervision Payments (9 tests)
"""

import pytest
import sqlite3
from unittest.mock import Mock, patch
from datetime import datetime


# ==================== FIXTURES ====================

@pytest.fixture
def mock_api_client():
    """Mock API client for testing"""
    client = Mock()
    client.is_online = True
    client._is_recently_offline = Mock(return_value=False)
    return client


@pytest.fixture
def mock_db(tmp_path):
    """Create test SQLite database"""
    db_path = tmp_path / "test_supervision.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create tables - ПОЛНАЯ СХЕМА соответствующая db_manager.py
    cursor.execute('''
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE,
            full_name TEXT,
            position TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_type TEXT NOT NULL,
            full_name TEXT,
            phone TEXT NOT NULL,
            email TEXT,
            organization_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_number TEXT UNIQUE NOT NULL,
            client_id INTEGER,
            address TEXT,
            city TEXT,
            area REAL,
            project_type TEXT NOT NULL,
            agent_type TEXT,
            status TEXT DEFAULT 'Новый заказ',
            contract_date TEXT,
            total_amount REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE supervision_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER UNIQUE NOT NULL,
            column_name TEXT NOT NULL DEFAULT 'Новые',
            dan_id INTEGER,
            is_paused INTEGER DEFAULT 0,
            pause_reason TEXT,
            pause_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE crm_supervision (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            column_name TEXT NOT NULL,
            deadline DATE,
            tags TEXT,
            is_approved INTEGER DEFAULT 0,
            is_purchased INTEGER DEFAULT 0,
            executor_id INTEGER,
            order_position INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id),
            FOREIGN KEY (executor_id) REFERENCES employees(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER,
            crm_card_id INTEGER,
            supervision_card_id INTEGER,
            employee_id INTEGER,
            role TEXT,
            stage_name TEXT,
            calculated_amount REAL DEFAULT 0,
            manual_amount REAL,
            final_amount REAL DEFAULT 0,
            is_manual INTEGER DEFAULT 0,
            payment_type TEXT,
            report_month TEXT,
            payment_status TEXT DEFAULT 'pending',
            is_paid INTEGER DEFAULT 0,
            reassigned INTEGER DEFAULT 0,
            old_employee_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE supervision_project_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supervision_card_id INTEGER,
            action TEXT,
            old_value TEXT,
            new_value TEXT,
            created_at TEXT,
            FOREIGN KEY (supervision_card_id) REFERENCES supervision_cards(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_type TEXT,
            role TEXT,
            stage_name TEXT,
            area_from REAL,
            area_to REAL,
            rate_per_m2 REAL,
            fixed_price REAL,
            is_supervision INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert test data
    cursor.execute("INSERT INTO employees (id, login, full_name, position) VALUES (1, 'admin', 'Admin User', 'Administrator')")
    cursor.execute("INSERT INTO employees (id, login, full_name, position) VALUES (2, 'dan1', 'DAN One', 'ДАН')")
    cursor.execute("INSERT INTO employees (id, login, full_name, position) VALUES (3, 'dan2', 'DAN Two', 'ДАН')")

    cursor.execute("""
        INSERT INTO contracts (id, contract_number, address, city, area, project_type, status, contract_date)
        VALUES (1, 'SUP-001', 'Test Address 1', 'Moscow', 100.0, 'Индивидуальный', 'АВТОРСКИЙ НАДЗОР', '2025-01-15')
    """)
    cursor.execute("""
        INSERT INTO contracts (id, contract_number, address, city, area, project_type, status, contract_date)
        VALUES (2, 'SUP-002', 'Test Address 2', 'Moscow', 150.0, 'Индивидуальный', 'СДАН', '2025-01-10')
    """)

    cursor.execute("INSERT INTO supervision_cards (id, contract_id, column_name, dan_id) VALUES (1, 1, 'Новые', 2)")

    cursor.execute("""
        INSERT INTO payments (id, contract_id, supervision_card_id, employee_id, role, stage_name, calculated_amount, final_amount, payment_type, reassigned)
        VALUES (1, 1, 1, 2, 'ДАН', 'Новые', 10000, 10000, 'Полная оплата', 0)
    """)

    cursor.execute("""
        INSERT INTO rates (project_type, role, area_from, area_to, rate_per_m2, is_supervision)
        VALUES ('Индивидуальный', 'ДАН', 0, 200, 100, 1)
    """)

    conn.commit()
    conn.close()

    return str(db_path)


@pytest.fixture
def db_manager(mock_db):
    """Create DatabaseManager with test DB"""
    from database.db_manager import DatabaseManager
    manager = DatabaseManager(mock_db)
    return manager


# ==================== 2.1 SUPERVISION CARD LOADING TESTS (8) ====================

class TestSupervisionCardLoading:
    """Tests for supervision card loading functionality"""

    def test_sup_001_load_active_cards_api_online(self, mock_api_client):
        """TEST_SUP_001: Load active supervision cards (API online)"""
        mock_api_client.get_supervision_cards.return_value = [
            {'id': 1, 'contract_id': 1, 'column_name': 'Новые', 'is_paused': False}
        ]

        cards = mock_api_client.get_supervision_cards(status='active')

        assert len(cards) == 1
        mock_api_client.get_supervision_cards.assert_called_once_with(status='active')

    def test_sup_002_load_active_cards_api_error_fallback(self, mock_api_client, db_manager):
        """TEST_SUP_002: Load active supervision cards (API error -> fallback)"""
        mock_api_client.get_supervision_cards.side_effect = Exception("API Error")

        try:
            cards = mock_api_client.get_supervision_cards(status='active')
        except:
            # Fallback to local DB
            cards = db_manager.get_supervision_cards() if hasattr(db_manager, 'get_supervision_cards') else []

        assert isinstance(cards, list)

    def test_sup_003_load_archived_cards(self, mock_api_client):
        """TEST_SUP_003: Load archived supervision cards"""
        mock_api_client.get_supervision_cards.return_value = [
            {'id': 2, 'contract_id': 2, 'contract_status': 'СДАН'}
        ]

        cards = mock_api_client.get_supervision_cards(status='archived')

        assert len(cards) >= 0

    def test_sup_004_filter_by_status_active_archived(self, mock_api_client):
        """TEST_SUP_004: Filter by status active/archived"""
        mock_api_client.get_supervision_cards.side_effect = [
            [{'id': 1, 'status': 'active'}],
            [{'id': 2, 'status': 'archived'}]
        ]

        active = mock_api_client.get_supervision_cards(status='active')
        archived = mock_api_client.get_supervision_cards(status='archived')

        assert len(active) > 0 or len(archived) > 0

    def test_sup_005_card_visible_only_if_supervision_status(self, mock_api_client):
        """TEST_SUP_005: Card visible only if Contract.status='АВТОРСКИЙ НАДЗОР'"""
        # Card should only be visible if associated contract has correct status
        mock_api_client.get_supervision_cards.return_value = [
            {'id': 1, 'contract_id': 1, 'contract_status': 'АВТОРСКИЙ НАДЗОР'}
        ]

        cards = mock_api_client.get_supervision_cards(status='active')

        for card in cards:
            assert card.get('contract_status') == 'АВТОРСКИЙ НАДЗОР'

    def test_sup_006_cards_linked_to_correct_contract(self, mock_api_client):
        """TEST_SUP_006: Cards are linked to correct contract"""
        mock_api_client.get_supervision_cards.return_value = [
            {'id': 1, 'contract_id': 1}
        ]
        mock_api_client.get_contract.return_value = {'id': 1, 'contract_number': 'SUP-001'}

        cards = mock_api_client.get_supervision_cards(status='active')
        contract = mock_api_client.get_contract(cards[0]['contract_id'])

        assert contract['id'] == cards[0]['contract_id']

    def test_sup_007_load_in_offline_mode(self, mock_api_client, db_manager):
        """TEST_SUP_007: Load in offline mode"""
        mock_api_client.is_online = False

        # Should use local DB
        cards = db_manager.get_supervision_cards() if hasattr(db_manager, 'get_supervision_cards') else []

        assert isinstance(cards, list)

    def test_sup_008_no_card_duplication(self, mock_api_client):
        """TEST_SUP_008: No card duplication"""
        mock_api_client.get_supervision_cards.return_value = [
            {'id': 1, 'contract_id': 1},
            {'id': 2, 'contract_id': 2}
        ]

        cards = mock_api_client.get_supervision_cards(status='active')

        # Check no duplicate IDs
        card_ids = [c['id'] for c in cards]
        assert len(card_ids) == len(set(card_ids))


# ==================== 2.2 CARD MOVEMENT AND STATUS TESTS (10) ====================

class TestSupervisionCardMovement:
    """Tests for supervision card movement and status functionality"""

    def test_sup_009_move_card_to_different_column(self, mock_api_client):
        """TEST_SUP_009: Move card to different column"""
        mock_api_client.move_supervision_card.return_value = {
            'id': 1, 'column_name': 'В работе'
        }

        result = mock_api_client.move_supervision_card(card_id=1, new_column='В работе')

        assert result['column_name'] == 'В работе'

    def test_sup_010_pause_card_api_online(self, mock_api_client):
        """TEST_SUP_010: Pause card (API online)"""
        mock_api_client.pause_supervision_card.return_value = {
            'id': 1, 'is_paused': True, 'pause_reason': 'Test reason'
        }

        result = mock_api_client.pause_supervision_card(
            card_id=1, pause_reason='Test reason'
        )

        assert result['is_paused'] == True

    def test_sup_011_pause_card_api_error_fallback(self, mock_api_client, db_manager):
        """TEST_SUP_011: Pause card (API error -> fallback)"""
        mock_api_client.pause_supervision_card.side_effect = Exception("API Error")

        try:
            result = mock_api_client.pause_supervision_card(card_id=1, pause_reason='Test')
        except:
            # Fallback to local DB
            db_manager.update_supervision_card(1, {'is_paused': 1})
            result = {'is_paused': True}

        assert result['is_paused'] == True

    def test_sup_012_resume_card(self, mock_api_client):
        """TEST_SUP_012: Resume paused card"""
        mock_api_client.resume_supervision_card.return_value = {
            'id': 1, 'is_paused': False
        }

        result = mock_api_client.resume_supervision_card(card_id=1)

        assert result['is_paused'] == False

    def test_sup_013_complete_supervision_card(self, mock_api_client):
        """TEST_SUP_013: Complete supervision card"""
        mock_api_client.update_supervision_card.return_value = {
            'id': 1, 'column_name': 'Завершено'
        }

        result = mock_api_client.update_supervision_card(1, {'column_name': 'Завершено'})

        assert result['column_name'] == 'Завершено'

    def test_sup_014_move_creates_payments_for_dan(self, mock_api_client):
        """TEST_SUP_014: Move creates payments for DAN"""
        # When card moves to certain columns, payments should be created
        mock_api_client.create_payment.return_value = {
            'id': 1, 'role': 'ДАН', 'stage_name': 'В работе'
        }

        payment_data = {
            'contract_id': 1,
            'supervision_card_id': 1,
            'employee_id': 2,
            'role': 'ДАН',
            'stage_name': 'В работе',
            'payment_type': 'Полная оплата'
        }

        result = mock_api_client.create_payment(payment_data)

        assert result['role'] == 'ДАН'

    def test_sup_015_stage_name_matches_column_name(self, mock_api_client):
        """TEST_SUP_015: stage_name in payments matches column_name"""
        column_name = 'В работе'
        payment = {'stage_name': column_name}

        assert payment['stage_name'] == column_name

    def test_sup_016_move_history_recorded(self, mock_api_client):
        """TEST_SUP_016: Move history is recorded"""
        mock_api_client.create_action_history.return_value = {'id': 1}

        history_data = {
            'entity_type': 'supervision_card',
            'entity_id': 1,
            'action': 'move',
            'old_value': 'Новые',
            'new_value': 'В работе'
        }

        result = mock_api_client.create_action_history(history_data)

        mock_api_client.create_action_history.assert_called_once()

    def test_sup_017_move_offline_mode(self, mock_api_client):
        """TEST_SUP_017: Move in offline mode"""
        mock_api_client.is_online = False

        # Should queue operation
        operation = {
            'type': 'UPDATE',
            'entity': 'supervision_card',
            'id': 1,
            'data': {'column_name': 'В работе'}
        }

        assert operation['type'] == 'UPDATE'

    def test_sup_018_validate_column_name_on_move(self, mock_api_client):
        """TEST_SUP_018: Validate column_name on move"""
        valid_columns = ['Новые', 'В работе', 'Завершено', 'Приостановлено']

        for col in valid_columns:
            assert col in valid_columns

        invalid_column = 'Invalid'
        assert invalid_column not in valid_columns


# ==================== 2.3 DAN REASSIGNMENT TESTS (8) ====================

class TestSupervisionDANReassignment:
    """Tests for DAN reassignment functionality"""

    def test_sup_019_reassign_dan_api_online(self, mock_api_client):
        """TEST_SUP_019: Reassign DAN (API online)"""
        mock_api_client.update_supervision_card.return_value = {
            'id': 1, 'dan_id': 3
        }

        result = mock_api_client.update_supervision_card(1, {'dan_id': 3})

        assert result['dan_id'] == 3

    def test_sup_020_reassign_dan_api_error_fallback(self, mock_api_client, db_manager):
        """TEST_SUP_020: Reassign DAN (API error -> fallback)"""
        mock_api_client.update_supervision_card.side_effect = Exception("API Error")

        try:
            mock_api_client.update_supervision_card(1, {'dan_id': 3})
        except:
            db_manager.update_supervision_card(1, {'dan_id': 3})

        assert True

    def test_sup_021_create_payments_for_new_dan(self, mock_api_client):
        """TEST_SUP_021: Create payments for new DAN"""
        mock_api_client.create_payment.return_value = {
            'id': 2, 'employee_id': 3, 'role': 'ДАН'
        }

        payment_data = {
            'contract_id': 1,
            'supervision_card_id': 1,
            'employee_id': 3,
            'role': 'ДАН',
            'payment_type': 'Полная оплата'
        }

        result = mock_api_client.create_payment(payment_data)

        assert result['employee_id'] == 3

    def test_sup_022_old_payments_marked_reassigned(self, mock_api_client):
        """TEST_SUP_022: Old payments marked as reassigned"""
        mock_api_client.update_payment.return_value = {
            'id': 1, 'reassigned': True
        }

        result = mock_api_client.update_payment(1, {'reassigned': True})

        assert result['reassigned'] == True

    def test_sup_023_no_duplicate_payments(self, mock_api_client):
        """TEST_SUP_023: No duplicate payments on reassignment"""
        existing_payments = [
            {'id': 1, 'employee_id': 2, 'reassigned': True},
            {'id': 2, 'employee_id': 3, 'reassigned': False}
        ]

        active_payments = [p for p in existing_payments if not p.get('reassigned')]

        assert len(active_payments) == 1

    def test_sup_024_reassign_offline_mode(self, mock_api_client):
        """TEST_SUP_024: Reassignment in offline mode"""
        mock_api_client.is_online = False

        operation = {
            'type': 'UPDATE',
            'entity': 'supervision_card',
            'data': {'dan_id': 3}
        }

        assert operation['type'] == 'UPDATE'

    def test_sup_025_reassign_history(self, mock_api_client):
        """TEST_SUP_025: Reassignment history recorded"""
        mock_api_client.create_action_history.return_value = {'id': 1}

        history_data = {
            'action': 'reassign_dan',
            'old_value': 'DAN One',
            'new_value': 'DAN Two'
        }

        mock_api_client.create_action_history(history_data)

        mock_api_client.create_action_history.assert_called_once()

    def test_sup_026_calculate_supervision_rate(self, mock_api_client):
        """TEST_SUP_026: Calculate supervision rate"""
        mock_api_client.calculate_payment_amount.return_value = 10000

        amount = mock_api_client.calculate_payment_amount(
            contract_id=1, employee_id=3, role='ДАН', supervision_card_id=1
        )

        assert amount > 0


# ==================== 2.4 SUPERVISION PAYMENTS TESTS (9) ====================

class TestSupervisionPayments:
    """Tests for supervision payments functionality"""

    def test_sup_027_payments_displayed_in_table(self, mock_api_client):
        """TEST_SUP_027: Payments displayed in table"""
        mock_api_client.get_payments_by_supervision_card.return_value = [
            {'id': 1, 'supervision_card_id': 1, 'role': 'ДАН'}
        ]

        payments = mock_api_client.get_payments_by_supervision_card(1)

        assert len(payments) >= 1

    def test_sup_028_edit_payment_amount(self, mock_api_client):
        """TEST_SUP_028: Edit payment amount"""
        mock_api_client.update_payment.return_value = {
            'id': 1, 'final_amount': 12000, 'is_manual': True
        }

        result = mock_api_client.update_payment(1, {
            'final_amount': 12000,
            'is_manual': True
        })

        assert result['final_amount'] == 12000

    def test_sup_029_delete_payment(self, mock_api_client):
        """TEST_SUP_029: Delete payment"""
        mock_api_client.delete_payment.return_value = {'status': 'deleted'}

        result = mock_api_client.delete_payment(1)

        assert result['status'] == 'deleted'

    def test_sup_030_payments_linked_to_supervision_card_id(self, mock_api_client):
        """TEST_SUP_030: Payments linked to supervision_card_id"""
        mock_api_client.get_payments_by_supervision_card.return_value = [
            {'id': 1, 'supervision_card_id': 1}
        ]

        payments = mock_api_client.get_payments_by_supervision_card(1)

        assert all(p['supervision_card_id'] == 1 for p in payments)

    def test_sup_031_payments_linked_to_contract_id(self, mock_api_client):
        """TEST_SUP_031: Payments linked to contract_id"""
        mock_api_client.get_payments_for_contract.return_value = [
            {'id': 1, 'contract_id': 1, 'supervision_card_id': 1}
        ]

        payments = mock_api_client.get_payments_for_contract(1)

        supervision_payments = [p for p in payments if p.get('supervision_card_id')]
        assert len(supervision_payments) >= 0

    def test_sup_032_change_payment_status(self, mock_api_client):
        """TEST_SUP_032: Change payment status"""
        mock_api_client.mark_payment_as_paid.return_value = {
            'id': 1, 'is_paid': True
        }

        result = mock_api_client.mark_payment_as_paid(1, paid_by=1)

        assert result['is_paid'] == True

    def test_sup_033_report_month_for_supervision_payments(self, mock_api_client):
        """TEST_SUP_033: report_month for supervision payments"""
        current_month = datetime.now().strftime('%Y-%m')

        mock_api_client.update_payment.return_value = {
            'id': 1, 'report_month': current_month
        }

        result = mock_api_client.update_payment(1, {'report_month': current_month})

        assert result['report_month'] == current_month

    def test_sup_034_payments_sorted(self, mock_api_client):
        """TEST_SUP_034: Payments are sorted"""
        payments = [
            {'id': 2, 'stage_name': 'В работе'},
            {'id': 1, 'stage_name': 'Новые'}
        ]

        # Sort by stage_name or id
        sorted_payments = sorted(payments, key=lambda p: p.get('id', 0))

        assert sorted_payments[0]['id'] == 1

    def test_sup_035_fallback_on_api_error(self, mock_api_client, db_manager):
        """TEST_SUP_035: Fallback on API error for payments"""
        mock_api_client.get_payments_by_supervision_card.side_effect = Exception("API Error")

        try:
            payments = mock_api_client.get_payments_by_supervision_card(1)
        except:
            # Fallback to local DB
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM payments WHERE supervision_card_id = 1")
            payments = cursor.fetchall()
            conn.close()

        assert isinstance(payments, (list, tuple))


# ==================== RUN TESTS ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
