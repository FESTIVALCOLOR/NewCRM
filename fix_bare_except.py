#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re

files = [
    'd:\\New CRM\\interior_studio\\ui\\crm_tab.py',
    'd:\\New CRM\\interior_studio\\ui\\crm_supervision_tab.py',
    'd:\\New CRM\\interior_studio\\ui\\contracts_tab.py',
    'd:\\New CRM\\interior_studio\\ui\\employees_tab.py',
    'd:\\New CRM\\interior_studio\\database\\db_manager.py'
]

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Замена bare except на except Exception
        pattern = r'(\n\s+)except:\n'
        replacement = r'\1except Exception:\n'
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            filename = filepath.split('\\')[-1]
            print(f'✓ Обновлен: {filename}')
        else:
            filename = filepath.split('\\')[-1]
            print(f'  Нет изменений: {filename}')
    except Exception as e:
        print(f'❌ Ошибка в {filepath}: {e}')

print('\n✓ Замена завершена!')
