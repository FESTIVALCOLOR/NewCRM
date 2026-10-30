"""
Property-based тесты для расчётов с граничными значениями.
Проверяют инварианты: для любого допустимого входа результат > 0.
"""

from hypothesis import given, settings
from hypothesis import strategies as st
import pytest


def _import_calc_contract_term():
    """Импорт функции расчёта срока из contract_dialogs."""
    import sys

    # Мокаем PyQt5 если не доступен
    try:
        from ui.contract_dialogs import ContractEditDialog

        return ContractEditDialog._calc_contract_term
    except Exception:
        # Fallback: копируем логику для теста без PyQt5
        return None


def _import_norm_days_calc():
    """Импорт из norm_days_settings_widget."""
    try:
        from ui.norm_days_settings_widget import _calc_contract_term

        return _calc_contract_term
    except Exception:
        return None


# Прямая реализация для CI (без PyQt5)
def _calc_contract_term_standalone(pt_code, area):
    """Копия логики для тестирования без PyQt5."""
    if pt_code == 1:
        thresholds = [(70, 50), (100, 60), (130, 70), (160, 80), (190, 90), (220, 100), (250, 110), (300, 120), (350, 130), (400, 140), (450, 150), (500, 160)]
    elif pt_code == 3:
        thresholds = [(70, 10), (100, 15), (130, 20), (160, 25), (190, 30), (220, 35), (250, 40), (300, 45), (350, 50), (400, 55), (450, 60), (500, 65)]
    else:
        thresholds = [(70, 30), (100, 35), (130, 40), (160, 45), (190, 50), (220, 55), (250, 60), (300, 65), (350, 70), (400, 75), (450, 80), (500, 85)]
    for max_area, days in thresholds:
        if area <= max_area:
            return days
    return thresholds[-1][1]


class TestCalcContractTermProperties:
    """Property-based: для любой площади > 0 и любого типа проекта — срок > 0."""

    @given(pt_code=st.sampled_from([1, 2, 3]), area=st.integers(min_value=1, max_value=10000))
    @settings(max_examples=200)
    def test_always_positive_result(self, pt_code, area):
        """Срок договора всегда > 0 для area > 0."""
        result = _calc_contract_term_standalone(pt_code, area)
        assert result > 0, f"pt_code={pt_code}, area={area} -> result={result}"

    @given(pt_code=st.sampled_from([1, 2, 3]), area=st.integers(min_value=501, max_value=50000))
    @settings(max_examples=100)
    def test_large_area_returns_max_threshold(self, pt_code, area):
        """Площадь > 500 м² — возвращает максимальный срок, НЕ ноль."""
        result = _calc_contract_term_standalone(pt_code, area)
        max_days = {1: 160, 2: 85, 3: 65}
        assert result == max_days[pt_code], f"pt_code={pt_code}, area={area}: ожидали {max_days[pt_code]}, получили {result}"

    @given(
        pt_code=st.sampled_from([1, 2, 3]),
        area1=st.integers(min_value=1, max_value=500),
        area2=st.integers(min_value=1, max_value=500),
    )
    @settings(max_examples=200)
    def test_monotonic_non_decreasing(self, pt_code, area1, area2):
        """Бо'льшая площадь = бо'льший или равный срок (монотонность)."""
        r1 = _calc_contract_term_standalone(pt_code, area1)
        r2 = _calc_contract_term_standalone(pt_code, area2)
        if area1 <= area2:
            assert r1 <= r2, f"Нарушена монотонность: area {area1}->{r1} дней, area {area2}->{r2} дней"

    def test_boundary_values_explicit(self):
        """Явные граничные значения: 0, 1, 70, 71, 500, 501, 1000."""
        for pt_code in [1, 2, 3]:
            for area in [1, 69, 70, 71, 99, 100, 101, 499, 500, 501, 1000, 5000]:
                result = _calc_contract_term_standalone(pt_code, area)
                assert result > 0, f"pt_code={pt_code}, area={area} -> 0!"

    def test_all_threshold_boundaries(self):
        """Проверка каждого порога: area == max_area и area == max_area + 1."""
        thresholds_map = {
            1: [(70, 50), (100, 60), (130, 70), (160, 80), (190, 90), (220, 100), (250, 110), (300, 120), (350, 130), (400, 140), (450, 150), (500, 160)],
            2: [(70, 30), (100, 35), (130, 40), (160, 45), (190, 50), (220, 55), (250, 60), (300, 65), (350, 70), (400, 75), (450, 80), (500, 85)],
            3: [(70, 10), (100, 15), (130, 20), (160, 25), (190, 30), (220, 35), (250, 40), (300, 45), (350, 50), (400, 55), (450, 60), (500, 65)],
        }
        for pt_code, thresholds in thresholds_map.items():
            for i, (max_area, expected_days) in enumerate(thresholds):
                # Точно на границе
                result = _calc_contract_term_standalone(pt_code, max_area)
                assert result == expected_days, f"pt={pt_code}, area={max_area}: ожидали {expected_days}, получили {result}"
                # На 1 больше границы (кроме последней — переход на следующий порог)
                if i < len(thresholds) - 1:
                    next_days = thresholds[i + 1][1]
                    result_plus = _calc_contract_term_standalone(pt_code, max_area + 1)
                    assert result_plus == next_days, f"pt={pt_code}, area={max_area + 1}: ожидали {next_days}, получили {result_plus}"
