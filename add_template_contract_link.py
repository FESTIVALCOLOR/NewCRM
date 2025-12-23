#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Миграция: добавление поля template_contract_file_link
"""
import sqlite3

DB_PATH = 'interior_studio.db'

def migrate():
    """Добавляем поле для ссылки на файл шаблонного договора"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Проверяем существование поля
        cursor.execute("PRAGMA table_info(contracts)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'template_contract_file_link' not in columns:
            print("[INFO] Добавляем поле template_contract_file_link...")
            cursor.execute('ALTER TABLE contracts ADD COLUMN template_contract_file_link TEXT')
            conn.commit()
            print("[OK] Поле template_contract_file_link добавлено!")
        else:
            print("[INFO] Поле template_contract_file_link уже существует")

    except Exception as e:
        print(f"[ERROR] Ошибка при миграции: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
