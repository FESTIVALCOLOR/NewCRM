# -*- coding: utf-8 -*-
"""
Полное покрытие utils/message_helper.py — ~8 тестов.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture(autouse=True)
def _mock_custom_message_box():
    """Мок CustomMessageBox для тестов без Qt."""
    mock_cls = MagicMock()
    mock_instance = MagicMock()
    mock_cls.return_value = mock_instance
    with patch.dict('sys.modules', {
        'PyQt5': MagicMock(),
        'PyQt5.QtWidgets': MagicMock(),
        'PyQt5.QtCore': MagicMock(),
        'PyQt5.QtGui': MagicMock(),
        'ui': MagicMock(),
        'ui.custom_message_box': MagicMock(CustomMessageBox=mock_cls),
    }):
        # Переимпортируем
        if 'utils.message_helper' in sys.modules:
            del sys.modules['utils.message_helper']
        yield mock_cls, mock_instance


class TestShowWarning:
    def test_calls_custom_message_box(self, _mock_custom_message_box):
        mock_cls, mock_instance = _mock_custom_message_box
        from utils.message_helper import show_warning
        parent = MagicMock()
        show_warning(parent, 'Ошибка', 'Текст')
        mock_cls.assert_called_once_with(parent, 'Ошибка', 'Текст', 'warning')
        mock_instance.exec_.assert_called_once()


class TestShowError:
    def test_calls_custom_message_box(self, _mock_custom_message_box):
        mock_cls, mock_instance = _mock_custom_message_box
        from utils.message_helper import show_error
        parent = MagicMock()
        show_error(parent, 'Ошибка', 'Текст ошибки')
        mock_cls.assert_called_once_with(parent, 'Ошибка', 'Текст ошибки', 'error')
        mock_instance.exec_.assert_called_once()


class TestShowSuccess:
    def test_calls_custom_message_box(self, _mock_custom_message_box):
        mock_cls, mock_instance = _mock_custom_message_box
        from utils.message_helper import show_success
        parent = MagicMock()
        show_success(parent, 'Успех', 'Сохранено')
        mock_cls.assert_called_once_with(parent, 'Успех', 'Сохранено', 'success')
        mock_instance.exec_.assert_called_once()


class TestShowInfo:
    def test_calls_custom_message_box(self, _mock_custom_message_box):
        mock_cls, mock_instance = _mock_custom_message_box
        from utils.message_helper import show_info
        parent = MagicMock()
        show_info(parent, 'Инфо', 'Текст')
        mock_cls.assert_called_once_with(parent, 'Инфо', 'Текст', 'info')
        mock_instance.exec_.assert_called_once()
