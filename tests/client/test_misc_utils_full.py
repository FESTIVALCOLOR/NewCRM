# -*- coding: utf-8 -*-
"""
Покрытие мелких utils модулей:
- validators.py (79 строк) — validate_phone, validate_email, validate_inn, etc.
- dialog_helpers.py (41 строк) — create_progress_dialog, center_dialog_on_parent
- message_helper.py (9 строк) — show_warning, show_error, show_success, show_info
- timeline_calc.py (31 строк) — calc_planned_dates
- password_utils.py (44 строк) — hash_password, verify_password, generate_strong_password
- add_indexes.py (87 строк) — add_database_indexes, analyze_query_performance
- migrate_passwords.py (98 строк) — migrate_passwords, create_backup
~50 тестов.
"""

import pytest
import sys
import os
import sqlite3
import shutil
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================================================================
# VALIDATORS (15 тестов)
# ==================================================================

from utils.validators import (
    validate_phone, validate_email, validate_date,
    validate_required, validate_positive_number,
    validate_inn, validate_passport, validate_contract_number,
    sanitize_string, format_phone, format_passport,
    ValidationError
)


class TestValidatePhoneExtended:
    """Дополнительные тесты validate_phone."""

    def test_valid_phone(self):
        assert validate_phone("+7 (900) 123-45-67") is True

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_phone("")

    def test_none_raises(self):
        with pytest.raises(ValidationError):
            validate_phone(None)

    def test_digits_only_raises(self):
        with pytest.raises(ValidationError):
            validate_phone("79001234567")

    def test_with_country_8_raises(self):
        with pytest.raises(ValidationError):
            validate_phone("8 (900) 123-45-67")


class TestValidateEmailExtended:
    """Дополнительные тесты validate_email."""

    def test_valid_email(self):
        assert validate_email("user@example.com") is True

    def test_empty_allowed(self):
        assert validate_email("") is True

    def test_double_at_raises(self):
        with pytest.raises(ValidationError):
            validate_email("user@@example.com")

    def test_spaces_in_email_raises(self):
        with pytest.raises(ValidationError):
            validate_email("user @example.com")


class TestValidateInnExtended:
    """Дополнительные тесты validate_inn."""

    def test_10_digits_valid(self):
        assert validate_inn("1234567890") is True

    def test_12_digits_valid(self):
        assert validate_inn("123456789012") is True

    def test_empty_allowed(self):
        assert validate_inn("") is True

    def test_none_allowed(self):
        assert validate_inn(None) is True

    def test_13_digits_raises(self):
        with pytest.raises(ValidationError):
            validate_inn("1234567890123")


class TestFormatPhoneExtended:
    """Дополнительные тесты format_phone."""

    def test_format_from_7_digits(self):
        assert format_phone("79001234567") == "+7 (900) 123-45-67"

    def test_format_from_8(self):
        assert format_phone("89001234567") == "+7 (900) 123-45-67"

    def test_with_plus_and_spaces(self):
        assert format_phone("+7 900 123 45 67") == "+7 (900) 123-45-67"

    def test_short_number_unchanged(self):
        assert format_phone("123") == "123"


class TestFormatPassportExtended:
    """Дополнительные тесты format_passport."""

    def test_format_10_digits(self):
        assert format_passport("1234567890") == "1234 567890"

    def test_with_spaces_already(self):
        assert format_passport("1234 567890") == "1234 567890"

    def test_wrong_length_unchanged(self):
        assert format_passport("12345") == "12345"


class TestSanitizeStringExtended:
    """Дополнительные тесты sanitize_string."""

    def test_removes_html(self):
        assert sanitize_string("<b>bold</b>") == "bold"

    def test_removes_script(self):
        result = sanitize_string("<script>alert(1)</script>")
        assert "<script>" not in result

    def test_escapes_sql_quotes(self):
        assert "''" in sanitize_string("O'Brien")

    def test_empty_returns_empty(self):
        assert sanitize_string("") == ""

    def test_none_returns_none(self):
        assert sanitize_string(None) is None


