# -*- coding: utf-8 -*-
"""
Полное покрытие utils/calendar_helpers.py — 118 строк, покрытие 25% -> 80%+
Тесты: add_working_days (строковая версия), working_days_between.
~25 тестов (только чистые функции, без Qt виджетов).
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.calendar_helpers import add_working_days, working_days_between


# ==================== add_working_days (15 тестов) ====================

class TestAddWorkingDays:
    """add_working_days из calendar_helpers — строковый вход/выход 'YYYY-MM-DD'."""

    def test_basic_add_1_day(self):
        # 2026-03-02 (пн) + 1 = 2026-03-03 (вт)
        assert add_working_days('2026-03-02', 1) == '2026-03-03'

    def test_skip_weekend_fri_to_mon(self):
        # 2026-03-06 (пт) + 1 = 2026-03-09 (пн)
        assert add_working_days('2026-03-06', 1) == '2026-03-09'

    def test_five_days_mon_to_mon(self):
        # 2026-03-02 (пн) + 5 = 2026-03-09 (пн)
        assert add_working_days('2026-03-02', 5) == '2026-03-09'

    def test_ten_days_two_weeks(self):
        # 2026-03-02 (пн) + 10 = 2026-03-16 (пн)
        assert add_working_days('2026-03-02', 10) == '2026-03-16'

    def test_empty_start_returns_empty(self):
        assert add_working_days('', 5) == ''

    def test_none_start_returns_empty(self):
        assert add_working_days(None, 5) == ''

    def test_zero_days_returns_same(self):
        assert add_working_days('2026-03-02', 0) == '2026-03-02'

    def test_negative_days_returns_same(self):
        assert add_working_days('2026-03-02', -1) == '2026-03-02'

    def test_invalid_date_returns_as_is(self):
        assert add_working_days('not-a-date', 5) == 'not-a-date'

    def test_result_format_is_yyyy_mm_dd(self):
        result = add_working_days('2026-03-02', 1)
        parts = result.split('-')
        assert len(parts) == 3
        assert len(parts[0]) == 4
        assert len(parts[1]) == 2
        assert len(parts[2]) == 2

    def test_skips_russian_holidays(self):
        # 2026-02-20 (пт) + 1 рабочий день:
        # 21 = сб, 22 = вс, 23 = праздник (23 февраля, пн)
        # -> 24 (вт)
        assert add_working_days('2026-02-20', 1) == '2026-02-24'

    def test_cross_month_boundary(self):
        # 2026-03-31 (вт) + 1 = 2026-04-01 (ср)
        assert add_working_days('2026-03-31', 1) == '2026-04-01'

    def test_cross_year_boundary(self):
        # 2025-12-31 (ср) + 1 рабочий день:
        # 1-8 января — праздники, 9 = пт
        assert add_working_days('2025-12-31', 1) == '2026-01-09'

    def test_add_from_saturday(self):
        # 2026-03-07 (сб) + 1 = 2026-03-09 (пн)
        assert add_working_days('2026-03-07', 1) == '2026-03-09'

    def test_add_from_sunday(self):
        # 2026-03-08 (вс, и праздник) + 1 = 2026-03-09 (пн)
        assert add_working_days('2026-03-08', 1) == '2026-03-09'


# ==================== working_days_between (12 тестов) ====================

class TestWorkingDaysBetween:
    """working_days_between — подсчёт рабочих дней (Пн-Пт) между двумя датами."""

    def test_same_day_zero(self):
        assert working_days_between('2026-03-02', '2026-03-02') == 0

    def test_one_working_day_mon_to_tue(self):
        assert working_days_between('2026-03-02', '2026-03-03') == 1

    def test_five_working_days_mon_to_mon(self):
        assert working_days_between('2026-03-02', '2026-03-09') == 5

    def test_ten_working_days(self):
        assert working_days_between('2026-03-02', '2026-03-16') == 10

    def test_reverse_dates_returns_zero(self):
        assert working_days_between('2026-03-09', '2026-03-02') == 0

    def test_empty_start_returns_zero(self):
        assert working_days_between('', '2026-03-09') == 0

    def test_empty_end_returns_zero(self):
        assert working_days_between('2026-03-02', '') == 0

    def test_none_start_returns_zero(self):
        assert working_days_between(None, '2026-03-09') == 0

    def test_none_end_returns_zero(self):
        assert working_days_between('2026-03-02', None) == 0

    def test_invalid_date_returns_zero(self):
        assert working_days_between('not-a-date', '2026-03-09') == 0

    def test_weekend_not_counted(self):
        # Пт -> след Пн = 1 рабочий день (пн)
        assert working_days_between('2026-03-06', '2026-03-09') == 1

    def test_cross_month_boundary(self):
        # 2026-03-30 (пн) -> 2026-04-03 (пт) = 4 рабочих дня
        result = working_days_between('2026-03-30', '2026-04-03')
        assert result == 4
