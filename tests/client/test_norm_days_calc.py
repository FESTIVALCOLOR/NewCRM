# -*- coding: utf-8 -*-
"""
Тесты для модульных функций ui/norm_days_settings_widget.py:
_get_areas_for_subtype, _calc_contract_term,
_build_individual_template, _build_template_template, _distribute_norm_days.

Чистые функции — PyQt5 не нужен.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ui.norm_days_settings_widget import (
    _get_areas_for_subtype,
    _calc_contract_term,
    _build_individual_template,
    _build_template_template,
    _distribute_norm_days,
    _SUBTYPES,
    _AREAS_INDIVIDUAL,
    _AREAS_TEMPLATE,
    _AREAS_BATHROOM,
)


# ==================== _get_areas_for_subtype ====================

class TestGetAreasForSubtype:
    """_get_areas_for_subtype — шкала площадей."""

    def test_individual_returns_individual_areas(self):
        """Индивидуальный проект — шкала индивидуальных площадей."""
        result = _get_areas_for_subtype('Индивидуальный', 'Полный (с 3д визуализацией)')
        assert result == _AREAS_INDIVIDUAL

    def test_individual_any_subtype_same(self):
        """Индивидуальный — подтип не влияет на шкалу."""
        r1 = _get_areas_for_subtype('Индивидуальный', 'Полный (с 3д визуализацией)')
        r2 = _get_areas_for_subtype('Индивидуальный', 'Планировочный')
        assert r1 == r2

    def test_template_standard_returns_template_areas(self):
        """Шаблонный Стандарт — шкала шаблонных площадей."""
        result = _get_areas_for_subtype('Шаблонный', 'Стандарт')
        assert result == _AREAS_TEMPLATE

    def test_template_bathroom_returns_empty(self):
        """Шаблонный ванная — пустая шкала (фиксированный срок)."""
        result = _get_areas_for_subtype('Шаблонный', 'Проект ванной комнаты')
        assert result == _AREAS_BATHROOM
        assert result == []

    def test_template_bathroom_with_viz_returns_empty(self):
        """Шаблонный ванная с визуализацией — тоже пустая шкала."""
        result = _get_areas_for_subtype('Шаблонный', 'Проект ванной комнаты с визуализацией')
        assert result == []

    def test_template_standard_viz_returns_template_areas(self):
        """Шаблонный Стандарт с визуализацией — шкала шаблонных."""
        result = _get_areas_for_subtype('Шаблонный', 'Стандарт с визуализацией')
        assert result == _AREAS_TEMPLATE


# ==================== _calc_contract_term ====================

class TestCalcContractTerm:
    """_calc_contract_term — расчёт срока договора."""

    # --- Индивидуальный Полный ---
    def test_individual_full_70(self):
        assert _calc_contract_term('Индивидуальный', 'Полный (с 3д визуализацией)', 70) == 50

    def test_individual_full_100(self):
        assert _calc_contract_term('Индивидуальный', 'Полный (с 3д визуализацией)', 100) == 60

    def test_individual_full_500(self):
        assert _calc_contract_term('Индивидуальный', 'Полный (с 3д визуализацией)', 500) == 160

    def test_individual_full_over_500(self):
        """Площадь > 500 — возвращает 0 (нет порога)."""
        assert _calc_contract_term('Индивидуальный', 'Полный (с 3д визуализацией)', 600) == 0

    # --- Индивидуальный Эскизный ---
    def test_individual_sketch_70(self):
        assert _calc_contract_term('Индивидуальный', 'Эскизный (с коллажами)', 70) == 30

    def test_individual_sketch_250(self):
        assert _calc_contract_term('Индивидуальный', 'Эскизный (с коллажами)', 250) == 60

    # --- Индивидуальный Планировочный ---
    def test_individual_planning_70(self):
        assert _calc_contract_term('Индивидуальный', 'Планировочный', 70) == 10

    def test_individual_planning_300(self):
        assert _calc_contract_term('Индивидуальный', 'Планировочный', 300) == 45

    # --- Шаблонный Стандарт ---
    def test_template_standard_90(self):
        assert _calc_contract_term('Шаблонный', 'Стандарт', 90) == 20

    def test_template_standard_140(self):
        """area=140: base = 20 + ((140-90-1)//50 + 1)*10 = 20 + 10 = 30."""
        assert _calc_contract_term('Шаблонный', 'Стандарт', 140) == 30

    def test_template_standard_290(self):
        """area=290: base = 20 + ((290-90-1)//50 + 1)*10 = 20 + 40 = 60."""
        assert _calc_contract_term('Шаблонный', 'Стандарт', 290) == 60

    # --- Шаблонный Стандарт с визуализацией ---
    def test_template_standard_viz_90(self):
        """area=90: base=20, +25 за визуализацию = 45."""
        assert _calc_contract_term('Шаблонный', 'Стандарт с визуализацией', 90) == 45

    def test_template_standard_viz_140(self):
        """area=140: base=30, +25 + ((140-90-1)//50 + 1)*15 = +40 = 70."""
        assert _calc_contract_term('Шаблонный', 'Стандарт с визуализацией', 140) == 70

    # --- Шаблонный Ванная ---
    def test_template_bathroom_no_viz(self):
        assert _calc_contract_term('Шаблонный', 'Проект ванной комнаты', 0) == 10

    def test_template_bathroom_with_viz(self):
        assert _calc_contract_term('Шаблонный', 'Проект ванной комнаты с визуализацией', 0) == 20

    # --- Граничные значения ---
    def test_individual_exact_threshold(self):
        """Площадь ровно на пороге — берёт этот порог."""
        assert _calc_contract_term('Индивидуальный', 'Полный (с 3д визуализацией)', 130) == 70


# ==================== _build_individual_template ====================

class TestBuildIndividualTemplate:
    """_build_individual_template — генерация шаблона нормо-дней."""

    def test_returns_tuple(self):
        result = _build_individual_template('Полный (с 3д визуализацией)', 100)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_entries_is_list(self):
        entries, _ = _build_individual_template('Полный (с 3д визуализацией)', 100)
        assert isinstance(entries, list)
        assert len(entries) > 0

    def test_contract_term_matches(self):
        """Срок договора совпадает с _calc_contract_term."""
        _, term = _build_individual_template('Полный (с 3д визуализацией)', 100)
        expected = _calc_contract_term('Индивидуальный', 'Полный (с 3д визуализацией)', 100)
        assert term == expected

    def test_entries_have_required_keys(self):
        entries, _ = _build_individual_template('Полный (с 3д визуализацией)', 100)
        required_keys = {'stage_code', 'stage_name', 'stage_group', 'substage_group',
                         'executor_role', 'is_in_contract_scope', 'sort_order', 'norm_days'}
        for e in entries:
            assert required_keys.issubset(e.keys()), f"Не хватает ключей: {required_keys - e.keys()}"

    def test_planning_subtype_filters_stages(self):
        """Планировочный — только STAGE1 и START."""
        entries, _ = _build_individual_template('Планировочный', 100)
        groups = {e['stage_group'] for e in entries}
        assert groups <= {'START', 'STAGE1'}

    def test_sketch_subtype_includes_stage2_moodboard(self):
        """Эскизный — STAGE2 только мудборды (Подэтап 2.1)."""
        entries, _ = _build_individual_template('Эскизный (с коллажами)', 100)
        stage2_entries = [e for e in entries if e['stage_group'] == 'STAGE2'
                         and e['executor_role'] != 'header']
        for e in stage2_entries:
            assert e['substage_group'] == 'Подэтап 2.1', f"Нежелательная запись STAGE2: {e['stage_name']}"

    def test_full_subtype_has_all_stages(self):
        """Полный — все 3 этапа."""
        entries, _ = _build_individual_template('Полный (с 3д визуализацией)', 100)
        groups = {e['stage_group'] for e in entries}
        assert 'STAGE1' in groups
        assert 'STAGE2' in groups
        assert 'STAGE3' in groups

    def test_sort_order_sequential(self):
        entries, _ = _build_individual_template('Полный (с 3д визуализацией)', 100)
        orders = [e['sort_order'] for e in entries]
        assert orders == list(range(1, len(entries) + 1))

    def test_norm_days_sum_equals_term(self):
        """Сумма norm_days in_scope == contract_term."""
        entries, term = _build_individual_template('Полный (с 3д визуализацией)', 100)
        in_scope_sum = sum(
            e['norm_days'] for e in entries
            if e['is_in_contract_scope'] and e['executor_role'] != 'header' and e.get('raw_norm_days', 0) > 0
        )
        assert in_scope_sum == term


# ==================== _build_template_template ====================

class TestBuildTemplateTemplate:
    """_build_template_template — шаблонный проект."""

    def test_returns_tuple(self):
        result = _build_template_template('Стандарт', 90)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_standard_has_stage1_and_stage2(self):
        entries, _ = _build_template_template('Стандарт', 90)
        groups = {e['stage_group'] for e in entries}
        assert 'STAGE1' in groups
        assert 'STAGE2' in groups

    def test_standard_no_stage3(self):
        """Стандарт без визуализации — нет STAGE3."""
        entries, _ = _build_template_template('Стандарт', 90)
        groups = {e['stage_group'] for e in entries}
        assert 'STAGE3' not in groups

    def test_standard_viz_has_stage3(self):
        """Стандарт с визуализацией — есть STAGE3."""
        entries, _ = _build_template_template('Стандарт с визуализацией', 90)
        groups = {e['stage_group'] for e in entries}
        assert 'STAGE3' in groups

    def test_contract_term_matches_calc(self):
        _, term = _build_template_template('Стандарт', 140)
        expected = _calc_contract_term('Шаблонный', 'Стандарт', 140)
        assert term == expected

    def test_norm_days_sum_equals_term(self):
        entries, term = _build_template_template('Стандарт', 90)
        in_scope_sum = sum(
            e['norm_days'] for e in entries
            if e['is_in_contract_scope'] and e['executor_role'] != 'header' and e.get('raw_norm_days', 0) > 0
        )
        assert in_scope_sum == term

    def test_bathroom_fixed_term(self):
        _, term = _build_template_template('Проект ванной комнаты', 0)
        assert term == 10

    def test_bathroom_viz_fixed_term(self):
        _, term = _build_template_template('Проект ванной комнаты с визуализацией', 0)
        assert term == 20


# ==================== _distribute_norm_days ====================

class TestDistributeNormDays:
    """_distribute_norm_days — пропорциональное распределение."""

    def test_simple_distribution(self):
        """Два этапа по 50% от 10 дней → 5+5."""
        entries = [
            {'raw_norm_days': 5, 'executor_role': 'Чертежник', 'is_in_contract_scope': True},
            {'raw_norm_days': 5, 'executor_role': 'Дизайнер', 'is_in_contract_scope': True},
        ]
        _distribute_norm_days(entries, 10)
        total = sum(e['norm_days'] for e in entries)
        assert total == 10

    def test_headers_get_zero(self):
        """Заголовки всегда получают 0."""
        entries = [
            {'raw_norm_days': 0, 'executor_role': 'header', 'is_in_contract_scope': False},
            {'raw_norm_days': 10, 'executor_role': 'Чертежник', 'is_in_contract_scope': True},
        ]
        _distribute_norm_days(entries, 20)
        assert entries[0]['norm_days'] == 0

    def test_out_of_scope_keeps_raw(self):
        """Этапы вне scope → round(raw_norm_days), но >= 1."""
        entries = [
            {'raw_norm_days': 3, 'executor_role': 'Клиент', 'is_in_contract_scope': False},
            {'raw_norm_days': 5, 'executor_role': 'Чертежник', 'is_in_contract_scope': True},
        ]
        _distribute_norm_days(entries, 10)
        assert entries[0]['norm_days'] == 3  # round(3) = 3

    def test_minimum_one_day(self):
        """Каждая in_scope запись получает минимум 1 день."""
        entries = [
            {'raw_norm_days': 1, 'executor_role': 'Чертежник', 'is_in_contract_scope': True},
            {'raw_norm_days': 100, 'executor_role': 'Дизайнер', 'is_in_contract_scope': True},
        ]
        _distribute_norm_days(entries, 5)
        assert entries[0]['norm_days'] >= 1

    def test_zero_contract_term(self):
        """contract_term=0 — не падает."""
        entries = [
            {'raw_norm_days': 5, 'executor_role': 'Чертежник', 'is_in_contract_scope': True},
        ]
        _distribute_norm_days(entries, 0)
        # Не должен упасть

    def test_empty_entries(self):
        """Пустой список — не падает."""
        _distribute_norm_days([], 10)


# ==================== Константы ====================

class TestConstants:
    """Проверка констант модуля."""

    def test_subtypes_has_individual(self):
        assert 'Индивидуальный' in _SUBTYPES

    def test_subtypes_has_template(self):
        assert 'Шаблонный' in _SUBTYPES

    def test_individual_has_3_subtypes(self):
        assert len(_SUBTYPES['Индивидуальный']) == 3

    def test_template_has_4_subtypes(self):
        assert len(_SUBTYPES['Шаблонный']) == 4

    def test_areas_individual_sorted(self):
        assert _AREAS_INDIVIDUAL == sorted(_AREAS_INDIVIDUAL)

    def test_areas_template_sorted(self):
        assert _AREAS_TEMPLATE == sorted(_AREAS_TEMPLATE)
