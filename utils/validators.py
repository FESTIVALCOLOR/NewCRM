# -*- coding: utf-8 -*-
"""
Валидаторы для проверки входных данных
"""

import re
from datetime import datetime
from typing import Union, Optional


class ValidationError(Exception):
    """Исключение для ошибок валидации"""
    pass


def validate_phone(phone: str) -> bool:
    """
    Проверяет формат телефона

    Args:
        phone: Номер телефона

    Returns:
        True если формат правильный

    Raises:
        ValidationError: Если формат неверный
    """
    if not phone:
        raise ValidationError("Телефон не может быть пустым")

    # Формат: +7 (XXX) XXX-XX-XX
    pattern = r'^\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}$'

    if not re.match(pattern, phone):
        raise ValidationError(
            "Неверный формат телефона. Ожидается: +7 (XXX) XXX-XX-XX"
        )

    return True


def validate_email(email: str) -> bool:
    """
    Проверяет формат email

    Args:
        email: Адрес электронной почты

    Returns:
        True если формат правильный

    Raises:
        ValidationError: Если формат неверный
    """
    if not email:
        return True  # Email необязателен

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(pattern, email):
        raise ValidationError("Неверный формат email")

    return True


def validate_date(date_str: str, format_str: str = "%d.%m.%Y") -> bool:
    """
    Проверяет формат даты

    Args:
        date_str: Строка с датой
        format_str: Формат даты

    Returns:
        True если формат правильный

    Raises:
        ValidationError: Если формат неверный
    """
    if not date_str:
        return True  # Дата может быть необязательной

    try:
        datetime.strptime(date_str, format_str)
        return True
    except ValueError:
        raise ValidationError(f"Неверный формат даты. Ожидается: {format_str}")


def validate_required(value: any, field_name: str) -> bool:
    """
    Проверяет что поле заполнено

    Args:
        value: Значение поля
        field_name: Название поля для сообщения об ошибке

    Returns:
        True если поле заполнено

    Raises:
        ValidationError: Если поле пустое
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"Поле '{field_name}' обязательно для заполнения")

    return True


def validate_positive_number(value: Union[int, float], field_name: str) -> bool:
    """
    Проверяет что число положительное

    Args:
        value: Число для проверки
        field_name: Название поля

    Returns:
        True если число положительное

    Raises:
        ValidationError: Если число не положительное
    """
    if value is None:
        return True

    if not isinstance(value, (int, float)):
        raise ValidationError(f"Поле '{field_name}' должно быть числом")

    if value < 0:
        raise ValidationError(f"Поле '{field_name}' должно быть положительным числом")

    return True


def validate_inn(inn: str) -> bool:
    """
    Проверяет формат ИНН

    Args:
        inn: ИНН

    Returns:
        True если формат правильный

    Raises:
        ValidationError: Если формат неверный
    """
    if not inn:
        return True  # ИНН необязателен

    # ИНН юр. лица: 10 цифр, ИНН физ. лица: 12 цифр
    if not re.match(r'^\d{10}$|^\d{12}$', inn):
        raise ValidationError("ИНН должен содержать 10 или 12 цифр")

    return True


def validate_passport(passport: str) -> bool:
    """
    Проверяет формат паспорта

    Args:
        passport: Серия и номер паспорта

    Returns:
        True если формат правильный

    Raises:
        ValidationError: Если формат неверный
    """
    if not passport:
        return True  # Паспорт необязателен

    # Формат: XXXX XXXXXX (4 цифры серия, 6 цифр номер)
    if not re.match(r'^\d{4} \d{6}$', passport):
        raise ValidationError("Неверный формат паспорта. Ожидается: XXXX XXXXXX")

    return True


def validate_contract_number(number: str) -> bool:
    """
    Проверяет формат номера договора

    Args:
        number: Номер договора

    Returns:
        True если формат правильный

    Raises:
        ValidationError: Если формат неверный
    """
    if not number:
        raise ValidationError("Номер договора обязателен")

    # Формат: XX/XXXX (номер/год)
    if not re.match(r'^\d+/\d{4}$', number):
        raise ValidationError("Неверный формат номера договора. Ожидается: XX/XXXX")

    return True


def sanitize_string(value: str) -> str:
    """
    Очищает строку от опасных символов

    Args:
        value: Исходная строка

    Returns:
        Очищенная строка
    """
    if not value:
        return value

    # Удаляем HTML теги
    value = re.sub(r'<[^>]+>', '', value)

    # Экранируем специальные символы SQL
    value = value.replace("'", "''")

    return value.strip()


def format_phone(phone: str) -> str:
    """
    Форматирует номер телефона в стандартный вид

    Args:
        phone: Исходный номер

    Returns:
        Отформатированный номер
    """
    if not phone:
        return phone

    # Оставляем только цифры
    digits = re.sub(r'\D', '', phone)

    # Если начинается с 8, меняем на 7
    if digits.startswith('8') and len(digits) == 11:
        digits = '7' + digits[1:]

    # Форматируем
    if len(digits) == 11 and digits.startswith('7'):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"

    return phone


def format_passport(passport: str) -> str:
    """
    Форматирует номер паспорта

    Args:
        passport: Исходный номер

    Returns:
        Отформатированный номер
    """
    if not passport:
        return passport

    # Оставляем только цифры
    digits = re.sub(r'\D', '', passport)

    if len(digits) == 10:
        return f"{digits[:4]} {digits[4:]}"

    return passport
