#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Миграция: добавление полей для хранения имен и путей файлов договоров
"""
import sqlite3

DB_PATH = 'interior_studio.db'

def migrate():
    """Добавляем поля для файлов договоров"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Проверяем существование полей
        cursor.execute("PRAGMA table_info(contracts)")
        columns = [row[1] for row in cursor.fetchall()]

        # Добавляем недостающие поля
        if 'contract_file_name' not in columns:
            print("[INFO] Добавляем поле contract_file_name...")
            cursor.execute('ALTER TABLE contracts ADD COLUMN contract_file_name TEXT')

        if 'contract_file_yandex_path' not in columns:
            print("[INFO] Добавляем поле contract_file_yandex_path...")
            cursor.execute('ALTER TABLE contracts ADD COLUMN contract_file_yandex_path TEXT')

        if 'template_contract_file_name' not in columns:
            print("[INFO] Добавляем поле template_contract_file_name...")
            cursor.execute('ALTER TABLE contracts ADD COLUMN template_contract_file_name TEXT')

        if 'template_contract_file_yandex_path' not in columns:
            print("[INFO] Добавляем поле template_contract_file_yandex_path...")
            cursor.execute('ALTER TABLE contracts ADD COLUMN template_contract_file_yandex_path TEXT')

        conn.commit()
        print("[OK] Миграция завершена успешно!")

    except Exception as e:
        print(f"[ERROR] Ошибка при миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
