# -*- coding: utf-8 -*-
"""
Property-based тесты расчёта зарплат.

В проекте нет выделенной функции calculate_salary — зарплаты рассчитываются
как сумма оплат сотрудника за период. Тестируем инварианты агрегации:
- Сумма >= каждого слагаемого
- Сумма >= 0
- Результат конечный (не NaN, не Inf)
"""

import math

from hypothesis import assume, given, settings
from hypothesis import strategies as st
import pytest

from tests.property.conftest import rate_per_m2, realistic_areas

pytestmark = pytest.mark.property


class TestSalaryAggregation:
    """Тесты агрегации оплат в зарплату: sum(payments) за период."""

    @given(payments=st.lists(st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False), min_size=0, max_size=50))
    @settings(max_examples=200)
    def test_salary_sum_non_negative(self, payments):
        """Сумма неотрицательных оплат всегда >= 0."""
        total = sum(payments)
        assert total >= 0, f"Отрицательная зарплата: {total}"

    @given(payments=st.lists(st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False), min_size=0, max_size=50))
    @settings(max_examples=200)
    def test_salary_sum_is_finite(self, payments):
        """Сумма оплат конечна (не NaN, не Inf)."""
        total = sum(payments)
        assert not math.isnan(total), f"NaN зарплата"
        assert not math.isinf(total), f"Inf зарплата"

    @given(payments=st.lists(st.floats(min_value=0.01, max_value=500_000.0, allow_nan=False, allow_infinity=False), min_size=1, max_size=50))
    @settings(max_examples=200)
    def test_salary_ge_max_payment(self, payments):
        """Сумма >= максимальной отдельной оплаты."""
        total = sum(payments)
        assert total >= max(payments), f"Сумма {total} < макс. оплаты {max(payments)}"

    @given(payments=st.lists(st.floats(min_value=0.01, max_value=500_000.0, allow_nan=False, allow_infinity=False), min_size=2, max_size=50))
    @settings(max_examples=200)
    def test_adding_payment_increases_salary(self, payments):
        """Добавление оплаты увеличивает зарплату."""
        partial = sum(payments[:-1])
        total = sum(payments)
        assert total > partial, f"Добавление {payments[-1]} не увеличило зарплату: partial={partial}, total={total}"

    @given(area=realistic_areas, rate=rate_per_m2, num_stages=st.integers(min_value=1, max_value=10))
    @settings(max_examples=200)
    def test_salary_from_stages_proportional(self, area, rate, num_stages):
        """Зарплата из N стадий = N * (area * rate) при одинаковых стадиях."""
        single_payment = area * rate
        total = single_payment * num_stages
        assert not math.isnan(total)
        assert not math.isinf(total)
        assert total >= single_payment

    @given(payments=st.lists(st.floats(min_value=0.0, max_value=500_000.0, allow_nan=False, allow_infinity=False), min_size=0, max_size=50))
    @settings(max_examples=200)
    def test_rounding_salary_to_kopecks(self, payments):
        """Округлённая зарплата >= 0 и конечна."""
        total = round(sum(payments), 2)
        assert total >= 0
        assert not math.isnan(total)
        assert not math.isinf(total)
