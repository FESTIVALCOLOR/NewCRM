# -*- coding: utf-8 -*-
"""
Скрипт для исправления названий вкладок в main_window.py
"""

# Читаем файл
with open('ui/main_window.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем строки с вкладками
replacements = [
    ("if 'Клиенты' in allowed_tabs:\n            self.tabs.addTab(ClientsTab(self.employee, api_client=self.api_client), '📋 Клиенты')",
     "if 'Клиенты' in allowed_tabs:\n            self.tabs.addTab(ClientsTab(self.employee, api_client=self.api_client), '📋 Клиенты')"),

    ("if 'Договоры' in allowed_tabs:\n            self.tabs.addTab(ContractsTab(self.employee, api_client=self.api_client), '📝 Договоры')",
     "if 'Договора' in allowed_tabs:\n            self.tabs.addTab(ContractsTab(self.employee, api_client=self.api_client), '📝 Договора')"),

    ("if 'CRM' in allowed_tabs:\n            self.tabs.addTab(CRMTab(self.employee, can_edit, api_client=self.api_client), '💼 CRM')",
     "if 'СРМ' in allowed_tabs:\n            self.tabs.addTab(CRMTab(self.employee, can_edit, api_client=self.api_client), '💼 СРМ')"),

    ("if 'Авторский надзор' in allowed_tabs:\n            self.tabs.addTab(CRMSupervisionTab(self.employee, api_client=self.api_client), '👁️ Авторский надзор')",
     "if 'СРМ надзора' in allowed_tabs:\n            self.tabs.addTab(CRMSupervisionTab(self.employee, api_client=self.api_client), '👁️ СРМ надзора')"),

    ("if 'Мои отчеты' in allowed_tabs:\n            self.tabs.addTab(ReportsTab(self.employee, api_client=self.api_client), '📊 Мои отчеты')",
     "if 'Отчеты и Статистика' in allowed_tabs:\n            self.tabs.addTab(ReportsTab(self.employee, api_client=self.api_client), '📊 Отчеты и Статистика')"),

    ("if 'Отчеты сотрудников' in allowed_tabs:\n            self.tabs.addTab(EmployeeReportsTab(self.employee, api_client=self.api_client), '📈 Отчеты сотрудников')",
     "if 'Отчеты по сотрудникам' in allowed_tabs:\n            self.tabs.addTab(EmployeeReportsTab(self.employee, api_client=self.api_client), '📈 Отчеты по сотрудникам')"),
]

# Сначала ищем и заменяем блок целиком
old_block = """        #
        if '' in allowed_tabs:
            self.tabs.addTab(ClientsTab(self.employee, api_client=self.api_client), '    ')

        if '' in allowed_tabs:
            self.tabs.addTab(ContractsTab(self.employee, api_client=self.api_client), '    ')

        if '' in allowed_tabs:
            self.tabs.addTab(CRMTab(self.employee, can_edit, api_client=self.api_client), '    ')

        if ' ' in allowed_tabs:
            self.tabs.addTab(CRMSupervisionTab(self.employee, api_client=self.api_client), '     ')

        if '  ' in allowed_tabs:
            self.tabs.addTab(ReportsTab(self.employee, api_client=self.api_client), '      ')

        if '' in allowed_tabs:
            self.tabs.addTab(EmployeesTab(self.employee, api_client=self.api_client), '    ')

        if '' in allowed_tabs:
            self.tabs.addTab(SalariesTab(self.employee, api_client=self.api_client), '    ')

        if '  ' in allowed_tabs:
            self.tabs.addTab(EmployeeReportsTab(self.employee, api_client=self.api_client), '      ')"""

new_block = """        # Добавляем вкладки
        if 'Клиенты' in allowed_tabs:
            self.tabs.addTab(ClientsTab(self.employee, api_client=self.api_client), '📋 Клиенты')

        if 'Договора' in allowed_tabs:
            self.tabs.addTab(ContractsTab(self.employee, api_client=self.api_client), '📝 Договора')

        if 'СРМ' in allowed_tabs:
            self.tabs.addTab(CRMTab(self.employee, can_edit, api_client=self.api_client), '💼 СРМ')

        if 'СРМ надзора' in allowed_tabs:
            self.tabs.addTab(CRMSupervisionTab(self.employee, api_client=self.api_client), '👁️ СРМ надзора')

        if 'Отчеты и Статистика' in allowed_tabs:
            self.tabs.addTab(ReportsTab(self.employee, api_client=self.api_client), '📊 Отчеты и Статистика')

        if 'Сотрудники' in allowed_tabs:
            self.tabs.addTab(EmployeesTab(self.employee, api_client=self.api_client), '👥 Сотрудники')

        if 'Зарплаты' in allowed_tabs:
            self.tabs.addTab(SalariesTab(self.employee, api_client=self.api_client), '💰 Зарплаты')

        if 'Отчеты по сотрудникам' in allowed_tabs:
            self.tabs.addTab(EmployeeReportsTab(self.employee, api_client=self.api_client), '📈 Отчеты по сотрудникам')"""

if old_block in content:
    content = content.replace(old_block, new_block)
    print("[OK] Блок с вкладками заменен")
else:
    print("[ERROR] Блок с вкладками не найден")
    print("Попробуем найти части...")

# Сохраняем
with open('ui/main_window.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Файл сохранен")
