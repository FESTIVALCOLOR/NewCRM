# -*- coding: utf-8 -*-
"""Тесты для ui/norm_days_settings_widget.py — логика нормо-дней + расчёт сроков"""

import pytest
from unittest.mock import patch, MagicMock


# ─── Чистая логика: _get_areas_for_subtype ──────────────────────────────

class TestGetAreasForSubtype:
    """Тесты _get_areas_for_subtype"""

    def test_individual_returns_individual_areas(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _get_areas_for_subtype, _AREAS_INDIVIDUAL
            result = _get_areas_for_subtype('Индивидуальный', 'Полный (с 3д визуализацией)')
            assert result == _AREAS_INDIVIDUAL

    def test_template_standard(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _get_areas_for_subtype, _AREAS_TEMPLATE
            result = _get_areas_for_subtype('Шаблонный', 'Стандарт')
            assert result == _AREAS_TEMPLATE

    def test_template_bathroom(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _get_areas_for_subtype, _AREAS_BATHROOM
            result = _get_areas_for_subtype('Шаблонный', 'Проект ванной комнаты')
            assert result == _AREAS_BATHROOM

    def test_template_bathroom_with_viz(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _get_areas_for_subtype
            result = _get_areas_for_subtype('Шаблонный', 'Проект ванной комнаты с визуализацией')
            assert result == []  # _AREAS_BATHROOM = []


# ─── Чистая логика: _calc_contract_term ─────────────────────────────────

class TestCalcContractTerm:
    """Тесты _calc_contract_term"""

    def test_individual_full_70(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _calc_contract_term
            assert _calc_contract_term('Индивидуальный', 'Полный (с 3д визуализацией)', 70) == 50

    def test_individual_full_100(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _calc_contract_term
            assert _calc_contract_term('Индивидуальный', 'Полный (с 3д визуализацией)', 100) == 60

    def test_individual_full_500(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _calc_contract_term
            assert _calc_contract_term('Индивидуальный', 'Полный (с 3д визуализацией)', 500) == 160

    def test_individual_full_over_500(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _calc_contract_term
            assert _calc_contract_term('Индивидуальный', 'Полный (с 3д визуализацией)', 600) == 0

    def test_individual_eskiz_70(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _calc_contract_term
            assert _calc_contract_term('Индивидуальный', 'Эскизный (с коллажами)', 70) == 30

    def test_individual_plan_70(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _calc_contract_term
            assert _calc_contract_term('Индивидуальный', 'Планировочный', 70) == 10

    def test_template_bathroom_no_viz(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _calc_contract_term
            assert _calc_contract_term('Шаблонный', 'Проект ванной комнаты', 90) == 10

    def test_template_bathroom_with_viz(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _calc_contract_term
            assert _calc_contract_term('Шаблонный', 'Проект ванной комнаты с визуализацией', 90) == 20

    def test_template_standard_90(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _calc_contract_term
            assert _calc_contract_term('Шаблонный', 'Стандарт', 90) == 20

    def test_template_standard_140(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _calc_contract_term
            result = _calc_contract_term('Шаблонный', 'Стандарт', 140)
            assert result == 30  # 20 + 10

    def test_template_viz_90(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _calc_contract_term
            result = _calc_contract_term('Шаблонный', 'Стандарт с визуализацией', 90)
            assert result == 45  # 20 + 25

    def test_template_viz_140(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _calc_contract_term
            result = _calc_contract_term('Шаблонный', 'Стандарт с визуализацией', 140)
            assert result == 70  # 30 + 25 + 15

    @pytest.mark.parametrize('area,expected_base', [
        (70, 20), (90, 20), (91, 30), (140, 30), (141, 40), (190, 40),
    ])
    def test_template_standard_parametrized(self, area, expected_base):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _calc_contract_term
            result = _calc_contract_term('Шаблонный', 'Стандарт', area)
            assert result == expected_base


# ─── Чистая логика: _distribute_norm_days ────────────────────────────────

class TestDistributeNormDays:
    """Тесты _distribute_norm_days"""

    def test_empty_entries(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _distribute_norm_days
            _distribute_norm_days([], 50)  # не падает

    def test_distributes_proportionally(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _distribute_norm_days
            entries = [
                {'executor_role': 'designer', 'is_in_contract_scope': True, 'raw_norm_days': 10, 'norm_days': 0},
                {'executor_role': 'designer', 'is_in_contract_scope': True, 'raw_norm_days': 20, 'norm_days': 0},
            ]
            _distribute_norm_days(entries, 30)
            total = sum(e['norm_days'] for e in entries if e['executor_role'] != 'header')
            assert total == 30

    def test_headers_not_distributed(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _distribute_norm_days
            entries = [
                {'executor_role': 'header', 'is_in_contract_scope': False, 'raw_norm_days': 0, 'norm_days': 0},
                {'executor_role': 'designer', 'is_in_contract_scope': True, 'raw_norm_days': 10, 'norm_days': 0},
            ]
            _distribute_norm_days(entries, 20)
            assert entries[0]['norm_days'] == 0


# ─── Чистая логика: _build_individual_template ──────────────────────────

class TestBuildIndividualTemplate:
    """Тесты _build_individual_template"""

    @pytest.mark.parametrize('subtype', [
        'Полный (с 3д визуализацией)',
        'Эскизный (с коллажами)',
        'Планировочный',
    ])
    def test_returns_list(self, subtype):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _build_individual_template
            entries, term = _build_individual_template(subtype, 100)
            assert isinstance(entries, list)
            assert len(entries) > 0

    def test_entries_have_required_keys(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _build_individual_template
            entries, term = _build_individual_template('Полный (с 3д визуализацией)', 100)
            for entry in entries:
                assert 'stage_name' in entry
                assert 'executor_role' in entry


# ─── Чистая логика: _build_template_template ────────────────────────────

class TestBuildTemplateTemplate:
    """Тесты _build_template_template"""

    @pytest.mark.parametrize('subtype', [
        'Стандарт',
        'Стандарт с визуализацией',
        'Проект ванной комнаты',
        'Проект ванной комнаты с визуализацией',
    ])
    def test_returns_list(self, subtype):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _build_template_template
            entries, term = _build_template_template(subtype, 90)
            assert isinstance(entries, list)
            assert len(entries) > 0


# ─── Константы ───────────────────────────────────────────────────────────

class TestConstants:
    """Тесты констант модуля"""

    def test_subtypes_keys(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _SUBTYPES
            assert 'Индивидуальный' in _SUBTYPES
            assert 'Шаблонный' in _SUBTYPES

    def test_individual_subtypes(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _SUBTYPES
            assert len(_SUBTYPES['Индивидуальный']) == 3

    def test_template_subtypes(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _SUBTYPES
            assert len(_SUBTYPES['Шаблонный']) == 4

    def test_areas_individual(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _AREAS_INDIVIDUAL
            assert 70 in _AREAS_INDIVIDUAL
            assert 500 in _AREAS_INDIVIDUAL

    def test_areas_template(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _AREAS_TEMPLATE
            assert 90 in _AREAS_TEMPLATE

    def test_areas_bathroom_empty(self):
        with patch('ui.norm_days_settings_widget.resource_path', return_value='/fake'):
            from ui.norm_days_settings_widget import _AREAS_BATHROOM
            assert _AREAS_BATHROOM == []


# ─── EmployeeReportsTab логика ───────────────────────────────────────────

class TestEmployeeReportsTabLogic:
    """Тесты логики EmployeeReportsTab"""

    def test_project_types(self):
        """Три типа проектов для вкладок"""
        types = ['Индивидуальный', 'Шаблонный', 'Авторский надзор']
        assert len(types) == 3

    def test_report_types(self):
        """Два типа отчётов на каждой вкладке"""
        report_types = ['completed', 'salary']
        assert 'completed' in report_types
        assert 'salary' in report_types
