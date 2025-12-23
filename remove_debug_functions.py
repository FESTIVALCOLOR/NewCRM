#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Удалить все debug функции и методы"""
import re

# 1. Удалить функцию debug_rates_in_db из rates_dialog.py
rates_dialog_path = r'd:\New CRM\interior_studio\ui\rates_dialog.py'
with open(rates_dialog_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Найти и удалить функцию debug_rates_in_db
pattern = r'    def debug_rates_in_db\(self\):.*?(?=\n    def |\Z)'
content = re.sub(pattern, '', content, flags=re.DOTALL)

with open(rates_dialog_path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'✓ Удалена функция debug_rates_in_db из {rates_dialog_path.split(chr(92))[-1]}')

# 2. Удалить методы debug из db_manager.py
db_manager_path = r'd:\New CRM\interior_studio\database\db_manager.py'
with open(db_manager_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Удалить debug_database_state
pattern = r'    def debug_database_state\(self\):.*?(?=\n    def |\Z)'
content = re.sub(pattern, '', content, flags=re.DOTALL)

# Удалить debug_supervision_state  
pattern = r'    def debug_supervision_state\(self\):.*?(?=\n    def |\Z)'
content = re.sub(pattern, '', content, flags=re.DOTALL)

with open(db_manager_path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'✓ Удалены методы debug_database_state и debug_supervision_state из {db_manager_path.split(chr(92))[-1]}')

print('\n✅ Все debug функции удалены!')
