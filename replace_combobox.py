# -*- coding: utf-8 -*-
"""
Скрипт для замены QComboBox на CustomComboBox во всех файлах проекта
"""
import re
import os

# Список файлов для обработки (все UI файлы кроме custom_combobox.py и main.py)
files_to_process = [
    'ui/clients_tab.py',
    'ui/contracts_tab.py',
    'ui/crm_supervision_tab.py',
    'ui/crm_tab.py',
    'ui/employees_tab.py',
    'ui/employee_reports_tab.py',
    'ui/rates_dialog.py',
    'ui/reports_tab.py',
    'ui/salaries_tab.py'
]

def replace_in_file(file_path):
    """Заменяет QComboBox на CustomComboBox в файле"""
    print(f"Обработка файла: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Проверяем, нужна ли замена
    if 'QComboBox()' not in content:
        print(f"  OK В файле нет QComboBox(), пропускаем")
        return

    # Проверяем, есть ли уже импорт CustomComboBox
    has_custom_import = 'from ui.custom_combobox import CustomComboBox' in content

    # Если импорта нет, добавляем его после импорта custom_message_box или custom_title_bar
    if not has_custom_import:
        # Ищем где добавить импорт
        if 'from ui.custom_message_box import' in content:
            content = re.sub(
                r'(from ui\.custom_message_box import [^\n]+)',
                r'\1\nfrom ui.custom_combobox import CustomComboBox',
                content
            )
            print(f"  + Добавлен импорт CustomComboBox после custom_message_box")
        elif 'from ui.custom_title_bar import' in content:
            content = re.sub(
                r'(from ui\.custom_title_bar import [^\n]+)',
                r'\1\nfrom ui.custom_combobox import CustomComboBox',
                content
            )
            print(f"  + Добавлен импорт CustomComboBox после custom_title_bar")
        else:
            # Добавляем после всех импортов из PyQt5
            lines = content.split('\n')
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith('from PyQt5') or line.startswith('import PyQt5'):
                    insert_pos = i + 1
            if insert_pos > 0:
                lines.insert(insert_pos, 'from ui.custom_combobox import CustomComboBox')
                content = '\n'.join(lines)
                print(f"  + Добавлен импорт CustomComboBox после импортов PyQt5")

    # Заменяем = QComboBox() на = CustomComboBox()
    original_count = content.count('= QComboBox()')
    content = re.sub(r'= QComboBox\(\)', '= CustomComboBox()', content)

    # Сохраняем изменения
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  OK Заменено {original_count} использований QComboBox() на CustomComboBox()")

def main():
    print("=" * 60)
    print("ЗАМЕНА QComboBox НА CustomComboBox ВО ВСЕХ ФАЙЛАХ ПРОЕКТА")
    print("=" * 60)
    print()

    for file_path in files_to_process:
        if os.path.exists(file_path):
            replace_in_file(file_path)
            print()
        else:
            print(f"Файл не найден: {file_path}")
            print()

    print("=" * 60)
    print("ЗАМЕНА ЗАВЕРШЕНА")
    print("=" * 60)

if __name__ == '__main__':
    main()
