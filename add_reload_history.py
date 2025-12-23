# -*- coding: utf-8 -*-
"""
Скрипт для добавления reload_project_history() после каждого add_action_history()
"""
import re

file_path = 'ui/crm_tab.py'

print("Чтение файла...")
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# Находим все строки с add_action_history и добавляем reload после закрывающей скобки
modified_lines = []
i = 0
added_count = 0

while i < len(lines):
    line = lines[i]
    modified_lines.append(line)

    # Проверяем, есть ли в строке self.db.add_action_history(
    if 'self.db.add_action_history(' in line:
        # Определяем отступ текущей строки
        indent = len(line) - len(line.lstrip())
        base_indent = ' ' * indent

        # Ищем закрывающую скобку для этого вызова
        open_parens = line.count('(') - line.count(')')
        j = i + 1

        # Если вызов многострочный, ищем закрывающую скобку
        while open_parens > 0 and j < len(lines):
            modified_lines.append(lines[j])
            open_parens += lines[j].count('(') - lines[j].count(')')
            j += 1

        # Проверяем, не добавлен ли уже reload_project_history на следующей строке
        next_line_index = j
        if next_line_index < len(lines):
            next_line = lines[next_line_index].strip()
            # Если следующая строка уже содержит reload_project_history, пропускаем
            if 'reload_project_history' not in next_line:
                # Добавляем вызов reload_project_history()
                modified_lines.append(f"{base_indent}self.reload_project_history()")
                added_count += 1
                print(f"  + Добавлен reload_project_history() после строки {i+1}")

        i = j - 1

    i += 1

# Сохраняем изменения
new_content = '\n'.join(modified_lines)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"\n✓ Обработка завершена. Добавлено вызовов: {added_count}")
