# -*- coding: utf-8 -*-
"""
Property-based тесты утилит дат (utils/date_utils.py).

Тестируемые функции:
- format_date: форматирование в ДД.ММ.ГГГГ
- format_month_year: "ГГГГ-ММ" → "месяц ГГГГ"
- is_working_day: True/False для рабочих/выходных
- networkdays: количество рабочих дней между датами
- add_working_days: добавление рабочих дней к дате

Инварианты:
- format_date(iso_string) всегда возвращает строку
- round-trip: format_date парсит то, что сам генерирует
- networkdays >= 0
- add_working_days возвращает дату >= start_date
"""

from datetime import date, datetime, timedelta
import os
import sys
from unittest.mock import MagicMock

from hypothesis import assume, given, settings
from hypothesis import strategies as st
import pytest

# Мокируем PyQt5 для импорта date_utils без Qt
_qt_mock = MagicMock()
_qt_mock.QDate = MagicMock
_qt_mock.QDateTime = MagicMock
sys.modules.setdefault("PyQt5", MagicMock())
sys.modules.setdefault("PyQt5.QtCore", _qt_mock)

from tests.property.conftest import date_strings_iso, date_strings_ru, month_strings

# Импортируем после мока PyQt5
from utils.date_utils import (
    MONTHS_RU,
    add_working_days,
    format_date,
    format_month_year,
    is_working_day,
    networkdays,
)

pytestmark = pytest.mark.property


class TestFormatDate:
    """Property-тесты format_date."""

    @given(d=st.dates(min_value=date(2000, 1, 1), max_value=date(2099, 12, 31)))
    @settings(max_examples=200)
    def test_iso_string_returns_dd_mm_yyyy(self, d):
        """ISO строка 'YYYY-MM-DD' → формат 'ДД.ММ.ГГГГ'."""
        iso = d.strftime("%Y-%m-%d")
        result = format_date(iso)
        assert isinstance(result, str)
        assert len(result) == 10, f"Неверная длина: '{result}' для {iso}"
        assert result[2] == "." and result[5] == ".", f"Неверный формат: '{result}'"
        # Проверяем компоненты
        dd, mm, yyyy = result.split(".")
        assert int(dd) == d.day
        assert int(mm) == d.month
        assert int(yyyy) == d.year

    @given(d=st.dates(min_value=date(2000, 1, 1), max_value=date(2099, 12, 31)))
    @settings(max_examples=200)
    def test_datetime_object_formatted(self, d):
        """datetime объект → корректный ДД.ММ.ГГГГ."""
        dt = datetime(d.year, d.month, d.day, 12, 30, 0)
        result = format_date(dt)
        expected = d.strftime("%d.%m.%Y")
        assert result == expected, f"datetime {dt} → '{result}', ожидалось '{expected}'"

    @given(d=st.dates(min_value=date(2000, 1, 1), max_value=date(2099, 12, 31)))
    @settings(max_examples=200)
    def test_round_trip_iso_to_formatted(self, d):
        """Round-trip: format_date(iso) парсится обратно в ту же дату."""
        iso = d.strftime("%Y-%m-%d")
        formatted = format_date(iso)
        # Парсим обратно
        parsed = datetime.strptime(formatted, "%d.%m.%Y").date()
        assert parsed == d, f"Round-trip fail: {iso} → {formatted} → {parsed}"

    @given(d=date_strings_ru)
    @settings(max_examples=200)
    def test_already_formatted_stays_same(self, d):
        """Уже отформатированная дата 'ДД.ММ.ГГГГ' не меняется."""
        result = format_date(d)
        assert result == d, f"'{d}' изменилось на '{result}'"

    @settings(max_examples=50)
    @given(val=st.one_of(st.none(), st.just(""), st.just(0)))
    def test_falsy_values_return_default(self, val):
        """None, '', 0 → значение по умолчанию."""
        result = format_date(val)
        assert result == "—", f"Для {val!r} вернулось '{result}', ожидалось '—'"

    @given(default=st.text(min_size=1, max_size=10))
    @settings(max_examples=200)
    def test_custom_default(self, default):
        """Кастомный default возвращается для None."""
        result = format_date(None, default=default)
        assert result == default


class TestFormatMonthYear:
    """Property-тесты format_month_year."""

    @given(ym=month_strings)
    @settings(max_examples=200)
    def test_valid_month_returns_russian_name(self, ym):
        """Валидный 'ГГГГ-ММ' → 'месяц ГГГГ' на русском."""
        result = format_month_year(ym)
        year, month = ym.split("-")
        expected_month = MONTHS_RU.get(month)
        if expected_month:
            assert result == f"{expected_month} {year}", f"'{ym}' → '{result}', ожидалось '{expected_month} {year}'"

    @given(val=st.one_of(st.none(), st.just(""), st.just("-")))
    @settings(max_examples=50)
    def test_empty_returns_default(self, val):
        """Пустые значения → дефолт."""
        assert format_month_year(val) == "—"


