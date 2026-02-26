# -*- coding: utf-8 -*-
"""
Полное покрытие utils/password_utils.py — ~15 тестов.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.password_utils import hash_password, verify_password, generate_strong_password


class TestHashPassword:
    def test_returns_string(self):
        result = hash_password('test123')
        assert isinstance(result, str)

    def test_contains_dollar_separator(self):
        result = hash_password('test123')
        assert '$' in result

    def test_different_hashes_for_same_password(self):
        h1 = hash_password('test123')
        h2 = hash_password('test123')
        assert h1 != h2  # разные соли

    def test_nonempty_result(self):
        result = hash_password('x')
        assert len(result) > 10


class TestVerifyPassword:
    def test_correct_password(self):
        hashed = hash_password('MySecret')
        assert verify_password('MySecret', hashed) is True

    def test_wrong_password(self):
        hashed = hash_password('MySecret')
        assert verify_password('WrongPass', hashed) is False

    def test_plaintext_rejected(self):
        assert verify_password('admin', 'admin') is False

    def test_empty_password(self):
        hashed = hash_password('')
        assert verify_password('', hashed) is True

    def test_unicode_password(self):
        hashed = hash_password('Пароль123')
        assert verify_password('Пароль123', hashed) is True
        assert verify_password('Пароль456', hashed) is False

    def test_invalid_stored_format(self):
        assert verify_password('test', 'invalid_base64$also_invalid') is False


class TestGenerateStrongPassword:
    def test_default_length(self):
        pwd = generate_strong_password()
        assert len(pwd) == 12

    def test_custom_length(self):
        pwd = generate_strong_password(20)
        assert len(pwd) == 20

    def test_min_length_enforced(self):
        pwd = generate_strong_password(3)
        assert len(pwd) == 8  # минимум 8

    def test_unique_passwords(self):
        p1 = generate_strong_password()
        p2 = generate_strong_password()
        assert p1 != p2
