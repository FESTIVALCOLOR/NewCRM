# -*- coding: utf-8 -*-
"""Тесты для utils/preview_generator.py и utils/tab_helpers.py"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QTabWidget, QWidget
from PyQt5.QtCore import QEvent


# ─── PreviewGenerator ────────────────────────────────────────────────────

class TestPreviewGenerator:
    """Тесты PreviewGenerator"""

    def test_constants(self):
        from utils.preview_generator import PreviewGenerator
        assert PreviewGenerator.PREVIEW_WIDTH == 400
        assert PreviewGenerator.PREVIEW_HEIGHT == 267

    def test_generate_image_preview_nonexistent(self, qtbot):
        from utils.preview_generator import PreviewGenerator
        result = PreviewGenerator.generate_image_preview('/nonexistent/path.jpg')
        assert result is None

    def test_generate_image_preview_valid(self, qtbot, tmp_path):
        from PyQt5.QtGui import QPixmap
        # Создаём простое изображение
        img_path = str(tmp_path / 'test.png')
        pixmap = QPixmap(800, 600)
        pixmap.fill()
        pixmap.save(img_path)

        from utils.preview_generator import PreviewGenerator
        result = PreviewGenerator.generate_image_preview(img_path)
        assert result is not None
        assert result.width() <= 400
        assert result.height() <= 267

    def test_generate_image_preview_small_image(self, qtbot, tmp_path):
        from PyQt5.QtGui import QPixmap
        img_path = str(tmp_path / 'small.png')
        pixmap = QPixmap(50, 50)
        pixmap.fill()
        pixmap.save(img_path)

        from utils.preview_generator import PreviewGenerator
        result = PreviewGenerator.generate_image_preview(img_path)
        assert result is not None

    def test_generate_pdf_preview_no_pymupdf(self, qtbot):
        from utils.preview_generator import PreviewGenerator
        with patch('utils.preview_generator.HAS_PYMUPDF', False):
            result = PreviewGenerator.generate_pdf_preview('/fake/doc.pdf')
            assert result is None

    def test_generate_pdf_preview_nonexistent(self, qtbot):
        from utils.preview_generator import PreviewGenerator, HAS_PYMUPDF
        if HAS_PYMUPDF:
            result = PreviewGenerator.generate_pdf_preview('/nonexistent/doc.pdf')
            assert result is None


# ─── NoWheelTabWidget ────────────────────────────────────────────────────

class TestNoWheelTabWidget:
    """Тесты NoWheelTabWidget"""

    def test_creation(self, qtbot):
        from utils.tab_helpers import NoWheelTabWidget
        tw = NoWheelTabWidget()
        qtbot.addWidget(tw)
        assert tw is not None

    def test_add_tabs(self, qtbot):
        from utils.tab_helpers import NoWheelTabWidget
        tw = NoWheelTabWidget()
        qtbot.addWidget(tw)
        tw.addTab(QWidget(), 'Вкладка 1')
        tw.addTab(QWidget(), 'Вкладка 2')
        assert tw.count() == 2

    def test_event_filter_non_wheel(self, qtbot):
        from utils.tab_helpers import NoWheelTabWidget
        tw = NoWheelTabWidget()
        qtbot.addWidget(tw)
        tw.addTab(QWidget(), 'Tab')
        event = QEvent(QEvent.MouseButtonPress)
        result = tw.eventFilter(tw, event)
        # Не должен блокировать не-wheel события


# ─── disable_wheel_on_tabwidget ──────────────────────────────────────────

class TestDisableWheelOnTabwidget:
    """Тесты disable_wheel_on_tabwidget"""

    def test_installs_filter(self, qtbot):
        from utils.tab_helpers import disable_wheel_on_tabwidget
        tw = QTabWidget()
        qtbot.addWidget(tw)
        tw.addTab(QWidget(), 'Tab')
        filter_obj = disable_wheel_on_tabwidget(tw)
        assert filter_obj is not None
        assert hasattr(tw, '_wheel_filters')
        assert filter_obj in tw._wheel_filters

    def test_multiple_installs(self, qtbot):
        from utils.tab_helpers import disable_wheel_on_tabwidget
        tw = QTabWidget()
        qtbot.addWidget(tw)
        f1 = disable_wheel_on_tabwidget(tw)
        f2 = disable_wheel_on_tabwidget(tw)
        assert len(tw._wheel_filters) == 2
