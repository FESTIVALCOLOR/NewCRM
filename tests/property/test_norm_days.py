# -*- coding: utf-8 -*-
"""
Property-based тесты расчёта нормо-дней и сроков договоров.

Тестируемые функции (server/services/timeline_service.py):
- calc_contract_term(project_type_code, area) → int (рабочие дни)
- calc_area_coefficient(area) → int (коэффициент K)
- calc_template_contract_term(template_subtype, area, floors) → int

Инварианты:
- 0 <= result <= 500
- result — целое число
- Монотонность по площади (не строгая для threshold-функций)
- calc_area_coefficient >= 0
"""

import math
import os
import sys
from unittest.mock import MagicMock

from hypothesis import assume, given, settings
from hypothesis import strategies as st
import pytest

from tests.property.conftest import (
    areas,
    project_type_codes,
    realistic_areas,
    template_subtypes,
)
from tests.property.conftest import (
    floors as floors_strategy,
)

# Мокируем серверный модуль database, чтобы избежать конфликта с клиентским database/
# timeline_service делает `from database import SessionLocal, NormDaysTemplate`
_mock_db = MagicMock()
_original_database = sys.modules.get("database")
sys.modules["database"] = _mock_db

# Добавляем server/ в sys.path для импорта services.timeline_service
_server_path = os.path.join(os.path.dirname(__file__), "..", "..", "server")
if _server_path not in sys.path:
    sys.path.insert(0, _server_path)

from services.timeline_service import (
    calc_area_coefficient,
    calc_contract_term,
    calc_template_contract_term,
)

# Восстанавливаем оригинальный модуль database
if _original_database is not None:
    sys.modules["database"] = _original_database
else:
    del sys.modules["database"]

pytestmark = pytest.mark.property


