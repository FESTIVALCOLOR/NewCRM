# -*- coding: utf-8 -*-
"""
Утилиты для безопасной работы с базой данных
Защита от SQL-инъекций
"""

# Whitelist разрешённых полей для каждой таблицы
ALLOWED_FIELDS = {
    'employees': {
        'full_name', 'phone', 'email', 'address', 'birth_date',
        'status', 'position', 'secondary_position', 'department',
        'login', 'password', 'role'
    },
    'clients': {
        'client_type', 'full_name', 'phone', 'email',
        'passport_series', 'passport_number', 'registration_address',
        'organization_name', 'inn', 'ogrn'
    },
    'contracts': {
        'client_id', 'project_type', 'agent_type', 'city',
        'contract_number', 'contract_date', 'address', 'area',
        'total_amount', 'advance_payment', 'additional_payment', 'third_payment',
        'contract_period', 'status', 'termination_reason'
    },
    'crm_cards': {
        'contract_id', 'column_name', 'deadline', 'tags',
        'is_approved', 'approval_stages', 'approval_deadline',
        'senior_manager_id', 'sdp_id', 'gap_id', 'manager_id',
        'surveyor_id', 'order_position'
    },
    'supervision_cards': {
        'contract_id', 'column_name', 'deadline', 'tags',
        'senior_manager_id', 'dan_id', 'dan_completed',
        'is_paused', 'pause_reason', 'paused_at'
    },
    'salaries': {
        'contract_id', 'employee_id', 'payment_type', 'stage_name',
        'amount', 'advance_payment', 'report_month'
    }
}


def validate_update_data(table_name: str, data: dict) -> dict:
    """
    Валидирует данные для UPDATE запроса

    Args:
        table_name: Название таблицы
        data: Словарь с данными для обновления

    Returns:
        Словарь с валидированными данными (только разрешённые поля)

    Raises:
        ValueError: Если таблица не найдена в whitelist
    """
    if table_name not in ALLOWED_FIELDS:
        raise ValueError(f"Таблица '{table_name}' не найдена в whitelist")

    allowed = ALLOWED_FIELDS[table_name]
    validated = {k: v for k, v in data.items() if k in allowed}

    # Предупреждаем о пропущенных полях
    skipped = set(data.keys()) - set(validated.keys())
    if skipped:
        print(f"[WARN]️ Пропущены неразрешённые поля: {', '.join(skipped)}")

    return validated


def build_update_query(table_name: str, data: dict, where_clause: str = "id = ?") -> tuple:
    """
    Безопасно создаёт UPDATE запрос с whitelist валидацией

    Args:
        table_name: Название таблицы
        data: Словарь с данными для обновления
        where_clause: WHERE условие (по умолчанию "id = ?")

    Returns:
        Tuple (sql_query, values) для execute()

    Example:
        query, values = build_update_query('clients', {'full_name': 'Иван', 'phone': '+7...'})
        cursor.execute(query, values + [client_id])
    """
    # Валидируем данные
    validated_data = validate_update_data(table_name, data)

    if not validated_data:
        raise ValueError("Нет данных для обновления после валидации")

    # Строим SET часть
    set_clause = ', '.join([f'{key} = ?' for key in validated_data.keys()])
    values = list(validated_data.values())

    # Формируем запрос
    query = f'UPDATE {table_name} SET {set_clause} WHERE {where_clause}'

    return query, values


def build_insert_query(table_name: str, data: dict) -> tuple:
    """
    Безопасно создаёт INSERT запрос с whitelist валидацией

    Args:
        table_name: Название таблицы
        data: Словарь с данными для вставки

    Returns:
        Tuple (sql_query, values) для execute()

    Example:
        query, values = build_insert_query('clients', {'full_name': 'Иван', 'phone': '+7...'})
        cursor.execute(query, values)
    """
    # Валидируем данные
    validated_data = validate_update_data(table_name, data)

    if not validated_data:
        raise ValueError("Нет данных для вставки после валидации")

    # Строим запрос
    columns = ', '.join(validated_data.keys())
    placeholders = ', '.join(['?' for _ in validated_data])
    values = list(validated_data.values())

    query = f'INSERT INTO {table_name} ({columns}) VALUES ({placeholders})'

    return query, values


def sanitize_table_name(table_name: str) -> str:
    """
    Проверяет безопасность имени таблицы

    Args:
        table_name: Название таблицы

    Returns:
        Валидированное имя таблицы

    Raises:
        ValueError: Если имя таблицы небезопасно
    """
    import re

    # Проверяем на допустимые символы (буквы, цифры, подчёркивание)
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        raise ValueError(f"Недопустимое имя таблицы: {table_name}")

    # Дополнительно проверяем через whitelist
    if table_name not in ALLOWED_FIELDS:
        raise ValueError(f"Таблица '{table_name}' не разрешена")

    return table_name


# Тестирование
if __name__ == '__main__':
    print("=== Тест модуля db_security ===\n")

    # Тест 1: Валидация данных
    print("1. Валидация данных:")
    test_data = {
        'full_name': 'Иван Иванов',
        'phone': '+7 (999) 123-45-67',
        'malicious_field': 'DROP TABLE clients'
    }

    validated = validate_update_data('clients', test_data)
    print(f"   Исходные поля: {list(test_data.keys())}")
    print(f"   Валидированные поля: {list(validated.keys())}")
    print(f"   Вредоносное поле отфильтровано\n")

    # Тест 2: Построение UPDATE запроса
    print("2. Построение UPDATE запроса:")
    query, values = build_update_query('clients', {'full_name': 'Иван', 'phone': '+7...'})
    print(f"   Запрос: {query}")
    print(f"   Значения: {values}\n")

    # Тест 3: Построение INSERT запроса
    print("3. Построение INSERT запроса:")
    query, values = build_insert_query('clients', {
        'client_type': 'Физическое лицо',
        'full_name': 'Иван',
        'phone': '+7...'
    })
    print(f"   Запрос: {query}")
    print(f"   Значения: {values}\n")

    # Тест 4: Санитизация имени таблицы
    print("4. Санитизация имени таблицы:")
    try:
        sanitize_table_name("clients; DROP TABLE employees")
        print("   SQL-инъекция не обнаружена")
    except ValueError as e:
        print(f"   SQL-инъекция заблокирована: {e}\n")

    print("=== Все тесты завершены ===")
