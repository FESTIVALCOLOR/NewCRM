# -*- coding: utf-8 -*-
"""
Скрипт для добавления полей references_yandex_path и photo_documentation_yandex_path в таблицу contracts
"""
import sqlite3

def add_references_and_photo_fields():
    """Добавление полей для хранения путей к папкам Референсов и Фотофиксации"""
    conn = sqlite3.connect('interior_studio.db')
    cursor = conn.cursor()

    try:
        # Проверяем, существуют ли поля
        cursor.execute("PRAGMA table_info(contracts)")
        columns = [column[1] for column in cursor.fetchall()]

        # Добавляем поле references_yandex_path, если его нет
        if 'references_yandex_path' not in columns:
            cursor.execute('''
                ALTER TABLE contracts
                ADD COLUMN references_yandex_path TEXT
            ''')
            print("[OK] Dobavleno pole references_yandex_path")
        else:
            print("[INFO] Pole references_yandex_path uzhe suschestvuet")

        # Добавляем поле photo_documentation_yandex_path, если его нет
        if 'photo_documentation_yandex_path' not in columns:
            cursor.execute('''
                ALTER TABLE contracts
                ADD COLUMN photo_documentation_yandex_path TEXT
            ''')
            print("[OK] Dobavleno pole photo_documentation_yandex_path")
        else:
            print("[INFO] Pole photo_documentation_yandex_path uzhe suschestvuet")

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
    add_references_and_photo_fields()
