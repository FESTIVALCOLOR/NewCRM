# -*- coding: utf-8 -*-
"""
Тесты utils/resource_path.py — определение путей к ресурсам.

Покрытие:
  - TestResourcePathDev (5) — поведение в dev-режиме (без PyInstaller)
  - TestResourcePathPyInstaller (5) — поведение при упаковке через PyInstaller
ИТОГО: 10 тестов
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.resource_path import resource_path


class TestResourcePathDev:
    """Тесты resource_path() в режиме разработки (без PyInstaller)."""

    def test_returns_string(self):
        """Результат — строка."""
        result = resource_path('resources/logo.png')
        assert isinstance(result, str)

    def test_relative_path_appended(self):
        """Относительный путь добавляется к базовому."""
        result = resource_path('resources/logo.png')
        assert result.endswith('resources/logo.png') or result.endswith('resources\\logo.png')

    def test_base_path_is_cwd_without_meipass(self):
        """Без _MEIPASS базовый путь = os.path.abspath('.')."""
        # Убеждаемся, что _MEIPASS не установлен
        if hasattr(sys, '_MEIPASS'):
            pytest.skip("_MEIPASS уже установлен в окружении")
        expected_base = os.path.abspath(".")
        result = resource_path('test.txt')
        assert result == os.path.join(expected_base, 'test.txt')

    def test_empty_relative_path(self):
        """Пустой относительный путь — возвращает базовый путь."""
        result = resource_path('')
        expected_base = os.path.abspath(".")
        assert result == expected_base or result == expected_base + os.sep

    def test_nested_path(self):
        """Вложенные пути корректно соединяются."""
        result = resource_path('resources/icons/edit.svg')
        assert 'resources' in result
        assert 'icons' in result
        assert 'edit.svg' in result


class TestResourcePathPyInstaller:
    """Тесты resource_path() при симуляции PyInstaller (_MEIPASS)."""

    def test_uses_meipass_when_available(self):
        """При наличии sys._MEIPASS использует его как базовый путь."""
        fake_meipass = '/tmp/_MEI_test_12345'
        with patch.object(sys, '_MEIPASS', fake_meipass, create=True):
            result = resource_path('resources/logo.png')
            assert result.startswith(fake_meipass)

    def test_meipass_joins_relative_path(self):
        """_MEIPASS + относительный путь соединяются через os.path.join."""
        fake_meipass = '/tmp/_MEI_test_67890'
        with patch.object(sys, '_MEIPASS', fake_meipass, create=True):
            result = resource_path('data/config.json')
            expected = os.path.join(fake_meipass, 'data/config.json')
            assert result == expected

    def test_meipass_empty_relative(self):
        """_MEIPASS + пустая строка."""
        fake_meipass = '/tmp/_MEI_empty'
        with patch.object(sys, '_MEIPASS', fake_meipass, create=True):
            result = resource_path('')
            assert result == fake_meipass or result == fake_meipass + os.sep

    def test_meipass_windows_style_path(self):
        """_MEIPASS с Windows-стилем пути."""
        fake_meipass = 'C:\\Users\\user\\AppData\\Local\\Temp\\_MEI1234'
        with patch.object(sys, '_MEIPASS', fake_meipass, create=True):
            result = resource_path('resources/icons/save.svg')
            assert fake_meipass in result
            assert 'save.svg' in result

    def test_meipass_overrides_cwd(self):
        """_MEIPASS имеет приоритет над текущей рабочей директорией."""
        fake_meipass = '/opt/pyinstaller_bundle'
        cwd = os.path.abspath(".")
        with patch.object(sys, '_MEIPASS', fake_meipass, create=True):
            result = resource_path('test.txt')
            # Результат должен содержать _MEIPASS, а не cwd
            assert result.startswith(fake_meipass)
            if cwd != fake_meipass:
                assert not result.startswith(cwd)
