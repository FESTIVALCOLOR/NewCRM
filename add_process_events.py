# -*- coding: utf-8 -*-
"""
Скрипт для добавления QApplication.processEvents() после каждого reload_project_history()
"""
import re

file_path = 'ui/crm_tab.py'

print("Чтение файла...")
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# Находим все строки с reload_project_history и добавляем processEvents после
modified_lines = []
i = 0
added_count = 0

while i < len(lines):
    line = lines[i]
    modified_lines.append(line)

    # Проверяем, есть ли в строке self.reload_project_history()
    if 'self.reload_project_history()' in line and 'try:' not in line:  # Пропускаем строку с try:
        # Определяем отступ текущей строки
        indent = len(line) - len(line.lstrip())
        base_indent = ' ' * indent

        # Проверяем следующие 5 строк: если уже есть processEvents, пропускаем
        has_process_events = False
        for j in range(i + 1, min(i + 6, len(lines))):
            if 'processEvents' in lines[j]:
                has_process_events = True
                break

        if not has_process_events:
            # Добавляем пустую строку и processEvents
            modified_lines.append('')
            modified_lines.append(f"{base_indent}# Принудительно обрабатываем отложенные события Qt")
            modified_lines.append(f"{base_indent}from PyQt5.QtWidgets import QApplication")
            modified_lines.append(f"{base_indent}QApplication.processEvents()")
            added_count += 1
            print(f"  + Добавлен processEvents() после строки {i+1}")

    i += 1

# Сохраняем изменения
new_content = '\n'.join(modified_lines)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"\n✓ Обработка завершена. Добавлено вызовов processEvents: {added_count}")
