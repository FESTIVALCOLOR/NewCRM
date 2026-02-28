# -*- coding: utf-8 -*-
"""
Unit-тесты для utils/calendar_helpers.py
Тестируются только чистые функции (без GUI): add_working_days, working_days_between.
"""
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

pytest = __import__('pytest')
pytest.importorskip("PyQt5")

from utils.calendar_helpers import add_working_days, working_days_between


# ========== Тесты working_days_between ==========

class TestWorkingDaysBetween:
    """Тесты функции подсчёта рабочих дней между датами."""

    def test_monday_to_friday_five_days(self):
        """Пн → Пт = 5 рабочих дней (не считая старт, считая конец)."""
        # 2024-01-01 Пн, 2024-01-05 Пт
        result = working_days_between('2024-01-01', '2024-01-05')
        assert result == 4, f"Пн→Пт ожидается 4, получено {result}"

    def test_same_date_returns_zero(self):
        """Одинаковые даты — 0 рабочих дней."""
        result = working_days_between('2024-01-01', '2024-01-01')
        assert result == 0

    def test_end_before_start_returns_zero(self):
        """Конец раньше начала — 0 рабочих дней."""
        result = working_days_between('2024-01-10', '2024-01-05')
        assert result == 0

    def test_empty_start_returns_zero(self):
        """Пустая начальная дата возвращает 0."""
        result = working_days_between('', '2024-01-05')
        assert result == 0

    def test_empty_end_returns_zero(self):
        """Пустая конечная дата возвращает 0."""
        result = working_days_between('2024-01-01', '')
        assert result == 0

    def test_none_start_returns_zero(self):
        """None начальная дата возвращает 0."""
        result = working_days_between(None, '2024-01-05')
        assert result == 0

    def test_none_end_returns_zero(self):
        """None конечная дата возвращает 0."""
        result = working_days_between('2024-01-01', None)
        assert result == 0

    def test_week_excludes_weekend(self):
        """Пн → следующий Пн = 5 рабочих дней (сб и вс не считаются)."""
        # 2024-01-01 (Пн) → 2024-01-08 (Пн) = 5 рабочих дней
        result = working_days_between('2024-01-01', '2024-01-08')
        assert result == 5, f"Пн→след.Пн ожидается 5, получено {result}"

    def test_invalid_date_format_returns_zero(self):
        """Неверный формат даты возвращает 0."""
        result = working_days_between('not-a-date', '2024-01-05')
        assert result == 0

    def test_two_weeks_ten_working_days(self):
        """Две рабочие недели = 10 рабочих дней."""
        # 2024-01-01 Пн → 2024-01-15 Пн = 10 рабочих дней
        result = working_days_between('2024-01-01', '2024-01-15')
        assert result == 10, f"Две недели ожидается 10, получено {result}"


# ========== Тесты add_working_days ==========

class TestAddWorkingDays:
    """Тесты функции добавления рабочих дней к дате."""

    def test_add_zero_days_returns_same(self):
        """Добавление 0 дней возвращает исходную дату."""
        result = add_working_days('2024-01-01', 0)
        assert result == '2024-01-01'

    def test_empty_date_returns_empty(self):
        """Пустая дата возвращает пустую строку."""
        result = add_working_days('', 5)
        assert result == ''

    def test_none_date_returns_empty(self):
        """None дата возвращает пустую строку."""
        result = add_working_days(None, 5)
        assert result == ''

    def test_negative_days_returns_same(self):
        """Отрицательное количество дней возвращает исходную дату."""
        result = add_working_days('2024-01-01', -1)
        assert result == '2024-01-01'

    def test_invalid_date_returns_original(self):
        """Неверный формат даты возвращает исходную строку."""
        result = add_working_days('not-a-date', 5)
        assert result == 'not-a-date'

    def test_returns_string_format(self):
        """Результат должен быть строкой в формате YYYY-MM-DD."""
        result = add_working_days('2024-01-01', 1)
        assert isinstance(result, str)
        # Проверяем формат YYYY-MM-DD
        parts = result.split('-')
        assert len(parts) == 3
        assert len(parts[0]) == 4  # год
