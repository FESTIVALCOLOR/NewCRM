# -*- coding: utf-8 -*-
"""
Тесты workflow дедлайнов и таймлайна (Фазы 1-5).

Покрытие:
  - TestResolveStageGroup (3) — маппинг колонок → stage_group
  - TestAddBusinessDays (4) — расчёт рабочих дней (серверная логика)
  - TestDeadlineUpdateLogic (3) — логика обновления дедлайна при workflow
  - TestTimelineDeviation (3) — расчёт отклонения с причинами
  - TestSupervisionPlanDate (2) — авторасчёт plan_date надзора
ИТОГО: 15 тестов
"""

import re
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# --- Копии серверных функций (без зависимостей от FastAPI/SQLAlchemy) ---

def _add_business_days(start_date, days: int):
    """Добавить рабочие дни (пн-пт) к дате. Копия из crm_router.py:33."""
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    current = start_date
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def _resolve_stage_group(column_name: str) -> str:
    """Маппинг колонки → stage_group. Копия из crm_router.py:1189."""
    col = column_name.lower()
    m = re.search(r'стадия\s*(\d+)', col)
    if m:
        return f'STAGE{m.group(1)}'
    if 'планировочн' in col:
        return 'STAGE1'
    elif 'концепция' in col or 'дизайн' in col:
        return 'STAGE2'
    elif 'чертеж' in col or 'чертёж' in col:
        return 'STAGE3'
    return ''


def _calc_supervision_plan_dates(start_str, deadline_str, n_stages=12):
    """Авторасчёт plan_date. Копия из supervision_timeline_router.py."""
    plan_dates = {}
    if start_str and deadline_str:
        try:
            start_dt = datetime.strptime(start_str, '%Y-%m-%d')
            deadline_dt = datetime.strptime(deadline_str, '%Y-%m-%d')
            total_days = (deadline_dt - start_dt).days
            if total_days > 0 and n_stages > 0:
                for i in range(n_stages):
                    stage_end = start_dt + timedelta(days=int(total_days * (i + 1) / n_stages))
                    plan_dates[i] = stage_end.strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            pass
    return plan_dates


def _calc_deviation_reasons(entries):
    """Расчёт отклонения. Копия из timeline_widget._build_display_rows."""
    deviation_reasons = []
    for e in entries:
        if e.get('executor_role', '') == 'header':
            continue
        ad = e.get('actual_days', 0) or 0
        if ad <= 0:
            continue
        effective_norm = e.get('custom_norm_days') or e.get('norm_days', 0) or 0
        if effective_norm <= 0:
            continue
        diff = ad - effective_norm
        if diff != 0:
            name = e.get('stage_name', e.get('stage_code', '?'))
            deviation_reasons.append({'name': name, 'diff': diff})
    return deviation_reasons


def _find_next_substep(entries, stage_group):
    """Логика выбора следующего подэтапа из _update_executor_deadline_for_next_substep."""
    for e in entries:
        if (e.get('stage_group') == stage_group
                and e.get('executor_role') != 'header'
                and not e.get('actual_date')
                and e.get('status') != 'skipped'
                and (e.get('norm_days', 0) or 0) > 0):
            return e
    return None


def _calc_new_deadline(entries, stage_group, stage_name):
    """Полная логика обновления дедлайна (без БД)."""
    sg = _resolve_stage_group(stage_name)
    if not sg:
        return None

    next_entry = _find_next_substep(entries, sg)
    if not next_entry:
        return None

    # Out-of-scope пауза
    if not next_entry.get('is_in_contract_scope', True):
        return None

    norm = next_entry.get('norm_days', 0) or 0
    custom = next_entry.get('custom_norm_days')
    if custom and custom > 0:
        norm = custom
    if norm <= 0:
        return None

    # Ищем prev_actual_date
    prev_date = None
    for e in entries:
        if e.get('executor_role') == 'header':
            continue
        if e.get('sort_order', 0) < next_entry.get('sort_order', 0) and e.get('actual_date'):
            prev_date = e['actual_date']

    base = prev_date or datetime.utcnow().strftime('%Y-%m-%d')
    result = _add_business_days(base, norm)
    return result.strftime('%Y-%m-%d')


