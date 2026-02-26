# -*- coding: utf-8 -*-
"""
Полное покрытие utils/date_utils.py — 137 statements.
Тесты: format_date, format_datetime, format_month_year, is_working_day,
       add_working_days, calculate_deadline.
~50 тестов.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ========== Мок QDate/QDateTime для тестов без Qt ==========

class MockQDate:
    """Мок QDate для тестов без PyQt5."""
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


# Патчим PyQt5.QtCore.QDate и QDateTime ДО импорта модуля
@pytest.fixture(autouse=True)
def _patch_qt():
    """Патч PyQt5 для тестов без Qt runtime."""
    with patch.dict('sys.modules', {
        'PyQt5': MagicMock(),
        'PyQt5.QtCore': MagicMock(QDate=MockQDate, QDateTime=MockQDateTime),
    }):
        # Переимпортируем модуль с замоканным Qt
        if 'utils.date_utils' in sys.modules:
            del sys.modules['utils.date_utils']
        yield


def _import():
    """Импорт date_utils после патча Qt."""
    from utils import date_utils
    # Инжектируем реальные классы для isinstance проверок
    date_utils.QDate = MockQDate
    date_utils.QDateTime = MockQDateTime
    return date_utils


# ========== format_date (15 тестов) ==========

class TestFormatDate:
    """format_date — форматирование дат."""

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

    def test_already_formatted(self):
        du = _import()
        assert du.format_date('15.03.2026') == '15.03.2026'

    def test_slash_format(self):
        du = _import()
        assert du.format_date('15/03/2026') == '15.03.2026'

    def test_slash_iso_format(self):
        du = _import()
        assert du.format_date('2026/03/15') == '15.03.2026'

    def test_datetime_object(self):
        du = _import()
        dt = datetime(2026, 6, 15, 10, 30)
        assert du.format_date(dt) == '15.06.2026'

    def test_qdate_object(self):
        du = _import()
        qd = MockQDate(2026, 6, 15)
        assert du.format_date(qd) == '15.06.2026'

    def test_qdatetime_object(self):
        du = _import()
        qdt = MockQDateTime(2026, 12, 31, 23, 59)
        assert du.format_date(qdt) == '31.12.2026'

    def test_long_string_truncated(self):
        du = _import()
        result = du.format_date('2026-03-15T10:30:00Z')
        assert '15.03.2026' in result

    def test_invalid_string_returns_as_is(self):
        du = _import()
        result = du.format_date('abc')
        assert result == 'abc'

    def test_whitespace_stripped(self):
        du = _import()
        assert du.format_date('  2026-03-15  ') == '15.03.2026'

    def test_false_value_returns_default(self):
        du = _import()
        assert du.format_date(0) == '—'


# ========== format_datetime (10 тестов) ==========

class TestFormatDatetime:
    """format_datetime — форматирование дат с временем."""

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

    def test_iso_date_only(self):
        du = _import()
        assert du.format_datetime('2026-03-15') == '15.03.2026'

    def test_datetime_object(self):
        du = _import()
        dt = datetime(2026, 6, 15, 10, 30)
        assert du.format_datetime(dt) == '15.06.2026 10:30'

    def test_qdatetime_object(self):
        du = _import()
        qdt = MockQDateTime(2026, 12, 31, 23, 59)
        assert du.format_datetime(qdt) == '31.12.2026 23:59'

    def test_invalid_string(self):
        du = _import()
        result = du.format_datetime('not-a-date')
        assert result == 'not-a-date'

    def test_custom_default(self):
        du = _import()
        assert du.format_datetime(None, default='N/A') == 'N/A'

    def test_whitespace_only(self):
        du = _import()
        assert du.format_datetime('   ') == '—'


# ========== format_month_year (8 тестов) ==========

class TestFormatMonthYear:
    """format_month_year — месяц прописью."""

    def test_none_returns_default(self):
        du = _import()
        assert du.format_month_year(None) == '—'

    def test_empty_string(self):
        du = _import()
        assert du.format_month_year('') == '—'

    def test_january(self):
        du = _import()
        assert du.format_month_year('2024-01') == 'январь 2024'

    def test_november(self):
        du = _import()
        assert du.format_month_year('2025-11') == 'ноябрь 2025'

    def test_december(self):
        du = _import()
        assert du.format_month_year('2026-12') == 'декабрь 2026'

    def test_dash_only(self):
        du = _import()
        assert du.format_month_year('-') == '—'

    def test_invalid_format(self):
        du = _import()
        result = du.format_month_year('March 2025')
        assert result == 'March 2025'

    def test_custom_default(self):
        du = _import()
        assert du.format_month_year(None, default='???') == '???'


# ========== is_working_day (7 тестов) ==========

class TestIsWorkingDay:
    """is_working_day — проверка рабочих дней."""

    def test_monday_is_working(self):
        du = _import()
        # 2026-03-02 is Monday
        assert du.is_working_day(datetime(2026, 3, 2)) is True

    def test_friday_is_working(self):
        du = _import()
        assert du.is_working_day(datetime(2026, 3, 6)) is True

    def test_saturday_not_working(self):
        du = _import()
        # 2026-02-28 is Saturday
        assert du.is_working_day(datetime(2026, 2, 28)) is False

    def test_sunday_not_working(self):
        du = _import()
        assert du.is_working_day(datetime(2026, 3, 1)) is False

    def test_new_year_holiday(self):
        du = _import()
        assert du.is_working_day(datetime(2026, 1, 1)) is False

    def test_feb_23_holiday(self):
        du = _import()
        assert du.is_working_day(datetime(2026, 2, 23)) is False

    def test_may_9_holiday(self):
        du = _import()
        assert du.is_working_day(datetime(2026, 5, 9)) is False


# ========== add_working_days (6 тестов) ==========

class TestAddWorkingDays:
    """add_working_days — добавление рабочих дней."""

    def test_string_input(self):
        du = _import()
        result = du.add_working_days('2026-03-02', 5)  # Mon + 5 = next Mon
        assert isinstance(result, datetime)
        assert result.weekday() < 5  # рабочий день

    def test_datetime_input(self):
        du = _import()
        dt = datetime(2026, 3, 2)  # Monday
        result = du.add_working_days(dt, 1)
        assert result == datetime(2026, 3, 3)  # Tuesday

    def test_qdate_input(self):
        du = _import()
        qd = MockQDate(2026, 3, 2)
        result = du.add_working_days(qd, 1)
        assert isinstance(result, datetime)

    def test_skips_weekend(self):
        du = _import()
        # 2026-03-06 is Friday, +1 = Monday 2026-03-09
        result = du.add_working_days('2026-03-06', 1)
        assert result == datetime(2026, 3, 9)

    def test_invalid_type_raises(self):
        du = _import()
        with pytest.raises(ValueError, match="Неподдерживаемый тип"):
            du.add_working_days(12345, 5)

    def test_zero_days(self):
        du = _import()
        dt = datetime(2026, 3, 2)
        result = du.add_working_days(dt, 0)
        assert result == dt


# ========== calculate_deadline (8 тестов) ==========

class TestCalculateDeadline:
    """calculate_deadline — расчёт дедлайна."""

    def test_contract_date_only(self):
        du = _import()
        result = du.calculate_deadline('2026-03-02', None, None, 10)
        assert isinstance(result, datetime)

    def test_all_dates_picks_latest(self):
        du = _import()
        result = du.calculate_deadline(
            '2026-01-01', '2026-03-01', '2026-02-01', 5
        )
        # Максимальная дата = 2026-03-01
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

    def test_qdate_inputs(self):
        du = _import()
        result = du.calculate_deadline(
            MockQDate(2026, 3, 2), MockQDate(2026, 3, 5), None, 5
        )
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
