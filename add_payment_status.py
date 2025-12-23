# -*- coding: utf-8 -*-
"""
Добавление поля payment_status в таблицы payments и salaries
"""
import sqlite3

conn = sqlite3.connect('interior_studio.db')
cursor = conn.cursor()

print("Добавление поля payment_status...")

# Проверяем, есть ли уже поле
cursor.execute('PRAGMA table_info(payments)')
columns = [col[1] for col in cursor.fetchall()]

if 'payment_status' not in columns:
    cursor.execute('''
        ALTER TABLE payments
        ADD COLUMN payment_status TEXT DEFAULT NULL
    ''')
    print("[OK] Добавлено поле payment_status в payments")
else:
    print("[INFO] Поле payment_status уже существует в payments")

# Добавляем в salaries
cursor.execute('PRAGMA table_info(salaries)')
columns = [col[1] for col in cursor.fetchall()]

if 'payment_status' not in columns:
    cursor.execute('''
        ALTER TABLE salaries
        ADD COLUMN payment_status TEXT DEFAULT NULL
    ''')
    print("[OK] Добавлено поле payment_status в salaries")
else:
    print("[INFO] Поле payment_status уже существует в salaries")

conn.commit()
conn.close()

print("[OK] Готово!")
