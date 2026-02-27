# -*- coding: utf-8 -*-
"""
Полное покрытие utils/date_utils.py — 137 строк, покрытие 7% -> 90%+
Тесты: format_date, format_datetime, format_month_year, is_working_day,
       add_working_days, calculate_deadline, MONTHS_RU, RUSSIAN_HOLIDAYS.
~55 тестов.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ========== Мок QDate/QDateTime для тестов без Qt ==========

class MockQDate:
    """Мок QDate."""
    def __init__(self, y, m, d):
        self._y, self._m, self._d = y, m, d
    def year(self): return self._y
    def month(self): return self._m
    def day(self): return self._d
    def toString(self, fmt):
        if fmt == 'dd.MM.yyyy':
            return f'{self._d:02d}.{self._m:02d}.{self._y}'
        return ''


class MockQDateTime:
    """Мок QDateTime."""
    def __init__(self, y, m, d, h=0, mi=0):
        self._date = MockQDate(y, m, d)
        self._h, self._mi = h, mi
    def date(self): return self._date
    def toString(self, fmt):
        if fmt == 'dd.MM.yyyy HH:mm':
            return f'{self._date._d:02d}.{self._date._m:02d}.{self._date._y} {self._h:02d}:{self._mi:02d}'
        return ''


@pytest.fixture(autouse=True)
def _patch_qt():
    """Патч PyQt5 для тестов без Qt runtime."""
    with patch.dict('sys.modules', {
        'PyQt5': MagicMock(),
        'PyQt5.QtCore': MagicMock(QDate=MockQDate, QDateTime=MockQDateTime),
    }):
        if 'utils.date_utils' in sys.modules:
            del sys.modules['utils.date_utils']
        yield


def _import():
    """Импорт date_utils после патча Qt."""
    from utils import date_utils
    date_utils.QDate = MockQDate
    date_utils.QDateTime = MockQDateTime
    return date_utils


# ========== format_date (18 тестов) ==========

class TestFormatDate:
    """format_date — форматирование дат в ДД.ММ.ГГГГ."""

    def test_none_returns_default(self):
        du = _import()
        assert du.format_date(None) == '—'

    def test_empty_string_returns_default(self):
        du = _import()
        assert du.format_date('') == '—'

    def test_custom_default(self):
        du = _import()
        assert du.format_date(None, default='N/A') == 'N/A'

    def test_iso_format(self):
        du = _import()
        assert du.format_date('2026-03-15') == '15.03.2026'

    def test_iso_with_time(self):
        du = _import()
        assert du.format_date('2026-01-20 14:30:00') == '20.01.2026'

    def test_already_formatted_dd_mm_yyyy(self):
        du = _import()
        assert du.format_date('15.03.2026') == '15.03.2026'

    def test_slash_dd_mm_yyyy(self):
        du = _import()
        assert du.format_date('15/03/2026') == '15.03.2026'

    def test_slash_yyyy_mm_dd(self):
        du = _import()
        assert du.format_date('2026/03/15') == '15.03.2026'

    def test_datetime_object(self):
        du = _import()
        assert du.format_date(datetime(2026, 6, 15, 10, 30)) == '15.06.2026'

    def test_qdate_object(self):
        du = _import()
        assert du.format_date(MockQDate(2026, 6, 15)) == '15.06.2026'

    def test_qdatetime_object(self):
        du = _import()
        assert du.format_date(MockQDateTime(2026, 12, 31, 23, 59)) == '31.12.2026'

    def test_long_iso_string_truncated(self):
        du = _import()
        result = du.format_date('2026-03-15T10:30:00Z')
        assert '15.03.2026' in result

    def test_invalid_string_returned_as_is(self):
        du = _import()
        result = du.format_date('abc')
        assert result == 'abc'

    def test_whitespace_stripped(self):
        du = _import()
        assert du.format_date('  2026-03-15  ') == '15.03.2026'

    def test_falsy_value_zero_returns_default(self):
        du = _import()
        assert du.format_date(0) == '—'

    def test_first_of_year(self):
        du = _import()
        assert du.format_date('2026-01-01') == '01.01.2026'

    def test_last_of_year(self):
        du = _import()
        assert du.format_date('2026-12-31') == '31.12.2026'

    def test_leap_day(self):
        du = _import()
        assert du.format_date('2024-02-29') == '29.02.2024'


# ========== format_datetime (12 тестов) ==========

class TestFormatDatetime:
    """format_datetime — форматирование даты-времени."""

    def test_none_returns_default(self):
        du = _import()
        assert du.format_datetime(None) == '—'

    def test_empty_string_returns_default(self):
        du = _import()
        assert du.format_datetime('') == '—'

    def test_iso_with_seconds(self):
        du = _import()
        assert du.format_datetime('2026-03-15 14:30:00') == '15.03.2026 14:30'

    def test_iso_with_minutes(self):
        du = _import()
        assert du.format_datetime('2026-03-15 14:30') == '15.03.2026 14:30'

    def test_iso_date_only_no_time(self):
        du = _import()
        assert du.format_datetime('2026-03-15') == '15.03.2026'

    def test_datetime_object_with_time(self):
        du = _import()
        assert du.format_datetime(datetime(2026, 6, 15, 10, 30)) == '15.06.2026 10:30'

    def test_datetime_object_midnight(self):
        du = _import()
        assert du.format_datetime(datetime(2026, 1, 1, 0, 0)) == '01.01.2026 00:00'

    def test_qdatetime_object(self):
        du = _import()
        assert du.format_datetime(MockQDateTime(2026, 12, 31, 23, 59)) == '31.12.2026 23:59'

    def test_invalid_string_returned_as_is(self):
        du = _import()
        assert du.format_datetime('not-a-date') == 'not-a-date'

    def test_custom_default(self):
        du = _import()
        assert du.format_datetime(None, default='N/A') == 'N/A'

    def test_whitespace_only_returns_default(self):
        du = _import()
        assert du.format_datetime('   ') == '—'

    def test_false_value_returns_default(self):
        du = _import()
        assert du.format_datetime(0) == '—'


# ========== format_month_year (10 тестов) ==========

class TestFormatMonthYear:
    """format_month_year — месяц прописью."""

    def test_none_returns_default(self):
        du = _import()
        assert du.format_month_year(None) == '—'

    def test_empty_string_returns_default(self):
        du = _import()
        assert du.format_month_year('') == '—'

    def test_dash_returns_default(self):
        du = _import()
        assert du.format_month_year('-') == '—'

    def test_all_12_months(self):
        du = _import()
        expected = [
            ('2026-01', 'январь 2026'), ('2026-02', 'февраль 2026'),
            ('2026-03', 'март 2026'), ('2026-04', 'апрель 2026'),
            ('2026-05', 'май 2026'), ('2026-06', 'июнь 2026'),
            ('2026-07', 'июль 2026'), ('2026-08', 'август 2026'),
            ('2026-09', 'сентябрь 2026'), ('2026-10', 'октябрь 2026'),
            ('2026-11', 'ноябрь 2026'), ('2026-12', 'декабрь 2026'),
        ]
        for input_val, expected_val in expected:
            assert du.format_month_year(input_val) == expected_val

    def test_invalid_format_returned_as_is(self):
        du = _import()
        assert du.format_month_year('March 2025') == 'March 2025'

    def test_custom_default(self):
        du = _import()
        assert du.format_month_year(None, default='???') == '???'

    def test_integer_input_converted(self):
        du = _import()
        # Передаём число, str(202601) не в формате ГГГГ-ММ
        result = du.format_month_year(202601)
        # Должен вернуть строковое представление
        assert isinstance(result, str)

    def test_months_ru_has_12_entries(self):
        du = _import()
        assert len(du.MONTHS_RU) == 12

    def test_wrong_length_string(self):
        du = _import()
        # "2026-1" — 6 символов, не 7
        result = du.format_month_year('2026-1')
        assert result == '2026-1'

    def test_invalid_month_13(self):
        du = _import()
        result = du.format_month_year('2026-13')
        assert result == '2026-13'


# ========== is_working_day (10 тестов) ==========

class TestIsWorkingDay:
    """is_working_day — проверка рабочих дней."""

    def test_monday_is_working(self):
        du = _import()
        assert du.is_working_day(datetime(2026, 3, 2)) is True

    def test_tuesday_is_working(self):
        du = _import()
        assert du.is_working_day(datetime(2026, 3, 3)) is True

    def test_friday_is_working(self):
        du = _import()
        assert du.is_working_day(datetime(2026, 3, 6)) is True

    def test_saturday_not_working(self):
        du = _import()
        assert du.is_working_day(datetime(2026, 2, 28)) is False

    def test_sunday_not_working(self):
        du = _import()
        assert du.is_working_day(datetime(2026, 3, 1)) is False

    def test_new_year_holidays(self):
        du = _import()
        for day in range(1, 9):
            assert du.is_working_day(datetime(2026, 1, day)) is False

    def test_feb_23_holiday(self):
        du = _import()
        assert du.is_working_day(datetime(2026, 2, 23)) is False

    def test_march_8_holiday(self):
        du = _import()
        assert du.is_working_day(datetime(2026, 3, 8)) is False

    def test_may_1_and_9_holidays(self):
        du = _import()
        assert du.is_working_day(datetime(2026, 5, 1)) is False
        assert du.is_working_day(datetime(2026, 5, 9)) is False

    def test_regular_workday_in_july(self):
        du = _import()
        # 2026-07-01 = среда
        assert du.is_working_day(datetime(2026, 7, 1)) is True


# ========== add_working_days (8 тестов) ==========

class TestAddWorkingDays:
    """add_working_days — добавление рабочих дней к дате."""

    def test_string_input(self):
        du = _import()
        result = du.add_working_days('2026-03-02', 5)
        assert isinstance(result, datetime)
        assert result.weekday() < 5

    def test_datetime_input_1_day(self):
        du = _import()
        result = du.add_working_days(datetime(2026, 3, 2), 1)  # Пн + 1 = Вт
        assert result == datetime(2026, 3, 3)

    def test_qdate_input(self):
        du = _import()
        result = du.add_working_days(MockQDate(2026, 3, 2), 1)
        assert isinstance(result, datetime)

    def test_skips_weekend(self):
        du = _import()
        result = du.add_working_days(datetime(2026, 3, 6), 1)  # Пт + 1 = Пн
        assert result == datetime(2026, 3, 9)

    def test_skips_holiday(self):
        du = _import()
        # 2026-02-20 Пт + 1 = Пн 2026-02-23 (праздник) -> Вт 2026-02-24
        result = du.add_working_days(datetime(2026, 2, 20), 1)
        assert result == datetime(2026, 2, 24)

    def test_zero_days_returns_same(self):
        du = _import()
        dt = datetime(2026, 3, 2)
        assert du.add_working_days(dt, 0) == dt

    def test_invalid_type_raises(self):
        du = _import()
        with pytest.raises(ValueError, match="Неподдерживаемый тип"):
            du.add_working_days(12345, 5)

    def test_ten_working_days(self):
        du = _import()
        result = du.add_working_days(datetime(2026, 3, 2), 10)  # 2 недели
        assert result == datetime(2026, 3, 16)


# ========== calculate_deadline (10 тестов) ==========

class TestCalculateDeadline:
    """calculate_deadline — расчёт дедлайна проекта."""

    def test_contract_date_only(self):
        du = _import()
        result = du.calculate_deadline('2026-03-02', None, None, 10)
        assert isinstance(result, datetime)

    def test_all_dates_picks_latest(self):
        du = _import()
        result = du.calculate_deadline('2026-01-01', '2026-03-01', '2026-02-01', 5)
        assert result > datetime(2026, 3, 1)

    def test_no_dates_returns_none(self):
        du = _import()
        assert du.calculate_deadline(None, None, None, 10) is None

    def test_zero_period_returns_none(self):
        du = _import()
        assert du.calculate_deadline('2026-03-02', None, None, 0) is None

    def test_negative_period_returns_none(self):
        du = _import()
        assert du.calculate_deadline('2026-03-02', None, None, -5) is None

    def test_none_period_returns_none(self):
        du = _import()
        assert du.calculate_deadline('2026-03-02', None, None, None) is None

    def test_qdate_inputs(self):
        du = _import()
        result = du.calculate_deadline(MockQDate(2026, 3, 2), MockQDate(2026, 3, 5), None, 5)
        assert isinstance(result, datetime)

    def test_datetime_inputs(self):
        du = _import()
        result = du.calculate_deadline(
            datetime(2026, 3, 2), datetime(2026, 3, 5), datetime(2026, 3, 10), 10
        )
        assert result > datetime(2026, 3, 10)

    def test_invalid_date_string_ignored(self):
        du = _import()
        result = du.calculate_deadline('not-a-date', None, None, 10)
        assert result is None

    def test_mixed_types(self):
        du = _import()
        result = du.calculate_deadline(
            '2026-03-02', MockQDate(2026, 3, 5), datetime(2026, 3, 10), 1
        )
        assert isinstance(result, datetime)
        assert result > datetime(2026, 3, 10)


# ========== RUSSIAN_HOLIDAYS ==========

class TestRussianHolidays:
    """RUSSIAN_HOLIDAYS — полнота списка праздников."""

    def test_all_holidays_present(self):
        du = _import()
        expected = [(1,1),(1,2),(1,3),(1,4),(1,5),(1,6),(1,7),(1,8),
                    (2,23),(3,8),(5,1),(5,9),(6,12),(11,4)]
        for h in expected:
            assert h in du.RUSSIAN_HOLIDAYS, f"Праздник {h} отсутствует"

    def test_holidays_count(self):
        du = _import()
        assert len(du.RUSSIAN_HOLIDAYS) == 14
