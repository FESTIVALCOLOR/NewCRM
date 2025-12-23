# -*- coding: utf-8 -*-
"""
Проверка нового запроса для get_all_payments
"""
from database.db_manager import DatabaseManager
import datetime

db = DatabaseManager()
month = datetime.datetime.now().month
year = datetime.datetime.now().year

payments = db.get_all_payments(month, year)

print(f'Всего выплат: {len(payments)}')

# Группировка по типу проекта
project_types = {}
for p in payments:
    pt = p.get('project_type') or 'None'
    project_types[pt] = project_types.get(pt, 0) + 1

print('\nПо типам проектов:')
for k, v in sorted(project_types.items()):
    print(f'  {k}: {v}')

# Группировка по источнику
sources = {}
for p in payments:
    src = p.get('source', 'Unknown')
    sources[src] = sources.get(src, 0) + 1

print('\nПо источникам:')
for k, v in sorted(sources.items()):
    print(f'  {k}: {v}')

print('\nПримеры записей (первые 10):')
for i, p in enumerate(payments[:10], 1):
    project_type = p.get('project_type') or 'N/A'
    name = p.get('employee_name', 'N/A')
    address = p.get('address') or 'Нет адреса'
    if len(address) > 30:
        address = address[:30] + '...'
    print(f'{i}. [{project_type}] {name} - {address}')
