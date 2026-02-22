# -*- coding: utf-8 -*-
"""
Чистые функции расчёта для таймлайна проекта.
Без зависимостей от PyQt5 — можно использовать в тестах.
"""
from utils.calendar_helpers import add_working_days


def calc_planned_dates(entries):
    """Рассчитать планируемые даты для каждого подэтапа.
    Логика: planned[START] = START.actual_date
            planned[N] = prev_date + norm_days[N]
    prev_date = actual_date (если заполнена) или planned_date предыдущего.
    Результат сохраняется в entry['_planned_date'] (строка 'YYYY-MM-DD').
    """
    prev_date = ''
    for entry in entries:
        role = entry.get('executor_role', '')
        if role == 'header':
            continue
        stage_code = entry.get('stage_code', '')
        if stage_code == 'START':
            prev_date = entry.get('actual_date', '')
            entry['_planned_date'] = prev_date
            continue
        norm = entry.get('norm_days', 0) or 0
        actual = entry.get('actual_date', '')
        if prev_date and norm > 0:
            entry['_planned_date'] = add_working_days(prev_date, norm)
        else:
            entry['_planned_date'] = ''
        if actual:
            prev_date = actual
        elif entry.get('_planned_date'):
            prev_date = entry['_planned_date']
    return entries
