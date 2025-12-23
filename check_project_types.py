# -*- coding: utf-8 -*-
"""
Проверка значений project_type в contracts
"""
import sqlite3

def check_project_types():
    conn = sqlite3.connect('interior_studio.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Проверяем уникальные значения project_type в contracts
    cursor.execute("""
        SELECT DISTINCT project_type
        FROM contracts
        WHERE project_type IS NOT NULL
        ORDER BY project_type
    """)

    print("Уникальные значения project_type в contracts:")
    for row in cursor.fetchall():
        print(f"  '{row['project_type']}'")

    # Проверяем количество по каждому типу
    cursor.execute("""
        SELECT project_type, COUNT(*) as count
        FROM contracts
        GROUP BY project_type
    """)

    print("\nКоличество по типам:")
    for row in cursor.fetchall():
        print(f"  '{row['project_type']}': {row['count']}")

    conn.close()

if __name__ == '__main__':
    check_project_types()
