# -*- coding: utf-8 -*-
"""
Скрипт для создания таблицы project_templates для хранения ссылок на шаблоны проектов
"""
import sqlite3

def add_project_templates_table():
    """Создание таблицы project_templates для хранения ссылок на шаблоны"""
    conn = sqlite3.connect('interior_studio.db')
    cursor = conn.cursor()

    try:
        # Проверяем, существует ли таблица
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='project_templates'
        """)

        if cursor.fetchone():
            print("[INFO] Таблица project_templates уже существует")
        else:
            # Создаем таблицу project_templates
            cursor.execute('''
                CREATE TABLE project_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id INTEGER NOT NULL,
                    template_url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE
                )
            ''')
            print("[OK] Создана таблица project_templates")

            # Создаем индекс для быстрого поиска по contract_id
            cursor.execute('''
                CREATE INDEX idx_project_templates_contract_id
                ON project_templates(contract_id)
            ''')
            print("[OK] Создан индекс idx_project_templates_contract_id")

        conn.commit()
        print("\n[SUCCESS] Миграция успешно завершена!")

    except Exception as e:
        print(f"\n[ERROR] Ошибка при выполнении миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("Начинаем миграцию базы данных...")
    print("-" * 50)
    add_project_templates_table()
