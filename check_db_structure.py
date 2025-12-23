#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3

DB_PATH = 'interior_studio.db'

def check_structure():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(contracts)")
    columns = cursor.fetchall()

    print("=== Поля в таблице contracts связанные с файлами ===")
    for col in columns:
        col_name = col[1]
        if 'file' in col_name.lower() or 'template' in col_name.lower() or 'link' in col_name.lower():
            print(f"{col[0]}: {col[1]} {col[2]}")

    conn.close()

if __name__ == '__main__':
    check_structure()
