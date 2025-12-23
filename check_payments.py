# -*- coding: utf-8 -*-
"""
Проверка данных в таблицах payments и salaries
"""
import sqlite3

def check_data():
    conn = sqlite3.connect('interior_studio.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Проверяем payments
    cursor.execute("SELECT COUNT(*) as count FROM payments")
    payments_count = cursor.fetchone()['count']
    print(f"Записей в payments: {payments_count}")

    # Проверяем payments с project_type
    cursor.execute("""
        SELECT c.project_type, COUNT(*) as count
        FROM payments p
        JOIN contracts c ON p.contract_id = c.id
        GROUP BY c.project_type
    """)
    print("\nРаспределение по типам проектов в payments:")
    for row in cursor.fetchall():
        print(f"  {row['project_type']}: {row['count']}")

    # Проверяем salaries
    cursor.execute("SELECT COUNT(*) as count FROM salaries")
    salaries_count = cursor.fetchone()['count']
    print(f"\nЗаписей в salaries: {salaries_count}")

    # Проверяем salaries с project_type
    cursor.execute("""
        SELECT project_type, COUNT(*) as count
        FROM salaries
        GROUP BY project_type
    """)
    print("\nРаспределение по типам проектов в salaries:")
    for row in cursor.fetchall():
        print(f"  {row['project_type']}: {row['count']}")

    conn.close()

if __name__ == '__main__':
    check_data()
