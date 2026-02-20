# -*- coding: utf-8 -*-
"""
Тесты date_utils — форматирование дат, рабочие дни, дедлайны
"""
import sys
from pathlib import Path
from datetime import datetime

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.date_utils import (
    format_date, format_datetime, format_month_year,
    is_working_day, add_working_days, calculate_deadline,
    MONTHS_RU, RUSSIAN_HOLIDAYS
)


# ============================================================================
# format_date
# ============================================================================

class TestFormatDate:
    def test_iso_format(self):
        assert format_date("2025-01-15") == "15.01.2025"

    def test_iso_with_time(self):
        assert format_date("2025-01-15 14:30:00") == "15.01.2025"

    def test_already_russian_format(self):
        assert format_date("15.01.2025") == "15.01.2025"

    def test_slash_format(self):
        assert format_date("15/01/2025") == "15.01.2025"

    def test_none_returns_default(self):
        assert format_date(None) == "—"

    def test_empty_returns_default(self):
        assert format_date("") == "—"

    def test_custom_default(self):
        assert format_date(None, default="N/A") == "N/A"

    def test_datetime_object(self):
        dt = datetime(2025, 3, 20)
        assert format_date(dt) == "20.03.2025"

    def test_qdate_object(self):
        from PyQt5.QtCore import QDate
        qd = QDate(2025, 6, 15)
        assert format_date(qd) == "15.06.2025"

    def test_qdatetime_object(self):
        from PyQt5.QtCore import QDateTime, QDate, QTime
        qdt = QDateTime(QDate(2025, 12, 31), QTime(23, 59))
        assert format_date(qdt) == "31.12.2025"


# ============================================================================
# format_datetime
# ============================================================================

class TestFormatDatetime:
    def test_iso_with_time(self):
        assert format_datetime("2025-01-15 14:30:00") == "15.01.2025 14:30"

    def test_iso_without_time(self):
        assert format_datetime("2025-01-15") == "15.01.2025"

    def test_none_returns_default(self):
        assert format_datetime(None) == "—"

    def test_datetime_object(self):
        dt = datetime(2025, 3, 20, 10, 30)
        assert format_datetime(dt) == "20.03.2025 10:30"


# ============================================================================
# format_month_year
# ============================================================================

class TestFormatMonthYear:
    def test_january(self):
        assert format_month_year("2025-01") == "январь 2025"

    def test_november(self):
        assert format_month_year("2025-11") == "ноябрь 2025"

    def test_december(self):
        assert format_month_year("2024-12") == "декабрь 2024"

    def test_none_returns_default(self):
        assert format_month_year(None) == "—"

    def test_empty_returns_default(self):
        assert format_month_year("") == "—"

    def test_dash_returns_default(self):
        assert format_month_year("-") == "—"

    def test_all_months_covered(self):
        """Все 12 месяцев в словаре"""
        assert len(MONTHS_RU) == 12
        for i in range(1, 13):
            key = f"{i:02d}"
            assert key in MONTHS_RU


# ============================================================================
# is_working_day
# ============================================================================

class TestIsWorkingDay:
    def test_monday_is_working(self):
        # 2025-01-13 = понедельник
        assert is_working_day(datetime(2025, 1, 13)) is True

    def test_saturday_not_working(self):
        # 2025-01-18 = суббота
        assert is_working_day(datetime(2025, 1, 18)) is False

    def test_sunday_not_working(self):
        # 2025-01-19 = воскресенье
        assert is_working_day(datetime(2025, 1, 19)) is False

    def test_new_year_not_working(self):
        assert is_working_day(datetime(2025, 1, 1)) is False
        assert is_working_day(datetime(2025, 1, 7)) is False

    def test_feb23_not_working(self):
        assert is_working_day(datetime(2025, 2, 23)) is False

    def test_march8_not_working(self):
        assert is_working_day(datetime(2025, 3, 8)) is False

    def test_may9_not_working(self):
        assert is_working_day(datetime(2025, 5, 9)) is False

    def test_june12_not_working(self):
        assert is_working_day(datetime(2025, 6, 12)) is False

    def test_nov4_not_working(self):
        assert is_working_day(datetime(2025, 11, 4)) is False

    def test_regular_wednesday_working(self):
        # 2025-01-15 = среда
        assert is_working_day(datetime(2025, 1, 15)) is True

    def test_all_holidays_defined(self):
        """Все государственные праздники РФ в списке"""
        expected_holidays = [(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8),
                             (2, 23), (3, 8), (5, 1), (5, 9), (6, 12), (11, 4)]
        for h in expected_holidays:
            assert h in RUSSIAN_HOLIDAYS, f"Праздник {h} отсутствует в RUSSIAN_HOLIDAYS"


# ============================================================================
# add_working_days
# ============================================================================

class TestAddWorkingDays:
    def test_add_5_working_days(self):
        """5 рабочих дней от понедельника = следующий понедельник"""
        # 2025-01-13 = понедельник
        result = add_working_days(datetime(2025, 1, 13), 5)
        assert result == datetime(2025, 1, 20)  # следующий понедельник

    def test_add_1_working_day_from_friday(self):
        """1 рабочий день от пятницы = понедельник"""
        # 2025-01-17 = пятница
        result = add_working_days(datetime(2025, 1, 17), 1)
        assert result == datetime(2025, 1, 20)  # понедельник

    def test_string_date_input(self):
        result = add_working_days("2025-01-13", 5)
        assert result == datetime(2025, 1, 20)

    def test_qdate_input(self):
        from PyQt5.QtCore import QDate
        qd = QDate(2025, 1, 13)
        result = add_working_days(qd, 5)
        assert result == datetime(2025, 1, 20)

    def test_skips_holidays(self):
        """Пропускает праздники при добавлении рабочих дней"""
        # 2025-02-21 = пятница, 2025-02-23 = воскресенье + праздник
        # 1 рабочий день от пятницы = понедельник 24-го
        result = add_working_days(datetime(2025, 2, 21), 1)
        assert result == datetime(2025, 2, 24)

    def test_add_zero_days(self):
        """0 рабочих дней = та же дата"""
        result = add_working_days(datetime(2025, 1, 13), 0)
        assert result == datetime(2025, 1, 13)


# ============================================================================
# calculate_deadline
# ============================================================================

class TestCalculateDeadline:
    def test_only_contract_date(self):
        result = calculate_deadline("2025-01-13", None, None, 10)
        assert result is not None
        assert isinstance(result, datetime)

    def test_latest_date_used(self):
        """Берётся самая поздняя из дат"""
        result = calculate_deadline("2025-01-01", "2025-01-10", "2025-01-05", 1)
        # Должна отталкиваться от 10 января (самая поздняя)
        assert result > datetime(2025, 1, 10)

    def test_no_dates_returns_none(self):
        assert calculate_deadline(None, None, None, 10) is None

    def test_no_period_returns_none(self):
        assert calculate_deadline("2025-01-01", None, None, 0) is None
        assert calculate_deadline("2025-01-01", None, None, None) is None

    def test_negative_period_returns_none(self):
        assert calculate_deadline("2025-01-01", None, None, -5) is None
