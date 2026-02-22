# -*- coding: utf-8 -*-
"""
Тесты каскадного расчёта планируемых дат (Phase 5).
Проверяем логику _calc_planned_dates() из timeline_widget.py.
"""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.calendar_helpers import add_working_days


def calc_planned_dates(entries):
    """Копия логики _calc_planned_dates() из timeline_widget.py
    для тестирования без создания QWidget."""
    prev_date = ''
    for entry in entries:
        role = entry.get('executor_role', '')
        if role == 'header':
            continue
        stage_code = entry.get('stage_code', '')
        if stage_code == 'START':
            prev_date = entry.get('actual_date', '')
            entry['_planned_date'] = prev_date
            continue
        norm = entry.get('norm_days', 0) or 0
        actual = entry.get('actual_date', '')
        if prev_date and norm > 0:
            entry['_planned_date'] = add_working_days(prev_date, norm)
        else:
            entry['_planned_date'] = ''
        if actual:
            prev_date = actual
        elif entry.get('_planned_date'):
            prev_date = entry['_planned_date']
    return entries


# ============================================================================
# Базовая цепочка
# ============================================================================

class TestCalcPlannedDatesBasic:
    """Базовые тесты расчёта planned_date"""

    def test_simple_chain_3_entries(self):
        """Цепочка из 3 подэтапов: START → A(5д) → B(10д) → C(3д)"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-01-05', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '', 'executor_role': 'designer'},
            {'stage_code': 'B', 'norm_days': 10, 'actual_date': '', 'executor_role': 'designer'},
            {'stage_code': 'C', 'norm_days': 3, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        # START = 2026-01-05 (понедельник)
        assert entries[0]['_planned_date'] == '2026-01-05'
        # A = START + 5 рабочих дней = 2026-01-12 (понедельник)
        assert entries[1]['_planned_date'] == '2026-01-12'
        # B = A_planned + 10 рабочих дней = 2026-01-26 (понедельник)
        assert entries[2]['_planned_date'] == '2026-01-26'
        # C = B_planned + 3 рабочих дня = 2026-01-29 (четверг)
        assert entries[3]['_planned_date'] == '2026-01-29'

    def test_headers_skipped(self):
        """Header-строки пропускаются, не влияют на цепочку"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-01-05', 'executor_role': ''},
            {'stage_code': 'STAGE1', 'executor_role': 'header', 'norm_days': 0, 'actual_date': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        assert entries[2]['_planned_date'] == '2026-01-12'

    def test_no_start_date_empty_chain(self):
        """Без START.actual_date — вся цепочка пустая"""
        entries = [
            {'stage_code': 'START', 'actual_date': '', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        assert entries[0]['_planned_date'] == ''
        assert entries[1]['_planned_date'] == ''

    def test_zero_norm_days_empty_planned(self):
        """norm_days=0 → planned_date пустая"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-01-05', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 0, 'actual_date': '', 'executor_role': 'designer'},
            {'stage_code': 'B', 'norm_days': 5, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        assert entries[1]['_planned_date'] == ''
        # B считается от START (prev_date не обновился из-за пустого planned)
        assert entries[2]['_planned_date'] == '2026-01-12'


# ============================================================================
# Каскадный пересчёт (actual_date влияет на цепочку)
# ============================================================================

class TestCalcPlannedDatesCascade:
    """Тесты каскадного пересчёта при наличии actual_date"""

    def test_actual_date_overrides_prev(self):
        """actual_date подэтапа A становится базой для B"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-01-05', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '2026-01-15', 'executor_role': 'designer'},
            {'stage_code': 'B', 'norm_days': 3, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        # A planned = START + 5 = 2026-01-12, но actual = 2026-01-15
        assert entries[1]['_planned_date'] == '2026-01-12'
        # B planned = actual_A + 3 = 2026-01-15 + 3 рабочих дня = 2026-01-20
        assert entries[2]['_planned_date'] == '2026-01-20'

    def test_cascade_after_manual_edit(self):
        """Симуляция ручного редактирования: A сдвинулся → B, C пересчитываются"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-01-05', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '2026-02-02', 'executor_role': 'designer'},
            {'stage_code': 'B', 'norm_days': 10, 'actual_date': '', 'executor_role': 'designer'},
            {'stage_code': 'C', 'norm_days': 3, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        # A planned = START + 5 = 2026-01-12
        assert entries[1]['_planned_date'] == '2026-01-12'
        # B planned = actual_A(02-02) + 10 рабочих дней = 2026-02-16
        assert entries[2]['_planned_date'] == '2026-02-16'
        # C planned = B_planned(02-16) + 3 рабочих дня = 2026-02-19
        assert entries[3]['_planned_date'] == '2026-02-19'

    def test_middle_actual_date_cascades(self):
        """actual_date в середине цепочки: A и C пустые, B заполнен"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-01-05', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '', 'executor_role': 'designer'},
            {'stage_code': 'B', 'norm_days': 10, 'actual_date': '2026-01-20', 'executor_role': 'designer'},
            {'stage_code': 'C', 'norm_days': 3, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        # A planned = START + 5 = 2026-01-12
        assert entries[1]['_planned_date'] == '2026-01-12'
        # B planned = A_planned(01-12) + 10 = 2026-01-26 (но actual = 01-20)
        assert entries[2]['_planned_date'] == '2026-01-26'
        # C planned = actual_B(01-20) + 3 = 2026-01-23
        assert entries[3]['_planned_date'] == '2026-01-23'

    def test_all_actual_dates_filled(self):
        """Все actual_date заполнены — planned_date всё равно рассчитываются"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-01-05', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '2026-01-10', 'executor_role': 'designer'},
            {'stage_code': 'B', 'norm_days': 3, 'actual_date': '2026-01-15', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        # A planned = START(05.01, пн) + 5 рабочих = 2026-01-12 (пн)
        assert entries[1]['_planned_date'] == '2026-01-12'
        # B planned = actual_A(10.01, сб) + 3 рабочих = 2026-01-14 (ср)
        assert entries[2]['_planned_date'] == '2026-01-14'


# ============================================================================
# Кросс-стадийная цепочка
# ============================================================================

class TestCalcPlannedDatesCrossStage:
    """Тесты: prev_date переходит через границы стадий"""

    def test_cross_stage_chain(self):
        """Цепочка проходит через STAGE1 → STAGE2 без разрыва"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-01-05', 'executor_role': ''},
            {'stage_code': 'STAGE1', 'executor_role': 'header', 'norm_days': 0, 'actual_date': ''},
            {'stage_code': 'S1_A', 'norm_days': 5, 'actual_date': '2026-01-12', 'executor_role': 'designer',
             'stage_group': 'STAGE1'},
            {'stage_code': 'STAGE2', 'executor_role': 'header', 'norm_days': 0, 'actual_date': ''},
            {'stage_code': 'S2_A', 'norm_days': 10, 'actual_date': '', 'executor_role': 'designer',
             'stage_group': 'STAGE2'},
        ]
        calc_planned_dates(entries)

        # S1_A planned = START + 5 = 2026-01-12
        assert entries[2]['_planned_date'] == '2026-01-12'
        # S2_A planned = actual_S1_A(01-12) + 10 = 2026-01-26
        assert entries[4]['_planned_date'] == '2026-01-26'


# ============================================================================
# Граничные случаи
# ============================================================================

class TestCalcPlannedDatesEdgeCases:
    """Граничные случаи"""

    def test_empty_entries(self):
        """Пустой список — без ошибок"""
        entries = []
        calc_planned_dates(entries)
        assert entries == []

    def test_only_start(self):
        """Только START — без ошибок"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-01-05', 'executor_role': ''},
        ]
        calc_planned_dates(entries)
        assert entries[0]['_planned_date'] == '2026-01-05'

    def test_none_norm_days_treated_as_zero(self):
        """norm_days=None → planned_date пустая"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-01-05', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': None, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)
        assert entries[1]['_planned_date'] == ''

    def test_weekend_skip(self):
        """Рабочие дни пропускают выходные"""
        # 2026-01-09 = пятница
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-01-09', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 1, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)
        # 1 рабочий день от пятницы = понедельник 2026-01-12
        assert entries[1]['_planned_date'] == '2026-01-12'