# =====================================================================
# Тест 1-3: _resolve_stage_group
# =====================================================================

class TestResolveStageGroup:
    """Маппинг имени колонки канбана → stage_group."""

    def test_stage_number_pattern(self):
        """'Стадия 2 ...' → STAGE2."""
        assert _resolve_stage_group('Стадия 2 — Концепция дизайна') == 'STAGE2'
        assert _resolve_stage_group('стадия 1 Планировка') == 'STAGE1'
        assert _resolve_stage_group('Стадия 3') == 'STAGE3'

    def test_alternative_names(self):
        """Альтернативные названия → правильный маппинг."""
        assert _resolve_stage_group('Планировочные решения') == 'STAGE1'
        assert _resolve_stage_group('Концепция') == 'STAGE2'
        assert _resolve_stage_group('Рабочие чертежи') == 'STAGE3'

    def test_unknown_column(self):
        """Неизвестная колонка → пустая строка."""
        assert _resolve_stage_group('В ожидании') == ''
        assert _resolve_stage_group('Архив') == ''
        assert _resolve_stage_group('') == ''


# =====================================================================
# Тест 4-7: _add_business_days
# =====================================================================

class TestAddBusinessDays:
    """Расчёт рабочих дней (серверная логика)."""

    def test_basic_weekdays(self):
        """Понедельник + 5 рабочих дней = следующий понедельник."""
        result = _add_business_days('2026-03-02', 5)  # Пн
        assert result.strftime('%Y-%m-%d') == '2026-03-09'

    def test_skip_weekend(self):
        """Пятница + 1 рабочий день = понедельник."""
        result = _add_business_days('2026-03-06', 1)  # Пт
        assert result.weekday() == 0  # Понедельник
        assert result.strftime('%Y-%m-%d') == '2026-03-09'

    def test_string_input(self):
        """Принимает строку 'YYYY-MM-DD'."""
        result = _add_business_days('2026-03-02', 2)
        assert isinstance(result, datetime)
        assert result.strftime('%Y-%m-%d') == '2026-03-04'

    def test_zero_days(self):
        """0 дней → исходная дата."""
        result = _add_business_days('2026-03-02', 0)
        assert result.strftime('%Y-%m-%d') == '2026-03-02'


# =====================================================================
# Тест 8-10: Логика обновления дедлайна при workflow
# =====================================================================

class TestDeadlineUpdateLogic:
    """Логика определения следующего подэтапа и расчёта дедлайна."""

    def _make_entries(self):
        """Типичная стадия: Чертёж(4дн) → Проверка СДП(2дн) → Клиент(3дн, out-of-scope)."""
        return [
            {'sort_order': 1, 'executor_role': 'Чертежник', 'actual_date': '2026-03-02',
             'norm_days': 4, 'stage_name': 'Чертёж', 'stage_group': 'STAGE1',
             'status': '', 'is_in_contract_scope': True},
            {'sort_order': 2, 'executor_role': 'СДП', 'actual_date': '',
             'norm_days': 2, 'stage_name': 'Проверка СДП', 'stage_group': 'STAGE1',
             'status': '', 'is_in_contract_scope': True},
            {'sort_order': 3, 'executor_role': 'Клиент', 'actual_date': '',
             'norm_days': 3, 'stage_name': 'Согласование', 'stage_group': 'STAGE1',
             'status': '', 'is_in_contract_scope': False},
        ]

    def test_next_substep_after_submit(self):
        """После сдачи (Чертёж заполнен) → следующий = Проверка СДП."""
        entries = self._make_entries()
        deadline = _calc_new_deadline(entries, 'STAGE1', 'Стадия 1')
        assert deadline is not None
        # Дедлайн = prev_actual_date(2026-03-02) + 2 раб.дн = 2026-03-04
        assert deadline == '2026-03-04'

    def test_out_of_scope_pause(self):
        """Если следующий подэтап out-of-scope (Клиент) → дедлайн не обновляется."""
        entries = self._make_entries()
        # Заполняем Чертёж и Проверку
        entries[1]['actual_date'] = '2026-03-04'
        # Теперь next = Клиент (out-of-scope)
        deadline = _calc_new_deadline(entries, 'STAGE1', 'Стадия 1')
        assert deadline is None  # Пауза — не обновляем

    def test_all_completed_no_update(self):
        """Все подэтапы заполнены → дедлайн не обновляется."""
        entries = self._make_entries()
        entries[0]['actual_date'] = '2026-03-02'
        entries[1]['actual_date'] = '2026-03-04'
        entries[2]['actual_date'] = '2026-03-10'
        deadline = _calc_new_deadline(entries, 'STAGE1', 'Стадия 1')
        assert deadline is None  # Всё заполнено


