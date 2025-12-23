# -*- coding: utf-8 -*-
"""Миграция: Добавление поля yandex_folder_path в таблицу contracts"""
import sqlite3

def add_yandex_folder_path():
    """Добавляет поле yandex_folder_path для хранения пути к папке на Яндекс.Диске"""
    conn = sqlite3.connect('interior_studio.db')
    cursor = conn.cursor()

    # Проверяем, есть ли уже это поле
    cursor.execute("PRAGMA table_info(contracts)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'yandex_folder_path' not in columns:
        print("Добавляем поле yandex_folder_path...")
        cursor.execute('''
        ALTER TABLE contracts
        ADD COLUMN yandex_folder_path TEXT
        ''')
        conn.commit()
        print("[OK] Поле yandex_folder_path успешно добавлено")
    else:
        print("[INFO] Поле yandex_folder_path уже существует")

    conn.close()

if __name__ == '__main__':
    add_yandex_folder_path()
