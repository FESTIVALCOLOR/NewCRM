# -*- coding: utf-8 -*-
"""
Миграция: добавление поля project_type в таблицу salaries
"""
import sqlite3

def migrate():
    """Добавляет поле project_type в таблицу salaries"""
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect('interior_studio.db')
        cursor = conn.cursor()

        # Проверяем, есть ли уже такое поле
        cursor.execute("PRAGMA table_info(salaries)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'project_type' not in columns:
            print("[INFO] Добавление поля project_type в таблицу salaries...")

            # Добавляем новое поле
            cursor.execute('''
                ALTER TABLE salaries
                ADD COLUMN project_type TEXT DEFAULT 'Индивидуальный'
            ''')

            conn.commit()
            print("[OK] Поле project_type успешно добавлено!")
        else:
            print("[OK] Поле project_type уже существует")

        conn.close()

    except Exception as e:
        print(f"[ERROR] Ошибка при миграции: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    migrate()