class TestCalcContractTerm:
    """Property-тесты calc_contract_term(project_type_code, area)."""

    @given(pt=project_type_codes, area=realistic_areas)
    @settings(max_examples=200)
    def test_result_non_negative(self, pt, area):
        """Результат >= 0."""
        result = calc_contract_term(pt, area)
        assert result >= 0, f"Отрицательный срок: pt={pt}, area={area}, result={result}"

    @given(pt=project_type_codes, area=realistic_areas)
    @settings(max_examples=200)
    def test_result_is_int(self, pt, area):
        """Результат — целое число."""
        result = calc_contract_term(pt, area)
        assert isinstance(result, int), f"Не int: type={type(result)}, value={result}"

    @given(pt=project_type_codes, area=st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=200)
    def test_result_in_range_for_normal_areas(self, pt, area):
        """Для площадей до 500 м² результат > 0 (есть threshold)."""
        result = calc_contract_term(pt, area)
        assert result > 0, f"Нулевой срок для area={area}, pt={pt}"

    @given(pt=project_type_codes)
    @settings(max_examples=50)
    def test_large_area_returns_zero(self, pt):
        """Для площади > 500 м² возвращает 0 (индивидуальный расчёт)."""
        result = calc_contract_term(pt, 501.0)
        assert result == 0, f"Для area=501 ожидался 0, получено {result}"

    @given(
        pt=project_type_codes,
        area1=st.floats(min_value=10.0, max_value=499.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=200)
    def test_monotonicity_weak(self, pt, area1):
        """Большая площадь → больший или равный срок (слабая монотонность)."""
        area2 = area1 + 1.0
        assume(area2 <= 500.0)
        r1 = calc_contract_term(pt, area1)
        r2 = calc_contract_term(pt, area2)
        assert r2 >= r1, f"Не монотонно: area1={area1}→{r1}, area2={area2}→{r2}"

    @given(area=st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=200)
    def test_full_project_longest(self, area):
        """Полный проект (1) имеет срок >= Эскизного (2) >= Планировочного (3)."""
        full = calc_contract_term(1, area)
        sketch = calc_contract_term(2, area)
        plan = calc_contract_term(3, area)
        assert full >= sketch >= plan, f"area={area}: Полный={full}, Эскизный={sketch}, Планировочный={plan}"


class TestCalcAreaCoefficient:
    """Property-тесты calc_area_coefficient(area)."""

    @given(area=areas)
    @settings(max_examples=200)
    def test_result_non_negative(self, area):
        """Коэффициент K >= 0."""
        result = calc_area_coefficient(area)
        assert result >= 0, f"Отрицательный K: area={area}, K={result}"

    @given(area=areas)
    @settings(max_examples=200)
    def test_result_is_int(self, area):
        """Коэффициент K — целое число."""
        result = calc_area_coefficient(area)
        assert isinstance(result, int), f"K не int: {type(result)}"

    @given(area=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=200)
    def test_small_area_gives_zero(self, area):
        """Площадь до 100 м² → K = 0."""
        result = calc_area_coefficient(area)
        assert result == 0, f"area={area}, K={result}, ожидался 0"

    @given(area1=realistic_areas)
    @settings(max_examples=200)
    def test_monotonicity(self, area1):
        """Большая площадь → больший или равный K."""
        area2 = area1 + 100.0
        r1 = calc_area_coefficient(area1)
        r2 = calc_area_coefficient(area2)
        assert r2 >= r1, f"Не монотонно: area1={area1}→{r1}, area2={area2}→{r2}"

    @given(area=realistic_areas)
    @settings(max_examples=200)
    def test_formula_matches(self, area):
        """Прямая проверка формулы: max(0, int((area - 1) // 100))."""
        expected = max(0, int((area - 1) // 100))
        result = calc_area_coefficient(area)
        assert result == expected, f"area={area}: got {result}, expected {expected}"


class TestCalcTemplateContractTerm:
    """Property-тесты calc_template_contract_term(template_subtype, area, floors)."""

    @given(sub=template_subtypes, area=realistic_areas, fl=floors_strategy)
    @settings(max_examples=200)
    def test_result_positive(self, sub, area, fl):
        """Срок шаблонного проекта > 0."""
        result = calc_template_contract_term(sub, area, fl)
        assert result > 0, f"Нулевой срок: sub='{sub}', area={area}, floors={fl}"

    @given(sub=template_subtypes, area=realistic_areas, fl=floors_strategy)
    @settings(max_examples=200)
    def test_result_is_int(self, sub, area, fl):
        """Результат — целое число."""
        result = calc_template_contract_term(sub, area, fl)
        assert isinstance(result, int), f"Не int: {type(result)}"

    @given(sub=template_subtypes, area=realistic_areas, fl=floors_strategy)
    @settings(max_examples=200)
    def test_result_reasonable_range(self, sub, area, fl):
        """Срок > 0 и конечный (верхний лимит не ограничиваем — 5 этажей + большая площадь могут давать тысячи дней)."""
        result = calc_template_contract_term(sub, area, fl)
        assert result >= 1, f"Нулевой или отрицательный срок: {result} дней"

    @given(
        sub=template_subtypes,
        area=st.floats(min_value=10.0, max_value=4000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=200)
    def test_more_floors_more_days(self, sub, area):
        """Больше этажей → больше или равный срок."""
        assume("ванной" not in sub.lower())  # Для ванных этажи не влияют
        r1 = calc_template_contract_term(sub, area, floors=1)
        r2 = calc_template_contract_term(sub, area, floors=2)
        assert r2 >= r1, f"Больше этажей — меньше срок: sub='{sub}', area={area}, 1 этаж={r1}, 2 этажа={r2}"

    @given(
        area=st.floats(min_value=10.0, max_value=4000.0, allow_nan=False, allow_infinity=False),
        fl=floors_strategy,
    )
    @settings(max_examples=200)
    def test_visualization_adds_time(self, area, fl):
        """Визуализация увеличивает срок (Стандарт vs Стандарт с визуализацией)."""
        r_standard = calc_template_contract_term("Стандарт", area, fl)
        r_viz = calc_template_contract_term("Стандарт с визуализацией", area, fl)
        assert r_viz >= r_standard, f"Визуализация не добавила время: area={area}, fl={fl}, стандарт={r_standard}, с визуализацией={r_viz}"

    @given(
        sub=st.sampled_from(["Стандарт", "Стандарт с визуализацией"]),
        area1=st.floats(min_value=10.0, max_value=3000.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=200)
    def test_area_monotonicity(self, sub, area1):
        """Большая площадь → больший или равный срок."""
        area2 = area1 + 50.0
        r1 = calc_template_contract_term(sub, area1, floors=1)
        r2 = calc_template_contract_term(sub, area2, floors=1)
        assert r2 >= r1, f"Не монотонно по площади: sub='{sub}', area1={area1}→{r1}, area2={area2}→{r2}"
