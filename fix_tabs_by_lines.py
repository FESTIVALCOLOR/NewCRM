# -*- coding: utf-8 -*-
"""
Скрипт для исправления названий вкладок в main_window.py по номерам строк
"""

# Читаем файл
with open('ui/main_window.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Заменяем строки (номер строки в файле - 1, т.к. индексы с 0)
# Строка 811: комментарий
lines[810] = "        # Добавляем вкладки\n"

# Строка 812: if 'Клиенты'
lines[811] = "        if 'Клиенты' in allowed_tabs:\n"
# Строка 813: addTab для Клиентов
lines[812] = "            self.tabs.addTab(ClientsTab(self.employee, api_client=self.api_client), '📋 Клиенты')\n"

# Строка 815: if 'Договора'
lines[814] = "        if 'Договора' in allowed_tabs:\n"
# Строка 816: addTab для Договоров
lines[815] = "            self.tabs.addTab(ContractsTab(self.employee, api_client=self.api_client), '📝 Договора')\n"

# Строка 818: if 'СРМ'
lines[817] = "        if 'СРМ' in allowed_tabs:\n"
# Строка 819: addTab для СРМ
lines[818] = "            self.tabs.addTab(CRMTab(self.employee, can_edit, api_client=self.api_client), '💼 СРМ')\n"

# Строка 821: if 'СРМ надзора'
lines[820] = "        if 'СРМ надзора' in allowed_tabs:\n"
# Строка 822: addTab для СРМ надзора
lines[821] = "            self.tabs.addTab(CRMSupervisionTab(self.employee, api_client=self.api_client), '👁️ СРМ надзора')\n"

# Строка 824: if 'Отчеты и Статистика'
lines[823] = "        if 'Отчеты и Статистика' in allowed_tabs:\n"
# Строка 825: addTab для Отчетов
lines[824] = "            self.tabs.addTab(ReportsTab(self.employee, api_client=self.api_client), '📊 Отчеты и Статистика')\n"

# Строка 827: if 'Сотрудники'
lines[826] = "        if 'Сотрудники' in allowed_tabs:\n"
# Строка 828: addTab для Сотрудников
lines[827] = "            self.tabs.addTab(EmployeesTab(self.employee, api_client=self.api_client), '👥 Сотрудники')\n"

# Строка 830: if 'Зарплаты'
lines[829] = "        if 'Зарплаты' in allowed_tabs:\n"
# Строка 831: addTab для Зарплат
lines[830] = "            self.tabs.addTab(SalariesTab(self.employee, api_client=self.api_client), '💰 Зарплаты')\n"

# Строка 833: if 'Отчеты по сотрудникам'
lines[832] = "        if 'Отчеты по сотрудникам' in allowed_tabs:\n"
# Строка 834: addTab для Отчетов по сотрудникам
lines[833] = "            self.tabs.addTab(EmployeeReportsTab(self.employee, api_client=self.api_client), '📈 Отчеты по сотрудникам')\n"

# Сохраняем
with open('ui/main_window.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("[OK] Файл исправлен успешно!")
print("Заменено 8 вкладок:")
print("  - Клиенты")
print("  - Договора")
print("  - СРМ")
print("  - СРМ надзора")
print("  - Отчеты и Статистика")
print("  - Сотрудники")
print("  - Зарплаты")
print("  - Отчеты по сотрудникам")
