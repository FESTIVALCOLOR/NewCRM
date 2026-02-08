"""
Interior Studio CRM - Test Configuration and Fixtures
Provides common fixtures for all test modules
"""

import os
import sys
import json
import sqlite3
import tempfile
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, MagicMock, patch
from contextlib import contextmanager

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('tests')

# Test logs directory
LOGS_DIR = PROJECT_ROOT / 'tests' / 'logs'
LOGS_DIR.mkdir(exist_ok=True)


# ============================================================================
# SESSION FIXTURES
# ============================================================================

@pytest.fixture(scope='session')
def project_root() -> Path:
    """Return project root directory"""
    return PROJECT_ROOT


@pytest.fixture(scope='session')
def test_log_file() -> Path:
    """Create test log file for this session"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = LOGS_DIR / f'test_results_{timestamp}.log'

    # Configure file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    logging.getLogger().addHandler(file_handler)

    logger.info(f"Test session started, logging to {log_file}")
    return log_file


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def temp_db_path(tmp_path) -> Path:
    """Create temporary database path"""
    return tmp_path / 'test_interior_studio.db'


@pytest.fixture
def temp_db(temp_db_path) -> sqlite3.Connection:
    """Create temporary SQLite database with schema"""
    conn = sqlite3.connect(str(temp_db_path))
    conn.row_factory = sqlite3.Row

    # Create tables
    conn.executescript('''
        -- Employees table
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            position TEXT,
            department TEXT,
            role TEXT DEFAULT 'user',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Clients table
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            client_type TEXT DEFAULT 'individual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Contracts table
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_number TEXT UNIQUE NOT NULL,
            client_id INTEGER REFERENCES clients(id),
            project_type TEXT,
            address TEXT,
            area REAL,
            total_area REAL,
            rooms_count INTEGER,
            contract_date TEXT,
            contract_amount REAL,
            status TEXT DEFAULT 'active',
            yandex_folder_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- CRM Cards table
        CREATE TABLE IF NOT EXISTS crm_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER REFERENCES contracts(id) ON DELETE CASCADE,
            column_name TEXT DEFAULT 'new_order',
            project_type TEXT,
            priority TEXT DEFAULT 'Средний',
            on_pause INTEGER DEFAULT 0,
            pause_date TEXT,
            column_before_pause TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Supervision Cards table
        CREATE TABLE IF NOT EXISTS supervision_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER REFERENCES contracts(id) ON DELETE CASCADE,
            status TEXT DEFAULT 'active',
            column_name TEXT DEFAULT 'Договор',
            dan_id INTEGER REFERENCES employees(id),
            pause_reason TEXT,
            pause_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Stage Executors table
        CREATE TABLE IF NOT EXISTS stage_executors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crm_card_id INTEGER REFERENCES crm_cards(id) ON DELETE CASCADE,
            stage_name TEXT NOT NULL,
            executor_id INTEGER REFERENCES employees(id),
            executor_type TEXT,
            role TEXT,
            deadline TEXT,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(crm_card_id, stage_name) ON CONFLICT REPLACE
        );

        -- Payments table
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER REFERENCES contracts(id),
            employee_id INTEGER REFERENCES employees(id),
            crm_card_id INTEGER REFERENCES crm_cards(id),
            stage_name TEXT,
            role TEXT,
            payment_type TEXT,
            calculated_amount REAL DEFAULT 0,
            manual_amount REAL,
            final_amount REAL DEFAULT 0,
            payment_status TEXT DEFAULT 'pending',
            report_month TEXT,
            reassigned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Rates table
        CREATE TABLE IF NOT EXISTS rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rate_type TEXT NOT NULL,
            role TEXT,
            stage_name TEXT,
            area_from REAL,
            area_to REAL,
            price REAL,
            executor_rate REAL,
            manager_rate REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Action History table
        CREATE TABLE IF NOT EXISTS action_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            user_id INTEGER REFERENCES employees(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Offline Queue table
        CREATE TABLE IF NOT EXISTS offline_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            data TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            sync_attempts INTEGER DEFAULT 0,
            last_error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced_at TIMESTAMP
        );

        -- Card History table
        CREATE TABLE IF NOT EXISTS card_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crm_card_id INTEGER REFERENCES crm_cards(id) ON DELETE CASCADE,
            action_type TEXT NOT NULL,
            action_description TEXT,
            old_value TEXT,
            new_value TEXT,
            user_id INTEGER REFERENCES employees(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()

    yield conn
    conn.close()


@pytest.fixture
def db_with_data(temp_db) -> sqlite3.Connection:
    """Database with sample test data"""
    cursor = temp_db.cursor()

    # Insert test employees
    cursor.executemany('''
        INSERT INTO employees (login, password_hash, full_name, position, role)
        VALUES (?, ?, ?, ?, ?)
    ''', [
        ('admin', 'hashed_password', 'Admin User', 'Administrator', 'admin'),
        ('designer1', 'hashed_password', 'Designer One', 'Designer', 'user'),
        ('manager1', 'hashed_password', 'Manager One', 'Senior Project Manager', 'user'),
        ('surveyor1', 'hashed_password', 'Surveyor One', 'Surveyor', 'user'),
    ])

    # Insert test clients
    cursor.executemany('''
        INSERT INTO clients (full_name, phone, client_type)
        VALUES (?, ?, ?)
    ''', [
        ('Test Client 1', '+7 900 111 2233', 'individual'),
        ('Test Company LLC', '+7 900 444 5566', 'company'),
    ])

    # Insert test contracts
    cursor.executemany('''
        INSERT INTO contracts (contract_number, client_id, project_type, address, area, contract_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', [
        ('D-2025-001', 1, 'Individual', 'Test Address 1', 100.5, '2025-01-15', 'active'),
        ('D-2025-002', 2, 'Template', 'Test Address 2', 250.0, '2025-01-20', 'active'),
    ])

    # Insert CRM cards
    cursor.executemany('''
        INSERT INTO crm_cards (contract_id, column_name)
        VALUES (?, ?)
    ''', [
        (1, 'new_order'),
        (2, 'in_progress'),
    ])

    # Insert supervision cards
    cursor.execute('''
        INSERT INTO supervision_cards (contract_id, status, dan_id)
        VALUES (?, ?, ?)
    ''', (1, 'active', 2))

    # Insert payments
    cursor.executemany('''
        INSERT INTO payments (contract_id, employee_id, stage_name, role, payment_type,
                             calculated_amount, final_amount, payment_status, reassigned)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        (1, 2, 'Design', 'Designer', 'advance', 5000.0, 5000.0, 'pending', 0),
        (1, 2, 'Design', 'Designer', 'completion', 5000.0, 5000.0, 'pending', 0),
        (1, 3, 'Management', 'Senior Project Manager', 'full', 3000.0, 3000.0, 'paid', 0),
    ])

    temp_db.commit()
    return temp_db


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================

@pytest.fixture
def mock_api_response():
    """Factory for creating mock API responses"""
    def _create_response(status_code: int = 200, json_data: Any = None,
                         raise_for_status: bool = False):
        response = Mock()
        response.status_code = status_code
        response.json.return_value = json_data or {}
        response.text = json.dumps(json_data) if json_data else ''
        response.headers = {'Content-Type': 'application/json'}

        if raise_for_status:
            response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
        else:
            response.raise_for_status.return_value = None

        return response
    return _create_response


@pytest.fixture
def mock_api_client(mock_api_response):
    """Mock APIClient for testing"""
    with patch('utils.api_client.requests') as mock_requests:
        # Default successful responses
        mock_requests.get.return_value = mock_api_response(200, {'status': 'ok'})
        mock_requests.post.return_value = mock_api_response(200, {'id': 1})
        mock_requests.put.return_value = mock_api_response(200, {'updated': True})
        mock_requests.patch.return_value = mock_api_response(200, {'updated': True})
        mock_requests.delete.return_value = mock_api_response(200, {'deleted': True})

        yield mock_requests


@pytest.fixture
def api_client_offline():
    """APIClient in offline mode"""
    with patch('utils.api_client.requests') as mock_requests:
        # Simulate connection error
        mock_requests.get.side_effect = Exception("Connection refused")
        mock_requests.post.side_effect = Exception("Connection refused")

        yield mock_requests


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_employee() -> Dict:
    """Sample employee data"""
    return {
        'id': 1,
        'login': 'test_user',
        'full_name': 'Test User',
        'position': 'Designer',
        'department': 'Design',
        'role': 'user',
        'is_active': True
    }


@pytest.fixture
def sample_client() -> Dict:
    """Sample client data"""
    return {
        'id': 1,
        'full_name': 'Test Client',
        'phone': '+7 900 123 4567',
        'email': 'test@example.com',
        'client_type': 'individual'
    }


@pytest.fixture
def sample_contract() -> Dict:
    """Sample contract data"""
    return {
        'id': 1,
        'contract_number': 'D-2025-001',
        'client_id': 1,
        'project_type': 'Individual',
        'address': 'Test Street, 123',
        'area': 150.5,
        'contract_date': '2025-01-15',
        'contract_amount': 500000.0,
        'status': 'active'
    }


@pytest.fixture
def sample_crm_card(sample_contract) -> Dict:
    """Sample CRM card data"""
    return {
        'id': 1,
        'contract_id': sample_contract['id'],
        'column_name': 'new_order',
        'priority': 0,
        'contract': sample_contract
    }


@pytest.fixture
def sample_payment() -> Dict:
    """Sample payment data"""
    return {
        'id': 1,
        'contract_id': 1,
        'employee_id': 2,
        'stage_name': 'Design',
        'role': 'Designer',
        'payment_type': 'advance',
        'calculated_amount': 5000.0,
        'manual_amount': None,
        'final_amount': 5000.0,
        'payment_status': 'pending',
        'report_month': '2025-01',
        'reassigned': False
    }


@pytest.fixture
def sample_payments_list() -> List[Dict]:
    """List of sample payments for testing duplicates"""
    return [
        {
            'id': 1,
            'contract_id': 1,
            'employee_id': 2,
            'stage_name': 'Design',
            'role': 'Designer',
            'payment_type': 'advance',
            'final_amount': 5000.0,
            'reassigned': False
        },
        {
            'id': 2,
            'contract_id': 1,
            'employee_id': 2,
            'stage_name': 'Design',
            'role': 'Designer',
            'payment_type': 'completion',
            'final_amount': 5000.0,
            'reassigned': False
        },
        {
            'id': 3,
            'contract_id': 1,
            'employee_id': 3,
            'stage_name': 'Management',
            'role': 'Senior Project Manager',
            'payment_type': 'full',
            'final_amount': 3000.0,
            'reassigned': False
        },
    ]


# ============================================================================
# PYQT5 FIXTURES (for frontend tests)
# ============================================================================

@pytest.fixture
def qapp():
    """Create QApplication for PyQt5 tests"""
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
    except ImportError:
        pytest.skip("PyQt5 not available")


@pytest.fixture
def mock_qwidget():
    """Mock QWidget for testing"""
    widget = Mock()
    widget.parent.return_value = None
    widget.isVisible.return_value = True
    widget.close.return_value = True
    return widget


# ============================================================================
# OFFLINE MANAGER FIXTURES
# ============================================================================

@pytest.fixture
def offline_queue_data() -> List[Dict]:
    """Sample offline queue operations"""
    return [
        {
            'id': 1,
            'operation_type': 'CREATE',
            'entity_type': 'client',
            'entity_id': None,
            'data': json.dumps({'full_name': 'New Client', 'phone': '+7 900 000 0000'}),
            'status': 'pending'
        },
        {
            'id': 2,
            'operation_type': 'UPDATE',
            'entity_type': 'payment',
            'entity_id': 1,
            'data': json.dumps({'final_amount': 6000.0}),
            'status': 'pending'
        },
    ]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def assert_no_duplicate_payments(payments: List[Dict],
                                  contract_id: int,
                                  stage_name: str,
                                  role: str,
                                  employee_id: int) -> bool:
    """
    Assert there are no duplicate active payments for the same
    contract/stage/role/employee combination.

    This is a critical test helper for the duplicate payment bug.
    """
    active_payments = [
        p for p in payments
        if p.get('contract_id') == contract_id
        and p.get('stage_name') == stage_name
        and p.get('role') == role
        and p.get('employee_id') == employee_id
        and not p.get('reassigned', False)
    ]

    # Group by payment_type
    payment_types = {}
    for p in active_payments:
        pt = p.get('payment_type', 'unknown')
        if pt in payment_types:
            return False  # Duplicate found!
        payment_types[pt] = p

    return True


def create_test_report(results: Dict, log_file: Path) -> str:
    """Create test report and save to log file"""
    report = f"""
