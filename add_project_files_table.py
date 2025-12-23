# -*- coding: utf-8 -*-
"""
Миграция: добавление таблицы project_files для управления файлами стадий проекта
"""
import sqlite3
import os

def migrate():
    """Создание таблицы project_files"""
    db_path = 'interior_studio.db'

    if not os.path.exists(db_path):
        print(f"[ERROR] База данных {db_path} не найдена!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Проверяем, существует ли таблица
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='project_files'
        """)

        if cursor.fetchone():
            print("[INFO] Таблица project_files уже существует")
            return

        print("[>] Создание таблицы project_files...")

        # Создаем таблицу
        cursor.execute('''
            CREATE TABLE project_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER NOT NULL,
                stage TEXT NOT NULL,
                file_type TEXT NOT NULL,
                public_link TEXT,
                yandex_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
                preview_cache_path TEXT,
                file_order INTEGER DEFAULT 0,
                FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE
            )
        ''')

        print("[OK] Таблица project_files создана")

        # Создаем индексы
        print("[>] Создание индексов...")

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_project_files_contract
            ON project_files(contract_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_project_files_stage
            ON project_files(contract_id, stage)
        ''')

        print("[OK] Индексы созданы")

        conn.commit()
        print("\n[SUCCESS] Миграция успешно завершена!")

    except Exception as e:
        print(f"\n[ERROR] Ошибка миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("Начало миграции...")
    print("-" * 60)
    migrate()
    print("-" * 60)
