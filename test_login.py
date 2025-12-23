# -*- coding: utf-8 -*-
"""
Тест входа в систему
"""

from database.db_manager import DatabaseManager

db = DatabaseManager()

print("="*60)
print("ТЕСТ ВХОДА В СИСТЕМУ")
print("="*60)
print()

# Тест 1: Вход с правильными данными
print("Тест 1: Вход с admin/admin")
employee = db.get_employee_by_login('admin', 'admin')

if employee:
    print("[OK] Вход успешен!")
    print(f"  Тип данных: {type(employee)}")
    print(f"  ФИО: {employee.get('full_name', 'N/A')}")
    print(f"  Должность: {employee.get('position', 'N/A')}")
    print(f"  Роль: {employee.get('role', 'N/A')}")
else:
    print("[FAIL] Вход не удался")

print()

# Тест 2: Вход с неправильным паролем
print("Тест 2: Вход с неправильным паролем")
employee = db.get_employee_by_login('admin', 'wrongpassword')

if employee:
    print("[FAIL] Ошибка: вход с неправильным паролем удался!")
else:
    print("[OK] Вход с неправильным паролем отклонен")

print()
print("="*60)
print("Все тесты завершены")
print("="*60)