================================================================================
TEST REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

Total tests: {results.get('total', 0)}
Passed: {results.get('passed', 0)}
Failed: {results.get('failed', 0)}
Skipped: {results.get('skipped', 0)}
Errors: {results.get('errors', 0)}

Duration: {results.get('duration', 0):.2f} seconds

--------------------------------------------------------------------------------
FAILED TESTS:
--------------------------------------------------------------------------------
"""
    for test_name, error in results.get('failures', {}).items():
        report += f"\n{test_name}:\n{error}\n"

    report += "\n================================================================================\n"

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(report)

    return report


# ============================================================================
# PYTEST HOOKS FOR WARN MODE
# ============================================================================

def pytest_runtest_makereport(item, call):
    """
    Custom hook to implement warn mode.
    Tests warn but don't fail the overall run.
    """
    if call.when == 'call' and call.excinfo is not None:
        # Log the failure
        logger.warning(f"Test FAILED: {item.name}")
        logger.warning(f"Error: {call.excinfo.value}")


def pytest_sessionfinish(session, exitstatus):
    """
    Custom hook to log session results.
    """
    logger.info(f"Test session finished with exit status: {exitstatus}")
    logger.info(f"Total tests collected: {session.testscollected}")

    # Create summary log
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_file = LOGS_DIR / f'session_summary_{timestamp}.txt'

    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"Test Session Summary\n")
        f.write(f"====================\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Total tests: {session.testscollected}\n")
        f.write(f"Exit status: {exitstatus}\n")
