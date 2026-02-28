# -*- coding: utf-8 -*-
"""
Покрытие utils/dialog_helpers.py — ~6 тестов (через моки Qt).
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestCreateProgressDialog:
    """create_progress_dialog тесты через моки."""

    @pytest.fixture(autouse=True)
    def _patch_qt(self):
        mock_progress = MagicMock()
        mock_qpd = MagicMock(return_value=mock_progress)
        mock_qt = MagicMock()
        mock_qt.WindowModal = 1
        mock_qt.FramelessWindowHint = 0x0800
        mock_qt.Dialog = 0x0001

        with patch.dict('sys.modules', {
            'PyQt5': MagicMock(),
            'PyQt5.QtWidgets': MagicMock(QProgressDialog=mock_qpd),
            'PyQt5.QtCore': MagicMock(Qt=mock_qt),
        }):
            if 'utils.dialog_helpers' in sys.modules:
                del sys.modules['utils.dialog_helpers']
            self.mock_progress = mock_progress
            self.mock_qpd = mock_qpd
            yield

    def test_creates_dialog(self):
        from utils.dialog_helpers import create_progress_dialog
        parent = MagicMock()
        result = create_progress_dialog('Заголовок', 'Текст', 'Отмена', 100, parent)
        assert result is not None

    def test_sets_window_title(self):
        from utils.dialog_helpers import create_progress_dialog
        parent = MagicMock()
        create_progress_dialog('Мой заголовок', 'Текст', None, 50, parent)
        self.mock_progress.setWindowTitle.assert_called_with('Мой заголовок')

    def test_shows_dialog(self):
        from utils.dialog_helpers import create_progress_dialog
        parent = MagicMock()
        create_progress_dialog('T', 'L', 'C', 10, parent)
        self.mock_progress.show.assert_called_once()

    def test_sets_fixed_size(self):
        from utils.dialog_helpers import create_progress_dialog
        parent = MagicMock()
        create_progress_dialog('T', 'L', 'C', 10, parent)
        self.mock_progress.setFixedSize.assert_called_once_with(420, 144)


class TestCenterDialogOnParent:
    """center_dialog_on_parent тесты."""

    @pytest.fixture(autouse=True)
    def _patch_qt(self):
        mock_app = MagicMock()
        mock_screen = MagicMock()
        mock_screen.x.return_value = 0
        mock_screen.y.return_value = 0
        mock_screen.width.return_value = 1920
        mock_screen.height.return_value = 1080
        mock_app.desktop.return_value.availableGeometry.return_value = mock_screen

        with patch.dict('sys.modules', {
            'PyQt5': MagicMock(),
            'PyQt5.QtWidgets': MagicMock(QApplication=mock_app),
            'PyQt5.QtCore': MagicMock(),
        }):
            if 'utils.dialog_helpers' in sys.modules:
                del sys.modules['utils.dialog_helpers']
            self.mock_app = mock_app
            yield

    def test_center_with_parent(self):
        from utils.dialog_helpers import center_dialog_on_parent
        dialog = MagicMock()
        dialog.width.return_value = 400
        dialog.height.return_value = 300
        parent = MagicMock()
        parent_window = MagicMock()
        parent.window.return_value = parent_window
        geom = MagicMock()
        geom.x.return_value = 100
        geom.y.return_value = 100
        geom.width.return_value = 800
        geom.height.return_value = 600
        parent_window.frameGeometry.return_value = geom
        center_dialog_on_parent(dialog, parent)
        dialog.move.assert_called_once()

    def test_center_without_parent(self):
        from utils.dialog_helpers import center_dialog_on_parent
        dialog = MagicMock()
        dialog.parent.return_value = None
        dialog.width.return_value = 400
        dialog.height.return_value = 300
        center_dialog_on_parent(dialog, None)
        dialog.move.assert_called_once()
