# -*- coding: utf-8 -*-
"""
Проверка данных для вкладок
"""
import sqlite3

conn = sqlite3.connect('interior_studio.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 60)
print("ИНДИВИДУАЛЬНЫЕ ПРОЕКТЫ")
print("=" * 60)

cursor.execute('''
SELECT p.*, e.full_name as employee_name, e.position,
       c.contract_number, c.address, c.area, c.city, c.agent_type,
       'CRM' as source
FROM payments p
JOIN employees e ON p.employee_id = e.id
LEFT JOIN crm_cards cc ON p.crm_card_id = cc.id
LEFT JOIN contracts c ON cc.contract_id = c.id
WHERE c.project_type = ?

UNION ALL

SELECT s.id, NULL as contract_id, NULL as crm_card_id, NULL as supervision_card_id,
       s.employee_id, s.payment_type as role, s.stage_name,
       s.amount as calculated_amount, NULL as manual_amount,
       s.amount as final_amount, 0 as is_manual,
       NULL as payment_type, s.report_month, 0 as is_paid,
       NULL as paid_date, NULL as paid_by, s.created_at, s.created_at as updated_at,
       e.full_name as employee_name, e.position,
       c.contract_number, c.address, c.area, c.city, c.agent_type,
       'Оклад' as source
FROM salaries s
JOIN employees e ON s.employee_id = e.id
LEFT JOIN contracts c ON s.contract_id = c.id
WHERE s.project_type = ?

ORDER BY 1 DESC
''', ('Индивидуальный', 'Индивидуальный'))

individual = cursor.fetchall()
print(f"Всего: {len(individual)}")
for row in individual[:5]:
    print(f"  {row['employee_name']} - {row['address'] or 'N/A'}")

print("\n" + "=" * 60)
print("ШАБЛОННЫЕ ПРОЕКТЫ")
print("=" * 60)

cursor.execute('''
SELECT p.*, e.full_name as employee_name, e.position,
       c.contract_number, c.address, c.area, c.city, c.agent_type,
       'CRM' as source
FROM payments p
JOIN employees e ON p.employee_id = e.id
LEFT JOIN crm_cards cc ON p.crm_card_id = cc.id
LEFT JOIN contracts c ON cc.contract_id = c.id
WHERE c.project_type = ?

UNION ALL

SELECT s.id, NULL as contract_id, NULL as crm_card_id, NULL as supervision_card_id,
       s.employee_id, s.payment_type as role, s.stage_name,
       s.amount as calculated_amount, NULL as manual_amount,
       s.amount as final_amount, 0 as is_manual,
       NULL as payment_type, s.report_month, 0 as is_paid,
       NULL as paid_date, NULL as paid_by, s.created_at, s.created_at as updated_at,
       e.full_name as employee_name, e.position,
       c.contract_number, c.address, c.area, c.city, c.agent_type,
       'Оклад' as source
FROM salaries s
JOIN employees e ON s.employee_id = e.id
LEFT JOIN contracts c ON s.contract_id = c.id
WHERE s.project_type = ?

ORDER BY 1 DESC
''', ('Шаблонный', 'Шаблонный'))

template = cursor.fetchall()
print(f"Всего: {len(template)}")
for row in template[:5]:
    print(f"  {row['employee_name']} - {row['address'] or 'N/A'}")

print("\n" + "=" * 60)
print("АВТОРСКИЙ НАДЗОР")
print("=" * 60)

cursor.execute('''
SELECT p.*, e.full_name as employee_name, e.position,
       c.contract_number, c.address, c.area, c.city, c.agent_type,
       'CRM Надзор' as source
FROM payments p
JOIN employees e ON p.employee_id = e.id
LEFT JOIN supervision_cards sc ON p.supervision_card_id = sc.id
LEFT JOIN contracts c ON sc.contract_id = c.id
WHERE c.project_type = ? OR (p.supervision_card_id IS NOT NULL AND c.project_type IS NULL)

UNION ALL

SELECT s.id, NULL as contract_id, NULL as crm_card_id, NULL as supervision_card_id,
       s.employee_id, s.payment_type as role, s.stage_name,
       s.amount as calculated_amount, NULL as manual_amount,
       s.amount as final_amount, 0 as is_manual,
       NULL as payment_type, s.report_month, 0 as is_paid,
       NULL as paid_date, NULL as paid_by, s.created_at, s.created_at as updated_at,
       e.full_name as employee_name, e.position,
       c.contract_number, c.address, c.area, c.city, c.agent_type,
       'Оклад' as source
FROM salaries s
JOIN employees e ON s.employee_id = e.id
LEFT JOIN contracts c ON s.contract_id = c.id
WHERE s.project_type = ?

ORDER BY 1 DESC
''', ('Авторский надзор', 'Авторский надзор'))

supervision = cursor.fetchall()
print(f"Всего: {len(supervision)}")
for row in supervision[:5]:
    print(f"  {row['employee_name']} - {row['address'] or 'N/A'}")

conn.close()
