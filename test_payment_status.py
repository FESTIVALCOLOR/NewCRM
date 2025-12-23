# -*- coding: utf-8 -*-
"""
Тестовый скрипт для установки статусов выплат
"""
import sqlite3

conn = sqlite3.connect('interior_studio.db')
cursor = conn.cursor()

print("Установка тестовых статусов...")

# Получаем первые 3 выплаты
cursor.execute('SELECT id FROM payments LIMIT 3')
payment_ids = [row[0] for row in cursor.fetchall()]

if len(payment_ids) >= 3:
    # Первая - к оплате
    cursor.execute('UPDATE payments SET payment_status = ? WHERE id = ?', ('to_pay', payment_ids[0]))
    print(f"[OK] Установлен статус 'to_pay' для ID={payment_ids[0]}")

    # Вторая - оплачено
    cursor.execute('UPDATE payments SET payment_status = ? WHERE id = ?', ('paid', payment_ids[1]))
    print(f"[OK] Установлен статус 'paid' для ID={payment_ids[1]}")

    # Третья - без статуса
    cursor.execute('UPDATE payments SET payment_status = NULL WHERE id = ?', (payment_ids[2],))
    print(f"[OK] Сброшен статус для ID={payment_ids[2]}")

    conn.commit()
    print("[OK] Изменения сохранены!")
else:
    print("[INFO] Недостаточно выплат в базе для тестирования")

# Проверка
cursor.execute('''
SELECT id, payment_status
FROM payments
WHERE payment_status IS NOT NULL
LIMIT 5
''')

print("\nВыплаты со статусами:")
for row in cursor.fetchall():
    print(f"  ID={row[0]}, статус={row[1]}")

conn.close()