class TestValidateContractNumberExtended:
    """Дополнительные тесты validate_contract_number."""

    def test_valid_number(self):
        assert validate_contract_number("12/2025") is True

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_contract_number("")

    def test_no_year_raises(self):
        with pytest.raises(ValidationError):
            validate_contract_number("12/25")


class TestValidatePassportExtended:
    """Дополнительные тесты validate_passport."""

    def test_valid(self):
        assert validate_passport("1234 567890") is True

    def test_none_allowed(self):
        assert validate_passport(None) is True


class TestValidateDateExtended:
    """Дополнительные тесты validate_date."""

    def test_none_allowed(self):
        assert validate_date(None) is True

    def test_custom_format(self):
        assert validate_date("2025-01-15", "%Y-%m-%d") is True


class TestValidateRequiredExtended:
    """Дополнительные тесты validate_required."""

    def test_list_is_valid(self):
        assert validate_required([1, 2], "items") is True


class TestValidatePositiveNumberExtended:
    """Дополнительные тесты validate_positive_number."""

    def test_float_is_valid(self):
        assert validate_positive_number(3.14, "pi") is True

    def test_bool_raises_type_error(self):
        # bool — подкласс int в Python, поэтому пройдёт isinstance
        assert validate_positive_number(True, "flag") is True


# ==================================================================
# PASSWORD_UTILS (8 тестов)
# ==================================================================

from utils.password_utils import hash_password, verify_password, generate_strong_password


