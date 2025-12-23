# -*- coding: utf-8 -*-
"""
Скрипт миграции паролей из plain text в хэшированный формат
ВАЖНО: Запустить один раз для миграции существующих паролей
"""

import sqlite3
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.password_utils import hash_password


def migrate_passwords(db_path='interior_studio.db'):
    """
    Мигрирует все пароли из plain text в хэшированный формат

    Args:
        db_path: Путь к базе данных
    """
    print("="*60)
    print("МИГРАЦИЯ ПАРОЛЕЙ В ХЭШИРОВАННЫЙ ФОРМАТ")
    print("="*60)

    if not os.path.exists(db_path):
        print(f"[ERROR] Файл базы данных не найден: {db_path}")
        return False

    try:
        # Подключаемся к БД
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Получаем всех сотрудников с паролями
        cursor.execute('''
            SELECT id, login, password, full_name
            FROM employees
            WHERE password IS NOT NULL AND password != ''
        ''')

        employees = cursor.fetchall()

        if not employees:
            print("[OK] Нет сотрудников для миграции")
            return True

        print(f"\nНайдено сотрудников: {len(employees)}")
        print("\nМигрируем пароли...")

        migrated_count = 0
        skipped_count = 0

        for emp_id, login, password, full_name in employees:
            # Проверяем, не хэширован ли уже пароль
            if '$' in password:
                print(f"  ⊘ Пропускаем {login} ({full_name}) - уже хэширован")
                skipped_count += 1
                continue

            # Хэшируем пароль
            hashed_password = hash_password(password)

            # Обновляем в БД
            cursor.execute('''
                UPDATE employees
                SET password = ?
                WHERE id = ?
            ''', (hashed_password, emp_id))

            print(f"  [OK] Мигрирован {login} ({full_name})")
            migrated_count += 1

        # Сохраняем изменения
        conn.commit()

        print("\n" + "="*60)
        print(f"[OK] МИГРАЦИЯ ЗАВЕРШЕНА")
        print(f"  Мигрировано: {migrated_count}")
        print(f"  Пропущено: {skipped_count}")
        print("="*60)

        conn.close()
        return True

    except Exception as e:
        print(f"\n[ERROR] ОШИБКА при миграции: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_backup(db_path='interior_studio.db'):
    """
    Создаёт резервную копию базы данных перед миграцией

    Args:
        db_path: Путь к базе данных
    """
    import shutil
    from datetime import datetime

    if not os.path.exists(db_path):
        return None

    # Создаём имя бэкапа с датой
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"

    try:
        shutil.copy2(db_path, backup_path)
        print(f"[OK] Создана резервная копия: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"[WARN] Не удалось создать резервную копию: {e}")
        return None


if __name__ == '__main__':
    print("\n")
    print("="*61)
    print("  СКРИПТ МИГРАЦИИ ПАРОЛЕЙ В ХЭШИРОВАННЫЙ ФОРМАТ")
    print("="*61)
    print()

    # Определяем путь к БД
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv

    if len(sys.argv) > 1 and sys.argv[1] not in ['--yes', '-y']:
        db_path = sys.argv[1]
    else:
        db_path = 'interior_studio.db'

    print(f"База данных: {db_path}")
    print()

    # Запрашиваем подтверждение (если не указан флаг --yes)
    if not auto_confirm:
        try:
            response = input("Продолжить миграцию? (да/нет): ").lower()
            if response not in ['да', 'yes', 'y', 'д']:
                print("Миграция отменена")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print("\nМиграция отменена")
            sys.exit(0)
    else:
        print("Автоматическое подтверждение (--yes)")
        print("Продолжаем миграцию...")

    print()

    # Создаём бэкап
    print("Создание резервной копии...")
    backup_path = create_backup(db_path)
    print()

    # Выполняем миграцию
    success = migrate_passwords(db_path)

    if success:
        print("\n[OK] Миграция выполнена успешно!")
        print("\nВАЖНО: Теперь все пароли хэшированы.")
        print("Пользователям НЕ нужно менять пароли - они останутся прежними.")
        if backup_path:
            print(f"\nРезервная копия сохранена: {backup_path}")
    else:
        print("\n[ERROR] Миграция завершилась с ошибками")
        if backup_path:
            print(f"Вы можете восстановить БД из резервной копии: {backup_path}")
        sys.exit(1)
