# -*- coding: utf-8 -*-
"""
Тест новых DELETE и PUT роутов на сервере
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from utils.api_client import APIClient

# Подключаемся к API
client = APIClient('https://147.45.154.193')

# Логинимся
print("=== ЛОГИН ===")
result = client.login('admin', 'admin123')
print(f"[OK] Успешный вход! Токен: {result['access_token'][:40]}...")

print("\n=== ТЕСТ 1: Создание тестового клиента ===")
try:
    test_client = client.create_client({
        'full_name': 'ТЕСТОВЫЙ КЛИЕНТ ДЛЯ УДАЛЕНИЯ',
        'phone': '+7 999 999-99-99',
        'email': 'test@test.ru',
        'address': 'Тестовый адрес',
        'source': 'Тест'
    })
    print(f"[OK] Клиент создан с ID: {test_client['id']}")
    test_client_id = test_client['id']
except Exception as e:
    print(f"[ERROR] Ошибка создания клиента: {e}")
    test_client_id = None

print("\n=== ТЕСТ 2: Удаление клиента (DELETE /api/clients/{id}) ===")
if test_client_id:
    try:
        result = client.delete_client(test_client_id)
        print(f"[OK] Клиент удален успешно!")
    except Exception as e:
        print(f"[ERROR] Ошибка удаления клиента: {e}")
else:
    print("[SKIP] Пропущено - клиент не был создан")

print("\n=== ТЕСТ 3: Обновление сотрудника (PUT /api/employees/{id}) ===")
try:
    # Получаем список сотрудников
    employees = client.get_employees()
    if employees:
        test_emp = employees[0]
        print(f"  Сотрудник для теста: {test_emp['full_name']} (ID: {test_emp['id']})")

        # Обновляем (меняем только department, чтобы не испортить данные)
        current_dept = test_emp.get('department', 'Другое')
        new_dept = 'ТЕСТ ОБНОВЛЕНИЯ' if current_dept != 'ТЕСТ ОБНОВЛЕНИЯ' else 'Другое'

        updated = client.update_employee(test_emp['id'], {
            'department': new_dept
        })
        print(f"[OK] Сотрудник обновлен! Department: {current_dept} -> {updated['department']}")

        # Возвращаем обратно
        client.update_employee(test_emp['id'], {'department': current_dept})
        print(f"[OK] Department возвращен к исходному значению: {current_dept}")
    else:
        print("[SKIP] Нет сотрудников для теста")
except Exception as e:
    print(f"[ERROR] Ошибка обновления сотрудника: {e}")

print("\n=== ТЕСТ 4: Создание и удаление договора ===")
try:
    # Получаем клиента для договора
    clients = client.get_clients()
    if clients:
        test_contract = client.create_contract({
            'client_id': clients[0]['id'],
            'contract_number': 'TEST-DELETE-001',
            'contract_amount': 1000.0,
            'status': 'Черновик'
        })
        print(f"[OK] Договор создан с ID: {test_contract['id']}")

        # Удаляем
        result = client.delete_contract(test_contract['id'])
        print(f"[OK] Договор удален успешно!")
    else:
        print("[SKIP] Нет клиентов для теста договора")
except Exception as e:
    print(f"[ERROR] Ошибка теста договора: {e}")

print("\n=== ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ ===")
