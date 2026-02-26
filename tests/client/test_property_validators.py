# -*- coding: utf-8 -*-
"""
Property-based тесты валидаторов (hypothesis).

Генерация случайных входных данных для проверки:
- Отсутствие необработанных исключений (fuzz)
- Идемпотентность форматирующих функций
- Корректность типов возвращаемых значений
- Инвариант: отформатированный телефон проходит валидацию
"""
import sys
from pathlib import Path

import pytest

hypothesis = pytest.importorskip("hypothesis", reason="hypothesis не установлен — пропуск property-based тестов")

from hypothesis import given, assume, settings, HealthCheck
import hypothesis.strategies as st

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.validators import (
    validate_phone,
    validate_email,
    validate_passport,
    validate_inn,
    format_phone,
    format_passport,
    ValidationError,
)


# ============================================================================
# Вспомогательные стратегии
# ============================================================================

# Стратегия: валидный российский телефон в различных форматах (11 цифр, начинается с 7 или 8)
russian_phone_digits = st.from_regex(r"[78]\d{10}", fullmatch=True)

# Стратегия: паспорт — ровно 10 цифр (серия 4 + номер 6)
passport_10_digits = st.from_regex(r"\d{10}", fullmatch=True)

# Стратегия: валидный паспорт в отформатированном виде "XXXX XXXXXX"
valid_passport = st.from_regex(r"\d{4} \d{6}", fullmatch=True)

# Стратегия: произвольная текстовая строка (включая unicode, спецсимволы, пустая)
any_text = st.text(min_size=0, max_size=200)

# Стратегия: ИНН — 10 или 12 цифр
valid_inn_10 = st.from_regex(r"\d{10}", fullmatch=True)
valid_inn_12 = st.from_regex(r"\d{12}", fullmatch=True)
valid_inn = st.one_of(valid_inn_10, valid_inn_12)


# ============================================================================
# 1. Валидный телефон после format_phone остаётся валидным
# ============================================================================

class TestFormatPhonePreservesValidity:
    """Любой валидный российский номер после format_phone проходит validate_phone."""

    @given(digits=russian_phone_digits)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_formatted_phone_is_valid(self, digits):
        """Отформатированный номер из 11 цифр (7/8...) всегда проходит validate_phone."""
        formatted = format_phone(digits)
        # format_phone возвращает +7 (XXX) XXX-XX-XX для 11-значных номеров
        assert validate_phone(formatted) is True


# ============================================================================
# 2. validate_phone не падает ни на каких строках (fuzz)
# ============================================================================

class TestValidatePhoneFuzz:
    """validate_phone никогда не бросает необработанное исключение, кроме ValidationError."""

    @given(phone=any_text)
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_no_unexpected_exceptions(self, phone):
        """На произвольной строке validate_phone возвращает True или бросает ValidationError."""
        try:
            result = validate_phone(phone)
            assert result is True
        except ValidationError:
            pass  # ожидаемое поведение


# ============================================================================
# 3. validate_email не падает ни на каких строках (fuzz)
# ============================================================================

class TestValidateEmailFuzz:
    """validate_email никогда не бросает необработанное исключение, кроме ValidationError."""

    @given(email=any_text)
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_no_unexpected_exceptions(self, email):
        """На произвольной строке validate_email возвращает True или бросает ValidationError."""
        try:
            result = validate_email(email)
            assert result is True
        except ValidationError:
            pass  # ожидаемое поведение


# ============================================================================
# 4. validate_passport принимает только правильный формат
# ============================================================================

class TestValidatePassportFormat:
    """validate_passport принимает строки формата 'XXXX XXXXXX' и пустые."""

    @given(passport=valid_passport)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_valid_format_always_accepted(self, passport):
        """Строка формата 'XXXX XXXXXX' всегда принимается."""
        assert validate_passport(passport) is True

    @given(text=any_text)
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_random_string_either_valid_or_rejected(self, text):
        """Произвольная строка либо проходит валидацию, либо отклоняется через ValidationError."""
        try:
            result = validate_passport(text)
            # Если прошло — строка либо пустая, либо соответствует формату XXXX XXXXXX
            assert result is True
            if text:
                import re
                assert re.match(r'^\d{4} \d{6}$', text), (
                    f"validate_passport приняла невалидную строку: {text!r}"
                )
        except ValidationError:
            pass  # ожидаемое отклонение


