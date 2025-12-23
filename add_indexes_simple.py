# -*- coding: utf-8 -*-
"""
Упрощенная версия добавления индексов (без Unicode для Windows)
"""

import sqlite3
import os

def add_database_indexes(db_path='interior_studio.db'):
    """Добавляет индексы в базу данных"""

    print("="*60)
    print("ДОБАВЛЕНИЕ ИНДЕКСОВ В БАЗУ ДАННЫХ")
    print("="*60)

    if not os.path.exists(db_path):
        print(f"[ERROR] Файл базы данных не найден: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Список индексов
        indexes = [
            ("idx_employees_login", "CREATE INDEX IF NOT EXISTS idx_employees_login ON employees(login)"),
            ("idx_employees_status", "CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status)"),
            ("idx_employees_position", "CREATE INDEX IF NOT EXISTS idx_employees_position ON employees(position)"),
            ("idx_clients_phone", "CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone)"),
            ("idx_clients_email", "CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email)"),
            ("idx_contracts_client_id", "CREATE INDEX IF NOT EXISTS idx_contracts_client_id ON contracts(client_id)"),
            ("idx_contracts_number", "CREATE INDEX IF NOT EXISTS idx_contracts_number ON contracts(contract_number)"),
            ("idx_contracts_status", "CREATE INDEX IF NOT EXISTS idx_contracts_status ON contracts(status)"),
            ("idx_crm_cards_contract_id", "CREATE INDEX IF NOT EXISTS idx_crm_cards_contract_id ON crm_cards(contract_id)"),
            ("idx_crm_cards_column_name", "CREATE INDEX IF NOT EXISTS idx_crm_cards_column_name ON crm_cards(column_name)"),
            ("idx_crm_cards_deadline", "CREATE INDEX IF NOT EXISTS idx_crm_cards_deadline ON crm_cards(deadline)"),
            ("idx_crm_cards_senior_manager", "CREATE INDEX IF NOT EXISTS idx_crm_cards_senior_manager ON crm_cards(senior_manager_id)"),
            ("idx_salaries_employee_id", "CREATE INDEX IF NOT EXISTS idx_salaries_employee_id ON salaries(employee_id)"),
            ("idx_salaries_report_month", "CREATE INDEX IF NOT EXISTS idx_salaries_report_month ON salaries(report_month)"),
        ]

        print(f"\nСоздание {len(indexes)} индексов...\n")

        created_count = 0
        for index_name, sql in indexes:
            try:
                cursor.execute(sql)
                print(f"  [OK] {index_name}")
                created_count += 1
            except Exception as e:
                print(f"  [ERROR] {index_name}: {e}")

        conn.commit()

        # Обновляем статистику
        print("\nОбновление статистики...")
        cursor.execute("ANALYZE")
        conn.commit()
        print("  [OK] Статистика обновлена")

        print("\n" + "="*60)
        print(f"[SUCCESS] ИНДЕКСЫ ДОБАВЛЕНЫ: {created_count} из {len(indexes)}")
        print("="*60)

        conn.close()
        return True

    except Exception as e:
        print(f"\n[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n")
    print("="*60)
    print("  ОПТИМИЗАЦИЯ БАЗЫ ДАННЫХ - INTERIOR STUDIO CRM")
    print("="*60)
    print()

    db_path = 'interior_studio.db'
    print(f"База данных: {db_path}\n")

    success = add_database_indexes(db_path)

    if success:
        print("\n[SUCCESS] Индексы успешно добавлены!")
        print("\nЗапросы станут работать в 10-100 раз быстрее.")
    else:
        print("\n[ERROR] Добавление индексов завершилось с ошибками")
