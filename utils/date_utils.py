# -*- coding: utf-8 -*-
"""
Утилиты для работы с датами
Единое форматирование дат в формате ДД.ММ.ГГГГ
"""

from datetime import datetime, timedelta
from PyQt5.QtCore import QDate, QDateTime

# Словарь для месяцев прописью
MONTHS_RU = {
    '01': 'январь',
    '02': 'февраль',
    '03': 'март',
    '04': 'апрель',
    '05': 'май',
    '06': 'июнь',
    '07': 'июль',
    '08': 'август',
    '09': 'сентябрь',
    '10': 'октябрь',
    '11': 'ноябрь',
    '12': 'декабрь'
}


def format_date(date_value, default='—'):
    """
    Форматирует дату в формат ДД.ММ.ГГГГ (без времени)

    Args:
        date_value: Может быть строкой, QDate, QDateTime, datetime или None
        default: Значение по умолчанию, если дата пустая

    Returns:
        str: Отформатированная дата в формате ДД.ММ.ГГГГ или значение по умолчанию
    """
    if not date_value:
        return default

    try:
        # Если это QDateTime
        if isinstance(date_value, QDateTime):
            return date_value.date().toString('dd.MM.yyyy')

        # Если это QDate
        if isinstance(date_value, QDate):
            return date_value.toString('dd.MM.yyyy')

        # Если это datetime
        if isinstance(date_value, datetime):
            return date_value.strftime('%d.%m.%Y')

        # Если это строка
        if isinstance(date_value, str):
            # Удаляем время если есть (берем только первые 10 символов для yyyy-MM-dd)
            date_str = date_value.strip()

            if not date_str:
                return default

            # Пытаемся распарсить разные форматы
            formats_to_try = [
                '%Y-%m-%d %H:%M:%S',  # yyyy-MM-dd HH:MM:SS
                '%Y-%m-%d',           # yyyy-MM-dd
                '%d.%m.%Y',           # dd.MM.yyyy (уже в нужном формате)
                '%d/%m/%Y',           # dd/MM/yyyy
                '%Y/%m/%d',           # yyyy/MM/dd
            ]

            for fmt in formats_to_try:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime('%d.%m.%Y')
                except ValueError:
                    continue

            # Если не удалось распарсить, пробуем взять только дату (первые 10 символов)
            if len(date_str) >= 10:
                try:
                    date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')
                    return date_obj.strftime('%d.%m.%Y')
                except ValueError:
                    pass

            # Если ничего не помогло, возвращаем исходную строку обрезанную
            return date_str[:10] if len(date_str) >= 10 else date_str

    except Exception as e:
        print(f"[WARN] Ошибка форматирования даты '{date_value}': {e}")
        return default

    return default


def format_datetime(datetime_value, default='—'):
    """
    Форматирует дату и время в формат ДД.ММ.ГГГГ ЧЧ:ММ

    Args:
        datetime_value: Может быть строкой, QDateTime, datetime или None
        default: Значение по умолчанию, если дата пустая

    Returns:
        str: Отформатированная дата со временем или значение по умолчанию
    """
    if not datetime_value:
        return default

    try:
        # Если это QDateTime
        if isinstance(datetime_value, QDateTime):
            return datetime_value.toString('dd.MM.yyyy HH:mm')

        # Если это datetime
        if isinstance(datetime_value, datetime):
            return datetime_value.strftime('%d.%m.%Y %H:%M')

        # Если это строка
        if isinstance(datetime_value, str):
            date_str = datetime_value.strip()

            if not date_str:
                return default

            # Пытаемся распарсить
            formats_to_try = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
            ]

            for fmt in formats_to_try:
                try:
                    dt_obj = datetime.strptime(date_str, fmt)
                    # Если нет времени, не показываем его
                    if fmt == '%Y-%m-%d':
                        return dt_obj.strftime('%d.%m.%Y')
                    return dt_obj.strftime('%d.%m.%Y %H:%M')
                except ValueError:
                    continue

            return date_str

    except Exception as e:
        print(f"[WARN] Ошибка форматирования даты-времени '{datetime_value}': {e}")
        return default

    return default


