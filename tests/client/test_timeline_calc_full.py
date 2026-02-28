# -*- coding: utf-8 -*-
"""
Полное покрытие utils/timeline_calc.py — calc_planned_dates.
~12 тестов.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.timeline_calc import calc_planned_dates


class TestCalcPlannedDates:
    """calc_planned_dates — расчёт плановых дат."""

    def test_empty_entries(self):
        result = calc_planned_dates([])
        assert result == []

    def test_start_entry_sets_planned(self):
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02', 'executor_role': 'manager'},
        ]
        result = calc_planned_dates(entries)
        assert result[0]['_planned_date'] == '2026-03-02'

    def test_header_skipped(self):
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02', 'executor_role': 'manager'},
            {'executor_role': 'header', 'stage_code': 'HDR'},
        ]
        result = calc_planned_dates(entries)
        assert '_planned_date' not in result[1]

    def test_norm_days_adds_working_days(self):
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02', 'executor_role': 'manager'},
            {'stage_code': 'DESIGN', 'norm_days': 5, 'actual_date': '', 'executor_role': 'designer'},
        ]
        result = calc_planned_dates(entries)
        assert result[1]['_planned_date'] != ''
        assert result[1]['_planned_date'] >= '2026-03-02'

    def test_zero_norm_inherits_prev_date(self):
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02', 'executor_role': 'manager'},
            {'stage_code': 'ZERO', 'norm_days': 0, 'actual_date': '', 'executor_role': 'designer'},
        ]
        result = calc_planned_dates(entries)
        assert result[1]['_planned_date'] == '2026-03-02'

    def test_custom_norm_overrides(self):
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02', 'executor_role': 'manager'},
            {'stage_code': 'S1', 'norm_days': 5, 'custom_norm_days': 10, 'actual_date': '', 'executor_role': 'x'},
        ]
        result = calc_planned_dates(entries)
        # custom_norm_days=10 should give later date than norm_days=5
        planned = result[1]['_planned_date']
        assert planned != ''

    def test_actual_date_updates_prev(self):
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02', 'executor_role': 'manager'},
            {'stage_code': 'S1', 'norm_days': 5, 'actual_date': '2026-03-20', 'executor_role': 'x'},
            {'stage_code': 'S2', 'norm_days': 3, 'actual_date': '', 'executor_role': 'x'},
        ]
        result = calc_planned_dates(entries)
        # S2 should be based on S1 actual_date (2026-03-20), not planned
        assert result[2]['_planned_date'] >= '2026-03-20'

    def test_no_start_no_prev_date(self):
        entries = [
            {'stage_code': 'S1', 'norm_days': 5, 'actual_date': '', 'executor_role': 'x'},
        ]
        result = calc_planned_dates(entries)
        assert result[0]['_planned_date'] == ''

    def test_none_norm_treated_as_zero(self):
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02', 'executor_role': 'manager'},
            {'stage_code': 'S1', 'norm_days': None, 'actual_date': '', 'executor_role': 'x'},
        ]
        result = calc_planned_dates(entries)
        assert result[1]['_planned_date'] == '2026-03-02'

    def test_multiple_stages_chain(self):
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02', 'executor_role': 'manager'},
            {'stage_code': 'S1', 'norm_days': 1, 'actual_date': '', 'executor_role': 'x'},
            {'stage_code': 'S2', 'norm_days': 1, 'actual_date': '', 'executor_role': 'x'},
            {'stage_code': 'S3', 'norm_days': 1, 'actual_date': '', 'executor_role': 'x'},
        ]
        result = calc_planned_dates(entries)
        # Each stage should be later than previous
        dates = [e['_planned_date'] for e in result if e.get('_planned_date')]
        for i in range(1, len(dates)):
            assert dates[i] >= dates[i-1]

    def test_start_without_actual_date(self):
        entries = [
            {'stage_code': 'START', 'actual_date': '', 'executor_role': 'manager'},
            {'stage_code': 'S1', 'norm_days': 5, 'actual_date': '', 'executor_role': 'x'},
        ]
        result = calc_planned_dates(entries)
        # No START actual_date means prev_date is empty
        assert result[0]['_planned_date'] == ''
        assert result[1]['_planned_date'] == ''

    def test_custom_norm_zero_not_used(self):
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-03-02', 'executor_role': 'manager'},
            {'stage_code': 'S1', 'norm_days': 5, 'custom_norm_days': 0, 'actual_date': '', 'executor_role': 'x'},
        ]
        result = calc_planned_dates(entries)
        # custom_norm_days=0 should NOT override norm_days=5
        assert result[1]['_planned_date'] != '2026-03-02'
