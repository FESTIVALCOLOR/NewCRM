# -*- coding: utf-8 -*-
"""
Утилиты для безопасной работы с паролями
Использует PBKDF2 с SHA-256 для хэширования
"""

import hashlib
import secrets
import base64


def hash_password(password: str) -> str:
    """
    Хэширует пароль с использованием PBKDF2-SHA256

    Args:
        password: Пароль в открытом виде

    Returns:
        Строка формата "salt$hash" для хранения в БД
    """
    # Генерируем соль (16 байт = 128 бит)
    salt = secrets.token_bytes(16)

    # Хэширование с 100000 итераций (рекомендация OWASP)
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )

    # Кодируем в base64 для хранения
    salt_b64 = base64.b64encode(salt).decode('utf-8')
    hash_b64 = base64.b64encode(password_hash).decode('utf-8')

    # Формат: salt$hash
    return f"{salt_b64}${hash_b64}"


def verify_password(password: str, stored_password: str) -> bool:
    """
    Проверяет соответствие пароля хэшу

    Args:
        password: Пароль для проверки
        stored_password: Хэшированный пароль из БД (формат "salt$hash")

    Returns:
        True если пароль верный, False иначе
    """
    try:
        # Разбираем сохранённый пароль
        if '$' not in stored_password:
            # Старый формат (plain text) - для обратной совместимости
            # ВАЖНО: Это временная мера, нужно удалить после миграции всех паролей
            return password == stored_password

        salt_b64, hash_b64 = stored_password.split('$', 1)

        # Декодируем из base64
        salt = base64.b64decode(salt_b64)
        stored_hash = base64.b64decode(hash_b64)

        # Хэшируем введённый пароль с той же солью
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )

        # Сравниваем хэши (используем secrets.compare_digest для защиты от timing attacks)
        return secrets.compare_digest(password_hash, stored_hash)

    except Exception as e:
        print(f"Ошибка при проверке пароля: {e}")
        return False


def generate_strong_password(length: int = 12) -> str:
    """
    Генерирует случайный надёжный пароль

    Args:
        length: Длина пароля (минимум 8)

    Returns:
        Случайный пароль
    """
    import string

    if length < 8:
        length = 8

    # Набор символов
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"

    # Генерируем пароль
    password = ''.join(secrets.choice(alphabet) for _ in range(length))

    return password


# Тестирование модуля
if __name__ == '__main__':
    print("=== Тест модуля password_utils ===\n")

    # Тест 1: Хэширование и проверка
    test_password = "MySecurePass123!"
    hashed = hash_password(test_password)
    print(f"Оригинальный пароль: {test_password}")
    print(f"Хэшированный пароль: {hashed}\n")

    # Тест 2: Проверка правильного пароля
    is_valid = verify_password(test_password, hashed)
    print(f"Проверка правильного пароля: {'УСПЕХ' if is_valid else 'ОШИБКА'}")

    # Тест 3: Проверка неправильного пароля
    is_invalid = verify_password("WrongPassword", hashed)
    print(f"Проверка неправильного пароля: {'ОШИБКА' if is_invalid else 'УСПЕХ'}")

    # Тест 4: Генерация случайного пароля
    random_pass = generate_strong_password(16)
    print(f"\nСгенерированный пароль: {random_pass}")

    # Тест 5: Обратная совместимость (plain text)
    plain_password = "admin"
    is_plain_valid = verify_password("admin", plain_password)
    print(f"Проверка plain text пароля: {'УСПЕХ' if is_plain_valid else 'ОШИБКА'}")
