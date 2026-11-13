# -*- coding: utf-8 -*-
"""
Покрытие ui/contract_dialogs.py — статические методы расчёта сроков.
~30 тестов.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _get_calc_methods():
    """Импортировать статические методы расчёта из ContractDialog."""
    from ui.contract_dialogs import ContractDialog
    return ContractDialog._calc_contract_term, ContractDialog._calc_template_contract_term


# ==================== _calc_contract_term ====================

class TestCalcContractTerm:
    """Тестирует расчёт срока индивидуального проекта."""

    def test_full_project_70sqm(self):
        calc, _ = _get_calc_methods()
        assert calc(1, 70) == 50

    def test_full_project_100sqm(self):
        calc, _ = _get_calc_methods()
        assert calc(1, 100) == 60

    def test_full_project_250sqm(self):
        calc, _ = _get_calc_methods()
        assert calc(1, 250) == 110

    def test_full_project_500sqm(self):
        calc, _ = _get_calc_methods()
        assert calc(1, 500) == 160

    def test_full_project_over_500sqm_returns_max(self):
        calc, _ = _get_calc_methods()
        assert calc(1, 501) == 160

    def test_sketch_project_70sqm(self):
        calc, _ = _get_calc_methods()
        assert calc(2, 70) == 30

    def test_sketch_project_200sqm(self):
        calc, _ = _get_calc_methods()
        assert calc(2, 200) == 55

    def test_sketch_project_500sqm(self):
        calc, _ = _get_calc_methods()
        assert calc(2, 500) == 85

    def test_planning_project_70sqm(self):
        calc, _ = _get_calc_methods()
        assert calc(3, 70) == 10

    def test_planning_project_250sqm(self):
        calc, _ = _get_calc_methods()
        assert calc(3, 250) == 40

    def test_planning_project_500sqm(self):
        calc, _ = _get_calc_methods()
        assert calc(3, 500) == 65

    def test_small_area_all_types(self):
        calc, _ = _get_calc_methods()
        assert calc(1, 50) == 50  # <= 70
        assert calc(2, 50) == 30
        assert calc(3, 50) == 10

    def test_boundary_values(self):
        """Тест граничных значений — площадь ровно на пороге."""
        calc, _ = _get_calc_methods()
        # Полный: 130м² = 70 дней, 131м² = 80 дней
        assert calc(1, 130) == 70
        assert calc(1, 131) == 80


# ==================== _calc_template_contract_term ====================

class TestCalcTemplateContractTerm:
    """Тестирует расчёт срока шаблонного проекта."""

    def test_bathroom_without_viz(self):
        _, calc = _get_calc_methods()
        assert calc('Ванной комнаты', 10) == 10

    def test_bathroom_with_viz(self):
        _, calc = _get_calc_methods()
        assert calc('Ванной комнаты с визуализацией', 10) == 20

    def test_standard_small_area(self):
        _, calc = _get_calc_methods()
        # <= 90м² → 20 дней
        assert calc('Стандарт', 80) == 20

    def test_standard_91sqm(self):
        _, calc = _get_calc_methods()
        # 91м² → 20 + 10 = 30 (extra=1)
        assert calc('Стандарт', 91) == 30

    def test_standard_140sqm(self):
        _, calc = _get_calc_methods()
        # 140м² → extra = (140-90-1)//50 + 1 = 49//50 + 1 = 0+1 = 1 → 20+10=30
        assert calc('Стандарт', 140) == 30

    def test_standard_141sqm(self):
        _, calc = _get_calc_methods()
        # 141м² → extra = (141-90-1)//50 + 1 = 50//50 + 1 = 1+1 = 2 → 20+20=40
        assert calc('Стандарт', 141) == 40

    def test_standard_2_floors(self):
        _, calc = _get_calc_methods()
        # 80м² × 2 этажа → 20 + 10 (второй этаж <=90) = 30
        assert calc('Стандарт', 80, floors=2) == 30

    def test_standard_2_floors_large(self):
        _, calc = _get_calc_methods()
        # 141м² × 2 этажа → base=40, + 1 доп. этаж × 10 = 50
        assert calc('Стандарт', 141, floors=2) == 50

    def test_standard_with_viz_small(self):
        _, calc = _get_calc_methods()
        # <=90м² с визуализацией → 20 + 25 = 45
        assert calc('Стандарт с визуализацией', 80) == 45

    def test_standard_with_viz_large(self):
        _, calc = _get_calc_methods()
        # 141м² → base=40, viz: 25 + 2*15 = 55 → 95
        assert calc('Стандарт с визуализацией', 141) == 95

    def test_standard_1_floor_default(self):
        _, calc = _get_calc_methods()
        # floors=1 не добавляет дополнительных дней
        assert calc('Стандарт', 80, floors=1) == 20

    def test_bathroom_ignores_area(self):
        _, calc = _get_calc_methods()
        assert calc('Ванной комнаты', 5) == 10
        assert calc('Ванной комнаты', 50) == 10
        assert calc('Ванной комнаты', 200) == 10

    def test_returns_int(self):
        _, calc = _get_calc_methods()
        result = calc('Стандарт', 100)
        assert isinstance(result, int)
