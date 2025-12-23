# -*- coding: utf-8 -*-
"""
Скрипт для добавления полей measurement_image_link и measurement_date в таблицу contracts
"""
import sqlite3

def add_measurement_fields():
    """Добавление полей для хранения данных о замере в таблицу contracts"""
    conn = sqlite3.connect('interior_studio.db')
    cursor = conn.cursor()

    try:
        # Проверяем, существуют ли поля
        cursor.execute("PRAGMA table_info(contracts)")
        columns = [column[1] for column in cursor.fetchall()]

        # Добавляем поле measurement_image_link, если его нет
        if 'measurement_image_link' not in columns:
            cursor.execute('''
                ALTER TABLE contracts
                ADD COLUMN measurement_image_link TEXT
            ''')
            print("[OK] Dobavleno pole measurement_image_link")
        else:
            print("[INFO] Pole measurement_image_link uzhe suschestvuet")

        # Добавляем поле measurement_date, если его нет
        if 'measurement_date' not in columns:
            cursor.execute('''
                ALTER TABLE contracts
                ADD COLUMN measurement_date TEXT
            ''')
            print("[OK] Dobavleno pole measurement_date")
        else:
            print("[INFO] Pole measurement_date uzhe suschestvuet")

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
    add_measurement_fields()