def format_month_year(month_value, default='—'):
    """
    Форматирует месяц из формата ГГГГ-ММ в формат "месяц ГГГГ"

    Args:
        month_value: Строка в формате "ГГГГ-ММ" (например, "2025-11")
        default: Значение по умолчанию, если месяц пустой

    Returns:
        str: Отформатированный месяц (например, "ноябрь 2025") или значение по умолчанию

    Examples:
        >>> format_month_year("2025-11")
        "ноябрь 2025"
        >>> format_month_year("2024-01")
        "январь 2024"
    """
    if not month_value:
        return default

    try:
        month_str = str(month_value).strip()

        if not month_str or month_str == '-':
            return default

        # Проверяем формат ГГГГ-ММ
        if '-' in month_str and len(month_str) == 7:
            year, month = month_str.split('-')

            # Получаем название месяца из словаря
            month_name = MONTHS_RU.get(month, None)

            if month_name:
                return f"{month_name} {year}"

        # Если формат не подошел, возвращаем исходную строку
        return month_str

    except Exception as e:
        print(f"[WARN] Ошибка форматирования месяца '{month_value}': {e}")
        return default


# Список праздничных дней России (нерабочие дни)
# Формат: (месяц, день)
RUSSIAN_HOLIDAYS = [
    (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8),  # Новогодние праздники
    (2, 23),  # День защитника Отечества
    (3, 8),   # Международный женский день
    (5, 1),   # Праздник Весны и Труда
    (5, 9),   # День Победы
    (6, 12),  # День России
    (11, 4),  # День народного единства
]


def is_working_day(date):
    """
    Проверяет, является ли день рабочим

    Args:
        date: datetime объект

    Returns:
        bool: True если рабочий день, False если выходной или праздник
    """
    # Проверяем выходные (суббота=5, воскресенье=6)
    if date.weekday() in [5, 6]:
        return False

    # Проверяем праздники
    if (date.month, date.day) in RUSSIAN_HOLIDAYS:
        return False

    return True


def add_working_days(start_date, working_days):
    """
    Добавляет указанное количество рабочих дней к дате

    Args:
        start_date: Начальная дата (datetime, str в формате 'YYYY-MM-DD', или QDate)
        working_days: Количество рабочих дней для добавления

    Returns:
        datetime: Результирующая дата
    """
    # Конвертируем start_date в datetime если нужно
    if isinstance(start_date, str):
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
    elif isinstance(start_date, QDate):
        current_date = datetime(start_date.year(), start_date.month(), start_date.day())
    elif isinstance(start_date, datetime):
        current_date = start_date
    else:
        raise ValueError(f"Неподдерживаемый тип даты: {type(start_date)}")

    # Добавляем рабочие дни
    days_added = 0
    while days_added < working_days:
        current_date += timedelta(days=1)
        if is_working_day(current_date):
            days_added += 1

    return current_date


def calculate_deadline(contract_date, survey_date, tech_task_date, contract_period):
    """
    Рассчитывает общий дедлайн проекта

    Логика:
    1. Определяет самую позднюю из дат: contract_date, survey_date, tech_task_date
    2. К этой дате добавляет contract_period рабочих дней

    Args:
        contract_date: Дата заключения договора (datetime, str, или QDate)
        survey_date: Дата замера (datetime, str, QDate, или None)
        tech_task_date: Дата ТЗ (datetime, str, QDate, или None)
        contract_period: Количество рабочих дней по договору

    Returns:
        datetime: Рассчитанный дедлайн или None если невозможно рассчитать
    """
    # Конвертируем все даты в datetime
    dates = []

    # Дата договора (обязательная)
    if contract_date:
        if isinstance(contract_date, str):
            try:
                dates.append(datetime.strptime(contract_date, '%Y-%m-%d'))
            except:
                pass
        elif isinstance(contract_date, QDate):
            dates.append(datetime(contract_date.year(), contract_date.month(), contract_date.day()))
        elif isinstance(contract_date, datetime):
            dates.append(contract_date)

    # Дата замера (опциональная)
    if survey_date:
        if isinstance(survey_date, str):
            try:
                dates.append(datetime.strptime(survey_date, '%Y-%m-%d'))
            except:
                pass
        elif isinstance(survey_date, QDate):
            dates.append(datetime(survey_date.year(), survey_date.month(), survey_date.day()))
        elif isinstance(survey_date, datetime):
            dates.append(survey_date)

    # Дата ТЗ (опциональная)
    if tech_task_date:
        if isinstance(tech_task_date, str):
            try:
                dates.append(datetime.strptime(tech_task_date, '%Y-%m-%d'))
            except:
                pass
        elif isinstance(tech_task_date, QDate):
            dates.append(datetime(tech_task_date.year(), tech_task_date.month(), tech_task_date.day()))
        elif isinstance(tech_task_date, datetime):
            dates.append(tech_task_date)

    # Если нет дат, возвращаем None
    if not dates:
        return None

    # Если нет срока договора, возвращаем None
    if not contract_period or contract_period <= 0:
        return None

    # Находим максимальную дату
    latest_date = max(dates)

    # Добавляем рабочие дни
    deadline = add_working_days(latest_date, contract_period)

    return deadline
