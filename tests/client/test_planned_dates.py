# -*- coding: utf-8 -*-
"""
Тесты каскадного расчёта планируемых дат (Phase 5).
Тестируем calc_planned_dates() из utils/timeline_calc.py.

ВАЖНО: Даты выбраны в июле 2026 (без российских праздников),
чтобы тесты не зависели от is_working_day с праздничным календарём.
"""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.timeline_calc import calc_planned_dates


# ============================================================================
# Базовая цепочка
# ============================================================================

class TestCalcPlannedDatesBasic:
    """Базовые тесты расчёта planned_date"""

    def test_simple_chain_3_entries(self):
        """Цепочка из 3 подэтапов: START → A(5д) → B(10д) → C(3д)"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-07-06', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '', 'executor_role': 'designer'},
            {'stage_code': 'B', 'norm_days': 10, 'actual_date': '', 'executor_role': 'designer'},
            {'stage_code': 'C', 'norm_days': 3, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        # START = 2026-07-06 (понедельник)
        assert entries[0]['_planned_date'] == '2026-07-06'
        # A = START + 5 рабочих дней = 2026-07-13 (понедельник)
        assert entries[1]['_planned_date'] == '2026-07-13'
        # B = A_planned + 10 рабочих дней = 2026-07-27 (понедельник)
        assert entries[2]['_planned_date'] == '2026-07-27'
        # C = B_planned + 3 рабочих дня = 2026-07-30 (четверг)
        assert entries[3]['_planned_date'] == '2026-07-30'

    def test_headers_skipped(self):
        """Header-строки пропускаются, не влияют на цепочку"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-07-06', 'executor_role': ''},
            {'stage_code': 'STAGE1', 'executor_role': 'header', 'norm_days': 0, 'actual_date': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        assert entries[2]['_planned_date'] == '2026-07-13'

    def test_no_start_date_empty_chain(self):
        """Без START.actual_date — вся цепочка пустая"""
        entries = [
            {'stage_code': 'START', 'actual_date': '', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        assert entries[0]['_planned_date'] == ''
        assert entries[1]['_planned_date'] == ''

    def test_zero_norm_days_inherits_prev(self):
        """norm_days=0 → planned_date наследует prev_date"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-07-06', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 0, 'actual_date': '', 'executor_role': 'designer'},
            {'stage_code': 'B', 'norm_days': 5, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        # norm=0 → наследует prev_date
        assert entries[1]['_planned_date'] == '2026-07-06'
        # B считается от A_planned (prev_date обновился из planned A)
        assert entries[2]['_planned_date'] == '2026-07-13'


# ============================================================================
# Каскадный пересчёт (actual_date влияет на цепочку)
# ============================================================================

class TestCalcPlannedDatesCascade:
    """Тесты каскадного пересчёта при наличии actual_date"""

    def test_actual_date_overrides_prev(self):
        """actual_date подэтапа A становится базой для B"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-07-06', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '2026-07-15', 'executor_role': 'designer'},
            {'stage_code': 'B', 'norm_days': 3, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        # A planned = START + 5 = 2026-07-13
        assert entries[1]['_planned_date'] == '2026-07-13'
        # B planned = actual_A(07-15, ср) + 3 рабочих дня = 2026-07-20 (пн)
        assert entries[2]['_planned_date'] == '2026-07-20'

    def test_cascade_after_manual_edit(self):
        """Симуляция ручного редактирования: A сдвинулся → B, C пересчитываются"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-07-06', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '2026-08-03', 'executor_role': 'designer'},
            {'stage_code': 'B', 'norm_days': 10, 'actual_date': '', 'executor_role': 'designer'},
            {'stage_code': 'C', 'norm_days': 3, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        # A planned = START + 5 = 2026-07-13
        assert entries[1]['_planned_date'] == '2026-07-13'
        # B planned = actual_A(08-03, пн) + 10 рабочих дней = 2026-08-17 (пн)
        assert entries[2]['_planned_date'] == '2026-08-17'
        # C planned = B_planned(08-17) + 3 рабочих дня = 2026-08-20 (чт)
        assert entries[3]['_planned_date'] == '2026-08-20'

    def test_middle_actual_date_cascades(self):
        """actual_date в середине цепочки: A и C пустые, B заполнен"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-07-06', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '', 'executor_role': 'designer'},
            {'stage_code': 'B', 'norm_days': 10, 'actual_date': '2026-07-20', 'executor_role': 'designer'},
            {'stage_code': 'C', 'norm_days': 3, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        # A planned = START + 5 = 2026-07-13
        assert entries[1]['_planned_date'] == '2026-07-13'
        # B planned = A_planned(07-13) + 10 = 2026-07-27 (но actual = 07-20)
        assert entries[2]['_planned_date'] == '2026-07-27'
        # C planned = actual_B(07-20) + 3 = 2026-07-23
        assert entries[3]['_planned_date'] == '2026-07-23'

    def test_all_actual_dates_filled(self):
        """Все actual_date заполнены — planned_date всё равно рассчитываются"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-07-06', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '2026-07-10', 'executor_role': 'designer'},
            {'stage_code': 'B', 'norm_days': 3, 'actual_date': '2026-07-15', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)

        # A planned = START(06.07, пн) + 5 рабочих = 2026-07-13 (пн)
        assert entries[1]['_planned_date'] == '2026-07-13'
        # B planned = actual_A(10.07, пт) + 3 рабочих = 2026-07-15 (ср)
        assert entries[2]['_planned_date'] == '2026-07-15'


# ============================================================================
# Кросс-стадийная цепочка
# ============================================================================

class TestCalcPlannedDatesCrossStage:
    """Тесты: prev_date переходит через границы стадий"""

    def test_cross_stage_chain(self):
        """Цепочка проходит через STAGE1 → STAGE2 без разрыва"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-07-06', 'executor_role': ''},
            {'stage_code': 'STAGE1', 'executor_role': 'header', 'norm_days': 0, 'actual_date': ''},
            {'stage_code': 'S1_A', 'norm_days': 5, 'actual_date': '2026-07-13', 'executor_role': 'designer',
             'stage_group': 'STAGE1'},
            {'stage_code': 'STAGE2', 'executor_role': 'header', 'norm_days': 0, 'actual_date': ''},
            {'stage_code': 'S2_A', 'norm_days': 10, 'actual_date': '', 'executor_role': 'designer',
             'stage_group': 'STAGE2'},
        ]
        calc_planned_dates(entries)

        # S1_A planned = START + 5 = 2026-07-13
        assert entries[2]['_planned_date'] == '2026-07-13'
        # S2_A planned = actual_S1_A(07-13) + 10 = 2026-07-27
        assert entries[4]['_planned_date'] == '2026-07-27'


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
            {'stage_code': 'START', 'actual_date': '2026-07-06', 'executor_role': ''},
        ]
        calc_planned_dates(entries)
        assert entries[0]['_planned_date'] == '2026-07-06'

    def test_none_norm_days_inherits_prev(self):
        """norm_days=None → planned_date наследует prev_date"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-07-06', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': None, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)
        # norm=None → 0 → наследует prev_date
        assert entries[1]['_planned_date'] == '2026-07-06'

    def test_weekend_skip(self):
        """Рабочие дни пропускают выходные"""
        # 2026-07-10 = пятница
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-07-10', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 1, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)
        # 1 рабочий день от пятницы = понедельник 2026-07-13
        assert entries[1]['_planned_date'] == '2026-07-13'

    def test_russian_holidays_skipped(self):
        """Российские праздники (1-8 января) корректно пропускаются"""
        # START = 2 января (праздник), +5 рабочих дней
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-01-02', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)
        # Первый рабочий день после новогодних каникул = 9 января (пт)
        # +5 рабочих дней: 9(1), 12(2), 13(3), 14(4), 15(5) = 2026-01-15
        assert entries[1]['_planned_date'] == '2026-01-15'

    def test_custom_norm_days_override(self):
        """custom_norm_days переопределяет norm_days"""
        entries = [
            {'stage_code': 'START', 'actual_date': '2026-07-06', 'executor_role': ''},
            {'stage_code': 'A', 'norm_days': 5, 'custom_norm_days': 3, 'actual_date': '', 'executor_role': 'designer'},
        ]
        calc_planned_dates(entries)
        # custom_norm_days=3 вместо norm_days=5
        # 2026-07-06 + 3 рабочих = Jul 7(1), 8(2), 9(3) = 2026-07-09
        assert entries[1]['_planned_date'] == '2026-07-09'
