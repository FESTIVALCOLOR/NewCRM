# -*- coding: utf-8 -*-
"""
Скрипт для проверки загрузки данных из API
"""

from utils.api_client import APIClient
import urllib3

# Отключаем предупреждения SSL
urllib3.disable_warnings()

def test_api_data_loading():
    """Тестирование загрузки данных из API"""
    print("=== ТЕСТИРОВАНИЕ ЗАГРУЗКИ ДАННЫХ ИЗ API ===\n")

    # Инициализация API клиента
    api_url = "https://147.45.154.193"
    client = APIClient(api_url)

    # 1. Авторизация
    print("1. Авторизация...")
    try:
        result = client.login("admin", "admin123")
        print(f"   [OK] Успешная авторизация")
        print(f"   Пользователь: {result['full_name']}")
        print(f"   Роль: {result['role']}\n")
    except Exception as e:
        print(f"   [ERROR] Ошибка авторизации: {e}\n")
        return

    # 2. Загрузка клиентов
    print("2. Загрузка клиентов...")
    try:
        clients = client.get_clients()
        print(f"   [OK] Загружено клиентов: {len(clients)}")
        if clients:
            print(f"   Пример: {clients[0]['full_name']} ({clients[0]['phone']})\n")
        else:
            print("   Список клиентов пуст\n")
    except Exception as e:
        print(f"   [ERROR] Ошибка загрузки клиентов: {e}\n")

    # 3. Загрузка сотрудников
    print("3. Загрузка сотрудников...")
    try:
        employees = client.get_employees()
        print(f"   [OK] Загружено сотрудников: {len(employees)}")
        if employees:
            print(f"   Пример: {employees[0]['full_name']} ({employees[0]['position']})\n")
        else:
            print("   Список сотрудников пуст\n")
    except Exception as e:
        print(f"   [ERROR] Ошибка загрузки сотрудников: {e}\n")

    # 4. Загрузка договоров
    print("4. Загрузка договоров...")
    try:
        contracts = client.get_contracts()
        print(f"   [OK] Загружено договоров: {len(contracts)}")
        if contracts:
            print(f"   Пример: Договор №{contracts[0]['contract_number']}, площадь {contracts[0]['area']} м²\n")
        else:
            print("   Список договоров пуст\n")
    except Exception as e:
        print(f"   [ERROR] Ошибка загрузки договоров: {e}\n")

    # 5. Статистика для Dashboard
    print("5. Расчет статистики для Dashboard...")
    try:
        contracts = client.get_contracts(limit=1000)

        stats = {
            'individual_orders': 0,
            'template_orders': 0,
            'supervision_orders': 0,
            'individual_area': 0.0,
            'template_area': 0.0,
            'supervision_area': 0.0
        }

        for contract in contracts:
            project_type = contract.get('project_type', '')
            area = float(contract.get('area', 0) or 0)
            supervision = contract.get('supervision', False)

            if project_type == 'Индивидуальный':
                stats['individual_orders'] += 1
                stats['individual_area'] += area
            elif project_type == 'Шаблонный':
                stats['template_orders'] += 1
                stats['template_area'] += area

            if supervision:
                stats['supervision_orders'] += 1
                stats['supervision_area'] += area

        print(f"   [OK] Статистика рассчитана:")
        print(f"   Индивидуальных проектов: {stats['individual_orders']} ({stats['individual_area']:.0f} м²)")
        print(f"   Шаблонных проектов: {stats['template_orders']} ({stats['template_area']:.0f} м²)")
        print(f"   Авторский надзор: {stats['supervision_orders']} ({stats['supervision_area']:.0f} м²)\n")
    except Exception as e:
        print(f"   [ERROR] Ошибка расчета статистики: {e}\n")

    print("=== ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")

if __name__ == "__main__":
    test_api_data_loading()
