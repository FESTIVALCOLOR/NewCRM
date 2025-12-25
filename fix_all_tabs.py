# -*- coding: utf-8 -*-
"""
Скрипт для добавления параметра api_client во все вкладки
"""

tabs_to_fix = [
    ('ui/contracts_tab.py', 'ContractsTab'),
    ('ui/crm_tab.py', 'CRMTab'),
    ('ui/crm_supervision_tab.py', 'CRMSupervisionTab'),
    ('ui/reports_tab.py', 'ReportsTab'),
    ('ui/employees_tab.py', 'EmployeesTab'),
    ('ui/salaries_tab.py', 'SalariesTab'),
    ('ui/employee_reports_tab.py', 'EmployeeReportsTab'),
]

for filepath, classname in tabs_to_fix:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Ищем конструктор вкладки
        # Вариант 1: def __init__(self, employee, parent=None):
        old_pattern1 = f"def __init__(self, employee, parent=None):"
        new_pattern1 = f"def __init__(self, employee, api_client=None, parent=None):"

        # Вариант 2: def __init__(self, employee, can_edit, parent=None): для CRMTab
        old_pattern2 = f"def __init__(self, employee, can_edit, parent=None):"
        new_pattern2 = f"def __init__(self, employee, can_edit, api_client=None, parent=None):"

        # Вариант 3: def __init__(self, employee):
        old_pattern3 = f"def __init__(self, employee):"
        new_pattern3 = f"def __init__(self, employee, api_client=None):"

        changed = False

        if old_pattern1 in content:
            content = content.replace(old_pattern1, new_pattern1)
            changed = True
            print(f"[OK] {filepath}: добавлен api_client (вариант 1)")
        elif old_pattern2 in content:
            content = content.replace(old_pattern2, new_pattern2)
            changed = True
            print(f"[OK] {filepath}: добавлен api_client (вариант 2 - с can_edit)")
        elif old_pattern3 in content:
            content = content.replace(old_pattern3, new_pattern3)
            changed = True
            print(f"[OK] {filepath}: добавлен api_client (вариант 3)")

        if changed:
            # Добавляем строку self.api_client = api_client после self.employee = employee
            lines = content.split('\n')
            new_lines = []
            added = False

            for i, line in enumerate(lines):
                new_lines.append(line)
                # Ищем строку с self.employee = employee и добавляем после нее
                if 'self.employee = employee' in line and not added:
                    # Определяем отступ
                    indent = len(line) - len(line.lstrip())
                    new_lines.append(' ' * indent + 'self.api_client = api_client  # Клиент для работы с API (многопользовательский режим)')
                    added = True

            content = '\n'.join(new_lines)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"     Добавлена строка self.api_client = api_client")
        else:
            print(f"[SKIP] {filepath}: api_client уже добавлен или не найден конструктор")

    except Exception as e:
        print(f"[ERROR] {filepath}: {e}")

print("\n=== ГОТОВО ===")
print("Все вкладки обновлены для поддержки api_client")
