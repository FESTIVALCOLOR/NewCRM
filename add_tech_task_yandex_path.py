# -*- coding: utf-8 -*-
"""
Скрипт для добавления поля tech_task_yandex_path в таблицу contracts
"""
import sqlite3

def add_tech_task_yandex_path_field():
    """Добавление поля для хранения пути к файлу тех.задания на Яндекс.Диске"""
    conn = sqlite3.connect('interior_studio.db')
    cursor = conn.cursor()

    try:
        # Проверяем, существует ли поле
        cursor.execute("PRAGMA table_info(contracts)")
        columns = [column[1] for column in cursor.fetchall()]

        # Добавляем поле tech_task_yandex_path, если его нет
        if 'tech_task_yandex_path' not in columns:
            cursor.execute('''
                ALTER TABLE contracts
                ADD COLUMN tech_task_yandex_path TEXT
            ''')
            print("[OK] Dobavleno pole tech_task_yandex_path")
        else:
            print("[INFO] Pole tech_task_yandex_path uzhe suschestvuet")

        conn.commit()
        print("\n[SUCCESS] Migraciya uspeshno zavershena!")

    except Exception as e:
        print(f"\n[ERROR] Oshibka pri vypolnenii migracii: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("Начинаем миграцию базы данных...")
    print("-" * 50)
    add_tech_task_yandex_path_field()
