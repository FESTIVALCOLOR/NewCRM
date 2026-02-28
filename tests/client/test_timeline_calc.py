# -*- coding: utf-8 -*-
"""
Тесты utils/timeline_calc.py — расчёт планируемых дат таймлайна.

Покрытие:
  - TestCalcPlannedDates (12) — все ветви логики calc_planned_dates
ИТОГО: 12 тестов
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _mock_add_working_days(start_date_str, working_days):
    """Упрощённый мок: добавляет calendar days (не рабочие) для предсказуемости."""
    from datetime import datetime, timedelta
    if not start_date_str or working_days <= 0:
        return start_date_str or ''
    try:
        dt = datetime.strptime(start_date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return start_date_str or ''
    dt += timedelta(days=working_days)
    return dt.strftime('%Y-%m-%d')


@pytest.fixture(autouse=True)
def mock_add_working_days():
    """Мокаем add_working_days чтобы не зависеть от PyQt5 и calendar_helpers."""
    with patch('utils.timeline_calc.add_working_days', side_effect=_mock_add_working_days):
        yield


class TestCalcPlannedDates:
    """Тесты расчёта планируемых дат для подэтапов таймлайна."""

    def _import_calc(self):
        from utils.timeline_calc import calc_planned_dates
        return calc_planned_dates

    def test_empty_entries(self):
        """Пустой список записей — возвращает пустой список."""
        calc = self._import_calc()
        result = calc([])
        assert result == []

    def test_start_entry_gets_actual_date(self):
        """START получает _planned_date из собственной actual_date."""
        calc = self._import_calc()
        entries = [
            {'stage_code': 'START', 'actual_date': '2025-01-10', 'executor_role': 'manager'}
        ]
        result = calc(entries)
        assert result[0]['_planned_date'] == '2025-01-10'

    def test_header_rows_skipped(self):
        """Записи с executor_role='header' пропускаются, _planned_date не добавляется."""
        calc = self._import_calc()
        entries = [
            {'stage_code': 'START', 'actual_date': '2025-01-10', 'executor_role': 'manager'},
            {'stage_code': 'H1', 'executor_role': 'header', 'norm_days': 5},
        ]
        result = calc(entries)
        assert '_planned_date' not in result[1]

    def test_norm_days_added_to_prev_date(self):
        """Планируемая дата = prev_date + norm_days."""
        calc = self._import_calc()
        entries = [
            {'stage_code': 'START', 'actual_date': '2025-01-10', 'executor_role': 'manager'},
            {'stage_code': 'DESIGN', 'executor_role': 'designer', 'norm_days': 5},
        ]
        result = calc(entries)
        # 2025-01-10 + 5 дней = 2025-01-15 (мок добавляет calendar days)
        assert result[1]['_planned_date'] == '2025-01-15'

    def test_custom_norm_days_overrides_norm(self):
        """custom_norm_days имеет приоритет над norm_days."""
        calc = self._import_calc()
        entries = [
            {'stage_code': 'START', 'actual_date': '2025-02-01', 'executor_role': 'manager'},
            {'stage_code': 'STAGE1', 'executor_role': 'designer', 'norm_days': 10, 'custom_norm_days': 3},
        ]
        result = calc(entries)
        # 2025-02-01 + 3 = 2025-02-04
        assert result[1]['_planned_date'] == '2025-02-04'

    def test_custom_norm_zero_uses_norm(self):
        """custom_norm_days=0 не перезаписывает norm_days."""
        calc = self._import_calc()
        entries = [
            {'stage_code': 'START', 'actual_date': '2025-03-01', 'executor_role': 'manager'},
            {'stage_code': 'STAGE1', 'executor_role': 'designer', 'norm_days': 7, 'custom_norm_days': 0},
        ]
        result = calc(entries)
        # custom_norm_days=0 => используется norm_days=7
        assert result[1]['_planned_date'] == '2025-03-08'

    def test_zero_norm_inherits_prev_date(self):
        """Этап с norm_days=0 наследует prev_date."""
        calc = self._import_calc()
        entries = [
            {'stage_code': 'START', 'actual_date': '2025-04-01', 'executor_role': 'manager'},
            {'stage_code': 'CHECK', 'executor_role': 'reviewer', 'norm_days': 0},
        ]
        result = calc(entries)
        assert result[1]['_planned_date'] == '2025-04-01'

    def test_actual_date_updates_prev_date(self):
        """Если у записи есть actual_date, она обновляет prev_date для следующих."""
        calc = self._import_calc()
        entries = [
            {'stage_code': 'START', 'actual_date': '2025-05-01', 'executor_role': 'manager'},
            {'stage_code': 'STAGE1', 'executor_role': 'designer', 'norm_days': 5, 'actual_date': '2025-05-08'},
            {'stage_code': 'STAGE2', 'executor_role': 'designer', 'norm_days': 3},
        ]
        result = calc(entries)
        # STAGE2: prev_date = actual_date STAGE1 = 2025-05-08, + 3 = 2025-05-11
        assert result[2]['_planned_date'] == '2025-05-11'

    def test_planned_date_as_prev_when_no_actual(self):
        """Без actual_date, _planned_date используется как prev_date."""
        calc = self._import_calc()
        entries = [
            {'stage_code': 'START', 'actual_date': '2025-06-01', 'executor_role': 'manager'},
            {'stage_code': 'S1', 'executor_role': 'designer', 'norm_days': 2},
            {'stage_code': 'S2', 'executor_role': 'designer', 'norm_days': 3},
        ]
        result = calc(entries)
        # S1: planned = 2025-06-01 + 2 = 2025-06-03
        # S2: prev = S1._planned = 2025-06-03, + 3 = 2025-06-06
        assert result[1]['_planned_date'] == '2025-06-03'
        assert result[2]['_planned_date'] == '2025-06-06'

    def test_no_start_actual_date(self):
        """Без START.actual_date — prev_date пустой, даты не рассчитываются."""
        calc = self._import_calc()
        entries = [
            {'stage_code': 'START', 'executor_role': 'manager'},
            {'stage_code': 'S1', 'executor_role': 'designer', 'norm_days': 5},
        ]
        result = calc(entries)
        # prev_date пустой => _planned_date = ''
        assert result[0]['_planned_date'] == ''
        assert result[1]['_planned_date'] == ''

    def test_none_norm_days_treated_as_zero(self):
        """norm_days=None обрабатывается как 0."""
        calc = self._import_calc()
        entries = [
            {'stage_code': 'START', 'actual_date': '2025-07-01', 'executor_role': 'manager'},
            {'stage_code': 'S1', 'executor_role': 'designer', 'norm_days': None},
        ]
        result = calc(entries)
        # None or 0 => 0, наследует prev_date
        assert result[1]['_planned_date'] == '2025-07-01'

    def test_returns_same_entries_list(self):
        """Функция возвращает тот же список (мутирует in-place)."""
        calc = self._import_calc()
        entries = [
            {'stage_code': 'START', 'actual_date': '2025-01-01', 'executor_role': 'manager'},
        ]
        result = calc(entries)
        assert result is entries
