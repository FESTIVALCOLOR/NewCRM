# -*- coding: utf-8 -*-
"""
Скрипт для добавления поля variation в таблицу project_files
"""
import sqlite3

def add_variation_field():
    """Добавление поля variation для хранения номера вариации"""
    conn = sqlite3.connect('interior_studio.db')
    cursor = conn.cursor()

    try:
        # Проверяем, существует ли поле
        cursor.execute("PRAGMA table_info(project_files)")
        columns = [column[1] for column in cursor.fetchall()]

        # Добавляем поле variation, если его нет
        if 'variation' not in columns:
            cursor.execute('''
                ALTER TABLE project_files
                ADD COLUMN variation INTEGER DEFAULT 1
            ''')
            print("[OK] Dobavleno pole variation")
        else:
            print("[INFO] Pole variation uzhe suschestvuet")

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
    add_variation_field()
