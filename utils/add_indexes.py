# -*- coding: utf-8 -*-
"""
Скрипт добавления индексов в базу данных для ускорения запросов
"""

import sqlite3
import sys
import os


def add_database_indexes(db_path='interior_studio.db'):
    """
    Добавляет индексы в базу данных для оптимизации производительности

    Args:
        db_path: Путь к базе данных
    """
    print("="*60)
    print("ДОБАВЛЕНИЕ ИНДЕКСОВ В БАЗУ ДАННЫХ")
    print("="*60)

    if not os.path.exists(db_path):
        print(f"[ERROR] Файл базы данных не найден: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Список индексов для создания
        indexes = [
            # Employees - часто используется для поиска по логину
            ("idx_employees_login", "CREATE INDEX IF NOT EXISTS idx_employees_login ON employees(login)"),
            ("idx_employees_status", "CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status)"),
            ("idx_employees_position", "CREATE INDEX IF NOT EXISTS idx_employees_position ON employees(position)"),
            ("idx_employees_department", "CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department)"),

            # Clients - поиск по телефону и email
            ("idx_clients_phone", "CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone)"),
            ("idx_clients_email", "CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email)"),
            ("idx_clients_inn", "CREATE INDEX IF NOT EXISTS idx_clients_inn ON clients(inn)"),
            ("idx_clients_type", "CREATE INDEX IF NOT EXISTS idx_clients_type ON clients(client_type)"),

            # Contracts - часто используются внешние ключи
            ("idx_contracts_client_id", "CREATE INDEX IF NOT EXISTS idx_contracts_client_id ON contracts(client_id)"),
            ("idx_contracts_number", "CREATE INDEX IF NOT EXISTS idx_contracts_number ON contracts(contract_number)"),
            ("idx_contracts_status", "CREATE INDEX IF NOT EXISTS idx_contracts_status ON contracts(status)"),
            ("idx_contracts_date", "CREATE INDEX IF NOT EXISTS idx_contracts_date ON contracts(contract_date)"),
            ("idx_contracts_project_type", "CREATE INDEX IF NOT EXISTS idx_contracts_project_type ON contracts(project_type)"),

            # CRM Cards - постоянные JOIN'ы по contract_id и фильтрация по column_name
            ("idx_crm_cards_contract_id", "CREATE INDEX IF NOT EXISTS idx_crm_cards_contract_id ON crm_cards(contract_id)"),
            ("idx_crm_cards_column_name", "CREATE INDEX IF NOT EXISTS idx_crm_cards_column_name ON crm_cards(column_name)"),
            ("idx_crm_cards_deadline", "CREATE INDEX IF NOT EXISTS idx_crm_cards_deadline ON crm_cards(deadline)"),
            ("idx_crm_cards_senior_manager", "CREATE INDEX IF NOT EXISTS idx_crm_cards_senior_manager ON crm_cards(senior_manager_id)"),
            ("idx_crm_cards_sdp", "CREATE INDEX IF NOT EXISTS idx_crm_cards_sdp ON crm_cards(sdp_id)"),
            ("idx_crm_cards_gap", "CREATE INDEX IF NOT EXISTS idx_crm_cards_gap ON crm_cards(gap_id)"),
            ("idx_crm_cards_manager", "CREATE INDEX IF NOT EXISTS idx_crm_cards_manager ON crm_cards(manager_id)"),
            ("idx_crm_cards_surveyor", "CREATE INDEX IF NOT EXISTS idx_crm_cards_surveyor ON crm_cards(surveyor_id)"),
            ("idx_crm_cards_approved", "CREATE INDEX IF NOT EXISTS idx_crm_cards_approved ON crm_cards(is_approved)"),

            # Supervision Cards
            ("idx_supervision_cards_contract_id", "CREATE INDEX IF NOT EXISTS idx_supervision_cards_contract_id ON supervision_cards(contract_id)"),
            ("idx_supervision_cards_column_name", "CREATE INDEX IF NOT EXISTS idx_supervision_cards_column_name ON supervision_cards(column_name)"),
            ("idx_supervision_cards_dan", "CREATE INDEX IF NOT EXISTS idx_supervision_cards_dan ON supervision_cards(dan_id)"),
            ("idx_supervision_cards_senior_manager", "CREATE INDEX IF NOT EXISTS idx_supervision_cards_senior_manager ON supervision_cards(senior_manager_id)"),

            # Salaries - группировка по месяцам и сотрудникам
            ("idx_salaries_employee_id", "CREATE INDEX IF NOT EXISTS idx_salaries_employee_id ON salaries(employee_id)"),
            ("idx_salaries_contract_id", "CREATE INDEX IF NOT EXISTS idx_salaries_contract_id ON salaries(contract_id)"),
            ("idx_salaries_report_month", "CREATE INDEX IF NOT EXISTS idx_salaries_report_month ON salaries(report_month)"),
            ("idx_salaries_payment_type", "CREATE INDEX IF NOT EXISTS idx_salaries_payment_type ON salaries(payment_type)"),

            # Composite indexes для частых комбинаций
            ("idx_crm_cards_contract_column", "CREATE INDEX IF NOT EXISTS idx_crm_cards_contract_column ON crm_cards(contract_id, column_name)"),
            ("idx_salaries_employee_month", "CREATE INDEX IF NOT EXISTS idx_salaries_employee_month ON salaries(employee_id, report_month)"),
        ]

        print(f"\nСоздание {len(indexes)} индексов...\n")

        created_count = 0
        for index_name, sql in indexes:
            try:
                cursor.execute(sql)
                print(f"  [OK] {index_name}")
                created_count += 1
            except sqlite3.Error as e:
                print(f"  [FAIL] {index_name}: {e}")

        conn.commit()

        # Анализируем таблицы для обновления статистики
        print("\nОбновление статистики для оптимизатора запросов...")
        cursor.execute("ANALYZE")
        conn.commit()
        print("  [OK] Статистика обновлена")

        print("\n" + "="*60)
        print(f"[OK] ИНДЕКСЫ ДОБАВЛЕНЫ: {created_count} из {len(indexes)}")
        print("="*60)

        # Показываем список всех индексов
        print("\nСписок всех индексов в базе данных:")
        cursor.execute("""
            SELECT name, tbl_name
            FROM sqlite_master
            WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
            ORDER BY tbl_name, name
        """)

        current_table = None
        for idx_name, table_name in cursor.fetchall():
            if table_name != current_table:
                print(f"\n  {table_name}:")
                current_table = table_name
            print(f"    - {idx_name}")

        conn.close()
        return True

    except Exception as e:
        print(f"\n[ERROR] ОШИБКА при добавлении индексов: {e}")
        import traceback
        traceback.print_exc()
        return False


def analyze_query_performance(db_path='interior_studio.db'):
    """
    Анализирует производительность типичных запросов

    Args:
        db_path: Путь к базе данных
    """
    print("\n" + "="*60)
    print("АНАЛИЗ ПРОИЗВОДИТЕЛЬНОСТИ ЗАПРОСОВ")
    print("="*60 + "\n")

    if not os.path.exists(db_path):
        print(f"[ERROR] Файл базы данных не найден: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Типичные запросы для анализа
    queries = [
        ("Поиск по логину", "SELECT * FROM employees WHERE login = 'admin'"),
        ("Карточки по договору", "SELECT * FROM crm_cards WHERE contract_id = 1"),
        ("Договоры клиента", "SELECT * FROM contracts WHERE client_id = 1"),
        ("Зарплаты за месяц", "SELECT * FROM salaries WHERE report_month = 'Ноябрь 2024'"),
    ]

    for query_name, query in queries:
        print(f"{query_name}:")
        cursor.execute(f"EXPLAIN QUERY PLAN {query}")
        for row in cursor.fetchall():
            print(f"  {row}")
        print()

    conn.close()


if __name__ == '__main__':
    print("\n")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  СКРИПТ ОПТИМИЗАЦИИ БАЗЫ ДАННЫХ - ДОБАВЛЕНИЕ ИНДЕКСОВ    ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Определяем путь к БД
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = 'interior_studio.db'

    print(f"База данных: {db_path}")
    print()

    # Запрашиваем подтверждение
    response = input("Добавить индексы? (да/нет): ").lower()

    if response not in ['да', 'yes', 'y', 'д']:
        print("[ERROR] Операция отменена")
        sys.exit(0)

    print()

    # Добавляем индексы
    success = add_database_indexes(db_path)

    if success:
        print("\n[OK] Индексы успешно добавлены!")
        print("\nПроизводительность запросов должна улучшиться.")
        print("Особенно это заметно на больших объёмах данных (>1000 записей).")

        # Анализируем производительность
        analyze_query_performance(db_path)
    else:
        print("\n[ERROR] Добавление индексов завершилось с ошибками")
        sys.exit(1)
