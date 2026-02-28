# -*- coding: utf-8 -*-
"""
Полное покрытие utils/resource_path.py — ~5 тестов.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.resource_path import resource_path


class TestResourcePath:
    def test_returns_string(self):
        result = resource_path('resources/logo.png')
        assert isinstance(result, str)

    def test_contains_relative_path(self):
        result = resource_path('resources/icons/edit.svg')
        assert 'resources' in result and 'edit.svg' in result

    def test_returns_absolute_path(self):
        result = resource_path('test.txt')
        assert os.path.isabs(result)

    def test_with_meipass(self):
        """Симуляция PyInstaller environment."""
        old = getattr(sys, '_MEIPASS', None)
        sys._MEIPASS = '/tmp/pyinstaller_temp'
        try:
            result = resource_path('resources/logo.png')
            assert result.startswith('/tmp/pyinstaller_temp')
        finally:
            if old is None:
                del sys._MEIPASS
            else:
                sys._MEIPASS = old

    def test_empty_relative_path(self):
        result = resource_path('')
        assert isinstance(result, str)
