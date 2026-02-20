# -*- coding: utf-8 -*-
"""
Тесты валидаторов — телефон, email, ИНН, паспорт, номер договора
"""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.validators import (
    validate_phone, validate_email, validate_date,
    validate_required, validate_positive_number,
    validate_inn, validate_passport, validate_contract_number,
    sanitize_string, format_phone, format_passport,
    ValidationError
)


class TestValidatePhone:
    def test_valid_phone(self):
        assert validate_phone("+7 (900) 123-45-67") is True

    def test_empty_phone_raises(self):
        with pytest.raises(ValidationError, match="не может быть пустым"):
            validate_phone("")

    def test_none_phone_raises(self):
        with pytest.raises(ValidationError):
            validate_phone(None)

    def test_wrong_format_raises(self):
        with pytest.raises(ValidationError, match="Неверный формат"):
            validate_phone("89001234567")

    def test_no_country_code(self):
        with pytest.raises(ValidationError):
            validate_phone("(900) 123-45-67")

    def test_extra_digits(self):
        with pytest.raises(ValidationError):
            validate_phone("+7 (900) 123-45-678")

    def test_letters_in_phone(self):
        with pytest.raises(ValidationError):
            validate_phone("+7 (ABC) 123-45-67")


class TestValidateEmail:
    def test_valid_email(self):
        assert validate_email("user@example.com") is True

    def test_empty_email_allowed(self):
        assert validate_email("") is True

    def test_none_email_allowed(self):
        assert validate_email(None) is True

    def test_no_at_sign(self):
        with pytest.raises(ValidationError):
            validate_email("userexample.com")

    def test_no_domain(self):
        with pytest.raises(ValidationError):
            validate_email("user@")

    def test_no_tld(self):
        with pytest.raises(ValidationError):
            validate_email("user@example")

    def test_valid_complex_email(self):
        assert validate_email("user.name+tag@sub.domain.co.uk") is True


class TestValidateDate:
    def test_valid_date(self):
        assert validate_date("15.01.2025") is True

    def test_empty_date_allowed(self):
        assert validate_date("") is True

    def test_wrong_format(self):
        with pytest.raises(ValidationError, match="Неверный формат"):
            validate_date("2025-01-15")

    def test_custom_format(self):
        assert validate_date("2025-01-15", "%Y-%m-%d") is True

    def test_invalid_date_value(self):
        with pytest.raises(ValidationError):
            validate_date("32.13.2025")


class TestValidateRequired:
    def test_filled_value(self):
        assert validate_required("text", "field") is True

    def test_none_raises(self):
        with pytest.raises(ValidationError, match="обязательно"):
            validate_required(None, "Имя")

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError):
            validate_required("", "Имя")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError):
            validate_required("   ", "Имя")

    def test_zero_is_valid(self):
        assert validate_required(0, "Сумма") is True

    def test_false_is_valid(self):
        assert validate_required(False, "Флаг") is True


class TestValidatePositiveNumber:
    def test_positive_int(self):
        assert validate_positive_number(5, "Сумма") is True

    def test_positive_float(self):
        assert validate_positive_number(10.5, "Площадь") is True

    def test_zero_is_valid(self):
        assert validate_positive_number(0, "Сумма") is True

    def test_none_allowed(self):
        assert validate_positive_number(None, "Сумма") is True

    def test_negative_raises(self):
        with pytest.raises(ValidationError, match="положительным"):
            validate_positive_number(-5, "Сумма")

    def test_string_raises(self):
        with pytest.raises(ValidationError, match="числом"):
            validate_positive_number("abc", "Сумма")


class TestValidateINN:
    def test_valid_inn_10(self):
        assert validate_inn("1234567890") is True

    def test_valid_inn_12(self):
        assert validate_inn("123456789012") is True

    def test_empty_allowed(self):
        assert validate_inn("") is True

    def test_9_digits_raises(self):
        with pytest.raises(ValidationError, match="10 или 12"):
            validate_inn("123456789")

    def test_11_digits_raises(self):
        with pytest.raises(ValidationError):
            validate_inn("12345678901")

    def test_letters_raise(self):
        with pytest.raises(ValidationError):
            validate_inn("12345ABCDE")


class TestValidatePassport:
    def test_valid_passport(self):
        assert validate_passport("1234 567890") is True

    def test_empty_allowed(self):
        assert validate_passport("") is True

    def test_no_space(self):
        with pytest.raises(ValidationError, match="XXXX XXXXXX"):
            validate_passport("1234567890")

    def test_wrong_length(self):
        with pytest.raises(ValidationError):
            validate_passport("123 567890")


class TestValidateContractNumber:
    def test_valid_number(self):
        assert validate_contract_number("12/2025") is True

    def test_empty_raises(self):
        with pytest.raises(ValidationError, match="обязателен"):
            validate_contract_number("")

    def test_no_slash(self):
        with pytest.raises(ValidationError):
            validate_contract_number("122025")

    def test_wrong_year_format(self):
        with pytest.raises(ValidationError):
            validate_contract_number("12/25")

    def test_valid_long_number(self):
        assert validate_contract_number("123/2025") is True


class TestSanitizeString:
    def test_removes_html(self):
        assert sanitize_string("<b>text</b>") == "text"

    def test_escapes_sql_quotes(self):
        result = sanitize_string("O'Brien")
        assert "''" in result

    def test_strips_whitespace(self):
        assert sanitize_string("  hello  ") == "hello"

    def test_empty_returns_empty(self):
        assert sanitize_string("") == ""

    def test_none_returns_none(self):
        assert sanitize_string(None) is None

    def test_nested_html_removed(self):
        assert sanitize_string("<div><p>text</p></div>") == "text"

    def test_script_tag_removed(self):
        result = sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result


class TestFormatPhone:
    def test_format_from_digits(self):
        assert format_phone("79001234567") == "+7 (900) 123-45-67"

    def test_format_from_8(self):
        assert format_phone("89001234567") == "+7 (900) 123-45-67"

    def test_already_formatted(self):
        result = format_phone("+7 (900) 123-45-67")
        assert result == "+7 (900) 123-45-67"

    def test_with_dashes(self):
        result = format_phone("+7-900-123-45-67")
        assert result == "+7 (900) 123-45-67"

    def test_empty_returns_empty(self):
        assert format_phone("") == ""

    def test_none_returns_none(self):
        assert format_phone(None) is None

    def test_short_number_unchanged(self):
        assert format_phone("123") == "123"


class TestFormatPassport:
    def test_format_digits(self):
        assert format_passport("1234567890") == "1234 567890"

    def test_already_formatted(self):
        assert format_passport("1234 567890") == "1234 567890"

    def test_empty_returns_empty(self):
        assert format_passport("") == ""

    def test_wrong_length_unchanged(self):
        assert format_passport("12345") == "12345"