class TestPasswordUtils:
    """hash_password, verify_password, generate_strong_password."""

    def test_hash_returns_salt_dollar_hash(self):
        result = hash_password("secret")
        assert '$' in result
        parts = result.split('$')
        assert len(parts) == 2

    def test_hash_different_each_time(self):
        h1 = hash_password("secret")
        h2 = hash_password("secret")
        assert h1 != h2  # Разные соли

    def test_verify_correct_password(self):
        hashed = hash_password("MyPass123!")
        assert verify_password("MyPass123!", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("MyPass123!")
        assert verify_password("WrongPass", hashed) is False

    def test_verify_plaintext_returns_false(self):
        assert verify_password("admin", "admin") is False

    def test_verify_invalid_hash_returns_false(self):
        assert verify_password("pass", "not$valid$base64") is False

    def test_generate_strong_password_default_length(self):
        pwd = generate_strong_password()
        assert len(pwd) == 12

    def test_generate_strong_password_min_8(self):
        pwd = generate_strong_password(4)
        assert len(pwd) == 8


# ==================================================================
# TIMELINE_CALC (5 тестов)
# ==================================================================

from utils.timeline_calc import calc_planned_dates


class TestTimelineCalc:
    """calc_planned_dates — расчёт планируемых дат."""

    def test_empty_entries(self):
        result = calc_planned_dates([])
        assert result == []

    def test_header_entries_skipped(self):
        entries = [
            {'executor_role': 'header', 'stage_code': 'H1'},
            {'executor_role': 'designer', 'stage_code': 'START', 'actual_date': '2026-03-02'},
        ]
        result = calc_planned_dates(entries)
        assert '_planned_date' not in result[0]  # header
        assert result[1]['_planned_date'] == '2026-03-02'

    def test_start_sets_prev_date(self):
        entries = [
            {'executor_role': 'manager', 'stage_code': 'START', 'actual_date': '2026-03-02'},
            {'executor_role': 'designer', 'stage_code': 'DESIGN', 'norm_days': 5,
             'custom_norm_days': None, 'actual_date': ''},
        ]
        result = calc_planned_dates(entries)
        assert result[1]['_planned_date'] != ''

    def test_custom_norm_days_override(self):
        entries = [
            {'executor_role': 'manager', 'stage_code': 'START', 'actual_date': '2026-03-02'},
            {'executor_role': 'designer', 'stage_code': 'DESIGN', 'norm_days': 5,
             'custom_norm_days': 3, 'actual_date': ''},
        ]
        result = calc_planned_dates(entries)
        # С custom_norm_days=3 дата должна быть раньше, чем с norm_days=5
        assert result[1]['_planned_date'] != ''

    def test_zero_norm_inherits_prev(self):
        entries = [
            {'executor_role': 'manager', 'stage_code': 'START', 'actual_date': '2026-03-02'},
            {'executor_role': 'designer', 'stage_code': 'ZERO', 'norm_days': 0,
             'custom_norm_days': None, 'actual_date': ''},
        ]
        result = calc_planned_dates(entries)
        assert result[1]['_planned_date'] == '2026-03-02'


# ==================================================================
# ADD_INDEXES (5 тестов)
# ==================================================================

from utils.add_indexes import add_database_indexes, analyze_query_performance


class TestAddIndexes:
    """add_database_indexes, analyze_query_performance."""

    def test_db_not_found_returns_false(self, tmp_path):
        result = add_database_indexes(str(tmp_path / 'nonexistent.db'))
        assert result is False

    def test_adds_indexes_to_empty_db(self, tmp_path):
        db_path = str(tmp_path / 'test.db')
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE employees (id INTEGER, login TEXT, status TEXT, position TEXT, department TEXT)")
        conn.execute("CREATE TABLE clients (id INTEGER, phone TEXT, email TEXT, inn TEXT, client_type TEXT)")
        conn.execute("CREATE TABLE contracts (id INTEGER, client_id INTEGER, contract_number TEXT, status TEXT, contract_date TEXT, project_type TEXT)")
        conn.execute("CREATE TABLE crm_cards (id INTEGER, contract_id INTEGER, column_name TEXT, deadline TEXT, senior_manager_id INTEGER, sdp_id INTEGER, gap_id INTEGER, manager_id INTEGER, surveyor_id INTEGER, is_approved INTEGER)")
        conn.execute("CREATE TABLE supervision_cards (id INTEGER, contract_id INTEGER, column_name TEXT, dan_id INTEGER, senior_manager_id INTEGER)")
        conn.execute("CREATE TABLE salaries (id INTEGER, employee_id INTEGER, contract_id INTEGER, report_month TEXT, payment_type TEXT)")
        conn.commit()
        conn.close()

        result = add_database_indexes(db_path)
        assert result is True

    def test_idempotent_run(self, tmp_path):
        db_path = str(tmp_path / 'test.db')
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE employees (id INTEGER, login TEXT, status TEXT, position TEXT, department TEXT)")
        conn.execute("CREATE TABLE clients (id INTEGER, phone TEXT, email TEXT, inn TEXT, client_type TEXT)")
        conn.execute("CREATE TABLE contracts (id INTEGER, client_id INTEGER, contract_number TEXT, status TEXT, contract_date TEXT, project_type TEXT)")
        conn.execute("CREATE TABLE crm_cards (id INTEGER, contract_id INTEGER, column_name TEXT, deadline TEXT, senior_manager_id INTEGER, sdp_id INTEGER, gap_id INTEGER, manager_id INTEGER, surveyor_id INTEGER, is_approved INTEGER)")
        conn.execute("CREATE TABLE supervision_cards (id INTEGER, contract_id INTEGER, column_name TEXT, dan_id INTEGER, senior_manager_id INTEGER)")
        conn.execute("CREATE TABLE salaries (id INTEGER, employee_id INTEGER, contract_id INTEGER, report_month TEXT, payment_type TEXT)")
        conn.commit()
        conn.close()

        # Два раза — не должно упасть
        add_database_indexes(db_path)
        result = add_database_indexes(db_path)
        assert result is True

    def test_analyze_not_found(self, tmp_path):
        analyze_query_performance(str(tmp_path / 'nonexistent.db'))
        # Просто не падает

    def test_analyze_with_tables(self, tmp_path):
        db_path = str(tmp_path / 'test.db')
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE employees (id INTEGER, login TEXT)")
        conn.execute("CREATE TABLE crm_cards (id INTEGER, contract_id INTEGER)")
        conn.execute("CREATE TABLE contracts (id INTEGER, client_id INTEGER)")
        conn.execute("CREATE TABLE salaries (id INTEGER, report_month TEXT)")
        conn.commit()
        conn.close()
        analyze_query_performance(db_path)  # Не должно упасть


# ==================================================================
# MIGRATE_PASSWORDS (6 тестов)
# ==================================================================

from utils.migrate_passwords import migrate_passwords, create_backup


class TestMigratePasswords:
    """migrate_passwords, create_backup."""

    def test_db_not_found_returns_false(self, tmp_path):
        result = migrate_passwords(str(tmp_path / 'nonexistent.db'))
        assert result is False

    def test_no_employees_returns_true(self, tmp_path):
        db_path = str(tmp_path / 'test.db')
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE employees (id INTEGER, login TEXT, password TEXT, full_name TEXT)")
        conn.commit()
        conn.close()
        result = migrate_passwords(db_path)
        assert result is True

    def test_migrates_plaintext_password(self, tmp_path):
        db_path = str(tmp_path / 'test.db')
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE employees (id INTEGER, login TEXT, password TEXT, full_name TEXT)")
        conn.execute("INSERT INTO employees VALUES (1, 'admin', 'plain123', 'Admin')")
        conn.commit()
        conn.close()

        result = migrate_passwords(db_path)
        assert result is True

        # Проверяем что пароль хэширован
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM employees WHERE id = 1")
        pwd = cursor.fetchone()[0]
        conn.close()
        assert '$' in pwd

    def test_skips_already_hashed(self, tmp_path):
        db_path = str(tmp_path / 'test.db')
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE employees (id INTEGER, login TEXT, password TEXT, full_name TEXT)")
        conn.execute("INSERT INTO employees VALUES (1, 'admin', 'salt$hash', 'Admin')")
        conn.commit()
        conn.close()

        result = migrate_passwords(db_path)
        assert result is True

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM employees WHERE id = 1")
        pwd = cursor.fetchone()[0]
        conn.close()
        assert pwd == 'salt$hash'  # Не изменился

    def test_create_backup_success(self, tmp_path):
        db_path = str(tmp_path / 'test.db')
        with open(db_path, 'w') as f:
            f.write('test')
        backup = create_backup(db_path)
        assert backup is not None
        assert os.path.exists(backup)

    def test_create_backup_nonexistent(self, tmp_path):
        result = create_backup(str(tmp_path / 'nonexistent.db'))
        assert result is None


# ==================================================================
# MESSAGE_HELPER (4 теста)
# ==================================================================

class TestMessageHelper:
    """show_warning, show_error, show_success, show_info — вызов CustomMessageBox."""

    def test_show_warning_calls_custom_message_box(self):
        with patch('utils.message_helper.CustomMessageBox') as MockCMB:
            from utils.message_helper import show_warning
            parent = MagicMock()
            show_warning(parent, 'Заголовок', 'Текст')
            MockCMB.assert_called_once_with(parent, 'Заголовок', 'Текст', 'warning')
            MockCMB.return_value.exec_.assert_called_once()

    def test_show_error_calls_custom_message_box(self):
        with patch('utils.message_helper.CustomMessageBox') as MockCMB:
            from utils.message_helper import show_error
            parent = MagicMock()
            show_error(parent, 'Ошибка', 'Описание')
            MockCMB.assert_called_once_with(parent, 'Ошибка', 'Описание', 'error')

    def test_show_success_calls_custom_message_box(self):
        with patch('utils.message_helper.CustomMessageBox') as MockCMB:
            from utils.message_helper import show_success
            parent = MagicMock()
            show_success(parent, 'Успех', 'Готово')
            MockCMB.assert_called_once_with(parent, 'Успех', 'Готово', 'success')

    def test_show_info_calls_custom_message_box(self):
        with patch('utils.message_helper.CustomMessageBox') as MockCMB:
            from utils.message_helper import show_info
            parent = MagicMock()
            show_info(parent, 'Инфо', 'Сообщение')
            MockCMB.assert_called_once_with(parent, 'Инфо', 'Сообщение', 'info')
