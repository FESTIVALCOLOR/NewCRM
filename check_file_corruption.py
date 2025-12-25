# -*- coding: utf-8 -*-
"""
Проверка всех файлов на наличие поврежденных emoji/русского текста
"""
import os
import re

def check_file_for_corruption(filepath):
    """Проверка файла на наличие квадратиков или поврежденных символов"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Ищем квадратики (replacement character)
        if '\ufffd' in content or '�' in content:
            return f"[CORRUPTED] {filepath} - содержит квадратики (поврежденные символы)"

        # Проверяем, что русский текст читается нормально
        if re.search(r'[а-яА-Я]', content):
            return f"[OK] {filepath} - русский текст в порядке"

        return f"[SKIP] {filepath} - нет русского текста"

    except Exception as e:
        return f"[ERROR] {filepath}: {e}"

# Проверяем файлы из коммита "Add multi-user mode support"
files_to_check = [
    'config.py',
    'migrate_to_server.py',
    'ui/login_window.py',
    'ui/main_window.py',
    'utils/api_client.py',
    'utils/logger.py',
]

print("=== ПРОВЕРКА ФАЙЛОВ НА ПОВРЕЖДЕНИЯ ===\n")

corrupted_files = []
ok_files = []

for filepath in files_to_check:
    if os.path.exists(filepath):
        result = check_file_for_corruption(filepath)
        print(result)

        if '[CORRUPTED]' in result:
            corrupted_files.append(filepath)
        elif '[OK]' in result:
            ok_files.append(filepath)
    else:
        print(f"[SKIP] {filepath} - файл не найден")

print(f"\n=== ИТОГО ===")
print(f"Проверено файлов: {len(files_to_check)}")
print(f"OK: {len(ok_files)}")
print(f"Повреждено: {len(corrupted_files)}")

if corrupted_files:
    print(f"\n[WARNING] Найдены поврежденные файлы:")
    for f in corrupted_files:
        print(f"  - {f}")
else:
    print(f"\n[SUCCESS] Все файлы в порядке!")
