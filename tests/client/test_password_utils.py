# -*- coding: utf-8 -*-
"""
Тесты password_utils — хеширование, верификация, генерация паролей
"""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.password_utils import hash_password, verify_password, generate_strong_password


class TestHashPassword:
    def test_returns_salt_hash_format(self):
        """Формат: salt$hash"""
        result = hash_password("test123")
        assert "$" in result
        parts = result.split("$")
        assert len(parts) == 2
        assert len(parts[0]) > 0  # salt
        assert len(parts[1]) > 0  # hash

    def test_different_salts(self):
        """Два хеша одного пароля должны быть разными (разные соли)"""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2

    def test_hash_is_base64(self):
        """Salt и hash в base64"""
        import base64
        result = hash_password("test")
        salt_b64, hash_b64 = result.split("$")
        # Проверяем что декодируется без ошибок
        base64.b64decode(salt_b64)
        base64.b64decode(hash_b64)

    def test_unicode_password(self):
        """Кириллические пароли работают"""
        result = hash_password("ПарольНаРусском123")
        assert "$" in result


class TestVerifyPassword:
    def test_correct_password(self):
        hashed = hash_password("MySecurePass!")
        assert verify_password("MySecurePass!", hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("MySecurePass!")
        assert verify_password("WrongPassword", hashed) is False

    @pytest.mark.xfail(reason="Plain text backward compat отключена (security hardening)")
    def test_plain_text_backward_compat(self):
        """Обратная совместимость с plain text паролями"""
        assert verify_password("admin", "admin") is True
        assert verify_password("admin", "wrong") is False

    def test_empty_password_hashed(self):
        """Пустой пароль тоже хешируется и верифицируется"""
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_corrupted_hash_returns_false(self):
        """Повреждённый хеш -> False (не исключение)"""
        assert verify_password("test", "invalid_base64$also_invalid") is False

    def test_unicode_verify(self):
        """Кириллические пароли верифицируются"""
        hashed = hash_password("ПарольНаРусском")
        assert verify_password("ПарольНаРусском", hashed) is True
        assert verify_password("ДругойПароль", hashed) is False

    def test_long_password(self):
        """Длинные пароли работают"""
        long_pass = "A" * 1000
        hashed = hash_password(long_pass)
        assert verify_password(long_pass, hashed) is True

    def test_special_characters(self):
        """Спецсимволы в пароле"""
        special = "p@$$w0rd!#%^&*()_+{}|:<>?"
        hashed = hash_password(special)
        assert verify_password(special, hashed) is True


class TestGenerateStrongPassword:
    def test_default_length(self):
        pwd = generate_strong_password()
        assert len(pwd) == 12

    def test_custom_length(self):
        pwd = generate_strong_password(20)
        assert len(pwd) == 20

    def test_min_length_enforced(self):
        """Минимум 8 символов"""
        pwd = generate_strong_password(3)
        assert len(pwd) == 8

    def test_contains_variety(self):
        """Содержит буквы, цифры или спецсимволы"""
        pwd = generate_strong_password(50)
        has_letter = any(c.isalpha() for c in pwd)
        has_digit = any(c.isdigit() for c in pwd)
        assert has_letter
        assert has_digit

    def test_randomness(self):
        """Два пароля не совпадают"""
        p1 = generate_strong_password()
        p2 = generate_strong_password()
        assert p1 != p2
