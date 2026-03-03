"""
Серверные хелперы для работы с датами.
Чистый Python без клиентских зависимостей (PyQt5, utils/).
"""
from datetime import datetime, timedelta

# Праздничные дни России (нерабочие)
RUSSIAN_HOLIDAYS = [
    (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8),
    (2, 23), (3, 8), (5, 1), (5, 9), (6, 12), (11, 4),
]


def is_working_day(date):
    """Является ли день рабочим (не выходной, не праздник РФ)."""
    if date.weekday() in [5, 6]:
        return False
    if (date.month, date.day) in RUSSIAN_HOLIDAYS:
        return False
    return True


def networkdays(start_date, end_date):
    """Рабочие дни между двумя датами (с учётом праздников РФ)."""
    if not start_date or not end_date:
        return 0
    if isinstance(start_date, str):
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            return 0
    if isinstance(end_date, str):
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return 0
    if hasattr(start_date, 'date'):
        start_date = start_date.date()
    if hasattr(end_date, 'date'):
        end_date = end_date.date()
    if end_date < start_date:
        return 0
    count = 0
    current = start_date
    while current < end_date:
        if is_working_day(current):
            count += 1
        current += timedelta(days=1)
    return count
