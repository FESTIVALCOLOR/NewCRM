# -*- coding: utf-8 -*-
"""
Полное покрытие utils/validators.py — ~40 тестов.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.validators import (
    ValidationError, validate_phone, validate_email, validate_date,
    validate_required, validate_positive_number, validate_inn,
    validate_passport, validate_contract_number, sanitize_string,
    format_phone, format_passport
)


# ========== validate_phone (6 тестов) ==========

class TestValidatePhone:
    def test_valid_phone(self):
        assert validate_phone('+7 (999) 123-45-67') is True

    def test_empty_phone_raises(self):
        with pytest.raises(ValidationError, match="пустым"):
            validate_phone('')

    def test_none_phone_raises(self):
        with pytest.raises(ValidationError, match="пустым"):
            validate_phone(None)

    def test_invalid_format_raises(self):
        with pytest.raises(ValidationError, match="формат"):
            validate_phone('89991234567')

    def test_short_phone_raises(self):
        with pytest.raises(ValidationError):
            validate_phone('+7 (999) 123')

    def test_letters_in_phone_raises(self):
        with pytest.raises(ValidationError):
            validate_phone('+7 (abc) 123-45-67')


# ========== validate_email (5 тестов) ==========

class TestValidateEmail:
    def test_valid_email(self):
        assert validate_email('user@example.com') is True

    def test_empty_email_ok(self):
        assert validate_email('') is True

    def test_none_email_ok(self):
        assert validate_email(None) is True

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError, match="email"):
            validate_email('not-an-email')

    def test_email_without_domain(self):
        with pytest.raises(ValidationError):
            validate_email('user@')


# ========== validate_date (4 теста) ==========

class TestValidateDate:
    def test_valid_date(self):
        assert validate_date('15.03.2026') is True

    def test_empty_date_ok(self):
        assert validate_date('') is True

    def test_invalid_date_raises(self):
        with pytest.raises(ValidationError, match="формат даты"):
            validate_date('2026-03-15')

    def test_custom_format(self):
        assert validate_date('2026-03-15', '%Y-%m-%d') is True


# ========== validate_required (4 теста) ==========

class TestValidateRequired:
    def test_filled_value(self):
        assert validate_required('hello', 'name') is True

    def test_none_raises(self):
        with pytest.raises(ValidationError, match="обязательно"):
            validate_required(None, 'name')

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError, match="обязательно"):
            validate_required('', 'name')

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="обязательно"):
            validate_required('   ', 'name')


# ========== validate_positive_number (5 тестов) ==========

class TestValidatePositiveNumber:
    def test_positive_int(self):
        assert validate_positive_number(10, 'amount') is True

    def test_positive_float(self):
        assert validate_positive_number(10.5, 'amount') is True

    def test_zero_ok(self):
        assert validate_positive_number(0, 'amount') is True

    def test_none_ok(self):
        assert validate_positive_number(None, 'amount') is True

    def test_negative_raises(self):
        with pytest.raises(ValidationError, match="положительным"):
            validate_positive_number(-1, 'amount')

    def test_string_raises(self):
        with pytest.raises(ValidationError, match="числом"):
            validate_positive_number('abc', 'amount')


# ========== validate_inn (4 теста) ==========

class TestValidateInn:
    def test_valid_10_digits(self):
        assert validate_inn('1234567890') is True

    def test_valid_12_digits(self):
        assert validate_inn('123456789012') is True

    def test_empty_ok(self):
        assert validate_inn('') is True

    def test_invalid_length_raises(self):
        with pytest.raises(ValidationError, match="10 или 12"):
            validate_inn('12345')


# ========== validate_passport (3 теста) ==========

class TestValidatePassport:
    def test_valid_passport(self):
        assert validate_passport('4510 123456') is True

    def test_empty_ok(self):
        assert validate_passport('') is True

    def test_invalid_format_raises(self):
        with pytest.raises(ValidationError, match="формат паспорта"):
            validate_passport('4510123456')


# ========== validate_contract_number (3 теста) ==========

class TestValidateContractNumber:
    def test_valid_number(self):
        assert validate_contract_number('123/2026') is True

    def test_empty_raises(self):
        with pytest.raises(ValidationError, match="обязателен"):
            validate_contract_number('')

    def test_invalid_format_raises(self):
        with pytest.raises(ValidationError, match="формат"):
            validate_contract_number('ABC-2026')


# ========== sanitize_string (4 теста) ==========

class TestSanitizeString:
    def test_removes_html(self):
        assert sanitize_string('hello <script>alert(1)</script> world') == "hello alert(1) world"

    def test_escapes_single_quote(self):
        assert sanitize_string("O'Brien") == "O''Brien"

    def test_strips_whitespace(self):
        assert sanitize_string('  hello  ') == 'hello'

    def test_empty_returns_as_is(self):
        assert sanitize_string('') == ''

    def test_none_returns_none(self):
        assert sanitize_string(None) is None


# ========== format_phone (5 тестов) ==========

class TestFormatPhone:
    def test_format_from_digits(self):
        assert format_phone('79991234567') == '+7 (999) 123-45-67'

    def test_format_with_8(self):
        assert format_phone('89991234567') == '+7 (999) 123-45-67'

    def test_empty_returns_empty(self):
        assert format_phone('') == ''

    def test_none_returns_none(self):
        assert format_phone(None) is None

    def test_short_number_returned_as_is(self):
        assert format_phone('123') == '123'


# ========== format_passport (4 теста) ==========

class TestFormatPassport:
    def test_format_10_digits(self):
        assert format_passport('4510123456') == '4510 123456'

    def test_already_formatted(self):
        # Already formatted string returns differently since digits extracted
        result = format_passport('4510 123456')
        assert result == '4510 123456'

    def test_empty_returns_empty(self):
        assert format_passport('') == ''

    def test_none_returns_none(self):
        assert format_passport(None) is None
