# -*- coding: utf-8 -*-
"""
Покрытие utils/calendar_helpers.py — функции add_working_days, working_days_between.
~15 тестов (функциональная часть, без Qt виджетов).
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Импортируем только чистые функции (не виджеты)
from utils.calendar_helpers import add_working_days, working_days_between


# ========== add_working_days (8 тестов) ==========

class TestAddWorkingDays:
    """add_working_days из calendar_helpers — строковый вход/выход."""

    def test_basic_add(self):
        # 2026-03-02 (пн) + 1 = 2026-03-03 (вт)
        result = add_working_days('2026-03-02', 1)
        assert result == '2026-03-03'

    def test_skip_weekend(self):
        # 2026-03-06 (пт) + 1 = 2026-03-09 (пн)
        result = add_working_days('2026-03-06', 1)
        assert result == '2026-03-09'

    def test_five_days(self):
        # 2026-03-02 (пн) + 5 = 2026-03-09 (пн)
        result = add_working_days('2026-03-02', 5)
        assert result == '2026-03-09'

    def test_empty_start_returns_empty(self):
        result = add_working_days('', 5)
        assert result == ''

    def test_none_start_returns_empty(self):
        result = add_working_days(None, 5)
        assert result == ''

    def test_zero_days_returns_same(self):
        result = add_working_days('2026-03-02', 0)
        assert result == '2026-03-02'

    def test_negative_days_returns_same(self):
        result = add_working_days('2026-03-02', -1)
        assert result == '2026-03-02'

    def test_invalid_date_returns_as_is(self):
        result = add_working_days('not-a-date', 5)
        assert result == 'not-a-date'


# ========== working_days_between (7 тестов) ==========

class TestWorkingDaysBetween:
    """working_days_between — подсчёт рабочих дней."""

    def test_same_day(self):
        assert working_days_between('2026-03-02', '2026-03-02') == 0

    def test_one_working_day(self):
        # пн -> вт
        assert working_days_between('2026-03-02', '2026-03-03') == 1

    def test_five_working_days(self):
        # пн -> пн (через выходные)
        assert working_days_between('2026-03-02', '2026-03-09') == 5

    def test_reverse_dates_returns_zero(self):
        assert working_days_between('2026-03-09', '2026-03-02') == 0

    def test_empty_start_returns_zero(self):
        assert working_days_between('', '2026-03-09') == 0

    def test_empty_end_returns_zero(self):
        assert working_days_between('2026-03-02', '') == 0

    def test_invalid_date_returns_zero(self):
        assert working_days_between('not-a-date', '2026-03-09') == 0
