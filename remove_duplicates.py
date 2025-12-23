# -*- coding: utf-8 -*-
"""
Скрипт удаления дублированного кода из папки database
"""

import os
import shutil

def remove_duplicates():
    """Удаляет дублированные файлы и папки"""

    base_path = os.path.dirname(os.path.abspath(__file__))
    database_path = os.path.join(base_path, 'database')

    items_to_remove = [
        os.path.join(database_path, 'ui'),
        os.path.join(database_path, 'utils'),
        os.path.join(database_path, 'config.py'),
        os.path.join(database_path, 'generate_icons.py'),
        os.path.join(database_path, 'fix_positions.py'),
        os.path.join(database_path, 'database', 'ui'),
        os.path.join(database_path, 'database', 'utils'),
        os.path.join(database_path, 'database', 'config.py'),
    ]

    print("="*60)
    print("УДАЛЕНИЕ ДУБЛИРОВАННОГО КОДА")
    print("="*60)
    print()

    removed_count = 0
    not_found_count = 0

    for item_path in items_to_remove:
        if os.path.exists(item_path):
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    print(f"[OK] Удалена папка: {os.path.basename(os.path.dirname(item_path))}/{os.path.basename(item_path)}")
                else:
                    os.remove(item_path)
                    print(f"[OK] Удален файл: {os.path.basename(item_path)}")
                removed_count += 1
            except Exception as e:
                print(f"[ERROR] Ошибка при удалении {item_path}: {e}")
        else:
            not_found_count += 1

    print()
    print("="*60)
    print(f"[SUCCESS] ОЧИСТКА ЗАВЕРШЕНА")
    print(f"  Удалено: {removed_count} элементов")
    if not_found_count > 0:
        print(f"  Не найдено: {not_found_count} элементов (уже удалены)")
    print("="*60)

    # Показываем что осталось в database/
    print()
    print("Оставшиеся файлы в database/:")
    for item in os.listdir(database_path):
        item_path = os.path.join(database_path, item)
        if os.path.isfile(item_path):
            print(f"  - {item}")
        elif os.path.isdir(item_path) and not item.startswith('__'):
            print(f"  - {item}/ (папка)")

if __name__ == '__main__':
    remove_duplicates()
