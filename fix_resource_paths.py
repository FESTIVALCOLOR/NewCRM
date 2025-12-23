# -*- coding: utf-8 -*-
"""
Скрипт для ОТКАТА изменений и ПРАВИЛЬНОГО исправления путей к ресурсам.
"""

import os
import re

def fix_ui_file_properly(file_path):
    """Правильно исправляет пути к ресурсам в файле"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    modified = False

    # 1. Удаляем неправильно вставленные импорты resource_path
    # Удаляем строку если она стоит отдельно посреди других импортов
    lines = content.split('\n')
    new_lines = []
    skip_next = False

    for i, line in enumerate(lines):
        # Пропускаем плохо вставленные импорты
        if line.strip() == 'from utils.resource_path import resource_path':
            # Проверяем контекст - если это не правильный импорт, пропускаем
            if i > 0 and i < len(lines) - 1:
                prev_line = lines[i-1].strip()
                # Если предыдущая строка - это незавершенный импорт, пропускаем
                if prev_line.endswith('(') or prev_line.endswith(','):
                    continue
        new_lines.append(line)

    content = '\n'.join(new_lines)

    # 2. Добавляем правильный импорт, если его нет
    if 'from utils.resource_path import resource_path' not in content:
        # Находим место после всех импортов PyQt5/Qt
        lines = content.split('\n')
        insert_pos = 0

        for i, line in enumerate(lines):
            if line.startswith('from PyQt5') or line.startswith('from database') or line.startswith('from ui'):
                insert_pos = i + 1
            elif line.strip().startswith('#') and insert_pos > 0:
                # Нашли комментарий после импортов
                break
            elif line.strip() == '' and insert_pos > 0:
                # Нашли пустую строку после импортов
                insert_pos = i
                break

        if insert_pos > 0:
            lines.insert(insert_pos, 'from utils.resource_path import resource_path')
            content = '\n'.join(lines)
            modified = True

    # 3. Заменяем пути к ресурсам
    # QPixmap('resources/...')
    new_content = re.sub(
        r"QPixmap\('resources/([^']+)'\)",
        r"QPixmap(resource_path('resources/\1'))",
        content
    )

    if new_content != content:
        content = new_content
        modified = True

    # QIcon('resources/...')
    new_content = re.sub(
        r"QIcon\('resources/([^']+)'\)",
        r"QIcon(resource_path('resources/\1'))",
        content
    )

    if new_content != content:
        content = new_content
        modified = True

    # os.path.abspath('resources/...')
    new_content = re.sub(
        r"os\.path\.abspath\('resources/([^']+)'\)",
        r"resource_path('resources/\1')",
        content
    )

    if new_content != content:
        content = new_content
        modified = True

    # Если файл изменился, сохраняем
    if modified or content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Обрабатывает все UI файлы"""
    ui_dir = 'ui'
    files_fixed = 0

    print("="*60)
    print("ПРАВИЛЬНОЕ ИСПРАВЛЕНИЕ ПУТЕЙ К РЕСУРСАМ")
    print("="*60)
    print()

    for filename in os.listdir(ui_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            file_path = os.path.join(ui_dir, filename)
            print(f"Обработка: {filename}...", end=' ')

            try:
                if fix_ui_file_properly(file_path):
                    print("[ИСПРАВЛЕН]")
                    files_fixed += 1
                else:
                    print("[БЕЗ ИЗМЕНЕНИЙ]")
            except Exception as e:
                print(f"[ОШИБКА: {e}]")

    print()
    print("="*60)
    print(f"Исправлено файлов: {files_fixed}")
    print("="*60)

if __name__ == '__main__':
    main()