# =====================================================================
# Тест 11-13: Расчёт отклонения таймлайна
# =====================================================================

class TestTimelineDeviation:
    """Расчёт отклонения факт vs норма с причинами."""

    def test_no_deviation(self):
        """Все подэтапы в срок → пустой список причин."""
        entries = [
            {'executor_role': 'Чертежник', 'actual_days': 4, 'norm_days': 4, 'stage_name': 'Чертёж'},
            {'executor_role': 'СДП', 'actual_days': 2, 'norm_days': 2, 'stage_name': 'Проверка'},
        ]
        assert _calc_deviation_reasons(entries) == []

    def test_positive_deviation(self):
        """Просрочка → положительное отклонение с причиной."""
        entries = [
            {'executor_role': 'Чертежник', 'actual_days': 6, 'norm_days': 4,
             'stage_name': 'Чертёж'},
            {'executor_role': 'СДП', 'actual_days': 2, 'norm_days': 2,
             'stage_name': 'Проверка'},
        ]
        result = _calc_deviation_reasons(entries)
        assert len(result) == 1
        assert result[0]['name'] == 'Чертёж'
        assert result[0]['diff'] == 2

    def test_custom_norm_days_in_deviation(self):
        """custom_norm_days приоритетнее norm_days при расчёте отклонения."""
        entries = [
            {'executor_role': 'Чертежник', 'actual_days': 5, 'norm_days': 4,
             'custom_norm_days': 5, 'stage_name': 'Чертёж'},
        ]
        # actual_days=5, effective_norm=custom_norm_days=5 → diff=0
        result = _calc_deviation_reasons(entries)
        assert result == []


# =====================================================================
# Тест 14-15: Авторасчёт plan_date надзора
# =====================================================================

class TestSupervisionPlanDate:
    """Авторасчёт plan_date при инициализации timeline надзора."""

    def test_even_distribution(self):
        """12 стадий за 120 дней → каждые 10 дней."""
        result = _calc_supervision_plan_dates('2026-03-01', '2026-06-29', 12)
        assert len(result) == 12
        # Первая стадия ≈ +10 дней
        assert result[0] == '2026-03-11'
        # Последняя стадия = дедлайн
        assert result[11] == '2026-06-29'
        # Порядок хронологический
        dates = [result[i] for i in range(12)]
        assert dates == sorted(dates)

    def test_no_dates_without_deadline(self):
        """Без дедлайна → пустой словарь plan_dates."""
        result = _calc_supervision_plan_dates('2026-03-01', '', 12)
        assert result == {}
        result2 = _calc_supervision_plan_dates('', '2026-06-01', 12)
        assert result2 == {}
        result3 = _calc_supervision_plan_dates('', '', 12)
        assert result3 == {}