class TestIsWorkingDay:
    """Property-тесты is_working_day."""

    @given(d=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)))
    @settings(max_examples=200)
    def test_returns_bool(self, d):
        """is_working_day всегда возвращает bool."""
        dt = datetime(d.year, d.month, d.day)
        result = is_working_day(dt)
        assert isinstance(result, bool)

    @given(d=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)))
    @settings(max_examples=200)
    def test_weekends_are_not_working(self, d):
        """Суббота и воскресенье — не рабочие дни."""
        assume(d.weekday() in [5, 6])
        dt = datetime(d.year, d.month, d.day)
        assert not is_working_day(dt), f"{d} (weekday={d.weekday()}) считается рабочим"

    @given(d=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)))
    @settings(max_examples=200)
    def test_weekdays_not_holidays_are_working(self, d):
        """Будни без праздников — рабочие дни."""
        from utils.date_utils import RUSSIAN_HOLIDAYS

        assume(d.weekday() < 5)
        assume((d.month, d.day) not in RUSSIAN_HOLIDAYS)
        dt = datetime(d.year, d.month, d.day)
        assert is_working_day(dt), f"{d} — будний непраздничный, но не рабочий"


class TestNetworkdays:
    """Property-тесты networkdays."""

    @given(d=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 6, 30)), delta=st.integers(min_value=0, max_value=365))
    @settings(max_examples=200)
    def test_result_non_negative(self, d, delta):
        """networkdays(start, end) >= 0 при end >= start."""
        start = d.strftime("%Y-%m-%d")
        end = (d + timedelta(days=delta)).strftime("%Y-%m-%d")
        result = networkdays(start, end)
        assert result >= 0, f"Отрицательный networkdays: {start} → {end} = {result}"

    @given(d=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 6, 30)), delta=st.integers(min_value=1, max_value=365))
    @settings(max_examples=200)
    def test_result_le_calendar_days(self, d, delta):
        """Рабочих дней <= календарных дней."""
        start = d.strftime("%Y-%m-%d")
        end = (d + timedelta(days=delta)).strftime("%Y-%m-%d")
        result = networkdays(start, end)
        assert result <= delta, f"Рабочих ({result}) > календарных ({delta})"

    @given(d=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)))
    @settings(max_examples=200)
    def test_same_date_returns_zero(self, d):
        """networkdays(d, d) == 0 (нет дней между одинаковыми датами)."""
        s = d.strftime("%Y-%m-%d")
        assert networkdays(s, s) == 0

    @given(d=st.dates(min_value=date(2020, 6, 1), max_value=date(2030, 6, 30)), delta=st.integers(min_value=1, max_value=180))
    @settings(max_examples=200)
    def test_reversed_dates_return_zero(self, d, delta):
        """networkdays(end, start) == 0 при end < start."""
        end = d.strftime("%Y-%m-%d")
        start = (d + timedelta(days=delta)).strftime("%Y-%m-%d")
        assert networkdays(start, end) == 0


class TestAddWorkingDays:
    """Property-тесты add_working_days."""

    @given(d=st.dates(min_value=date(2020, 1, 1), max_value=date(2029, 12, 31)), wd=st.integers(min_value=1, max_value=250))
    @settings(max_examples=200)
    def test_result_after_start(self, d, wd):
        """Результат add_working_days > start_date."""
        start_str = d.strftime("%Y-%m-%d")
        result = add_working_days(start_str, wd)
        assert result > datetime(d.year, d.month, d.day), f"add_working_days({start_str}, {wd}) = {result} <= {d}"

    @given(d=st.dates(min_value=date(2020, 1, 1), max_value=date(2029, 12, 31)), wd=st.integers(min_value=1, max_value=250))
    @settings(max_examples=200)
    def test_result_is_working_day(self, d, wd):
        """Результат add_working_days — рабочий день."""
        start_str = d.strftime("%Y-%m-%d")
        result = add_working_days(start_str, wd)
        assert is_working_day(result), f"add_working_days({start_str}, {wd}) = {result} (weekday={result.weekday()}) — не рабочий день"

    @given(
        d=st.dates(min_value=date(2020, 1, 1), max_value=date(2029, 12, 31)),
        wd1=st.integers(min_value=1, max_value=100),
        wd2=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=200)
    def test_monotonicity(self, d, wd1, wd2):
        """Больше рабочих дней → позже дата."""
        assume(wd1 < wd2)
        start_str = d.strftime("%Y-%m-%d")
        r1 = add_working_days(start_str, wd1)
        r2 = add_working_days(start_str, wd2)
        assert r2 > r1, f"Не монотонно: +{wd1}→{r1}, +{wd2}→{r2}"
