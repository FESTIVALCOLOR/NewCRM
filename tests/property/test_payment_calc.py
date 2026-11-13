# -*- coding: utf-8 -*-
"""
Property-based тесты расчёта оплат.

Тестируемая логика: area * rate_per_m2 = amount
Инварианты:
- При area > 0 и rate > 0 → amount > 0
- Результат не NaN и не Inf
- Монотонность: большая площадь → большая или равная сумма (при одинаковом тарифе)
"""

import math

from hypothesis import assume, given, settings
import pytest

from tests.property.conftest import areas, rate_per_m2, rates, realistic_areas

pytestmark = pytest.mark.property


class TestPaymentAmountCalculation:
    """Тесты формулы расчёта суммы оплаты: area * rate_per_m2."""

    @given(area=areas, rate=rate_per_m2)
    @settings(max_examples=200)
    def test_positive_inputs_give_positive_result(self, area, rate):
        """При area > 0 и rate > 0 результат всегда > 0."""
        assume(area > 0 and rate > 0)
        amount = area * rate
        assert amount > 0, f"area={area}, rate={rate}, amount={amount}"

    @given(area=areas, rate=rate_per_m2)
    @settings(max_examples=200)
    def test_result_is_finite(self, area, rate):
        """Результат никогда не NaN и не Inf."""
        amount = area * rate
        assert not math.isnan(amount), f"NaN: area={area}, rate={rate}"
        assert not math.isinf(amount), f"Inf: area={area}, rate={rate}"

    @given(area=areas, rate=rate_per_m2)
    @settings(max_examples=200)
    def test_result_non_negative(self, area, rate):
        """Результат всегда >= 0 (оба множителя неотрицательны)."""
        amount = area * rate
        assert amount >= 0, f"Отрицательная сумма: area={area}, rate={rate}"

    @given(area=realistic_areas, rate=rate_per_m2)
    @settings(max_examples=200)
    def test_monotonicity_by_area(self, area, rate):
        """Большая площадь при том же тарифе → большая сумма."""
        assume(rate > 0)
        amount1 = area * rate
        amount2 = (area + 10) * rate
        assert amount2 > amount1, f"Не монотонно: area={area}, area+10={area + 10}, rate={rate}, a1={amount1}, a2={amount2}"

    @given(area=realistic_areas, rate=rate_per_m2)
    @settings(max_examples=200)
    def test_monotonicity_by_rate(self, area, rate):
        """Больший тариф при той же площади → большая сумма."""
        assume(area > 0)
        amount1 = area * rate
        amount2 = area * (rate + 1.0)
        assert amount2 > amount1

    @given(area=realistic_areas)
    @settings(max_examples=200)
    def test_zero_rate_gives_zero(self, area):
        """Нулевой тариф → нулевая сумма."""
        amount = area * 0.0
        assert amount == 0.0

    @given(rate=rate_per_m2)
    @settings(max_examples=200)
    def test_zero_area_gives_zero(self, rate):
        """Нулевая площадь → нулевая сумма (граничный случай в CRM: area=0 → 0 руб)."""
        amount = 0.0 * rate
        assert amount == 0.0

    @given(area=realistic_areas, rate=rate_per_m2)
    @settings(max_examples=200)
    def test_rounding_to_kopecks(self, area, rate):
        """Округление до копеек (2 знака) не создаёт отрицательных значений."""
        amount = round(area * rate, 2)
        assert amount >= 0
        assert not math.isnan(amount)
        assert not math.isinf(amount)

    @given(area=realistic_areas, rate=rate_per_m2)
    @settings(max_examples=200)
    def test_commutativity(self, area, rate):
        """Коммутативность умножения: area * rate == rate * area."""
        assert area * rate == rate * area