# ============================================================================
# 5. format_passport(format_passport(x)) == format_passport(x) — идемпотентность
# ============================================================================

class TestFormatPassportIdempotent:
    """Повторное форматирование паспорта не меняет результат."""

    @given(text=any_text)
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_idempotent_on_any_string(self, text):
        """format_passport(format_passport(x)) == format_passport(x) для любой строки."""
        once = format_passport(text)
        twice = format_passport(once)
        assert twice == once, (
            f"Идемпотентность нарушена: format_passport({text!r}) = {once!r}, "
            f"format_passport({once!r}) = {twice!r}"
        )

    @given(digits=passport_10_digits)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_idempotent_on_10_digit_input(self, digits):
        """format_passport идемпотентен для входа из ровно 10 цифр."""
        once = format_passport(digits)
        twice = format_passport(once)
        assert twice == once


# ============================================================================
# 6. validate_inn не падает на случайных строках
# ============================================================================

class TestValidateInnFuzz:
    """validate_inn никогда не бросает необработанное исключение, кроме ValidationError."""

    @given(inn=any_text)
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_no_unexpected_exceptions(self, inn):
        """На произвольной строке validate_inn возвращает True или бросает ValidationError."""
        try:
            result = validate_inn(inn)
            assert result is True
        except ValidationError:
            pass  # ожидаемое поведение

    @given(inn=valid_inn)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_valid_inn_always_accepted(self, inn):
        """ИНН из 10 или 12 цифр всегда принимается."""
        assert validate_inn(inn) is True


# ============================================================================
# 7. format_phone(None) и format_phone("") не падают
# ============================================================================

class TestFormatPhoneEdgeCases:
    """format_phone корректно обрабатывает граничные значения."""

    def test_none_does_not_crash(self):
        """format_phone(None) не бросает исключение."""
        result = format_phone(None)
        assert result is None

    def test_empty_string_does_not_crash(self):
        """format_phone('') не бросает исключение."""
        result = format_phone("")
        assert result == ""

    @given(text=any_text)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_format_phone_never_crashes(self, text):
        """format_phone не бросает исключение на произвольной строке."""
        result = format_phone(text)
        assert isinstance(result, str)


# ============================================================================
# 8. Все валидаторы возвращают bool или строку (проверка типов)
# ============================================================================

class TestValidatorReturnTypes:
    """Все валидаторы возвращают bool (True) при успехе или бросают ValidationError."""

    @given(text=any_text)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_validate_phone_returns_bool_or_raises(self, text):
        """validate_phone возвращает bool или бросает ValidationError."""
        try:
            result = validate_phone(text)
            assert isinstance(result, bool), (
                f"validate_phone вернула {type(result).__name__}, ожидался bool"
            )
        except ValidationError:
            pass

    @given(text=any_text)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_validate_email_returns_bool_or_raises(self, text):
        """validate_email возвращает bool или бросает ValidationError."""
        try:
            result = validate_email(text)
            assert isinstance(result, bool), (
                f"validate_email вернула {type(result).__name__}, ожидался bool"
            )
        except ValidationError:
            pass

    @given(text=any_text)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_validate_passport_returns_bool_or_raises(self, text):
        """validate_passport возвращает bool или бросает ValidationError."""
        try:
            result = validate_passport(text)
            assert isinstance(result, bool), (
                f"validate_passport вернула {type(result).__name__}, ожидался bool"
            )
        except ValidationError:
            pass

    @given(text=any_text)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_validate_inn_returns_bool_or_raises(self, text):
        """validate_inn возвращает bool или бросает ValidationError."""
        try:
            result = validate_inn(text)
            assert isinstance(result, bool), (
                f"validate_inn вернула {type(result).__name__}, ожидался bool"
            )
        except ValidationError:
            pass

    @given(text=any_text)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_format_phone_returns_str_or_none(self, text):
        """format_phone возвращает строку для строкового входа."""
        result = format_phone(text)
        assert isinstance(result, str), (
            f"format_phone вернула {type(result).__name__}, ожидался str"
        )

    @given(text=any_text)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_format_passport_returns_str_or_none(self, text):
        """format_passport возвращает строку для строкового входа."""
        result = format_passport(text)
        assert isinstance(result, str), (
            f"format_passport вернула {type(result).__name__}, ожидался str"
        )
