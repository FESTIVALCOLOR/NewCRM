# -*- coding: utf-8 -*-
"""
Скрипт замены Unicode символов на ASCII-совместимые
"""

import re

def fix_unicode_in_file(filepath):
    """Заменяет Unicode символы на ASCII в файле"""

    replacements = {
        '✓': '[OK]',
        '✗': '[FAIL]',
        '⚠️': '[WARN]',
        '⚠': '[WARN]',
        '❌': '[ERROR]',
        '✅': '[SUCCESS]',
        '🔴': '[!]',
        '🟠': '[!]',
        '🟡': '[!]',
        '🔵': '[i]',
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Замена символов
        for old, new in replacements.items():
            content = content.replace(old, new)

        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[OK] Исправлен файл: {filepath}")
            return True
        else:
            print(f"[SKIP] Нет Unicode символов в: {filepath}")
            return False

    except Exception as e:
        print(f"[ERROR] Ошибка в {filepath}: {e}")
        return False


if __name__ == '__main__':
    files_to_fix = [
        'database/db_manager.py',
        'main.py',
        'utils/migrate_passwords.py',
        'utils/add_indexes.py',
    ]

    print("="*60)
    print("ЗАМЕНА UNICODE СИМВОЛОВ НА ASCII")
    print("="*60)
    print()

    fixed_count = 0
    for filepath in files_to_fix:
        if fix_unicode_in_file(filepath):
            fixed_count += 1

    print()
    print("="*60)
    print(f"[SUCCESS] Исправлено файлов: {fixed_count}")
    print("="*60)
