# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

from utils.api_client import APIClient

# Подключение
c = APIClient('https://147.45.154.193')
r = c.login('admin', 'admin123')
print(f'[OK] Login as: {r["full_name"]} (ID: {r["employee_id"]}, Role: {r["role"]})')

# Тест обновления сотрудника
emps = c.get_employees()
# Найдём сотрудника не-руководителя для теста
test_emp = None
for emp in emps:
    if emp['position'] not in ['Руководитель студии', 'Старший менеджер проектов']:
        test_emp = emp
        break

if not test_emp:
    print('[ERROR] No suitable employee for testing')
else:
    print(f'Testing employee: {test_emp["full_name"]} (ID: {test_emp["id"]}, Position: {test_emp["position"]})')

    dept = test_emp.get('department', 'Другое')
    new_dept = 'TEST UPDATE' if dept != 'TEST UPDATE' else 'Другое'

    try:
        updated = c.update_employee(test_emp['id'], {'department': new_dept})
        print(f'[OK] Updated department: {dept} -> {updated["department"]}')

        # Возврат обратно
        c.update_employee(test_emp['id'], {'department': dept})
        print('[OK] Restored department back')
    except Exception as e:
        print(f'[ERROR] Update failed: {e}')

print('\n=== TEST COMPLETE ===')
