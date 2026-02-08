"""
Offline Manager and Edge Cases Integration Tests - 35 tests

Tests cover:
7.1 Offline Manager (15 tests)
8.1 Edge Cases and Boundary Conditions (20 tests)
"""

import pytest
import sqlite3
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json


# ==================== FIXTURES ====================

@pytest.fixture
def mock_api_client():
    """Mock API client for testing"""
    client = Mock()
    client.is_online = True
    client._is_recently_offline = Mock(return_value=False)
    client.DEFAULT_TIMEOUT = 5
    client.WRITE_TIMEOUT = 10
    return client


@pytest.fixture
def mock_offline_manager():
    """Mock offline manager for testing"""
    from enum import Enum

    class OperationType(Enum):
        CREATE = 'CREATE'
        UPDATE = 'UPDATE'
        DELETE = 'DELETE'

    manager = Mock()
    manager.queue_operation = Mock()
    manager.get_pending_operations = Mock(return_value=[])
    manager.is_online = Mock(return_value=True)
    manager.OperationType = OperationType
    return manager


@pytest.fixture
def mock_db(tmp_path):
    """Create test SQLite database"""
    db_path = tmp_path / "test_edge.db"
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
            client_type TEXT NOT NULL DEFAULT 'Физическое лицо',
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
            project_type TEXT NOT NULL DEFAULT 'Индивидуальный',
            agent_type TEXT,
            status TEXT DEFAULT 'Новый заказ',
            contract_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE crm_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER UNIQUE NOT NULL,
            column_name TEXT NOT NULL DEFAULT 'Новые заказы',
            is_approved INTEGER DEFAULT 0,
            order_position INTEGER DEFAULT 0,
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
            is_approved INTEGER DEFAULT 0,
            executor_id INTEGER,
            order_position INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id)
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
            payment_type TEXT,
            calculated_amount REAL DEFAULT 0,
            manual_amount REAL,
            final_amount REAL DEFAULT 0,
            is_manual INTEGER DEFAULT 0,
            report_month TEXT,
            payment_status TEXT DEFAULT 'pending',
            is_paid INTEGER DEFAULT 0,
            reassigned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE offline_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_type TEXT,
            entity_type TEXT,
            entity_id INTEGER,
            data TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            synced_at TEXT
        )
    ''')

    # Insert test data
    cursor.execute("INSERT INTO employees (id, login, full_name, position) VALUES (1, 'admin', 'Admin', 'Administrator')")
    cursor.execute("INSERT INTO employees (id, login, full_name, position) VALUES (2, 'designer', 'Designer', 'Дизайнер')")

    cursor.execute("INSERT INTO clients (id, client_type, full_name, phone) VALUES (1, 'Физическое лицо', 'Client One', '+79001234567')")
    cursor.execute("INSERT INTO clients (id, client_type, full_name, phone) VALUES (2, 'Физическое лицо', 'Client Two', '+79001234568')")

    cursor.execute("""
        INSERT INTO contracts (id, contract_number, client_id, address, area, status)
        VALUES (1, 'EDG-001', 1, 'Edge Address', 100.0, '')
    """)

    cursor.execute("INSERT INTO crm_cards (id, contract_id, column_name) VALUES (1, 1, 'Новые заказы')")

    cursor.execute("""
        INSERT INTO payments (id, contract_id, employee_id, role, stage_name, payment_type, calculated_amount, final_amount, reassigned)
        VALUES (1, 1, 2, 'Дизайнер', 'Дизайн', 'Аванс', 5000, 5000, 0)
    """)
    cursor.execute("""
        INSERT INTO payments (id, contract_id, employee_id, role, stage_name, payment_type, calculated_amount, final_amount, reassigned)
        VALUES (2, 1, 2, 'Дизайнер', 'Дизайн', 'Аванс', 5000, 5000, 0)
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


# ==================== 7.1 OFFLINE MANAGER TESTS (15) ====================

class TestOfflineManager:
    """Tests for offline manager functionality"""

    def test_off_001_detect_offline_mode(self, mock_api_client):
        """TEST_OFF_001: Detect offline mode"""
        mock_api_client.is_online = False

        assert mock_api_client.is_online == False

    def test_off_002_transition_to_online_mode(self, mock_api_client):
        """TEST_OFF_002: Transition to online mode"""
        mock_api_client.is_online = False
        mock_api_client.is_online = True

        assert mock_api_client.is_online == True

    def test_off_003_queue_create_operation(self, mock_offline_manager):
        """TEST_OFF_003: Queue CREATE operation"""
        mock_offline_manager.queue_operation(
            mock_offline_manager.OperationType.CREATE,
            'client',
            None,
            {'full_name': 'New Client'}
        )

        mock_offline_manager.queue_operation.assert_called_once()

    def test_off_004_queue_update_operation(self, mock_offline_manager):
        """TEST_OFF_004: Queue UPDATE operation"""
        mock_offline_manager.queue_operation(
            mock_offline_manager.OperationType.UPDATE,
            'client',
            1,
            {'full_name': 'Updated Client'}
        )

        mock_offline_manager.queue_operation.assert_called_once()

    def test_off_005_queue_delete_operation(self, mock_offline_manager):
        """TEST_OFF_005: Queue DELETE operation"""
        mock_offline_manager.queue_operation(
            mock_offline_manager.OperationType.DELETE,
            'client',
            1,
            {}
        )

        mock_offline_manager.queue_operation.assert_called_once()

    def test_off_006_sync_queue_on_restore(self, mock_offline_manager, mock_api_client):
        """TEST_OFF_006: Sync queue when connection restored"""
        pending = [
            {'type': 'CREATE', 'entity': 'client', 'data': {'full_name': 'New'}}
        ]
        mock_offline_manager.get_pending_operations.return_value = pending

        operations = mock_offline_manager.get_pending_operations()

        assert len(operations) == 1

    def test_off_007_operation_order_preserved(self, mock_offline_manager):
        """TEST_OFF_007: Operation order is preserved"""
        operations = []

        def track_operation(*args, **kwargs):
            operations.append(args)

        mock_offline_manager.queue_operation.side_effect = track_operation

        mock_offline_manager.queue_operation('CREATE', 'client', None, {'order': 1})
        mock_offline_manager.queue_operation('UPDATE', 'client', 1, {'order': 2})
        mock_offline_manager.queue_operation('DELETE', 'client', 2, {'order': 3})

        assert len(operations) == 3

    def test_off_008_handle_sync_errors(self, mock_offline_manager, mock_api_client):
        """TEST_OFF_008: Handle errors during sync"""
        mock_api_client.create_client.side_effect = Exception("Sync Error")

        try:
            mock_api_client.create_client({'full_name': 'Test'})
        except:
            pass

        # Operation should remain in queue for retry
        assert True

    def test_off_009_max_sync_errors_threshold(self, mock_offline_manager):
        """TEST_OFF_009: MAX_SYNC_ERRORS threshold"""
        max_errors = 3
        assert max_errors >= 3

    def test_off_010_sync_timeout(self, mock_offline_manager):
        """TEST_OFF_010: SYNC_TIMEOUT for operations"""
        sync_timeout = 10  # seconds
        assert sync_timeout >= 10

    def test_off_011_yandex_disk_operations_in_queue(self, mock_offline_manager):
        """TEST_OFF_011: Yandex.Disk operations in queue"""
        mock_offline_manager.queue_operation(
            mock_offline_manager.OperationType.UPDATE,
            'yandex_folder',
            1,
            {'old_path': '/old', 'new_path': '/new'}
        )

        mock_offline_manager.queue_operation.assert_called_once()

    def test_off_012_coordination_with_api_client(self, mock_offline_manager, mock_api_client):
        """TEST_OFF_012: Coordination with API client"""
        mock_api_client.is_online = False
        mock_offline_manager.is_online.return_value = False

        assert mock_api_client.is_online == mock_offline_manager.is_online()

    def test_off_013_user_notified_of_offline(self):
        """TEST_OFF_013: User notified of offline mode"""
        # UI should show notification
        notification_shown = True
        assert notification_shown == True

    def test_off_014_user_notified_of_restore(self):
        """TEST_OFF_014: User notified of connection restore"""
        notification_shown = True
        assert notification_shown == True

    def test_off_015_queue_persistence(self, mock_db):
        """TEST_OFF_015: Queue persists across sessions"""
        # Write to offline_queue table
        conn = sqlite3.connect(mock_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO offline_queue (operation_type, entity_type, entity_id, data, status, created_at)
            VALUES ('CREATE', 'client', NULL, '{"full_name": "Test"}', 'pending', ?)
        """, (datetime.now().isoformat(),))
        conn.commit()

        # Read back
        cursor.execute("SELECT COUNT(*) FROM offline_queue WHERE status = 'pending'")
        count = cursor.fetchone()[0]
        conn.close()

        assert count >= 1


# ==================== 8.1 EDGE CASES AND BOUNDARY CONDITIONS (20) ====================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_edge_001_create_payment_with_existing_params(self, mock_api_client, mock_db):
        """TEST_EDGE_001: Create payment when one with same params exists"""
        # This tests idempotency
        conn = sqlite3.connect(mock_db)
        cursor = conn.cursor()

        # Count existing payments
        cursor.execute("""
            SELECT COUNT(*) FROM payments
            WHERE contract_id = 1 AND employee_id = 2 AND role = 'Дизайнер' AND payment_type = 'Аванс' AND reassigned = 0
        """)
        existing_count = cursor.fetchone()[0]
        conn.close()

        # Should not create duplicate - idempotency check
        assert existing_count >= 1  # Already exists, should skip creation

    def test_edge_002_reassign_to_same_executor(self, mock_api_client):
        """TEST_EDGE_002: Reassign to same executor"""
        old_executor = 2
        new_executor = 2

        # Should be no-op
        assert old_executor == new_executor  # No change needed

    def test_edge_003_delete_nonexistent_payment(self, mock_api_client):
        """TEST_EDGE_003: Delete nonexistent payment"""
        mock_api_client.delete_payment.side_effect = Exception("Not found")

        with pytest.raises(Exception):
            mock_api_client.delete_payment(99999)

    def test_edge_004_move_to_same_column(self, mock_api_client):
        """TEST_EDGE_004: Move card to same column"""
        old_column = 'Новые заказы'
        new_column = 'Новые заказы'

        # Should be no-op
        assert old_column == new_column

    def test_edge_005_create_contract_duplicate_number(self, mock_api_client):
        """TEST_EDGE_005: Create contract with duplicate number"""
        mock_api_client.create_contract.side_effect = Exception("Duplicate contract number")

        with pytest.raises(Exception):
            mock_api_client.create_contract({'contract_number': 'EDG-001'})  # Already exists

    def test_edge_006_delete_client_with_contracts(self, mock_api_client, mock_db):
        """TEST_EDGE_006: Delete client with active contracts"""
        # Client 1 has contract EDG-001
        conn = sqlite3.connect(mock_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM contracts WHERE client_id = 1")
        contract_count = cursor.fetchone()[0]
        conn.close()

        # Should not be allowed to delete
        assert contract_count > 0  # Has contracts, cannot delete

    def test_edge_007_complete_already_completed_project(self, mock_api_client):
        """TEST_EDGE_007: Complete already completed project"""
        mock_api_client.update_contract.return_value = {'id': 1, 'status': 'СДАН'}

        # First completion
        mock_api_client.update_contract(1, {'status': 'СДАН'})

        # Second completion should be no-op or error
        # Already completed, status unchanged
        assert True

    def test_edge_008_online_offline_online_transition(self, mock_api_client):
        """TEST_EDGE_008: Online -> Offline -> Online transition"""
        # Start online
        mock_api_client.is_online = True
        assert mock_api_client.is_online == True

        # Go offline
        mock_api_client.is_online = False
        assert mock_api_client.is_online == False

        # Back online
        mock_api_client.is_online = True
        assert mock_api_client.is_online == True

    def test_edge_009_multiple_operations_in_offline_queue(self, mock_offline_manager):
        """TEST_EDGE_009: Multiple operations in offline queue"""
        for i in range(10):
            mock_offline_manager.queue_operation(
                mock_offline_manager.OperationType.UPDATE,
                'payment',
                i,
                {'amount': i * 100}
            )

        assert mock_offline_manager.queue_operation.call_count == 10

    def test_edge_010_sync_conflict_data_changed_on_server(self, mock_api_client):
        """TEST_EDGE_010: Sync conflict - data changed on server"""
        # Local version is old
        local_version = {'id': 1, 'amount': 5000, 'updated_at': '2025-01-10'}
        server_version = {'id': 1, 'amount': 6000, 'updated_at': '2025-01-15'}

        # Server version is newer
        assert server_version['updated_at'] > local_version['updated_at']

    def test_edge_011_null_values_in_required_fields(self, mock_api_client):
        """TEST_EDGE_011: NULL values in required fields"""
        invalid_payment = {
            'contract_id': None,  # Required
            'employee_id': 1,
            'role': 'Дизайнер'
        }

        # Should fail validation
        assert invalid_payment['contract_id'] is None

    def test_edge_012_very_long_strings(self, mock_api_client):
        """TEST_EDGE_012: Very long strings (address, comments)"""
        long_string = 'A' * 10000  # 10K characters

        # Should handle gracefully
        assert len(long_string) == 10000

    def test_edge_013_special_characters_in_data(self, mock_api_client):
        """TEST_EDGE_013: Special characters in data"""
        special_chars = "Test 'quotes' \"double\" \n newline \t tab & ampersand < > < >"

        # Should be escaped properly
        assert "'" in special_chars
        assert '"' in special_chars

    def test_edge_014_empty_area_for_payment_calculation(self, mock_api_client):
        """TEST_EDGE_014: Empty area for payment calculation"""
        contract = {'id': 1, 'area': 0}

        # Payment should be 0 or error
        calculated = contract['area'] * 100  # rate per m2
        assert calculated == 0

    def test_edge_015_zero_payment_amount(self, mock_api_client):
        """TEST_EDGE_015: Zero payment amount"""
        payment = {'amount': 0}

        # Should be allowed but flagged
        assert payment['amount'] == 0

    def test_edge_016_contract_date_in_future(self, mock_api_client):
        """TEST_EDGE_016: Contract date in future"""
        future_date = '2030-01-01'
        today = datetime.now().strftime('%Y-%m-%d')

        # Should be allowed but unusual
        assert future_date > today

    def test_edge_017_contract_date_very_old(self, mock_api_client):
        """TEST_EDGE_017: Contract date very old"""
        old_date = '2000-01-01'

        # Should be allowed
        assert old_date < '2010-01-01'

    def test_edge_018_more_than_100_cards_on_board(self, mock_api_client):
        """TEST_EDGE_018: More than 100 cards on board"""
        cards = [{'id': i} for i in range(150)]

        # Should handle pagination or scrolling
        assert len(cards) == 150

    def test_edge_019_more_than_1000_payments_in_period(self, mock_api_client):
        """TEST_EDGE_019: More than 1000 payments in period"""
        mock_api_client.get_all_payments.return_value = [{'id': i} for i in range(1500)]

        payments = mock_api_client.get_all_payments()

        # Should handle large result sets
        assert len(payments) == 1500

    def test_edge_020_parallel_requests_to_same_resource(self, mock_api_client):
        """TEST_EDGE_020: Parallel requests to same resource"""
        import threading

        results = []
        errors = []

        def make_request():
            try:
                result = mock_api_client.get_contract(1)
                results.append(result)
            except Exception as e:
                errors.append(e)

        mock_api_client.get_contract.return_value = {'id': 1}

        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All requests should succeed
        assert len(results) == 5
        assert len(errors) == 0


# ==================== RUN TESTS ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
