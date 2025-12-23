# -*- coding: utf-8 -*-
"""
Исправление crm_card_id для выплат исполнителей
"""
import sqlite3

conn = sqlite3.connect('interior_studio.db')
cursor = conn.cursor()

print("Обновление crm_card_id для выплат исполнителей...")

# Находим выплаты без crm_card_id и связываем их через contract_id
cursor.execute('''
UPDATE payments
SET crm_card_id = (
    SELECT cc.id
    FROM crm_cards cc
    WHERE cc.contract_id = payments.contract_id
    LIMIT 1
)
WHERE crm_card_id IS NULL
AND contract_id IS NOT NULL
AND role IN ('Дизайнер', 'Чертежник')
''')

updated = cursor.rowcount
conn.commit()

print(f"[OK] Obnovleno {updated} zapisey")

# Проверка
cursor.execute('''
SELECT COUNT(*) as cnt
FROM payments
WHERE role IN ('Дизайнер', 'Чертежник')
AND crm_card_id IS NOT NULL
''')

result = cursor.fetchone()
print(f"[OK] Vsego vyplat dizaynerov/chertezhnikov s crm_card_id: {result[0]}")

conn.close()
print("[OK] Gotovo!")
