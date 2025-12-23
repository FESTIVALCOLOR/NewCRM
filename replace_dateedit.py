# -*- coding: utf-8 -*-
"""
Скрипт для замены QDateEdit на CustomDateEdit во всех UI файлах
"""
import re
import os

files_to_update = [
    'ui/crm_tab.py',
    'ui/contracts_tab.py',
    'ui/clients_tab.py',
    'ui/employees_tab.py',
    'ui/crm_supervision_tab.py'
]

total_replacements = 0

for file_path in files_to_update:
    if not os.path.exists(file_path):
        print(f"[SKIP] Файл не найден: {file_path}")
        continue

    print(f"\n[PROCESSING] {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # 1. Добавляем импорт CustomDateEdit если его нет
    if 'from ui.custom_dateedit import CustomDateEdit' not in content:
        # Ищем блок импортов из PyQt5
        if 'from PyQt5.QtWidgets import' in content:
            # Добавляем импорт после первого импорта из PyQt5
            lines = content.split('\n')
            new_lines = []
            import_added = False

            for line in lines:
                new_lines.append(line)
                if not import_added and line.strip().startswith('from PyQt5.QtWidgets import'):
                    new_lines.append('from ui.custom_dateedit import CustomDateEdit')
                    import_added = True

            content = '\n'.join(new_lines)
            print(f"  [+] Добавлен импорт CustomDateEdit")

    # 2. Заменяем QDateEdit( на CustomDateEdit(
    count1 = content.count('QDateEdit(')
    content = content.replace('QDateEdit(', 'CustomDateEdit(')

    # 3. Заменяем = QDateEdit() на = CustomDateEdit()
    count2 = content.count('= QDateEdit()')
    content = content.replace('= QDateEdit()', '= CustomDateEdit()')

    # 4. Заменяем QDateEdit.currentDate() на CustomDateEdit.currentDate()
    count3 = content.count('QDateEdit.currentDate()')
    content = content.replace('QDateEdit.currentDate()', 'CustomDateEdit.currentDate()')

    replacements = count1 + count2 + count3

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [OK] Заменено: {replacements} вхождений")
        total_replacements += replacements
    else:
        print(f"  [SKIP] Нет изменений")

print(f"\n[DONE] Всего заменено: {total_replacements} вхождений QDateEdit на CustomDateEdit")
